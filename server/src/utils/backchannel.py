"""Soft listening continuers while the user still holds the floor."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Literal

from livekit.agents import (
    AgentSession,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
    UserStateChangedEvent,
)
from livekit.agents.voice.events import _AgentBackchannelOpportunityEvent

from constants import SupportState

logger = logging.getLogger(__name__)

# Soft continuers when the user is clearly still holding the floor (low EOT).
_BACKCHANNEL_RISKY = {
    "hi": ["haan haan", "acha", "samajh gaya", "theek hai"],
    "en": ["yeah", "okay", "right", "I see"],
}
# Safer sounds near a possible turn boundary (higher EOT).
_BACKCHANNEL_SAFE = {
    "hi": ["hmm", "haan", "mm", "hmm hmm"],
    "en": ["mm-hmm", "uh-huh", "hmm", "mm"],
}


def _backchannel_lang_key(language: str | None) -> Literal["hi", "en"]:
    code = (language or "hi-IN").lower()
    if code.startswith("en"):
        return "en"
    return "hi"


class ListeningBackchannel:
    """Play short affirmations while the user is still holding the floor.

    Primary: LiveKit cloud turn-detector ``on_agent_backchannel_opportunity``
    (often silent — mini model / missing server thresholds produce no signal).

    Fallback: when the user pauses mid-story (speaking → listening) after enough
    speech, emit a soft continuer unless the agent has already started a reply.
    """

    def __init__(
        self,
        session: AgentSession[SupportState],
        *,
        frequency: float = 0.7,
        cooldown_s: float = 3.0,
        min_speech_s: float = 2.0,
        pause_delay_s: float = 0.35,
    ) -> None:
        self._session = session
        self._frequency = frequency
        self._cooldown_s = cooldown_s
        self._min_speech_s = min_speech_s
        self._pause_delay_s = pause_delay_s
        self._last_emitted_at = 0.0
        self._speech_started_at: float | None = None
        self._turn_chars = 0
        self._pause_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._cloud_hits = 0

    def attach(self) -> None:
        self._session.on("user_state_changed", self._on_user_state)
        self._session.on("agent_state_changed", self._on_agent_state)
        self._session.on("user_input_transcribed", self._on_transcript)

        activity = getattr(self._session, "_activity", None)
        if activity is not None:
            activity.on_agent_backchannel_opportunity = self.on_opportunity
            logger.info("backchannel: cloud opportunity hook attached")
        else:
            logger.warning(
                "backchannel: no activity yet; using pause/heartbeat fallback"
            )

        logger.info(
            "backchannel ready (pause+heartbeat fallback, cooldown=%.1fs, min_speech=%.1fs)",
            self._cooldown_s,
            self._min_speech_s,
        )

    def on_opportunity(self, ev: _AgentBackchannelOpportunityEvent) -> None:
        self._cloud_hits += 1
        threshold = ev.end_of_turn_threshold or 1.0
        eot_frac = ev.end_of_turn_probability / threshold if threshold > 0 else 1.0
        lang_key = _backchannel_lang_key(
            ev.language or self._session.userdata.language
        )
        pool = (
            _BACKCHANNEL_RISKY[lang_key]
            if eot_frac < 0.15
            else _BACKCHANNEL_SAFE[lang_key]
        )
        self._maybe_say(random.choice(pool), reason="cloud")

    def _on_user_state(self, ev: UserStateChangedEvent) -> None:
        if ev.new_state == "speaking":
            if self._speech_started_at is None:
                self._speech_started_at = time.time()
            self._cancel_pause_task()
            self._ensure_heartbeat()
            return

        if ev.old_state == "speaking" and ev.new_state == "listening":
            self._stop_heartbeat()
            self._cancel_pause_task()
            self._pause_task = asyncio.create_task(self._pause_backchannel())

    def _on_agent_state(self, ev: AgentStateChangedEvent) -> None:
        # Agent started a real reply — reset turn tracking / cancel pending continuer.
        if ev.new_state == "thinking":
            self._cancel_pause_task()
            self._stop_heartbeat()
            self._speech_started_at = None
            self._turn_chars = 0

    def _on_transcript(self, ev: UserInputTranscribedEvent) -> None:
        if not ev.is_final or not ev.transcript:
            return
        self._turn_chars += len(ev.transcript.strip())

    def _cancel_pause_task(self) -> None:
        if self._pause_task is not None and not self._pause_task.done():
            self._pause_task.cancel()
        self._pause_task = None

    def _ensure_heartbeat(self) -> None:
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def _stop_heartbeat(self) -> None:
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        """Soft continuer during long continuous speech (no VAD pause)."""
        try:
            while self._session.user_state == "speaking":
                await asyncio.sleep(max(self._cooldown_s, 4.0))
                if self._session.user_state != "speaking":
                    return
                if self._session.agent_state not in ("listening", "idle"):
                    return
                speech_s = (
                    time.time() - self._speech_started_at
                    if self._speech_started_at is not None
                    else 0.0
                )
                if speech_s < self._min_speech_s:
                    continue
                lang_key = _backchannel_lang_key(self._session.userdata.language)
                self._maybe_say(
                    random.choice(_BACKCHANNEL_SAFE[lang_key]), reason="heartbeat"
                )
        except asyncio.CancelledError:
            return

    async def _pause_backchannel(self) -> None:
        try:
            await asyncio.sleep(self._pause_delay_s)
        except asyncio.CancelledError:
            return

        # User resumed, or agent already took the turn.
        if self._session.user_state != "listening":
            return
        if self._session.agent_state != "listening":
            return

        speech_s = (
            time.time() - self._speech_started_at
            if self._speech_started_at is not None
            else 0.0
        )
        if speech_s < self._min_speech_s and self._turn_chars < 40:
            logger.debug(
                "backchannel skip: too little speech yet (%.1fs, %d chars)",
                speech_s,
                self._turn_chars,
            )
            return

        lang_key = _backchannel_lang_key(self._session.userdata.language)
        # Prefer soft sounds on pause fallback — less likely to collide with a real reply.
        phrase = random.choice(_BACKCHANNEL_SAFE[lang_key])
        self._maybe_say(phrase, reason="pause")

    def _maybe_say(self, phrase: str, *, reason: str) -> None:
        now = time.time()
        if now - self._last_emitted_at < self._cooldown_s:
            return
        if self._session.agent_state == "thinking":
            return
        if random.random() > self._frequency:
            return

        self._last_emitted_at = now
        logger.info(
            "backchannel [%s]: %r (cloud_hits=%d)", reason, phrase, self._cloud_hits
        )
        try:
            self._session.say(
                phrase,
                add_to_chat_ctx=False,
                allow_interruptions=True,
            )
        except Exception:
            logger.exception("backchannel say failed")
