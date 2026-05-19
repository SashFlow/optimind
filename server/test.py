import asyncio
import logging
import time
from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    JobContext,
    UserStateChangedEvent,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    AudioConfig,
    cli,
    room_io,
)
from livekit.plugins import google, ai_coustics
from livekit.agents.voice import AgentSession
from agents.tools import end_call
from agents.reminder_agent import ReminderAgent
from google.genai.types import (
    FunctionResponseScheduling,
)
import utils.patch as patch  # noqa: F401

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

server = AgentServer()


@server.rtc_session(agent_name="demo-agent-6")
async def entrypoint(ctx: JobContext):
    # Connect to Room
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    await ctx.connect()

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

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-3.1-flash-live-preview",
            voice="Leda",
            language="hi",
            tool_response_scheduling=FunctionResponseScheduling.WHEN_IDLE,
        ),
        tools=[end_call],
        vad=ai_coustics.VAD(),
        preemptive_generation=True,
        resume_false_interruption=True,
    )

    @session.on("user_state_changed")
    def _on_user_state_changed(ev: UserStateChangedEvent):
        print(ev.new_state, ev.old_state)
        if ev.new_state == "away":
            session.generate_reply(
                instructions="It seems you are away. I'll end the call now. Goodbye!"
            )

    await session.start(
        agent=ReminderAgent(
            "Samira",
            "Female",
            "Hindi",
            validation_details={
                "phone_number": "+919958684675",
                "dob": "2000-07-20",
                "full_name": "Sahil",
            },
            appointment={
                "appointment_type": "Medical Examination",
                "date": "2026-05-27",
                "time": "10:00 AM",
                "address": "807, Prathameshwar, MG Road, Bengaluru",
                "pin_code": "560001",
                "exam_type": "Home Visit",
                "location": "HealthCare Clinic, 123 Main St.",
            },
        ),
        room=ctx.room,
        room_options=room_options,
    )

    background_audio = BackgroundAudioPlayer(
        # play office ambience sound looping in the background
        ambient_sound=AudioConfig(BuiltinAudioClip.OFFICE_AMBIENCE, volume=0.8),
        # play keyboard typing sound when the agent is thinking
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.8),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.7),
        ],
    )

    await background_audio.start(room=ctx.room, agent_session=session)


if __name__ == "__main__":
    cli.run_app(server)
