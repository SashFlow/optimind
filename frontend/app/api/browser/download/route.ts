import { NextResponse } from 'next/server';
import { getDownloadUrl } from '@/lib/gcs-browser';

export const runtime = 'nodejs';
export const revalidate = 0;

function getStatusCode(error: unknown) {
  if (!(error instanceof Error)) {
    return 500;
  }

  if (
    error.message === 'Relative path traversal is not allowed' ||
    error.message === 'File path is required'
  ) {
    return 400;
  }

  if (error.message === 'File not found') {
    return 404;
  }

  return 500;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const filePath = searchParams.get('path') ?? '';

  try {
    const downloadUrl = await getDownloadUrl(filePath);
    return NextResponse.redirect(downloadUrl, {
      status: 302,
      headers: {
        'Cache-Control': 'no-store',
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to create download URL';
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
