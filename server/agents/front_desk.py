from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_VISITOR = "Aarav Mehta"
DEFAULT_TOPIC = "general"

VISITORS = {
    "aarav mehta": {
        "name": "Aarav Mehta",
        "host": "Operations Team",
        "meeting_room": "Harbor 2",
        "arrival_time": "11:15 AM",
        "status": "Checked in",
        "badge": "V-218",
    }
}

BOOKING_SLOTS = {
    "today": {
        "next_open_slot": "2:30 PM",
        "secondary_slot": "4:00 PM",
        "desk": "Reception Desk B",
        "notes": "Priority booking window reserved for walk-ins after 5 PM",
    }
}

OFFICE_INFO = {
    "general": {
        "hours": "Mon-Fri, 8:30 AM to 6:00 PM",
        "parking": "Visitor parking in Basement B2",
        "contact": "+91-80-4411-2200",
        "policy": "Photo ID is required for all external visitors",
    },
    "parking": {
        "parking": "Visitor parking in Basement B2",
        "entry": "Use Gate 3 and collect a temporary pass at reception",
        "validation": "Parking is validated for meetings over 60 minutes",
    },
}


class FrontDeskAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "Front Desk Assistance",
                """
Your primary function is to help callers with visitor check-ins, booking availability, and office logistics in a polished front desk style.
You should give concise, welcoming answers, use the available tools before sharing specific visitor or booking details, and direct security-sensitive changes to on-site reception staff.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Greet the caller warmly and understand whether they need visitor, booking, or office help
- Use visitor, booking, or office information tools before giving specific operational details
- If the request is unclear, ask one short clarifying question
- Keep answers brief, polished, and directional

## Security
- For badge changes, identity verification, or other security-sensitive requests:
  Direct the caller to reception staff for verification

## Fallback
- If the requested record is not available:
  Offer the nearest available option naturally

## Closing
- When the request is complete:
  "You're all set. Let me know if you need anything else."
""",
                """
User: "Can you check if Aarav Mehta has arrived?"
Assistant: "Sure, let me check that for you."

User: "Do you have any booking slots today?"
Assistant: "Yes, I can check today's availability for you."

User: "Where should visitors park?"
Assistant: "I can help with that. Let me check the parking details."

User: "I need to change a visitor badge"
Assistant: "For that, reception staff will need to verify the request in person."
""",
                """
- Use available tools to check visitor records, booking slots, and office information before giving specific details.
""",
            ),
        )

    @function_tool()
    async def lookup_visitor(
        self, context: RunContext, visitor_name: str = DEFAULT_VISITOR
    ) -> dict[str, Any]:
        """Look up a visitor or guest arrival before answering check-in or host questions.

        Args:
            visitor_name: Full visitor name to search in the reception log.
        """

        visitor = VISITORS.get(normalize_lookup_key(visitor_name))
        if visitor is None:
            result = {
                "found": False,
                "requested_visitor": visitor_name,
                "available_visitors": [entry["name"] for entry in VISITORS.values()],
            }
            await self.push_widget(
                WidgetPayload(
                    id="frontdesk-visitor",
                    type="visitor",
                    title="Visitor not found",
                    status="warning",
                    description="No reception log entry matched that name in the demo data.",
                    data=rows_from_mapping(
                        {
                            "Requested": visitor_name,
                            "Available": result["available_visitors"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="frontdesk-visitor",
                type="visitor",
                title=f"{visitor['name']} visitor record",
                status="success",
                description="Current reception desk check-in details.",
                data=rows_from_mapping(
                    {
                        "Host": visitor["host"],
                        "Meeting room": visitor["meeting_room"],
                        "Arrival time": visitor["arrival_time"],
                        "Status": visitor["status"],
                        "Badge": visitor["badge"],
                    }
                ),
            )
        )
        return visitor

    @function_tool()
    async def get_booking_slots(
        self, context: RunContext, day: str = "today"
    ) -> dict[str, Any]:
        """Fetch the available booking windows before confirming an appointment or front desk slot.

        Args:
            day: Day label for the slot lookup, such as today.
        """

        slots = BOOKING_SLOTS.get(normalize_lookup_key(day))
        if slots is None:
            result = {
                "found": False,
                "requested_day": day,
                "available_days": list(BOOKING_SLOTS.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="frontdesk-booking",
                    type="schedule",
                    title="No booking slots found",
                    status="warning",
                    description="That day does not have boilerplate booking data.",
                    data=rows_from_mapping(
                        {
                            "Requested": day,
                            "Available": result["available_days"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="frontdesk-booking",
                type="schedule",
                title=f"{day.title()} booking slots",
                status="success",
                description="Current reception availability for scheduling.",
                data=rows_from_mapping(
                    {
                        "Next open slot": slots["next_open_slot"],
                        "Secondary slot": slots["secondary_slot"],
                        "Desk": slots["desk"],
                        "Notes": slots["notes"],
                    }
                ),
            )
        )
        return slots

    @function_tool()
    async def get_office_information(
        self, context: RunContext, topic: str = DEFAULT_TOPIC
    ) -> dict[str, Any]:
        """Retrieve office logistics such as hours, parking, and visitor policy before answering reception questions.

        Args:
            topic: Information topic, such as general or parking.
        """

        info = OFFICE_INFO.get(normalize_lookup_key(topic))
        if info is None:
            result = {
                "found": False,
                "requested_topic": topic,
                "available_topics": list(OFFICE_INFO.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="frontdesk-office-info",
                    type="office-info",
                    title="Office topic not found",
                    status="warning",
                    description="That office information topic is not available in the demo dataset.",
                    data=rows_from_mapping(
                        {
                            "Requested": topic,
                            "Available": result["available_topics"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="frontdesk-office-info",
                type="office-info",
                title=f"{topic.title()} office information",
                status="success",
                description="Reception logistics for the current office setup.",
                data=rows_from_mapping(info),
            )
        )
        return info
