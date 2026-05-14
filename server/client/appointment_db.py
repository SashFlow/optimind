from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_ENGINE: Engine | None = None


def _engine() -> Engine:
    global _ENGINE
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required for appointment database access.")

    if _ENGINE is None:
        _ENGINE = create_engine(
            url=database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            future=True,
        )
    return _ENGINE


def _row_to_dict(row: Any) -> dict[str, Any]:
    result = dict(row)
    appt_date = result.get("appointment_date")
    appt_time = result.get("appointment_time")
    created_at = result.get("created_at") or result.get("createdAt")
    updated_at = result.get("updated_at") or result.get("updatedAt")
    dob = result.get("dob")

    if isinstance(appt_date, date):
        result["date"] = appt_date.isoformat()
    if appt_time is not None:
        result["time"] = appt_time.strftime("%H:%M")
    if isinstance(created_at, datetime):
        result["created_at"] = created_at.isoformat()
    if isinstance(updated_at, datetime):
        result["updated_at"] = updated_at.isoformat()
    if isinstance(dob, date):
        result["dob"] = dob.isoformat()

    if "id" in result and "appointment_id" not in result:
        result["appointment_id"] = str(result["id"])

    result.pop("appointment_date", None)
    result.pop("appointment_time", None)
    result.pop("createdAt", None)
    result.pop("updatedAt", None)
    return result


def get_user(phone_number: str) -> dict[str, Any] | None:
    with _engine().begin() as conn:
        row = conn.execute(
            text(
                "SELECT phone_number, full_name, dob "
                "FROM registered_users WHERE phone_number = :phone_number"
            ),
            {"phone_number": phone_number},
        ).mappings().first()
        if not row:
            return None
        user = dict(row)
        if isinstance(user.get("dob"), date):
            user["dob"] = user["dob"].isoformat()
        return user


def get_latest_confirmed_booking(phone_number: str, dob: str) -> dict[str, Any] | None:
    with _engine().begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, phone_number, full_name, dob, appointment_date, appointment_time,
                       exam_type, pin_code, address, "createdAt", "updatedAt"
                FROM appointments
                WHERE phone_number = :phone_number AND dob = :dob
                ORDER BY "createdAt" DESC
                LIMIT 1
                """
            ),
            {"phone_number": phone_number, "dob": dob},
        ).mappings().first()
        return _row_to_dict(row) if row else None


def is_slot_taken(appointment_date: str, appointment_time: str, exam_type: str) -> bool:
    with _engine().begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1
                                FROM appointments
                                WHERE appointment_date = :appointment_date
                                    AND appointment_time = :appointment_time
                  AND exam_type = :exam_type
                LIMIT 1
                """
            ),
            {
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "exam_type": exam_type,
            },
        ).first()
        return row is not None


def get_daily_booking_count(appointment_date: str) -> int:
    with _engine().begin() as conn:
        row = conn.execute(
            text(
                "SELECT COUNT(*) AS total "
                "FROM appointments WHERE appointment_date = :appointment_date"
            ),
            {"appointment_date": appointment_date},
        ).mappings().first()
        return int(row["total"]) if row else 0


def create_appointment(payload: dict[str, Any]) -> dict[str, Any]:
    with _engine().begin() as conn:
        inserted = conn.execute(
            text(
                """
                INSERT INTO appointments(
                    dob,
                    phone_number,
                    full_name,
                    appointment_date,
                    appointment_time,
                    exam_type,
                    pin_code,
                    address,
                    "createdAt"
                ) VALUES (
                    :dob,
                    :phone_number,
                    :full_name,
                    :date,
                    :time,
                    :exam_type,
                    :pin_code,
                    :address,
                    CAST(:created_at AS TIMESTAMPTZ)
                )
                RETURNING id, phone_number, full_name, dob, appointment_date, appointment_time,
                          exam_type, pin_code, address, "createdAt", "updatedAt"
                """
            ),
            payload,
        ).mappings().first()
        return _row_to_dict(inserted)


def reschedule_appointment(
    phone_number: str,
    dob: str,
    new_date: str,
    new_time: str,
    exam_type: str,
    pin_code: str = "",
    address: str = "",
) -> dict[str, Any]:
    """Reschedule an existing appointment by creating a new one.

    Args:
        phone_number: User phone number.
        dob: User date of birth (ISO format).
        new_date: New appointment date (ISO format).
        new_time: New appointment time (HH:MM format).
        exam_type: Home Collection or Center Visit.
        pin_code: Optional pincode.
        address: Optional address for home collection.

    Returns:
        New appointment record or error dict.
    """
    with _engine().begin() as conn:
        old_appointment = conn.execute(
            text(
                """SELECT id, phone_number, full_name FROM appointments
                   WHERE phone_number = :phone_number AND dob = :dob
                   ORDER BY \"createdAt\" DESC LIMIT 1"""
            ),
            {"phone_number": phone_number, "dob": dob},
        ).mappings().first()

        if not old_appointment:
            return {
                "result": "failed",
                "error": "No existing appointment found to reschedule.",
            }

        full_name = old_appointment["full_name"]

        new_appointment = conn.execute(
            text(
                """
                INSERT INTO appointments(
                    dob,
                    phone_number,
                    full_name,
                    appointment_date,
                    appointment_time,
                    exam_type,
                    pin_code,
                    address,
                    "createdAt"
                ) VALUES (
                    :dob,
                    :phone_number,
                    :full_name,
                    :new_date,
                    :new_time,
                    :exam_type,
                    :pin_code,
                    :address,
                    CAST(:created_at AS TIMESTAMPTZ)
                )
                RETURNING id, phone_number, full_name, dob, appointment_date, appointment_time,
                          exam_type, pin_code, address, "createdAt", "updatedAt"
                """
            ),
            {
                "dob": dob,
                "phone_number": phone_number,
                "full_name": full_name,
                "new_date": new_date,
                "new_time": new_time,
                "exam_type": exam_type,
                "pin_code": pin_code or "",
                "address": address or "",
                "created_at": datetime.now().isoformat(),
            },
        ).mappings().first()

    return _row_to_dict(new_appointment) if new_appointment else {"result": "failed", "error": "Failed to create new appointment."}
