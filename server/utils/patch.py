# ============================================================================
# MONKEY-PATCH: Gemini 3.1 Flash Live — send_client_content compatibility
# ----------------------------------------------------------------------------
# Gemini 3.1 rejects ALL send_client_content calls (the old way of sending
# text turns). The LiveKit plugin's generate_reply() uses send_client_content
# internally to trigger the model to speak (e.g., greeting on_enter).
#
# This patch swaps generate_reply() to use send_realtime_input() instead,
# which 3.1 accepts. Only activates for models with "3.1" in the name —
# 2.5 models continue to use the original unpatched method.
#
# TODO(livekit-update): REMOVE this entire block when livekit-plugins-google
# ships native Gemini 3.1 support. Track: https://github.com/livekit/agents
# ============================================================================
try:
    from livekit.plugins.google.realtime.realtime_api import RealtimeSession as _GeminiRS
    from livekit.agents.types import NOT_GIVEN as _NOT_GIVEN
    from livekit.agents.utils import is_given as _is_given
    import asyncio
    from google.genai import types

    _original_generate_reply = _GeminiRS.generate_reply

    def _patched_generate_reply(self, *, instructions=_NOT_GIVEN, tool_choice, tools):
        # Non-3.1 models: use original (send_client_content works fine)
        if "3.1" not in getattr(getattr(self, "_opts", None), "model", ""):
            return _original_generate_reply(self, instructions=instructions)

        # --- 3.1 path: replicate generate_reply but with send_realtime_input ---
        if self._pending_generation_fut and not self._pending_generation_fut.done():
            self._pending_generation_fut.cancel(
                "Superseded by new generate_reply call")

        fut = asyncio.Future()
        self._pending_generation_fut = fut

        if self._in_user_activity:
            self._send_client_event(
                types.LiveClientRealtimeInput(activity_end=types.ActivityEnd())
            )
            self._in_user_activity = False

        # 3.1 fix: send text via send_realtime_input instead of send_client_content
        text = instructions if _is_given(instructions) else "."
        self._send_client_event(types.LiveClientRealtimeInput(text=text))

        def _on_timeout():
            if not fut.done():
                from livekit.agents.llm import RealtimeError
                fut.set_exception(
                    RealtimeError(
                        "generate_reply timed out waiting for generation_created event.")
                )
                if self._pending_generation_fut is fut:
                    self._pending_generation_fut = None

        timeout_handle = asyncio.get_event_loop().call_later(5.0, _on_timeout)
        fut.add_done_callback(lambda _: timeout_handle.cancel())
        return fut

    _GeminiRS.generate_reply = _patched_generate_reply
except ImportError:
    pass  # Non-Google agents skip this patch
