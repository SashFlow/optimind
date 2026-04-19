"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { avatarScenarios } from "@/lib/scenarios";
import { ScenarioSession } from "@/components/player/ScenarioSession";

export default function AvatarScenarioPage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug;
  const scenario = slug
    ? avatarScenarios[slug as keyof typeof avatarScenarios] ?? null
    : null;

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
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8 md:px-10">
        <Button asChild variant="ghost" className="mb-4 pl-0">
          <Link href="/" className="p-0">
            <ArrowLeft className="size-4" />
            Back
          </Link>
        </Button>
        <ScenarioSession
          mode="video"
          scenarioKey={slug}
          title={scenario.title}
          description={scenario.description}
          highlights={[...scenario.highlights]}
        />
      </div>
    </main>
  );
}
