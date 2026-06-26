from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from livekit.agents import RunContext, function_tool

from client.appointment_db import reschedule_appointment as db_reschedule_appointment
from agents.base import ScenarioAgent
from agents.common import normalize_lookup_key
from .medical_appointment import (
    DIAGNOSTIC_CENTERS,
    _normalize_dob,
    _normalize_phone,
    _normalize_appointment_date,
    _normalize_appointment_time,
)
from agents.lib import REMINDER_AGENT_PROMPT

logger = logging.getLogger(__name__)

INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _format_appointment_summary(appointment: dict | None) -> str:
    if not appointment:
        return "No existing appointment found in the system."
    appt_type = appointment.get("appointment_type", "unknown")
    type_label = "Home Visit" if appt_type == "home" else "Diagnostic Center Visit"
    lines = [
        f"Type: {type_label}",
        f"Date: {appointment.get('date', 'unknown')}",
        f"Time: {appointment.get('time', 'unknown')}",
    ]
    address = appointment.get("address", "")
    if address:
        lines.append(f"Address: {address}")
    return "\n".join(lines)


class ReminderAgent(ScenarioAgent):
    def __init__(self, name, gender, language, validation_details, appointment) -> None:
        self.validation_details = validation_details
        self.appointment = appointment
        self._dob_attempts: int = 0
        self._booking_context: dict[str, Any] = {}
        self._current_step: str = "greeting"

        customer_name = validation_details.get("full_name", "the customer")
        current_time = datetime.now(INDIA_TZ).strftime("%A, %d %B %Y %H:%M IST")
        appt_summary = _format_appointment_summary(appointment)

        appt_date_str = (appointment or {}).get("date", "")
        appt_is_past = False
        if appt_date_str:
            try:
                appt_is_past = date.fromisoformat(appt_date_str) < date.today()
            except ValueError:
                pass
        past_note = (
            "\n⚠️ NOTE: The appointment date has already passed. "
            "When you reach Step 3, proactively inform the customer and offer to reschedule."
            if appt_is_past
            else ""
        )

        super().__init__(
            language=language,
            instructions=REMINDER_AGENT_PROMPT.format(
                name=name,
                gender=gender,
                language=language,
                current_time=current_time,
                customer_name=customer_name,
                appt_summary=appt_summary,
                past_note=past_note,
            ),
        )

    # -----------------------------------------------------------------------
    # Appointment details
    # -----------------------------------------------------------------------

    @function_tool()
    async def get_appointment_details(self, context: RunContext) -> dict[str, Any]:
        """Retrieve the customer's appointment details on file.

        Call this in Step 3 after identity verification to read out the appointment.
        Also checks whether the appointment date has already passed.
        """
        self._current_step = "appointment_details"

        if not self.appointment:
            return {
                "appointment_found": False,
                "next_step": "escalate",
            }

        appt_type = self.appointment.get("appointment_type", "")
        appt_date_str = self.appointment.get("date", "")
        appt_time = self.appointment.get("time", "")
        address = self.appointment.get("address", "")
        pin_code = self.appointment.get("pin_code", "")
        exam_type = self.appointment.get("exam_type", "")

        appt_is_past = False
        if appt_date_str:
            try:
                appt_is_past = date.fromisoformat(appt_date_str) < date.today()
            except ValueError:
                pass

        type_label = "Home Visit" if appt_type == "home" else "Diagnostic Center Visit"

        # Cache existing appointment details for potential reschedule reuse
        self._booking_context.update(
            {
                "appointment_type": appt_type,
                "address": address,
                "pin_code": pin_code,
                "exam_type": exam_type,
            }
        )

        return {
            "appointment_found": True,
            "appointment_type": type_label,
            "raw_type": appt_type,
            "date": appt_date_str,
            "time": appt_time,
            "address": address,
            "pin_code": pin_code,
            "exam_type": exam_type,
            "appointment_is_past": appt_is_past,
            "next_step": "reschedule" if appt_is_past else "confirm_convenience",
        }

    # -----------------------------------------------------------------------
    # Home visit address
    # -----------------------------------------------------------------------

    @function_tool()
    async def save_home_visit_address(
        self,
        context: RunContext,
        house: str,
        street: str,
        area: str,
        city: str,
        pin_code: str,
        landmark: str = "",
    ) -> dict[str, Any]:
        """Save a new home address for a rescheduled home visit.

        Call this after the customer has confirmed all address components during reschedule.

        Args:
            house: House or flat number.
            street: Street or road name.
            area: Locality or neighbourhood.
            city: City name.
            pin_code: 6-digit Indian postal code.
            landmark: Optional nearby landmark for the technician.
        """
        await asyncio.sleep(2)
        parts = [house, street, area, city, f"PIN {pin_code}"]
        if landmark:
            parts.append(f"Near {landmark}")
        full_address = ", ".join(p.strip() for p in parts if p.strip())

        self._booking_context.update(
            {
                "address": full_address,
                "pin_code": pin_code,
                "appointment_type": "home",
                "exam_type": "Home Collection",
            }
        )
        return {
            "saved": True,
            "full_address": full_address,
            "next_step": "collect_datetime",
        }

    # -----------------------------------------------------------------------
    # Center visit tools
    # -----------------------------------------------------------------------

    @function_tool()
    async def search_nearby_centers(
        self, context: RunContext, location: str
    ) -> dict[str, Any]:
        """Find nearby diagnostic centers for the customer's preferred area or city.

        Args:
            location: Area name, locality, or city provided by the customer.
        """
        await asyncio.sleep(2)
        self._current_step = "center_search"
        key = normalize_lookup_key(location)

        matches = [
            {"id": cid, **info}
            for cid, info in DIAGNOSTIC_CENTERS.items()
            if key in normalize_lookup_key(info["city"])
            or key in normalize_lookup_key(info["area"])
        ]

        if not matches:
            matches = [
                {"id": cid, **info}
                for cid, info in DIAGNOSTIC_CENTERS.items()
                if info["city"] == "Bangalore"
            ]

        return {"centers": matches[:3], "next_step": "center_select"}

    @function_tool()
    async def select_center(
        self, context: RunContext, center_id: str
    ) -> dict[str, Any]:
        """Confirm the customer's chosen diagnostic center for the rescheduled visit.

        Args:
            center_id: The center identifier (e.g. C001).
        """
        await asyncio.sleep(2)
        self._current_step = "center_select"
        center = DIAGNOSTIC_CENTERS.get(center_id.upper())
        if center is None:
            center_id = "C001"
            center = DIAGNOSTIC_CENTERS[center_id]

        self._booking_context.update(
            {
                "appointment_type": "center",
                "exam_type": "Medical Examination",
                "center_id": center_id,
                "center_name": center["name"],
                "address": center["address"],
            }
        )
        return {"selected": True, "center": center, "next_step": "collect_datetime"}

    # -----------------------------------------------------------------------
    # Reschedule
    # -----------------------------------------------------------------------

    @function_tool()
    async def reschedule_appointment_booking(
        self,
        context: RunContext,
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

        phone = _normalize_phone(self.validation_details.get("phone_number", ""))
        dob = _normalize_dob(
            self.validation_details.get("dob", "")
        ) or self.validation_details.get("dob", "")

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
        self, context: RunContext, preferred_time: str = ""
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

    @function_tool()
    async def mark_wrong_number(self, context: RunContext) -> dict[str, Any]:
        """Mark this contact as a wrong number and update the record.

        Call immediately when the answering party confirms they are not the intended customer.
        """
        await asyncio.sleep(2)
        return {"updated": True, "status": "wrong_number", "next_step": "close"}

    @function_tool()
    async def mark_exam_completed(self, context: RunContext) -> dict[str, Any]:
        """Mark the medical examination as already completed by the customer.

        Call when the customer reports they have already done the exam.
        """
        await asyncio.sleep(2)
        return {"updated": True, "status": "exam_completed", "next_step": "close"}

    @function_tool()
    async def get_call_status(self, context: RunContext) -> dict[str, Any]:
        """Return the current step and all data collected so far in this call.

        Call this whenever you are unsure which step you are on, what information
        has already been gathered, or what to do next.
        """
        await asyncio.sleep(2)
        step_next_map: dict[str, str] = {
            "greeting": "introduction",
            "introduction": "appointment_details",
            "appointment_details": "preparation_reminder",
            "preparation_reminder": "confirm_convenience",
            "confirm_convenience": "close or reschedule",
            "center_search": "center_select",
            "center_select": "collect_datetime",
            "reschedule_booking": "close",
            "close": "done",
        }

        return {
            "current_step": self._current_step,
            "next_step": step_next_map.get(self._current_step, "unknown"),
            "dob_attempts_used": self._dob_attempts,
            "collected": {k: v for k, v in self._booking_context.items()},
        }
