from __future__ import annotations

import asyncio
import logging
import re
import random
import uuid
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from livekit.agents import RunContext, function_tool

from client.appointment_db import create_appointment
from agents.base import ScenarioAgent
from agents.common import normalize_lookup_key
from agents.lib import MAX_MEDICAL_APPOINTMENT_PROMPT, MEDICAL_APPOINTMENT_PROMPT

logger = logging.getLogger(__name__)

INDIA_TZ = ZoneInfo("Asia/Kolkata")
SLOT_INTERVAL_MINUTES = 30
MAX_BOOKING_WINDOW_DAYS = 30
APPOINTMENT_START_HOUR = 9
APPOINTMENT_END_HOUR = 18

# ---------------------------------------------------------------------------
# Hardcoded demo data
# ---------------------------------------------------------------------------

DIAGNOSTIC_CENTERS: dict[str, dict[str, str]] = {
    "C001": {
        "name": "Apollo Diagnostics",
        "area": "Koramangala",
        "city": "Bangalore",
        "address": "45 Koramangala Industrial Layout, Bangalore – 560034",
        "distance": "2.1 km",
    },
    "C002": {
        "name": "SRL Diagnostics",
        "area": "Indiranagar",
        "city": "Bangalore",
        "address": "12th Main, HAL 2nd Stage, Indiranagar, Bangalore – 560038",
        "distance": "3.4 km",
    },
    "C003": {
        "name": "Metropolis Healthcare",
        "area": "Whitefield",
        "city": "Bangalore",
        "address": "Prestige Tech Park, Whitefield, Bangalore – 560066",
        "distance": "5.7 km",
    },
    "C004": {
        "name": "Dr Lal PathLabs",
        "area": "Andheri",
        "city": "Mumbai",
        "address": "Silver Arcade, J.B. Nagar, Andheri East, Mumbai – 400059",
        "distance": "1.8 km",
    },
    "C005": {
        "name": "Thyrocare Technologies",
        "area": "Bandra",
        "city": "Mumbai",
        "address": "Plot 1, Bandra Kurla Complex, Bandra East, Mumbai – 400051",
        "distance": "3.2 km",
    },
    "C006": {
        "name": "Suburban Diagnostics",
        "area": "Powai",
        "city": "Mumbai",
        "address": "Hiranandani Business Park, Powai, Mumbai – 400076",
        "distance": "4.5 km",
    },
    "C007": {
        "name": "Pathkind Labs",
        "area": "Lajpat Nagar",
        "city": "Delhi",
        "address": "Central Market, Lajpat Nagar II, New Delhi – 110024",
        "distance": "2.0 km",
    },
    "C008": {
        "name": "Fortis Diagnostics",
        "area": "Vasant Kunj",
        "city": "Delhi",
        "address": "Fortis Healthcare Complex, Vasant Kunj, New Delhi – 110070",
        "distance": "3.7 km",
    },
    "C009": {
        "name": "Vijaya Diagnostic Centre",
        "area": "Banjara Hills",
        "city": "Hyderabad",
        "address": "Road No. 2, Banjara Hills, Hyderabad – 500034",
        "distance": "2.6 km",
    },
    "C010": {
        "name": "Medall Diagnostics",
        "area": "T. Nagar",
        "city": "Chennai",
        "address": "45 Venkatnarayana Road, T. Nagar, Chennai – 600017",
        "distance": "1.5 km",
    },
}

# Month name → zero-padded number
_MONTH_MAP: dict[str, str] = {
    "january": "01",
    "jan": "01",
    "february": "02",
    "feb": "02",
    "march": "03",
    "mar": "03",
    "april": "04",
    "apr": "04",
    "may": "05",
    "june": "06",
    "jun": "06",
    "july": "07",
    "jul": "07",
    "august": "08",
    "aug": "08",
    "september": "09",
    "sep": "09",
    "sept": "09",
    "october": "10",
    "oct": "10",
    "november": "11",
    "nov": "11",
    "december": "12",
    "dec": "12",
}


_TIME_WORDS: dict[str, str] = {
    "morning": "09:00",
    "noon": "12:00",
    "afternoon": "13:00",
    "evening": "17:00",
    "night": "19:00",
    "midnight": "00:00",
}

INSURANCE_COMPANIES = [
    "Axis Max-Life Insurance",
    "HDFC Life Insurance",
    "ICICI Prudential Life Insurance",
]

ADDRESSES = [
    {
        "pin_code": "560034",
        "address": "45 Koramangala Industrial Layout, Bangalore",
    },
    {
        "pin_code": "560038",
        "address": "12th Main, HAL 2nd Stage, Indiranagar, Bangalore",
    },
    {
        "pin_code": "560066",
        "address": "Prestige Tech Park, Whitefield, Bangalore",
    },
    {
        "pin_code": "400059",
        "address": "Silver Arcade, J.B. Nagar, Andheri East, Mumbai",
    },
    {
        "pin_code": "400051",
        "address": "Plot 1, Bandra Kurla Complex, Bandra East, Mumbai",
    },
    {
        "pin_code": "400076",
        "address": "Hiranandani Business Park, Powai, Mumbai",
    },
    {
        "pin_code": "110024",
        "address": "Central Market, Lajpat Nagar II, New Delhi",
    },
    {
        "pin_code": "110070",
        "address": "Fortis Healthcare Complex, Vasant Kunj, New Delhi",
    },
    {
        "pin_code": "500034",
        "address": "Road No. 2, Banjara Hills, Hyderabad",
    },
]


def _normalize_appointment_date(raw: str) -> str:
    """Normalize a spoken or typed appointment date to ISO YYYY-MM-DD.

    Handles:
      - YYYY-MM-DD (ISO, pass-through)
      - DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
      - "25th May", "25 May 2026", "May 25", "May 25, 2026"
      - Relative: "today", "tomorrow", "day after tomorrow"
      - Weekday: "Monday", "next Monday", "coming Friday"

    Returns the original string unchanged if it cannot be parsed.
    """
    s = raw.strip()
    s_lower = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s.lower())
    today = datetime.now(INDIA_TZ).date()

    # Already ISO YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s_lower):
        return s_lower

    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", s_lower)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return d.isoformat()
        except ValueError:
            pass

    # Relative dates
    relative: dict[str, date] = {
        "today": today,
        "tomorrow": today + timedelta(days=1),
        "day after tomorrow": today + timedelta(days=2),
    }
    if s_lower in relative:
        return relative[s_lower].isoformat()

    # "next <weekday>" or "coming <weekday>" or bare weekday name
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    for i, day_name in enumerate(weekdays):
        for prefix in ("next ", "coming ", ""):
            if s_lower == f"{prefix}{day_name}":
                days_ahead = i - today.weekday()
                if days_ahead <= 0 or prefix in ("next ", "coming "):
                    days_ahead += 7
                return (today + timedelta(days=days_ahead)).isoformat()

    # Spoken: "25 may", "25 may 2026", "may 25", "may 25 2026"
    m = re.search(
        r"(\d{1,2})\s+([a-z]+)(?:\s+(\d{4}))?$|^([a-z]+)\s+(\d{1,2})(?:[,\s]+(\d{4}))?$",
        s_lower,
    )
    if m:
        if m.group(1):
            day_s, month_s = m.group(1), m.group(2)
            year_s = m.group(3) or str(today.year)
        else:
            month_s, day_s = m.group(4), m.group(5)
            year_s = m.group(6) or str(today.year)
        month_num = _MONTH_MAP.get(month_s)
        if month_num:
            try:
                d = date(int(year_s), int(month_num), int(day_s))
                if d < today:
                    d = date(d.year + 1, d.month, d.day)
                return d.isoformat()
            except ValueError:
                pass

    return s


def _normalize_appointment_time(raw: str) -> str:
    """Normalize a spoken or typed time to HH:MM (24-hour).

    Handles:
      - HH:MM or HH:MM:SS (24-hour, pass-through)
      - "10 AM", "10:30 AM", "10am", "2:30pm"
      - HHMM (4 digits, e.g. "1030", "1430")
      - Words: "morning", "noon", "afternoon", "evening", "night"

    Returns the original string unchanged if it cannot be parsed.
    """
    s = raw.strip().lower()

    if s in _TIME_WORDS:
        return _TIME_WORDS[s]

    # HH:MM (24-hour, already normalized)
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    # HH:MM:SS — strip seconds
    m = re.fullmatch(r"(\d{1,2}):(\d{2}):\d{2}", s)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    # "10am", "10 am", "10:30am", "10:30 am"
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)", s.replace(" ", ""))
    if m:
        h = int(m.group(1))
        mn = int(m.group(2)) if m.group(2) else 0
        period = m.group(3)
        if period == "pm" and h != 12:
            h += 12
        elif period == "am" and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    # HHMM (4 digits: "1030", "0930", "1430")
    m = re.fullmatch(r"(\d{2})(\d{2})", s)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    return raw.strip()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class MedicalAppointmentAgent(ScenarioAgent):
    def __init__(
        self, name: str, gender: str, language: str, validation_details: dict
    ) -> None:
        self.validation_details = validation_details
        self._dob_attempts: int = 0
        self._current_step: str = "greeting"

        customer_name = validation_details.get("full_name", "the customer")
        company_name = random.choice(INSURANCE_COMPANIES)
        current_time = datetime.now(INDIA_TZ).strftime("%A, %d %B %Y %H:%M IST")
        is_home_visit_available = random.choice([True, False])
        is_axis_max_life = company_name == "Axis Max-Life Insurance"
        address = random.choice(ADDRESSES)
        center = random.choice(DIAGNOSTIC_CENTERS.values())
        self._booking_context = {
            "pin_code": address["pin_code"],
            "address": address["address"],
            "center_name": center["name"],
            "center_address": center["address"],
        }

        super().__init__(
            language=language,
            instructions=MAX_MEDICAL_APPOINTMENT_PROMPT.format(
                name=name,
                gender=gender,
                company_name=company_name,
                current_time=current_time,
                customer_name=customer_name,
                pin_code=address["pin_code"],
                address=address["address"],
                is_home_visit_available=is_home_visit_available,
                center_name=center["name"],
                center_address=center["address"],
            )
            if is_axis_max_life
            else MEDICAL_APPOINTMENT_PROMPT.format(
                name=name,
                gender=gender,
                current_time=current_time,
                company_name=company_name,
                customer_name=customer_name,
                pin_code=address["pin_code"],
                address=address["address"],
                is_home_visit_available=is_home_visit_available,
                center_name=center["name"],
                center_address=center["address"],
            ),
        )

    # -----------------------------------------------------------------------
    # Home visit tools
    # -----------------------------------------------------------------------

    @function_tool()
    async def book_home_visit(
        self, context: RunContext, date: str, time: str
    ) -> dict[str, Any]:
        """Confirm a home visit appointment at the customer's preferred date and time.

        Call this after the customer provides a date and time. No validation is applied
        — accept whatever the customer says.

        Args:
            date: YYYY-MM-DD
            time: HH:MM (24-hour format)
        """
        norm_date = _normalize_appointment_date(date)
        norm_time = _normalize_appointment_time(time)
        self._current_step = "home_datetime"
        self._booking_context.update(
            {
                "appointment_type": "home_visit",
                "date": norm_date,
                "time": norm_time,
            }
        )

        now_iso = datetime.now(INDIA_TZ).isoformat()
        payload = {
            "appointment_id": str(uuid.uuid4()),
            "dob": self.validation_details.get("dob", ""),
            "phone_number": self.validation_details.get("phone_number", ""),
            "full_name": self.validation_details.get("full_name", ""),
            "date": norm_date,
            "time": norm_time,
            "appointment_type": "home",
            "exam_type": "Home Collection",
            "pin_code": self._booking_context.get("pin_code", ""),
            "address": self._booking_context.get("address", ""),
            "created_at": now_iso,
        }

        try:
            record = await asyncio.to_thread(create_appointment, payload)
        except Exception as exc:
            logger.exception("Failed to persist home visit booking: %s", exc)
            record = {}

        return {
            "confirmed": True,
            "appointment_id": record.get("appointment_id", payload["appointment_id"]),
            "date": norm_date,
            "time": norm_time,
            "next_step": "confirm_booking",
        }

    @function_tool()
    async def book_center_visit(
        self, context: RunContext, center_id: str, date: str, time: str
    ) -> dict[str, Any]:
        """Confirm the center visit appointment at the customer's preferred date and time.

        Call after the customer has chosen a center and provided a date and time.
        No validation is applied — accept whatever the customer says.

        Args:
            center_id: The diagnostic center identifier (e.g. C001).
            date: Preferred date as stated by the customer.
            time: Preferred time as stated by the customer.
        """

        norm_date = _normalize_appointment_date(date)
        norm_time = _normalize_appointment_time(time)
        self._current_step = "center_datetime"
        center = DIAGNOSTIC_CENTERS.get(center_id.upper(), DIAGNOSTIC_CENTERS["C001"])

        self._booking_context.update(
            {
                "appointment_type": "center_visit",
                "center_id": center_id,
                "center_name": center["name"],
                "date": norm_date,
                "time": norm_time,
            }
        )

        now_iso = datetime.now(INDIA_TZ).isoformat()
        payload = {
            "appointment_id": str(uuid.uuid4()),
            "dob": self.validation_details.get("dob", ""),
            "phone_number": self.validation_details.get("phone_number", ""),
            "full_name": self.validation_details.get("full_name", ""),
            "date": norm_date,
            "time": norm_time,
            "appointment_type": "center",
            "exam_type": "Medical Examination",
            "pin_code": "",
            "address": center["address"],
            "created_at": now_iso,
        }

        try:
            record = await asyncio.to_thread(create_appointment, payload)
        except Exception as exc:
            logger.exception("Failed to persist center visit booking: %s", exc)
            record = {}

        return {
            "confirmed": True,
            "appointment_id": record.get("appointment_id", payload["appointment_id"]),
            "center": center["name"],
            "address": center["address"],
            "date": norm_date,
            "time": norm_time,
            "next_step": "confirm_booking",
        }

    # -----------------------------------------------------------------------
    # Notification & flow control tools
    # -----------------------------------------------------------------------

    @function_tool()
    async def schedule_callback(
        self, context: RunContext, preferred_time: str = ""
    ) -> dict[str, Any]:
        """Schedule a callback for the customer at a preferred time.

        Use when the customer is unavailable, interrupts, or requests a later call.

        Args:
            preferred_time: Customer's preferred callback time (free text). Optional.
        """
        await asyncio.sleep(2)  # Simulate thinking time before responding
        callback_time = preferred_time.strip() if preferred_time else "within 2 hours"
        return {
            "scheduled": True,
            "callback_time": callback_time,
            "next_step": "close",
        }
