from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Optional
import secrets
from google.cloud import firestore
from config.settings import settings
from models.schemas import InterviewRequest, ChatMessage
from services import send_interview_email, chat_with_ai

router = APIRouter(prefix="/api", tags=["interview"])

db = firestore.Client(project=settings.GCP_PROJECT_ID)

@router.post("/send_interview_link/{deal_id}")
async def send_interview_link(
    deal_id: str,
    request: InterviewRequest
):
    """Send email to founder with one-time interview link"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        company_name = deal_data['metadata'].get('company_name', 'Your Company')
        
        interview_token = secrets.token_urlsafe(32)
        
        interview_ref = db.collection('interviews').document(interview_token)
        interview_ref.set({
            "deal_id": deal_id,
            "founder_email": request.founder_email,
            "founder_name": request.founder_name or "Founder",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "used": False,
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z",
            "chat_history": []
        })
        
        interview_link = f"{settings.BASE_URL}/interview/{interview_token}"
        
        await send_interview_email(
            request.founder_email,
            request.founder_name or "Founder",
            company_name,
            interview_link
        )
        
        return {
            "message": "Interview link sent successfully",
            "interview_token": interview_token,
            "interview_link": interview_link,
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/interview/{token}")
async def get_interview_session(token: str):
    """Validate interview token and get session details"""
    try:
        interview_ref = db.collection('interviews').document(token)
        interview_doc = interview_ref.get()
        
        if not interview_doc.exists:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        interview_data = interview_doc.to_dict()
        
        if interview_data.get('used', False):
            raise HTTPException(status_code=403, detail="This interview link has already been used")
        
        expires_at = datetime.fromisoformat(interview_data['expires_at'].replace('Z', '+00:00'))
        if datetime.utcnow() > expires_at.replace(tzinfo=None):
            raise HTTPException(status_code=403, detail="This interview link has expired")
        
        deal_ref = db.collection('deals').document(interview_data['deal_id'])
        deal_doc = deal_ref.get()
        deal_data = deal_doc.to_dict()
        
        interview_ref.update({"used": True})
        
        return {
            "founder_name": interview_data.get('founder_name'),
            "company_name": deal_data['metadata'].get('company_name'),
            "deal_id": interview_data['deal_id'],
            "chat_history": interview_data.get('chat_history', [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interview/{token}/chat")
async def chat_with_founder(
    token: str,
    message: ChatMessage
):
    """Handle chat messages in founder interview"""
    try:
        interview_ref = db.collection('interviews').document(token)
        interview_doc = interview_ref.get()
        
        if not interview_doc.exists:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        interview_data = interview_doc.to_dict()
        
        deal_ref = db.collection('deals').document(interview_data['deal_id'])
        deal_doc = deal_ref.get()
        deal_data = deal_doc.to_dict()
        
        memo = deal_data.get('memo', {}).get('draft_v1', {})
        chat_history = interview_data.get('chat_history', [])
        
        ai_response = await chat_with_ai(
            memo,
            deal_data['metadata'].get('company_name'),
            deal_data['metadata'].get('sector'),
            chat_history,
            message.text
        )
        
        chat_history.append({
            "role": "founder",
            "message": message.text,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        chat_history.append({
            "role": "ai",
            "message": ai_response,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        interview_ref.update({"chat_history": chat_history})
        
        return {
            "response": ai_response,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interview/{token}/complete")
async def complete_interview(token: str):
    """Mark interview as complete"""
    try:
        interview_ref = db.collection('interviews').document(token)
        interview_doc = interview_ref.get()
        
        if not interview_doc.exists:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        interview_data = interview_doc.to_dict()
        
        interview_ref.update({
            "completed_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed"
        })
        
        return {
            "message": "Interview completed successfully",
            "deal_id": interview_data['deal_id']
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
