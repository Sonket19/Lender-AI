from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import deals, interviews, investor_chat, auth
import firebase_admin
from firebase_admin import credentials

# Initialize Firebase Admin
import os
from config.settings import settings

# Enforce the use of the configured service account file
if settings.FIREBASE_SERVICE_ACCOUNT_PATH:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.FIREBASE_SERVICE_ACCOUNT_PATH

if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

app = FastAPI(title="AI Startup Analyst API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(deals.router)
app.include_router(interviews.router)
app.include_router(investor_chat.router)
app.include_router(auth.router)

@app.get("/health")
async def health_check():
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
