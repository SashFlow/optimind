from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

DEFAULT_SCENARIO = "front-desk-agent"


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
        title="Medical Officer",
        summary="Supports patient intake, appointment coordination, prescription review, and basic clinic workflow questions.",
        domain_focus="Patient intake support, scheduling, routine care coordination, and safe escalation for urgent symptoms.",
        greeting="Welcome the caller as the medical officer and offer help with appointments, patient information, and follow-up questions.",
        highlights=(
            "Patient profiles and allergies",
            "Upcoming appointments and check-in details",
            "Prescription summaries and follow-up notes",
        ),
        live_data_points=(
            "patient profiles",
            "appointment schedules",
            "prescription summaries",
        ),
    ),
    "front-desk-agent": ScenarioDefinition(
        slug="front-desk-agent",
        title="Front Desk Agent",
        summary="Handles visitor arrivals, appointment bookings, office information, and reception workflows.",
        domain_focus="Greeting visitors, confirming bookings, answering office logistics, and routing requests clearly.",
        greeting="Greet the caller as the front desk agent and offer help with bookings, visitor details, or office information.",
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
        greeting="Welcome the guest as the restaurant agent and offer help with reservations, menu questions, or order updates.",
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
        greeting="Introduce yourself as the study partner and offer to review plans, flashcards, or practice questions.",
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
        greeting="Introduce yourself as the help desk partner and offer help with tickets, troubleshooting steps, or device status.",
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


def extract_scenario_slug(metadata: str | None) -> str:
    raw_metadata = (metadata or "").strip()
    if not raw_metadata:
        return DEFAULT_SCENARIO

    for prefix in ("audio-", "video-"):
        if raw_metadata.startswith(prefix):
            return raw_metadata[len(prefix) :]

    return raw_metadata


def resolve_room_metadata(metadata: str | None) -> tuple[str, str]:
    raw_metadata = (metadata or "").strip()
    if raw_metadata.startswith("video-"):
        return "video", raw_metadata[len("video-") :]
    if raw_metadata.startswith("audio-"):
        return "audio", raw_metadata[len("audio-") :]
    return "audio", raw_metadata or DEFAULT_SCENARIO


def build_agent_instructions(
    scenario: ScenarioDefinition, operating_notes: Sequence[str]
) -> str:
    live_data_bullets = "\n".join(
        f"- {item}" for item in scenario.live_data_points
    )
    rule_bullets = "\n".join(f"- {note}" for note in operating_notes)

    return f"""
You are {scenario.title}, a voice-first AI assistant.
The user is interacting through voice, so respond with short, natural spoken sentences.
Stay focused on {scenario.domain_focus}
Use the available tools whenever the user asks for live operational data, records, schedules, menus, tickets, reservations, or study materials.
Never invent live data when a tool exists for it.
After using a tool, summarize the answer clearly and mention only the most relevant details.
Escalate urgent medical, safety, or account-security situations to a human immediately.

Live data you can fetch:
{live_data_bullets}

Operating rules:
{rule_bullets}
""".strip()
