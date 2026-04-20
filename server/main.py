import logging
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
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
from agents.tools import end_call

load_dotenv()


logger = logging.getLogger("avatar")
logger.setLevel(logging.INFO)


@dataclass
class UserData:
    ctx: Optional[JobContext] = None


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    interaction_mode, _ = resolveRoomMetadata(ctx.room.metadata)

    vad = ctx.proc.userdata["vad"]
    turn_detector = MultilingualModel()

    realtime_model = google.realtime.RealtimeModel(
        voice="Charon",
    )

    session = AgentSession(
        llm=realtime_model,
        tools=[google.tools.GoogleSearch(), end_call],
        turn_handling=TurnHandlingOptions(
            turn_detection=turn_detector,
        ),
        vad=vad,
        preemptive_generation=True,
    )

    @session.on("agent_false_interruption")
    def _on_false_interrupt(ev: AgentFalseInterruptionEvent):
        logger.info("False interruption detected → resuming")
        session.generate_reply(instructions=ev.extra_instructions or NOT_GIVEN)

    @session.on("overlapping_speech")
    def _on_user_interrupt(ev):
        logger.info("User interruption → stopping response")
        session.generate_reply(
            instructions="User interrupted, respond concisely.",
        )

    def noise_filter(params):
        if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            return noise_cancellation.BVCTelephony()
        else:
            return noise_cancellation.BVC()

    if interaction_mode == "video":
        avatar = bey.AvatarSession(
            avatar_id="2ed7477f-3961-4ce1-b331-5e4530c55a57",
        )
        await avatar.start(session, room=ctx.room)

    await session.start(
        agent=getAgent(ctx.room.metadata),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_filter,
            ),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="production-voice-agent",
        )
    )
