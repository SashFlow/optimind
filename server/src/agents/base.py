"""Base agent for the support agent."""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import textwrap
from typing import Any
import asyncio

from livekit.agents.voice import Agent
from livekit.agents import RunContext, function_tool, inference
from constants import (
    SupportState,
    EMOTION_PROFILES,
    MALE_SPEAKER,
    FEMALE_SPEAKER,
    EmotionMode,
    VoiceGender,
)
from utils.helper import apply_tts_presence
from prompts import SESSION_INSTRUCTIONS


logger = logging.getLogger(__name__)


def build_instructions(
    instructions: str, job_instructions: str, state: SupportState
) -> str:
    """Build the instructions for the agent."""
    profile = EMOTION_PROFILES[state.emotion]
    voice_name = MALE_SPEAKER if state.voice == "male" else FEMALE_SPEAKER
    return textwrap.dedent(
        f"""
        Job Instructions:
        {job_instructions}

        Date and Time:
        - The current local time is {datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A, %d, %B %Y %H:%M:%S")}.

        You are a warm, multilingual companion for people in India.

        Language:
        - Mirror the user's language and code-mixing (Hindi, Hinglish, Tamil, Telugu,
          Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Odia, Indian English).
        - Keep replies speakable for TTS: natural spoken phrasing, not essay-like text.
        - Prefer 1-2 short sentences per turn unless the user clearly wants more depth.
        - Reply language is synced automatically from speech — do not call tools for language.

        Personality:
        - Ask only one question at a time.
        - Give a brief acknowledgment after each answer before moving to the next question.
        - Empathize with the user and acknowledge their feedback when relevant.
        - Never diagnose, prescribe medication, or claim to replace professional care.
        - Match the user's emotional tone in your wording so TTS sounds natural.
        - Incase of a scripted question, add some prefix and suffix to the question to make it sound natural.
        - Reaffirm the user's feelings and emotions in your response.
        - Incase of vague response, ask clarifying questions until you get the full picture.

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

        Current presence:
        - Emotion mode: {state.emotion}
        - Style: {profile["style"]}
        - Reply language target: {state.language}
        - Voice: {state.voice} ({voice_name})

        {instructions}
        """
    ).strip()


class ScenarioAgent(Agent):
    """Base agent for the scenario agent."""

    def __init__(
        self, *, instructions: str, job_instructions: str, state: SupportState
    ) -> None:
        self._state = state or SupportState()
        self._end_call_invoked: bool = False
        self._current_step: str = "greeting"
        super().__init__(
            llm=inference.LLM(
                model="google/gemini-3.1-flash-lite",
                extra_kwargs={"temperature": 0.5},
            ),
            instructions=build_instructions(
                job_instructions=job_instructions,
                instructions=instructions,
                state=self._state,
            ),
        )

    async def on_enter(self) -> None:
        await super().on_enter()
        self.session.generate_reply(
            instructions=(
                "Greet the user warmly in Hindi-first with a soft English-friendly tone. "
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

    @function_tool()
    async def end_call(self, context: RunContext) -> str:
        """End the call after your final goodbye has been spoken.

        Call exactly once at the end of the conversation. Speak your goodbye first in the
        same turn, then invoke this tool. After this tool returns, produce no further
        speech or tool calls.
        """
        if self._end_call_invoked or getattr(
            context.session, "_end_call_invoked", False
        ):
            logger.debug("end_call ignored — already invoked")
            return "TERMINAL: Call already ended. Produce no further output."

        self._end_call_invoked = True
        context.session._end_call_invoked = True
        logger.info("Insurance feedback call ending")
        context.session.shutdown()
        return "TERMINAL: Call ended. Produce no further output."

    @function_tool()
    async def schedule_callback(
        self, _context: RunContext, preferred_time: str = ""
    ) -> dict[str, Any]:
        """Schedule a callback for the customer at a preferred time.

        Use when the customer is unavailable, interrupted, or requests a later call.

        Args:
            preferred_time: Customer's preferred callback time (free text). Optional.
        """
        await asyncio.sleep(2)
        callback_time = preferred_time.strip() if preferred_time else "within 2 hours"
        self._current_step = "closing"
        return {
            "scheduled": True,
            "callback_time": callback_time,
            "current_step": self._current_step,
            "next_action": "Say a brief goodbye, then call end_call exactly once.",
        }
