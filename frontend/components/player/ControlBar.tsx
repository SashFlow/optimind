import { useVoiceAssistant } from "@livekit/components-react";
import { RiMap2Line, RiTaxiLine } from "@remixicon/react";
import { Button } from "../ui/button";
import { VoiceAssistantControlBar } from "@livekit/components-react";
import { DisconnectButton } from "@livekit/components-react";
import { CloseIcon } from "../CloseIcon";

export function ControlBar(props: {
  onConnectButtonClicked: () => void;
  setShowCab: (show: boolean) => void;
  setShowMap: (show: boolean) => void;
}) {
  const { state: agentState } = useVoiceAssistant();

  return (
    <div className="relative h-15">
      <>
        {agentState === "disconnected" && (
          <div className="uppercase absolute left-1/2 -translate-x-1/2 flex gap-2">
            <button
              onClick={() => props.setShowMap(true)}
              className="bg-white text-black rounded-md px-2 py-1"
            >
              <RiMap2Line size={24} />
            </button>
            <button
              onClick={() => props.onConnectButtonClicked()}
              className="px-4 py-2 bg-white text-black rounded-md"
            >
              Connect to Agent
            </button>
            <button
              onClick={() => props.setShowCab(true)}
              className="bg-white text-black rounded-md px-2 py-1"
            >
              <RiTaxiLine size={24} />
            </button>
          </div>
        )}
      </>
      <>
        {agentState !== "disconnected" && agentState !== "connecting" && (
          <div className="flex h-8 absolute left-1/2 -translate-x-1/2  justify-center gap-2">
            <Button
              onClick={() => props.setShowMap(true)}
              variant="ghost"
              size="icon"
              className="bg-white text-black rounded-md px-2 py-1"
            >
              <RiMap2Line size={24} />
            </Button>
            <VoiceAssistantControlBar controls={{ leave: false }} />
            <DisconnectButton>
              <CloseIcon />
            </DisconnectButton>
            <Button
              onClick={() => props.setShowCab(true)}
              variant="ghost"
              size="icon"
              className="bg-white text-black rounded-md px-2 py-1"
            >
              <RiTaxiLine size={24} />
            </Button>
          </div>
        )}
      </>
    </div>
  );
}
