import asyncio
from asyncio.log import logger

from livekit.agents import AgentSession

from agents.medical_examinar import MedicalExaminationAgent
from agents.reminder_agent import ReminderAgent
from agents.medical_appointment import MedicalAppointmentAgent
from agents.insurance_feedback import InsuranceFeedbackAgent


def get_agent(slug, selected_agent, agent, language, persona):
    if slug == "medical-examination":
        return MedicalExaminationAgent(selected_agent, agent["gender"], language)
    elif slug == "medical-appointment":
        return MedicalAppointmentAgent(
            selected_agent, agent["gender"], language, validation_details=persona
        )
    elif slug == "insurance-feedback":
        return InsuranceFeedbackAgent(
            selected_agent, agent["gender"], validation_details=persona
        )
    elif slug == "reminder-call":
        return ReminderAgent(
            selected_agent,
            agent["gender"],
            language,
            validation_details=persona,
        )
    else:
        return ReminderAgent(
            selected_agent,
            agent["gender"],
            language,
            validation_details=persona,
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
