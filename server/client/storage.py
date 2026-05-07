import os

import boto3
from dotenv import load_dotenv


class _S3ClientProxy:
    """Lazy S3 client that resolves env vars only when first used."""

    def __init__(self) -> None:
        self._client = None

    def _build_client(self):
        # Ensure .env values are available even if this module is imported early.
        load_dotenv()
        session = boto3.Session(
            aws_access_key_id=os.getenv("S3_ACCESS_KEY", "").strip(),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY", "").strip(),
            region_name=os.getenv("S3_REGION", "").strip(),
        )
        endpoint = os.getenv("S3_ENDPOINT", "").strip() or None
        return session.client("s3", endpoint_url=endpoint)

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def __getattr__(self, item):
        return getattr(self.client, item)


s3_client = _S3ClientProxy()
