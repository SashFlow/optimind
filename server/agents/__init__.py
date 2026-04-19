from livekit.agents.voice import Agent

from .frontdesk import AvatarAgent


def getAgent(metadata) -> Agent:
    return AvatarAgent()
