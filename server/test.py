import argparse
import csv
import io
import os
import random
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv

from client.storage import gcp_storage_client


def build_random_csv(rows: int) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "metric", "score", "captured_at_utc"])

    for index in range(rows):
        writer.writerow(
            [
                index + 1,
                random.choice(["heart_rate", "bp", "spo2", "weight"]),
                random.randint(40, 180),
                datetime.now(timezone.utc).isoformat(),
            ]
        )

    return buffer.getvalue().encode("utf-8")


def upload_random_csv(bucket_name: str, rows: int) -> str:
    object_key = f"test-uploads/random_csv_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}.csv"
    csv_bytes = build_random_csv(rows)

    bucket = gcp_storage_client.bucket(bucket_name)
    blob = bucket.blob(object_key)
    blob.upload_from_file(io.BytesIO(csv_bytes), content_type="text/csv")

    return f"gs://{bucket_name}/{object_key}"


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Generate a random CSV and upload it to Google Cloud Storage."
    )
    parser.add_argument(
        "--bucket",
        default=os.getenv("GCP_BUCKET_NAME", "").strip(),
        help="GCS bucket name. Defaults to GCP_BUCKET_NAME env var.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=25,
        help="Number of random rows to include in the CSV.",
    )
    args = parser.parse_args()

    if not args.bucket:
        raise SystemExit("Missing bucket. Set GCP_BUCKET_NAME or pass --bucket.")

    if args.rows <= 0:
        raise SystemExit("--rows must be greater than 0.")

    uploaded_uri = upload_random_csv(args.bucket, args.rows)
    print("Upload successful:", uploaded_uri)


if __name__ == "__main__":
    main()
