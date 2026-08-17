# ============================================================================
# MONKEY-PATCH: Gemini 3.1 Flash Live — send_client_content compatibility
# ----------------------------------------------------------------------------
# Gemini 3.1 rejects mid-session send_client_content. LiveKit's generate_reply()
# uses that API, so 3.1 sessions time out waiting for generation_created.
#
# Official LiveKit stance (1.6+): generate_reply is "not compatible" with 3.1.
# This patch restores it via send_realtime_input(text=...), matching PR #5251.
#
# Improvements over the naive patch:
#   1. Wait for the Live websocket before sending / starting the timeout clock
#      (on_enter often races the cold connect — the #1 cause of 5s timeouts).
#   2. Longer generation timeout + one short-trigger retry.
#   3. Frame instructions as an internal directive (not raw "user speech").
#   4. Match upstream pending-future cancel / interrupt lifecycle.
#
# TODO(livekit-update): REMOVE when livekit-plugins-google natively supports
# Gemini 3.1 generate_reply. Track: https://github.com/livekit/agents/issues/5260
# ============================================================================
try:
    from livekit.plugins.google.realtime.realtime_api import RealtimeSession as _GeminiRS
    from livekit.agents.types import NOT_GIVEN as _NOT_GIVEN
    from livekit.agents.utils import is_given as _is_given
    from livekit.agents.llm import RealtimeError as _RealtimeError
    import asyncio
    import logging
    from google.genai import types

    _logger = logging.getLogger("utils.patch.gemini31")

    # Cold connect + first audio token often exceeds the plugin's default 5s.
    _SESSION_READY_TIMEOUT_S = 12.0
    _GENERATION_TIMEOUT_S = 12.0
    _MAX_ATTEMPTS = 2

    _original_generate_reply = _GeminiRS.generate_reply

    def _is_gemini_31(self) -> bool:
        model = getattr(getattr(self, "_opts", None), "model", "") or ""
        return "3.1" in model

    def _frame_instructions(instructions) -> str:
        """Realtime text is treated as user input — keep directives short and explicit."""
        if _is_given(instructions) and str(instructions).strip():
            body = str(instructions).strip()
            return (
                "[Internal directive — do not read this aloud. "
                "Speak in character and follow it now.]\n"
                f"{body}"
            )
        return (
            "[Internal directive — do not read this aloud.] "
            "Please begin speaking to the user now."
        )

    async def _wait_for_active_session(self, timeout: float) -> bool:
        """Block until Gemini Live websocket is up (or timeout)."""
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if getattr(self, "_active_session", None) is not None:
                return True
            if getattr(self, "_msg_ch", None) is not None and self._msg_ch.closed:
                return False
            await asyncio.sleep(0.05)
        return getattr(self, "_active_session", None) is not None

    def _end_user_activity_if_needed(self) -> None:
        if getattr(self, "_in_user_activity", False):
            self._send_client_event(
                types.LiveClientRealtimeInput(activity_end=types.ActivityEnd())
            )
            self._in_user_activity = False

    def _send_trigger_text(self, text: str) -> None:
        self._send_client_event(types.LiveClientRealtimeInput(text=text))

    async def _drive_31_generation(self, fut: asyncio.Future, instructions) -> None:
        """Wait for session, trigger generation, retry once on timeout."""
        try:
            ready = await _wait_for_active_session(self, _SESSION_READY_TIMEOUT_S)
            if not ready:
                if not fut.done():
                    fut.set_exception(
                        _RealtimeError(
                            "generate_reply failed: Gemini Live session not ready "
                            f"within {_SESSION_READY_TIMEOUT_S:.0f}s."
                        )
                    )
                return

            prompts = [
                _frame_instructions(instructions),
                # Fallback: minimal turn-complete nudge (same as 2.5 placeholder).
                "Please continue speaking now.",
            ]

            for attempt, text in enumerate(prompts[:_MAX_ATTEMPTS], start=1):
                if fut.done():
                    return

                if attempt > 1:
                    # Drop a late/hung first attempt before nudging again.
                    try:
                        self.interrupt()
                    except Exception:
                        _logger.debug("interrupt before retry failed", exc_info=True)

                _end_user_activity_if_needed(self)
                preview = text.replace("\n", " ").strip()
                if len(preview) > 80:
                    preview = preview[:77] + "..."
                _logger.info(
                    "gemini-3.1 generate_reply attempt %s/%s trigger=%r",
                    attempt,
                    _MAX_ATTEMPTS,
                    preview,
                )
                _send_trigger_text(self, text)

                try:
                    await asyncio.wait_for(
                        asyncio.shield(fut),
                        timeout=_GENERATION_TIMEOUT_S,
                    )
                    return
                except asyncio.TimeoutError:
                    _logger.warning(
                        "gemini-3.1 generate_reply attempt %s timed out after %.0fs",
                        attempt,
                        _GENERATION_TIMEOUT_S,
                    )
                    if attempt < _MAX_ATTEMPTS and not fut.done():
                        continue
                    if not fut.done():
                        fut.set_exception(
                            _RealtimeError(
                                "generate_reply timed out waiting for "
                                "generation_created event."
                            )
                        )
                    return
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Future already completed with result/exception via
                    # _start_new_generation — nothing else to do.
                    return
        except asyncio.CancelledError:
            # Generation may already have completed; only cancel if still pending.
            if not fut.done():
                fut.cancel()
            raise
        except Exception as exc:
            _logger.exception("gemini-3.1 generate_reply driver failed")
            if not fut.done():
                fut.set_exception(
                    _RealtimeError(f"generate_reply failed: {exc}")
                )
        finally:
            if getattr(self, "_pending_generation_fut", None) is fut:
                self._pending_generation_fut = None

    def _patched_generate_reply(
        self,
        *,
        instructions=_NOT_GIVEN,
        tool_choice=_NOT_GIVEN,
        tools=_NOT_GIVEN,
    ):
        if not _is_gemini_31(self):
            return _original_generate_reply(
                self,
                instructions=instructions,
                tool_choice=tool_choice,
                tools=tools,
            )

        if _is_given(tools):
            _logger.warning(
                "per-response tools is not supported by Google Realtime API, ignoring"
            )

        # Match upstream: clear slot before cancel so the done callback does not
        # treat supersession as an external cancel that interrupts Gemini.
        if self._pending_generation_fut and not self._pending_generation_fut.done():
            _logger.warning(
                "generate_reply called while another generation is pending, "
                "cancelling previous."
            )
            old_fut = self._pending_generation_fut
            self._pending_generation_fut = None
            old_fut.cancel("Superseded by new generate_reply call")

        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending_generation_fut = fut

        driver = loop.create_task(
            _drive_31_generation(self, fut, instructions),
            name="gemini31-generate-reply",
        )

        def _on_fut_done(f: asyncio.Future) -> None:
            if not driver.done():
                driver.cancel()
            is_current = self._pending_generation_fut is fut
            if is_current:
                self._pending_generation_fut = None
            if f.cancelled() and is_current:
                # External cancel: interrupt Gemini via activity_start.
                try:
                    self.interrupt()
                except Exception:
                    _logger.debug(
                        "interrupt after generate_reply cancel failed",
                        exc_info=True,
                    )

        fut.add_done_callback(_on_fut_done)
        return fut

    _GeminiRS.generate_reply = _patched_generate_reply
    _logger.info("Applied Gemini 3.1 generate_reply monkey-patch")
except ImportError:
    pass  # Non-Google agents skip this patch
