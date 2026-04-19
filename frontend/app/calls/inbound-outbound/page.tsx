"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { audioScenarios } from "@/lib/scenarios";
import { ScenarioSession } from "@/components/player/ScenarioSession";

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

  if (!scenario || !slug) {
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
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8 md:px-10">
        <Button asChild variant="ghost" className="mb-4 pl-0">
          <Link href="/" className="p-0">
            <ArrowLeft className="size-4" />
            Back
          </Link>
        </Button>
        <ScenarioSession
          mode="audio"
          scenarioKey={slug}
          title={scenario.title}
          description={scenario.description}
          highlights={[...scenario.highlights]}
        />
      </div>
    </main>
  );
}
