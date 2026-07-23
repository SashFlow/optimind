'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { ArrowLeftIcon } from '@phosphor-icons/react/dist/ssr';
import { WelcomeImage } from '@/components/app/welcome-view';
import { Button } from '@/components/ui/button';
import { scenarios } from '@/constants';
import { normalizePhoneNumber } from '@/lib/phone';
import { cn } from '@/lib/shadcn/utils';

type ScenarioSlug = keyof typeof scenarios;

function isScenarioSlug(value: string): value is ScenarioSlug {
  return value in scenarios;
}

type CallStatus = 'idle' | 'dialing' | 'dispatched' | 'error';

export function PhoneOutboundView() {
  const params = useParams();
  const searchParams = useSearchParams();
  const slugParam = params?.slug;
  const slug = Array.isArray(slugParam) ? slugParam[0] : slugParam;
  const scenario = slug && isScenarioSlug(slug) ? scenarios[slug] : null;
  const language = searchParams.get('language') || 'English';
  const selectedAgent = searchParams.get('selectedAgent') || 'Sanjay';

  const [phoneNumber, setPhoneNumber] = useState('');
  const [status, setStatus] = useState<CallStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [roomName, setRoomName] = useState<string | null>(null);

  if (!scenario || !slug) {
    return (
      <main className="bg-background min-h-screen">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-10 md:px-10">
          <div>
            <Button asChild variant="ghost" className="mb-4 pl-0">
              <Link href="/" className="p-0">
                <ArrowLeftIcon className="size-4" />
                Back
              </Link>
            </Button>
            <h1 className="text-3xl font-semibold tracking-tight">Phone Scenario Not Found</h1>
            <p className="text-muted-foreground mt-3">
              The requested phone scenario does not exist.
            </p>
          </div>
        </div>
      </main>
    );
  }

  const normalized = normalizePhoneNumber(phoneNumber);
  const canCall = Boolean(normalized) && status !== 'dialing';

  const handleCallMe = async () => {
    if (!normalized || status === 'dialing') return;

    setStatus('dialing');
    setErrorMessage(null);
    setRoomName(null);

    try {
      const res = await fetch('/api/outbound-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phoneNumber: normalized,
          slug,
          language,
          selectedAgent,
        }),
      });

      const data = (await res.json().catch(() => ({}))) as {
        roomName?: string;
        status?: string;
        error?: string;
      };

      if (!res.ok) {
        setStatus('error');
        setErrorMessage(data.error || 'Failed to start the outbound call.');
        return;
      }

      setRoomName(data.roomName ?? null);
      setStatus('dispatched');
    } catch {
      setStatus('error');
      setErrorMessage('Network error while starting the call. Please try again.');
    }
  };

  const handleReset = () => {
    setStatus('idle');
    setErrorMessage(null);
    setRoomName(null);
  };

  return (
    <main className="bg-background min-h-screen">
      <section className="bg-background mx-auto flex max-w-5xl flex-col items-center justify-center px-6 py-10 text-center md:px-10">
        <WelcomeImage />

        <p className="text-foreground text-3xl font-semibold tracking-tight">{scenario.title}</p>
        <p className="text-muted-foreground max-w-2xl pt-3 text-sm leading-6 md:text-base">
          Enter your phone number and we will call you. Answer to speak with {selectedAgent}.
        </p>

        <div className="mt-8 grid w-full gap-4 text-left md:grid-cols-2">
          <div className="border-border/70 bg-card rounded-2xl border p-6 shadow-sm">
            <h2 className="text-center text-sm font-semibold tracking-wide uppercase">
              Capabilities
            </h2>
            <ul className="mt-4 space-y-3 text-sm leading-6">
              {scenario.highlights.map((highlight) => (
                <li key={highlight} className="text-muted-foreground text-center">
                  {highlight}
                </li>
              ))}
            </ul>
          </div>

          <div className="border-border/70 bg-card rounded-2xl border p-6 shadow-sm">
            <h2 className="text-center text-sm font-semibold tracking-wide uppercase">
              Your phone number
            </h2>
            <label className="mt-4 block text-left text-sm font-medium" htmlFor="phone-number">
              Mobile number
            </label>
            <input
              id="phone-number"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="+91 98765 43210"
              value={phoneNumber}
              disabled={status === 'dialing' || status === 'dispatched'}
              onChange={(e) => setPhoneNumber(e.target.value)}
              className={cn(
                'border-input bg-background mt-2 flex h-10 w-full rounded-md border px-3 py-2 text-sm',
                'placeholder:text-muted-foreground focus-visible:ring-ring outline-none focus-visible:ring-2'
              )}
            />
            <p className="text-muted-foreground mt-2 text-xs leading-5">
              Use E.164 (e.g. +919876543210) or a 10-digit Indian mobile number.
            </p>
            {phoneNumber && !normalized && (
              <p className="text-destructive mt-2 text-xs">Enter a valid phone number.</p>
            )}
          </div>
        </div>

        {status === 'dispatched' && (
          <div className="border-border/70 bg-card mt-6 w-full max-w-lg rounded-2xl border p-4 text-sm">
            <p className="font-medium">Calling {normalized}…</p>
            <p className="text-muted-foreground mt-2 leading-6">
              Your phone should ring shortly. Answer to start the conversation.
              {roomName ? ` Session: ${roomName}.` : ''} If it does not ring, check the number and
              try again.
            </p>
          </div>
        )}

        {status === 'error' && errorMessage && (
          <div className="border-destructive/40 bg-destructive/5 text-destructive mt-6 w-full max-w-lg rounded-2xl border p-4 text-sm">
            {errorMessage}
          </div>
        )}

        <div className="mt-8 flex w-full flex-col justify-between gap-2 md:flex-row">
          {status === 'dispatched' ? (
            <Button
              size="lg"
              onClick={handleReset}
              className="w-full max-w-sm rounded-full font-mono text-xs font-bold tracking-wider uppercase"
            >
              Call another number
            </Button>
          ) : (
            <Button
              size="lg"
              disabled={!canCall}
              onClick={() => void handleCallMe()}
              className="w-full max-w-sm rounded-full font-mono text-xs font-bold tracking-wider uppercase"
            >
              {status === 'dialing' ? 'Calling…' : 'Call me'}
            </Button>
          )}
          <Button
            size="lg"
            asChild
            variant="secondary"
            className="w-full max-w-sm rounded-full font-mono text-xs font-bold tracking-wider uppercase"
          >
            <Link href="/">Go Back</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
