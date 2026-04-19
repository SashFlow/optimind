import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from google.genai import types
from livekit import rtc
from livekit.agents import (
    NOT_GIVEN,
    AgentFalseInterruptionEvent,
    JobContext,
    JobProcess,
    TurnHandlingOptions,
    WorkerOptions,
    cli,
    room_io,
)
from livekit.agents.voice import AgentSession
from livekit.plugins import bey, google, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from agents import getAgent, resolveRoomMetadata

load_dotenv()

logger = logging.getLogger("avatar")
logger.setLevel(logging.INFO)


@dataclass
class UserData:
    """Class to store user data during a session."""

    ctx: Optional[JobContext] = None


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    interaction_mode, _ = resolveRoomMetadata(ctx.room.metadata)
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-live-2.5-flash-native-audio",
            vertexai=True,
            # realtime_input_config=types.RealtimeInputConfig(
            #     automatic_activity_detection=types.AutomaticActivityDetection(
            #         disabled=True,
            #     ),
            # ),
            voice="Charon",
            input_audio_transcription=None,
        ),
        tools=[google.tools.GoogleSearch()],
        # turn_handling=TurnHandlingOptions(turn_detection=MultilingualModel()),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev: AgentFalseInterruptionEvent):
        logger.info("false positive interruption, resuming")
        session.generate_reply(instructions=ev.extra_instructions or NOT_GIVEN)

    await session.start(
        agent=getAgent(ctx.room.metadata),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )
    if interaction_mode == "video":
        avatar = bey.AvatarSession(
            avatar_id="2ed7477f-3961-4ce1-b331-5e4530c55a57",
        )

        await avatar.start(session, room=ctx.room)
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint, prewarm_fnc=prewarm, agent_name="demo-agent"
        )
    )
