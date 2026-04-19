import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from livekit.agents import (
    NOT_GIVEN,
    AgentFalseInterruptionEvent,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import AgentSession
from livekit.plugins import bey, google, noise_cancellation, silero

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
        llm=google.beta.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Charon",
            vertexai=False,
        ),
        turn_handling={
            "interruption": {
                "mode": "adaptive",
            },
            "preemptive_generation": {"preemptive_tts": True},
        },
        turn_detection="realtime_llm",
        vad=ctx.proc.userdata["vad"],
    )

    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev: AgentFalseInterruptionEvent):
        logger.info("false positive interruption, resuming")
        session.generate_reply(instructions=ev.extra_instructions or NOT_GIVEN)

    await session.start(
        agent=getAgent(ctx.room.metadata),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
            delete_room_on_close=True,
            audio_enabled=True,
        ),
    )
    if interaction_mode == "video":
        avatar = bey.AvatarSession(
            avatar_id="2ed7477f-3961-4ce1-b331-5e4530c55a57",
        )

        await avatar.start(session, room=ctx.room)
    # Join the room and connect to the user
    await session.generate_reply(user_input="Greet user in a friendly manner.")
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
