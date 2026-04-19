"use client";

import { Assistant } from "@/components/player/Assistant";

export default function SimpleVoiceAssistant() {
  return (
    <Assistant
      mediaMode="audio"
      title="Voice Assistant"
      description="Reusable assistant shell with live widget support."
      highlights={[
        "Uses LiveKit device selection",
        "Receives backend widget updates",
        "Uses the shared live data panel",
      ]}
    />
  );
}
