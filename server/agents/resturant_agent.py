from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_GUEST = "Maya Kapoor"
DEFAULT_PREFERENCE = "vegetarian"
DEFAULT_ORDER = "ORD-104"
DEFAULT_MENU_CATEGORY = "featured"
DEFAULT_ORDER_ITEMS = "Truffle mushroom risotto, Citrus soda"

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

MENU_SHOWCASE = {
    "featured": (
        {
            "name": "Truffle mushroom risotto",
            "category": "Main",
            "price": "INR 680",
            "image_url": "https://picsum.photos/seed/risotto/640/480",
        },
        {
            "name": "Charred broccoli salad",
            "category": "Starter",
            "price": "INR 420",
            "image_url": "https://picsum.photos/seed/broccoli-salad/640/480",
        },
        {
            "name": "Chocolate hazelnut tart",
            "category": "Dessert",
            "price": "INR 360",
            "image_url": "https://picsum.photos/seed/hazelnut-tart/640/480",
        },
    ),
    "drinks": (
        {
            "name": "Citrus soda",
            "category": "Beverage",
            "price": "INR 180",
            "image_url": "https://picsum.photos/seed/citrus-soda/640/480",
        },
        {
            "name": "Masala buttermilk",
            "category": "Beverage",
            "price": "INR 150",
            "image_url": "https://picsum.photos/seed/buttermilk/640/480",
        },
    ),
}

ORDER_STATUS = {
    "ord-104": {
        "order_id": "ORD-104",
        "status": "Preparing",
        "eta": "18 minutes",
        "items": "Paneer tikka pizza, Citrus soda",
        "delivery_partner": "Rakesh",
        "guest_name": "Maya Kapoor",
    }
}

ACTIVE_ORDERS = {
    "maya kapoor": "ord-104",
}


class ResturantAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "Restaurant Support",
                """
You help callers with restaurant reservations, menu browsing with image links, menu recommendations, active-order details, new food orders, dietary guidance, and order status updates.
Use the reservation, menu, and order tools before giving specific guest, kitchen, or delivery details.
Sound like attentive front-of-house staff: warm, confident, and brief.
If a request is outside the demo data, explain the nearest available option naturally.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Greet the guest warmly and understand whether they need help with a reservation, menu choice, menu images, an active order, placing an order, or an order update
- Use reservation lookup for booking details, menu image and recommendation tools for food guidance, active-order tools for current carts, and order status for live updates
- If the request is unclear, ask one short clarifying question
- Keep replies brief, natural, and service-oriented

## Reservation Requests
- Confirm reservation details only after checking the reservation tool
- If no reservation is found, offer the nearest available option from the demo data naturally

## Menu Guidance
- Use the menu showcase tool when the guest wants to browse dishes or see menu items with image links
- Use the menu tool before recommending dishes tied to preferences or dietary needs
- Keep recommendations short and practical

## Order Updates
- Use the active order tool when the guest wants to know what is currently in their open order
- Use the place order tool when the guest wants to order items from the menu
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

User: "Can you show me the menu?"
Assistant: "Absolutely — I'll pull up the featured menu items for you."

User: "Where's my order ORD-104?"
Assistant: "I'll check the latest order status now."

User: "Can you add a risotto and soda to my order?"
Assistant: "Yes — I'll create that order for you now."

User: "Can you change my booking?"
Assistant: "I can share the current reservation details, but booking changes would need the restaurant team."
""",
                """
- Tool mapping:
  - lookup_reservation: use for reservation confirmation, time, table, and party details
  - show_menu_with_images: use when the guest wants to browse dishes or see menu items with image links
  - get_menu_recommendations: use for dietary preferences and tailored recommendations
  - get_active_order: use to show the items and state of the guest's current open order
  - place_order: use when the guest wants to order menu items
  - check_order_status: use for ETA, preparation state, and delivery updates
                """,
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
    async def show_menu_with_images(
        self, context: RunContext, category: str = DEFAULT_MENU_CATEGORY
    ) -> dict[str, Any]:
        """Show menu items for a category together with image links and prices.

        Use this when the guest wants to browse the menu, see featured dishes, or ask
        for visually oriented menu options. The image URLs are demo links that can be
        displayed or opened by the client experience.

        Args:
            category: Menu category such as featured or drinks.
        """

        menu_items = MENU_SHOWCASE.get(normalize_lookup_key(category))
        if menu_items is None:
            result = {
                "found": False,
                "requested_category": category,
                "available_categories": list(MENU_SHOWCASE.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="restaurant-menu-showcase",
                    type="menu-showcase",
                    title="Menu category not found",
                    status="warning",
                    description="That menu category is not available in the demo showcase.",
                    data=rows_from_mapping(
                        {
                            "Requested": category,
                            "Available": result["available_categories"],
                        }
                    ),
                )
            )
            return result

        items_summary = {
            item["name"]: f"{item['category']} • {item['price']} • {item['image_url']}"
            for item in menu_items
        }
        await self.push_widget(
            WidgetPayload(
                id="restaurant-menu-showcase",
                type="menu-showcase",
                title=f"{category.title()} menu",
                status="success",
                description="Featured menu items with image links from the demo restaurant catalog.",
                data=rows_from_mapping(items_summary),
                highlights=tuple(item["image_url"] for item in menu_items),
            )
        )
        return {
            "category": category,
            "items": list(menu_items),
        }

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
    async def get_active_order(
        self, context: RunContext, guest_name: str = DEFAULT_GUEST
    ) -> dict[str, Any]:
        """Show the guest's currently active order with its items and status.

        Use this when the guest wants to know what is already in their open order
        before asking for status, changes, or a repeat of the current items.

        Args:
            guest_name: Full guest name for the active-order lookup.
        """

        active_order_id = ACTIVE_ORDERS.get(normalize_lookup_key(guest_name))
        if active_order_id is None:
            result = {
                "found": False,
                "requested_guest": guest_name,
                "available_guests": [entry["guest_name"] for entry in RESERVATIONS.values()],
            }
            await self.push_widget(
                WidgetPayload(
                    id="restaurant-active-order",
                    type="order",
                    title="No active order found",
                    status="warning",
                    description="This guest does not currently have an active order in the demo system.",
                    data=rows_from_mapping(
                        {
                            "Requested guest": guest_name,
                            "Known guests": result["available_guests"],
                        }
                    ),
                )
            )
            return result

        order = ORDER_STATUS[active_order_id]
        await self.push_widget(
            WidgetPayload(
                id="restaurant-active-order",
                type="order",
                title=f"{guest_name} active order",
                status="success",
                description="Current open order linked to the guest.",
                data=rows_from_mapping(
                    {
                        "Order ID": order["order_id"],
                        "Status": order["status"],
                        "Items": order["items"],
                        "ETA": order["eta"],
                    }
                ),
            )
        )
        return order

    @function_tool()
    async def place_order(
        self,
        context: RunContext,
        guest_name: str = DEFAULT_GUEST,
        items: str = DEFAULT_ORDER_ITEMS,
    ) -> dict[str, Any]:
        """Create or replace an active order for a guest using menu item text.

        Use this when the guest clearly wants to order food or drinks. The items
        argument can contain one or more comma-separated menu items in natural text.

        Args:
            guest_name: Full guest name for the order.
            items: One or more comma-separated menu items to place in the order.
        """

        normalized_guest = normalize_lookup_key(guest_name)
        order_number = max(
            int(entry["order_id"].split("-")[1]) for entry in ORDER_STATUS.values()
        ) + 1
        order_id = f"ORD-{order_number}"
        order = {
            "order_id": order_id,
            "status": "Confirmed",
            "eta": "25 minutes",
            "items": items,
            "delivery_partner": "Awaiting assignment",
            "guest_name": guest_name,
        }
        ORDER_STATUS[normalize_lookup_key(order_id)] = order
        ACTIVE_ORDERS[normalized_guest] = normalize_lookup_key(order_id)

        await self.push_widget(
            WidgetPayload(
                id="restaurant-place-order",
                type="order",
                title=f"Order {order_id} placed",
                status="success",
                description="A new order has been created in the demo ordering flow.",
                data=rows_from_mapping(
                    {
                        "Guest": guest_name,
                        "Order ID": order_id,
                        "Items": items,
                        "Status": order["status"],
                        "ETA": order["eta"],
                    }
                ),
            )
        )
        return order

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
