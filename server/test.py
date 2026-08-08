import asyncio
import logging
import random
import textwrap
import time
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AgentStateChangedEvent,
    JobContext,
    RunContext,
    TurnHandlingOptions,
    UserInputTranscribedEvent,
    UserStateChangedEvent,
    cli,
    function_tool,
    inference,
    room_io,
)
from livekit.agents.voice.events import _AgentBackchannelOpportunityEvent
from livekit.plugins import ai_coustics, sarvam

logger = logging.getLogger("agent")

load_dotenv(".env")

EmotionMode = Literal["warm", "calm", "empathetic", "uplifting", "playful", "steady"]
VoiceGender = Literal["male", "female"]
SarvamLanguage = Literal[
    "bn-IN",
    "en-IN",
    "gu-IN",
    "hi-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "od-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
]

TTS_LANGUAGES: set[str] = {
    "bn-IN",
    "en-IN",
    "gu-IN",
    "hi-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "od-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
}

MALE_SPEAKER = "shubh"
FEMALE_SPEAKER = "priya"

EMOTION_PROFILES: dict[EmotionMode, dict[str, float | str]] = {
    "warm": {
        "pace": 1.0,
        "temperature": 0.6,
        "style": "Be open, caring, and lightly conversational. Make the user feel welcome and safe.",
    },
    "calm": {
        "pace": 0.85,
        "temperature": 0.45,
        "style": "Speak slowly and grounding. Use short sentences. Help the user settle their breath and body.",
    },
    "empathetic": {
        "pace": 0.9,
        "temperature": 0.55,
        "style": "Offer soft validation. Sit with their feelings. Avoid toxic positivity or rushing to fix things.",
    },
    "uplifting": {
        "pace": 1.05,
        "temperature": 0.7,
        "style": "Offer gentle encouragement while staying grounded. Celebrate small strengths without dismissing pain.",
    },
    "playful": {
        "pace": 1.1,
        "temperature": 0.75,
        "style": "Match light, joking energy with warm humor. Never mock or minimize what matters to them.",
    },
    "steady": {
        "pace": 0.95,
        "temperature": 0.5,
        "style": "Stay calm and firm. De-escalate anger or frustration without matching intensity or blaming.",
    },
}


@dataclass
class SupportState:
    emotion: EmotionMode = "warm"
    language: SarvamLanguage = "hi-IN"
    voice: VoiceGender = "male"
    last_heard_language: str | None = None


def normalize_tts_language(language: str | None) -> SarvamLanguage | None:
    if not language:
        return None
    code = language.strip()
    if code in TTS_LANGUAGES:
        return code  # type: ignore[return-value]
    # e.g. "hi" / "en" → hi-IN / en-IN
    short = code.split("-", 1)[0].lower()
    mapped = {
        "bn": "bn-IN",
        "en": "en-IN",
        "gu": "gu-IN",
        "hi": "hi-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        "mr": "mr-IN",
        "or": "od-IN",
        "od": "od-IN",
        "pa": "pa-IN",
        "ta": "ta-IN",
        "te": "te-IN",
    }.get(short)
    return mapped  # type: ignore[return-value]


def apply_tts_presence(
    session: AgentSession[SupportState], state: SupportState
) -> None:
    """Update Sarvam TTS options only — no instruction rewrite (keeps replies fast)."""
    profile = EMOTION_PROFILES[state.emotion]
    speaker = MALE_SPEAKER if state.voice == "male" else FEMALE_SPEAKER
    tts = session.tts
    if tts is not None and hasattr(tts, "update_options"):
        tts.update_options(
            target_language_code=state.language,
            speaker=speaker,
            pace=float(profile["pace"]),
            temperature=float(profile["temperature"]),
        )


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
        lang_key = _backchannel_lang_key(ev.language or self._session.userdata.language)
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


def build_instructions(state: SupportState) -> str:
    profile = EMOTION_PROFILES[state.emotion]
    voice_name = MALE_SPEAKER if state.voice == "male" else FEMALE_SPEAKER
    return textwrap.dedent(
        f"""
        You are a warm, multilingual emotional support companion for people in India.
        You are a caring friend, not a clinician, therapist, or crisis hotline.

        Language:
        - Mirror the user's language and code-mixing (Hindi, Hinglish, Tamil, Telugu,
          Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Odia, Indian English).
        - Keep replies speakable for TTS: natural spoken phrasing, not essay-like text.
        - Prefer 1–3 short sentences per turn unless the user clearly wants more depth.
        - Reply language is synced automatically from speech — do not call tools for language.

        Presence:
        - Listen first. Validate feelings before advice.
        - Ask one gentle clarifying or reflective question when it helps — but not every turn;
          sometimes a warm reflection or reassurance without a question feels more human.
        - Never diagnose, prescribe medication, or claim to replace professional care.
        - Match the user's emotional tone in your wording so TTS sounds natural.

        Delivery (sound like a real person, not a script):
        - Use contractions and everyday words. Avoid formal or essay-like phrasing.
        - It's okay to open with a short, soft reflex sound in the user's language
          ("Hmm,", "Acha,", "Arre,", "I hear you,") before the main sentence — use sparingly,
          not every single turn.
        - Vary sentence rhythm and length turn to turn; never repeat the same sentence shape
          or stock phrase twice in a row.
        - Use commas and short pauses (",", "...") for natural breathing room in speech.

        Auto-adapt (silent tools — use rarely):
        - Call adapt_presence ONLY when mood clearly shifts for a full thought
          (not fillers like "um", "hmm", "haan"), or when the user asks for male/female voice.
        - Prefer answering immediately; skip the tool if unsure.
        - Never call tools during the opening greeting.
        - Do not announce tool use.
        - Emotion modes: warm, calm, empathetic, uplifting, playful, steady.

        Safety:
        - If the user expresses active self-harm, suicide intent, or immediate danger:
          respond with care, urge them to seek help now, and share Indian resources such as
          iCall (9152987821) and AASRA, plus local emergency services.
        - Stay with them emotionally while encouraging real-world support.

        Current presence:
        - Emotion mode: {state.emotion}
        - Style: {profile["style"]}
        - Reply language target: {state.language}
        - Voice: {state.voice} ({voice_name})
        """
    ).strip()


class EmotionalSupportAgent(Agent):
    def __init__(self, state: SupportState | None = None) -> None:
        self._state = state or SupportState()
        super().__init__(
            # LiveKit Inference gateway: colocated infra (no extra hop to Google's API) +
            # flash-lite is tuned for lowest time-to-first-token — this is the same model
            # LiveKit itself defaults to for latency-critical greeting classification.
            llm=inference.LLM(
                model="google/gemini-3.1-flash-lite",
                extra_kwargs={"temperature": 0.85},
            ),
            instructions=build_instructions(self._state),
        )

    async def on_enter(self) -> None:
        await super().on_enter()
        self.session.generate_reply(
            instructions=(
                "Greet the user warmly in Hindi-first with a soft English-friendly tone. "
                "Let them know you are here with them and invite them to share what is on "
                "their mind. Keep it to one or two short sentences. Do not call any tools."
            ),
            tool_choice="none",
        )

    @function_tool()
    async def adapt_presence(
        self,
        context: RunContext[SupportState],
        emotion: EmotionMode | None = None,
        voice: VoiceGender | None = None,
    ) -> str:
        """Adapt emotion or companion voice. Language is synced automatically — do not pass it.

        Call rarely: only for a clear mood shift on a full user thought, or when the user
        asks for a male/female voice. Skip for fillers and short acknowledgements.

        Args:
            emotion: warm, calm, empathetic, uplifting, playful, or steady.
            voice: male or female; only when the user asks to change it.
        """
        state = context.userdata
        changed: list[str] = []

        if emotion is not None and emotion != state.emotion:
            state.emotion = emotion
            changed.append(f"emotion={emotion}")

        if voice is not None and voice != state.voice:
            state.voice = voice
            changed.append(f"voice={voice}")

        if not changed:
            return "Presence unchanged — continue your reply."

        # TTS only: skip update_instructions to avoid extra chat churn / Gemini lag.
        apply_tts_presence(context.session, state)
        style = EMOTION_PROFILES[state.emotion]["style"]
        logger.info("adapt_presence: %s", ", ".join(changed))
        return f"Presence updated: {', '.join(changed)}. Style for this reply: {style}"


server = AgentServer()


@server.rtc_session(agent_name="assistant")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    state = SupportState()
    session = AgentSession[SupportState](
        userdata=state,
        stt=sarvam.STT(
            model="saaras:v3",
            language="unknown",
            mode="codemix",
            sample_rate=16000,
            high_vad_sensitivity=True,
            # Ask Sarvam to finalize the transcript as soon as it sees our flush —
            # shaves the STT-side tail latency off every turn.
            flush_signal=True,
        ),
        tts=sarvam.TTS(
            model="bulbul:v3",
            speaker=MALE_SPEAKER,
            target_language_code=state.language,
            pace=float(EMOTION_PROFILES["warm"]["pace"]),
            temperature=float(EMOTION_PROFILES["warm"]["temperature"]),
            speech_sample_rate=8000,
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            # Dynamic endpointing: shrinks the wait when the semantic turn model is
            # confident the user is done, and only stretches toward max_delay when it
            # isn't sure (e.g. a slow Sarvam final) — much snappier than a fixed delay
            # on every single turn.
            endpointing={"mode": "dynamic", "min_delay": 0.2, "max_delay": 2.2},
            # Start LLM+TTS before the turn is fully confirmed.
            preemptive_generation={"enabled": True, "preemptive_tts": True},
        ),
    )

    @session.on("user_input_transcribed")
    def _sync_language(ev: UserInputTranscribedEvent) -> None:
        if not ev.is_final or not ev.language:
            return
        state.last_heard_language = str(ev.language)
        language = normalize_tts_language(ev.language)
        # Apply as soon as STT detects language so preemptive TTS uses the right code.
        if language is not None and language != state.language:
            state.language = language
            apply_tts_presence(session, state)
            logger.info("auto language=%s", language)

    await session.start(
        agent=EmotionalSupportAgent(state),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            ),
        ),
    )
    # Soft continuers while the user pauses mid-story (cloud hook + pause fallback).
    ListeningBackchannel(session).attach()
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
