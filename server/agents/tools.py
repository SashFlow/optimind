import asyncio
import logging

from livekit import api
from livekit.agents import RunContext, function_tool, get_job_context

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@function_tool
async def end_call(ctx: RunContext):
    """End the current call or live session in a controlled way.

    Use this when the user explicitly wants to stop, the conversation has naturally
    finished, the user is no longer engaging, or a polite close-out is the best
    experience. Prefer giving a short closing line before invoking this tool so the
    ending feels natural to the user.
    """
    job_ctx = get_job_context()
    if job_ctx is None:
        logging.error("No job context found when trying to end call.")
        return "Error: No job context found."

    logger.info("Ending call as requested by agent.")

    try:
        await asyncio.sleep(5)
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
