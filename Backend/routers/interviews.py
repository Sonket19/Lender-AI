from fastapi import APIRouter, HTTPException
from models.schemas import InitiateInterviewRequest, ChatMessage, ChatResponse
from services.interview_service import create_interview, validate_interview_token, complete_interview
from services.interview_ai import chat_with_founder
from services.email_service import send_interview_email
from google.cloud import firestore
from config.settings import settings
from datetime import datetime

router = APIRouter(prefix="/api/interviews", tags=["interviews"])
db = firestore.Client(project=settings.GCP_PROJECT_ID)

@router.post("/initiate")
async def initiate_interview(request: InitiateInterviewRequest):
    """Create interview link and send email to founder"""
    try:
        # Create interview
        interview = create_interview(
            deal_id=request.deal_id,
            founder_email=request.founder_email,
            founder_name=request.founder_name
        )
        
        # Try to send email
        try:
            await send_interview_email(
                to_email=request.founder_email,
                founder_name=request.founder_name or "Founder",
                interview_link=interview['link'],
                deal_id=request.deal_id,
                missing_count=interview['total_questions']
            )
        except Exception as email_error:
            # Rollback: Delete interview if email fails
            db.collection('deals').document(request.deal_id).update({
                "interview": firestore.DELETE_FIELD
            })
            raise HTTPException(status_code=500, detail=str(email_error))
        
        return {
            "success": True,
            "message": "Interview invitation sent successfully",
            "deal_id": interview['deal_id'],
            "total_questions": interview['total_questions'],
            "critical_questions": interview['critical_questions'],
            "breakdown": interview['breakdown']
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/reset/{deal_id}")
async def reset_interview(deal_id: str):
    """Delete interview for a deal"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        if 'interview' not in deal_data:
            raise HTTPException(status_code=404, detail="No interview found for this deal")
        
        deal_ref.update({"interview": firestore.DELETE_FIELD})
        
        return {
            "success": True,
            "message": "Interview deleted successfully",
            "deal_id": deal_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/validate/{token}")
async def validate_interview(token: str):
    """Validate interview token and return interview details WITH initial AI greeting"""
    try:
        interview = validate_interview_token(token)
        
        # Check if chat already started
        chat_history = interview.get('chat_history', [])
        
        # If no chat history, create simple greeting (NO question yet)
        if len(chat_history) == 0:
            total_questions = len(interview.get('issues', []))
            
            # Simple warm greeting - NO question
            initial_message = f"Hello {interview['founder_name']}! 👋\n\nThanks for taking the time to chat with me about {interview['company_name']}. I have {total_questions} questions to help complete our investment analysis.\n\nThis should take about 5-10 minutes. Ready to get started?"
            
            # Save initial message to Firestore
            deal_ref = db.collection('deals').document(interview['deal_id'])
            initial_chat = [{
                "role": "assistant",
                "message": initial_message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }]
            
            deal_ref.update({
                'interview.chat_history': initial_chat
            })
            
            chat_history = initial_chat
        
        return {
            "valid": True,
            "deal_id": interview['deal_id'],
            "company_name": interview['company_name'],
            "sector": interview['sector'],
            "founder_name": interview['founder_name'],
            "status": interview['status'],
            "missing_fields_count": len(interview['missing_fields']),
            "chat_history": chat_history
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in validate_interview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/chat")
# async def chat(message: ChatMessage) -> ChatResponse:
#     """Handle chat message from founder"""
#     try:
#         interview = validate_interview_token(message.interview_token)
#         deal_id = interview['deal_id']
        
#         response = await chat_with_founder(
#             interview_data=interview,
#             user_message=message.message,
#             chat_history=interview.get('chat_history', [])
#         )
        
#         deal_ref = db.collection('deals').document(deal_id)
        
#         new_messages = [
#             {
#                 "role": "user",
#                 "message": message.message,
#                 "timestamp": datetime.utcnow().isoformat() + "Z"
#             },
#             {
#                 "role": "assistant",
#                 "message": response['message'],
#                 "timestamp": datetime.utcnow().isoformat() + "Z"
#             }
#         ]
        
#         deal_ref.update({
#             'interview.chat_history': firestore.ArrayUnion(new_messages),
#             'interview.gathered_info': response['gathered_info']
#         })
        
#         # If complete, finalize interview
#         if response['is_complete']:
#             complete_interview(deal_id, response['gathered_info'])
#             # ❌ REMOVED: await regenerate_memo_with_interview(deal_id)
#             # ✅ Now called inside complete_interview() only
        
#         gathered_fields = list(response.get('gathered_info', {}).keys())
#         still_missing = [f for f in interview['missing_fields'] if f not in gathered_fields]
        
#         return ChatResponse(
#             message=response['message'],
#             is_complete=response['is_complete'],
#             gathered_fields=gathered_fields,
#             missing_fields=still_missing
#         )
    
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         print(f"Error in chat: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/chat")
# async def chat(message: ChatMessage) -> ChatResponse:
#     """Handle chat message from founder"""
#     try:
#         interview = validate_interview_token(message.interview_token)
#         deal_id = interview['deal_id']
        
#         response = await chat_with_founder(
#             interview_data=interview,
#             user_message=message.message,
#             chat_history=interview.get('chat_history', [])
#         )
        
#         deal_ref = db.collection('deals').document(deal_id)
        
#         new_messages = [
#             {
#                 "role": "user",
#                 "message": message.message,
#                 "timestamp": datetime.utcnow().isoformat() + "Z"
#             },
#             {
#                 "role": "assistant",
#                 "message": response['message'],
#                 "timestamp": datetime.utcnow().isoformat() + "Z"
#             }
#         ]
        
#         # Get fields they can't answer
#         cannot_answer = response.get('cannot_answer_fields', [])
        
#         # Update interview
#         updates = {
#             'interview.chat_history': firestore.ArrayUnion(new_messages),
#             'interview.gathered_info': response['gathered_info']
#         }
        
#         # ✅ Add cannot_answer fields to track them
#         if cannot_answer:
#             # Add to list of fields they said they don't know
#             existing_cannot_answer = interview.get('cannot_answer_fields', [])
#             all_cannot_answer = list(set(existing_cannot_answer + cannot_answer))
#             print("existing_cannot_answer: ",existing_cannot_answer)
#             print("cannot_answer: ",cannot_answer)
#             print("all_cannot_answer: ", all_cannot_answer)
#             updates['interview.cannot_answer_fields'] = all_cannot_answer
            
#             # ✅ Remove from missing_fields
#             current_missing = interview.get('missing_fields', [])
#             new_missing = [f for f in current_missing if f not in all_cannot_answer]
#             updates['interview.missing_fields'] = new_missing
        
#         deal_ref.update(updates)
        
#         # If complete, finalize and regenerate memo
#         if response['is_complete']:
#             complete_interview(deal_id, response['gathered_info'])
            
#             from services.memo_regeneration import regenerate_memo_with_interview
#             await regenerate_memo_with_interview(deal_id)
        
#         # ✅ Return fields they can't answer too
#         gathered_fields = list(response.get('gathered_info', {}).keys())
#         still_missing = [f for f in interview['missing_fields'] if f not in gathered_fields]
        
#         return ChatResponse(
#             message=response['message'],
#             is_complete=response['is_complete'],
#             gathered_fields=gathered_fields,
#             missing_fields=still_missing
#         )
    
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         print(f"Error in chat: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat(message: ChatMessage) -> ChatResponse:
    """Handle chat message from founder"""
    try:
        # Validate token and get interview data
        interview = validate_interview_token(message.interview_token)
        deal_id = interview['deal_id']
        
        print(f"\n{'='*60}")
        print(f"💬 NEW CHAT MESSAGE")
        print(f"{'='*60}")
        print(f"Deal ID: {deal_id}")
        print(f"Company: {interview.get('company_name')}")
        print(f"Message: {message.message[:100]}...")
        
        # Get AI response with new reliable system
        response = await chat_with_founder(
            interview_data=interview,
            user_message=message.message,
            chat_history=interview.get('chat_history', [])
        )
        
        deal_ref = db.collection('deals').document(deal_id)
        
        # Create new messages
        new_messages = [
            {
                "role": "user",
                "message": message.message,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            {
                "role": "assistant",
                "message": response['message'],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ]
        
        # Get all tracking fields from response
        gathered_info = response.get('gathered_info', {})
        cannot_answer = response.get('cannot_answer_fields', [])
        asked_questions = response.get('asked_questions', [])
        ask_count = response.get('ask_count', {})
        progress = response.get('progress', {})
        is_complete = response.get('is_complete', False)
        
        # Build updates with dot notation for nested interview field
        updates = {
            'interview.chat_history': firestore.ArrayUnion(new_messages),
            'interview.gathered_info': gathered_info,
            'interview.asked_questions': asked_questions,
            'interview.ask_count': ask_count,
            'interview.progress': progress,
            'interview.is_complete': is_complete,
            'interview.updated_at': datetime.utcnow().isoformat() + "Z"
        }
        
        # Handle cannot_answer fields
        if cannot_answer:
            # Merge with existing cannot_answer
            existing_cannot_answer = interview.get('cannot_answer_fields', [])
            all_cannot_answer = list(set(existing_cannot_answer + cannot_answer))
            
            print(f"\n📊 Cannot answer tracking:")
            print(f"   - Existing: {existing_cannot_answer}")
            print(f"   - New from this turn: {cannot_answer}")
            print(f"   - Total: {all_cannot_answer}")
            
            updates['interview.cannot_answer_fields'] = all_cannot_answer
            
            # Update missing_fields: remove both answered AND cannot_answer
            current_missing = interview.get('missing_fields', [])
            gathered_fields = list(gathered_info.keys())
            
            new_missing = [
                f for f in current_missing 
                if f not in gathered_fields and f not in all_cannot_answer
            ]
            
            updates['interview.missing_fields'] = new_missing
            
            print(f"\n📋 Missing fields update:")
            print(f"   - Was: {len(current_missing)} fields")
            print(f"   - Now: {len(new_missing)} fields")
        
        # Apply updates to Firestore
        deal_ref.update(updates)
        
        print(f"\n✅ Firestore updated")
        print(f"   - Chat history: +2 messages")
        print(f"   - Gathered: {len(gathered_info)} fields")
        print(f"   - Cannot answer: {len(cannot_answer)} fields")
        print(f"   - Progress: {progress.get('attempted', 0)}/{progress.get('total', 0)}")
        print(f"   - Complete: {is_complete}")
        
        # If complete, finalize and regenerate memo
        if is_complete:
            print(f"\n🎉 Interview complete for deal {deal_id}!")
            print(f"🔄 Triggering memo regeneration...")
            
            complete_interview(deal_id, gathered_info)
        
        # Prepare response for frontend
        gathered_fields = list(gathered_info.keys())
        
        # Still missing = not gathered AND not cannot_answer
        all_fields = [issue['field'] for issue in interview.get('issues', [])]
        still_missing = [
            f for f in all_fields 
            if f not in gathered_fields and f not in cannot_answer
        ]
        
        print(f"\n📤 Sending response:")
        print(f"   - Message: {response['message'][:80]}...")
        print(f"   - Gathered: {len(gathered_fields)} fields")
        print(f"   - Still missing: {len(still_missing)} fields")
        print(f"   - Complete: {is_complete}")
        print(f"{'='*60}\n")
        
        return ChatResponse(
            message=response['message'],
            is_complete=is_complete,
            gathered_fields=gathered_fields,
            missing_fields=still_missing
        )
    
    except ValueError as e:
        print(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error in chat: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{deal_id}")
async def get_interview_status(deal_id: str):
    """Get interview status"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_data = deal_ref.get().to_dict()
        
        if not deal_data:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        if 'interview' not in deal_data:
            return {"has_interview": False, "status": None}
        
        interview = deal_data['interview']
        
        return {
            "has_interview": True,
            "status": interview['status'],
            "missing_fields": interview.get('missing_fields', []),
            "gathered_fields": list(interview.get('gathered_info', {}).keys()),
            "message_count": len(interview.get('chat_history', [])),
            "created_at": interview.get('created_at'),
            "completed_at": interview.get('completed_at'),
            "founder_email": interview.get('founder_email')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
