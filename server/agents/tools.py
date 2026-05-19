import asyncio
import logging

from livekit import api
from livekit.agents import RunContext, function_tool, get_job_context
from livekit.agents.beta.tools import EndCallTool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Add this function definition anywhere
async def hangup_call():
    ctx = get_job_context()
    if ctx is None:
        # Not running in a job context
        return

    await ctx.api.room.delete_room(
        api.DeleteRoomRequest(
            room=ctx.room.name,
        )
    )


@function_tool
async def end_call(ctx: RunContext):
    """End the current call or live session in a controlled way.

    Use this when the user explicitly wants to stop, or the conversation has naturally
    finished, the user is no longer engaging, or a polite close-out is the best
    experience. Prefer giving a short closing line before invoking this tool so the
    ending feels natural to the user.
    """
    await asyncio.sleep(5)
    ctx.session.shutdown()
    return "Call Ended"


@function_tool
async def transfer_to_human(ctx: RunContext) -> str:
    """Escalate the conversation to a human agent or staff member.

    Use this when the user explicitly asks for a person, when policy or safety
    requires human review, when account or identity verification is needed, or when
    the available tools do not support the requested action. Tell the user that you
    are transferring them before calling this tool.
    """
    job_ctx = get_job_context()
    if job_ctx is None:
        logging.error("No job context found when trying to transfer to human.")
        return "Error: No job context found."

    logger.info("Transferring call to human agent as requested by agent.")

    try:
        logger.info("Call transferred to human agent successfully.")
        return "Simulating call transfer to human agent."
    except Exception as e:
        logger.error(f"Failed to transfer call: {e}")
        return f"Error: Failed to transfer call - {e}"


def get_centers_by_pin(pin: str) -> dict:
    """Fetch nearby diagnostic centers for an Indian pincode using hard-coded data.

    Returns a stable payload with `result`, `pin_code`, and `options` so callers
    can safely consume responses and fallback states.
    """
    normalized_pin = "".join(ch for ch in (pin or "") if ch.isdigit())
    if len(normalized_pin) != 6:
        return {
            "result": "failed",
            "pin_code": normalized_pin,
            "options": [],
            "error": "Invalid pincode. Please provide a 6-digit Indian pincode.",
        }

    # Hard-coded diagnostic centers for common Indian cities
    hardcoded_centers = {
        "110001": [  # Delhi
            {
                "name": "City Imaging & Clinical Labs",
                "address": "Tilak Nagar, New Delhi",
                "distance_km": "1.5 km",
                "rating": 4.5,
                "phone": "011-4722-2222",
            },
            {
                "name": "Dr. Lal PathLabs",
                "address": "Connaught Place, New Delhi",
                "distance_km": "2.0 km",
                "rating": 4.2,
                "phone": "011-3988-5050",
            },
        ],
        "400001": [  # Mumbai
            {
                "name": "Metropolis Healthcare",
                "address": "Fort, Mumbai",
                "distance_km": "0.5 km",
                "rating": 4.6,
                "phone": "022-3399-3939",
            },
            {
                "name": "SRL Diagnostics",
                "address": "Colaba, Mumbai",
                "distance_km": "1.8 km",
                "rating": 4.3,
                "phone": "022-2282-0000",
            },
        ],
        "560001": [  # Bangalore
            {
                "name": "Anand Diagnostic Laboratory",
                "address": "Shivajinagar, Bangalore",
                "distance_km": "1.2 km",
                "rating": 4.7,
                "phone": "080-2222-1234",
            },
            {
                "name": "Aarthi Scans & Labs",
                "address": "Jayanagar, Bangalore",
                "distance_km": "3.5 km",
                "rating": 4.4,
                "phone": "080-4666-4666",
            },
        ],
        "600001": [  # Chennai
            {
                "name": "Hi-Tech Diagnostic Centre",
                "address": "George Town, Chennai",
                "distance_km": "0.8 km",
                "rating": 4.5,
                "phone": "044-2534-1234",
            },
            {
                "name": "Neuberg Ehrlich Laboratory",
                "address": "Royapettah, Chennai",
                "distance_km": "2.5 km",
                "rating": 4.3,
                "phone": "044-4200-0000",
            },
        ],
        "700001": [  # Kolkata
            {
                "name": "Pulse Diagnostics",
                "address": "Esplanade, Kolkata",
                "distance_km": "1.0 km",
                "rating": 4.4,
                "phone": "033-2225-1234",
            },
            {
                "name": "Suraksha Diagnostic",
                "address": "B.B.D. Bagh, Kolkata",
                "distance_km": "2.2 km",
                "rating": 4.2,
                "phone": "033-6619-1000",
            },
        ],
    }

    # Default options for any other valid 6-digit PIN
    default_options = [
        {
            "name": "Apollo Diagnostics",
            "address": "Main Road, Sector 15",
            "distance_km": "2.5 km",
            "rating": 4.3,
            "phone": "1800-102-4567",
        },
        {
            "name": "Thyrocare Technologies",
            "address": "Industrial Area, Phase 2",
            "distance_km": "4.0 km",
            "rating": 4.1,
            "phone": "9412-222-222",
        },
    ]

    options = hardcoded_centers.get(normalized_pin, default_options)

    return {
        "result": "success",
        "pin_code": normalized_pin,
        "options": options,
        "source": "hardcoded",
    }


end_call_tool = EndCallTool(
    end_instructions="Thank you for your time. Have a great day ahead!"
).tools[0]
