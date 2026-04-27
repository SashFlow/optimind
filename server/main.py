import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    NOT_GIVEN,
    AgentFalseInterruptionEvent,
    AgentServer,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.agents.voice import AgentSession
from livekit.plugins import anam, google, noise_cancellation, silero

from agents import getAgent, getUserData, resolveRoomMetadata
from agents.tools import end_call, transfer_to_human

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="demo-agent")
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    interaction_mode, _ = resolveRoomMetadata(ctx.job.metadata)
    userdata = getUserData(ctx.job.metadata, ctx)
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-live-2.5-flash-native-audio",
            vertexai=True,
            voice="Charon",
        ),
        tools=[google.tools.GoogleSearch(), end_call, transfer_to_human],
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        userdata=userdata,
    )
    if interaction_mode == "video":
        avatar = anam.AvatarSession(
            persona_config=anam.PersonaConfig(
                name="Liv",
                avatarId="9483f9bb-e4e2-49d1-936d-85bf2aef9f29",
            ),
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
    cli.run_app(server)
