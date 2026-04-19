"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { RoomContext } from "@livekit/components-react";
import { Room, RoomEvent } from "livekit-client";
import { useCallback, useEffect, useState } from "react";
import type { ConnectionDetails } from "@/types";
import { onDeviceFailure } from "@/components/player/utils";
import { Assistant } from "@/components/player/Assistant";
import { RiArrowRightLine } from "@remixicon/react";
import { useRouter } from "next/navigation";
import { setupDisconnectButton } from "@livekit/components-core";

const avatarScenarios = {
  "medical-officer": {
    title: "Medical Officer",
    description:
      "A visual healthcare assistant designed to support patient guidance, intake conversations, and care-related interactions.",
    highlights: [
      "Guide patients through intake and onboarding steps",
      "Answer common healthcare support questions",
      "Assist with appointment preparation and follow-up context",
    ],
  },
  "study-partner": {
    title: "Study Partner",
    description:
      "An interactive avatar companion that helps learners review concepts, practice responses, and stay on track with study goals.",
    highlights: [
      "Explain concepts in a conversational format",
      "Support mock practice and revision sessions",
      "Encourage structured learning and study planning",
    ],
  },
  "help-desk-partner": {
    title: "Help Desk Partner",
    description:
      "A visual support assistant for troubleshooting workflows, answering user questions, and guiding people through common issues.",
    highlights: [
      "Walk users through troubleshooting steps",
      "Answer product and support questions clearly",
      "Provide a friendly first-line support experience",
    ],
  },
} as const;

export default function AvatarScenarioPage() {
  const params = useParams<{ slug: string }>();
  const [room] = useState(new Room());
  const { disconnect } = setupDisconnectButton(room);
  const router = useRouter();
  const scenario = useMemo(() => {
    const slug = params?.slug;
    if (!slug) return null;
    return avatarScenarios[slug as keyof typeof avatarScenarios] ?? null;
  }, [params]);
  const scenarioType = params?.slug ?? null;
  const onConnectButtonClicked = useCallback(async () => {
    if (!scenarioType) return;

    const response = await fetch(`/api/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        room_metadata: `video-${scenarioType}`,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch token: ${response.status}`);
    }

    const connectionDetailsData: ConnectionDetails = await response.json();

    await room.connect(
      connectionDetailsData.serverUrl,
      connectionDetailsData.participantToken,
    );
    await room.localParticipant.setMicrophoneEnabled(true);
  }, [room, scenarioType]);

  useEffect(() => {
    room.on(RoomEvent.MediaDevicesError, onDeviceFailure);

    return () => {
      room.off(RoomEvent.MediaDevicesError, onDeviceFailure);
    };
  }, [room]);

  return (
    <main
      data-lk-theme="default"
      className="h-full grid content-center bg-(--lk-bg)"
    >
      <RoomContext.Provider value={room}>
        <div className="w-full h-full flex items-center justify-center gap-4 z–10">
          <Button
            variant="ghost"
            className="text-white border-0 underline text-xs cursor-pointer"
            onClick={() => {
              disconnect(true);
              router.push("/audio");
            }}
          >
            DataSaver Mode <RiArrowRightLine size={24} />
          </Button>
        </div>
        <div className="relative lk-room-container w-full h-full p-4">
          <Assistant
            room={room}
            onConnectButtonClicked={onConnectButtonClicked}
          />
        </div>
      </RoomContext.Provider>
    </main>
  );
}
