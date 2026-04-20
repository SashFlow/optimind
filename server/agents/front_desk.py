from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_VISITOR = "Aarav Mehta"
DEFAULT_TOPIC = "general"
DEFAULT_SERVICE = "product demo"
DEFAULT_SLOT = "2:30 PM"

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

SERVICE_CATALOG = {
    "product demo": {
        "service": "Product demo",
        "duration": "30 minutes",
        "mode": "In-person or video",
        "summary": "Overview of Sashflow voice and chat automation capabilities.",
        "availability": "Weekdays between 10:00 AM and 5:00 PM",
    },
    "consultation": {
        "service": "Consultation",
        "duration": "45 minutes",
        "mode": "Video or office meeting",
        "summary": "Discovery call for workflow design, integrations, and rollout planning.",
        "availability": "Weekdays between 11:00 AM and 6:00 PM",
    },
    "implementation review": {
        "service": "Implementation review",
        "duration": "60 minutes",
        "mode": "Video",
        "summary": "Detailed review of an existing deployment, blockers, and next steps.",
        "availability": "By prior scheduling only",
    },
}


class FrontDeskAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "Front Desk Assistance",
                """
Your primary function is to act like a polished front desk coordinator who can explain services, check free slots, book appointments, and handle visitor or reception questions.
You should sound welcoming and organized, use the relevant tools before sharing any service, booking, or visitor details, and route identity-sensitive changes to on-site staff.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Greet the caller warmly and understand whether they need service information, free slots, an appointment booking, visitor help, or office information
- Use the matching tool before giving specific operational details
- If the request is unclear, ask one short clarifying question
- Keep answers brief, polished, and directional

## Booking Guidance
- If the caller wants availability, use the booking slot tool first
- If the caller wants to reserve a time, use the appointment booking tool after confirming the service and preferred slot
- If the exact slot is unavailable, offer the closest available option from the tool result

## Service Guidance
- Use the service information tool when the caller asks what the team offers, how long a session takes, or which service fits their need
- Summarize the service in simple language instead of reading every field unless asked

## Security
- For badge changes, identity verification, or other security-sensitive requests:
  Direct the caller to reception staff or transfer to a human for verification

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

User: "Can you book me for a product demo at 2:30?"
Assistant: "Absolutely — I'll check that slot and reserve it if it's available."

User: "What services do you offer?"
Assistant: "I can walk you through the available services and what each one is best for."

User: "Where should visitors park?"
Assistant: "I can help with that. Let me check the parking details."

User: "I need to change a visitor badge"
Assistant: "For that, reception staff will need to verify the request in person."
                """,
                """
- Tool mapping:
  - lookup_visitor: use for arrival status, hosts, badge details, and meeting-room questions
  - get_booking_slots: use for free-slot checks and availability questions
  - book_appointment: use to reserve an appointment when the caller wants a booking confirmed
  - get_service_information: use when the caller asks about available services, duration, format, or suitability
  - get_office_information: use for logistics such as parking, office hours, and visitor policy
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
        """Fetch available appointment windows for the requested day.

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
    async def book_appointment(
        self,
        context: RunContext,
        visitor_name: str = DEFAULT_VISITOR,
        service: str = DEFAULT_SERVICE,
        day: str = "today",
        preferred_slot: str = DEFAULT_SLOT,
    ) -> dict[str, Any]:
        """Reserve an appointment for a caller using the available demo booking slots.

        Use this after confirming the service and preferred time. The tool checks the
        requested day and slot against the available booking data, returns a confirmed
        appointment when possible, and suggests alternate slots when the exact request
        is not available.

        Args:
            visitor_name: Name of the person who wants the booking.
            service: Service being scheduled, such as product demo or consultation.
            day: Day label for the booking request.
            preferred_slot: Preferred time slot to reserve.
        """

        normalized_day = normalize_lookup_key(day)
        normalized_service = normalize_lookup_key(service)
        slots = BOOKING_SLOTS.get(normalized_day)
        service_info = SERVICE_CATALOG.get(normalized_service)

        if service_info is None:
            result = {
                "confirmed": False,
                "requested_service": service,
                "available_services": list(SERVICE_CATALOG.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="frontdesk-book-appointment",
                    type="booking-confirmation",
                    title="Service not available",
                    status="warning",
                    description="That service is not part of the demo front desk catalog.",
                    data=rows_from_mapping(
                        {
                            "Requested service": service,
                            "Available services": result["available_services"],
                        }
                    ),
                )
            )
            return result

        if slots is None:
            result = {
                "confirmed": False,
                "requested_day": day,
                "available_days": list(BOOKING_SLOTS.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="frontdesk-book-appointment",
                    type="booking-confirmation",
                    title="Booking day unavailable",
                    status="warning",
                    description="The requested day does not have booking data in the demo setup.",
                    data=rows_from_mapping(
                        {
                            "Requested day": day,
                            "Available days": result["available_days"],
                        }
                    ),
                )
            )
            return result

        available_slots = {slots["next_open_slot"], slots["secondary_slot"]}
        if preferred_slot not in available_slots:
            result = {
                "confirmed": False,
                "requested_slot": preferred_slot,
                "available_slots": sorted(available_slots),
                "requested_day": day,
            }
            await self.push_widget(
                WidgetPayload(
                    id="frontdesk-book-appointment",
                    type="booking-confirmation",
                    title="Preferred slot unavailable",
                    status="warning",
                    description="The requested slot is not free in the demo schedule, but alternate slots are available.",
                    data=rows_from_mapping(
                        {
                            "Requested slot": preferred_slot,
                            "Available slots": result["available_slots"],
                            "Day": day,
                        }
                    ),
                )
            )
            return result

        confirmation = {
            "confirmed": True,
            "visitor_name": visitor_name,
            "service": service_info["service"],
            "day": day.title(),
            "slot": preferred_slot,
            "desk": slots["desk"],
            "confirmation_id": "FD-BOOK-230",
            "notes": f"Please arrive 10 minutes early for the {service_info['service'].lower()}.",
        }
        await self.push_widget(
            WidgetPayload(
                id="frontdesk-book-appointment",
                type="booking-confirmation",
                title=f"{service_info['service']} booked",
                status="success",
                description="The appointment has been reserved in the front desk demo scheduler.",
                data=rows_from_mapping(
                    {
                        "Visitor": confirmation["visitor_name"],
                        "Service": confirmation["service"],
                        "Day": confirmation["day"],
                        "Time": confirmation["slot"],
                        "Desk": confirmation["desk"],
                        "Confirmation ID": confirmation["confirmation_id"],
                        "Notes": confirmation["notes"],
                    }
                ),
            )
        )
        return confirmation

    @function_tool()
    async def get_service_information(
        self, context: RunContext, service: str = DEFAULT_SERVICE
    ) -> dict[str, Any]:
        """Retrieve service details before explaining what can be booked.

        Use this for questions about available services, session length, booking mode,
        or which option best fits the caller's goal.

        Args:
            service: Service name such as product demo, consultation, or implementation review.
        """

        service_info = SERVICE_CATALOG.get(normalize_lookup_key(service))
        if service_info is None:
            result = {
                "found": False,
                "requested_service": service,
                "available_services": list(SERVICE_CATALOG.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="frontdesk-service-info",
                    type="service-info",
                    title="Service not found",
                    status="warning",
                    description="That service is not available in the front desk demo catalog.",
                    data=rows_from_mapping(
                        {
                            "Requested": service,
                            "Available": result["available_services"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="frontdesk-service-info",
                type="service-info",
                title=f"{service_info['service']} details",
                status="success",
                description="Service information that the front desk can share before booking.",
                data=rows_from_mapping(service_info),
            )
        )
        return service_info

    @function_tool()
    async def get_office_information(
        self, context: RunContext, topic: str = DEFAULT_TOPIC
    ) -> dict[str, Any]:
        """Retrieve office logistics such as hours, parking, and visitor policy.

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
