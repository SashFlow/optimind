from .exam import MER_AGENT_PROMPT
from .reminder import MAX_REMINDER_AGENT_PROMPT, REMINDER_AGENT_PROMPT
from .feedback import INSURANCE_FEEDBACK_AGENT_PROMPT
from .appointment import MAX_MEDICAL_APPOINTMENT_PROMPT, MEDICAL_APPOINTMENT_PROMPT

SESSION_INSTRUCTIONS = """
Greet the customer warmly and naturally, like someone genuinely glad to help — not
someone reading a script. Introduce yourself in one or two short, natural-sounding
sentences and ease into the reason for the call. Let a little warmth come through in
how you say it, not just what you say. Do not call any tools yet.
"""

__all__ = [
    "MER_AGENT_PROMPT",
    "MAX_REMINDER_AGENT_PROMPT",
    "REMINDER_AGENT_PROMPT",
    "INSURANCE_FEEDBACK_AGENT_PROMPT",
    "MAX_MEDICAL_APPOINTMENT_PROMPT",
    "MEDICAL_APPOINTMENT_PROMPT",
    "SESSION_INSTRUCTIONS",
]
