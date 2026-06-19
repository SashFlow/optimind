import logging
import asyncio
import os
from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    AudioConfig,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    JobContext,
    cli,
    room_io,
)
import json
from livekit import api
from livekit.protocol.egress import (
    EncodedFileOutput,
    RoomCompositeEgressRequest,
    EncodedFileType,
    GCPUpload,
)
from livekit.plugins import anam, google, ai_coustics
from livekit.agents.voice import AgentSession, UserStateChangedEvent
from agents.common import resolve_metadata_payload
from agents.tools import end_call
from utils.helper import get_agent
from google.genai.types import FunctionResponseScheduling
import utils.patch as patch  # noqa: F401

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
LANGUAGE_DICT = {
    "English": "en",
    "Hindi": "hi",
    "Marathi": "mr",
    "Bengali": "bn",
}


def load_gcp_credentials_json():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if creds_path and os.path.exists(creds_path):
        with open(creds_path, "r", encoding="utf-8") as f:
            return json.load(f)
    default_creds = "./creds.json"
    if os.path.exists(default_creds):
        with open(default_creds, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@server.rtc_session(agent_name="demo-agent")
async def entrypoint(ctx: JobContext):
    # Connect to Room
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    await ctx.connect()

    lkapi = api.LiveKitAPI()
    egress = lkapi.egress

    # Session Creation
    interaction_mode, slug, selected_agent, language, persona = (
        resolve_metadata_payload(ctx.job.metadata)
    )
    use_avatar = interaction_mode == "video"
    avatar_started = False

    room_options = room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=ai_coustics.audio_enhancement(
                model=ai_coustics.EnhancerModel.QUAIL_VF_S,
            ),
        ),
        close_on_disconnect=True,
        delete_room_on_close=True,
        audio_output=room_io.AudioOutputOptions(),
    )

    agent = AGENT_LIB[selected_agent]
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice=agent["voice"],
            language=LANGUAGE_DICT.get(language, "en"),
            tool_response_scheduling=FunctionResponseScheduling.WHEN_IDLE,
        ),
        tools=[end_call],
        vad=ai_coustics.VAD(),
        preemptive_generation=True,
        user_away_timeout=30,
    )

    @session.on("user_state_changed")
    def _on_user_state_changed(ev: UserStateChangedEvent):
        if ev.new_state == "away":
            session.generate_reply(
                instructions="It seems you are away. I'll end the call now. Goodbye!"
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
            room_options.audio_output = True

    await session.start(
        agent=get_agent(slug, selected_agent, agent, language, persona),
        room=ctx.room,
        room_options=room_options,
    )

    # Egress Init
    await egress.start_room_composite_egress(
        start=RoomCompositeEgressRequest(
            room_name=ctx.room.name,
            audio_only=False,
            layout="grid",
            preset=api.EncodingOptionsPreset.H264_720P_30,
            file=EncodedFileOutput(
                file_type=EncodedFileType.MP4,
                filepath=f"{ctx.room.name}/recording-session.mp4",
                gcp=GCPUpload(
                    bucket=os.getenv("GCP_BUCKET_NAME", "").strip(),
                    credentials=load_gcp_credentials_json(),
                ),
            ),
        )
    )
    background_audio = BackgroundAudioPlayer(
        # play office ambience sound looping in the background
        ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.8),
        # play keyboard typing sound when the agent is thinking
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
        ],
    )

    await background_audio.start(room=ctx.room, agent_session=session)


if __name__ == "__main__":
    cli.run_app(server)
