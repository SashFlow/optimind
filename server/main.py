import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    NOT_GIVEN,
    AgentFalseInterruptionEvent,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    room_io,
)
from livekit.agents.voice import AgentSession
from livekit.plugins import bey, google, noise_cancellation, silero

from agents import getAgent, getUserData, resolveRoomMetadata
from agents.tools import end_call, transfer_to_human

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    interaction_mode, _ = resolveRoomMetadata(ctx.job.metadata)
    userdata = getUserData(ctx.job.metadata)
    session = AgentSession[userdata](
        llm=google.realtime.RealtimeModel(
            model="gemini-live-2.5-flash-native-audio",
            vertexai=True,
            voice="Charon",
        ),
        tools=[google.tools.GoogleSearch(), end_call, transfer_to_human],
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )
    if interaction_mode == "video":
        avatar = bey.AvatarSession(
            avatar_id="2ed7477f-3961-4ce1-b331-5e4530c55a57",
        )

        await avatar.start(session, room=ctx.room)

    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev: AgentFalseInterruptionEvent):
        logger.info("false positive interruption, resuming")
        session.generate_reply(instructions=ev.extra_instructions or NOT_GIVEN)

    await session.start(
        agent=getAgent(ctx.job.metadata),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint, prewarm_fnc=prewarm, agent_name="demo-agent"
        )
    )
