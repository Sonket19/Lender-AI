from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form, Request
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
import io
import asyncio
import threading
from google.cloud import firestore, storage
from config.settings import settings
from config.auth import get_current_user
from models.schemas import FactCheckResponse
from services import (
    extract_text_from_pdf,
    analyze_with_gemini,
    upload_to_gcs,
    generate_deal_id,
    create_word_document,
    extract_cma_data
)
from services.excel_extraction import extract_text_from_excel

router = APIRouter(prefix="/api", tags=["deals"])

# Initialize clients
db = firestore.Client(project=settings.GCP_PROJECT_ID)
storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)

# def generate_investment_decision_in_background(deal_id: str, memo: dict, extracted_text: str, user_id: str):
#     """Thread-based background task to generate investment decision"""
#     print(f"[{deal_id}] 🚀 Starting background investment decision generation...")
#     
#     async def _generate():
#         try:
#             from services import generate_investment_decision
#             decision = await generate_investment_decision(
#                 deal_id=deal_id,
#                 memo=memo,
#                 extracted_text=extracted_text,
#                 user_id=user_id
#             )
#             
#             # Convert Pydantic model to dict for Firestore
#             decision_dict = decision.dict() if hasattr(decision, 'dict') else decision
#             
#             db.collection('deals').document(deal_id).update({
#                 "investment_decision": decision_dict,
#                 "metadata.investment_decision_generated_at": datetime.utcnow().isoformat() + "Z"
#             })
#             print(f"[{deal_id}] ✅ Background investment decision generated successfully!")
#         except Exception as e:
#             print(f"[{deal_id}] ⚠️ Failed to generate background investment decision: {str(e)}")
#             import traceback
#             traceback.print_exc()
#     
#     # Run the async function in a new event loop (required for threading)
#     asyncio.run(_generate())

@router.post("/upload")
async def upload_file(
    file: Optional[UploadFile] = File(None),
    cma_report: Optional[UploadFile] = File(None),
    processing_mode: str = "research", # Default to research
    request: Request = None,
    current_user: str = Depends(get_current_user)
):
    """
    Upload Pitch Deck (PDF) and CMA Report (PDF/Excel)
    Forces 'research' processing mode.
    """
    try:
        print(f"Received upload request. Processing mode: {processing_mode}")
        
        # Fallback: Try to retrieve file from form if dependency injection failed
        if not file and request:
            try:
                form = await request.form()
                print(f"Raw Form Keys: {form.keys()}")
                if 'file' in form:
                    file_obj = form['file']
                    # Check if it's an UploadFile (Starlette/FastAPI)
                    if hasattr(file_obj, 'filename'):
                        file = file_obj
                        print(f"✅ Recovered file from form: {file.filename}")
            except Exception as e:
                print(f"Error reading form: {e}")

        print(f"File received: {file}, Filename: {file.filename if file else 'None'}")

        # Validate processing mode - overwritten to Force Research
        processing_mode = "research"
        
        # Validate input: both files function be provided
        if not file or not cma_report:
            raise HTTPException(status_code=400, detail="Both Pitch Deck (PDF) and CMA Report (PDF/Excel) are required.")
            
        deal_id = generate_deal_id()
        
        # Determine input type and process accordingly
        pitch_deck_url = ""
        mime_type = "text/plain"
        
        if file:
            file_content = await file.read()
            mime_type = file.content_type
            
            # Force PDF for pitch deck
            if mime_type == "application/octet-stream" and file.filename.endswith(".pdf"):
                mime_type = "application/pdf"
            
            if mime_type != "application/pdf":
                 raise HTTPException(status_code=400, detail="Pitch Deck must be a PDF file.")

            # Define GCS path based on type
            gcs_path = f"deals/{deal_id}/pitch_deck.pdf"
            pitch_deck_url = upload_to_gcs(file_content, gcs_path)
        
        deal_ref = db.collection('deals').document(deal_id)
        
        initial_data = {
            "raw_files": {"pitch_deck_url": pitch_deck_url, "mime_type": mime_type},
            "metadata": {
                "processing_mode": processing_mode,
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
                "user_id": current_user,
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
            print(f"\n{'='*60}")
            print(f"[{deal_id}] 📊 PROCESSING STARTED ({mime_type})")
            print(f"{'='*60}\n")
            
            import time
            start_time = time.time()
            step_start = time.time()
            
            # Validate pitch deck is PDF
            if mime_type != "application/pdf":
                raise HTTPException(status_code=400, detail=f"Unsupported Pitch Deck file type: {mime_type}. Only PDF is supported.")
            
            print(f"[{deal_id}] ✅ Pitch Deck PDF received ({len(file_content)} bytes) - will send directly to Gemini")
            extraction_time = time.time() - step_start
            
            # --- CMA REPORT EXTRACTION ---
            step_start = time.time()
            cma_text = ""
            cma_pages = 0
            cma_url = ""
            
            if cma_report:
                print(f"[{deal_id}] Processing CMA Report...")
                cma_content = await cma_report.read()
                cma_mime = cma_report.content_type
                
                # Upload CMA to GCS
                cma_ext = "xlsx" if "spreadsheet" in cma_mime or "excel" in cma_mime else "pdf"
                if cma_report.filename.endswith(".xlsx"): cma_ext = "xlsx"
                elif cma_report.filename.endswith(".pdf"): cma_ext = "pdf"
                
                cma_path = f"deals/{deal_id}/cma_report.{cma_ext}"
                cma_url = upload_to_gcs(cma_content, cma_path)
                
                # Extract text from CMA
                if cma_ext == "xlsx":
                    print(f"[{deal_id}] Extracting text from CMA Excel...")
                    cma_data = extract_text_from_excel(cma_content)
                    cma_text = cma_data.get('text', '')
                    cma_pages = cma_data.get('pages', 0)
                    
                    # Update Firestore with CMA text
                    deal_ref.update({
                        "extracted_text.cma_report": {
                            "text": cma_text, 
                            "pages": cma_pages,
                            "url": cma_url
                        },
                        "raw_files.cma_report_url": cma_url
                    })
                    print(f"[{deal_id}] ✅ CMA Excel extraction complete - {cma_pages} sheets")
                    
                    # Extract structured CMA data from text
                    if cma_text:
                        step_start = time.time()
                        print(f"[{deal_id}] Extracting structured CMA data from Excel...")
                        cma_structured_data = await extract_cma_data(raw_text=cma_text)
                        cma_extraction_time = time.time() - step_start
                        
                        deal_ref.update({
                            "cma_data": cma_structured_data
                        })
                        print(f"[{deal_id}] ✅ CMA structured data extracted")
                        print(f"[{deal_id}] ⏱️  CMA Parsing Time: {cma_extraction_time:.2f}s\n")
                        
                elif cma_ext == "pdf":
                    # Send CMA PDF directly to Gemini (bypasses Document AI 30-page limit)
                    print(f"[{deal_id}] 📄 Sending CMA PDF directly to Gemini...")
                    
                    # Update Firestore with CMA URL (text will be empty since we're using direct PDF)
                    deal_ref.update({
                        "extracted_text.cma_report": {
                            "text": "", 
                            "pages": 0,
                            "url": cma_url,
                            "processing_method": "direct_pdf"
                        },
                        "raw_files.cma_report_url": cma_url
                    })
                    
                    # Extract structured CMA data directly from PDF bytes
                    step_start = time.time()
                    cma_structured_data = await extract_cma_data(pdf_bytes=cma_content)
                    cma_extraction_time = time.time() - step_start
                    
                    deal_ref.update({
                        "cma_data": cma_structured_data
                    })
                    print(f"[{deal_id}] ✅ CMA structured data extracted directly from PDF")
                    print(f"[{deal_id}] ⏱️  CMA Parsing Time: {cma_extraction_time:.2f}s\n")
                
                print(f"[{deal_id}] ⏱️  Extraction Time: {extraction_time:.2f}s\n")
            
            # Get current weightage
            deal_data = deal_ref.get().to_dict()
            weightage = deal_data['metadata']['weightage']
            
            # Analyze with Gemini - send PDF directly (multimodal)
            step_start = time.time()
            print(f"[{deal_id}] Starting Gemini analysis (Research Mode) - sending PDF directly...")
            analysis = await analyze_with_gemini(
                pdf_bytes=file_content,  # Send PDF bytes directly
                cma_text=cma_text,  # Include CMA text for financial context
                weightage=weightage,
                processing_mode="research"  # Force research mode
            )
            analysis_time = time.time() - step_start
            
            # Extract metadata from analysis result (instead of separate extraction)
            company_name = analysis.get('company_overview', {}).get('name', 'Unknown')
            sector = analysis.get('company_overview', {}).get('sector', 'Unknown')
            founders = analysis.get('company_overview', {}).get('founders', [])
            founder_names = [f.get('name', '') for f in founders if f.get('name')]
            
            deal_ref.update({
                "metadata.company_name": company_name,
                "metadata.founder_names": founder_names,
                "metadata.sector": sector
            })
            
            print(f"[{deal_id}] ✅ Gemini analysis complete - {company_name}")
            print(f"[{deal_id}] ⏱️  Analysis Time: {analysis_time:.2f}s\n")
            
            # Create Word document (5-10 seconds)
            step_start = time.time()
            print(f"[{deal_id}] Creating Word document...")
            docx_url = create_word_document(analysis, deal_id)
            docx_time = time.time() - step_start
            print(f"[{deal_id}] ✅ Word document created")
            print(f"[{deal_id}] ⏱️  Document Time: {docx_time:.2f}s\n")
            
            # Final update
            deal_ref.update({
                "memo.draft_v1": analysis,
                "memo.generated_at": datetime.utcnow().isoformat() + "Z",
                "memo.docx_url": docx_url,
                "metadata.status": "processed",
                "metadata.processed_at": datetime.utcnow().isoformat() + "Z"
            })
            
            print(f"[{deal_id}] ✅ Core processing completed successfully!")
            
            
            # Generate draft interview questions immediately
            print(f"[{deal_id}] Generating draft interview questions...")
            from services.interview_service import generate_draft_interview
            generate_draft_interview(deal_id)
            
            # Only generate investment decision for research mode - DISABLED
            # if processing_mode == "research":
            #     # Start investment decision generation in a separate thread (non-blocking)
            #     print(f"[{deal_id}] 🚀 Starting investment decision in background thread...")
            #     thread = threading.Thread(
            #         target=generate_investment_decision_in_background,
            #         args=(deal_id, analysis, extracted_data.get('text', ''), current_user),
            #         daemon=True  # Daemon thread will not block server shutdown
            #     )
            #     thread.start()
            # else:
            #     print(f"[{deal_id}] ⚡ Fast mode - skipping investment decision generation")
            
            # Get final deal data to return
            total_time = time.time() - start_time
            print(f"\n{'='*60}")
            print(f"[{deal_id}] 🎉 UPLOAD PROCESSING COMPLETE (Investment Decision running in background)")
            print(f"[{deal_id}] ⏱️  TOTAL TIME: {total_time:.2f}s ({total_time/60:.2f} minutes)")
            print(f"{'='*60}\n")

            
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
    except Exception as e:
        print(f"Error in upload_file: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/deals/{deal_id}")
async def get_deal(
    deal_id: str,
    include_extracted_text: bool = False,
    current_user: str = Depends(get_current_user)
):
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
        
        # Verify ownership
        if deal_data.get('metadata', {}).get('user_id') != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
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
    include_extracted_text: bool = False,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch all deals with optional filtering
    By default, excludes extracted_text for performance
    """
    try:
        print(f"Fetching deals for user: {current_user}")
        
        # Simplified query: just filter by user_id (no composite index needed)
        query = db.collection('deals').where(
            filter=firestore.FieldFilter('metadata.user_id', '==', current_user)
        )
        
        if status:
            query = query.where(filter=firestore.FieldFilter('metadata.status', '==', status))
        
        # Fetch all results and sort in Python to avoid composite index
        deals = []
        stream = query.stream()
        
        for doc in stream:
            deal_data = doc.to_dict()
            deal_data['id'] = doc.id
            
            # Remove extracted_text unless explicitly requested
            if not include_extracted_text and 'extracted_text' in deal_data:
                del deal_data['extracted_text']
            
            deals.append(deal_data)
        
        # Sort by created_at in Python (descending - newest first)
        deals.sort(
            key=lambda x: x.get('metadata', {}).get('created_at', ''),
            reverse=True
        )
        
        # Apply pagination after sorting
        paginated_deals = deals[offset:offset + limit]
        
        print(f"Found {len(deals)} total deals for user {current_user}, returning {len(paginated_deals)} after pagination")
        
        return {
            "deals": paginated_deals,
            "count": len(paginated_deals),
            "total": len(deals),
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        print(f"Error fetching deals: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/deals/{deal_id}")
async def delete_deal(
    deal_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete a specific deal"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        # Verify ownership
        if deal_data.get('metadata', {}).get('user_id') != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
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
async def download_memo(
    deal_id: str,
    current_user: str = Depends(get_current_user)
):
    """Download Word document for a specific deal"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        # Verify ownership
        if deal_data.get('metadata', {}).get('user_id') != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
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

# @router.post("/deals/{deal_id}/investment-decision")
# async def create_investment_decision(
#     deal_id: str,
#     current_user: str = Depends(get_current_user)
# ):
#     """
#     Generate comprehensive investment decision and funding plan for a deal.
#     Uses existing memo and pitch deck analysis to create:
#     - Funding recommendation (PROCEED/PASS/CONDITIONAL)
#     - Disbursement schedule with tranches
#     - Milestone-based roadmap
#     - Next round criteria
#     - Red flags and success metrics
#     
#     Response time: 15-30 seconds
#     """
#     try:
#         deal_ref = db.collection('deals').document(deal_id)
#         deal_doc = deal_ref.get()
#         
#         if not deal_doc.exists:
#             raise HTTPException(status_code=404, detail="Deal not found")
#         
#         deal_data = deal_doc.to_dict()
#         
#         # Verify ownership
#         if deal_data.get('metadata', {}).get('user_id') != current_user:
#             raise HTTPException(status_code=403, detail="Access denied")
#         
#         # Check if memo exists
#         if 'memo' not in deal_data or 'draft_v1' not in deal_data['memo']:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Investment memo not yet generated. Please wait for pitch deck analysis to complete."
#             )
#         
#         # Check if extracted text exists
#         if 'extracted_text' not in deal_data or 'pitch_deck' not in deal_data['extracted_text']:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Pitch deck text not available. Please reprocess the document."
#             )
#         
#         print(f"[{deal_id}] Generating investment decision...")
#         
#         # Import the service
#         from services import generate_investment_decision
#         
#         # Generate investment decision
#         memo = deal_data['memo']['draft_v1']
#         extracted_text = deal_data['extracted_text']['pitch_deck'].get('text', '')
#         
#         decision = await generate_investment_decision(
#             deal_id=deal_id,
#             memo=memo,
#             extracted_text=extracted_text,
#             user_id=current_user
#         )
#         
#         # Store in Firestore
#         deal_ref.update({
#             "investment_decision": decision,
#             "metadata.investment_decision_generated_at": datetime.utcnow().isoformat() + "Z"
#         })
#         
#         print(f"[{deal_id}] ✅ Investment decision generated successfully!")
#         
#         return decision
#     
#     except HTTPException:
#         raise
#     except Exception as e:
#         error_msg = str(e)
#         print(f"[{deal_id}] ❌ Error generating investment decision: {error_msg}")
#         raise HTTPException(status_code=500, detail=f"Failed to generate investment decision: {error_msg}")
# 
# @router.get("/deals/{deal_id}/investment-decision")
# async def get_investment_decision(
#     deal_id: str,
#     current_user: str = Depends(get_current_user)
# ):
#     """
#     Retrieve existing investment decision for a deal
#     """
#     try:
#         deal_ref = db.collection('deals').document(deal_id)
#         deal_doc = deal_ref.get()
#         
#         if not deal_doc.exists:
#             raise HTTPException(status_code=404, detail="Deal not found")
#         
#         deal_data = deal_doc.to_dict()
#         
#         # Verify ownership
#         if deal_data.get('metadata', {}).get('user_id') != current_user:
#             raise HTTPException(status_code=403, detail="Access denied")
#         
#         if 'investment_decision' not in deal_data:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Investment decision not yet generated. Use POST to create one."
#             )
#         
#         return deal_data['investment_decision']
#     
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@router.post("/deals/{deal_id}/fact-check", response_model=FactCheckResponse)
async def run_fact_check(
    deal_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Run an automated fact check on the deal's pitch deck using Google Search.
    """
    try:
        # Fetch deal data
        doc_ref = db.collection('deals').document(deal_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
            
        deal_data = doc.to_dict()
        
        # Verify ownership
        if deal_data.get('metadata', {}).get('user_id') != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Extract text
        extracted_text_data = deal_data.get('extracted_text', {})
        if isinstance(extracted_text_data, dict) and 'pitch_deck' in extracted_text_data:
            extracted_text = extracted_text_data['pitch_deck'].get('text', '')
        elif isinstance(extracted_text_data, str):
            extracted_text = extracted_text_data
        else:
            extracted_text = ''
            
        if not extracted_text:
            raise HTTPException(status_code=400, detail="No pitch deck text available for fact checking")
            
        # Run verification
        from services.gemini_service import verify_claims_with_google
        result = await verify_claims_with_google(extracted_text)
        
        # Save result to Firestore
        fact_check_data = {
            "claims": result.get('claims', []),
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }
        
        doc_ref.update({
            "fact_check": fact_check_data
        })
        
        return {
            "deal_id": deal_id,
            "claims": result.get('claims', []),
            "checked_at": fact_check_data["checked_at"]
        }
        
    except Exception as e:
        print(f"Error in fact check endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
