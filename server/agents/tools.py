import logging

from livekit import api
from livekit.agents import RunContext, function_tool, get_job_context

logger = logging.getLogger("avatar.tools")
logger.setLevel(logging.INFO)


@function_tool
async def end_call(ctx: RunContext):
    """End the call. If  the user isn't interested, expresses general dissatisfaction, wants to end the call, or if the call has been going on for a long time, the agent can choose to end the call by invoking this tool."""
    job_ctx = get_job_context()
    if job_ctx is None:
        logging.error("No job context found when trying to end call.")
        return "Error: No job context found."

    logger.info("Ending call as requested by agent.")

    try:
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=job_ctx.room.name)
        )
        logger.info("Call ended successfully.")
        return "Call ended successfully."
    except Exception as e:
        logger.error(f"Failed to end call: {e}")
        return f"Error: Failed to end call - {e}"


@function_tool
async def transfer_to_human(ctx: RunContext) -> str:
    """Transfer the call to a human agent. If the user requests to speak with a human agent, or if the agent determines that the user's needs would be better served by a human, the agent can choose to transfer the call by invoking this tool."""
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
