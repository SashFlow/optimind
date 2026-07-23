import { NextResponse } from 'next/server';
import { AgentDispatchClient, RoomServiceClient } from 'livekit-server-sdk';
import { normalizePhoneNumber } from '@/lib/phone';

// NOTE: expected in `.env.local` / `.env`:
// LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, AGENT_NAME
// Outbound PSTN dial uses SIP_OUTBOUND_TRUNK_ID on the agent worker (verify with: lk sip outbound list).
const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;
const AGENT_NAME = process.env.AGENT_NAME || 'demo-agent';

export const revalidate = 0;

function livekitHttpHost(url: string): string {
  return url.replace(/^wss:/, 'https:').replace(/^ws:/, 'http:');
}

type OutboundCallBody = {
  phoneNumber?: string;
  slug?: string;
  language?: string;
  selectedAgent?: string;
};

export async function POST(req: Request) {
  try {
    if (!LIVEKIT_URL) {
      throw new Error('LIVEKIT_URL is not defined');
    }
    if (!API_KEY) {
      throw new Error('LIVEKIT_API_KEY is not defined');
    }
    if (!API_SECRET) {
      throw new Error('LIVEKIT_API_SECRET is not defined');
    }

    const body = (await req.json()) as OutboundCallBody;
    const phoneNumber = normalizePhoneNumber(body.phoneNumber ?? '');
    const slug = (body.slug ?? '').trim();
    const language = (body.language ?? 'English').trim() || 'English';
    const selectedAgent = (body.selectedAgent ?? 'Sanjay').trim() || 'Sanjay';

    if (!phoneNumber) {
      return NextResponse.json({ error: 'Invalid phone number' }, { status: 400 });
    }
    if (!slug) {
      return NextResponse.json({ error: 'Missing scenario slug' }, { status: 400 });
    }

    const host = livekitHttpHost(LIVEKIT_URL);
    const roomName = `PHONE_SESSION_${Math.floor(Math.random() * 100_000)}`;
    const metadata = JSON.stringify({
      interactionMode: 'audio',
      scenarioSlug: slug,
      scenarioType: 'phone',
      language,
      selectedAgent,
      phone_number: phoneNumber,
    });

    const roomClient = new RoomServiceClient(host, API_KEY, API_SECRET);
    const dispatchClient = new AgentDispatchClient(host, API_KEY, API_SECRET);

    await roomClient.createRoom({
      name: roomName,
      emptyTimeout: 5 * 60,
      metadata: `audio-${slug}`,
    });

    await dispatchClient.createDispatch(roomName, AGENT_NAME, { metadata });

    return NextResponse.json(
      { roomName, status: 'dispatched' },
      { headers: { 'Cache-Control': 'no-store' } }
    );
  } catch (error) {
    console.error(error);
    const message = error instanceof Error ? error.message : 'Failed to dispatch outbound call';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
