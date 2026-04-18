"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const avatarScenarios = {
  "medical-officer": {
    title: "Medical Officer",
    description:
      "A visual healthcare assistant designed to support patient guidance, intake conversations, and care-related interactions.",
    highlights: [
      "Guide patients through intake and onboarding steps",
      "Answer common healthcare support questions",
      "Assist with appointment preparation and follow-up context",
    ],
  },
  "study-partner": {
    title: "Study Partner",
    description:
      "An interactive avatar companion that helps learners review concepts, practice responses, and stay on track with study goals.",
    highlights: [
      "Explain concepts in a conversational format",
      "Support mock practice and revision sessions",
      "Encourage structured learning and study planning",
    ],
  },
  "help-desk-partner": {
    title: "Help Desk Partner",
    description:
      "A visual support assistant for troubleshooting workflows, answering user questions, and guiding people through common issues.",
    highlights: [
      "Walk users through troubleshooting steps",
      "Answer product and support questions clearly",
      "Provide a friendly first-line support experience",
    ],
  },
} as const;

export default function AvatarScenarioPage() {
  const params = useParams<{ slug: string }>();

  const scenario = useMemo(() => {
    const slug = params?.slug;
    if (!slug) return null;
    return avatarScenarios[slug as keyof typeof avatarScenarios] ?? null;
  }, [params]);

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-8 md:px-10">
        <div>
          <Button asChild variant="ghost" className="mb-4 pl-0">
            <Link href="/" className="p-0">
              <ArrowLeft className="size-4" />
              Back
            </Link>
          </Button>

          <h1 className="text-3xl font-semibold tracking-tight">
            {scenario?.title ?? "Avatar Scenario"}
          </h1>
        </div>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle>Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="leading-7 text-muted-foreground">
              {scenario?.description ??
                "This avatar scenario page is ready for future implementation details, demos, and integrations."}
            </p>

            <div className="space-y-3">
              <h2 className="text-lg font-medium">Key capabilities</h2>
              <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-muted-foreground">
                {(
                  scenario?.highlights ?? [
                    "Present scenario-specific details",
                    "Add avatar experience components",
                    "Extend this page with live interactions",
                  ]
                ).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
