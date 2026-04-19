"use client";

import { Room } from "livekit-client";
import { Assistant } from "@/components/player/Assistant";

export default function SimpleVoiceAssistant(props: {
  onConnectButtonClicked: () => void;
  room: Room;
}) {
  return (
    <Assistant
      room={props.room}
      onConnectButtonClicked={props.onConnectButtonClicked}
      title="Voice Assistant"
      description="Reusable assistant shell with live widget support."
      highlights={[
        "Connects automatically",
        "Receives backend widget updates",
        "Uses the shared live data panel",
      ]}
    />
  );
}
