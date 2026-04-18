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
  return at.toJwt();
}

app.post("/token", async (c) => {
  const roomType = c.req.query("room");
  const type = c.req.query("type");

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
    const participantIdentity = `lokibots_voice_assistant_user_${roomType}_${type}_${uuidv4()}`;
    const roomName = `lokibots_voice_assistant_room_${roomType}_${type}_${uuidv4()}`;
    const participantToken = await createParticipantToken(
      { identity: participantIdentity },
      roomName,
    );
    console.log(roomType, type, roomName);
    // Return connection details
    const data: ConnectionDetails = {
      serverUrl: process.env.LIVEKIT_URL,
      roomName,
      participantToken: participantToken,
      participantName: participantIdentity,
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
