from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from livekit.agents import RunContext, function_tool

from client.appointment_db import create_appointment
from agents.base import ScenarioAgent
from agents.common import normalize_lookup_key
from agents.lib import MEDICAL_APPOINTMENT_PROMPT

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


def _normalize_dob(raw: str) -> str | None:
    """Parse common spoken and typed DOB formats into ISO YYYY-MM-DD.

    Handles:
      - DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
      - YYYY-MM-DD  (ISO)
      - DDMMYYYY    (8 digits, no separator)
      - "15th August 1992", "August 15 1992", "15 August 1992"
    Returns None if the input cannot be parsed.
    """
    s = raw.strip().lower()

    # Remove ordinal suffixes: 1st → 1, 2nd → 2, etc.
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)

    # --- Numeric formats ---
    # YYYY-MM-DD or YYYY/MM/DD
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return d.isoformat()
        except ValueError:
            return None

    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", s)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return d.isoformat()
        except ValueError:
            return None

    # DDMMYYYY (exactly 8 digits)
    m = re.fullmatch(r"(\d{2})(\d{2})(\d{4})", s)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return d.isoformat()
        except ValueError:
            return None

    # --- Spoken formats ---
    # "15 august 1992" or "august 15 1992"
    m = re.search(
        r"(\d{1,2})\s+([a-z]+)\s+(\d{4})|([a-z]+)\s+(\d{1,2})[,\s]+(\d{4})", s
    )
    if m:
        if m.group(1):
            day_s, month_s, year_s = m.group(1), m.group(2), m.group(3)
        else:
            month_s, day_s, year_s = m.group(4), m.group(5), m.group(6)
        month_num = _MONTH_MAP.get(month_s)
        if month_num:
            try:
                d = date(int(year_s), int(month_num), int(day_s))
                return d.isoformat()
            except ValueError:
                return None

    return None


def _normalize_phone(raw: str) -> str:
    """Return the last 10 digits of any phone-like input."""
    digits = re.sub(r"\D", "", raw or "")
    return digits[-10:] if len(digits) >= 10 else digits


_TIME_WORDS: dict[str, str] = {
    "morning": "09:00",
    "noon": "12:00",
    "afternoon": "13:00",
    "evening": "17:00",
    "night": "19:00",
    "midnight": "00:00",
}


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
        self._booking_context: dict[str, Any] = {}
        self._dob_attempts: int = 0
        self._current_step: str = "greeting"

        customer_name = validation_details.get("full_name", "the customer")
        current_time = datetime.now(INDIA_TZ).strftime("%A, %d %B %Y %H:%M IST")

        super().__init__(
            language=language,
            instructions=MEDICAL_APPOINTMENT_PROMPT.format(
                name=name,
                gender=gender,
                language=language,
                current_time=current_time,
                customer_name=customer_name,
            ),
        )

    # -----------------------------------------------------------------------
    # Identity verification tools
    # -----------------------------------------------------------------------

    @function_tool()
    async def verify_dob(self, context: RunContext, dob: str) -> dict[str, Any]:
        """Verify the customer's date of birth against the registered record.

        Call this immediately after the customer provides their date of birth.
        Pass the raw response — the tool handles format normalization.

        Args:
            dob: Date of birth in YYYY-MM-DD.
        """
        self._dob_attempts += 1
        max_attempts = 2
        attempts_remaining = max(0, max_attempts - self._dob_attempts)

        stored_iso = self.validation_details.get("dob", "")
        parsed_iso = _normalize_dob(dob)
        verified = parsed_iso is not None and parsed_iso == stored_iso

        if verified:
            self._current_step = "verify_dob"
            return {
                "verified": True,
                "attempts_remaining": attempts_remaining,
                "next_step": "verify_phone",
            }
        return {
            "verified": False,
            "attempts_remaining": attempts_remaining,
            "next_step": "retry_dob" if attempts_remaining > 0 else "escalate",
        }

    @function_tool()
    async def verify_phone(
        self, context: RunContext, phone_number: str
    ) -> dict[str, Any]:
        """Verify the customer's registered mobile number.

        Accepts full 10-digit number, last 4 digits, or number with country code.

        Args:
            phone_number: Mobile number or last four digits as given by the customer.
        """
        stored = _normalize_phone(self.validation_details.get("phone_number", ""))
        provided = _normalize_phone(phone_number)

        # Accept last-4 shorthand or full match
        verified = (len(provided) == 4 and stored.endswith(provided)) or (
            len(provided) == 10 and provided == stored
        )

        if verified:
            self._current_step = "verify_phone"
            return {"verified": True, "next_step": "explain_purpose"}
        return {"verified": False, "next_step": "escalate"}

    # -----------------------------------------------------------------------
    # Home visit tools
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
        """Save the customer's home address for the medical visit.

        Call this after the customer has confirmed all address components.

        Args:
            house: House or flat number.
            street: Street or road name.
            area: Locality or neighbourhood.
            city: City name.
            pin_code: 6-digit Indian postal code.
            landmark: Optional nearby landmark for the technician.
        """
        parts = [house, street, area, city, f"PIN {pin_code}"]
        if landmark:
            parts.append(f"Near {landmark}")
        full_address = ", ".join(p.strip() for p in parts if p.strip())

        self._current_step = "home_address"
        self._booking_context["address"] = full_address
        self._booking_context["pin_code"] = pin_code
        self._booking_context["appointment_type"] = "home_visit"
        return {
            "saved": True,
            "full_address": full_address,
            "next_step": "home_datetime",
        }

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

        self._current_step = "center_search"
        key = normalize_lookup_key(location)

        # Match on city or area name (case-insensitive substring)
        matches = [
            {"id": cid, **info}
            for cid, info in DIAGNOSTIC_CENTERS.items()
            if key in normalize_lookup_key(info["city"])
            or key in normalize_lookup_key(info["area"])
        ]

        # Fall back to Bangalore centers if no city match
        if not matches:
            matches = [
                {"id": cid, **info}
                for cid, info in DIAGNOSTIC_CENTERS.items()
                if info["city"] == "Bangalore"
            ]

        # Return at most 3 centers
        matches = matches[:3]
        return {"centers": matches, "next_step": "center_select"}

    @function_tool()
    async def select_center(
        self, context: RunContext, center_id: str
    ) -> dict[str, Any]:
        """Confirm the customer's chosen diagnostic center.

        Args:
            center_id: The center identifier (e.g. C001).
        """

        self._current_step = "center_select"
        center = DIAGNOSTIC_CENTERS.get(center_id.upper())
        if center is None:
            center_id = "C001"
            center = DIAGNOSTIC_CENTERS[center_id]

        self._booking_context.update(
            {
                "appointment_type": "center_visit",
                "center_id": center_id,
                "center_name": center["name"],
            }
        )
        return {"selected": True, "center": center, "next_step": "center_datetime"}

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
        callback_time = preferred_time.strip() if preferred_time else "within 2 hours"
        return {
            "scheduled": True,
            "callback_time": callback_time,
            "next_step": "close",
        }

    @function_tool()
    async def mark_wrong_number(self, context: RunContext) -> dict[str, Any]:
        """Mark this contact as a wrong number and update the record.

        Call immediately when the answering party confirms they are not the
        intended customer.
        """
        return {"updated": True, "status": "wrong_number"}

    @function_tool()
    async def mark_exam_completed(self, context: RunContext) -> dict[str, Any]:
        """Mark the medical examination as already completed by the customer.

        Call when the customer reports they have already done the exam.
        """
        return {"updated": True, "status": "exam_completed"}

    @function_tool()
    async def get_call_status(self, context: RunContext) -> dict[str, Any]:
        """Return the current step and all data collected so far in this call.

        Call this whenever you are unsure which step you are on, what information
        has already been gathered, or what to do next.
        """
        step_next_map: dict[str, str] = {
            "greeting": "introduction",
            "introduction": "verify_dob",
            "verify_dob": "verify_phone",
            "verify_phone": "explain_purpose",
            "explain_purpose": "appointment_type",
            "appointment_type": "home_address or center_search",
            "home_address": "home_datetime",
            "home_datetime": "confirm_booking",
            "center_search": "center_select",
            "center_select": "center_datetime",
            "center_datetime": "confirm_booking",
            "confirm_booking": "close",
            "close": "done",
        }

        ctx = {
            "current_step": self._current_step,
            "next_step": step_next_map.get(self._current_step, "unknown"),
            "dob_attempts_used": self._dob_attempts,
            "collected": {k: v for k, v in self._booking_context.items()},
        }
        return ctx
