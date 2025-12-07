import secrets
from google.cloud import storage
from config.settings import settings

storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)

def generate_deal_id() -> str:
    """Generate a unique 6-character deal ID"""
    return secrets.token_hex(3)

def upload_to_gcs(file_content: bytes, destination_path: str) -> str:
    """Upload file to Google Cloud Storage"""
    blob = bucket.blob(destination_path)
    blob.upload_from_string(file_content)
    return f"gs://{settings.GCS_BUCKET_NAME}/{destination_path}"
