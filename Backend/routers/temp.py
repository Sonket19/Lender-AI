from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
import io
from google.cloud import firestore, storage
from config.settings import settings
from models.schemas import WeightageUpdate
from services import (
    extract_text_from_pdf,
    extract_metadata_from_text,
    analyze_with_gemini,
    upload_to_gcs,
    generate_deal_id,
    create_word_document
)

router = APIRouter(prefix="/api", tags=["deals"])

# Initialize clients
db = firestore.Client(project=settings.GCP_PROJECT_ID)
storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload pitch deck file and generate complete analysis
    Returns complete data after processing (1-2 minutes)
    """
    try:
        if file.content_type not in ["application/pdf"]:
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        deal_id = generate_deal_id()
        file_content = await file.read()
        
        gcs_path = f"deals/{deal_id}/pitch_deck.pdf"
        pitch_deck_url = upload_to_gcs(file_content, gcs_path)
        
        deal_ref = db.collection('deals').document(deal_id)
        
        initial_data = {
            "raw_files": {"pitch_deck_url": pitch_deck_url},
            "metadata": {
                "weightage": {
                    "traction": 20,
                    "team_strength": 20,
                    "claim_credibility": 20,
                    "financial_health": 20,
                    "market_opportunity": 20
                },
                "created_at": datetime.utcnow().isoformat() + "Z",
                "status": "processing",
                "deal_id": deal_id,
                "company_name": "",
                "processed_at": None,
                "error": None,
                "sector": "",
                "founder_names": []
            },
            "public_data": {
                "competitors": [],
                "news": [],
                "market_stats": {},
                "founder_profile": []
            },
            "extracted_text": {},
            "memo": {}
        }
        
        deal_ref.set(initial_data)
        
        # ===== SYNCHRONOUS PROCESSING - WAITS FOR COMPLETION =====
        try:
            # Extract text using Document AI (10-30 seconds)
            print(f"[{deal_id}] Starting text extraction...")
            extracted_data = await extract_text_from_pdf(file_content, deal_id)
            
            # Update Firestore with extracted text
            deal_ref.update({
                "extracted_text.pitch_deck": extracted_data
            })
            print(f"[{deal_id}] Text extraction complete - {extracted_data['pages']} pages")
            
            # Extract metadata (5-10 seconds)
            print(f"[{deal_id}] Extracting metadata...")
            metadata = await extract_metadata_from_text(extracted_data.get('text', ''))
            
            # Update metadata
            deal_ref.update({
                "metadata.company_name": metadata.get('company_name', 'Unknown'),
                "metadata.founder_names": metadata.get('founder_names', []),
                "metadata.sector": metadata.get('sector', 'Unknown')
            })
            print(f"[{deal_id}] Metadata extracted: {metadata.get('company_name')}")
            
            # Get current weightage
            deal_data = deal_ref.get().to_dict()
            weightage = deal_data['metadata']['weightage']
            
            # Analyze with Gemini (30-60 seconds)
            print(f"[{deal_id}] Starting Gemini analysis...")
            analysis = await analyze_with_gemini(extracted_data.get('text', ''), weightage)
            
            # Create Word document (5-10 seconds)
            print(f"[{deal_id}] Creating Word document...")
            docx_url = create_word_document(analysis, deal_id)
            
            # Final update
            deal_ref.update({
                "memo.draft_v1": analysis,
                "memo.generated_at": datetime.utcnow().isoformat() + "Z",
                "memo.docx_url": docx_url,
                "metadata.status": "processed",
                "metadata.processed_at": datetime.utcnow().isoformat() + "Z"
            })
            
            print(f"[{deal_id}] ✅ Processing completed successfully!")
            
            # Get final deal data to return
            final_deal_data = deal_ref.get().to_dict()
            
            # Remove extracted_text from response (too large)
            if 'extracted_text' in final_deal_data:
                del final_deal_data['extracted_text']
            
            # Return complete response with all data EXCEPT extracted_text
            return final_deal_data
            
        except Exception as e:
            # Update error status
            error_msg = str(e)
            print(f"[{deal_id}] ❌ Error processing pitch deck: {error_msg}")
            deal_ref.update({
                "metadata.status": "error",
                "metadata.error": error_msg,
                "metadata.processed_at": datetime.utcnow().isoformat() + "Z"
            })
            
            raise HTTPException(status_code=500, detail=f"Processing failed: {error_msg}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate_memo/{deal_id}")
async def regenerate_memo(
    deal_id: str,
    weightage: WeightageUpdate
):
    """
    Regenerate memo with updated weightage (synchronous)
    Returns complete deal object after re-evaluation of risk_metrics and conclusion
    Response time: 40-70 seconds
    """
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        if 'extracted_text' not in deal_data or 'pitch_deck' not in deal_data['extracted_text']:
            raise HTTPException(
                status_code=400,
                detail="Pitch deck not yet processed. Please wait for initial processing."
            )
        
        # Update weightage and status
        deal_ref.update({
            "metadata.weightage": weightage.dict(),
            "metadata.status": "reprocessing",
            "metadata.reprocessing_started_at": datetime.utcnow().isoformat() + "Z"
        })
        
        print(f"[{deal_id}] Regenerating analysis with weightage: {weightage.dict()}")
        
        # Get extracted text from original processing
        extracted_text = deal_data['extracted_text']['pitch_deck'].get('text', '')
        
        # Analyze with Gemini using NEW weightage (30-60 seconds)
        # This recalculates risk_metrics and conclusion based on updated weightage
        print(f"[{deal_id}] Calling Gemini with updated weightage...")
        analysis = await analyze_with_gemini(extracted_text, weightage.dict())
        
        # Create updated Word document (5-10 seconds)
        print(f"[{deal_id}] Creating updated Word document...")
        docx_url = create_word_document(analysis, deal_id)
        
        # Update Firestore with new analysis
        deal_ref.update({
            "memo.draft_v1": analysis,
            "memo.generated_at": datetime.utcnow().isoformat() + "Z",
            "memo.docx_url": docx_url,
            "metadata.status": "processed",
            "metadata.processed_at": datetime.utcnow().isoformat() + "Z",
            "metadata.last_weightage_update": datetime.utcnow().isoformat() + "Z"
        })
        
        print(f"[{deal_id}] ✅ Regeneration completed with updated risk metrics and conclusion")
        
        # Get final deal data from Firestore
        final_deal_data = deal_ref.get().to_dict()
        
        # Remove extracted_text from response (too large)
        if 'extracted_text' in final_deal_data:
            del final_deal_data['extracted_text']
        
        # Return complete response with all data EXCEPT extracted_text
        return final_deal_data
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[{deal_id}] ❌ Error regenerating analysis: {error_msg}")
        deal_ref.update({
            "metadata.status": "error",
            "metadata.error": error_msg,
            "metadata.processed_at": datetime.utcnow().isoformat() + "Z"
        })
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/deals/{deal_id}")
async def get_deal(deal_id: str, include_extracted_text: bool = False):
    """
    Fetch specific deal data
    By default, excludes extracted_text (set include_extracted_text=true to include it)
    """
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        # Remove extracted_text unless explicitly requested
        if not include_extracted_text and 'extracted_text' in deal_data:
            del deal_data['extracted_text']
        
        return deal_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/deals")
async def get_all_deals(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    include_extracted_text: bool = False
):
    """
    Fetch all deals with optional filtering
    By default, excludes extracted_text for performance
    """
    try:
        query = db.collection('deals').order_by(
            'metadata.created_at',
            direction=firestore.Query.DESCENDING
        )
        
        if status:
            query = query.where('metadata.status', '==', status)
        
        query = query.limit(limit).offset(offset)
        
        deals = []
        for doc in query.stream():
            deal_data = doc.to_dict()
            deal_data['id'] = doc.id
            
            # Remove extracted_text unless explicitly requested
            if not include_extracted_text and 'extracted_text' in deal_data:
                del deal_data['extracted_text']
            
            deals.append(deal_data)
        
        return {
            "deals": deals,
            "count": len(deals),
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/deals/{deal_id}")
async def delete_deal(deal_id: str):
    """Delete a specific deal"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        try:
            if 'raw_files' in deal_data and 'pitch_deck_url' in deal_data['raw_files']:
                gcs_path = deal_data['raw_files']['pitch_deck_url'].replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                blob = bucket.blob(gcs_path)
                blob.delete()
            
            if 'memo' in deal_data and 'docx_url' in deal_data['memo']:
                gcs_path = deal_data['memo']['docx_url'].replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                blob = bucket.blob(gcs_path)
                blob.delete()
        except Exception as e:
            print(f"Error deleting GCS files: {str(e)}")
        
        deal_ref.delete()
        
        return {
            "message": "Deal deleted successfully",
            "deal_id": deal_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download_memo/{deal_id}")
async def download_memo(deal_id: str):
    """Download Word document for a specific deal"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        if 'memo' not in deal_data or 'docx_url' not in deal_data['memo']:
            raise HTTPException(status_code=404, detail="Memo not yet generated")
        
        gcs_path = deal_data['memo']['docx_url'].replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
        blob = bucket.blob(gcs_path)
        file_content = blob.download_as_bytes()
        
        company_name = deal_data['metadata'].get('company_name', 'Unknown')
        filename = f"{company_name}_Investment_Memo_{deal_id}.docx"
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download_pitch_deck/{deal_id}")
async def download_pitch_deck(deal_id: str):
    """Download original pitch deck file"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        if 'raw_files' not in deal_data or 'pitch_deck_url' not in deal_data['raw_files']:
            raise HTTPException(status_code=404, detail="Pitch deck not found")
        
        gcs_path = deal_data['raw_files']['pitch_deck_url'].replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
        blob = bucket.blob(gcs_path)
        file_content = blob.download_as_bytes()
        
        company_name = deal_data['metadata'].get('company_name', 'Unknown')
        filename = f"{company_name}_Pitch_Deck_{deal_id}.pdf"
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
