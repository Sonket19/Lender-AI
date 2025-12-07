from typing import Dict, Any, List, Tuple
from google.cloud import firestore
from datetime import datetime, timedelta
import secrets
import json
from config.settings import settings
from google import genai
from google.genai.types import GenerateContentConfig

client = genai.Client(
    vertexai=True,
    project=settings.GCP_PROJECT_ID,
    location=settings.GCP_LOCATION
)

db = firestore.Client(project=settings.GCP_PROJECT_ID)

def generate_interview_token() -> str:
    """Generate secure unique token for interview"""
    return secrets.token_urlsafe(32)

def is_field_missing_or_shallow(value: Any, field_type: str = "text") -> Tuple[bool, str]:
    """
    Check if field is missing or needs more detail
    Returns: (needs_attention, reason)
    """
    if value is None:
        return True, "missing"
    
    # Convert to string for analysis
    value_str = str(value).strip()
    
    # Check for explicit missing indicators
    missing_indicators = [
        "not available",
        "n/a",
        "unknown",
        "not provided",
        "not mentioned",
        "no information",
        "not specified",
        "not found",
        ""
    ]
    
    if value_str.lower() in missing_indicators:
        return True, "missing"
    
    # Check for shallow/vague content (needs more detail)
    if field_type == "text":
        # Text should be at least 20 characters for meaningful content
        if len(value_str) < 20:
            return True, "too_vague"
        
        # Check for vague phrases
        vague_phrases = [
            "limited information",
            "details unclear",
            "not enough detail",
            "minimal information",
            "brief mention",
            "vague description"
        ]
        if any(phrase in value_str.lower() for phrase in vague_phrases):
            return True, "needs_detail"
    
    elif field_type == "list":
        if isinstance(value, list) and len(value) == 0:
            return True, "missing"
        if isinstance(value, list) and len(value) < 2:
            return True, "needs_more_items"
    
    elif field_type == "numeric":
        # Check for numeric fields that are zero or missing
        try:
            num_val = float(value_str.replace('$', '').replace(',', '').replace('%', ''))
            if num_val == 0:
                return True, "zero_value"
        except:
            return True, "invalid_numeric"
    
    return False, "complete"

def identify_missing_and_shallow_fields(deal_data: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """
    Use AI to intelligently identify missing, shallow, and vague information in memo
    """
    
    memo = deal_data.get('memo', {}).get('draft_v1', {})
    metadata = deal_data.get('metadata', {})
    
    company_name = metadata.get('company_name', 'Unknown')
    sector = metadata.get('sector', 'Unknown')
    stage = metadata.get('stage', 'Unknown')
    
    # Build memo JSON safely
    memo_json = json.dumps(memo, indent=2)
    
    # Build prompt without raw newlines in f-string
    analysis_prompt = f"""You are an experienced VC analyst reviewing an investment memo for completeness and depth.

COMPANY INFORMATION:
- Name: {company_name}
- Sector: {sector}
- Stage: {stage}

INVESTMENT MEMO TO ANALYZE:
{memo_json}

YOUR TASK:
Analyze this memo and identify:
1. MISSING - Critical information completely absent
2. SHALLOW - Information present but too brief/vague to be useful
3. NEEDS_DETAIL - Basic info exists but lacks depth for investment decision

WHAT TO CHECK:

Financials (CRITICAL):
- ARR/MRR with specific numbers
- Monthly burn rate with actual amount
- Runway in months
- Funding history (rounds, amounts, investors)
- Gross margin percentage
- Revenue projections for next 2-3 years
- Unit economics (CAC, LTV) with calculations

Team (CRITICAL):
- Each founder's full background (education + work experience)
- Years of relevant experience
- Previous startups or exits
- Domain expertise credentials

Market (HIGH):
- TAM with source/calculation
- SAM and SOM breakdown
- Market growth rate with evidence
- At least 3-4 main competitors with details

Business Model (HIGH):
- Clear revenue streams
- Pricing strategy and tiers
- Customer acquisition channels
- Sales cycle details

Traction (HIGH):
- Customer count with specifics
- Revenue metrics month-over-month
- Key milestones achieved

IMPORTANT RULES:
- "Not available" or "N/A" or "Unknown" = MISSING
- Very brief text (less than 30 characters) = SHALLOW
- Generic statements without specifics = NEEDS_DETAIL
- Zero or null values = MISSING
- Ask specific questions 
- Don't repeat same question.

Return VALID JSON with this exact structure (no extra text):
{{
    "missing": [
        {{
            "field": "field_id",
            "category": "financials/team/market/business/traction/product",
            "question": "Natural question to ask",
            "importance": "critical/high/medium/low"
        }}
    ],
    "shallow": [],
    "needs_detail": []
}}

Only return valid JSON, nothing else:"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=analysis_prompt,
            config=GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
                max_output_tokens=32768
            )
        )
        
        print("Response Text: ",response.text)
        response_text = response.text.strip()
        
        # Clean up response if it has markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith('```'):
            response_text = response_text[3:]  # Remove ```
        if response_text.endswith('```'):
            response_text = response_text[:-3]  # Remove trailing ```
        
        # response_text = response_text.strip()
        print("Final Text: ",response_text)
        issues = json.loads(response_text)
        
        print(f"📊 Gap Analysis Complete:")
        print(f"   - Missing: {len(issues.get('missing', []))}")
        print(f"   - Shallow: {len(issues.get('shallow', []))}")
        print(f"   - Needs Detail: {len(issues.get('needs_detail', []))}")
        
        return issues
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {str(e)}")
        print(f"Response was: {response_text[:200]}")
        raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
    except Exception as e:
        print(f"❌ Error analyzing memo gaps: {str(e)}")
        raise ValueError(f"Failed to analyze memo: {str(e)}")

def generate_draft_interview(deal_id: str) -> bool:
    """
    Generate interview questions and save as draft.
    Returns True if questions were generated, False if no questions needed.
    """
    print(f"[{deal_id}] Generating draft interview questions...")
    
    # Get deal data
    deal_ref = db.collection('deals').document(deal_id)
    deal_data = deal_ref.get().to_dict()
    
    if not deal_data:
        print(f"[{deal_id}] Deal not found")
        return False
        
    # Identify issues
    try:
        issues = identify_missing_and_shallow_fields(deal_data)
    except Exception as e:
        print(f"[{deal_id}] Failed to identify issues: {e}")
        return False
    
    # Flatten and sort issues
    all_issues = []
    for category in ['missing', 'shallow', 'needs_detail']:
        for issue in issues.get(category, []):
            issue['status'] = category
            all_issues.append(issue)
            
    importance_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    all_issues.sort(key=lambda x: importance_order.get(x['importance'], 999))
    
    # ALWAYS ADD DEFAULT REGULATORY & COMPLIANCE QUESTION AT THE START
    regulatory_question = {
        'field': 'regulatory_compliance',
        'category': 'risks',
        'question': 'Can you share details about any regulatory requirements, compliance frameworks, or legal considerations relevant to your business? For example, data privacy regulations (GDPR, CCPA), industry-specific licenses, or certifications you need to maintain.',
        'importance': 'high',
        'status': 'default_question'
    }
    
    # Prepend the regulatory question to the front
    all_issues.insert(0, regulatory_question)
    
    if not all_issues:
        print(f"[{deal_id}] No issues found, skipping interview generation")
        return False
        
    # Create draft interview object
    interview_data = {
        'deal_id': deal_id,
        'status': 'draft',
        'created_at': datetime.utcnow().isoformat() + "Z",
        'issues': all_issues,
        'missing_fields': [issue['field'] for issue in all_issues],
        'gathered_info': {},
        'cannot_answer_fields': [],
        'asked_questions': [],
        'ask_count': {},
        'progress': {
            'total': len(all_issues),
            'answered': 0,
            'cannot_answer': 0,
            'attempted': 0,
            'remaining': len(all_issues),
            'is_complete': False
        },
        'chat_history': [],
        'is_complete': False
    }
    
    deal_ref.update({
        'interview': interview_data
    })
    
    print(f"[{deal_id}] Draft interview saved with {len(all_issues)} questions")
    return True

def create_interview(deal_id: str, founder_email: str, founder_name: str = None) -> Dict[str, Any]:
    """
    Activate an existing draft interview or create a new one if missing.
    Generates token and sends email.
    """
    deal_ref = db.collection('deals').document(deal_id)
    deal_data = deal_ref.get().to_dict()
    
    if not deal_data:
        raise ValueError(f"Deal {deal_id} not found")
        
    interview = deal_data.get('interview')
    
    # Case 1: Interview already active or pending - return existing
    if interview and interview.get('status') in ['pending', 'active']:
        # Update email/name if provided
        updates = {}
        if founder_email and founder_email != interview.get('founder_email'):
            updates['interview.founder_email'] = founder_email
            interview['founder_email'] = founder_email
        if founder_name and founder_name != interview.get('founder_name'):
            updates['interview.founder_name'] = founder_name
            interview['founder_name'] = founder_name
            
        if updates:
            deal_ref.update(updates)
            
        return {
            "deal_id": deal_id,
            "token": interview['token'],
            "link": f"{settings.FRONTEND_URL}/interview/{interview['token']}",
            "total_questions": len(interview.get('issues', [])),
            "critical_questions": len([i for i in interview.get('issues', []) if i.get('importance') == 'critical']),
            "breakdown": {} # Not strictly needed for re-sending
        }

    # Case 2: No draft exists - generate one now (fallback)
    if not interview or interview.get('status') != 'draft':
        print(f"[{deal_id}] No draft interview found, generating now...")
        has_questions = generate_draft_interview(deal_id)
        if not has_questions:
            raise ValueError("No questions generated for this deal. Interview not needed.")
        # Refetch to get the draft
        deal_data = deal_ref.get().to_dict()
        interview = deal_data.get('interview')

    # Case 3: Activate draft
    token = generate_interview_token()
    
    updates = {
        'interview.status': 'pending',
        'interview.token': token,
        'interview.founder_email': founder_email,
        'interview.founder_name': founder_name or "Founder",
        'interview.expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z",
        'interview.activated_at': datetime.utcnow().isoformat() + "Z"
    }
    
    deal_ref.update(updates)
    
    # Merge updates into local object for return
    interview.update({
        'token': token,
        'founder_email': founder_email,
        'founder_name': founder_name
    })
    
    return {
        "deal_id": deal_id,
        "token": token,
        "link": f"{settings.FRONTEND_URL}/interview/{token}",
        "total_questions": len(interview['issues']),
        "critical_questions": len([i for i in interview['issues'] if i.get('importance') == 'critical']),
        "breakdown": {
            "missing": len([i for i in interview['issues'] if i.get('status') == 'missing']),
            "shallow": len([i for i in interview['issues'] if i.get('status') == 'shallow']),
            "needs_detail": len([i for i in interview['issues'] if i.get('status') == 'needs_detail'])
        }
    }

# def validate_interview_token(token: str) -> Dict[str, Any]:
#     """
#     Validate interview token and return interview data
#     Uses single query on deals collection
#     """
#     # Query deals collection for matching token
#     deals_ref = db.collection('deals')
#     query = deals_ref.where('interview.token', '==', token).limit(1)
    
#     results = list(query.stream())
    
#     if not results:
#         raise ValueError("Invalid interview token")
    
#     deal_doc = results[0]
#     deal_data = deal_doc.to_dict()
#     deal_id = deal_doc.id
    
#     if 'interview' not in deal_data:
#         raise ValueError("No interview found")
    
#     interview = deal_data['interview']
    
#     # Check status
#     if interview['status'] == 'completed':
#         raise ValueError("Interview already completed")
    
#     if interview['status'] == 'expired':
#         raise ValueError("Interview link has expired")
    
#     # Check expiration
#     expires_at = datetime.fromisoformat(interview['expires_at'].replace('Z', '+00:00'))
#     if datetime.utcnow() > expires_at.replace(tzinfo=None):
#         # Mark as expired
#         db.collection('deals').document(deal_id).update({
#             'interview.status': 'expired'
#         })
#         raise ValueError("Interview link has expired")
    
#     # Mark as active if pending
#     if interview['status'] == 'pending':
#         db.collection('deals').document(deal_id).update({
#             'interview.status': 'active',
#             'interview.started_at': datetime.utcnow().isoformat() + "Z"
#         })
#         interview['status'] = 'active'
    
#     interview['deal_id'] = deal_id
#     interview['company_name'] = deal_data.get('metadata', {}).get('company_name', 'Unknown')
#     interview['sector'] = deal_data.get('metadata', {}).get('sector', 'Unknown')
    
#     return interview

def validate_interview_token(token: str) -> Dict[str, Any]:
    """
    Validate interview token and return interview data
    Uses single query on deals collection
    """
    # Query deals collection for matching token
    deals_ref = db.collection('deals')
    query = deals_ref.where('interview.token', '==', token).limit(1)
    
    results = list(query.stream())
    
    if not results:
        raise ValueError("Invalid interview token")
    
    deal_doc = results[0]
    deal_data = deal_doc.to_dict()
    deal_id = deal_doc.id
    
    if 'interview' not in deal_data:
        raise ValueError("No interview found")
    
    interview = deal_data['interview']
    
    # Check status
    if interview['status'] == 'completed':
        raise ValueError("Interview already completed")
    
    if interview['status'] == 'expired':
        raise ValueError("Interview link has expired")
    
    # Check expiration
    expires_at = datetime.fromisoformat(interview['expires_at'].replace('Z', '+00:00'))
    if datetime.utcnow() > expires_at.replace(tzinfo=None):
        # Mark as expired
        db.collection('deals').document(deal_id).update({
            'interview.status': 'expired'
        })
        raise ValueError("Interview link has expired")
    
    # Mark as active if pending
    if interview['status'] == 'pending':
        db.collection('deals').document(deal_id).update({
            'interview.status': 'active',
            'interview.started_at': datetime.utcnow().isoformat() + "Z"
        })
        interview['status'] = 'active'
    
    interview['deal_id'] = deal_id
    interview['company_name'] = deal_data.get('metadata', {}).get('company_name', 'Unknown')
    interview['sector'] = deal_data.get('metadata', {}).get('sector', 'Unknown')
    
    return interview

# def complete_interview(deal_id: str, gathered_info: Dict[str, Any]):
#     """Mark interview as complete and update deal with gathered info"""
#     deal_ref = db.collection('deals').document(deal_id)
    
#     # Update interview status
#     deal_ref.update({
#         'interview.status': 'completed',
#         'interview.completed_at': datetime.utcnow().isoformat() + "Z",
#         'interview.gathered_info': gathered_info
#     })
    
#     # Update deal memo with gathered information
#     update_deal_with_interview_data(deal_id, gathered_info)

# def complete_interview(deal_id: str, gathered_info: Dict[str, Any]):
#     """Mark interview as complete and update memo with interview data"""
#     from services.memo_regeneration import regenerate_memo_with_interview
#     import asyncio
    
#     deal_ref = db.collection('deals').document(deal_id)
    
#     # Update interview status
#     deal_ref.update({
#         'interview.status': 'completed',
#         'interview.completed_at': datetime.utcnow().isoformat() + "Z",
#         'interview.gathered_info': gathered_info
#     })
    
#     print(f"✅ Interview completed for deal {deal_id}")
#     print(f"🔄 Updating memo with interview insights...")
    
#     # Update memo with interview data
#     try:
#         loop = asyncio.get_event_loop()
#         if loop.is_running():
#             asyncio.create_task(regenerate_memo_with_interview(deal_id))
#         else:
#             loop.run_until_complete(regenerate_memo_with_interview(deal_id))
#     except Exception as e:
#         print(f"❌ Error updating memo: {str(e)}")

def complete_interview(deal_id: str, gathered_info: Dict[str, Any]):
    """Mark interview as complete and update memo with interview data"""
    from services.memo_regeneration import regenerate_memo_with_interview
    import asyncio
    
    deal_ref = db.collection('deals').document(deal_id)
    
    # Update interview status
    deal_ref.update({
        'interview.status': 'completed',
        'interview.completed_at': datetime.utcnow().isoformat() + "Z",
        'interview.gathered_info': gathered_info
    })
    
    print(f"✅ Interview completed for deal {deal_id}")
    print(f"🔄 Updating memo with interview insights...")
    
    # Update memo with interview data
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(regenerate_memo_with_interview(deal_id))
        else:
            loop.run_until_complete(regenerate_memo_with_interview(deal_id))
    except Exception as e:
        print(f"❌ Error updating memo: {str(e)}")

def update_deal_with_interview_data(deal_id: str, gathered_info: Dict[str, Any]):
    """Update deal memo with information gathered from interview"""
    deal_ref = db.collection('deals').document(deal_id)
    
    updates = {}
    
    # Map gathered info back to memo structure
    for field_key, field_data in gathered_info.items():
        if field_key.startswith('current_arr'):
            if isinstance(field_data, dict) and 'value' in field_data:
                updates['memo.draft_v1.financials.arr_mrr.current_booked_arr'] = field_data['value']
        elif field_key.startswith('current_mrr'):
            if isinstance(field_data, dict) and 'value' in field_data:
                updates['memo.draft_v1.financials.arr_mrr.current_mrr'] = field_data['value']
        elif field_key.startswith('burn_rate'):
            if isinstance(field_data, dict) and 'value' in field_data:
                updates['memo.draft_v1.financials.burn_and_runway.implied_net_burn'] = field_data['value']
        elif field_key.startswith('runway'):
            if isinstance(field_data, dict) and 'value' in field_data:
                updates['memo.draft_v1.financials.burn_and_runway.stated_runway'] = field_data['value']
        elif field_key == 'funding_history':
            if isinstance(field_data, dict) and 'value' in field_data:
                updates['memo.draft_v1.financials.funding_history'] = field_data['value']
        # Add more mappings as needed
    
    if updates:
        try:
            deal_ref.update(updates)
            print(f"✅ Updated {len(updates)} fields in memo for deal {deal_id}")
        except Exception as e:
            print(f"❌ Error updating memo: {str(e)}")
            # Store in separate field if direct update fails
            deal_ref.update({
                'interview.memo_updates_pending': updates
            })
