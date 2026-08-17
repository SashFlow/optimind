import logging
from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    AudioConfig,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    JobContext,
    cli,
    room_io,
)
from livekit.plugins import google, ai_coustics
from livekit.agents.voice import AgentSession, UserStateChangedEvent
from agents.tools import end_call
from utils.helper import get_agent
from google.genai.types import FunctionResponseScheduling
import utils.patch as patch  # noqa: F401

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

server = AgentServer()

AGENT_LIB = {
    "Sanjay": {
        "gender": "male",
        "avatar": "5f46f99e-c4be-4f22-bde2-b364975a0851",
        "voice": "Charon",
    },
    "Samira": {
        "gender": "female",
        "avatar": "d3e94c42-b348-4bec-8225-e47a682128a0",
        "voice": "Leda",
    },
}
LANGUAGE_DICT = {
    "English": "en",
    "Hindi": "hi",
    "Marathi": "mr",
    "Bengali": "bn",
}


@server.rtc_session(agent_name="demo-agent")
async def entrypoint(ctx: JobContext):
    # Connect to Room
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    await ctx.connect()

    # Session Creation Modify the following to change interactions
    
    slug = "medical-appointment" # medical-appointment, medical-examination, reminder-agent
    selected_agent = "Sanjay" # Sanajay, Samira
    language = "Hindi" # any Language
    persona = {
        "full_name": "Rohit",
        "phone_number": "9958684675",
        "dob": "2000-08-20"
    }
    
    room_options = room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=ai_coustics.audio_enhancement(
                model=ai_coustics.EnhancerModel.QUAIL_VF_S,
            ),
        ),
        close_on_disconnect=True,
        delete_room_on_close=True,
        audio_output=room_io.AudioOutputOptions(),
    )

    agent = AGENT_LIB[selected_agent]
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice=agent["voice"],
            language=LANGUAGE_DICT[language],
            tool_response_scheduling=FunctionResponseScheduling.WHEN_IDLE,
        ),
        tools=[end_call],
        vad=ai_coustics.VAD(),
        preemptive_generation=True,
        user_away_timeout=30,
    )

    @session.on("user_state_changed")
    def _on_user_state_changed(ev: UserStateChangedEvent):
        if ev.new_state == "away":
            session.generate_reply(
                instructions="It seems you are away. I'll end the call now. Goodbye!"
            )

    await session.start(
        agent=get_agent(slug, selected_agent, agent, language, persona),
        room=ctx.room,
        room_options=room_options,
    )

    background_audio = BackgroundAudioPlayer(
        # play office ambience sound looping in the background
        ambient_sound=AudioConfig(
            BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.8),
        # play keyboard typing sound when the agent is thinking
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
        ],
    )

    await background_audio.start(room=ctx.room, agent_session=session)


if __name__ == "__main__":
    cli.run_app(server)
