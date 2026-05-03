from __future__ import annotations

import json
import logging
from typing import Any

from livekit.agents.voice import Agent
from livekit.agents.voice.room_io import RoomIO
from livekit.rtc.rpc import RpcError
from livekit.agents.beta.tools import EndCallTool
from .common import WidgetPayload
from .prompts import SESSION_INSTRUCTIONS

logger = logging.getLogger(__name__)


class ScenarioAgent(Agent):
    def __init__(self, *, instructions: str) -> None:
        end_call_tool = EndCallTool(
            extra_description="Only end the call after confirming the user examination is complete and all the questions are answered.",
            delete_room=True,
            end_instructions="Thank the user for their time and wish them a good day.",
        )
        super().__init__(instructions=instructions, tools=end_call_tool.tools)

    async def on_enter(self) -> None:
        # await self.clear_widgets()
        self.session.generate_reply(instructions=SESSION_INSTRUCTIONS)

    async def clear_widgets(self) -> None:
        await self._send_widget_rpc({"action": "clear"})

    async def push_widget(self, widget: WidgetPayload) -> None:
        await self._send_widget_rpc({"action": "upsert", "widget": widget.to_payload()})

    async def _send_widget_rpc(self, payload: dict[str, Any]) -> None:
        room_io = self._room_io()
        if room_io is None:
            logger.debug(
                "Skipping widget RPC because the agent session has no room.",
                extra={"payload_action": payload.get("action")},
            )
            return

        subscribed_fut = room_io.subscribed_fut
        if subscribed_fut is not None and not subscribed_fut.done():
            await subscribed_fut

        try:
            await room_io.room.local_participant.perform_rpc(
                destination_identity=self._remote_identity(),
                method="client.widget",
                payload=json.dumps(payload),
                response_timeout=5.0,
            )
        except RpcError as exc:
            if "Method not supported at destination" in str(exc):
                logger.debug(
                    "Skipping widget RPC because the remote participant does not support client.widget.",
                    extra={"payload_action": payload.get("action")},
                )
                return
            raise

    def _remote_identity(self) -> str:
        room_io = self._room_io()
        if room_io is None:
            raise RuntimeError("No room available for widget updates.")

        if room_io.linked_participant is not None:
            return room_io.linked_participant.identity

        remote_participants = list(room_io.room.remote_participants.values())
        if remote_participants:
            return remote_participants[0].identity

        raise RuntimeError("No remote participant available for widget updates.")

    def _room_io(self) -> RoomIO | None:
        return getattr(self.session, "_room_io", None)
