"""Helper functions for the agent."""

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Literal
from livekit.agents import AgentSession

from constants import (
    SupportState,
    EMOTION_PROFILES,
    MALE_SPEAKER,
    FEMALE_SPEAKER,
    SarvamLanguage,
    TTS_LANGUAGES,
    DEFAULT_SCENARIO,
    DEFAULT_NAME,
    DEFAULT_LANGUAGE,
    DEFAULT_PERSONA,
    INTERACTION_MODE_BY_SCENARIO_TYPE,
    INTERACTION_MODES,
    PERSONAS,
)
import os
from livekit.protocol.egress import (
    S3Upload,
)
from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest
from livekit.agents import JobContext

logger = logging.getLogger(__name__)


def normalize_lookup_key(value: str) -> str:
    return value.casefold().strip()


async def check_for_false_interruption(session: AgentSession) -> None:
    """Check for false interruption by the user."""
    try:
        await asyncio.sleep(20)
        if session.agent_state != "listening":
            return

        logger.info("agent still listening after speaking; prompting for clarification")
        session.generate_reply(
            instructions=(
                "ask the user if they have any other questions or need further assistance"
            )
        )
    except asyncio.CancelledError:
        # State changed before timeout, so this check is no longer needed.
        return
    except Exception:
        logger.exception("failed to run false interruption check")


def normalize_tts_language(language: str | None) -> SarvamLanguage | None:
    """Normalize the language code to a Sarvam language code."""
    if not language:
        return None
    code = language.strip()
    if code in TTS_LANGUAGES:
        return code  # type: ignore[return-value]
    # e.g. "hi" / "en" → hi-IN / en-IN
    short = code.split("-", 1)[0].lower()
    mapped = {
        "bn": "bn-IN",
        "en": "en-IN",
        "gu": "gu-IN",
        "hi": "hi-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        "mr": "mr-IN",
        "or": "od-IN",
        "od": "od-IN",
        "pa": "pa-IN",
        "ta": "ta-IN",
        "te": "te-IN",
    }.get(short)
    return mapped  # type: ignore[return-value]


def apply_tts_presence(
    session: AgentSession[SupportState], state: SupportState
) -> None:
    """Update Sarvam TTS options only — no instruction rewrite (keeps replies fast)."""
    profile = EMOTION_PROFILES[state.emotion]
    speaker = MALE_SPEAKER if state.voice == "male" else FEMALE_SPEAKER
    tts = session.tts
    if tts is not None and hasattr(tts, "update_options"):
        tts.update_options(
            target_language_code=state.language,
            speaker=speaker,
            pace=float(profile["pace"]),
            temperature=float(profile["temperature"]),
        )


_PREFIX_MODES = (
    ("video-", "video"),
    ("avatar-", "video"),
    ("audio-", "audio"),
    ("phone-", "audio"),
    ("calls-", "audio"),
)

MetadataFields = tuple[str, str, str, str, dict, str | None]


def _session_fields(
    mode: str = "audio",
    slug: str = DEFAULT_SCENARIO,
    agent: str  = DEFAULT_NAME,
    language: str = DEFAULT_LANGUAGE,
    persona: dict | None = None,
    phone: str | None = None,
) -> MetadataFields:
    if persona is None:
        persona = PERSONAS[DEFAULT_PERSONA]
    return mode, slug, agent, language, persona, phone


def _resolve_interaction_mode(payload: Mapping) -> str:
    interaction_mode_value = payload.get("interactionMode")
    if interaction_mode_value is None and payload.get("scenarioType") is not None:
        interaction_mode_value = INTERACTION_MODE_BY_SCENARIO_TYPE.get(
            normalize_lookup_key(str(payload["scenarioType"])),
            "audio",
        )

    interaction_mode = normalize_lookup_key(str(interaction_mode_value or "audio"))
    if interaction_mode not in INTERACTION_MODES:
        return "audio"
    return interaction_mode


def _from_json_payload(payload: Mapping) -> MetadataFields:
    slug = (
        str(
            payload.get("scenarioSlug")
            or payload.get("slug")
            or DEFAULT_SCENARIO
        ).strip()
        or DEFAULT_SCENARIO
    )

    persona_key = payload.get("persona")
    persona = PERSONAS[persona_key] if persona_key in PERSONAS else {}

    phone = payload.get("phone_number") or payload.get("phoneNumber")
    phone_number = str(phone).strip() if phone is not None else None
    if not phone_number:
        phone_number = None

    return _session_fields(
        mode=_resolve_interaction_mode(payload),
        slug=slug,
        agent=payload.get("selectedAgent", DEFAULT_NAME),
        language=payload.get("language", DEFAULT_LANGUAGE),
        persona=persona,
        phone=phone_number,
    )


def resolve_metadata_payload(metadata: str | None) -> MetadataFields:
    """Resolve job metadata into session fields and an optional dial number."""
    raw = (metadata or "").strip()
    if not raw:
        return _session_fields()

    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, Mapping):
            return _from_json_payload(payload)

    for prefix, mode in _PREFIX_MODES:
        if raw.startswith(prefix):
            return _session_fields(
                mode=mode,
                slug=raw[len(prefix) :].strip() or DEFAULT_SCENARIO,
            )

    return _session_fields(slug=raw, persona={})


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
