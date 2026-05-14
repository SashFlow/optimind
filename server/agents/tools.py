import asyncio
import json
import logging
import os
from urllib.parse import urlencode
from urllib.request import urlopen

from livekit import api
from livekit.agents import RunContext, function_tool, get_job_context

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

    logger.info("Ending call as requested by agent.")
    await ctx.wait_for_playout()
    await asyncio.sleep(3)
    await hangup_call()


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
    """Fetch nearby diagnostic centers for an Indian pincode using SerpAPI.

    Returns a stable payload with `result`, `pin_code`, and `options` so callers
    can safely consume API responses and fallback states.
    """
    normalized_pin = "".join(ch for ch in (pin or "") if ch.isdigit())
    if len(normalized_pin) != 6:
        return {
            "result": "failed",
            "pin_code": normalized_pin,
            "options": [],
            "error": "Invalid pincode. Please provide a 6-digit Indian pincode.",
        }

    api_key = os.getenv("SERP_API_KEY", "").strip(
    ) or os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key:
        return {
            "result": "failed",
            "pin_code": normalized_pin,
            "options": [],
            "error": "SERP_API_KEY is not configured.",
        }

    params = {
        "engine": "google_maps",
        "q": f"diagnostic center near {normalized_pin} India",
        "hl": "en",
        "gl": "in",
        "api_key": api_key,
    }
    url = f"https://serpapi.com/search.json?{urlencode(params)}"

    try:
        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        logger.exception(
            "SerpAPI request failed for pincode %s", normalized_pin)
        return {
            "result": "failed",
            "pin_code": normalized_pin,
            "options": [],
            "error": f"Unable to fetch centers from SerpAPI: {exc}",
        }

    local_results = payload.get("local_results", []) or []
    options = []
    for item in local_results[:5]:
        options.append(
            {
                "name": item.get("title", "Unknown Center"),
                "address": item.get("address", "Address unavailable"),
                "distance_km": item.get("distance") or "N/A",
                "rating": item.get("rating"),
                "phone": item.get("phone"),
            }
        )

    return {
        "result": "success",
        "pin_code": normalized_pin,
        "options": options,
        "source": "serpapi",
    }
