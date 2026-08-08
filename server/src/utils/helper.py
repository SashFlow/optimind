"""Helper functions for the agent."""

import asyncio
from asyncio.log import logger
import json
from collections.abc import Mapping
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


def resolve_metadata_payload(
    metadata: str | None,
) -> tuple[str, str, str, str, dict]:
    """Resolve the metadata payload."""
    raw_metadata = (metadata or "").strip()
    if not raw_metadata:
        return "audio", DEFAULT_SCENARIO, DEFAULT_NAME, DEFAULT_LANGUAGE, {}

    if raw_metadata.startswith("{"):
        try:
            payload = json.loads(raw_metadata)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(payload, Mapping):
                slug = (
                    str(
                        payload.get("scenarioSlug")
                        or payload.get("slug")
                        or DEFAULT_SCENARIO
                    ).strip()
                    or DEFAULT_SCENARIO
                )

                interaction_mode_value = payload.get("interactionMode")
                if (
                    interaction_mode_value is None
                    and payload.get("scenarioType") is not None
                ):
                    interaction_mode_value = INTERACTION_MODE_BY_SCENARIO_TYPE.get(
                        normalize_lookup_key(str(payload["scenarioType"])),
                        "audio",
                    )

                interaction_mode = normalize_lookup_key(
                    str(interaction_mode_value or "audio")
                )
                if interaction_mode not in INTERACTION_MODES:
                    interaction_mode = "audio"
                agent_name = payload.get("selectedAgent", DEFAULT_NAME)
                language = payload.get("language", DEFAULT_LANGUAGE)

                persona = (
                    PERSONAS[payload.get("persona", DEFAULT_PERSONA)]
                    if payload.get("persona") in PERSONAS
                    else {}
                )

                return (
                    interaction_mode,
                    slug,
                    agent_name,
                    language,
                    persona,
                )

    for prefix, interaction_mode in (
        ("video-", "video"),
        ("avatar-", "video"),
        ("audio-", "audio"),
        ("phone-", "audio"),
        ("calls-", "audio"),
    ):
        if raw_metadata.startswith(prefix):
            slug = raw_metadata[len(prefix) :].strip()
            return (
                interaction_mode,
                slug or DEFAULT_SCENARIO,
                DEFAULT_NAME,
                DEFAULT_LANGUAGE,
                {},
            )

    return "audio", raw_metadata, DEFAULT_NAME, DEFAULT_LANGUAGE, {}


def extract_dial_phone_number(metadata: str | None) -> str | None:
    """Return the PSTN number to dial from job metadata, if present."""
    raw_metadata = (metadata or "").strip()
    if not raw_metadata.startswith("{"):
        return None
    try:
        payload = json.loads(raw_metadata)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    phone = payload.get("phone_number") or payload.get("phoneNumber")
    if phone is None:
        return None
    phone_str = str(phone).strip()
    return phone_str or None
