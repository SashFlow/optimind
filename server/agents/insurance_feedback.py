import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
import asyncio

from agents.base import ScenarioAgent
from agents.lib import INSURANCE_FEEDBACK_AGENT_PROMPT
from livekit.agents import RunContext, function_tool

logger = logging.getLogger(__name__)

INDIA_TZ = ZoneInfo("Asia/Kolkata")


class InsuranceFeedbackAgent(ScenarioAgent):
    def __init__(self, name, gender, validation_details) -> None:
        self.validation_details = validation_details
        self._current_step: str = "greeting"

        customer_name = validation_details.get("full_name", "the customer")
        company_name = validation_details.get("company_name", "MAX HEALTH")
        current_time = datetime.now(INDIA_TZ).strftime("%A, %d %B %Y %H:%M IST")

        super().__init__(
            language="english",
            instructions=INSURANCE_FEEDBACK_AGENT_PROMPT.format(
                name=name,
                gender=gender,
                company_name=company_name,
                current_time=current_time,
                customer_name=customer_name,
            ),
        )

    @function_tool()
    async def schedule_callback(
        self, _context: RunContext, preferred_time: str = ""
    ) -> dict[str, Any]:
        """Schedule a callback for the customer at a preferred time.

        Use when the customer is unavailable, interrupted, or requests a later call.

        Args:
            preferred_time: Customer's preferred callback time (free text). Optional.
        """
        await asyncio.sleep(2)
        callback_time = preferred_time.strip() if preferred_time else "within 2 hours"
        return {
            "scheduled": True,
            "callback_time": callback_time,
            "next_step": "close",
        }
