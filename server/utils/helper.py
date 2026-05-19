import asyncio
from asyncio.log import logger

from livekit.agents import AgentSession

from agents.medical_examinar import MedicalExaminationAgent
from agents.reminder_agent import ReminderAgent
from agents.medical_appointment import MedicalAppointmentAgent


def get_agent(slug, selected_agent, agent, language, persona):
    if slug == "medical-examination":
        return MedicalExaminationAgent(selected_agent, agent["gender"], language)
    elif slug == "medical-appointment":
        return MedicalAppointmentAgent(
            selected_agent, agent["gender"], language, validation_details=persona
        )
    else:
        from client.appointment_db import get_latest_confirmed_booking

        appointment = get_latest_confirmed_booking(
            persona.get("phone_number", ""), persona.get("dob", "")
        )
        return ReminderAgent(
            selected_agent,
            agent["gender"],
            language,
            validation_details=persona,
            appointment=appointment,
        )


async def check_for_false_interruption(session: AgentSession) -> None:
    try:
        await asyncio.sleep(20)
        if session.agent_state != "listening":
            return

        logger.info("agent still listening after speaking; prompting for clarification")
        session.generate_reply(
            instructions=(
                "ask the user if they have any other questions or need further assistance"
            )
        )
    except asyncio.CancelledError:
        # State changed before timeout, so this check is no longer needed.
        return
    except Exception:
        logger.exception("failed to run false interruption check")
