import { NextResponse } from 'next/server';
import { listBrowserPrefix } from '@/lib/gcs-browser';

export const runtime = 'nodejs';
export const revalidate = 0;

function getStatusCode(error: unknown) {
  if (!(error instanceof Error)) {
    return 500;
  }

  if (error.message === 'Relative path traversal is not allowed') {
    return 400;
  }

  if (error.message === 'GCP_BUCKET_NAME is not configured') {
    return 500;
  }

  return 500;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const prefix = searchParams.get('prefix') ?? '';

  try {
    const response = await listBrowserPrefix(prefix);
    return NextResponse.json(response, {
      headers: {
        'Cache-Control': 'no-store',
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to list bucket files';
    return NextResponse.json(
      { error: message },
      {
        status: getStatusCode(error),
        headers: {
          'Cache-Control': 'no-store',
        },
      }
    );
  }
}