import logging
import asyncio
import json

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
from agents.tools import end_call

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

server = AgentServer()


agents = {
    'sai': {
        'gender': 'male',
        'voice': 'Charon',
        'avatar': '9483f9bb-e4e2-49d1-936d-85bf2aef9f29',
    },
    'sonia': {
        'gender': 'female',
        'voice': 'Leda',
        'avatar': '9483f9bb-e4e2-49d1-936d-85bf2aef9f29',
    },
    'sagar': {
        'gender': 'male',
        'voice': 'Puck',
        'avatar': '9483f9bb-e4e2-49d1-936d-85bf2aef9f29',
    }
}

DEFAULT_AGENT_NAME = "sai"


def _parse_metadata(metadata: str | None) -> dict:
    raw_metadata = (metadata or "").strip()
    if not raw_metadata.startswith("{"):
        return {}

    try:
        payload = json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}

    return payload if isinstance(payload, dict) else {}


def _resolve_agent_name(metadata: str | None) -> str:
    payload = _parse_metadata(metadata)
    candidate = str(payload.get("agentName") or "").strip().lower()
    if candidate in agents:
        return candidate
    return DEFAULT_AGENT_NAME


def _resolve_agent_init_metadata(metadata: str | None) -> str | None:
    payload = _parse_metadata(metadata)
    conversation_agent = str(
        payload.get("conversationAgent") or payload.get(
            "conversationAgentName") or ""
    ).strip()
    return conversation_agent or metadata


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="demo-agent")
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    interaction_mode, _ = resolveRoomMetadata(ctx.job.metadata)
    selected_agent_name = _resolve_agent_name(ctx.job.metadata)
    selected_agent = agents[selected_agent_name]
    agent_init_metadata = _resolve_agent_init_metadata(ctx.job.metadata)
    userdata = getUserData(ctx.job.metadata, ctx)

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-live-2.5-flash-native-audio",
            vertexai=True,
            voice=selected_agent["voice"],
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
                    name=selected_agent_name.title(),
                    avatarId=selected_agent["avatar"],
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
        agent=getAgent(agent_init_metadata),
        room=ctx.room,
        room_options=room_options,
    )
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
