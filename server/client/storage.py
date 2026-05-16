import os

from google.cloud import storage
from dotenv import load_dotenv


class _GCPStorageClientProxy:
    """Lazy GCP storage client that resolves credentials when first used."""

    def __init__(self) -> None:
        self._client = None

    def _build_client(self):
        load_dotenv()
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if creds_path:
            return storage.Client.from_service_account_json(creds_path)

        default_creds = "./creds.json"
        if os.path.exists(default_creds):
            return storage.Client.from_service_account_json(default_creds)

        return storage.Client()

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def __getattr__(self, item):
        return getattr(self.client, item)


gcp_storage_client = _GCPStorageClientProxy()
