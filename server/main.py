import logging
import asyncio

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

from agents import getUserData
from agents.common import resolve_metadata_payload
from agents.tools import end_call
from agents.medical_examinar import MedicalExaminationAgent

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

server = AgentServer()

AGENT_LIB = {
    'Sanjay': {
        'gender': 'male',
        'avatar': '5f46f99e-c4be-4f22-bde2-b364975a0851'
    },
    'Samira': {
        'gender': 'female',
        'avatar': '48bda6b9-a35c-43df-83a0-0264361677db'
    }
}


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="demo-agent-4")
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    interaction_mode, _, selected_agent, language = resolve_metadata_payload(
        ctx.job.metadata)
    userdata = getUserData(ctx.job.metadata, ctx)
    agent = AGENT_LIB[selected_agent]
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            vertexai=True,
            voice="Charon",
        ),
        tools=[google.tools.GoogleSearch(), end_call],
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        userdata=userdata,
    )

    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev: AgentFalseInterruptionEvent):
        logger.info("false positive interruption, resuming")
        session.generate_reply(instructions=ev.extra_instructions or NOT_GIVEN)

    use_avatar = interaction_mode == "video"
    avatar_started = False

    room_options = room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
            if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
            else noise_cancellation.BVC(),
        ),
        # In avatar mode, audio is published by the avatar worker.
        audio_output=not use_avatar,
    )

    if use_avatar:
        participant = None
        if ctx.room.remote_participants:
            participant = next(iter(ctx.room.remote_participants.values()))
        else:
            try:
                participant = await asyncio.wait_for(
                    ctx.wait_for_participant(), timeout=10
                )
            except TimeoutError:
                logger.warning(
                    "video mode requested but no participant joined in time; avatar disabled"
                )

        if participant is not None:
            avatar = anam.AvatarSession(
                persona_config=anam.PersonaConfig(
                    name="Liv",
                    avatarId="9483f9bb-e4e2-49d1-936d-85bf2aef9f29",
                ),
            )
            try:
                # Start avatar first so it can receive/relay agent output immediately.
                await avatar.start(session, room=ctx.room)
                avatar_started = True
            except Exception:
                logger.exception(
                    "avatar startup failed; falling back to voice-only output"
                )

        if not avatar_started:
            # Keep the user experience alive even when avatar startup fails.
            room_options.audio_output = True

    await session.start(
        agent=MedicalExaminationAgent(
            selected_agent, agent['gender'], language),
        room=ctx.room,
        room_options=room_options,
    )
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
