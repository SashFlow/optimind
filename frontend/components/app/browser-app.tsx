'use client';

import { useEffect, useState, useTransition } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowClockwise,
  ArrowSquareOut,
  DownloadSimple,
  File,
  Folder,
  WarningCircle,
} from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatBytes, formatUpdatedAt } from '@/lib/browser-format';
import type { BrowserListResponse } from '@/types/browser';

async function fetchBrowserData(prefix: string, signal: AbortSignal) {
  const query = new URLSearchParams();
  if (prefix) {
    query.set('prefix', prefix);
  }

  const response = await fetch(`/api/browser/list?${query.toString()}`, {
    cache: 'no-store',
    signal,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(payload?.error ?? 'Failed to load bucket contents');
  }

  return (await response.json()) as BrowserListResponse;
}

export function BrowserApp() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [data, setData] = useState<BrowserListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [requestVersion, setRequestVersion] = useState(0);
  const currentPrefix = searchParams.get('prefix') ?? '';

  useEffect(() => {
    const controller = new AbortController();

    setIsLoading(true);
    setError(null);

    fetchBrowserData(currentPrefix, controller.signal)
      .then((response) => {
        setData(response);
      })
      .catch((fetchError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setError(
          fetchError instanceof Error ? fetchError.message : 'Failed to load bucket contents'
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      });

    return () => controller.abort();
  }, [currentPrefix, requestVersion]);

  function navigateToPrefix(prefix: string) {
    startTransition(() => {
      const nextSearchParams = new URLSearchParams(searchParams.toString());
      if (prefix) {
        nextSearchParams.set('prefix', prefix);
      } else {
        nextSearchParams.delete('prefix');
      }

      const query = nextSearchParams.toString();
      router.push(query ? `/browser?${query}` : '/browser');
    });
  }

  function handleRefresh() {
    startTransition(() => {
      setRequestVersion((value) => value + 1);
    });
  }

  const bucketLabel = data?.bucketName ?? 'GCS bucket';
  const rootLabel = data?.rootPrefix ? `/${data.rootPrefix}` : '/';

  return (
    <main className="bg-background min-h-screen px-4 py-8 md:px-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="space-y-2">
            <p className="text-muted-foreground text-sm font-medium tracking-[0.22em] uppercase">
              Bucket Browser
            </p>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">{bucketLabel}</h1>
              <p className="text-muted-foreground text-sm">
                Read-only access rooted at{' '}
                <span className="text-foreground font-medium">{rootLabel}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isPending || isLoading}
            >
              <ArrowClockwise className="size-4" />
              Refresh
            </Button>
          </div>
        </div>

        <Card className="overflow-hidden">
          <CardHeader className="border-b">
            <CardTitle>Contents</CardTitle>
            <CardDescription>
              Browse folders, inspect metadata, and download files directly from Google Cloud
              Storage.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="flex flex-wrap items-center gap-2">
              {(data?.breadcrumbs ?? [{ label: 'Root', prefix: '' }]).map((crumb) => (
                <Button
                  key={`${crumb.label}-${crumb.prefix}`}
                  variant={crumb.prefix === currentPrefix ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => navigateToPrefix(crumb.prefix)}
                  disabled={isPending || isLoading}
                >
                  {crumb.label}
                </Button>
              ))}
            </div>

            {error ? (
              <div className="border-destructive/30 bg-destructive/5 text-destructive flex items-start gap-3 rounded-xl border p-4 text-sm">
                <WarningCircle className="mt-0.5 size-5 shrink-0" weight="fill" />
                <div>
                  <p className="font-medium">Unable to load bucket contents</p>
                  <p className="text-destructive/80 mt-1">{error}</p>
                </div>
              </div>
            ) : null}

            <div className="overflow-hidden rounded-xl border">
              <div className="bg-muted/40 text-muted-foreground hidden grid-cols-[minmax(0,1.6fr)_140px_180px_120px] gap-4 border-b px-4 py-3 text-xs font-medium tracking-[0.18em] uppercase md:grid">
                <span>Name</span>
                <span>Size</span>
                <span>Updated</span>
                <span className="text-right">Action</span>
              </div>

              {isLoading ? (
                <div className="space-y-3 p-4">
                  {Array.from({ length: 6 }).map((_, index) => (
                    <div key={index} className="bg-muted/50 h-16 animate-pulse rounded-lg" />
                  ))}
                </div>
              ) : null}

              {!isLoading &&
              !error &&
              data &&
              data.folders.length === 0 &&
              data.files.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
                  <Folder className="text-muted-foreground size-10" />
                  <div>
                    <p className="font-medium">This folder is empty</p>
                    <p className="text-muted-foreground text-sm">
                      Choose another breadcrumb or upload files to this prefix.
                    </p>
                  </div>
                </div>
              ) : null}

              {!isLoading && !error && data ? (
                <div className="divide-y">
                  {data.folders.map((folder) => (
                    <button
                      key={folder.prefix}
                      type="button"
                      className="hover:bg-muted/40 grid w-full gap-3 px-4 py-4 text-left transition-colors md:grid-cols-[minmax(0,1.6fr)_140px_180px_120px] md:items-center"
                      onClick={() => navigateToPrefix(folder.prefix)}
                    >
                      <span className="flex min-w-0 items-center gap-3 font-medium">
                        <Folder className="text-primary size-5 shrink-0" weight="duotone" />
                        <span className="truncate">{folder.name}</span>
                      </span>
                      <span className="text-muted-foreground text-sm">Folder</span>
                      <span className="text-muted-foreground text-sm">-</span>
                      <span className="flex justify-start md:justify-end">
                        <span className="text-primary inline-flex items-center gap-2 text-sm">
                          Open
                          <ArrowSquareOut className="size-4" />
                        </span>
                      </span>
                    </button>
                  ))}

                  {data.files.map((file) => {
                    const downloadHref = `/api/browser/download?path=${encodeURIComponent(file.path)}`;

                    return (
                      <div
                        key={file.path}
                        className="grid gap-3 px-4 py-4 md:grid-cols-[minmax(0,1.6fr)_140px_180px_120px] md:items-center"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <File className="text-muted-foreground size-5 shrink-0" />
                          <div className="min-w-0">
                            <p className="truncate font-medium">{file.name}</p>
                            <p className="text-muted-foreground truncate text-sm">
                              {file.contentType ?? 'Unknown type'}
                            </p>
                          </div>
                        </div>
                        <span className="text-muted-foreground text-sm">
                          {formatBytes(file.size)}
                        </span>
                        <span className="text-muted-foreground text-sm">
                          {formatUpdatedAt(file.updatedAt)}
                        </span>
                        <span className="flex justify-start md:justify-end">
                          <Button asChild variant="outline" size="sm">
                            <a href={downloadHref}>
                              <DownloadSimple className="size-4" />
                              Download
                            </a>
                          </Button>
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
