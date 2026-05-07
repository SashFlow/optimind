import os
from dotenv import load_dotenv
from client.storage import s3_client

load_dotenv()

s3_bucket = os.getenv("S3_BUCKET", "voice").strip()

s3_key = "test/test.xlsx"
report_path = "/Users/sahil/Dev/Company/sashflow/optimind/server/reports/Sahil_voice_assistant_room_7603_20260507_183424.xlsx"
s3_client.upload_file(report_path, s3_bucket, s3_key)
