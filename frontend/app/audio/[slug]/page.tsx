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
import { audioScenarios } from "@/lib/scenarios";

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
      <div className="w-full h-full flex items-center justify-between gap-4 z-10">
        <Button asChild variant="ghost" className="mb-4 pl-0">
          <Link href="/" className="p-0">
            <ArrowLeft className="size-4" />
            Back
          </Link>
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight">
          {scenario.title}
        </h1>
        <div />
      </div>
      <RoomContext.Provider value={room}>
        <div className="lk-room-container max-w-5xl w-[90vw] mx-auto max-h-[90vh]">
          <Assistant
            room={room}
            onConnectButtonClicked={onConnectButtonClicked}
            title={scenario.title}
            description={scenario.description}
            highlights={[...scenario.highlights]}
          />
        </div>
      </RoomContext.Provider>
    </main>
  );
}
