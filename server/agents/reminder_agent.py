from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any

from livekit.agents import RunContext, function_tool
from zoneinfo import ZoneInfo

from .base import ScenarioAgent
from client.appointment_db import (
    get_daily_booking_count,
    get_latest_confirmed_booking,
    get_user,
    is_slot_taken,
    reschedule_appointment,
)

from .tools import get_centers_by_pin, hangup_call


logger = logging.getLogger(__name__)

INDIA_TZ = ZoneInfo("Asia/Kolkata")
SLOT_INTERVAL_MINUTES = 30
MAX_BOOKING_WINDOW_DAYS = 30
APPOINTMENT_START_HOUR = 9
APPOINTMENT_END_HOUR = 18


def _normalize_phone(phone_number: str) -> str:
    digits = re.sub(r"\D", "", phone_number or "")
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if phone_number.startswith("+") and len(digits) == 12 and digits.startswith("91"):
        return phone_number
    return f"+{digits}" if digits else ""


def _parse_dob(dob: str) -> datetime | None:
    formats = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y")
    raw = (dob or "").strip()
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=INDIA_TZ)
        except ValueError:
            continue
    return None


def _parse_booking_date(date_value: str) -> datetime | None:
    raw = (date_value or "").strip().lower()
    now = datetime.now(INDIA_TZ)
    if raw == "today":
        return now
    if raw == "tomorrow":
        return now + timedelta(days=1)

    formats = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y")
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=INDIA_TZ)
        except ValueError:
            continue
    return None


def _parse_booking_time(time_value: str) -> tuple[int, int] | None:
    raw = (time_value or "").strip().lower()
    formats = ("%H:%M", "%I:%M %p", "%I %p")
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.hour, parsed.minute
        except ValueError:
            continue
    return None


def _normalize_exam_type(exam_type: str) -> str:
    normalized = (exam_type or "").strip().lower()
    if normalized in {"home", "home collection", "home sample collection"}:
        return "Home Collection"
    if normalized in {"center", "centre", "center visit", "visit to medical center"}:
        return "Center Visit"
    return ""


def _valid_slots_for_exam_type(exam_type: str) -> list[str]:
    start_hour = APPOINTMENT_START_HOUR
    end_hour = APPOINTMENT_END_HOUR
    if exam_type == "Home Collection":
        start_hour = 8
        end_hour = 17

    slots: list[str] = []
    for hour in range(start_hour, end_hour):
        for minute in (0, SLOT_INTERVAL_MINUTES):
            slots.append(f"{hour:02d}:{minute:02d}")
    return slots


def _is_slot_taken(date: str, time: str, exam_type: str) -> bool:
    return is_slot_taken(
        appointment_date=date, appointment_time=time, exam_type=exam_type
    )


def _suggest_next_slots(date_str: str, exam_type: str, limit: int = 3) -> list[str]:
    options: list[str] = []
    now = datetime.now(INDIA_TZ)
    is_today = date_str == now.date().isoformat()

    for slot in _valid_slots_for_exam_type(exam_type):
        if is_today:
            slot_dt = datetime.combine(
                now.date(),
                datetime.strptime(slot, "%H:%M").time(),
                tzinfo=INDIA_TZ,
            )
            if slot_dt < now + timedelta(hours=2):
                continue

        if not _is_slot_taken(date=date_str, time=slot, exam_type=exam_type):
            options.append(slot)
        if len(options) >= limit:
            break
    return options


def _is_within_booking_window(appointment_dt: datetime) -> bool:
    now = datetime.now(INDIA_TZ)
    window_end = now + timedelta(days=MAX_BOOKING_WINDOW_DAYS)
    return now <= appointment_dt <= window_end


def _is_valid_same_day_timing(appointment_dt: datetime) -> bool:
    now = datetime.now(INDIA_TZ)
    if appointment_dt.date() != now.date():
        return True
    return appointment_dt >= now + timedelta(hours=2)


def _build_appointment_id(date_str: str, time_str: str, exam_type: str) -> str:
    mode = "HC" if exam_type == "Home Collection" else "CV"
    sequence = get_daily_booking_count(appointment_date=date_str) + 1
    compact_date = date_str.replace("-", "")
    compact_time = time_str.replace(":", "")
    return f"APT-{compact_date}-{compact_time}-{mode}-{sequence:04d}"


class ReminderAgent(ScenarioAgent):
    def __init__(self, name, gender, language, validation_details, appointment) -> None:
        appointment_info = "No active appointment found."
        if appointment:
            appointment_info = f"""
            - Date: {appointment.get("appointment_date")}
            - Time: {appointment.get("appointment_time")}
            - Type: {appointment.get("exam_type")}
            - Location: {appointment.get("address", "Not provided")}
            """

        super().__init__(
            instructions=f"""
            ROLE:
            You are {name}, a {gender} Scheduling Assistant. You help people confirm and reschedule medical appointments for their insurance process in India.
            You are based out of India and talk to Indian native people so you must make sure you sound like an Indian Doctor with a thick accent.
            User has selected {language} as their primary language. YOU MUST CONVERSE IN {language}.
            
            
            RULES:
            - YOU MUST NEVER CALL END_CALL FUNCTION WITHOUT CALLING GOODBYE FUNCTION FIRST. ALWAYS CALL GOODBYE FUNCTION TO SAY FAREWELL MESSAGES TO THE USER AND THEN CALL END_CALL TO HANG UP THE CALL. DO NOT END THE CALL UNLESS THE USER HAS INDICATED THEY HAVE NO MORE QUESTIONS OR NEEDS, SUCH AS BY SAYING "NO THANKS", "THAT'S ALL", "GOODBYE", "THANK YOU", OR SIMILAR PHRASES.
            - YOU MUST REPEAT THE RESPONSE FROM GOODBYE FUNCTION IN YOUR OWN WORDS TO THE USER IN A FRIENDLY MANNER AND THEN CALL END_CALL TO END THE CALL AFTER THAT. DO NOT CALL END_CALL WITHOUT SAYING GOODBYE MESSAGES TO THE USER.
            - You must go through all the questions.
            - Please respond in a friendly, conversational tone but not too zesty.
            - Use everyday simple vocabulary that easy to understand for people of all ages.
            - Paragraphs are only 1-2 sentences long.
            - User can provide or correct information in any order, so be sure to ask all the questions and confirm the answers at the end.
            - Make sure the wordings are less predictable, has high burstiness, and high stylometric.
            - Wait after each question, and give ample time for user to respond to your questions and dont group the questions together.
            - Avoid translating abbreviations unless medically required; preserve global consistency.
            - YOU MUST NOT translate day to day terms like quality, date of birth, audit, gender, height, weight, diabetes, heart issues, family history etc. and use the English terms even when conversing in other languages.
            - Ensure that key medical terms (e.g., BP for Blood Pressure) remain consistent across all supported languages.
            - Provide confirmation after each question and once completed conclude the call after greeting the user.
            - Incase the answer is not clear, ask one brief clarifying question to get the answer. Do not ask more than one clarifying question.
            - You must use grammatically correct native-language gender forms based on your own gender ({gender}).
            - When speaking Hindi or other Indian languages, all verbs, pronouns, honorifics, and sentence endings MUST match the assistant's gender naturally.
            - NEVER mix masculine and feminine forms incorrectly.     
            - If gender = female:
            - Use feminine verb forms and feminine self-references.
            - Examples:
                - "मैं पूछूंगी"
                - "मैं आपकी मदद करूंगी"
                - "मैं आई हूँ"
                - "मैं समझ गई"
                - "मैं तैयार हूँ"

            - If gender = male:
            - Use masculine verb forms and masculine self-references.
            - Examples:
                - "मैं पूछूंगा"
                - "मैं आपकी मदद करूंगा"
                - "मैं आया हूँ"
                - "मैं समझ गया"
                - "मैं तैयार हूँ"

            Today's Date is {datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()}
            
            KEY GUIDELINES:
            - Use a natural, friendly Indian tone with a professional yet conversational style.
            - Keep responses short (1-2 sentences per paragraph).
            - Use everyday vocabulary.
            - DO NOT translate key terms: date of birth, gender, height, weight, diabetes, heart issues, family history, BP, Home Collection, Center Visit. Use English terms.
            - Follow assistant's gender ({gender}) for correct verb forms and honorifics in {language}.
            
            APPOINTMENT DETAILS FOR CALLER:
            {appointment_info}

            VALIDATION DETAILS FOR CALLER:
            {validation_details}

            CONVERSATION GUIDELINES:

            "Hi, this is {name}. I'm calling to confirm that your medical examination appointment is scheduled for {appointment.get("appointment_date") if appointment else "[DATE]"} at {appointment.get("appointment_time") if appointment else "[TIME]"}."

            "Your appointment details are as follows:
            - Date: {appointment.get("appointment_date") if appointment else "[DATE]"}
            - Time: {appointment.get("appointment_time") if appointment else "[TIME]"}
            - Type: {appointment.get("exam_type") if appointment else "[TYPE]"}"

            "When the technician arrives at your location, kindly call back on this number. Please note that the medical process will be conducted and recorded through a video call. A video call link will be shared with you through SMS or WhatsApp."

            "During the process:
            - Your height and weight will be measured
            - Blood pressure (BP) will be checked
            - Abdomen measurement will be conducted
            - Blood sample collection will be completed"

            "Our doctor will also join the video call to verify the procedure and ask a few health-related questions."

            "Please ensure:
            - Your phone is available during the appointment
            - Internet connection is active for the video call
            - You follow any fasting instructions shared earlier"

            "May I confirm if you will be available for the appointment on {appointment.get("appointment_date") if appointment else "[DATE]"} at {appointment.get("appointment_time") if appointment else "[TIME]"}?"

            IF CUSTOMER CONFIRMS:
            - Call goodbye tool and end the call after that.

            IF CUSTOMER ASKS TO RESCHEDULE:
            - Inform them you can help.
            - Ask for new date and time.
            - Use `reschedule_appointment_tool` to finalize.
            - Confirm the new details with the user.
            - Call goodbye tool and end the call after that.

            IF CUSTOMER IS FRUSTRATED:
            - Offer to transfer to a human agent using `transfer_to_human`.
 """
        )
        self.validation_details = validation_details
        self.appointment = appointment

    def _validate_and_check_slot(
        self,
        date: str,
        time: str,
        exam_type: str,
    ) -> dict[str, Any]:
        """Common logic to validate date, time, and slot availability."""
        normalized_exam_type = _normalize_exam_type(exam_type)
        if not normalized_exam_type:
            return {
                "result": "failed",
                "error": "Invalid exam type. Use Home Collection or Center Visit.",
            }

        parsed_date = _parse_booking_date(date)
        if parsed_date is None:
            return {
                "result": "failed",
                "error": "Invalid date format. Use DD-MM-YYYY or YYYY-MM-DD.",
            }

        parsed_time = _parse_booking_time(time)
        if parsed_time is None:
            return {
                "result": "failed",
                "error": "Invalid time format. Use HH:MM (24-hour) or 10:30 AM format.",
            }

        hour, minute = parsed_time
        if minute not in {0, SLOT_INTERVAL_MINUTES}:
            return {
                "result": "failed",
                "error": "Appointments are available every 30 minutes only.",
            }

        date_obj = parsed_date.date()
        appointment_dt = datetime(
            year=date_obj.year,
            month=date_obj.month,
            day=date_obj.day,
            hour=hour,
            minute=minute,
            tzinfo=INDIA_TZ,
        )

        if not _is_within_booking_window(appointment_dt):
            return {
                "result": "failed",
                "error": f"Appointments can only be booked within the next {MAX_BOOKING_WINDOW_DAYS} days.",
            }

        if not _is_valid_same_day_timing(appointment_dt):
            return {
                "result": "failed",
                "error": "Same-day appointments require at least a 2-hour lead time.",
            }

        normalized_time = f"{hour:02d}:{minute:02d}"
        date_str = date_obj.isoformat()
        valid_slots = _valid_slots_for_exam_type(normalized_exam_type)
        if normalized_time not in valid_slots:
            return {
                "result": "failed",
                "error": "Requested slot is outside service hours for this exam type.",
            }

        if _is_slot_taken(
            date=date_str, time=normalized_time, exam_type=normalized_exam_type
        ):
            return {
                "result": "failed",
                "error": "Requested slot is already booked.",
                "alternate_slots": _suggest_next_slots(
                    date_str=date_str, exam_type=normalized_exam_type
                ),
            }

        return {
            "result": "success",
            "date_str": date_str,
            "normalized_time": normalized_time,
            "normalized_exam_type": normalized_exam_type,
        }

    @function_tool()
    async def validate_user(
        self,
        context: RunContext,
        phone_number: str,
        dob: str,
    ) -> dict[str, Any]:
        """Validate user identity using mobile number and date of birth.

        Args:
            phone_number: User mobile number in India format.
            dob: Date of birth in YYYY-MM-DD or DD-MM-YYYY.
        """
        normalized_phone = _normalize_phone(phone_number)
        parsed_dob = _parse_dob(dob)

        if not re.fullmatch(r"\+91[6-9]\d{9}", normalized_phone):
            return {
                "is_registered": False,
                "is_valid": False,
                "error": "Please provide a valid 10-digit Indian mobile number.",
                "phone_number": normalized_phone,
            }

        if parsed_dob is None:
            return {
                "is_registered": False,
                "is_valid": False,
                "error": "Date of birth format is invalid. Use DD-MM-YYYY or YYYY-MM-DD.",
                "phone_number": normalized_phone,
            }

        today = datetime.now(INDIA_TZ).date()
        dob_date = parsed_dob.date()
        age_years = int((today - dob_date).days / 365.25)
        if dob_date >= today or age_years < 18 or age_years > 120:
            return {
                "is_registered": False,
                "is_valid": False,
                "error": "Please provide a valid adult date of birth.",
                "phone_number": normalized_phone,
            }

        # Validate against provided session details
        expected_phone = _normalize_phone(
            self.validation_details.get("phone_number", "")
        )
        expected_dob = self.validation_details.get("dob", "")

        if normalized_phone[-10:] != expected_phone[-10:]:
            return {
                "is_registered": False,
                "is_valid": True,
                "error": f"The mobile number {phone_number} is not registered for this medical scheduling session.",
                "phone_number": normalized_phone,
            }

        if dob_date.isoformat() != expected_dob:
            return {
                "is_registered": False,
                "is_valid": True,
                "error": "The date of birth provided does not match our records.",
                "phone_number": normalized_phone,
                "dob": dob_date.isoformat(),
            }

        expected_profile = get_user(
            normalized_phone) or self.validation_details
        active_booking = get_latest_confirmed_booking(
            phone_number=normalized_phone,
            dob=dob_date.isoformat(),
        )

        return {
            "is_registered": True,
            "is_valid": True,
            "phone_number": normalized_phone,
            "dob": dob_date.isoformat(),
            "profile": expected_profile,
            "has_active_booking": active_booking is not None,
            "active_booking": active_booking or {},
        }

    @function_tool()
    async def get_medical_center(
        self,
        context: RunContext,
        pin_code: str,
    ) -> dict[str, Any]:
        """Get nearest medical center based on the pincode

        Args:
            pin_code: pincode to find nearest medical center.
        """
        normalized_pin = re.sub(r"\D", "", pin_code or "")
        if not re.fullmatch(r"\d{6}", normalized_pin):
            return {
                "result": "failed",
                "error": "Invalid pin code. Please provide a 6-digit Indian pincode.",
            }

        center_response = get_centers_by_pin(normalized_pin)
        if center_response.get("result") == "failed":
            return center_response

        centers = center_response.get("options", [])
        if not centers:
            return {
                "result": "success",
                "pin_code": normalized_pin,
                "options": [],
                "message": "No mapped center for this pincode. Offer Home Collection or ask for nearby pincode.",
            }

        return {
            "result": "success",
            "pin_code": normalized_pin,
            "options": centers,
            "source": center_response.get("source", "serpapi"),
        }

    @function_tool()
    async def reschedule_appointment_tool(
        self,
        context: RunContext,
        phone_number: str,
        dob: str,
        new_date: str,
        new_time: str,
        exam_type: str,
        pin_code: str = "",
        address: str = "",
    ) -> dict[str, Any]:
        """Reschedule an existing appointment to a new date and time.

        Args:
            phone_number: User mobile number in India format.
            dob: Date of birth in YYYY-MM-DD or DD-MM-YYYY.
            new_date: New appointment date in YYYY-MM-DD or DD-MM-YYYY.
            new_time: New appointment time in HH:MM format.
            exam_type: Home Collection or Center Visit.
            pin_code: Optional 6-digit pincode.
            address: Optional address for Home Collection.
        """
        user_validation = await self.validate_user(
            context=context,
            phone_number=phone_number,
            dob=dob,
        )  # type: ignore
        if not user_validation.get("is_valid"):
            return {
                "result": "failed",
                "error": user_validation.get("error", "User validation failed."),
            }

        # If exam_type is not provided, try to get it from the active booking
        if not exam_type and user_validation.get("has_active_booking"):
            exam_type = user_validation["active_booking"].get("exam_type", "")

        slot_check = self._validate_and_check_slot(
            date=new_date,
            time=new_time,
            exam_type=exam_type,
        )
        if slot_check["result"] == "failed":
            return slot_check

        date_str = slot_check["date_str"]
        normalized_time = slot_check["normalized_time"]
        normalized_exam_type = slot_check["normalized_exam_type"]

        try:
            new_appointment = reschedule_appointment(
                phone_number=user_validation["phone_number"],
                dob=user_validation["dob"],
                new_date=date_str,
                new_time=normalized_time,
                exam_type=normalized_exam_type,
                pin_code=re.sub(r"\D", "", pin_code or ""),
                address=address.strip(),
            )
        except Exception as e:
            logger.exception("Reschedule failed: %s", e)
            return {
                "result": "failed",
                "error": f"Failed to reschedule appointment: {e}",
            }

        if new_appointment.get("result") == "failed":
            return new_appointment

        return {
            "result": "success",
            "message": f"Appointment successfully rescheduled to {date_str} at {normalized_time}.",
            "new_appointment": new_appointment,
            "instructions": [
                "Please update your calendar with the new appointment details.",
                "You will receive updated confirmation via SMS or WhatsApp.",
            ],
        }

    @function_tool()
    async def transfer_to_human(self, context: RunContext) -> str:
        """Transfer the call to a human agent if you cannot assist the user or if they are frustrated."""
        return "Transferring you to a human agent. Please stay on the line."

    @function_tool()
    async def goodbye(
        self,
        context: RunContext,
    ) -> str:
        """
        You should call this function when the user indicates they have no more questions or needs, such as by saying "no thanks", "that's all", "goodbye", "thank you", or similar phrases. When you call this function, you should first generate a friendly goodbye message to the user, such as "Thank you for your time. Have a great day ahead!" and then end the call cleanly.
         - Generate a friendly goodbye message to the user.
         - Do not call this function unless the user has indicated they have no more questions or needs
         - After generating the goodbye message, end the call cleanly.
        """

        async def _end_after_delay():
            await asyncio.sleep(9)
            context.session.shutdown()
            await hangup_call()

        asyncio.ensure_future(_end_after_delay())
        return "Say have a nice day to the user in a friendly manner and end the call."
