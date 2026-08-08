import logging
import re
import random
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from agents.base import ScenarioAgent
from prompts import INSURANCE_FEEDBACK_AGENT_PROMPT
from livekit.agents import RunContext, function_tool
from constants import SupportState

logger = logging.getLogger(__name__)

INDIA_TZ = ZoneInfo("Asia/Kolkata")

CALL_STEPS = (
    "greeting",
    "language",
    "availability",
    "feedback",
    "closing",
)

SALUTATION_PREFIXES = ("Mr.", "Mrs.", "Ms.", "Mx.", "Dr.")


def parse_customer_salutation(full_name: str) -> str:
    """Extract honorific prefix from a customer full name."""
    normalized = (full_name or "").strip()
    for prefix in SALUTATION_PREFIXES:
        if normalized.startswith(prefix):
            return prefix
    return ""


def resolve_is_home_visit(validation_details: dict[str, Any]) -> str:
    """Resolve home vs center visit path from persona / validation data."""
    visit_type = validation_details.get(
        "visit_type", validation_details.get("is_home_visit")
    )
    if isinstance(visit_type, bool):
        return "YES" if visit_type else "NO"
    if isinstance(visit_type, str):
        normalized = visit_type.strip().lower()
        if normalized in ("home", "yes", "true"):
            return "YES"
        if normalized in ("center", "centre", "no", "false"):
            return "NO"
    return "YES"


class InsuranceFeedbackAgent(ScenarioAgent):
    def __init__(self, state: SupportState, validation_details) -> None:
        self._state = state or SupportState()
        self._name = "Sanjay" if state.voice == "male" else "Samira"
        self.validation_details = validation_details
        self._current_step: str = "greeting"
        self._feedback: dict[str, dict[str, Any]] = {}
        self._end_call_invoked = False

        customer_name = validation_details.get("full_name", "the customer")
        company_name = validation_details.get("company_name", "MAX HEALTH")
        current_time = datetime.now(INDIA_TZ).strftime("%A, %d %B %Y %H:%M IST")
        customer_salutation = parse_customer_salutation(customer_name)
        is_home_visit = random.choice(["YES", "NO"])

        super().__init__(
            instructions=INSURANCE_FEEDBACK_AGENT_PROMPT.format(
                name=self._name,
                company_name=company_name,
                current_time=current_time,
                customer_name=customer_name,
                is_home_visit=is_home_visit,
                customer_salutation=customer_salutation,
            ),
            job_instructions=f"""
            You are {self._name}, a confident, friendly {self._state.voice} outbound voice agent calling on behalf of {company_name}
            to collect feedback from a customer about their medical examination experience in India.

            """,
            state=self._state,
        )

    def _step_guidance(self) -> str:
        guidance = {
            "greeting": "Complete right-party check, then call advance_call_step(step='language').",
            "language": "Confirm language choice, then call advance_call_step(step='availability').",
            "availability": "Confirm availability, then call advance_call_step(step='feedback').",
            "feedback": (
                "Deliver recording notice and call purpose, then ask Step 3 feedback questions "
                "one at a time; call submit_feedback after each answer."
            ),
            "closing": (
                "Deliver all Step 4 closing lines, then call end_call exactly once in the same turn."
            ),
        }
        return guidance.get(self._current_step, "Continue the scripted call flow.")

    @function_tool()
    async def advance_call_step(
        self, _context: RunContext, step: str
    ) -> dict[str, Any]:
        """Move to the next script step after the current step is fully resolved.

        Use when completing Steps 0 through 2, when entering feedback, when entering closing, or before end_call.
        Valid steps: greeting, language, availability, feedback, closing.

        Args:
            step: The step you are advancing to.
        """
        normalized = re.sub(r"[^a-z_]", "", step.strip().lower())
        if normalized not in CALL_STEPS:
            return {
                "recorded": False,
                "error": f"Invalid step '{step}'. Use one of: {', '.join(CALL_STEPS)}",
                "current_step": self._current_step,
            }

        self._current_step = normalized
        logger.info("Insurance feedback call advanced to step: %s", normalized)
        return {
            "recorded": True,
            "current_step": self._current_step,
            "next_action": self._step_guidance(),
        }

    @function_tool()
    async def submit_feedback(
        self,
        _context: RunContext,
        question_key: str,
        answer: str,
        is_complaint: bool = False,
    ) -> dict[str, Any]:
        """Record a feedback answer or customer complaint for this call.

        Call after each Step 3 feedback question is answered and whenever the customer raises a complaint.

        Args:
            question_key: Identifier such as q1, q2, q3, q4, q5, q6, rating, or complaint_topic.
            answer: Summary of the customer's response.
            is_complaint: Set true when the customer expresses dissatisfaction or a process failure.
        """
        key = question_key.strip().lower()
        self._feedback[key] = {
            "answer": answer.strip(),
            "is_complaint": is_complaint,
        }
        if self._current_step != "feedback" and not is_complaint:
            self._current_step = "feedback"

        logger.info(
            "Insurance feedback recorded: step=%s key=%s complaint=%s answer=%s",
            self._current_step,
            key,
            is_complaint,
            answer,
        )
        return {
            "recorded": True,
            "question_key": key,
            "is_complaint": is_complaint,
            "current_step": self._current_step,
            "answers_recorded": len(self._feedback),
            "next_action": (
                "Deliver the Complaint Response before the next question."
                if is_complaint
                else "Acknowledge briefly, then ask the next Step 3 feedback question."
            ),
        }
