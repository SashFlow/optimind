'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const modes = [
  { id: 'audio', label: 'Audio Assistant' },
  { id: 'avatar', label: 'Avatar Assistant' },
] as const;

const agents = [
  {
    name: 'Sanjay',
    url: '/sanjay.mp4',
  },
  {
    name: 'Samira',
    url: '/simran.mp4',
  },
];

const popularIndianLanguages = [
  'English',
  'Hindi',
  'Marathi',
  'Bengali',
];

type Mode = (typeof modes)[number]['id'];

function AudioWaveformPreview() {
  const bars = [40, 66, 52, 78, 60, 48, 70, 56, 74, 44, 64, 50];

  return (
    <div className="bg-muted/40 flex aspect-[3/2] w-full items-end justify-center gap-1 rounded-lg border px-4 py-3">
      {bars.map((height, index) => (
        <span
          key={`${height}-${index}`}
          className="bg-primary/80 inline-block w-2 rounded-full"
          style={{ height: `${height}%` }}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

function AvatarPlaceholderPreview({ url }: { url: string }) {
  return <video src={url} autoPlay loop muted />;
}

export default function Page() {
  const [selectedMode, setSelectedMode] = useState<Mode>('avatar');
  const [selectedAgentSlug, setSelectedAgentSlug] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('English');

  const nextHref =
    selectedAgentSlug == null
      ? null
      : `/${selectedMode}/medical-examination?language=${selectedLanguage}&selectedAgent=${selectedAgentSlug}`;

  return (
    <main className="bg-background min-h-screen">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-6 py-10 md:px-10">
        <div className="space-y-3">
          <h1 className="text-4xl font-semibold tracking-tight">Sashflow</h1>
          <p className="text-muted-foreground max-w-2xl">
            Explore audio and avatar Medical Examination Assistants.
          </p>
        </div>

        <section className="space-y-6">
          <div className="flex w-full flex-wrap items-center justify-center gap-3">
            {modes.map((mode) => (
              <Button
                key={mode.id}
                variant={selectedMode === mode.id ? 'default' : 'outline'}
                onClick={() => {
                  setSelectedMode(mode.id);
                  setSelectedAgentSlug(null);
                }}
              >
                {mode.label}
              </Button>
            ))}
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-2">
            {agents.map((agent) => {
              const isSelected = agent.name === selectedAgentSlug;

              return (
                <Card
                  key={agent.name}
                  className={isSelected ? 'border-primary ring-primary/20 ring-2' : undefined}
                >
                  <CardHeader className="space-y-4">
                    {selectedMode === 'audio' ? (
                      <AudioWaveformPreview />
                    ) : (
                      <AvatarPlaceholderPreview url={agent.url} />
                    )}
                    <CardTitle className="text-center text-base">{agent.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Button
                      className="w-full"
                      variant={isSelected ? 'default' : 'outline'}
                      onClick={() => setSelectedAgentSlug(agent.name)}
                    >
                      {isSelected ? 'Selected' : 'Select'}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-2">
              <p className="text-sm font-medium">Preferred Language</p>
              <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                <SelectTrigger className="w-[260px]">
                  <SelectValue placeholder="Select a language" />
                </SelectTrigger>
                <SelectContent>
                  {popularIndianLanguages.map((language) => (
                    <SelectItem key={language} value={language}>
                      {language}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {nextHref ? (
              <Button asChild className="w-full sm:w-auto">
                <Link href={nextHref}>Next</Link>
              </Button>
            ) : (
              <Button className="w-full sm:w-auto" disabled>
                Next
              </Button>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
