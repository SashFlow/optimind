from __future__ import annotations

import logging

from livekit.agents.voice import Agent

from .common import extract_scenario_slug, resolve_room_metadata
from .front_desk import FrontDeskAgent
from .general_purpose import GeneralPurposeAgent
from .help_desk_partner import HelpDeskPartnerAgent
from .medical_officer import MedicalOfficerAgent
from .resturant_agent import ResturantAgent
from .study_partner import StudyPartnerAgent

logger = logging.getLogger(__name__)

AGENT_FACTORIES: dict[str, type[Agent]] = {
    "general-purpose": GeneralPurposeAgent,
    "medical-officer": MedicalOfficerAgent,
    "front-desk-agent": FrontDeskAgent,
    "resturant-agent": ResturantAgent,
    "study-partner": StudyPartnerAgent,
    "help-desk-partner": HelpDeskPartnerAgent,
}


def get_agent(metadata: str | None) -> Agent:
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
