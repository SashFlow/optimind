import { Hono } from "hono";
import { handle } from "hono/vercel";
import { ConnectionDetails } from "@/types";
import {
  AccessToken,
  AccessTokenOptions,
  RoomServiceClient,
  VideoGrant,
} from "livekit-server-sdk";
import { v4 as uuidv4 } from "uuid";

const app = new Hono().basePath("/api");

function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  roomMetadata: string,
) {
  const at = new AccessToken(
    process.env.LIVEKIT_API_KEY,
    process.env.LIVEKIT_API_SECRET,
    {
      ...userInfo,
      ttl: "15m",
    },
  );
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };
  at.addGrant(grant);
  at.metadata = roomMetadata;
  return at.toJwt();
}

function getRequiredEnv(name: "LIVEKIT_URL" | "LIVEKIT_API_KEY" | "LIVEKIT_API_SECRET") {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is not defined`);
  }
  return value;
}

function createRoomName(roomMetadata?: string) {
  const base = roomMetadata
    ? roomMetadata.replace(/[^a-z0-9-]+/gi, "-").replace(/-+/g, "-").toLowerCase()
    : "session";

  return `optimind-${base}-${uuidv4()}`;
}

function createRoomServiceClient() {
  return new RoomServiceClient(
    getRequiredEnv("LIVEKIT_URL"),
    getRequiredEnv("LIVEKIT_API_KEY"),
    getRequiredEnv("LIVEKIT_API_SECRET"),
  );
}

app.post("/token", async (c) => {
  const body = await c.req.json();
  const room_name = body.room_name ?? createRoomName(body.room_metadata);
  const participant_name = body.participant_name ?? "Demo User";
  const participant_identity = body.participant_identity ?? uuidv4();
  const participant_metadata = body.participant_metadata;
  const participant_attributes = body.participant_attributes;
  const room_metadata = body.room_metadata ?? "";

  try {
    const livekitUrl = getRequiredEnv("LIVEKIT_URL");
    getRequiredEnv("LIVEKIT_API_KEY");
    getRequiredEnv("LIVEKIT_API_SECRET");

    // Generate participant token
    const participantToken = await createParticipantToken(
      {
        identity: participant_identity,
        name: participant_name,
        metadata: participant_metadata,
        attributes: participant_attributes,
      },
      room_name,
      room_metadata,
    );
    // Return connection details
    const data: ConnectionDetails = {
      serverUrl: livekitUrl,
      participantToken: participantToken,
      roomName: room_name,
      participantIdentity: participant_identity,
    };
    return c.json(data, 200);
  } catch (error) {
    if (error instanceof Error) {
      console.error(error);
      return c.text(error.message, 500);
    }

    return c.text("Internal Server Error", 500);
  }
});

app.post("/room/cleanup", async (c) => {
  const body = await c.req.json();
  const roomName = body.room_name;

  if (typeof roomName !== "string" || roomName.length === 0) {
    return c.text("room_name is required", 400);
  }
  if (!roomName.startsWith("optimind-")) {
    return c.text("room_name is invalid", 400);
  }

  try {
    const roomService = createRoomServiceClient();
    const rooms = await roomService.listRooms([roomName]);

    if (rooms.length === 0) {
      return c.json({ deleted: false, reason: "room-not-found" }, 200);
    }

    await roomService.deleteRoom(roomName);
    return c.json({ deleted: true, roomName }, 200);
  } catch (error) {
    if (error instanceof Error) {
      console.error(error);
      return c.text(error.message, 500);
    }

    return c.text("Internal Server Error", 500);
  }
});

export const POST = handle(app);
