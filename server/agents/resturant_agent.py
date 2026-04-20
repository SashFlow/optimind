from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_GUEST = "Maya Kapoor"
DEFAULT_PREFERENCE = "vegetarian"
DEFAULT_ORDER = "ORD-104"

RESERVATIONS = {
    "maya kapoor": {
        "guest_name": "Maya Kapoor",
        "reservation_id": "RSV-320",
        "party_size": "4",
        "time": "8:00 PM",
        "table": "Terrace 6",
        "status": "Confirmed",
        "notes": "Birthday dessert requested",
    }
}

MENU_GUIDES = {
    "vegetarian": {
        "starter": "Charred broccoli salad",
        "main": "Truffle mushroom risotto",
        "dessert": "Saffron panna cotta",
        "dietary_note": "All dishes can be prepared nut-free on request",
    },
    "popular": {
        "starter": "Crispy lotus stem",
        "main": "Wood-fired pepper chicken",
        "dessert": "Chocolate hazelnut tart",
        "dietary_note": "The kitchen can swap dairy on most mains",
    },
}

ORDER_STATUS = {
    "ord-104": {
        "order_id": "ORD-104",
        "status": "Preparing",
        "eta": "18 minutes",
        "items": "Paneer tikka pizza, Citrus soda",
        "delivery_partner": "Rakesh",
    }
}


class ResturantAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "Restaurant Support",
                """
You help callers with restaurant reservations, menu recommendations, dietary guidance, and order status updates.
Use the reservation, menu, and order tools before giving specific guest, kitchen, or delivery details.
Sound like attentive front-of-house staff: warm, confident, and brief.
If a request is outside the demo data, explain the nearest available option naturally.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Greet the guest warmly and understand whether they need help with a reservation, menu choice, or order update
- Use reservation lookup for booking details, menu recommendations for food guidance, and order status for live updates
- If the request is unclear, ask one short clarifying question
- Keep replies brief, natural, and service-oriented

## Reservation Requests
- Confirm reservation details only after checking the reservation tool
- If no reservation is found, offer the nearest available option from the demo data naturally

## Menu Guidance
- Use the menu tool before recommending dishes tied to preferences or dietary needs
- Keep recommendations short and practical

## Order Updates
- Use the order status tool before sharing preparation or delivery timing
- Share only the key status and next useful detail

## Escalation
- If the user asks for changes that require staff verification or anything outside the available data, direct them to the restaurant team
""",
                """
User: "Can you check Maya Kapoor's reservation?"
Assistant: "Sure — let me check that for you."

User: "What do you recommend for a vegetarian?"
Assistant: "I can help with that — let me pull up the vegetarian options."

User: "Where's my order ORD-104?"
Assistant: "I'll check the latest order status now."

User: "Can you change my booking?"
Assistant: "I can share the current reservation details, but booking changes would need the restaurant team."
""",
                "",
            ),
        )

    @function_tool()
    async def lookup_reservation(
        self, context: RunContext, guest_name: str = DEFAULT_GUEST
    ) -> dict[str, Any]:
        """Look up a table reservation before answering timing, party size, or seating questions.

        Args:
            guest_name: Full guest name for the reservation lookup.
        """

        reservation = RESERVATIONS.get(normalize_lookup_key(guest_name))
        if reservation is None:
            result = {
                "found": False,
                "requested_guest": guest_name,
                "available_reservations": [
                    entry["guest_name"] for entry in RESERVATIONS.values()
                ],
            }
            await self.push_widget(
                WidgetPayload(
                    id="restaurant-reservation",
                    type="reservation",
                    title="Reservation not found",
                    status="warning",
                    description="No reservation matched that guest name in the demo data.",
                    data=rows_from_mapping(
                        {
                            "Requested": guest_name,
                            "Available": result["available_reservations"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="restaurant-reservation",
                type="reservation",
                title=f"{reservation['guest_name']} reservation",
                status="success",
                description="Current reservation details from the host stand.",
                data=rows_from_mapping(
                    {
                        "Reservation ID": reservation["reservation_id"],
                        "Party size": reservation["party_size"],
                        "Time": reservation["time"],
                        "Table": reservation["table"],
                        "Status": reservation["status"],
                        "Notes": reservation["notes"],
                    }
                ),
            )
        )
        return reservation

    @function_tool()
    async def get_menu_recommendations(
        self, context: RunContext, preference: str = DEFAULT_PREFERENCE
    ) -> dict[str, Any]:
        """Retrieve menu suggestions and dietary notes before recommending dishes.

        Args:
            preference: Dining preference such as vegetarian or popular.
        """

        menu = MENU_GUIDES.get(normalize_lookup_key(preference))
        if menu is None:
            result = {
                "found": False,
                "requested_preference": preference,
                "available_preferences": list(MENU_GUIDES.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="restaurant-menu",
                    type="menu",
                    title="Menu preference not found",
                    status="warning",
                    description="That menu preference is not available in the demo recommendation set.",
                    data=rows_from_mapping(
                        {
                            "Requested": preference,
                            "Available": result["available_preferences"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="restaurant-menu",
                type="menu",
                title=f"{preference.title()} recommendations",
                status="success",
                description="Suggested dishes from the current demo menu.",
                data=rows_from_mapping(menu),
            )
        )
        return menu

    @function_tool()
    async def check_order_status(
        self, context: RunContext, order_id: str = DEFAULT_ORDER
    ) -> dict[str, Any]:
        """Check the preparation or delivery state of an order before quoting ETA information.

        Args:
            order_id: Restaurant order identifier such as ORD-104.
        """

        order = ORDER_STATUS.get(normalize_lookup_key(order_id))
        if order is None:
            result = {
                "found": False,
                "requested_order": order_id,
                "available_orders": [
                    entry["order_id"] for entry in ORDER_STATUS.values()
                ],
            }
            await self.push_widget(
                WidgetPayload(
                    id="restaurant-order",
                    type="order",
                    title="Order not found",
                    status="warning",
                    description="That order ID is not available in the demo order tracker.",
                    data=rows_from_mapping(
                        {
                            "Requested": order_id,
                            "Available": result["available_orders"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="restaurant-order",
                type="order",
                title=f"Order {order['order_id']}",
                status="success",
                description="Live kitchen and delivery status.",
                data=rows_from_mapping(
                    {
                        "Status": order["status"],
                        "ETA": order["eta"],
                        "Items": order["items"],
                        "Delivery partner": order["delivery_partner"],
                    }
                ),
            )
        )
        return order
