import {
  RoomAudioRenderer,
  useRoomContext,
  useVoiceAssistant,
} from "@livekit/components-react";
import { Room } from "livekit-client";
import { useEffect, useRef, useState } from "react";
import type { LiveWidget, LiveWidgetRpcPayload, ScenarioDetails } from "@/types";
import { AgentVisualizer } from "./AgentVisualizer";
import { ControlBar } from "./ControlBar";
import { LiveWidgetsPanel } from "./LiveWidgetsPanel";

function isLiveWidget(value: unknown): value is LiveWidget {
  if (!value || typeof value !== "object") return false;

  const widget = value as Partial<LiveWidget>;
  return (
    typeof widget.id === "string" &&
    typeof widget.type === "string" &&
    typeof widget.title === "string" &&
    typeof widget.status === "string" &&
    typeof widget.description === "string" &&
    Array.isArray(widget.data) &&
    Array.isArray(widget.highlights)
  );
}

function isWidgetRpcPayload(value: unknown): value is LiveWidgetRpcPayload {
  if (!value || typeof value !== "object") return false;

  const payload = value as Partial<LiveWidgetRpcPayload>;
  if (payload.action === "clear") {
    return true;
  }

  if (payload.action === "replace") {
    return Array.isArray(payload.widgets) && payload.widgets.every(isLiveWidget);
  }

  if (payload.action === "upsert") {
    return isLiveWidget(payload.widget);
  }

  return false;
}

type AssistantProps = {
  onConnectButtonClicked: () => void;
  room: Room;
} & ScenarioDetails;

export function Assistant(props: AssistantProps) {
  const { onConnectButtonClicked, title, description, highlights } = props;
  const room = useRoomContext();
  const { state: agentState } = useVoiceAssistant();
  const [widgets, setWidgets] = useState<LiveWidget[]>([]);
  const hasConnectedRef = useRef(false);

  useEffect(() => {
    if (hasConnectedRef.current) return;
    hasConnectedRef.current = true;
    onConnectButtonClicked();
  }, [onConnectButtonClicked]);

  useEffect(() => {
    if (!room) return;

    const handleWidgetUpdate = async (data: {
      payload?: string;
    }): Promise<string> => {
      try {
        if (!data || data.payload === undefined) {
          return "Error: Invalid RPC data format";
        }

        const payload =
          typeof data.payload === "string"
            ? JSON.parse(data.payload)
            : data.payload;

        if (!isWidgetRpcPayload(payload)) {
          return "Error: Invalid widget payload";
        }

        if (payload.action === "clear") {
          setWidgets([]);
        } else if (payload.action === "replace") {
          setWidgets(payload.widgets);
        } else if (payload.action === "upsert") {
          setWidgets((currentWidgets) => [
            payload.widget,
            ...currentWidgets.filter(
              (widget) => widget.id !== payload.widget.id,
            ),
          ]);
        }

        return "Success";
      } catch (error) {
        return (
          `Error: ${error instanceof Error ? error.message : String(error)}`
        );
      }
    };

    room.localParticipant.registerRpcMethod("client.widget", handleWidgetUpdate);

    return () => {
      room.localParticipant.unregisterRpcMethod("client.widget");
    };
  }, [room]);

  return (
    <div className="grid min-h-[80vh] gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,420px)]">
      <div className="flex min-h-[70vh] flex-col items-center gap-4 rounded-3xl border border-white/10 bg-black/20 p-4 shadow-2xl backdrop-blur">
        <div className="w-full rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-white">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-white/55">
            Live conversation
          </p>
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-white/70">
            {description}
          </p>
        </div>
        <div className="flex min-h-[50vh] w-full items-center justify-center">
          <AgentVisualizer />
        </div>
        <div className="w-full">
          <ControlBar onConnectButtonClicked={onConnectButtonClicked} />
        </div>
        <RoomAudioRenderer />
      </div>
      <LiveWidgetsPanel
        title={title}
        description={description}
        highlights={highlights}
        connectionState={agentState}
        widgets={widgets}
      />
    </div>
  );
}
