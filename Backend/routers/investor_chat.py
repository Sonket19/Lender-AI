from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from google.cloud import firestore
from config.settings import settings
from services.gemini_service import generate_investor_chat_response

router = APIRouter(
    prefix="/api/investor_chat",
    tags=["investor_chat"]
)

# Initialize Firestore client
db = firestore.Client(project=settings.GCP_PROJECT_ID)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    deal_id: str
    message: str
    history: List[ChatMessage]

@router.post("")
async def chat_with_investor_bot(request: ChatRequest):
    """
    Chat with the AI Investor Analyst about a specific deal.
    """
    try:
        # Fetch deal data from Firestore
        doc_ref = db.collection('deals').document(request.deal_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
            
        deal_data = doc.to_dict()
        
        # Extract context
        extracted_text_data = deal_data.get('extracted_text', {})
        memo = deal_data.get('memo', {}).get('draft_v1', {})
        
        # Extract the actual text string from the nested structure
        if isinstance(extracted_text_data, dict) and 'pitch_deck' in extracted_text_data:
            extracted_text = extracted_text_data['pitch_deck'].get('text', '')
        elif isinstance(extracted_text_data, str):
            extracted_text = extracted_text_data
        else:
            extracted_text = ''
        
        if not extracted_text:
            extracted_text = "Pitch deck text not available."
            
        # Generate response
        response_text = await generate_investor_chat_response(
            extracted_text=extracted_text,
            memo_context=memo,
            chat_history=[msg.dict() for msg in request.history],
            user_message=request.message
        )
        
        return {"message": response_text}
        
    except Exception as e:
        print(f"Error in investor chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
