from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DEFAULT_SCENARIO = "front-desk-agent"
CURRENT_DATE = datetime.now(tz=timezone.utc).date().isoformat()
INTERACTION_MODES = {"audio", "video"}
INTERACTION_MODE_BY_SCENARIO_TYPE = {
    "audio": "audio",
    "avatar": "video",
    "calls": "audio",
    "video": "video",
}


@dataclass(frozen=True)
class WidgetField:
    label: str
    value: str


@dataclass(frozen=True)
class WidgetPayload:
    id: str
    type: str
    title: str
    status: str = "info"
    description: str = ""
    data: tuple[WidgetField, ...] = ()
    highlights: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "description": self.description,
            "data": [
                {"label": field.label, "value": field.value} for field in self.data
            ],
            "highlights": list(self.highlights),
        }


@dataclass(frozen=True)
class ScenarioDefinition:
    slug: str
    title: str
    summary: str
    domain_focus: str
    greeting: str
    highlights: tuple[str, ...]
    live_data_points: tuple[str, ...]


SCENARIOS: dict[str, ScenarioDefinition] = {
    "medical-officer": ScenarioDefinition(
        slug="medical-officer",
        title="Medical Consultation Assistant",
        summary="Supports broad medical consultations with symptom intake, triage guidance, care-navigation questions, and safe escalation.",
        domain_focus="General medical consultation support, symptom triage, cautious diagnostic guidance, and safe escalation for urgent symptoms.",
        greeting="Open with one calm, human line as the medical consultation assistant, then invite questions about symptoms, urgency, or next-step care.",
        highlights=(
            "Structured symptom intake and triage",
            "Care-setting guidance across common complaints",
            "Cautious visual observations during live sessions",
        ),
        live_data_points=(
            "symptom intake summaries",
            "triage guidance",
            "visual-observation guidance",
        ),
    ),
    "front-desk-agent": ScenarioDefinition(
        slug="front-desk-agent",
        title="Front Desk Agent",
        summary="Handles visitor arrivals, appointment bookings, office information, and reception workflows.",
        domain_focus="Greeting visitors, confirming bookings, answering office logistics, and routing requests clearly.",
        greeting="Open with one warm, polished line as the front desk, then invite questions about visitors, bookings, or office details.",
        highlights=(
            "Visitor and meeting lookups",
            "Open booking slots",
            "Office hours, parking, and contact details",
        ),
        live_data_points=(
            "visitor lookups",
            "booking slots",
            "office information",
        ),
    ),
    "resturant-agent": ScenarioDefinition(
        slug="resturant-agent",
        title="Resturant Agent",
        summary="Supports reservations, menu questions, dietary guidance, and order status updates for guests.",
        domain_focus="Reservations, menu assistance, order support, and courteous restaurant service conversations.",
        greeting="Open with one warm host-style line, then invite the guest to ask about reservations, menu choices, or order updates.",
        highlights=(
            "Reservations and table timing",
            "Menu recommendations and dietary notes",
            "Takeaway and delivery order status",
        ),
        live_data_points=(
            "reservation details",
            "menu items",
            "order status",
        ),
    ),
    "study-partner": ScenarioDefinition(
        slug="study-partner",
        title="Study Partner",
        summary="Provides study plans, flashcards, and practice questions with a coaching-oriented teaching style.",
        domain_focus="Study planning, revision support, quick explanations, and practice coaching.",
        greeting="Open with one upbeat, human line as a study coach, then invite the learner to pick a topic, plan, or quiz.",
        highlights=(
            "Study plans by subject",
            "Flashcard review sets",
            "Practice quiz prompts and coaching notes",
        ),
        live_data_points=(
            "study plans",
            "flashcards",
            "practice quizzes",
        ),
    ),
    "help-desk-partner": ScenarioDefinition(
        slug="help-desk-partner",
        title="Help Desk Partner",
        summary="Helps with ticket status, troubleshooting guides, and device/account support data.",
        domain_focus="First-line troubleshooting, support ticket updates, and practical escalation guidance.",
        greeting="Open with one calm support-desk line, then invite questions about tickets, troubleshooting, or device status.",
        highlights=(
            "Ticket ownership and ETA",
            "Troubleshooting playbooks",
            "Device and account health status",
        ),
        live_data_points=(
            "ticket status",
            "troubleshooting guides",
            "device status",
        ),
    ),
}


def normalize_lookup_key(value: str) -> str:
    return value.casefold().strip()


def stringify_value(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)
    return str(value)


def rows_from_mapping(mapping: Mapping[str, Any]) -> tuple[WidgetField, ...]:
    return tuple(
        WidgetField(label=label, value=stringify_value(value))
        for label, value in mapping.items()
    )


def resolve_metadata_payload(metadata: str | None) -> tuple[str, str]:
    raw_metadata = (metadata or "").strip()
    if not raw_metadata:
        return "audio", DEFAULT_SCENARIO

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

                return interaction_mode, slug

    for prefix, interaction_mode in (
        ("video-", "video"),
        ("avatar-", "video"),
        ("audio-", "audio"),
        ("calls-", "audio"),
    ):
        if raw_metadata.startswith(prefix):
            slug = raw_metadata[len(prefix) :].strip()
            return interaction_mode, slug or DEFAULT_SCENARIO

    return "audio", raw_metadata


def extract_scenario_slug(metadata: str | None) -> str:
    _, scenario_slug = resolve_metadata_payload(metadata)
    return scenario_slug


def resolve_room_metadata(metadata: str | None) -> tuple[str, str]:
    return resolve_metadata_payload(metadata)


def build_agent_instructions(
    scenario: ScenarioDefinition, operating_notes: Sequence[str]
) -> str:
    live_data_bullets = "\n".join(f"- {item}" for item in scenario.live_data_points)
    rule_bullets = "\n".join(f"- {note}" for note in operating_notes)

    return f"""
You are {scenario.title}, a real-time voice assistant for {scenario.domain_focus}
- Current date is {CURRENT_DATE}.
- You have access to the internet and search for any relavent information to answer user questions.
- Always answer with an indian accent and in a warm, human tone. Be specific and concise in your responses.


Speak like a helpful human on a call:
- Lead with the answer.
- Usually use 1 short sentence; use 2 only when it helps.
- Sound warm, natural, and specific.
- Do not repeat the user's words, use bullet points, or mention tools unless the user asks.
- Ask at most 1 brief follow-up when a missing detail blocks the answer.

Tool use:
- Answer directly when the user does not need live data.
- Use the single best tool for live records or status checks.
- Only use multiple tools if the user clearly asked for multiple things.
- Never invent tool-backed facts.
- After a tool call, give only the key result and the next useful detail.

Safety:
- Escalate urgent medical, physical safety, or account-security situations to a human immediately.

Live data you can fetch:
{live_data_bullets}

Domain rules:
{rule_bullets}
""".strip()
