import boto3
import os

session = boto3.Session(
    aws_access_key_id=os.getenv("S3_ACCESS_KEY", "").strip(),
    aws_secret_access_key=os.getenv(
        "S3_SECRET_KEY",
        "",
    ).strip(),
    region_name=os.getenv("S3_REGION", "").strip(),
)

s3_client = session.client("s3", endpoint_url="")
