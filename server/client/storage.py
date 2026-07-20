import os

import boto3
from dotenv import load_dotenv


class _S3StorageClientProxy:
    """Lazy S3 client that resolves credentials when first used."""

    def __init__(self) -> None:
        self._client = None

    def _build_client(self):
        load_dotenv()
        endpoint = os.getenv("AWS_S3_ENDPOINT", "").strip() or None
        region = (
            os.getenv("AWS_REGION", "").strip()
            or os.getenv("AWS_DEFAULT_REGION", "").strip()
            or None
        )
        kwargs: dict = {
            "service_name": "s3",
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "").strip() or None,
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
            or None,
            "aws_session_token": os.getenv("AWS_SESSION_TOKEN", "").strip() or None,
            "region_name": region,
        }
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        return boto3.client(**{k: v for k, v in kwargs.items() if v is not None})

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def __getattr__(self, item):
        return getattr(self.client, item)


s3_storage_client = _S3StorageClientProxy()
