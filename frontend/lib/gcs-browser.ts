import { Storage } from '@google-cloud/storage';
import type { BrowserBreadcrumb, BrowserFileEntry, BrowserListResponse } from '@/types/browser';

const bucketName = process.env.GCP_BUCKET_NAME?.trim() ?? '';
const rootPrefix = normalizePrefix(process.env.GCP_BROWSER_PREFIX ?? '');

let storageClient: Storage | null = null;

function getStorageClient() {
  if (storageClient) {
    return storageClient;
  }

  const credentials = JSON.parse(process.env.GCP_SERVICE_ACCOUNT || '{}');
  storageClient = new Storage({
    projectId: credentials.project_id,
    credentials,
  });
  return storageClient;
}

function assertBucketConfigured() {
  if (!bucketName) {
    throw new Error('GCP_BUCKET_NAME is not configured');
  }
}

function normalizeSegments(input: string) {
  return input
    .replace(/\\/g, '/')
    .split('/')
    .filter(Boolean)
    .map((segment) => segment.trim())
    .map((segment) => {
      if (segment === '.' || segment === '..') {
        throw new Error('Relative path traversal is not allowed');
      }

      return segment;
    });
}

function normalizePrefix(input: string) {
  const segments = normalizeSegments(input);
  if (segments.length === 0) {
    return '';
  }

  return `${segments.join('/')}/`;
}

function normalizeObjectPath(input: string) {
  return normalizeSegments(input).join('/');
}

function toActualPrefix(relativePrefix: string) {
  const normalizedPrefix = normalizePrefix(relativePrefix);
  return `${rootPrefix}${normalizedPrefix}`;
}

function toActualObjectPath(relativePath: string) {
  const normalizedPath = normalizeObjectPath(relativePath);
  return `${rootPrefix}${normalizedPath}`;
}

function toRelativePrefix(actualPrefix: string) {
  if (!actualPrefix.startsWith(rootPrefix)) {
    throw new Error('Requested prefix is outside the configured browser root');
  }

  return normalizePrefix(actualPrefix.slice(rootPrefix.length));
}

function toRelativePath(actualPath: string) {
  if (!actualPath.startsWith(rootPrefix)) {
    throw new Error('Requested object is outside the configured browser root');
  }

  return normalizeObjectPath(actualPath.slice(rootPrefix.length));
}

function getDisplayName(value: string) {
  const normalizedValue = value.endsWith('/') ? value.slice(0, -1) : value;
  const segments = normalizedValue.split('/').filter(Boolean);
  return segments.at(-1) ?? normalizedValue;
}

function toBreadcrumbs(relativePrefix: string): BrowserBreadcrumb[] {
  const segments = relativePrefix.split('/').filter(Boolean);

  return [
    { label: 'Root', prefix: '' },
    ...segments.map((segment, index) => ({
      label: segment,
      prefix: segments.slice(0, index + 1).join('/') + '/',
    })),
  ];
}

function mapFileEntry(file: {
  name: string;
  metadata?: { size?: string | number; updated?: string; contentType?: string };
}): BrowserFileEntry {
  const rawSize = file.metadata?.size;
  const size = typeof rawSize === 'number' ? rawSize : rawSize ? Number(rawSize) : null;

  return {
    name: getDisplayName(file.name),
    path: toRelativePath(file.name),
    size: Number.isFinite(size) ? size : null,
    updatedAt: file.metadata?.updated ?? null,
    contentType: file.metadata?.contentType ?? null,
  };
}

export async function listBrowserPrefix(relativePrefix = ''): Promise<BrowserListResponse> {
  assertBucketConfigured();

  const currentPrefix = normalizePrefix(relativePrefix);
  const actualPrefix = toActualPrefix(currentPrefix);
  const [files, , apiResponse] = await getStorageClient().bucket(bucketName).getFiles({
    prefix: actualPrefix,
    delimiter: '/',
    autoPaginate: false,
  });
  const responseWithPrefixes = apiResponse as { prefixes?: string[] } | undefined;

  const folders = (responseWithPrefixes?.prefixes ?? [])
    .map((prefix) => toRelativePrefix(prefix))
    .filter((prefix) => prefix !== currentPrefix)
    .sort((left, right) => left.localeCompare(right))
    .map((prefix) => ({
      name: getDisplayName(prefix),
      prefix,
    }));

  const listedFiles = files
    .filter((file) => file.name !== actualPrefix && !file.name.endsWith('/'))
    .sort((left, right) => left.name.localeCompare(right.name))
    .map((file) => mapFileEntry(file));

  return {
    bucketName,
    rootPrefix,
    currentPrefix,
    breadcrumbs: toBreadcrumbs(currentPrefix),
    folders,
    files: listedFiles,
  };
}

export async function getDownloadUrl(relativePath: string) {
  assertBucketConfigured();

  const normalizedPath = normalizeObjectPath(relativePath);
  if (!normalizedPath) {
    throw new Error('File path is required');
  }

  const actualPath = toActualObjectPath(normalizedPath);
  const file = getStorageClient().bucket(bucketName).file(actualPath);
  const [exists] = await file.exists();

  if (!exists) {
    throw new Error('File not found');
  }

  const downloadName = getDisplayName(normalizedPath);
  const [signedUrl] = await file.getSignedUrl({
    version: 'v4',
    action: 'read',
    expires: Date.now() + 15 * 60 * 1000,
    responseDisposition: `attachment; filename="${downloadName}"`,
  });

  return signedUrl;
}

export function getBrowserConfig() {
  assertBucketConfigured();

  return {
    bucketName,
    rootPrefix,
  };
}
