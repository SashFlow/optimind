"""Agents for the support agent."""

from .medical_appointment import MedicalAppointmentAgent
from .medical_examinar import MedicalExaminationAgent
from .reminder_agent import ReminderAgent
from .insurance_feedback import InsuranceFeedbackAgent
from constants import SupportState
from livekit.agents import Agent


def get_agent(slug: str, state: SupportState, persona: dict) -> Agent:
    """Get the agent for the given slug."""
    if slug == "medical_appointment":
        return MedicalAppointmentAgent(state, persona)
    elif slug == "medical_examinar":
        return MedicalExaminationAgent(state)
    elif slug == "reminder":
        return ReminderAgent(state, persona)
    elif slug == "insurance_feedback":
        return InsuranceFeedbackAgent(state, persona)
    else:
        raise ValueError(f"Invalid agent slug: {slug}")


__all__ = [
    "MedicalAppointmentAgent",
    "MedicalExaminationAgent",
    "ReminderAgent",
    "InsuranceFeedbackAgent",
    "get_agent",
]
