from google import genai
from google.genai.types import GenerateContentConfig
from config.settings import settings
from google.cloud import firestore
import json

client = genai.Client(
    vertexai=True,
    project=settings.GCP_PROJECT_ID,
    location=settings.GCP_LOCATION
)

db = firestore.Client(project=settings.GCP_PROJECT_ID)

async def regenerate_memo_with_interview(deal_id: str):
    """
    Update existing memo by merging pitch deck analysis + interview conversation
    """
    
    deal_ref = db.collection('deals').document(deal_id)
    deal_data = deal_ref.get().to_dict()
    
    if not deal_data:
        raise ValueError(f"Deal {deal_id} not found")
    
    original_memo = deal_data.get('memo', {}).get('draft_v1', {})
    interview = deal_data.get('interview', {})
    chat_history = interview.get('chat_history', [])
    gathered_info = interview.get('gathered_info', {})
    
    # Format chat conversation
    conversation_text = "\n\n".join([
        f"{'Analyst' if msg['role'] == 'assistant' else 'Founder'}: {msg['message']}"
        for msg in chat_history
    ])
    
    # Format gathered information
    gathered_summary = "\n".join([
        f"- {field}: {data.get('value') if isinstance(data, dict) else data}"
        for field, data in gathered_info.items()
    ])
    
    print(f"🔄 Updating memo for deal {deal_id} with interview data...")
    
    updated_memo = await merge_memo_with_interview_data(
        original_memo=original_memo,
        conversation=conversation_text,
        gathered_info=gathered_summary,
        deal_metadata=deal_data.get('metadata', {})
    )
    
    deal_ref.update({
        'memo.draft_v1': updated_memo,
        'memo.last_updated': firestore.SERVER_TIMESTAMP,
        'memo.includes_interview_data': True
    })
    
    print(f"✅ Memo updated successfully for deal {deal_id}")
    
    # Regenerate investment decision with interview-enhanced memo
    print(f"[{deal_id}] Regenerating investment decision with interview insights...")
    try:
        from services.investment_decision_service import generate_investment_decision
        
        # Get user_id from deal metadata
        user_id = deal_data.get('metadata', {}).get('user_id', 'system')
        
        # Get extracted text for context
        extracted_text = deal_data.get('extracted_text', {}).get('pitch_deck', {}).get('text', '')
        
        decision = await generate_investment_decision(
            deal_id=deal_id,
            memo=updated_memo,
            extracted_text=extracted_text,
            user_id=user_id
        )
        
        # Convert Pydantic model to dict for Firestore
        decision_dict = decision.dict() if hasattr(decision, 'dict') else decision
        
        deal_ref.update({
            "investment_decision": decision_dict,
            "metadata.investment_decision_generated_at": firestore.SERVER_TIMESTAMP
        })
        print(f"[{deal_id}] ✅ Investment decision regenerated with interview data!")
    except Exception as e:
        print(f"[{deal_id}] ⚠️ Failed to regenerate investment decision: {str(e)}")
        import traceback
        traceback.print_exc()
        # Don't fail memo update if investment decision fails
    
    return updated_memo


async def merge_memo_with_interview_data(
    original_memo: dict,
    conversation: str,
    gathered_info: str,
    deal_metadata: dict
) -> dict:
    """
    Use AI to intelligently merge pitch deck analysis with interview insights
    """
    
    company_name = deal_metadata.get('company_name', 'Unknown')
    sector = deal_metadata.get('sector', 'Unknown')
    
    # ✅ Properly escape memo
    memo_json = json.dumps(original_memo, indent=2)
    
    merge_prompt = f"""You are an expert investment analyst. You need to UPDATE an investment memo by merging information from a pitch deck analysis with insights gathered from a founder interview.

## COMPANY: {company_name} ({sector})

## ORIGINAL MEMO (from pitch deck):
{memo_json}

## INTERVIEW CONVERSATION:
{conversation}

## KEY INFORMATION GATHERED:
{gathered_info}

## YOUR TASK:
Create an UPDATED investment memo that:
1. Keeps all good information from the original memo
2. REPLACES missing/vague data with specific information from the interview
3. ADDS new insights learned from the conversation
4. IMPROVES shallow sections with detail from the interview
5. Maintains the same JSON structure as the original memo

## SPECIFIC INSTRUCTIONS:

### Financials Section:
- Update ARR, MRR, burn rate, runway with specific numbers from interview
- If founder didn't know something, keep original or mark as "Not available from interview"
- Add any new financial insights mentioned
- Update funding history with new details
- Add unit economics (CAC, LTV) if discussed

### Team Section:
- Enhance founder backgrounds with details from conversation
- Add experiences, education, previous companies mentioned
- Add years of relevant experience
- Add information about previous ventures and outcomes
- Keep original info if interview didn't cover it

### Market Analysis:
- Update TAM/SAM if better numbers discussed
- Add competitor insights from conversation
- Enhance market trends with founder's perspective
- Add growth rate information if mentioned

### Business Model:
- Update unit economics (CAC, LTV) if discussed
- Add pricing details from conversation
- Clarify revenue streams if explained better
- Add sales cycle details if mentioned

### Traction:
- Add customer numbers, growth metrics mentioned
- Update with any milestones discussed
- Add monthly growth rates if provided
- Keep original if not covered in interview

### Claims Analysis:
- Validate or update claims based on conversation
- Add supporting evidence mentioned by founder
- Update metrics with real data from interview

### Risk Assessment:
- Keep original risk scores
- Add notes about information gathered to mitigate risks
- Update risk factors based on founder's insights

### Conclusion Section:
- Ensure the conclusion follows the structured format:
  - overall_attractiveness
  - product_summary
  - financial_analysis
  - investment_thesis
  - risk_summary
- Update these fields based on new insights from the interview

## IMPORTANT RULES:
1. If interview provided specific data → USE IT (it's more recent and direct from founder)
2. If interview didn't cover a topic → KEEP original analysis
3. If founder said "I don't know" → Keep original or mark as "Information not available"
4. Maintain exact JSON structure - don't change schema
5. Be comprehensive - this is the final memo
6. Merge intelligently - don't duplicate information

Return the complete updated memo in the exact same JSON structure (VALID JSON only):"""
    
    try:
        response = client.models.generate_content(
            model='gemini-3-pro-preview',
            contents=merge_prompt,
            config=GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
                max_output_tokens=16384
            )
        )
        
        # ✅ Validate response
        if response is None or not hasattr(response, 'text') or response.text is None:
            print(f"⚠️ Invalid response from API: {response}")
            raise ValueError("API returned invalid response")
        
        response_text = response.text.strip()
        
        if not response_text:
            raise ValueError("API returned empty response")
        
        # ✅ Clean markdown
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # ✅ Parse with error handling
        try:
            updated_memo = json.loads(response_text)
            print("✅ Memo successfully merged with interview data")
            return updated_memo
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {str(e)}")
            print(f"Response preview: {response_text[:500]}")
            # Fallback
            original_memo['interview_summary'] = gathered_info
            return original_memo
        
    except Exception as e:
        print(f"❌ Error merging memo: {str(e)}")
        # Fallback
        original_memo['interview_summary'] = gathered_info
        return original_memo