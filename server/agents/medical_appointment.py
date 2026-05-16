from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from livekit.agents import RunContext, function_tool
from sqlalchemy.exc import IntegrityError
from zoneinfo import ZoneInfo

from .base import ScenarioAgent
from client.appointment_db import (
    create_appointment,
    get_daily_booking_count,
    get_latest_confirmed_booking,
    get_user,
    is_slot_taken,
)

from .tools import get_centers_by_pin


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


class MedicalAppointmentAgent(ScenarioAgent):
    def __init__(self, name, gender, language, validation_details) -> None:
        super().__init__(
            instructions=f"""
            ROLE:
            You are {name}, a {gender} Scheduling Assistant. You help people schedule medical appointments for their insurance process in India.
            You are based out of India and talk to Indian native people so you must make sure you sound like an Indian Doctor with a thick accent.
            User has selected {language} as their primary language. YOU MUST CONVERSE IN {language}.
            
            RULES:
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
            
            CONVERSATION GUIDELINES:

            "Hi, this is {name}, this is regarding your medical appointment for insurance."

            ID VERIFICATION CATEGORY:

            1. Could you confirm your date of birth ?
            2. What is your registered phone number?

            - Call `validate_user` to validate the user's identity based on their responses. If validation fails, politely inform the user and ask for clarification.
            
            3. Ask if the user would like a "Home Collection" or "Center Visit".
            4. If Home Collection: Ask for their area pincode, then full address and a landmark.
            5. If Center Visit: Ask for their pincode, call `get_medical_center`, and present available centers for them to choose from.
            6. Ask for their preferred date and time for the appointment. 
            7. Once all details are gathered, call `book_appointment` to finalize the booking.
            8. Confirm the appointment details with the user, mention the medical check process (BP, weight, etc.), and ask if they need any further assistance.
            9. End Call: Say "Thank You" and then call the `end_call` tool.

            RULES:
            - Wait for user response after each question.
            - Confirm information provided by the user before moving to the next step.
            - If an answer is unclear, ask exactly one brief clarifying question.
            - Before each tool call, inform the user about what you are going to do (e.g., "Let me check available slots for that date."). 
            
            TOOLS:
            - validate_user: To check user registration.
            - get_medical_center: To find centers near a pincode.
            - book_appointment: To finalize the booking.
            - end_call: To hang up after "Thank You".
"""
        )
        self.validation_details = validation_details

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

        if normalized_phone != expected_phone:
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
    async def book_appointment(
        self,
        context: RunContext,
        phone_number: str,
        dob: str,
        date: str,
        time: str,
        exam_type: str,
        pin_code: str = "",
        address: str = "",
        center_name: str = "",
    ) -> dict[str, Any]:
        """Reserve an appointment for a caller.

        Use this after confirming the Exam Type and preferred date and time. The tool checks the
        requested day and slot against the available booking data, returns a confirmed
        appointment when possible, and suggests alternate slots when the exact request
        is not available.

        Args:
            phone_number: phone number of the person who wants the booking.
            dob: Date of birth in DD-MM-YYYY or YYYY-MM-DD.
            date: Requested date in DD-MM-YYYY or YYYY-MM-DD.
            time: Preferred time slot to reserve (HH:MM).
            exam_type: Home Collection / Center Visit.
            pin_code: Optional 6-digit pincode.
            address: Required for Home Collection.
            center_name: Optional center name for Center Visit.
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
                "details": user_validation,
            }

        normalized_exam_type = _normalize_exam_type(exam_type)
        if not normalized_exam_type:
            return {
                "result": "failed",
                "error": "Invalid exam type. Please choose Home Collection or Center Visit.",
            }

        parsed_date = _parse_booking_date(date)
        if parsed_date is None:
            return {
                "result": "failed",
                "error": "Invalid date format. Please use DD-MM-YYYY or YYYY-MM-DD.",
            }

        parsed_time = _parse_booking_time(time)
        if parsed_time is None:
            return {
                "result": "failed",
                "error": "Invalid time format. Please use HH:MM (24-hour) or 10:30 AM format.",
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
                "service_hours": {
                    "exam_type": normalized_exam_type,
                    "first_slot": valid_slots[0],
                    "last_slot": valid_slots[-1],
                },
            }

        if normalized_exam_type == "Home Collection" and not address.strip():
            return {
                "result": "failed",
                "error": "Address is required for Home Collection appointments.",
            }

        normalized_pin = re.sub(r"\D", "", pin_code or "")
        if normalized_pin and not re.fullmatch(r"\d{6}", normalized_pin):
            return {
                "result": "failed",
                "error": "Pin code must be a 6-digit number.",
            }

        if normalized_exam_type == "Center Visit":
            if not center_name.strip():
                return {
                    "result": "failed",
                    "error": "Medical center name is required for Center Visit.",
                }
            if normalized_pin:
                center_result = get_centers_by_pin(normalized_pin)
                if center_result.get("result") == "success":
                    available_centers = [
                        c["name"] for c in center_result.get("options", [])
                    ]
                    if (
                        available_centers
                        and center_name.strip() not in available_centers
                    ):
                        return {
                            "result": "failed",
                            "error": "Requested center is not available for the provided pincode.",
                            "available_centers": available_centers,
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

        appointment_id = _build_appointment_id(
            date_str=date_str,
            time_str=normalized_time,
            exam_type=normalized_exam_type,
        )

        appointment_type = (
            "home" if normalized_exam_type == "Home Collection" else "center"
        )
        final_address = address.strip()
        if appointment_type == "center" and center_name:
            final_address = (
                f"{center_name.strip()} - {final_address}"
                if final_address
                else center_name.strip()
            )

        booking = {
            "appointment_id": appointment_id,
            "phone_number": user_validation["phone_number"],
            "dob": user_validation["dob"],
            "full_name": user_validation.get("profile", {}).get(
                "full_name", "Unknown User"
            ),
            "date": date_str,
            "time": normalized_time,
            "appointment_type": appointment_type,
            "exam_type": normalized_exam_type,
            "pin_code": normalized_pin,
            "address": final_address,
            "created_at": datetime.now(INDIA_TZ).isoformat(),
        }
        try:
            booking = create_appointment(booking)
        except IntegrityError as e:
            print(f"Database error during booking: {e}")
            return {
                "result": "failed",
                "error": "Requested slot is already booked.",
                "alternate_slots": _suggest_next_slots(
                    date_str=date_str, exam_type=normalized_exam_type
                ),
            }

        return {
            "result": "success",
            "message": "Appointment booked successfully. Please arrive or be available 10 minutes early.",
            "booking": booking,
            "instructions": [
                "Carry a valid photo ID.",
                "Stay hydrated; fasting is not required unless informed separately.",
                "You may receive confirmation on SMS or WhatsApp.",
            ],
        }
