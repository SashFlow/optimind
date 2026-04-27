from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from livekit.agents.voice import Agent

from agents.medical_examinar import MedicalExaminationAgent

from .common import extract_scenario_slug, resolve_room_metadata
from .front_desk import FrontDeskAgent
from .general_purpose import GeneralPurposeAgent
from .medical_officer import MedicalOfficerAgent
from .resturant_agent import ResturantAgent
from .study_partner import StudyPartnerAgent, StudyPartnerUserData

if TYPE_CHECKING:
    from livekit.agents import JobContext

logger = logging.getLogger(__name__)

AGENT_FACTORIES: dict[str, type[Agent]] = {
    "general-purpose": GeneralPurposeAgent,
    "medical-officer": MedicalOfficerAgent,
    "front-desk-agent": FrontDeskAgent,
    "resturant-agent": ResturantAgent,
    "study-partner": StudyPartnerAgent,
    "help-desk-partner": FrontDeskAgent,
    "medical-examination": MedicalExaminationAgent,
}


def getUserData(
    metadata: str | None, ctx: Optional["JobContext"] = None
) -> StudyPartnerUserData | None:
    """Return an initialised userdata instance for the resolved scenario slug.

    Only the study-partner scenario requires userdata (for flash card and quiz
    state). All other scenarios return None, which is safe to pass to AgentSession.

    Args:
        metadata: Raw room metadata string used to resolve the scenario slug.
        ctx: JobContext for the current session. Stored on StudyPartnerUserData so
             its function tools can access the room for RPC calls.
    """
    slug = extract_scenario_slug(metadata)
    if slug == "study-partner":
        return StudyPartnerUserData(ctx=ctx)
    return None


def get_agent(metadata: str | None):
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


def resolveRoomMetadata(metadata: str | None) -> tuple[str, str]:
    return resolve_room_metadata(metadata)
