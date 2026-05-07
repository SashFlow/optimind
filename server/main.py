import logging
import asyncio
import os
import time

from dotenv import load_dotenv
from livekit.agents import (
    NOT_GIVEN,
    AgentFalseInterruptionEvent,
    AgentServer,
    JobContext,
    cli,
    room_io,
)
from livekit import api
from livekit.protocol.egress import (
    EncodedFileOutput,
    RoomCompositeEgressRequest,
    EncodedFileType,
    S3Upload,
    StopEgressRequest,
)
from livekit.agents.voice import AgentSession, AgentStateChangedEvent
from livekit.plugins import anam, google, ai_coustics
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from agents.common import resolve_metadata_payload
from agents.medical_examinar import MedicalExaminationAgent
from agents.tools import end_call

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

# TODO: move to redis later if we want to persist across server restarts or have multiple server instances
EGRESS_IDS = {}


def set_egress_id(room_name: str, egress_id: str) -> None:
    EGRESS_IDS[room_name] = egress_id


def get_egress_id(room_name: str) -> str | None:
    id = EGRESS_IDS.get(room_name)
    del EGRESS_IDS[room_name]
    return id


@server.rtc_session(agent_name="demo-agent")
async def entrypoint(ctx: JobContext):
    lkapi = api.LiveKitAPI()
    egress = lkapi.egress
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    interaction_mode, _, selected_agent, language = resolve_metadata_payload(
        ctx.job.metadata
    )
    agent = AGENT_LIB[selected_agent]
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-live-2.5-flash-native-audio",
            vertexai=True,
            voice=agent["voice"],
        ),
        tools=[google.tools.GoogleSearch(), end_call],
        turn_detection=MultilingualModel(),
        vad=ai_coustics.VAD(),
        preemptive_generation=True,
    )

    false_interruption_task: asyncio.Task[None] | None = None

    async def _check_for_false_interruption() -> None:
        try:
            await asyncio.sleep(20)
            if session.agent_state != "listening":
                return

            logger.info(
                "agent still listening after speaking; prompting for clarification"
            )
            session.generate_reply(instructions=("Can you repeat the question."))
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

    @session.on("close")
    def _on_close():
        async def cleanup():
            await egress.stop_egress(
                stop=StopEgressRequest(egress_id=get_egress_id(ctx.room.name))
            )

        asyncio.create_task(cleanup())

    use_avatar = interaction_mode == "video"
    avatar_started = False

    room_options = room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=ai_coustics.audio_enhancement(
                model=ai_coustics.EnhancerModel.QUAIL_VF_L
            ),
        ),
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
        agent=MedicalExaminationAgent(selected_agent, agent["gender"], language),
        room=ctx.room,
        room_options=room_options,
    )

    response = await egress.start_room_composite_egress(
        start=RoomCompositeEgressRequest(
            room_name=ctx.room.name,
            audio_only=False,
            layout="grid",
            preset=api.EncodingOptionsPreset.H264_720P_30,
            file=EncodedFileOutput(
                file_type=EncodedFileType.MP4,
                filepath=f"{ctx.room.name}/recording-{int(time.time())}.mp4",
                s3=S3Upload(
                    access_key=os.getenv("S3_ACCESS_KEY", ""),
                    secret=os.getenv("S3_SECRET_KEY", ""),
                    bucket=os.getenv("S3_BUCKET", ""),
                    region=os.getenv("S3_REGION", ""),
                    endpoint=os.getenv("S3_ENDPOINT", ""),
                    force_path_style=True,
                ),
            ),
        )
    )
    set_egress_id(ctx.room.name, response.egress_id)
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
