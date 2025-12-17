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
    extract_cma_data,
    verify_claims_with_google,
    augment_cma_with_web_search
)
from services.credit_service import CreditService, parse_cma_to_model
from models.credit_schemas import UserProfile, TrustTier
from services.excel_extraction import extract_text_from_excel, extract_sheets_from_excel

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
    loan_amount_requested: Optional[str] = Form(None),
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
        
        # Validate input: CMA is required, Pitch Deck is optional
        if not cma_report:
            raise HTTPException(status_code=400, detail="CMA Report (PDF/Excel) is required.")
            
        deal_id = generate_deal_id()
        
        # Handle optional pitch deck
        pitch_deck_url = ""
        mime_type = "text/plain"
        file_content = None
        
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
                "founder_names": [],
                "loan_amount_requested": loan_amount_requested or ""
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
            
            # Validate pitch deck is PDF (only if provided)
            if file_content:
                if mime_type != "application/pdf":
                    raise HTTPException(status_code=400, detail=f"Unsupported Pitch Deck file type: {mime_type}. Only PDF is supported.")
                print(f"[{deal_id}] ✅ Pitch Deck PDF received ({len(file_content)} bytes) - will send directly to Gemini")
            else:
                print(f"[{deal_id}] ℹ️ No Pitch Deck provided - processing CMA only")
            extraction_time = time.time() - step_start
            
            # --- CMA REPORT EXTRACTION ---
            step_start = time.time()
            cma_text = ""
            cma_pages = 0
            cma_url = ""
            cma_structured_data = {}  # Will be populated during CMA extraction
            
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
                    
                    # Also extract structured sheet data for dynamic tab rendering
                    print(f"[{deal_id}] Extracting structured sheet data...")
                    sheets_data = extract_sheets_from_excel(cma_content)
                    
                    print(f"[{deal_id}] CMA Excel raw extraction: {cma_pages} sheets, {len(cma_text)} chars of text")
                    print(f"[{deal_id}] Structured sheets: {sheets_data.get('sheet_count', 0)} sheets")
                    
                    # Update Firestore with CMA text AND dynamic sheets
                    deal_ref.update({
                        "extracted_text.cma_report": {
                            "text": cma_text, 
                            "pages": cma_pages,
                            "url": cma_url
                        },
                        "raw_files.cma_report_url": cma_url,
                        "cma_data": sheets_data  # Store sheet-based structure for dynamic tabs
                    })
                    print(f"[{deal_id}] ✅ CMA Excel extraction complete - {cma_pages} sheets")
                    
                    # For Excel: Use AI-powered extraction with Gemini
                    # This handles varying layouts by using semantic understanding
                    step_start = time.time()
                    print(f"[{deal_id}] 🤖 Using AI-powered CMA extraction with Gemini...")
                    from services.document_ai import extract_cma_with_gemini
                    
                    cma_structured_data = await extract_cma_with_gemini(cma_text)
                    cma_extraction_time = time.time() - step_start
                    
                    # Save to cma_structured (NOT cma_data, which has sheet-based data for UI)
                    deal_ref.update({
                        "cma_structured": cma_structured_data
                    })
                    print(f"[{deal_id}] ✅ CMA structured data extracted via AI")
                    print(f"[{deal_id}] ⏱️  CMA AI Extraction Time: {cma_extraction_time:.2f}s\n")
                    
                    # === DETAILED SCHEMA LOGGING ===
                    print(f"\n{'='*60}")
                    print(f"[{deal_id}] 📋 EXTRACTED CMA SCHEMA DATA (AI-Powered)")
                    print(f"{'='*60}")
                    import json
                    print(json.dumps(cma_structured_data, indent=2, default=str))
                    print(f"{'='*60}\n")
                        
                elif cma_ext == "pdf":
                    # Use Document AI for structured CMA extraction from PDF
                    print(f"[{deal_id}] 📄 Extracting CMA PDF using Document AI...")
                    
                    # Update Firestore with CMA URL
                    deal_ref.update({
                        "extracted_text.cma_report": {
                            "text": "", 
                            "pages": 0,
                            "url": cma_url,
                            "processing_method": "document_ai"
                        },
                        "raw_files.cma_report_url": cma_url
                    })
                    
                    # Extract structured CMA data using Document AI
                    step_start = time.time()
                    from services.document_ai import extract_cma_with_docai
                    cma_structured_data = await extract_cma_with_docai(
                        file_content=cma_content,
                        mime_type="application/pdf"
                    )
                    cma_extraction_time = time.time() - step_start
                    
                    # Save to BOTH cma_data (legacy) and cma_structured (new frontend expects this)
                    deal_ref.update({
                        "cma_data": cma_structured_data,
                        "cma_structured": cma_structured_data
                    })
                    print(f"[{deal_id}] ✅ CMA structured data extracted via Document AI")
                    print(f"[{deal_id}] ⏱️  CMA Parsing Time: {cma_extraction_time:.2f}s\n")
                    
                    # === DETAILED SCHEMA LOGGING ===
                    print(f"\n{'='*60}")
                    print(f"[{deal_id}] 📋 EXTRACTED CMA SCHEMA DATA (PDF)")
                    print(f"{'='*60}")
                    import json
                    print(json.dumps(cma_structured_data, indent=2, default=str))
                    print(f"{'='*60}\n")
                
                print(f"[{deal_id}] ⏱️  Extraction Time: {extraction_time:.2f}s\n")
            
            # Get current weightage
            deal_data = deal_ref.get().to_dict()
            weightage = deal_data['metadata']['weightage']
            # Use local cma_structured_data if available, else try from Firestore
            if not cma_structured_data:
                cma_structured_data = deal_data.get('cma_data', {})
            
            # Analyze with Gemini - send PDF directly (multimodal) or use CMA text
            step_start = time.time()
            if file_content:
                print(f"[{deal_id}] Starting Gemini analysis (Research Mode) - sending PDF directly...")
                analysis = await analyze_with_gemini(
                    pdf_bytes=file_content,  # Send PDF bytes directly
                    cma_text=cma_text,  # Include CMA text for financial context
                    weightage=weightage,
                    processing_mode="research"  # Force research mode
                )
            else:
                # CMA-only mode: Perform Web-Augmented Analysis using Google Search
                print(f"[{deal_id}] CMA-Only Mode - Performing Web-Augmented Analysis...")
                
                # 1. Perform Web Search to get Qualitative Data (Overview, Market, Competitors)
                web_start = time.time()
                web_analysis = await augment_cma_with_web_search(cma_text, cma_structured_data)
                print(f"[{deal_id}] ⏱️  Web Search Analysis Time: {time.time() - web_start:.2f}s")
                
                # 2. POPULATE FINANCIALS FROM CMA
                # Default empty financials with cma_tables support
                financials = {
                    "arr_mrr": {},
                    "burn_and_runway": {},
                    "projections": [],
                    "cma_tables": cma_structured_data if cma_structured_data else {}
                }
                
                if cma_structured_data:
                    # Try to extracting projections from Operating Statement for backward compatibility
                    op_statement = cma_structured_data.get('operating_statement', {})
                    years = op_statement.get('years', [])
                    rows = op_statement.get('rows', [])
                    
                    # specific rows to look for
                    revenue_row = next((r['values'] for r in rows if 'revenue' in r['particulars'].lower() or 'sales' in r['particulars'].lower()), [])
                    pat_row = next((r['values'] for r in rows if 'profit after tax' in r['particulars'].lower() or 'pat' in r['particulars'].lower()), [])
                    
                    projections = []
                    for i, year in enumerate(years):
                        proj_entry = {"year": year}
                        if i < len(revenue_row): proj_entry["revenue"] = revenue_row[i]
                        if i < len(pat_row): proj_entry["pat"] = pat_row[i]
                        projections.append(proj_entry)
                    
                    financials["projections"] = projections
                    print(f"[{deal_id}] Populated {len(projections)} projection years from CMA")

                
                # 3. RUN CREDIT ENGINE
                credit_result_dict = None
                try:
                    if cma_structured_data:
                        print(f"[{deal_id}] Running automatic Credit Analysis...")
                        # Convert to CMAModel
                        from services.credit_service import parse_cma_to_model
                        cma_model = parse_cma_to_model(cma_structured_data)
                        
                        # Create UserProfile
                        from models.credit_schemas import UserProfile
                        # Extract info from General Info or use defaults
                        # PRIORITIZE info found from Web Search!
                        web_overview = web_analysis.get('company_overview', {})
                        gen_info = cma_structured_data.get('general_info', {})
                        
                        user_profile = UserProfile(
                            deal_id=deal_id,
                            loan_amount_requested=float(loan_amount_requested) if loan_amount_requested and loan_amount_requested.replace('.','',1).isdigit() else 5000000.0, # Default 50L
                            applicant_name=web_overview.get('name') or gen_info.get('Name of the Unit') or gen_info.get('Name') or "Unknown Applicant",
                            entity_type=gen_info.get('Constitution') or "Pvt Ltd",
                            industry_sector=web_overview.get('sector') or gen_info.get('Line of Activity') or "General",
                            vintage_years=3 # Default assumption if not found
                        )
                        
                        from services.credit_service import CreditService
                        credit_service = CreditService()
                        credit_result = credit_service.analyze(cma_model, user_profile)
                        credit_result_dict = credit_result.dict()
                        
                        deal_ref.update({"credit_analysis": credit_result_dict})
                        print(f"[{deal_id}] 🔍 Credit Analysis Result: Status={credit_result.status}, Scheme={credit_result.eligible_scheme}, WaterfallLen={len(credit_result.waterfall_data)}")
                        import json
                        # print(json.dumps(credit_result_dict, indent=2, default=str)) # limiting log spam
                        print(f"[{deal_id}] ✅ Credit Analysis complete")
                except Exception as e:
                    print(f"[{deal_id}] ❌ Credit Engine Failed: {e}")
                    import traceback
                    traceback.print_exc()

                # 4. CONSTRUCT FULL MEMO
                analysis = {
                    "company_overview": web_analysis.get('company_overview', {}),
                    "market_analysis": web_analysis.get('market_analysis', {}),
                    "products_and_services": web_analysis.get('products_and_services', []),
                    "financials": financials,
                    "credit_analysis": credit_result_dict if 'credit_result_dict' in locals() else None,
                    "claims_analysis": [],
                    "risk_metrics": {},
                    "risks_and_mitigation": [],
                    "conclusion": {
                        "summary": f"This analysis is based on the CMA report ({cma_pages} pages) and web research for {web_analysis.get('company_overview', {}).get('name', 'the company')}.",
                        "strengths": ["Financial data available from CMA", "Web-verified market context"],
                        "weaknesses": ["No pitch deck provided", "Qualitative insights derived from public web data"],
                        "overall_recommendation": "PENDING - CMA Only"
                    },
                    "_weightage_used": weightage
                }
                print(f"[{deal_id}] ✅ Web-Augmented Memo created for CMA-only analysis")
            analysis_time = time.time() - step_start
            
            # Extract metadata from analysis result (instead of separate extraction)
            company_name = analysis.get('company_overview', {}).get('name', 'Unknown')
            sector = analysis.get('company_overview', {}).get('sector', 'Unknown')
            founders = analysis.get('company_overview', {}).get('founders', [])
            founder_names = []
            for f in founders:
                if isinstance(f, str):
                    founder_names.append(f)
                elif isinstance(f, dict):
                    name = f.get('name')
                    if name: founder_names.append(name)
            
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
            
            # Run Credit Analysis if CMA data is available
            try:
                updated_deal = deal_ref.get().to_dict()
                # Prefer cma_structured (has audited/projected financials) over cma_data (may have raw sheet structure)
                cma_for_credit = updated_deal.get('cma_structured') or updated_deal.get('cma_data')
                if cma_for_credit:
                    print(f"[{deal_id}] 💳 Running Credit Analysis...")
                    print(f"[{deal_id}] 📊 CMA source keys: {list(cma_for_credit.keys()) if isinstance(cma_for_credit, dict) else 'not a dict'}")
                    from services.credit_service import CreditService, parse_cma_to_model
                    from models.credit_schemas import UserProfile
                    
                    cma_model = parse_cma_to_model(cma_for_credit)
                    
                    # Build user profile from analysis
                    memo = updated_deal.get('memo', {}).get('draft_v1', {})
                    company = memo.get('company_overview', {})
                    financials = memo.get('financials', {})
                    funding_ask = financials.get('current_raise', {})
                    
                    # Parse funding amount
                    from routers.credit import parse_amount_string
                    loan_amount = parse_amount_string(str(funding_ask.get('amount', '0')))
                    
                    # Estimate vintage
                    founding_year = company.get('founding_year', datetime.now().year)
                    vintage = datetime.now().year - int(founding_year) if founding_year else 0
                    
                    user_profile = UserProfile(
                        deal_id=deal_id,
                        entity_type=company.get('legal_structure', 'Pvt Ltd'),
                        vintage_years=vintage,
                        loan_amount_requested=loan_amount if loan_amount > 0 else 50_00_000,  # Default 50L
                        has_collateral=False,
                        dpiit_recognized='dpiit' in str(company).lower(),
                        industry_sector=updated_deal.get('metadata', {}).get('sector', ''),
                        is_profitable_2_years=False
                    )
                    
                    credit_service = CreditService()
                    credit_result = credit_service.analyze(cma_model, user_profile)
                    
                    # Get the credit result as dict
                    credit_analysis_dict = credit_result.dict()
                    
                    # Merge in extracted ratios from key_ratios_summary if available
                    # These are more accurate than recalculated values
                    key_ratios = cma_for_credit.get('key_ratios_summary', {})
                    current_year_ratios = key_ratios.get('current_year', {})
                    if current_year_ratios:
                        print(f"[{deal_id}] 📊 Overriding with extracted ratios from key_ratios_summary")
                        if current_year_ratios.get('dscr'):
                            credit_analysis_dict['avg_dscr'] = float(current_year_ratios.get('dscr', 0))
                        if current_year_ratios.get('tol_tnw_ratio'):
                            credit_analysis_dict['tol_tnw'] = float(current_year_ratios.get('tol_tnw_ratio', 0))
                        if current_year_ratios.get('current_ratio'):
                            credit_analysis_dict['current_ratio'] = float(current_year_ratios.get('current_ratio', 0))
                    
                    # Add key_ratios_summary for frontend hover display
                    credit_analysis_dict['key_ratios_summary'] = key_ratios
                    
                    deal_ref.update({
                        'credit_analysis': credit_analysis_dict,
                        'metadata.credit_analyzed_at': datetime.utcnow().isoformat() + "Z"
                    })
                    
                    print(f"[{deal_id}] ✅ Credit Analysis complete: {credit_result.status} - {credit_result.eligible_scheme}")
                else:
                    print(f"[{deal_id}] ℹ️ Skipping credit analysis (no CMA data)")
            except Exception as credit_error:
                print(f"[{deal_id}] ⚠️ Credit analysis failed (non-blocking): {str(credit_error)}")
                import traceback
                traceback.print_exc()
            
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
            # Helper to delete file (GCS or Local)
            def delete_file(file_url: str):
                if not file_url: return
                if file_url.startswith("gs://"):
                    gcs_path = file_url.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                    blob = bucket.blob(gcs_path)
                    blob.delete()
                else:
                    # Local file: extract path from URL or assume logical path
                    # URL: http://host/uploads/deals/{id}/file.ext
                    if settings.LOCAL_UPLOAD_DIR in file_url:
                        # Extract relative path starting from LOCAL_UPLOAD_DIR
                        # Simple hack: split by LOCAL_UPLOAD_DIR and take last part
                        part = file_url.split(f"/{settings.LOCAL_UPLOAD_DIR}/")[-1]
                        local_path = os.path.join(settings.LOCAL_UPLOAD_DIR, part)
                        if os.path.exists(local_path):
                            os.remove(local_path)
            
            if 'raw_files' in deal_data:
                delete_file(deal_data['raw_files'].get('pitch_deck_url'))
                delete_file(deal_data['raw_files'].get('cma_report_url'))
            
            if 'memo' in deal_data:
                delete_file(deal_data['memo'].get('docx_url'))
                
        except Exception as e:
            print(f"Error deleting files: {str(e)}")
        
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
        
        url = deal_data['memo']['docx_url']
        company_name = deal_data['metadata'].get('company_name', 'Unknown')
        filename = f"{company_name}_Investment_Memo_{deal_id}.docx"
        
        if url.startswith("gs://"):
            gcs_path = url.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = bucket.blob(gcs_path)
            file_content = blob.download_as_bytes()
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
             # Local file
             # Reconstruct path: uploads/deals/{deal_id}/memo.docx 
             # (Actually create_word_document might name it differently, but let's try to find it by URL structure)
             part = url.split(f"/{settings.LOCAL_UPLOAD_DIR}/")[-1]
             local_path = os.path.join(settings.LOCAL_UPLOAD_DIR, part)
             
             if not os.path.exists(local_path):
                 raise HTTPException(status_code=404, detail="Local file not found")
                 
             return StreamingResponse(
                open(local_path, "rb"),
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
        
        url = deal_data['raw_files']['pitch_deck_url']
        company_name = deal_data['metadata'].get('company_name', 'Unknown')
        filename = f"{company_name}_Pitch_Deck_{deal_id}.pdf"
        
        if url.startswith("gs://"):
            gcs_path = url.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = bucket.blob(gcs_path)
            file_content = blob.download_as_bytes()
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
             part = url.split(f"/{settings.LOCAL_UPLOAD_DIR}/")[-1]
             local_path = os.path.join(settings.LOCAL_UPLOAD_DIR, part)
             
             if not os.path.exists(local_path):
                 raise HTTPException(status_code=404, detail="Local file not found")
                 
             return StreamingResponse(
                open(local_path, "rb"),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download_cma_report/{deal_id}")
async def download_cma_report(deal_id: str):
    """Download CMA report file (Excel or PDF)"""
    try:
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        if 'raw_files' not in deal_data or 'cma_report_url' not in deal_data['raw_files']:
            raise HTTPException(status_code=404, detail="CMA report not found")
        
        url = deal_data['raw_files']['cma_report_url']
        company_name = deal_data['metadata'].get('company_name', 'Unknown')
        
        is_xlsx = url.endswith('.xlsx')
        if is_xlsx:
            filename = f"{company_name}_CMA_Report_{deal_id}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            filename = f"{company_name}_CMA_Report_{deal_id}.pdf"
            media_type = "application/pdf"
            
        if url.startswith("gs://"):
            gcs_path = url.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = bucket.blob(gcs_path)
            file_content = blob.download_as_bytes()
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
             part = url.split(f"/{settings.LOCAL_UPLOAD_DIR}/")[-1]
             local_path = os.path.join(settings.LOCAL_UPLOAD_DIR, part)
             
             if not os.path.exists(local_path):
                 raise HTTPException(status_code=404, detail="Local file not found")
                 
             return StreamingResponse(
                open(local_path, "rb"),
                media_type=media_type,
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
            # Fallback: Check if we have the PDF file stored (new multimodal flow)
            pdf_bytes = None
            if 'raw_files' in deal_data and 'pitch_deck_url' in deal_data['raw_files']:
                try:
                    print(f"[{deal_id}] No text found. Downloading PDF for multimodal fact checking...")
                    gcs_path = deal_data['raw_files']['pitch_deck_url'].replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                    blob = bucket.blob(gcs_path)
                    pdf_bytes = blob.download_as_bytes()
                    print(f"[{deal_id}] ✅ Downloaded PDF ({len(pdf_bytes)} bytes)")
                except Exception as e:
                    print(f"[{deal_id}] ⚠️ Failed to download PDF: {str(e)}")
            
            if not pdf_bytes:
                raise HTTPException(status_code=400, detail="No pitch deck text or PDF available for fact checking")
            
            # Run verification with PDF bytes
            from services.gemini_service import verify_claims_with_google
            result = await verify_claims_with_google(pdf_bytes=pdf_bytes)
        else:
            # Run verification with extracted text
            from services.gemini_service import verify_claims_with_google
            result = await verify_claims_with_google(extracted_text=extracted_text)
        
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
