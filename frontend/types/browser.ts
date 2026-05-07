export interface BrowserBreadcrumb {
  label: string;
  prefix: string;
}

export interface BrowserFolderEntry {
  name: string;
  prefix: string;
}

export interface BrowserFileEntry {
  name: string;
  path: string;
  size: number | null;
  updatedAt: string | null;
  contentType: string | null;
}

export interface BrowserListResponse {
  bucketName: string;
  rootPrefix: string;
  currentPrefix: string;
  breadcrumbs: BrowserBreadcrumb[];
  folders: BrowserFolderEntry[];
  files: BrowserFileEntry[];
}