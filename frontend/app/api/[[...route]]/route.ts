import { Hono } from "hono";
import { handle } from "hono/vercel";
import { ConnectionDetails } from "@/types";
import {
  AccessToken,
  AccessTokenOptions,
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

app.post("/token", async (c) => {
  const body = await c.req.json();
  const room_name = body.room_name ?? "Demo Room";
  const participant_name = body.participant_name ?? "Demo User";
  const participant_identity = body.participant_identity ?? uuidv4();
  const participant_metadata = body.participant_metadata;
  const participant_attributes = body.participant_attributes;
  const room_metadata = body.room_metadata;

  try {
    if (process.env.LIVEKIT_URL === undefined) {
      throw new Error("LIVEKIT_URL is not defined");
    }
    if (process.env.LIVEKIT_API_KEY === undefined) {
      throw new Error("LIVEKIT_API_KEY is not defined");
    }
    if (process.env.LIVEKIT_API_SECRET === undefined) {
      throw new Error("LIVEKIT_API_SECRET is not defined");
    }

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
      serverUrl: process.env.LIVEKIT_URL,
      participantToken: participantToken,
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

export const POST = handle(app);
