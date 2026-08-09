"""Main module for the support agent."""

import logging
import asyncio
import os
from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    AudioConfig,
    BackgroundAudioPlayer,
    TurnHandlingOptions,
    BuiltinAudioClip,
    JobContext,
    cli,
    inference,
    room_io,
)
from livekit import api
from livekit.protocol.egress import (
    EncodedFileOutput,
    RoomCompositeEgressRequest,
    EncodedFileType,
    S3Upload,
)
from livekit.protocol.sip import CreateSIPParticipantRequest
from livekit.protocol.egress import EncodingOptionsPreset
from livekit.plugins import anam, ai_coustics, sarvam
from livekit.agents.voice import (
    AgentSession,
    UserStateChangedEvent,
    UserInputTranscribedEvent,
)
from utils.tools import transfer_to_human
from utils.backchannel import ListeningBackchannel
from utils.helper import (
    extract_dial_phone_number,
    normalize_tts_language,
    resolve_metadata_payload,
    apply_tts_presence,
)
from constants import (
    DEFAULT_NAME,
    EMOTION_PROFILES,
    FEMALE_SPEAKER,
    MALE_SPEAKER,
    SarvamLanguage,
    SupportState,
)
from agents import get_agent

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

server = AgentServer()

AGENT_LIB = {
    "Sanjay": {
        "gender": "male",
        "avatar": "5f46f99e-c4be-4f22-bde2-b364975a0851",
    },
    "Samira": {
        "gender": "female",
        "avatar": "d3e94c42-b348-4bec-8225-e47a682128a0",
    },
}

# Display names from job metadata → Sarvam BCP-47 India locales.
SARVAM_LANGUAGE_CODES = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Marathi": "mr-IN",
    "Bengali": "bn-IN",
}


def resolve_session_language(language: str | None) -> SarvamLanguage:
    """Map metadata language labels/codes to a Sarvam TTS locale."""
    raw = (language or "").strip()
    if not raw:
        return "en-IN"
    if raw in SARVAM_LANGUAGE_CODES:
        return SARVAM_LANGUAGE_CODES[raw]  # type: ignore[return-value]
    normalized = normalize_tts_language(raw)
    if normalized is not None:
        return normalized
    # Case-insensitive display-name lookup (e.g. "hindi").
    for label, code in SARVAM_LANGUAGE_CODES.items():
        if label.casefold() == raw.casefold():
            return code  # type: ignore[return-value]
    logger.warning("unrecognized language %r; defaulting to en-IN", raw)
    return "en-IN"


def build_s3_upload() -> S3Upload:
    """Build the S3 upload object."""
    endpoint = os.getenv("AWS_S3_ENDPOINT", "").strip()
    return S3Upload(
        access_key=os.getenv("AWS_ACCESS_KEY_ID", "").strip(),
        secret=os.getenv("AWS_SECRET_ACCESS_KEY", "").strip(),
        session_token=os.getenv("AWS_SESSION_TOKEN", "").strip(),
        region=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "")).strip(),
        bucket=os.getenv("S3_BUCKET_NAME", "").strip(),
        endpoint=endpoint,
        force_path_style=bool(endpoint),
    )


async def dial_outbound_sip(ctx: JobContext, phone_number: str) -> bool:
    """Place an outbound PSTN call via the configured LiveKit/Plivo trunk.

    Returns True if the callee answered and joined the room.
    """
    trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID", "").strip()
    if not trunk_id:
        logger.error("SIP_OUTBOUND_TRUNK_ID is not set; cannot place outbound call")
        ctx.shutdown()
        return False

    try:
        await ctx.api.sip.create_sip_participant(
            CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=trunk_id,
                sip_call_to=phone_number,
                participant_identity=phone_number,
                wait_until_answered=True,
                play_dialtone=False,
            )
        )
        logger.info("outbound call answered: %s", phone_number)
    except api.SipCallError as e:
        logger.error(
            "outbound call failed: %s %s",
            e.sip_status_code,
            e.sip_status,
        )
        ctx.shutdown()
        return False
    except Exception:
        logger.exception("outbound call failed unexpectedly")
        ctx.shutdown()
        return False

    await ctx.wait_for_participant(identity=phone_number)
    return True


@server.rtc_session(agent_name=os.getenv("AGENT_NAME", "demo-agent"))
async def entrypoint(ctx: JobContext):
    """Entrypoint for the support agent."""
    # Connect to Room
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    await ctx.connect()

    phone_number = extract_dial_phone_number(ctx.job.metadata)
    if phone_number is not None:
        answered = await dial_outbound_sip(ctx, phone_number)
        if not answered:
            return

    lkapi = api.LiveKitAPI()
    egress = lkapi.egress

    # Session Creation
    interaction_mode, slug, selected_agent, language, persona = (
        resolve_metadata_payload(ctx.job.metadata)
    )
    # PSTN calls are always audio-only (no avatar).
    use_avatar = interaction_mode == "video" and phone_number is None
    avatar_started = False
    is_phone_call = phone_number is not None

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

    if selected_agent not in AGENT_LIB:
        logger.warning(
            "unknown selectedAgent %r; falling back to %s",
            selected_agent,
            DEFAULT_NAME,
        )
        selected_agent = DEFAULT_NAME
    agent = AGENT_LIB[selected_agent]
    voice = agent["gender"]
    speaker = MALE_SPEAKER if voice == "male" else FEMALE_SPEAKER

    state = SupportState(
        language=resolve_session_language(language),
        voice=voice,
    )

    session = AgentSession[SupportState](
        userdata=state,
        stt=sarvam.STT(
            model="saaras:v3",
            language="unknown",
            mode="codemix",
            sample_rate=16000,
            high_vad_sensitivity=True,
            flush_signal=True,
        ),
        tts=sarvam.TTS(
            model="bulbul:v3",
            speaker=speaker,
            target_language_code=state.language,
            pace=float(EMOTION_PROFILES["warm"]["pace"]),
            temperature=float(EMOTION_PROFILES["warm"]["temperature"]),
            # Match console/test tuning — 8 kHz reads warmer on Sarvam bulbul:v3
            # than 16 kHz web output (less stiff / metallic).
            speech_sample_rate=8000,
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            endpointing={"mode": "dynamic", "min_delay": 0.2, "max_delay": 2.2},
            preemptive_generation={"enabled": True, "preemptive_tts": True},
        ),
        tools=[transfer_to_human],
    )

    @session.on("user_state_changed")
    def _on_user_state_changed(ev: UserStateChangedEvent):
        if ev.new_state == "away":
            session.generate_reply(
                instructions="It seems you are away. I'll end the call now. Goodbye!"
            )

    @session.on("user_input_transcribed")
    def _sync_language(ev: UserInputTranscribedEvent) -> None:
        if not ev.is_final or not ev.language:
            return
        state.last_heard_language = str(ev.language)
        language = normalize_tts_language(ev.language)
        # Apply as soon as STT detects language so preemptive TTS uses the right code.
        if language is not None and language != state.language:
            state.language = language
            apply_tts_presence(session, state)
            logger.info("auto language=%s", language)

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
        agent=get_agent(slug, state, persona),
        room=ctx.room,
        room_options=room_options,
    )
    # Soft continuers while the user pauses mid-turn (cloud hook + pause fallback).
    ListeningBackchannel(session).attach()

    # Egress Init
    # await egress.start_room_composite_egress(
    #     start=RoomCompositeEgressRequest(
    #         room_name=ctx.room.name,
    #         audio_only=is_phone_call,
    #         layout="grid",
    #         preset=EncodingOptionsPreset.H264_720P_30,
    #         file=EncodedFileOutput(
    #             file_type=EncodedFileType.MP4,
    #             filepath=f"{ctx.room.name}/recording-session.mp4",
    #             s3=build_s3_upload(),
    #         ),
    #     )
    # )
    background_audio = BackgroundAudioPlayer(
        # play keyboard typing sound when the agent is thinking
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
        ],
    )

    await background_audio.start(room=ctx.room, agent_session=session)


if __name__ == "__main__":
    cli.run_app(server)
