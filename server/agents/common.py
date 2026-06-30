from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DEFAULT_SCENARIO = "medical-examination"
DEFAULT_LANGUAGE = "English"
DEFAULT_NAME = "Sanjay"
DEFAULT_PERSONA = "9876543210"
PERSONAS = {
    "9876543210": {
        "phone_number": "9876543210",
        "full_name": "Mr. Rohit Sharma",
        "dob": "1992-08-15",
    },
    "9876500001": {
        "phone_number": "9876500001",
        "full_name": "Ms. Priya Nair",
        "dob": "1995-01-20",
    },
    "9876500002": {
        "phone_number": "9876500002",
        "full_name": "Mr. Arjun Mehta",
        "dob": "1990-03-11",
    },
    "9876500003": {
        "phone_number": "9876500003",
        "full_name": "Ms. Sneha Kapoor",
        "dob": "1993-07-24",
    },
    "9876500004": {
        "phone_number": "9876500004",
        "full_name": "Mr. Vikram Singh",
        "dob": "1988-12-02",
    },
    "9876500005": {
        "phone_number": "9876500005",
        "full_name": "Ms. Ananya Reddy",
        "dob": "1996-09-18",
    },
    "9876500006": {
        "phone_number": "9876500006",
        "full_name": "Mr. Karan Malhotra",
        "dob": "1991-05-14",
    },
    "9876500007": {
        "phone_number": "9876500007",
        "full_name": "Ms. Neha Verma",
        "dob": "1994-02-28",
    },
    "9876500008": {
        "phone_number": "9876500008",
        "full_name": "Mr. Rahul Khanna",
        "dob": "1989-11-10",
    },
    "9876500009": {
        "phone_number": "9876500009",
        "full_name": "Ms. Pooja Iyer",
        "dob": "1997-06-06",
    },
    "9876500010": {
        "phone_number": "9876500010",
        "full_name": "Mr. Amit Joshi",
        "dob": "1992-01-17",
    },
    "9876500011": {
        "phone_number": "9876500011",
        "full_name": "Ms. Divya Menon",
        "dob": "1993-10-03",
    },
    "9876500012": {
        "phone_number": "9876500012",
        "full_name": "Mr. Siddharth Rao",
        "dob": "1987-04-22",
    },
    "9876500013": {
        "phone_number": "9876500013",
        "full_name": "Ms. Meera Pillai",
        "dob": "1998-08-09",
    },
    "9876500014": {
        "phone_number": "9876500014",
        "full_name": "Mr. Yash Patel",
        "dob": "1991-12-30",
    },
    "9876500015": {
        "phone_number": "9876500015",
        "full_name": "Ms. Kavya Shetty",
        "dob": "1995-03-26",
    },
    "9876500016": {
        "phone_number": "9876500016",
        "full_name": "Mr. Aditya Kulkarni",
        "dob": "1990-07-01",
    },
    "9876500017": {
        "phone_number": "9876500017",
        "full_name": "Ms. Ritika Bansal",
        "dob": "1994-11-19",
    },
    "9876500018": {
        "phone_number": "9876500018",
        "full_name": "Mr. Nikhil Jain",
        "dob": "1988-02-13",
    },
    "9876500019": {
        "phone_number": "9876500019",
        "full_name": "Ms. Shreya Das",
        "dob": "1996-05-29",
    },
    "9876500020": {
        "phone_number": "9876500020",
        "full_name": "Mr. Manish Tiwari",
        "dob": "1992-09-07",
    },
    "9876500021": {
        "phone_number": "9876500021",
        "full_name": "Ms. Aisha Khan",
        "dob": "1997-01-12",
    },
    "9876500022": {
        "phone_number": "9876500022",
        "full_name": "Mr. Rajat Arora",
        "dob": "1989-06-21",
    },
    "9876500023": {
        "phone_number": "9876500023",
        "full_name": "Ms. Simran Kaur",
        "dob": "1993-04-04",
    },
    "9876500024": {
        "phone_number": "9876500024",
        "full_name": "Mr. Harsh Vardhan",
        "dob": "1991-08-25",
    },
    "9876500025": {
        "phone_number": "9876500025",
        "full_name": "Ms. Ishita Roy",
        "dob": "1995-12-08",
    },
    "9876500026": {
        "phone_number": "9876500026",
        "full_name": "Mr. Deepak Yadav",
        "dob": "1987-10-16",
    },
    "9876500027": {
        "phone_number": "9876500027",
        "full_name": "Ms. Tanvi Mishra",
        "dob": "1998-02-01",
    },
    "9876500028": {
        "phone_number": "9876500028",
        "full_name": "Mr. Akash Choudhary",
        "dob": "1990-11-23",
    },
    "9876500029": {
        "phone_number": "9876500029",
        "full_name": "Ms. Nandini Rao",
        "dob": "1994-06-14",
    },
    "9876500030": {
        "phone_number": "9876500030",
        "full_name": "Mr. Varun Bhatia",
        "dob": "1992-03-05",
    },
    "9876500031": {
        "phone_number": "9876500031",
        "full_name": "Ms. Rhea Thomas",
        "dob": "1996-09-27",
    },
    "9876500032": {
        "phone_number": "9876500032",
        "full_name": "Mr. Abhishek Sinha",
        "dob": "1988-01-31",
    },
    "9876500033": {
        "phone_number": "9876500033",
        "full_name": "Ms. Mitali Ghosh",
        "dob": "1995-07-13",
    },
    "9876500034": {
        "phone_number": "9876500034",
        "full_name": "Mr. Sameer Puri",
        "dob": "1991-04-18",
    },
    "9876500035": {
        "phone_number": "9876500035",
        "full_name": "Ms. Lavanya Krishnan",
        "dob": "1997-11-09",
    },
    "9876500036": {
        "phone_number": "9876500036",
        "full_name": "Mr. Gaurav Saxena",
        "dob": "1989-05-02",
    },
    "9876500037": {
        "phone_number": "9876500037",
        "full_name": "Ms. Bhavna Chopra",
        "dob": "1993-08-20",
    },
    "9876500038": {
        "phone_number": "9876500038",
        "full_name": "Mr. Rohan Desai",
        "dob": "1990-12-11",
    },
    "9876500039": {
        "phone_number": "9876500039",
        "full_name": "Ms. Sanya Mallick",
        "dob": "1996-03-15",
    },
    "9876500040": {
        "phone_number": "9876500040",
        "full_name": "Mr. Tushar Anand",
        "dob": "1992-10-28",
    },
    "9876500041": {
        "phone_number": "9876500041",
        "full_name": "Ms. Keerthi Narayan",
        "dob": "1994-01-07",
    },
    "9876500042": {
        "phone_number": "9876500042",
        "full_name": "Mr. Mohit Sehgal",
        "dob": "1987-06-26",
    },
    "9876500043": {
        "phone_number": "9876500043",
        "full_name": "Ms. Pallavi Sen",
        "dob": "1998-04-12",
    },
    "9876500044": {
        "phone_number": "9876500044",
        "full_name": "Mr. Naveen Kumar",
        "dob": "1991-09-03",
    },
    "9876500045": {
        "phone_number": "9876500045",
        "full_name": "Ms. Anjali Bhat",
        "dob": "1995-02-22",
    },
    "9876500046": {
        "phone_number": "9876500046",
        "full_name": "Mr. Prateek Agarwal",
        "dob": "1989-07-30",
    },
    "9876500047": {
        "phone_number": "9876500047",
        "full_name": "Ms. Shruti Kulshrestha",
        "dob": "1993-11-14",
    },
    "9876500048": {
        "phone_number": "9876500048",
        "full_name": "Mr. Devansh Gupta",
        "dob": "1990-05-19",
    },
    "9876500049": {
        "phone_number": "9876500049",
        "full_name": "Ms. Aarushi Bedi",
        "dob": "1997-08-06",
    },
    "9876500050": {
        "phone_number": "9876500050",
        "full_name": "Mr. Chirag Oberoi",
        "dob": "1992-12-24",
    },
}
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


def resolve_metadata_payload(metadata: str | None) -> tuple[str, str, str, str, dict]:
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

                return interaction_mode, slug, agent_name, language, persona

    for prefix, interaction_mode in (
        ("video-", "video"),
        ("avatar-", "video"),
        ("audio-", "audio"),
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


def extract_scenario_slug(metadata: str | None) -> str:
    _, scenario_slug, _, _, _ = resolve_metadata_payload(metadata)
    return scenario_slug


def resolve_room_metadata(metadata: str | None) -> tuple[str, str, str, str, dict]:
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
