# from typing import Dict, Any, List
# from google import genai
# from google.genai.types import GenerateContentConfig
# from config.settings import settings
# import json

# client = genai.Client(
#     vertexai=True,
#     project=settings.GCP_PROJECT_ID,
#     location=settings.GCP_LOCATION
# )

# async def chat_with_founder(
#     interview_data: Dict[str, Any],
#     user_message: str,
#     chat_history: List[Dict[str, str]]
# ) -> Dict[str, Any]:
#     """
#     Natural conversational AI that adapts to founder's responses
#     """
    
#     company_name = interview_data.get('company_name', 'your startup')
#     sector = interview_data.get('sector', 'your industry')
#     founder_name = interview_data.get('founder_name', 'Founder')
#     issues = interview_data.get('issues', [])
#     gathered_info = interview_data.get('gathered_info', {})
#     cannot_answer_fields = interview_data.get('cannot_answer_fields', [])
    
#     # ✅ Get all original issue field names
#     all_issue_fields = [issue['field'] for issue in issues]
    
#     # ✅ Only count gathered_info that matches actual issue fields
#     gathered_issue_fields = [f for f in gathered_info.keys() if f in all_issue_fields]

#     # Build what we still need - EXCLUDE fields they can't answer
#     still_needed = [
#         {
#             'field': issue['field'],
#             'question': issue['question'],
#             'category': issue['category'],
#             'importance': issue['importance'],
#             'status': issue['status']
#         }
#         for issue in issues
#         if issue['field'] not in gathered_issue_fields and issue['field'] not in cannot_answer_fields
#     ]
    
#     # Get recent context
#     recent_context = chat_history[-10:] if len(chat_history) > 10 else chat_history
    
#     # Get next 3 questions to ask
#     next_questions = [q['question'] for q in still_needed[:3]]
    
#     # ✅ Check if this should be closing message
#     # print("still_needed: ", still_needed)
#     # print("gathered_info: ", gathered_info)
#     # print("cannot_answer_fields: ", len(cannot_answer_fields))
#     # print("Still Need Count: ", len(still_needed))
#     print(f"📋 Total issues: {len(all_issue_fields)}")
#     print(f"✅ Gathered (matching issues): {len(gathered_issue_fields)}")
#     print(f"📊 Progress: {len(gathered_issue_fields) + len(cannot_answer_fields)}/{len(all_issue_fields)}")
    

#     will_be_closing = len(still_needed) <= 0
    
#     # Build conversation prompt
#     if will_be_closing:
#         # ✅ CLOSING MESSAGE
#         prompt = f"""
# You are Sarah, a friendly investment analyst. You just finished interviewing {founder_name} about {company_name}.

# ## CONTEXT:
# - We've gathered all the important information we need
# - Total topics: {len(all_issue_fields)}
# - Answered: {len(gathered_issue_fields)}
# - Couldn't answer: {len(cannot_answer_fields)}
# - Founder's last message: "{user_message}"

# ## YOUR TASK:
# Write a warm, professional CLOSING message that:
# 1. Thanks them for their time and openness
# 2. Summarizes what you'll do next (update investment memo, share feedback)
# 3. Encourages them about their company
# 4. Mentions when they might expect to hear back (within 2-3 weeks)
# 5. Leaves them feeling positive

# Keep it 60-100 words. Be warm and genuine, not robotic.

# Closing message:
# """
#     else:
#         # ✅ NORMAL CONTINUATION
#         prompt = f"""
# You are Sarah, a friendly investment analyst talking with {founder_name} about {company_name} ({sector}).

# ## CONTEXT:
# - Progress: {len(gathered_issue_fields) + len(cannot_answer_fields)}/{len(all_issue_fields)} topics covered
# - Founder's latest message: "{user_message}"
# - Fields they already said they don't know: {json.dumps(cannot_answer_fields[:5])}

# ## NEXT 3 QUESTIONS TO ASK (in priority order):
# 1. {next_questions[0] if len(next_questions) > 0 else 'Tell me about your financials?'}
# 2. {next_questions[1] if len(next_questions) > 1 else 'Tell me about your team?'}
# 3. {next_questions[2] if len(next_questions) > 2 else 'Tell me about your market?'}

# ## RECENT CONVERSATION:
# {json.dumps(recent_context, indent=2)}

# ## YOUR RULES:
# 1. Be warm, conversational, human-like
# 2. Acknowledge their answer briefly (1-2 sentences)
# 3. THEN ASK THE NEXT QUESTION (required!)
# 4. If they say "don't know":
#    - First time → Try ONE different angle OR ask for rough estimate
#    - After that → Move to DIFFERENT question, don't repeat
# 5. One question at a time, 40-80 words total
# 6. Make it feel like coffee chat, not interrogation
# 7. MUST END WITH A QUESTION MARK
# 8. DO NOT ask questions about topics in "Fields they already said they don't know"

# ## CRITICAL: YOUR RESPONSE MUST:
# ✓ Acknowledge their answer
# ✓ Ask ONE of the next 3 questions above
# ✓ End with "?"
# ✓ NOT ask questions they already said they don't know to

# Based on all this, respond with acknowledgment + next question:
# """
    
#     try:
#         response = client.models.generate_content(
#             model='gemini-2.5-flash',
#             contents=prompt,
#             config=GenerateContentConfig(
#                 temperature=0.85,
#                 max_output_tokens=5000,
#                 top_p=0.95
#             )
#         )
        
#         if response is None or not hasattr(response, 'text'):
#             raise ValueError("Invalid API response")
        
#         ai_message = response.text.strip()
        
#         if not ai_message:
#             raise ValueError("Empty response from AI")
        
#         # ✅ Only add question mark if NOT closing message
#         if not will_be_closing:
#             if not ai_message.endswith('?'):
#                 if not any(ai_message.endswith(p) for p in ['?', '!', '.']):
#                     ai_message += '?'
#                 elif ai_message.endswith('.'):
#                     if '?' not in ai_message:
#                         ai_message = ai_message[:-1] + '?'
        
#     except Exception as e:
#         print(f"❌ Chat Error: {str(e)}")
#         if will_be_closing:
#             ai_message = f"Thank you so much for your time, {founder_name}! We've gathered excellent insights about {company_name}. I'll update our investment memo and get back to you within 2-3 weeks with our feedback. Best of luck with everything!"
#         else:
#             next_q = still_needed[0]['question'] if still_needed else "What else can you tell me?"
#             ai_message = f"Thanks for sharing! {next_q}"
    
#     # Extract what was gathered from this turn
#     completion_check = await analyze_and_extract(
#         issues,
#         gathered_info,
#         cannot_answer_fields,
#         chat_history + [
#             {"role": "user", "message": user_message},
#             {"role": "assistant", "message": ai_message}
#         ]
#     )
    
#     return {
#         "message": ai_message,
#         "is_complete": completion_check['is_complete'],
#         "gathered_info": completion_check['gathered_info'],
#         "cannot_answer_fields": completion_check.get('cannot_answer_fields', [])
#     }

# async def analyze_and_extract(
#     issues: List[Dict[str, str]],
#     gathered_info: Dict[str, Any],
#     existing_cannot_answer: List[str],
#     chat_history: List[Dict[str, str]]
# ) -> Dict[str, Any]:
#     """
#     Let AI analyze conversation and decide what to extract and if complete
#     """
    
#     user_messages = [msg for msg in chat_history if msg['role'] == 'user']
    
#     if len(user_messages) < 2:
#         return {
#             "is_complete": False,
#             "gathered_info": gathered_info,
#             "still_pending": [i['field'] for i in issues],
#             "cannot_answer_fields": []
#         }
    
#     # ✅ Get all issue field names
#     all_issue_fields = [issue['field'] for issue in issues]

#     # Build conversation
#     conversation = []
#     for msg in chat_history[-20:]:
#         role = "Analyst" if msg['role'] == 'assistant' else "Founder"
#         conversation.append(f"{role}: {msg['message']}")
    
#     # What we're looking for
#     fields_needed = [
#         {
#             'field': issue['field'],
#             'question': issue['question'],
#             'category': issue['category']
#         }
#         for issue in issues
#         if issue['field'] not in gathered_info
#     ]
    
#     # Ask AI to analyze
#     analysis_prompt = f"""
# Analyze this founder interview and decide:

# ## INFORMATION NEEDED:
# {json.dumps(fields_needed[:15], indent=2)}

# ## ALREADY HAVE:
# {json.dumps([f for f in gathered_info.keys() if f in all_issue_fields])}

# ## CONVERSATION:
# {json.dumps(conversation, indent=2)}

# ## YOUR TASK:
# 1. Extract ANY specific information founder mentioned (numbers, facts, names)
# 2. Track which topics they said "don't know" or couldn't answer
# 3. Decide if interview should continue or wrap up
# 4. Match extracted info to the field names in "field_name"

# Return JSON:
# {{
#     "extracted": {{
#         "field_name": {{
#             "value": "what they said",
#             "confidence": "high/medium/low"
#         }}
#     }},
#     "cannot_answer": ["field1", "field2"],
#     "is_complete": true/false,
#     "completion_reason": "why"
# }}

# RULES:
# - Extract ONLY specific data (numbers, names, facts)
# - Ignore: "I don't know", "not sure", vague answers
# - Confidence high = clear specific answer
# - Confidence medium = partial/rough answer
# - cannot_answer = topics they explicitly said they don't know
# - is_complete = true ONLY if:
#   * All the issues attempted 
#   * NOT just because we've talked a lot
# """
    
#     try:
#         response = client.models.generate_content(
#             model='gemini-2.5-flash',
#             contents=analysis_prompt,
#             config=GenerateContentConfig(
#                 temperature=0.2,
#                 response_mime_type="application/json",
#                 max_output_tokens=5000
#             )
#         )
        
#         if response is None or not hasattr(response, 'text') or response.text is None:
#             raise ValueError("Invalid API response")
        
#         response_text = response.text.strip()
        
#         if not response_text:
#             raise ValueError("Empty response")
        
#         result = json.loads(response_text)
        
#         # Merge extracted info
#         merged = {**gathered_info}
#         for field, data in result.get('extracted', {}).items():
#             # if data.get('confidence') in ['high', 'medium']:
#             if field in all_issue_fields and data.get('confidence') in ['high', 'medium']:
#                 merged[field] = data
        
#         # # Calculate coverage - STRICTER now
#         # total_issues = len(issues)
#         # gathered = len(merged)
#         # cannot_answer = len(result.get('cannot_answer', []))

#         # # Calculate how many issues have been attempted (either answered or marked as "don't know")
#         # total_attempted = gathered + cannot_answer

#         # ✅ Get NEW cannot_answer fields from this response
#         new_cannot_answer = [f for f in result.get('cannot_answer', []) if f in all_issue_fields]
        
#         # ✅ Calculate progress based on ACTUAL issue fields only
#         gathered_count = len([f for f in merged.keys() if f in all_issue_fields])
#         total_cannot_answer = len(set(existing_cannot_answer + new_cannot_answer))
#         total_attempted = gathered_count + total_cannot_answer
#         total_issues = len(all_issue_fields)
        
#         # # Completion criteria (much stricter)
#         # gathered_pct = gathered / total if total > 0 else 0
#         # cannot_answer_pct = cannot_answer / total if total > 0 else 0
#         # total_coverage_pct = (gathered + cannot_answer) / total if total > 0 else 0
        
#         # # ✅ FIXED: More strict completion check
#         # is_complete = (
#         #     (result.get('is_complete') == True and gathered >= total * 0.8) or  # AI says complete AND 80% gathered
#         #     (gathered >= total * 0.85) or  # 85% gathered
#         #     (total_coverage_pct >= 0.95 and cannot_answer > 0)  # 95% covered (including don't knows)
#         # )
        
#         # print(f"📊 {gathered}/{total} gathered ({gathered_pct*100:.0f}%), {cannot_answer} can't answer ({cannot_answer_pct*100:.0f}%), total coverage: {total_coverage_pct*100:.0f}%")
#         # print(f"   is_complete: {is_complete}")


#         # Simple rule: Interview is complete when ALL issues are attempted
#         is_complete = (total_attempted >= total_issues)

#         print(f"📊 Extraction result:")
#         print(f"   - Gathered: {gathered_count}/{total_issues}")
#         print(f"   - Cannot answer: {total_cannot_answer}")
#         print(f"   - Total attempted: {total_attempted}/{total_issues}")
#         print(f"   - Complete: {is_complete}")
        
#         return {
#             "is_complete": is_complete,
#             "gathered_info": merged,
#             "still_pending": [f for f in all_issue_fields if f not in merged.keys() and f not in existing_cannot_answer],
#             # "cannot_answer_fields": result.get('cannot_answer', [])
#             "cannot_answer_fields": new_cannot_answer  # Only NEW ones from this turn
#         }
        
#     except json.JSONDecodeError as e:
#         print(f"❌ JSON Parse Error: {str(e)}")
#         return {
#             "is_complete": False,
#             "gathered_info": gathered_info,
#             "still_pending": [f['field'] for f in fields_needed],
#             "cannot_answer_fields": []
#         }
#     except Exception as e:
#         print(f"❌ Analysis Error: {str(e)}")
#         return {
#             "is_complete": False,
#             "gathered_info": gathered_info,
#             "still_pending": [f['field'] for f in fields_needed],
#             "cannot_answer_fields": []
#         }


"""
Reliable Interview System with Answer Validation
- No repeated questions
- Deterministic completion (pure math, no LLM)
- Validates answer relevance (catches random/joke answers)
- Re-asks up to 2 times for irrelevant answers
"""

from typing import Dict, Any, List, Optional
from google import genai
from google.genai.types import GenerateContentConfig
from config.settings import settings
import json
import re


client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


# ===== STATE MANAGEMENT =====

class InterviewState:
    """Clear state tracking for interview progress"""
    
    def __init__(self, interview_data: Dict[str, Any]):
        self.all_issues = interview_data.get('issues', [])
        self.gathered_info = interview_data.get('gathered_info', {})
        self.cannot_answer = set(interview_data.get('cannot_answer_fields', []))
        self.asked_questions = set(interview_data.get('asked_questions', []))
        self.ask_count = interview_data.get('ask_count', {})
        
        # Get all field names
        self.all_fields = [issue['field'] for issue in self.all_issues]
        
    def get_ask_count(self, field: str) -> int:
        """Get how many times we've asked this question"""
        return self.ask_count.get(field, 0)
    
    def increment_ask_count(self, field: str):
        """Increment ask count for a field"""
        self.ask_count[field] = self.ask_count.get(field, 0) + 1
        
    def get_next_question(self) -> Optional[Dict[str, Any]]:
        """Get next unanswered question that hasn't been asked too many times"""
        for issue in self.all_issues:
            field = issue['field']
            
            # Skip if already gathered or cannot answer
            if field in self.gathered_info or field in self.cannot_answer:
                continue
            
            # Allow re-asking up to 2 times if user gave irrelevant answers
            ask_count = self.get_ask_count(field)
            if ask_count >= 2:  # Asked twice already, skip
                # Mark as cannot answer if asked twice and still no good answer
                self.cannot_answer.add(field)
                continue
            
            return {
                'field': field,
                'question': issue['question'],
                'category': issue.get('category', 'General'),
                'importance': issue.get('importance', 'medium'),
                'ask_count': ask_count
            }
        
        return None
    
    def mark_question_asked(self, field: str):
        """Mark question as asked"""
        self.asked_questions.add(field)
        self.increment_ask_count(field)
    
    def add_answer(self, field: str, value: Any, confidence: str = 'high'):
        """Record an answer"""
        self.gathered_info[field] = {
            'value': value,
            'confidence': confidence
        }
    
    def mark_cannot_answer(self, field: str):
        """Mark field as cannot answer"""
        self.cannot_answer.add(field)
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress - PURE MATH, NO LLM"""
        total = len(self.all_fields)
        answered = len([f for f in self.gathered_info.keys() if f in self.all_fields])
        cannot = len(self.cannot_answer)
        attempted = answered + cannot
        
        return {
            'total': total,
            'answered': answered,
            'cannot_answer': cannot,
            'attempted': attempted,
            'remaining': total - attempted,
            'is_complete': attempted >= total  # ✅ DETERMINISTIC COMPLETION
        }
    
    def get_remaining_questions(self) -> List[str]:
        """Get list of questions still to ask"""
        remaining = []
        for issue in self.all_issues:
            field = issue['field']
            if field not in self.gathered_info and field not in self.cannot_answer:
                remaining.append(field)
        return remaining


# ===== RESPONSE ANALYSIS =====

def analyze_user_response(user_message: str) -> Dict[str, Any]:
    """
    Simple pattern matching to detect:
    - "Don't know" responses
    - Numerical data
    - Specific answers
    """
    message_lower = user_message.lower().strip()
    
    # Detect "don't know" patterns
    dont_know_patterns = [
        r"\bdon'?t know\b",
        r"\bnot sure\b",
        r"\bno idea\b",
        r"\bcan'?t say\b",
        r"\bdon'?t have\b",
        r"\bhavent\b",
        r"\bhaven'?t\b",
        r"\bunclear\b",
        r"\bno clue\b"
    ]
    
    is_dont_know = any(re.search(pattern, message_lower) for pattern in dont_know_patterns)
    
    # Detect if response has substance (numbers, facts)
    has_numbers = bool(re.search(r'\d+', user_message))
    has_substance = len(user_message.split()) > 3  # More than 3 words
    
    # Extract numbers if present
    numbers = re.findall(r'\d+[,.]?\d*', user_message)
    
    return {
        'is_dont_know': is_dont_know,
        'has_substance': has_substance,
        'has_numbers': has_numbers,
        'numbers': numbers,
        'word_count': len(user_message.split())
    }


async def validate_answer_relevance(
    user_message: str,
    question: str,
    field_name: str
) -> Dict[str, Any]:
    """
    Validate if user's answer is actually relevant to the question asked
    Catches random/irrelevant/joke answers
    """
    
    prompt = f"""
You are validating if a founder's answer is relevant to the question asked.

QUESTION ASKED: "{question}"
FIELD: {field_name}
FOUNDER'S ANSWER: "{user_message}"

Determine if the answer is:
1. ON-TOPIC and relevant to the question
2. OFF-TOPIC, random, joke, or irrelevant

Return JSON:
{{
    "is_relevant": true/false,
    "reason": "brief explanation",
    "is_joke": true/false,
    "is_offtopic": true/false
}}

Examples:
Q: "What is your monthly revenue?"
A: "Around $50k per month" → {{"is_relevant": true, "reason": "Direct answer with numbers", "is_joke": false, "is_offtopic": false}}

Q: "What is your monthly revenue?"  
A: "The sky is blue and cats are cool" → {{"is_relevant": false, "reason": "Completely unrelated", "is_joke": false, "is_offtopic": true}}

Q: "How many employees do you have?"
A: "lol idk probably like a million" → {{"is_relevant": false, "reason": "Joke/sarcastic answer", "is_joke": true, "is_offtopic": false}}

Q: "What is your customer acquisition cost?"
A: "I'm hungry, let's talk about pizza" → {{"is_relevant": false, "reason": "Off-topic, avoiding question", "is_joke": false, "is_offtopic": true}}

Be strict. Mark as irrelevant if:
- Joke/sarcastic
- Random unrelated response
- Deliberately avoiding the question
- Nonsense/gibberish
"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                max_output_tokens=5000
            )
        )
        
        if response and hasattr(response, 'text') and response.text:
            result = json.loads(response.text.strip())
            return result
    except Exception as e:
        print(f"❌ Validation error: {e}")
    
    # Default to relevant if validation fails (benefit of doubt)
    return {
        "is_relevant": True,
        "reason": "validation_failed",
        "is_joke": False,
        "is_offtopic": False
    }


async def extract_info_from_response(
    user_message: str,
    current_field: str,
    question: str
) -> Optional[Dict[str, Any]]:
    """
    Use LLM to extract specific info from user response
    Only called if response seems to have substance
    """
    
    prompt = f"""
You are analyzing a founder's response to extract specific information.

QUESTION ASKED: "{question}"
FIELD NAME: {current_field}
FOUNDER'S ANSWER: "{user_message}"

Extract ONLY if the answer contains specific, concrete information.

Return JSON:
{{
    "has_answer": true/false,
    "value": "extracted specific value or null",
    "confidence": "high/medium/low"
}}

Rules:
- has_answer = true ONLY if specific data provided (numbers, names, facts)
- has_answer = false if vague, uncertain, or no clear answer
- value = null if has_answer is false
- confidence high = very specific answer
- confidence medium = somewhat specific
- confidence low = vague but something mentioned

Examples:
"We have 5 engineers" → {{"has_answer": true, "value": "5 engineers", "confidence": "high"}}
"Maybe around 10-15 people" → {{"has_answer": true, "value": "10-15 people", "confidence": "medium"}}
"We're still figuring it out" → {{"has_answer": false, "value": null, "confidence": "low"}}
"I don't know" → {{"has_answer": false, "value": null, "confidence": "low"}}
"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                max_output_tokens=5000
            )
        )
        
        if response and hasattr(response, 'text') and response.text:
            result = json.loads(response.text.strip())
            return result
    except Exception as e:
        print(f"❌ Extraction error: {e}")
    
    return None


# ===== CONVERSATIONAL AI =====

async def generate_conversational_response(
    state: InterviewState,
    user_message: str,
    next_question: Optional[Dict[str, Any]],
    is_closing: bool,
    company_name: str,
    founder_name: str,
    chat_history: List[Dict[str, str]],
    was_irrelevant: bool = False
) -> str:
    """
    Generate natural conversational response
    """
    
    progress = state.get_progress()
    
    if is_closing:
        # Closing message
        prompt = f"""
You are Sarah, a friendly investment analyst. You just finished interviewing {founder_name} about {company_name}.

We've covered all {progress['total']} topics. Write a warm closing message (60-80 words) that:
1. Thanks them for their time
2. Mentions you'll update the investment memo
3. Says you'll get back within 2-3 weeks
4. Encourages them about their company

Founder's last message: "{user_message}"

Be warm, professional, genuine. DO NOT ask any more questions.

Closing message:
"""
    else:
        # Normal conversation with next question
        next_q_text = next_question['question'] if next_question else "Tell me more?"
        category = next_question.get('category', 'General') if next_question else 'General'
        ask_count = next_question.get('ask_count', 0) if next_question else 0
        
        recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
        conversation_context = "\n".join([
            f"{'Analyst' if m['role'] == 'assistant' else 'Founder'}: {m['message']}"
            for m in recent_history
        ])
        
        # Add context if this is a re-ask
        reask_context = ""
        if was_irrelevant:
            reask_context = "\nNOTE: Their previous answer was off-topic/irrelevant. Gently redirect them back to the question."
        elif ask_count > 0:
            reask_context = f"\nNOTE: This is attempt #{ask_count + 1} for this question. Be patient but direct."
        
        prompt = f"""
You are Sarah, a friendly investment analyst having a natural conversation with {founder_name} about {company_name}.

PROGRESS: {progress['answered']} answered, {progress['remaining']} remaining
FOUNDER'S LATEST: "{user_message}"
NEXT QUESTION TO ASK: "{next_q_text}"
CATEGORY: {category}{reask_context}

RECENT CONVERSATION:
{conversation_context}

YOUR TASK:
1. Briefly acknowledge their answer (1 sentence, be natural)
2. Smoothly transition to the next question
3. Ask: "{next_q_text}"

RULES:
1. Be warm, conversational, human-like
2. Acknowledge their answer briefly (1 sentence, be natural)
3. THEN ASK THE NEXT QUESTION (required!)
4. If they said "don't know", acknowledge kindly and move on
5. If their answer was off-topic or irrelevant:
   - Gently redirect: "That's interesting, but let me ask about [topic]..."
   - Don't be rude, stay friendly
6. One question at a time, 40-80 words total
7. Make it feel like coffee chat, not interrogation
8. MUST end with asking the next question

Response (acknowledgment + next question):
"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=5000
            )
        )
        
        if response and hasattr(response, 'text') and response.text:
            ai_message = response.text.strip()
            
            # Ensure question mark if not closing
            if not is_closing and not ai_message.endswith('?'):
                ai_message += '?'
            
            return ai_message
    except Exception as e:
        print(f"❌ Conversation error: {e}")
    
    # Fallback
    if is_closing:
        return f"Thank you so much for your time, {founder_name}! I'll update our investment memo and get back to you within 2-3 weeks. Best of luck with {company_name}!"
    else:
        next_q = next_question['question'] if next_question else "What else can you tell me?"
        return f"Thanks for sharing! {next_q}"


# ===== MAIN CHAT FUNCTION =====

async def chat_with_founder(
    interview_data: Dict[str, Any],
    user_message: str,
    chat_history: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Main interview chat function - RELIABLE & PREDICTABLE
    
    Features:
    - Never repeats questions
    - Deterministic completion (pure math)
    - Validates answer relevance
    - Re-asks up to 2 times for irrelevant answers
    - No LLM control over completion
    """
    
    # Initialize state
    state = InterviewState(interview_data)
    
    company_name = interview_data.get('company_name', 'your startup')
    founder_name = interview_data.get('founder_name', 'Founder')
    
    # Get progress
    progress = state.get_progress()
    
    print(f"\n{'='*60}")
    print(f"📊 INTERVIEW STATE")
    print(f"{'='*60}")
    print(f"Total questions: {progress['total']}")
    print(f"Answered: {progress['answered']}")
    print(f"Cannot answer: {progress['cannot_answer']}")
    print(f"Attempted: {progress['attempted']}/{progress['total']}")
    print(f"Remaining: {progress['remaining']}")
    print(f"Complete: {progress['is_complete']}")
    
    # If complete, send closing message
    if progress['is_complete']:
        print("✅ Interview complete - sending closing message")
        
        closing_message = await generate_conversational_response(
            state=state,
            user_message=user_message,
            next_question=None,
            is_closing=True,
            company_name=company_name,
            founder_name=founder_name,
            chat_history=chat_history
        )
        
        return {
            "message": closing_message,
            "is_complete": True,
            "progress": progress,
            "gathered_info": state.gathered_info,
            "cannot_answer_fields": list(state.cannot_answer),
            "asked_questions": list(state.asked_questions),
            "ask_count": state.ask_count
        }
    
    # Analyze user's latest response
    response_analysis = analyze_user_response(user_message)
    
    print(f"\n📝 USER RESPONSE ANALYSIS")
    print(f"Don't know: {response_analysis['is_dont_know']}")
    print(f"Has substance: {response_analysis['has_substance']}")
    print(f"Has numbers: {response_analysis['has_numbers']}")
    
    # Get the LAST question we asked (from chat history)
    last_assistant_message = None
    for msg in reversed(chat_history):
        if msg['role'] == 'assistant':
            last_assistant_message = msg['message']
            break
    
    # Try to find which field we were asking about
    current_field = None
    for issue in state.all_issues:
        # Simple heuristic: if question text is in last assistant message
        if last_assistant_message and issue['question'].lower() in last_assistant_message.lower():
            current_field = issue['field']
            break
    
    # Track if answer was irrelevant (for conversational response)
    was_irrelevant = False
    
    # Process response
    if current_field:
        print(f"🎯 Processing answer for: {current_field}")
        
        if response_analysis['is_dont_know']:
            # Mark as cannot answer
            state.mark_cannot_answer(current_field)
            print(f"   → Marked as 'cannot answer'")
        
        elif response_analysis['has_substance']:
            # Validate if answer is relevant
            validation = await validate_answer_relevance(
                user_message=user_message,
                question=last_assistant_message or "",
                field_name=current_field
            )
            
            print(f"   🔍 Relevance check:")
            print(f"      - Relevant: {validation['is_relevant']}")
            print(f"      - Reason: {validation.get('reason', 'N/A')}")
            print(f"      - Is joke: {validation.get('is_joke', False)}")
            print(f"      - Off-topic: {validation.get('is_offtopic', False)}")
            
            if not validation['is_relevant']:
                # Answer is irrelevant/joke/off-topic
                was_irrelevant = True
                ask_count = state.get_ask_count(current_field)
                print(f"   ⚠️ Irrelevant answer (asked {ask_count} times)")
                
                # Mark as asked to increment count
                state.mark_question_asked(current_field)
                
                # If asked twice already, mark as cannot answer
                if ask_count >= 1:  # This was the 2nd attempt
                    state.mark_cannot_answer(current_field)
                    print(f"   → Asked twice, marking as 'cannot answer'")
                
            else:
                # Answer is relevant - try to extract info
                extracted = await extract_info_from_response(
                    user_message=user_message,
                    current_field=current_field,
                    question=last_assistant_message or ""
                )
                
                if extracted and extracted.get('has_answer'):
                    state.add_answer(
                        field=current_field,
                        value=extracted.get('value'),
                        confidence=extracted.get('confidence', 'medium')
                    )
                    print(f"   ✅ Extracted: {extracted.get('value')} (confidence: {extracted.get('confidence')})")
                else:
                    # Relevant but vague answer - mark as cannot answer
                    state.mark_cannot_answer(current_field)
                    print(f"   → Too vague, marked as 'cannot answer'")
        
        else:
            # Very short answer with no substance
            print(f"   → Too short, no substance")
            state.mark_question_asked(current_field)
    
    # Get next question to ask
    next_question = state.get_next_question()
    
    if next_question:
        print(f"\n🔜 NEXT QUESTION: {next_question['field']}")
        print(f"   → {next_question['question']}")
        print(f"   → Ask count: {next_question.get('ask_count', 0)}")
        
        # Mark as asked
        if not was_irrelevant:  # Don't double-increment if already marked
            state.mark_question_asked(next_question['field'])
    else:
        print(f"\n✅ No more questions to ask")
    
    # Check if we're done now
    progress = state.get_progress()
    is_closing = progress['is_complete']
    
    print(f"\n📊 UPDATED PROGRESS:")
    print(f"   Attempted: {progress['attempted']}/{progress['total']}")
    print(f"   Closing: {is_closing}")
    
    # Generate response
    ai_message = await generate_conversational_response(
        state=state,
        user_message=user_message,
        next_question=next_question,
        is_closing=is_closing,
        company_name=company_name,
        founder_name=founder_name,
        chat_history=chat_history,
        was_irrelevant=was_irrelevant
    )
    
    print(f"\n💬 AI RESPONSE: {ai_message[:100]}...")
    print(f"{'='*60}\n")
    
    return {
        "message": ai_message,
        "is_complete": is_closing,
        "progress": progress,
        "gathered_info": state.gathered_info,
        "cannot_answer_fields": list(state.cannot_answer),
        "asked_questions": list(state.asked_questions),
        "ask_count": state.ask_count
    }
