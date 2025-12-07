# import os
# from typing import Optional
# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     # Google Cloud Project
#     gcp_project_id: str
#     gcp_location: str = "us-central1"
    
#     # Document AI
#     document_ai_processor_id: str
#     document_ai_location: str = "us"
    
#     # Google Cloud Storage
#     gcs_bucket_name: str = "investment_memo_ai"
    
#     # SendGrid
#     sendgrid_api_key: Optional[str] = None
    
#     # Application
#     base_url: str = "https://studio--studio-6714467766-8a879.us-central1.hosted.app"
    
#     class Config:
#         env_file = ".env"
#         case_sensitive = False

# settings = Settings()
