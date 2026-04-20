'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { ArrowLeftIcon, WarningIcon } from '@phosphor-icons/react/dist/ssr';
import type { AppConfig } from '@/app-config';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { scenarios } from '@/constants';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import { Button } from '../ui/button';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

interface AppProps {
  appConfig: AppConfig;
  scenarioType: string;
}

type ScenarioSlug = keyof typeof scenarios;

function isScenarioSlug(value: string): value is ScenarioSlug {
  return value in scenarios;
}

export function App({ appConfig, scenarioType }: AppProps) {
  const params = useParams();
  const slugParam = params?.slug;
  const slug = Array.isArray(slugParam) ? slugParam[0] : slugParam;
  const scenario = slug && isScenarioSlug(slug) ? scenarios[slug] : null;

  const tokenSource = TokenSource.endpoint(
    `/api/token?scenarioType=${encodeURIComponent(scenarioType)}&slug=${encodeURIComponent(slug ?? '')}`
  );

  const session = useSession(
    tokenSource,
    appConfig.agentName ? { agentName: appConfig.agentName } : undefined
  );

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
            <h1 className="text-3xl font-semibold tracking-tight">Audio Scenario Not Found</h1>
            <p className="text-muted-foreground mt-3">
              The requested audio scenario does not exist.
            </p>
          </div>
        </div>
      </main>
    );
  }
  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <main className="grid h-svh grid-cols-1 place-content-center">
        <ViewController appConfig={appConfig} />
      </main>
      <StartAudioButton label="Start" />
      <Toaster
        icons={{
          warning: <WarningIcon weight="bold" />,
        }}
        position="top-center"
        className="toaster group"
        style={
          {
            '--normal-bg': 'var(--popover)',
            '--normal-text': 'var(--popover-foreground)',
            '--normal-border': 'var(--border)',
          } as React.CSSProperties
        }
      />
    </AgentSessionProvider>
  );
}
