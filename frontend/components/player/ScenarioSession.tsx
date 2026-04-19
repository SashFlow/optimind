"use client";

import {
  PreJoin,
  RoomContext,
  type LocalUserChoices,
} from "@livekit/components-react";
import { ConnectionState, Room, RoomEvent } from "livekit-client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ConnectionDetails, ScenarioDetails } from "@/types";
import { onDeviceFailure } from "./utils";
import { Assistant } from "./Assistant";

type ScenarioSessionProps = {
  mode: "audio" | "video";
  scenarioKey: string;
} & ScenarioDetails;

const CLEANUP_ENDPOINT = "/api/room/cleanup";

function toCaptureDeviceId(deviceId: string) {
  return deviceId && deviceId !== "default" ? deviceId : undefined;
}

export function ScenarioSession(props: ScenarioSessionProps) {
  const { mode, scenarioKey, title, description, highlights } = props;
  const [room] = useState(
    () =>
      new Room({
        disconnectOnPageLeave: true,
      }),
  );
  const [session, setSession] = useState<ConnectionDetails | null>(null);
  const [sessionMediaMode, setSessionMediaMode] = useState<"audio" | "video">(
    mode,
  );
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const activeSessionRef = useRef<ConnectionDetails | null>(null);
  const cleanupInFlightRef = useRef(false);

  const cleanupRoom = useCallback((useBeacon = false) => {
    const activeSession = activeSessionRef.current;
    if (!activeSession || cleanupInFlightRef.current) {
      return Promise.resolve();
    }

    cleanupInFlightRef.current = true;
    const payload = JSON.stringify({
      room_name: activeSession.roomName,
      participant_identity: activeSession.participantIdentity,
    });

    if (
      useBeacon &&
      typeof navigator !== "undefined" &&
      typeof navigator.sendBeacon === "function"
    ) {
      const queued = navigator.sendBeacon(
        CLEANUP_ENDPOINT,
        new Blob([payload], { type: "application/json" }),
      );
      if (queued) {
        activeSessionRef.current = null;
        return Promise.resolve();
      }
    }

    return fetch(CLEANUP_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: payload,
      keepalive: useBeacon,
    })
      .then(() => {
        activeSessionRef.current = null;
      })
      .catch((error) => {
        cleanupInFlightRef.current = false;
        console.error("Failed to clean up LiveKit room", error);
      });
  }, []);

  useEffect(() => {
    room.on(RoomEvent.MediaDevicesError, onDeviceFailure);

    const handleDisconnected = () => {
      setSession(null);
      setIsConnecting(false);
      void cleanupRoom();
    };

    const handlePageLeave = () => {
      if (room.state !== ConnectionState.Disconnected) {
        void room.disconnect();
      }
      void cleanupRoom(true);
    };

    room.on(RoomEvent.Disconnected, handleDisconnected);
    window.addEventListener("pagehide", handlePageLeave);
    window.addEventListener("beforeunload", handlePageLeave);

    return () => {
      room.off(RoomEvent.MediaDevicesError, onDeviceFailure);
      room.off(RoomEvent.Disconnected, handleDisconnected);
      window.removeEventListener("pagehide", handlePageLeave);
      window.removeEventListener("beforeunload", handlePageLeave);
      if (room.state !== ConnectionState.Disconnected) {
        void room.disconnect();
      }
      void cleanupRoom(true);
    };
  }, [cleanupRoom, room]);

  const handleJoin = useCallback(
    async (userChoices: LocalUserChoices) => {
      if (isConnecting) return;

      setIsConnecting(true);
      setConnectError(null);

      try {
        const response = await fetch("/api/token", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            participant_name: userChoices.username.trim() || "Guest",
            room_metadata: `${mode}-${scenarioKey}`,
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(
            `Failed to fetch token: ${response.status}${errorText ? ` - ${errorText}` : ""}`,
          );
        }

        const connectionDetails: ConnectionDetails = await response.json();

        await room.connect(
          connectionDetails.serverUrl,
          connectionDetails.participantToken,
        );

        activeSessionRef.current = connectionDetails;
        cleanupInFlightRef.current = false;

        await room.localParticipant.setMicrophoneEnabled(
          userChoices.audioEnabled,
          userChoices.audioEnabled
            ? { deviceId: toCaptureDeviceId(userChoices.audioDeviceId) }
            : undefined,
        );

        await room.localParticipant.setCameraEnabled(
          userChoices.videoEnabled,
          userChoices.videoEnabled
            ? { deviceId: toCaptureDeviceId(userChoices.videoDeviceId) }
            : undefined,
        );

        setSessionMediaMode(userChoices.videoEnabled ? "video" : "audio");
        setSession(connectionDetails);
      } catch (error) {
        setConnectError(
          error instanceof Error ? error.message : "Failed to join session",
        );
        if (room.state !== ConnectionState.Disconnected) {
          await room.disconnect();
        }
        await cleanupRoom();
      } finally {
        setIsConnecting(false);
      }
    },
    [cleanupRoom, isConnecting, mode, room, scenarioKey],
  );

  if (session) {
    return (
      <div data-lk-theme="default" className="min-h-[80vh]">
        <RoomContext.Provider value={room}>
          <Assistant
            mediaMode={sessionMediaMode}
            title={title}
            description={description}
            highlights={highlights}
          />
        </RoomContext.Provider>
      </div>
    );
  }

  return (
    <div
      data-lk-theme="default"
      className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(360px,420px)]"
    >
      <section className="rounded-3xl border border-white/10 bg-black/20 p-6 text-white shadow-2xl backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/55">
          {mode === "video" ? "Video session" : "Audio session"}
        </p>
        <h1 className="mt-3 text-3xl font-semibold">{title}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-white/70">
          {description}
        </p>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {highlights.map((highlight) => (
            <div
              key={highlight}
              className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/75"
            >
              {highlight}
            </div>
          ))}
        </div>
        {connectError ? (
          <div className="mt-6 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {connectError}
          </div>
        ) : null}
      </section>

      <section className="rounded-3xl border border-white/10 bg-(--lk-bg) p-6 shadow-2xl">
        <div className="mx-auto max-w-md">
          <PreJoin
            defaults={{
              audioEnabled: true,
              videoEnabled: mode === "video",
            }}
            onError={onDeviceFailure}
            onSubmit={(choices) => {
              void handleJoin(choices);
            }}
            onValidate={() => true}
            persistUserChoices
            joinLabel={isConnecting ? "Joining..." : "Join session"}
          />
        </div>
      </section>
    </div>
  );
}
