"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

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
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-6 py-10 md:px-10">
        <div className="space-y-4">
          <Button asChild variant="ghost" className="pl-0">
            <Link href="/">
              <ArrowLeft className="size-4" />
              Back
            </Link>
          </Button>

          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-muted-foreground">
              Audio
            </p>
            <h1 className="text-4xl font-semibold tracking-tight">
              {scenario.title}
            </h1>
            <p className="max-w-2xl text-base leading-7 text-muted-foreground">
              {scenario.description}
            </p>
          </div>
        </div>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle>Scenario Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-6 text-muted-foreground">
              This page is the dedicated route for the{" "}
              <strong>{scenario.title}</strong> audio scenario. You can use it
              as the starting point for wiring in custom flows, voice
              assistants, or scenario-specific UI.
            </p>

            <div>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-foreground">
                Key Capabilities
              </h2>
              <ul className="space-y-3">
                {scenario.highlights.map((highlight) => (
                  <li
                    key={highlight}
                    className="rounded-lg border border-border/70 bg-muted/30 px-4 py-3 text-sm text-muted-foreground"
                  >
                    {highlight}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
