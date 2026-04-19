import {
  DisconnectButton,
  VoiceAssistantControlBar,
  useVoiceAssistant,
} from "@livekit/components-react";
import { CloseIcon } from "../CloseIcon";
import { Button } from "../ui/button";

export function ControlBar(props: {
  onConnectButtonClicked: () => void;
}) {
  const { state: agentState } = useVoiceAssistant();

  return (
    <div className="flex min-h-14 items-center justify-center">
      {agentState === "disconnected" ? (
        <Button
          onClick={props.onConnectButtonClicked}
          className="px-6"
          size="lg"
        >
          Connect to Agent
        </Button>
      ) : null}
      {agentState === "connecting" ? (
        <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium uppercase tracking-[0.18em] text-white/70">
          Connecting
        </div>
      ) : null}
      {agentState !== "disconnected" && agentState !== "connecting" ? (
        <div className="flex items-center justify-center gap-2">
          <VoiceAssistantControlBar controls={{ leave: false }} />
          <DisconnectButton>
            <CloseIcon />
          </DisconnectButton>
        </div>
      ) : null}
    </div>
  );
}
