"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RoomContext } from "@livekit/components-react";
import { Room, RoomEvent } from "livekit-client";
import { useCallback, useEffect, useState } from "react";
import type { ConnectionDetails } from "@/types";
import { Assistant } from "@/components/player/Assistant";
import { onDeviceFailure } from "@/components/player/utils";
import { useRouter } from "next/navigation";
import { RiArrowRightLine } from "@remixicon/react";
import { setupDisconnectButton } from "@livekit/components-core";

const audioScenarios = {
  "medical-officer": {
    title: "Medical Officer",
    description:
      "Support patient intake, appointment coordination, symptom collection, and general healthcare communication.",
    highlights: [
      "Collect patient details and reason for visit",
      "Guide callers through appointment scheduling",
      "Answer common healthcare workflow questions",
      "Escalate urgent cases to the right team",
    ],
  },
  "front-desk-agent": {
    title: "Front Desk Agent",
    description:
      "Handle greetings, visitor support, booking requests, and day-to-day front desk conversations.",
    highlights: [
      "Welcome callers and identify their needs",
      "Manage bookings and appointment confirmations",
      "Share office hours, directions, and policies",
      "Route requests to the correct department",
    ],
  },
  "resturant-agent": {
    title: "Resturant Agent",
    description:
      "Assist guests with reservations, menu questions, order support, and restaurant service interactions.",
    highlights: [
      "Take and update table reservations",
      "Answer menu and dietary questions",
      "Support takeaway and delivery inquiries",
      "Handle guest requests with a friendly tone",
    ],
  },
  "ai-ivr": {
    title: "AI IVR",
    description:
      "Provide intelligent voice routing, automated menu navigation, and fast caller intent detection.",
    highlights: [
      "Understand caller intent in natural language",
      "Route calls without rigid keypad menus",
      "Reduce wait times with smart automation",
      "Capture context before handoff to an agent",
    ],
  },
  "answering-incoming-calls": {
    title: "Answering Incoming Calls",
    description:
      "Respond to inbound calls, gather context, and guide each conversation toward the right resolution.",
    highlights: [
      "Answer calls with a professional greeting",
      "Capture caller purpose and urgency",
      "Provide first-line support and information",
      "Transfer or log requests when needed",
    ],
  },
} as const;

type AudioScenarioSlug = keyof typeof audioScenarios;

function isAudioScenarioSlug(value: string): value is AudioScenarioSlug {
  return value in audioScenarios;
}

export default function AudioScenarioPage() {
  const params = useParams();
  const slugParam = params?.slug;
  const slug = Array.isArray(slugParam) ? slugParam[0] : slugParam;

  const scenario =
    slug && isAudioScenarioSlug(slug) ? audioScenarios[slug] : null;
  const scenarioType = slug && isAudioScenarioSlug(slug) ? slug : null;
  const [room] = useState(new Room());
  const { disconnect } = setupDisconnectButton(room);
  const router = useRouter();
  const onConnectButtonClicked = useCallback(async () => {
    if (!scenarioType) return;

    const response = await fetch(`/api/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        room_metadata: `audio-${scenarioType}`,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Failed to fetch token: ${response.status}${errorText ? ` - ${errorText}` : ""}`,
      );
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

  if (!scenario) {
    return (
      <main className="min-h-screen bg-background">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-10 md:px-10">
          <div>
            <Button asChild variant="ghost" className="mb-4 pl-0">
              <Link href="/" className="p-0">
                <ArrowLeft className="size-4" />
                Back
              </Link>
            </Button>
            <h1 className="text-3xl font-semibold tracking-tight">
              Audio Scenario Not Found
            </h1>
            <p className="mt-3 text-muted-foreground">
              The requested audio scenario does not exist.
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main
      data-lk-theme="default"
      className="h-full grid content-center bg-(--lk-bg)"
    >
      <div className="w-full h-full flex items-center justify-center gap-4 z-10">
        <Button
          variant="ghost"
          className="text-white border-0 underline text-xs cursor-pointer"
          onClick={() => {
            disconnect(true);
            router.push("/personal");
          }}
        >
          Personal Assistant <RiArrowRightLine size={24} />
        </Button>
      </div>
      <RoomContext.Provider value={room}>
        <div className="lk-room-container max-w-5xl w-[90vw] mx-auto max-h-[90vh]">
          <Assistant
            room={room}
            onConnectButtonClicked={onConnectButtonClicked}
          />
        </div>
      </RoomContext.Provider>
    </main>
  );
}
