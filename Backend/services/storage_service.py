import os
import secrets
from google.cloud import storage
from config.settings import settings

# Initialize GCS client lazily or handle error if project not found
try:
    storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
    bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
except Exception as e:
    print(f"⚠️ Warning: Could not initialize GCS client: {e}")
    storage_client = None
    bucket = None

def generate_deal_id() -> str:
    """Generate a unique 6-character deal ID"""
    return secrets.token_hex(3)

def upload_to_gcs(file_content: bytes, destination_path: str) -> str:
    """
    Upload file to Google Cloud Storage.
    FALLBACK: If GCS fails (billing/auth), save locally.
    """
    use_local = settings.USE_LOCAL_STORAGE or bucket is None
    
    # Try GCS first if not forced to local
    if not use_local:
        try:
            blob = bucket.blob(destination_path)
            blob.upload_from_string(file_content)
            return f"gs://{settings.GCS_BUCKET_NAME}/{destination_path}"
        except Exception as e:
            print(f"⚠️ GCS Upload Failed ({e}). Falling back to local storage.")
            # Proceed to local save
    
    # Local Storage Fallback
    try:
        # Ensure directory exists
        local_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, os.path.dirname(destination_path))
        os.makedirs(local_dir, exist_ok=True)
        
        # Full local path
        filename = os.path.basename(destination_path)
        local_path = os.path.join(local_dir, filename)
        
        with open(local_path, "wb") as f:
            f.write(file_content)
            
        print(f"✅ Saved locally: {local_path}")
        
        # Return HTTP URL for local access
        # Assuming backend serves 'uploads/' at /uploads/
        # Construct public URL
        # Windows path handling for URL
        url_path = destination_path.replace("\\", "/")
        return f"{settings.BASE_URL}/{settings.LOCAL_UPLOAD_DIR}/{url_path}"
        
    except Exception as local_e:
        print(f"❌ Local Save Failed: {local_e}")
        raise local_e
