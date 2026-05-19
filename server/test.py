import asyncio
import logging
from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    JobContext,
    cli,
    function_tool,
)
from livekit import api
from livekit.plugins import google
from livekit.agents.voice import AgentSession, RunContext
from agents.tools import end_call, hangup_call
from agents.base import ScenarioAgent

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

server = AgentServer()

AGENT_LIB = {
    "Sanjay": {
        "gender": "male",
        "avatar": "5f46f99e-c4be-4f22-bde2-b364975a0851",
        "voice": "echo",
    },
    "Samira": {
        "gender": "female",
        "avatar": "d3e94c42-b348-4bec-8225-e47a682128a0",
        "voice": "marin",
    },
}


class DemoAgent(ScenarioAgent):
    def __init__(self, name: str):
        instructions = f"""
        You are a helpful assistant named {name}. 
        Always refer to yourself as {name} and use they/them pronouns. 
        You speek in Hindi.
        - call goodbye function
        - You Say Goodbye and end the call when the user indicates they have no more questions or needs.
        """
        super().__init__(instructions=instructions)

    @function_tool()
    async def goodbye(
        self,
        context: RunContext,
    ) -> str:
        """
        You should call this function when the user indicates they have no more questions or needs, such as by saying "no thanks", "that's all", "goodbye", "thank you", or similar phrases. When you call this function, you should first generate a friendly goodbye message to the user, such as "Thank you for your time. Have a great day ahead!" and then end the call cleanly.
         - Generate a friendly goodbye message to the user.
         - Do not call this function unless the user has indicated they have no more questions or needs
         - After generating the goodbye message, end the call cleanly.
        """

        async def _end_after_delay():
            await asyncio.sleep(5)
            await hangup_call()

        asyncio.ensure_future(_end_after_delay())
        return "Say goodbye and have a nice day to the user in a friendly manner and end the call."


@server.rtc_session(agent_name="demo-agent-6")
async def entrypoint(ctx: JobContext):
    # Connect to Room
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    async def my_shutdown_hook():
        await ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=ctx.room.name,
            )
        )

    ctx.add_shutdown_callback(my_shutdown_hook)

    await ctx.connect()

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-live-2.5-flash-native-audio",
            vertexai=True,
            voice="Charon",
        ),
        tools=[end_call],
        preemptive_generation=True,
    )

    await session.start(
        agent=DemoAgent(name="Sanjay"),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)
