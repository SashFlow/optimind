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
from livekit.agents.voice import AgentSession, AgentStateChangedEvent
from livekit.plugins import anam, google, noise_cancellation, silero
from agents import getUserData
from agents.common import resolve_metadata_payload
from agents.medical_examinar import MedicalExaminationAgent

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

server = AgentServer()

AGENT_LIB = {
    "Sanjay": {
        "gender": "male",
        "avatar": "5f46f99e-c4be-4f22-bde2-b364975a0851",
        "voice": "Charon",
    },
    "Samira": {
        "gender": "female",
        "avatar": "d3e94c42-b348-4bec-8225-e47a682128a0",
        "voice": "Leda",
    },
}


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="demo-agent")
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    interaction_mode, _, selected_agent, language = resolve_metadata_payload(
        ctx.job.metadata
    )
    userdata = getUserData(ctx.job.metadata, ctx)
    agent = AGENT_LIB[selected_agent]
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-live-2.5-flash-native-audio",
            vertexai=True,
            voice=agent["voice"],
        ),
        tools=[google.tools.GoogleSearch()],
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        userdata=userdata,
    )

    false_interruption_task: asyncio.Task[None] | None = None

    async def _check_for_false_interruption() -> None:
        try:
            await asyncio.sleep(10)
            if session.agent_state != "listening":
                return

            logger.info(
                "agent still listening after speaking; prompting for clarification"
            )
            session.generate_reply(
                instructions=(
                    "Looks like I may have been interrupted by mistake. "
                    "Ask the user briefly if they want clarification or to continue."
                )
            )
        except asyncio.CancelledError:
            # State changed before timeout, so this check is no longer needed.
            return
        except Exception:
            logger.exception("failed to run false interruption check")

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: AgentStateChangedEvent):
        nonlocal false_interruption_task

        if false_interruption_task and not false_interruption_task.done():
            false_interruption_task.cancel()
            false_interruption_task = None

        if ev.new_state == "listening" and ev.old_state == "speaking":
            # If we remain in listening unexpectedly, nudge the user for clarification.
            false_interruption_task = asyncio.create_task(
                _check_for_false_interruption()
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
                    name=selected_agent,
                    avatarId=agent["avatar"],
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
        agent=MedicalExaminationAgent(selected_agent, agent["gender"], "Hindi"),
        room=ctx.room,
        room_options=room_options,
    )
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
