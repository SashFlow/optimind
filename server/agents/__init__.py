from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from livekit.agents.voice import Agent

from .common import extract_scenario_slug, resolve_room_metadata

if TYPE_CHECKING:
    from livekit.agents import JobContext
    from .study_partner import StudyPartnerUserData

logger = logging.getLogger(__name__)


def getUserData(
    metadata: str | None, ctx: Optional["JobContext"] = None
) -> Optional["StudyPartnerUserData"]:
    """Return an initialised userdata instance for the resolved scenario slug.

    Only the study-partner scenario requires userdata (for flash card and quiz
    state). All other scenarios return None, which is safe to pass to AgentSession.

    Args:
        metadata: Raw room metadata string used to resolve the scenario slug.
        ctx: JobContext for the current session. Stored on StudyPartnerUserData so
             its function tools can access the room for RPC calls.
    """
    from .study_partner import StudyPartnerUserData

    slug = extract_scenario_slug(metadata)
    if slug == "study-partner":
        return StudyPartnerUserData(ctx=ctx)
    return None


def get_agent(metadata: str | None) -> Agent:
    from agents.medical_examinar import MedicalExaminationAgent
    from agents.medical_appointment import MedicalAppointmentAgent
    from .general_purpose import GeneralPurposeAgent
    from .insurance_feedback import InsuranceFeedbackAgent

    AGENT_FACTORIES: dict[str, type[Agent]] = {
        "medical-examination": MedicalExaminationAgent,
        "reminder-call": MedicalAppointmentAgent,
        "medical-appointment": MedicalAppointmentAgent,
        "insurance-feedback": InsuranceFeedbackAgent,
    }

    slug = extract_scenario_slug(metadata)
    agent_factory = AGENT_FACTORIES.get(slug)
    if agent_factory is None:
        logger.warning(
            "Unknown room metadata '%s'; defaulting to GeneralPurposeAgent.",
            metadata,
        )
        agent_factory = GeneralPurposeAgent

    return agent_factory()


def getAgent(metadata: str | None) -> Agent:
    return get_agent(metadata)


def resolveRoomMetadata(metadata: str | None) -> tuple[str, str, str, str, dict]:
    return resolve_room_metadata(metadata)
