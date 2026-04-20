from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_TICKET = "HD-4421"
DEFAULT_ISSUE = "vpn"
DEFAULT_EMPLOYEE = "Jordan Lee"

TICKETS = {
    "hd-4421": {
        "ticket_id": "HD-4421",
        "owner": "Priyanka S",
        "priority": "High",
        "status": "In progress",
        "eta": "Next update in 45 minutes",
        "summary": "VPN connection drops every 10 minutes on macOS",
    }
}

TROUBLESHOOTING_GUIDES = {
    "vpn": {
        "step_1": "Confirm the device is on the latest VPN client build",
        "step_2": "Remove and re-add the corporate VPN profile",
        "step_3": "Restart the network service after profile sync",
        "escalation": "Escalate to Network Ops if the issue persists after Step 3",
    }
}

DEVICE_STATUS = {
    "jordan lee": {
        "employee": "Jordan Lee",
        "device": "MacBook Pro 14",
        "asset_tag": "SF-8831",
        "patch_level": "2026.04 security rollup applied",
        "account_state": "Active",
        "last_check_in": "14 minutes ago",
    }
}


class HelpDeskPartnerAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "Help Desk Support",
                """
Your primary function is to help users with ticket updates, troubleshooting guidance, and device or account status questions.
You should sound like a calm, experienced support teammate and give practical, reassuring help without overwhelming the caller.
Use the available ticket, troubleshooting, and device context before giving specific operational details.
Escalate lockouts, security issues, or destructive actions to a human engineer.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Start by understanding whether the user needs ticket status, troubleshooting help, or device/account support
- If the request is unclear, ask one short clarifying question
- Give troubleshooting steps one at a time
- Keep responses brief, direct, and reassuring

## Escalation
- If the issue involves account lockout, security risk, or destructive changes:
    Explain that a human engineer should handle it immediately

## Fallback
- If the request is outside the available support data:
    Offer the nearest helpful option naturally

## Closing
- When the issue is resolved or the conversation naturally ends:
    "Glad I could help. Take care!"
""",
                """
User: "Can you check ticket HD-4421?"
Assistant: "Sure, I can help with that."

User: "My VPN keeps disconnecting"
Assistant: "I can help troubleshoot that. Are you calling about the VPN issue?"

User: "Is Jordan Lee's device active?"
Assistant: "I can check that for you."

User: "I'm locked out of my account"
Assistant: "That needs a human engineer right away for security reasons."
""",
                "",
            ),
        )

    @function_tool()
    async def check_ticket_status(
        self, context: RunContext, ticket_id: str = DEFAULT_TICKET
    ) -> dict[str, Any]:
        """Look up a help desk ticket before discussing ownership, ETA, or support status.

        Args:
            ticket_id: Ticket identifier such as HD-4421.
        """

        ticket = TICKETS.get(normalize_lookup_key(ticket_id))
        if ticket is None:
            result = {
                "found": False,
                "requested_ticket": ticket_id,
                "available_tickets": [entry["ticket_id"] for entry in TICKETS.values()],
            }
            await self.push_widget(
                WidgetPayload(
                    id="helpdesk-ticket",
                    type="ticket",
                    title="Ticket not found",
                    status="warning",
                    description="That ticket ID is not available in the demo help desk queue.",
                    data=rows_from_mapping(
                        {
                            "Requested": ticket_id,
                            "Available": result["available_tickets"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="helpdesk-ticket",
                type="ticket",
                title=f"Ticket {ticket['ticket_id']}",
                status="success",
                description="Current support queue status.",
                data=rows_from_mapping(
                    {
                        "Owner": ticket["owner"],
                        "Priority": ticket["priority"],
                        "Status": ticket["status"],
                        "ETA": ticket["eta"],
                        "Summary": ticket["summary"],
                    }
                ),
            )
        )
        return ticket

    @function_tool()
    async def get_troubleshooting_guide(
        self, context: RunContext, issue_type: str = DEFAULT_ISSUE
    ) -> dict[str, Any]:
        """Retrieve a troubleshooting guide before walking the user through a known issue.

        Args:
            issue_type: Support issue label such as vpn.
        """

        guide = TROUBLESHOOTING_GUIDES.get(normalize_lookup_key(issue_type))
        if guide is None:
            result = {
                "found": False,
                "requested_issue": issue_type,
                "available_issues": list(TROUBLESHOOTING_GUIDES.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="helpdesk-guide",
                    type="troubleshooting",
                    title="Guide not found",
                    status="warning",
                    description="That issue type is not available in the demo troubleshooting library.",
                    data=rows_from_mapping(
                        {
                            "Requested": issue_type,
                            "Available": result["available_issues"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="helpdesk-guide",
                type="troubleshooting",
                title=f"{issue_type.upper()} troubleshooting",
                status="success",
                description="Step-by-step guidance for the reported issue.",
                data=rows_from_mapping(guide),
            )
        )
        return guide

    @function_tool()
    async def lookup_device_status(
        self, context: RunContext, employee_name: str = DEFAULT_EMPLOYEE
    ) -> dict[str, Any]:
        """Look up device and account status before discussing endpoint health or user readiness.

        Args:
            employee_name: Employee name tied to the managed device.
        """

        device = DEVICE_STATUS.get(normalize_lookup_key(employee_name))
        if device is None:
            result = {
                "found": False,
                "requested_employee": employee_name,
                "available_employees": [
                    entry["employee"] for entry in DEVICE_STATUS.values()
                ],
            }
            await self.push_widget(
                WidgetPayload(
                    id="helpdesk-device",
                    type="device-status",
                    title="Device not found",
                    status="warning",
                    description="That employee does not have a boilerplate device record.",
                    data=rows_from_mapping(
                        {
                            "Requested": employee_name,
                            "Available": result["available_employees"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="helpdesk-device",
                type="device-status",
                title=f"{device['employee']} device status",
                status="success",
                description="Latest endpoint health snapshot from the demo fleet.",
                data=rows_from_mapping(
                    {
                        "Device": device["device"],
                        "Asset tag": device["asset_tag"],
                        "Patch level": device["patch_level"],
                        "Account state": device["account_state"],
                        "Last check-in": device["last_check_in"],
                    }
                ),
            )
        )
        return device
