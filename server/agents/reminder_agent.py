import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
import random
from livekit.agents import RunContext, function_tool

from client.appointment_db import reschedule_appointment as db_reschedule_appointment
from agents.base import ScenarioAgent
from .medical_appointment import (
    INSURANCE_COMPANIES,
    _normalize_appointment_date,
    _normalize_appointment_time,
)
from agents.lib import REMINDER_AGENT_PROMPT, MAX_REMINDER_AGENT_PROMPT

logger = logging.getLogger(__name__)

INDIA_TZ = ZoneInfo("Asia/Kolkata")


APPOINTMENTS = [
    {
        "date": "2026-07-27",
        "time": "10:00 AM",
        "pin_code": "400067",
        "address": "807, Golden Lane, Kandivali West, Mumbai",
        "landmark": "Golden Lane",
        "contact_number": "9876543210",
        "center_name": "Apollo Hospital",
        "center_address": "123, Main St, Anytown, Mumbai",
    },
    {
        "date": "2026-07-28",
        "time": "11:00 AM",
        "pin_code": "400067",
        "address": "807, Golden Lane, Kandivali West, Mumbai",
        "landmark": "Golden Lane",
        "contact_number": "9876543210",
        "center_name": "Apollo Hospital",
        "center_address": "123, Main St, Anytown, Mumbai",
    },
    {
        "date": "2026-07-29",
        "time": "12:00 PM",
        "pin_code": "400067",
        "address": "807, Golden Lane, Kandivali West, Mumbai",
        "landmark": "Golden Lane",
        "contact_number": "9876543210",
        "center_name": "Apollo Hospital",
        "center_address": "123, Main St, Anytown, Mumbai",
    },
    {
        "date": "2026-07-30",
        "time": "13:00 PM",
        "pin_code": "400067",
        "address": "807, Golden Lane, Kandivali West, Mumbai",
        "landmark": "Golden Lane",
        "contact_number": "9876543210",
        "center_name": "Apollo Hospital",
        "center_address": "123, Main St, Anytown, Mumbai",
    },
    {
        "date": "2026-07-31",
        "time": "14:00 PM",
        "pin_code": "400067",
        "address": "807, Golden Lane, Kandivali West, Mumbai",
        "landmark": "Golden Lane",
        "contact_number": "9876543210",
        "center_name": "Apollo Hospital",
        "center_address": "123, Main St, Anytown, Mumbai",
    },
]


class ReminderAgent(ScenarioAgent):
    def __init__(self, name, gender, language, validation_details) -> None:
        self.validation_details = validation_details
        self.appointment = random.choice(APPOINTMENTS)
        self._dob_attempts: int = 0
        self._current_step: str = "greeting"

        customer_name = validation_details.get("full_name", "the customer")
        current_time = datetime.now(INDIA_TZ).strftime("%A, %d %B %Y %H:%M IST")
        company_name = random.choice(INSURANCE_COMPANIES)

        is_axis_max_life = company_name == "Axis Max-Life Insurance"

        is_home_visit_available = random.choice([True, False])

        if is_home_visit_available:
            self._booking_context = {
                "exam_type": "Home Collection",
                "address": self.appointment.get("address", ""),
                "pin_code": self.appointment.get("pin_code", ""),
                "landmark": self.appointment.get("landmark", ""),
                "contact_number": self.appointment.get("contact_number", ""),
            }
        else:
            self._booking_context = {
                "exam_type": "Medical Examination",
                "address": self.appointment.get("center_address", ""),
                "center_name": self.appointment.get("center_name", ""),
                "pin_code": "",
            }

        super().__init__(
            language=language,
            instructions=MAX_REMINDER_AGENT_PROMPT.format(
                name=name,
                gender=gender,
                company_name=company_name,
                current_time=current_time,
                customer_name=customer_name,
                is_home_visit_available=is_home_visit_available,
                appointment_date=self.appointment.get("date", ""),
                appointment_time=self.appointment.get("time", ""),
                address=self.appointment.get("address", ""),
                landmark=self.appointment.get("landmark", ""),
                contact_number=self.appointment.get("contact_number", ""),
                center_name=self.appointment.get("center_name", ""),
                center_address=self.appointment.get("center_address", ""),
            )
            if is_axis_max_life
            else REMINDER_AGENT_PROMPT.format(
                name=name,
                gender=gender,
                company_name=company_name,
                current_time=current_time,
                customer_name=customer_name,
                is_home_visit_available=is_home_visit_available,
                appointment_date=self.appointment.get("date", ""),
                appointment_time=self.appointment.get("time", ""),
                address=self.appointment.get("address", ""),
                landmark=self.appointment.get("landmark", ""),
                contact_number=self.appointment.get("contact_number", ""),
                center_name=self.appointment.get("center_name", ""),
                center_address=self.appointment.get("center_address", ""),
            ),
        )

    # -----------------------------------------------------------------------
    # Reschedule
    # -----------------------------------------------------------------------

    @function_tool()
    async def reschedule_appointment_booking(
        self,
        _context: RunContext,
        new_date: str,
        new_time: str,
        exam_type: str = "",
        pin_code: str = "",
        address: str = "",
    ) -> dict[str, Any]:
        """Reschedule the customer's existing appointment to a new date and time.

        Call this after collecting the new date and time from the customer.
        The tool updates the existing appointment record in the database.

        Args:
            new_date: New preferred date as stated by the customer (e.g. "25th May", "next Monday").
            new_time: New preferred time as stated by the customer (e.g. "10 AM", "2:30").
            exam_type: "Home Collection" for home visit or "Medical Examination" for center. Leave blank to keep existing.
            pin_code: Pin code for home visit. Leave blank to keep existing.
            address: Address for home visit or center address. Leave blank to keep existing.
        """
        await asyncio.sleep(2)
        self._current_step = "reschedule_booking"

        norm_date = _normalize_appointment_date(new_date)
        norm_time = _normalize_appointment_time(new_time)
        final_exam_type = exam_type or self._booking_context.get("exam_type", "")
        final_pin_code = pin_code or self._booking_context.get("pin_code", "")
        final_address = address or self._booking_context.get("address", "")
        phone = self.validation_details.get("phone_number", "")
        dob = self.validation_details.get("dob", "")
        try:
            record = await asyncio.to_thread(
                db_reschedule_appointment,
                phone,
                dob,
                norm_date,
                norm_time,
                final_exam_type,
                final_pin_code,
                final_address,
            )
        except Exception as exc:
            logger.exception("Failed to reschedule appointment: %s", exc)
            record = {}

        if record.get("result") == "failed":
            return {
                "rescheduled": False,
                "error": record.get("error", "Could not reschedule the appointment."),
                "next_step": "escalate",
            }

        return {
            "rescheduled": True,
            "appointment_id": record.get("appointment_id", ""),
            "date": norm_date,
            "time": norm_time,
            "exam_type": final_exam_type,
            "address": final_address or record.get("address", ""),
            "center_name": self._booking_context.get("center_name", ""),
            "next_step": "close",
        }

    # -----------------------------------------------------------------------
    # Flow control
    # -----------------------------------------------------------------------

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
