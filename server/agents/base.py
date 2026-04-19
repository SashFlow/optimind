from __future__ import annotations

import json
from typing import Any, Sequence

from livekit.agents.voice import Agent

from .common import (
    ScenarioDefinition,
    WidgetPayload,
    build_agent_instructions,
    rows_from_mapping,
)


class ScenarioAgent(Agent):
    def __init__(
        self, *, scenario: ScenarioDefinition, operating_notes: Sequence[str]
    ) -> None:
        self.scenario = scenario
        super().__init__(
            instructions=build_agent_instructions(scenario, operating_notes)
        )

    async def on_enter(self) -> None:
        await self.clear_widgets()
        await self.push_widget(
            WidgetPayload(
                id=f"{self.scenario.slug}-overview",
                type="overview",
                title=f"{self.scenario.title} live data",
                description=self.scenario.summary,
                data=rows_from_mapping(
                    {
                        "Available data": self.scenario.live_data_points,
                        "Suggested asks": self.scenario.highlights,
                    }
                ),
                highlights=self.scenario.highlights,
            )
        )
        self.session.generate_reply(instructions=self.scenario.greeting)

    async def clear_widgets(self) -> None:
        await self._send_widget_rpc({"action": "clear"})

    async def push_widget(self, widget: WidgetPayload) -> None:
        await self._send_widget_rpc(
            {"action": "upsert", "widget": widget.to_payload()}
        )

    async def _send_widget_rpc(self, payload: dict[str, Any]) -> None:
        subscribed_fut = self.session.room_io.subscribed_fut
        if subscribed_fut is not None and not subscribed_fut.done():
            await subscribed_fut

        await self.session.room_io.room.local_participant.perform_rpc(
            destination_identity=self._remote_identity(),
            method="client.widget",
            payload=json.dumps(payload),
            response_timeout=5.0,
        )

    def _remote_identity(self) -> str:
        room_io = self.session.room_io
        if room_io.linked_participant is not None:
            return room_io.linked_participant.identity

        remote_participants = list(room_io.room.remote_participants.values())
        if remote_participants:
            return remote_participants[0].identity

        raise RuntimeError("No remote participant available for widget updates.")
