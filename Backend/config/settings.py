import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GCP_PROJECT_ID: str
    GCP_LOCATION: str = "us-central1"
    DOCUMENT_AI_PROCESSOR_ID: str
    DOCUMENT_AI_LOCATION: str = "us"
    GCS_BUCKET_NAME: str = "investment_memo_ai"
    # Brevo (formerly Sendinblue)
    BREVO_API_KEY: str
    GEMINI_API_KEY: str
    FROM_EMAIL: str = "vanikmanthan@gmail.com"
    BASE_URL: str = "https://studio--studio-6714467766-8a879.us-central1.hosted.app"
    FRONTEND_URL: str = "https://studio--studio-6714467766-8a879.us-central1.hosted.app"
    
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "./firebase-service-account.json"
    
    # Local Storage Fallback
    USE_LOCAL_STORAGE: bool = True
    LOCAL_UPLOAD_DIR: str = "uploads"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
