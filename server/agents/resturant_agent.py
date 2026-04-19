from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import SCENARIOS, WidgetPayload, normalize_lookup_key, rows_from_mapping

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
            scenario=SCENARIOS["resturant-agent"],
            operating_notes=(
                "Use the reservation, menu, and order tools before quoting concrete guest or kitchen details.",
                "Sound warm and hospitality-focused while keeping answers short enough for voice.",
                "If the user asks for a change outside the demo data, explain what is available and offer the closest option.",
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
                "available_orders": [entry["order_id"] for entry in ORDER_STATUS.values()],
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
