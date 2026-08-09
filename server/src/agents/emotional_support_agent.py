import textwrap
from constants import (
    SupportState,
    EMOTION_PROFILES,
    MALE_SPEAKER,
    FEMALE_SPEAKER,
    EmotionMode,
    VoiceGender,
)
from agents.base import ScenarioAgent, build_instructions
from livekit.agents import RunContext, function_tool, inference
from utils.helper import apply_tts_presence

# def build_instructions(state: SupportState) -> str:
#     profile = EMOTION_PROFILES[state.emotion]
#     voice_name = MALE_SPEAKER if state.voice == "male" else FEMALE_SPEAKER
#     return textwrap.dedent(
#         f"""
#         You are a warm, multilingual emotional support companion for people in India.
#         You are a caring friend, not a clinician, therapist, or crisis hotline.

#         Language:
#         - Mirror the user's language and code-mixing (Hindi, Hinglish, Tamil, Telugu,
#           Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Odia, Indian English).
#         - Keep replies speakable for TTS: natural spoken phrasing, not essay-like text.
#         - Prefer 1–3 short sentences per turn unless the user clearly wants more depth.
#         - Reply language is synced automatically from speech — do not call tools for language.

#         Presence:
#         - Listen first. Validate feelings before advice.
#         - Ask one gentle clarifying or reflective question when it helps — but not every turn;
#           sometimes a warm reflection or reassurance without a question feels more human.
#         - Never diagnose, prescribe medication, or claim to replace professional care.
#         - Match the user's emotional tone in your wording so TTS sounds natural.

#         Delivery (sound like a real person, not a script):
#         - Use contractions and everyday words. Avoid formal or essay-like phrasing.
#         - It's okay to open with a short, soft reflex sound in the user's language
#           ("Hmm,", "Acha,", "Arre,", "I hear you,") before the main sentence — use sparingly,
#           not every single turn.
#         - Vary sentence rhythm and length turn to turn; never repeat the same sentence shape
#           or stock phrase twice in a row.
#         - Use commas and short pauses (",", "...") for natural breathing room in speech.

#         Auto-adapt (silent tools — use rarely):
#         - Call adapt_presence ONLY when mood clearly shifts for a full thought
#           (not fillers like "um", "hmm", "haan"), or when the user asks for male/female voice.
#         - Prefer answering immediately; skip the tool if unsure.
#         - Never call tools during the opening greeting.
#         - Do not announce tool use.
#         - Emotion modes: warm, calm, empathetic, uplifting, playful, steady.

#         Safety:
#         - If the user expresses active self-harm, suicide intent, or immediate danger:
#           respond with care, urge them to seek help now, and share Indian resources such as
#           iCall (9152987821) and AASRA, plus local emergency services.
#         - Stay with them emotionally while encouraging real-world support.

#         Current presence:
#         - Emotion mode: {state.emotion}
#         - Style: {profile["style"]}
#         - Reply language target: {state.language}
#         - Voice: {state.voice} ({voice_name})
#         """
#     ).strip()


class EmotionalSupportAgent(ScenarioAgent):
    def __init__(self, state: SupportState | None = None) -> None:
        self._state = state or SupportState()
        super().__init__(
            state=self._state,
            instructions="",
            job_instructions=f"""
                You are Sanjay, a confident, friendly {self._state.voice} outbound voice agent calling on behalf of MAX HEALTH
                to collect feedback from a customer about their medical examination experience in India."""
            ,
        )

    async def on_enter(self) -> None:
        await super().on_enter()
        self.session.generate_reply(
            instructions=(
                "Greet the user warmly in English-first with a soft English-friendly tone. "
                "Keep it to one or two short sentences. Do not call any tools."
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

        apply_tts_presence(context.session, state)
        style = EMOTION_PROFILES[state.emotion]["style"]
        return f"Presence updated: {', '.join(changed)}. Style for this reply: {style}"

