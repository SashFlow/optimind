"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
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
import { avatarScenarios } from "@/lib/scenarios";

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
              Avatar Scenario Not Found
            </h1>
            <p className="mt-3 text-muted-foreground">
              The requested avatar scenario does not exist.
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
      <RoomContext.Provider value={room}>
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
        <div className="relative lk-room-container w-full h-full p-4">
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
