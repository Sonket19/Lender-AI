import json
import base64
import re
from typing import Dict, Any, Optional, Union, List
from fastapi import HTTPException
from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch, Part
from config.settings import settings

# Initialize Google Gen AI client with API Key
client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)

# Model priority list (will try in order if one fails)
MODELS_PRO = ["gemini-3-pro-preview", "gemini-2.5-pro"]  # Try 3-pro first, fallback to 2.5-pro
MODELS_FLASH = ["gemini-2.5-flash", "gemini-2.0-flash"]

async def generate_with_fallback(
    contents,
    config: GenerateContentConfig,
    models: List[str] = None,
    use_flash: bool = False
) -> Any:
    """
    Generate content with automatic model fallback.
    If the primary model returns 503/overloaded, tries the next model in the list.
    """
    if models is None:
        models = MODELS_FLASH if use_flash else MODELS_PRO
    
    last_error = None
    for model_name in models:
        try:
            print(f"🤖 Trying model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            print(f"✅ Success with model: {model_name}")
            
            # Additional check: If response.text is None (e.g. Safety Filters), treat as failure
            if not response.text:
                print(f"⚠️ Model {model_name} returned empty text (Use Fallback)")
                if hasattr(response, 'candidates') and response.candidates:
                     print(f"Details: {response.candidates[0].finish_reason}")
                raise ValueError("Empty response from model")

            return response
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Model {model_name} failed: {error_msg[:100]}")
            last_error = e
            # Continue to next model if 503/overloaded OR if empty response
            if "503" in error_msg or "overloaded" in error_msg.lower() or "UNAVAILABLE" in error_msg or "Empty response" in error_msg:
                continue
            else:
                # For other errors, don't try fallback
                raise e
    
    # All models failed
    raise last_error

async def analyze_with_gemini(
    pdf_bytes: Optional[bytes] = None,
    extracted_text: Optional[str] = None,
    cma_text: Optional[str] = None,
    weightage: Dict[str, int] = None,
    processing_mode: str = "fast"
) -> Dict[str, Any]:
    """
    Analyze pitch deck content using Gemini with Google Search grounding.
    Can accept either PDF bytes (preferred) or extracted text.
    processing_mode: 'fast' uses gemini-2.5-flash, 'research' uses gemini-3-pro-preview
    """
    if weightage is None:
        weightage = {
            'team_strength': 20,
            'market_opportunity': 20,
            'traction': 20,
            'claim_credibility': 20,
            'financial_health': 20
        }
    try:
        # Build CMA section if available
        cma_section = ""
        if cma_text:
            cma_section = f"""

CMA REPORT DATA (Credit Monitoring Arrangement - Financial Statements):
{cma_text[:40000]}
"""

        # 4-Gate Digital Underwriting Framework Prompt
        prompt = f"""
You are an expert Bank Credit Officer working for a modern Indian NBFC/Bank. Your job is to analyze loan applications from startups and MSMEs using the "4-Gate Credit Algorithm" framework.

Analyze the attached Pitch Deck and the following CMA Report data to determine whether this business should be sanctioned the requested loan.

{cma_section}

=== THE 4-GATE CREDIT ALGORITHM ===

GATE 1: POLICY & MARKET "KNOCK-OUT"
Goal: Filter out "Non-Starters" based on qualitative risk.

1. NEGATIVE LIST CHECK (Compliance)
   - RBI and internal bank policies strictly ban certain sectors.
   - REJECT IF business involves: Gambling, Cryptocurrency, Multi-Level Marketing (MLM), Real Estate Speculation, Chit Fund, Arms/Ammunition, or any illegal activity.

2. SECTOR VIABILITY SCAN (The "Sunset" Filter)
   - Classify the industry:
     * GREEN (Sunrise): Green Energy, SaaS/AI, Healthcare, EV Components, Fintech
     * AMBER (Stable): FMCG, Textiles, Logistics, Manufacturing, E-commerce
     * RED (Sunset/Risky): Print Media, Coal-based tech, Single-use Plastic
   - If RED, flag as "High-Risk Alert" requiring special review.

3. MARKET SIZING REALITY CHECK
   - Prevents "Delusional Projections"
   - If a Seed-Stage startup claims >1% of a massive market in Year 1, flag as "Unrealistic Projections"

---

GATE 2: DATA INTEGRITY AUDIT (The "BS Detector")
Goal: Catch manipulated numbers in the CMA before doing financial math.

4. ACCOUNTING EQUATION CHECK
   - Total Assets must equal (Total Liabilities + Net Worth)
   - If it doesn't balance, flag as "Data Error"

5. HOCKEY STICK FORENSIC CHECK
   - Revenue cannot grow exponentially without capital expenditure or marketing spend.
   - RED FLAG IF:
     * Revenue Growth > 100% YoY
     * AND Fixed Asset Growth < 10%
     * AND Employee Cost Growth < 10%
   - Flag as "Artificial Inflation"

6. UNIT ECONOMICS AUDIT
   - Startups often inflate future margins to make loan look repayable.
   - RED FLAG IF:
     * Projected EBITDA Margin > Current EBITDA Margin + 5%
     * AND COGS is constant or declining
   - Flag as "Unjustified Margin Improvement"

---

GATE 3: FINANCIAL ASSESSMENT (The "Calculator")
Goal: Calculate actual Loan Eligibility using RBI-approved methods.

7. MAXIMUM PERMISSIBLE BANK FINANCE (MPBF) - Turnover Method
   - For limits up to ₹5 Crore (Nayak Committee norms):
     * Gross Working Capital (GWC) = 25% of Projected Annual Turnover
     * Promoter's Contribution (Margin) = 5% of Projected Annual Turnover
     * Loan Eligibility = Projected Turnover × 0.20 (20%)
   - If Actual Drawing Power (Stock + Debtors - Creditors) is lower, restrict limit accordingly.

8. REPAYMENT CAPACITY (DSCR)
   - Formula: (Net Profit + Depreciation + Interest) / (Interest + Principal Repayment)
   - Thresholds:
     * > 1.5: Excellent (Low Risk)
     * 1.2 - 1.5: Acceptable for Startups (Medium Risk)
     * < 1.2: REJECT (Cash flow insufficient)

9. FINANCIAL HEALTH RATIOS (Vital Signs)
   - Current Ratio: Must be > 1.33 (Indicates liquidity)
   - TOL/TNW Ratio (Leverage): Must be < 3:1 (For startups, < 4:1 may be allowed)
   - Debtor Days: Must match industry (30-90 days). If >180 days, flag as "Bad Debts Risk"

---

GATE 4: FINAL VERDICT & STARTUP SPECIFICS
Goal: Synthesize a decision.

10. RUNWAY TEST (Critical for Loss-Making Startups)
    - If startup is currently burning cash, will this loan save them or just delay death?
    - Formula: (Cash on Hand + Loan Amount) / Monthly Cash Burn
    - Threshold: Must be > 12 Months. If less, default risk is near 100%.

11. GUARANTEE SCHEME ELIGIBILITY (CGTMSE)
    - If startup has no collateral, check Government Guarantee eligibility:
      * Is Loan < ₹5 Crore? 
      * Is Industry "Manufacturing" or "Service"?
    - If YES to both, tag as "CGTMSE Eligible" (Reduces Bank's Risk)

---

=== OUTPUT FORMAT (STRICT JSON) ===

Return your analysis in the following JSON structure:

{{
    "company_overview": {{
        "name": "Company name from pitch deck",
        "sector": "Industry/Sector",
        "founders": [
            {{
                "name": "Founder name",
                "education": "Educational background with institution names",
                "professional_background": "Detailed work experience with companies and roles",
                "previous_ventures": "Prior entrepreneurial experience with outcomes"
            }}
        ],
        "technologies_used": "Detailed description of core technologies, frameworks, and technical stack",
        "key_problems_solved": ["Problem 1", "Problem 2", "Problem 3"],
        "loan_amount_requested": "Amount requested in the pitch deck (e.g., ₹50 Lakhs)",
        "purpose_of_loan": "What the loan will be used for"
    }},
    "market_analysis": {{
        "industry_size_and_growth": {{
            "total_addressable_market": {{
                "name": "TAM description",
                "value": "market size with units (use Google Search for current data)",
                "cagr": "growth rate from recent reports",
                "source": "cite source with year"
            }},
            "serviceable_obtainable_market": {{
                "name": "SOM description",
                "value": "realistic market size for this company",
                "projection": "future projections for next 3-5 years",
                "cagr": "projected growth rate",
                "source": "cite source with year"
            }},
            "commentary": "detailed market insights and trends"
        }},
        "sub_segment_opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"],
        "competitor_details": [
            {{
                "name": "competitor name (search for real competitors)",
                "headquarters": "HQ location",
                "founding_year": "year founded",
                "total_funding_raised": "total funding amount",
                "funding_rounds": "number of rounds and details",
                "investors": "list of key investors",
                "business_model": "how they make money",
                "revenue_streams": "primary revenue sources",
                "target_market": "their target customers",
                "gross_margin": "gross margin % if available",
                "net_margin": "net margin % if available",
                "operating_expense": "OpEx details if available",
                "current_arr": "ARR if publicly known",
                "current_mrr": "MRR if publicly known",
                "arr_growth_rate": "growth rate if available",
                "churn_rate": "customer churn rate if available"
            }}
        ],
        "reports": [
            {{
                "title": "relevant industry report title (search Google)",
                "source_name": "report publisher name",
                "source_url": "URL to report",
                "summary": "2-3 sentence summary of key findings"
            }}
        ]
    }},
    "credit_analysis": {{
        "gates": [
            {{
                "gate_number": 1,
                "gate_name": "Policy & Market Knock-Out",
                "status": "Pass/Fail/Review",
                "checks": [
                    {{
                        "name": "Negative List Check",
                        "status": "Pass/Fail",
                        "result": "Industry/Sector name",
                        "details": "Explanation",
                        "flags": []
                    }},
                    {{
                        "name": "Sector Viability",
                        "status": "Pass/Fail/Review",
                        "result": "Green/Amber/Red (Sector Type)",
                        "details": "Explanation",
                        "flags": []
                    }},
                    {{
                        "name": "Market Sizing Reality",
                        "status": "Pass/Fail",
                        "result": "Projected market share %",
                        "details": "Assessment of projections",
                        "flags": []
                    }}
                ]
            }},
            {{
                "gate_number": 2,
                "gate_name": "Data Integrity Audit",
                "status": "Pass/Fail/Review",
                "checks": [
                    {{
                        "name": "Accounting Equation",
                        "status": "Pass/Fail",
                        "result": "Balance check result",
                        "details": "Verification details",
                        "flags": []
                    }},
                    {{
                        "name": "Hockey Stick Check",
                        "status": "Pass/Fail",
                        "result": "Revenue vs Capex growth comparison",
                        "details": "Analysis",
                        "flags": []
                    }},
                    {{
                        "name": "Unit Economics Audit",
                        "status": "Pass/Fail",
                        "result": "Margin projection analysis",
                        "details": "EBITDA margin trends",
                        "flags": []
                    }}
                ]
            }},
            {{
                "gate_number": 3,
                "gate_name": "Financial Assessment",
                "status": "Pass/Fail/Review",
                "checks": [
                    {{
                        "name": "MPBF Calculation",
                        "status": "Pass/Fail",
                        "result": "Calculated limit (e.g., ₹40 Lakhs)",
                        "details": "Turnover method calculation",
                        "flags": []
                    }},
                    {{
                        "name": "DSCR",
                        "status": "Pass/Fail",
                        "result": "DSCR value (e.g., 1.45)",
                        "details": "Repayment capacity analysis",
                        "flags": []
                    }},
                    {{
                        "name": "Current Ratio",
                        "status": "Pass/Fail",
                        "result": "Ratio value",
                        "details": "Liquidity assessment",
                        "flags": []
                    }},
                    {{
                        "name": "TOL/TNW Ratio",
                        "status": "Pass/Fail",
                        "result": "Leverage ratio",
                        "details": "Debt capacity assessment",
                        "flags": []
                    }}
                ]
            }},
            {{
                "gate_number": 4,
                "gate_name": "Final Verdict & Specifics",
                "status": "Pass/Fail/Review",
                "checks": [
                    {{
                        "name": "Runway Test",
                        "status": "Pass/Fail",
                        "result": "X months runway",
                        "details": "Cash burn analysis",
                        "flags": []
                    }},
                    {{
                        "name": "CGTMSE Eligibility",
                        "status": "Pass/Fail",
                        "result": "Eligible/Not Eligible",
                        "details": "Government guarantee assessment",
                        "flags": []
                    }}
                ]
            }}
        ],
        
        "loan_amount_requested": "₹X Lakhs",
        "max_permissible_limit": "₹X Lakhs (calculated MPBF)",
        "dscr": "X.XX",
        "current_ratio": "X.XX",
        "tol_tnw_ratio": "X.X:1",
        "runway_months": "X months",
        
        "recommendation": "SANCTION/REJECT/CONDITIONAL",
        "sanction_amount": "₹X Lakhs (if approved)",
        "conditions": ["Condition 1", "Condition 2"],
        "rejection_reasons": ["Reason 1 (if rejected)"],
        "cgtmse_eligible": true/false,
        
        "summary_table": [
            {{"parameter": "Industry Risk", "result": "SaaS / Technology (Sunrise)", "status": "🟢 Low"}},
            {{"parameter": "Data Integrity", "result": "Growth aligns with Capex", "status": "🟢 Verified"}},
            {{"parameter": "MPBF Limit", "result": "₹40 Lakhs (vs Request ₹50L)", "status": "🟡 Restricted"}},
            {{"parameter": "DSCR", "result": "1.45 (Acceptable)", "status": "🟢 Pass"}},
            {{"parameter": "Collateral", "result": "None (CGTMSE Cover)", "status": "🟢 Secured"}}
        ],
        
        "final_verdict": "Detailed recommendation statement (e.g., 'Sanction up to some Lakhs under CGTMSE scheme. Subject to Promoter Margin of 5% being deposited upfront.')"
    }},
    
    "market_analysis": {{
        "industry_size_and_growth": {{
            "total_addressable_market": {{
                "name": "TAM description",
                "value": "Market size with units (use Google Search for current data)",
                "cagr": "Growth rate from recent reports",
                "source": "Cite source with year"
            }},
            "serviceable_obtainable_market": {{
                "name": "SOM description",
                "value": "Realistic market size for this company",
                "projection": "Future projections for next 3-5 years",
                "cagr": "Projected growth rate",
                "source": "Cite source with year"
            }},
            "commentary": "Detailed market insights and trends"
        }},
        "sub_segment_opportunities": ["Opportunity 1", "Opportunity 2", "Opportunity 3"],
        "competitor_details": [
            {{
                "name": "Competitor name (search for real competitors)",
                "headquarters": "HQ location",
                "founding_year": "Year founded",
                "total_funding_raised": "Total funding amount",
                "funding_rounds": "Number of rounds and details",
                "investors": "List of key investors",
                "business_model": "How they make money",
                "revenue_streams": "Primary revenue sources",
                "target_market": "Their target customers",
                "gross_margin": "Gross margin % if available",
                "net_margin": "Net margin % if available",
                "current_arr": "ARR if publicly known",
                "current_mrr": "MRR if publicly known"
            }}
        ],
        "reports": [
            {{
                "title": "Relevant industry report title (search Google)",
                "source_name": "Report publisher name",
                "source_url": "URL to report",
                "summary": "2-3 sentence summary of key findings"
            }}
        ]
    }},
    
    "financials": {{
        "arr_mrr": {{
            "current_booked_arr": "Annual Recurring Revenue",
            "current_mrr": "Monthly Recurring Revenue"
        }},
        "burn_and_runway": {{
            "implied_net_burn": "Monthly burn rate",
            "stated_runway": "Current runway without loan",
            "funding_ask": "Loan amount requested",
            "gross_margin": "Gross margin %",
            "cm1": "Contribution Margin 1",
            "cm2": "Contribution Margin 2",
            "cm3": "Contribution Margin 3"
        }},
        "funding_history": "Previous funding/loans",
        "valuation_rationale": "Current valuation basis",
        "projections": [
            {{"year": "FY25", "revenue": "Projected revenue"}}
        ]
    }},
    
    "conclusion": {{
        "overall_recommendation": "SANCTION/REJECT/CONDITIONAL - Clear verdict",
        "product_summary": "One sentence product summary",
        "financial_analysis": "Brief financial pros & cons",
        "credit_thesis": "Why sanction or reject - the core argument from a lender's perspective",
        "key_risks": "Summary of main credit risks identified"
    }}
}}

CRITICAL INSTRUCTIONS:
1. Use Google Search to find real market data and competitor information
2. All financial calculations MUST be based on CMA data provided
3. DSCR, Current Ratio, and TOL/TNW MUST be calculated from actual numbers
4. If CMA data is missing critical fields, flag as "Incomplete Data"
5. Be CONSERVATIVE - banks prefer to reject a good loan than approve a bad one
6. Return ONLY valid JSON, no additional text or markdown
7. For market_analysis data, USE GOOGLE SEARCH to find current, accurate information
8. Search for real competitors and get their actual funding, metrics, and business details
9. Find recent industry reports from credible sources (Gartner, McKinsey, CB Insights, etc.)
10. For reports, provide title, source name, URL, and key findings
11. If information is not available in pitch deck OR via search, use exactly "Not available" (not N/A, Unknown, etc.)
12. Ensure all numeric values include units (e.g., "$5M", "25%", "18 months")
13. Include at least 3-5 real competitors with as much detail as possible
14. Include at least 2-3 recent industry reports
15. Analyze at least 3-5 major claims from the pitch deck
16. Include all 5 risk categories with detailed mitigation strategies
17. Return ONLY valid JSON, no additional text or markdown
"""
        
        # Select model based on processing mode
        model_name = "gemini-2.5-flash" if processing_mode == "fast" else "gemini-3-pro-preview"
        
        # Build content parts based on input type
        if pdf_bytes:
            # Send PDF directly to Gemini (multimodal)
            print(f"📄 Sending PDF directly to Gemini ({len(pdf_bytes)} bytes)")
            contents = [
                Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                prompt
            ]
        elif extracted_text:
            # Fallback to text-based analysis
            print(f"📝 Using extracted text for analysis ({len(extracted_text)} chars)")
            contents = f"{prompt}\n\nPitch Deck Content:\n{extracted_text[:50000]}"
        else:
            raise HTTPException(status_code=400, detail="Either pdf_bytes or extracted_text must be provided")
        
        # Use fallback helper for automatic model switching on 503 errors
        use_flash = (processing_mode == "fast")
        response = await generate_with_fallback(
            contents=contents,
            config=GenerateContentConfig(
                tools=[Tool(google_search=GoogleSearch())],
                temperature=0.2,
                top_p=0.8,
                top_k=40,
                max_output_tokens=16384
            ),
            use_flash=use_flash
        )
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Remove markdown formatting if present
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
        
        # If response doesn't start with {, try to find JSON in the response
        if not response_text.startswith("{"):
            # Look for JSON block in markdown code block
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                response_text = json_match.group(1).strip()
            else:
                # Try to find the outermost { } block
                json_match = re.search(r'(\{[\s\S]*\})', response_text)
                if json_match:
                    response_text = json_match.group(1)
                else:
                    print(f"Could not find JSON in response: {response_text[:500]}")
                    raise ValueError("No JSON found in response")
        
        # Parse JSON
        analysis = json.loads(response_text)
        
        # Validate required fields (risk fields optional for fast mode)
        required_fields = [
            'company_overview', 'market_analysis',
            'financials', 'claims_analysis', 'conclusion'
        ]
        
        if processing_mode == "research":
            required_fields.extend(['risk_metrics', 'risks_and_mitigation'])
        
        for field in required_fields:
            if field not in analysis:
                print(f"Warning: Missing required field: {field}")
                analysis[field] = {}
        
        # Add weightage metadata to the analysis
        analysis['_weightage_used'] = weightage
        
        return analysis
    
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Gemini: {str(e)}")
        print(f"Response text: {response_text[:500]}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to parse analysis response. Invalid JSON format."
        )
    except Exception as e:
        print(f"Error in Gemini analysis: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze content: {str(e)}"
        )

async def recalculate_risk_and_conclusion(
    existing_memo: Dict[str, Any], 
    extracted_text: str,
    weightage: Dict[str, int]
) -> Dict[str, Any]:
    """
    Recalculate ONLY risk_metrics and conclusion based on new weightage
    Uses both extracted text and existing memo for full context
    Keeps all other sections unchanged
    """
    try:
        # Extract key information from existing memo for context
        company_name = existing_memo.get('company_overview', {}).get('name', 'Unknown')
        sector = existing_memo.get('company_overview', {}).get('sector', 'Unknown')
        
        prompt = f"""
You are a VC analyst recalculating risk assessment with NEW weightage.

ORIGINAL PITCH DECK CONTENT (for reference):
{extracted_text[:15000]}

EXISTING ANALYSIS:
Company: {company_name} | Sector: {sector}

Team:
{json.dumps(existing_memo.get('company_overview', {}), indent=2)[:1000]}

Market:
{json.dumps(existing_memo.get('market_analysis', {}), indent=2)[:2000]}

Financials:
{json.dumps(existing_memo.get('financials', {}), indent=2)[:1000]}

Claims:
{json.dumps(existing_memo.get('claims_analysis', []), indent=2)[:1000]}

NEW WEIGHTAGE (total=100%):
- Team Strength: {weightage.get('team_strength', 20)}%
- Market Opportunity: {weightage.get('market_opportunity', 20)}%
- Traction: {weightage.get('traction', 20)}%
- Claim Credibility: {weightage.get('claim_credibility', 20)}%
- Financial Health: {weightage.get('financial_health', 20)}%

TASK: Recalculate risk_metrics and conclusion using NEW weightage.

CALCULATION METHOD:
1. Review ORIGINAL pitch deck + EXISTING analysis
2. Score each factor 0-100 (higher = riskier):
   - Team: founder experience, completeness
   - Market: TAM size, growth, competition
   - Traction: ARR/MRR, growth rate, customers
   - Claims: evidence vs claims ratio
   - Financials: burn rate, runway, margins
3. Apply formula: Composite = (Team×{weightage.get('team_strength')}/100) + (Market×{weightage.get('market_opportunity')}/100) + (Traction×{weightage.get('traction')}/100) + (Claims×{weightage.get('claim_credibility')}/100) + (Financials×{weightage.get('financial_health')}/100)

Return ONLY this JSON (complete all fields):

{{
    "risk_metrics": {{
        "composite_risk_score": 0,
        "score_interpretation": "Low (0-40), Medium (41-70), High (71-100)",
        "narrative_justification": "Explain calculation: Team risk X × {weightage.get('team_strength')}%, Market risk Y × {weightage.get('market_opportunity')}%, etc. Show how new weights changed the score."
    }},
    "conclusion": {{
        "overall_attractiveness": "Start with INVEST/PASS/CONDITIONAL.",
        "product_summary": "One sentence summary of the product.",
        "financial_analysis": "Brief summary of financial pros & cons.",
        "investment_thesis": "Why invest? (or why not?). The core argument.",
        "risk_summary": "Reference the composite risk score and the main risk factor."
    }}
}}

CRITICAL: Return ONLY valid complete JSON. No markdown.
"""
        
        response = client.models.generate_content(
            # model='gemini-3-pro-preview',
            model='gemini-3-pro-preview',
            contents=prompt,
            config=GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
                response_mime_type="application/json",
            )
        )
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Remove markdown formatting if present
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
        
        # Parse JSON
        recalculated = json.loads(response_text)
        
        # Validate required fields
        if 'risk_metrics' not in recalculated:
            raise ValueError("Missing risk_metrics in response")
        if 'conclusion' not in recalculated:
            raise ValueError("Missing conclusion in response")
        
        # Validate nested fields
        if 'composite_risk_score' not in recalculated['risk_metrics']:
            raise ValueError("Missing composite_risk_score")
        if 'overall_attractiveness' not in recalculated['conclusion']:
            raise ValueError("Missing overall_attractiveness")
        
        return recalculated
    
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Gemini: {str(e)}")
        print(f"Full response text:\n{response_text}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to parse recalculation response. Response was truncated or invalid."
        )
    except Exception as e:
        print(f"Error recalculating risk and conclusion: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to recalculate: {str(e)}"
        )

async def chat_with_ai(memo: Dict[str, Any], company_name: str, sector: str, chat_history: list, user_message: str) -> str:
    """Handle AI chat for founder interview"""
    try:
        context = f"""
        You are an AI investment analyst conducting an interview with a startup founder.
        
        Company: {company_name}
        Sector: {sector}
        
        Current Investment Memo Summary:
        {json.dumps(memo, indent=2)[:5000]}
        
        Your goal is to gather missing or unclear information to complete the investment analysis.
        Focus on:
        1. Missing financial data (ARR, MRR, burn rate, margins)
        2. Unclear market assumptions
        3. Team background gaps
        4. Unsubstantiated claims
        5. Customer traction details
        6. Technology and IP details
        7. Competitive advantages
        
        Be professional, concise, and focused. Ask one question at a time.
        
        Chat History:
        {json.dumps(chat_history[-10:], indent=2)}
        
        Founder's latest message: {user_message}
        
        Respond naturally and ask relevant follow-up questions.
        """
        
        response = client.models.generate_content(
            # model='gemini-3-pro-preview',
            model='gemini-3-pro-preview',
            contents=context
        )
        
        return response.text
    
    except Exception as e:
        print(f"Error in AI chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate AI response: {str(e)}")

async def generate_investor_chat_response(
    extracted_text: str,
    memo_context: Dict[str, Any],
    chat_history: list,
    user_message: str
) -> str:
    """
    Generate a response for the investor chatbot using Gemini 2.5 Pro.
    Uses the pitch deck text and generated memo as context.
    Enabled with Google Search for external validation.
    """
    try:
        # Format chat history for context
        formatted_history = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}" 
            for msg in chat_history[-5:] # Keep last 5 turns for context window efficiency
        ])
        
        prompt = f"""
        You are an expert Venture Capital Analyst Assistant. Your job is to answer questions about a specific startup based on its pitch deck and the investment memo we have generated.
        
        CONTEXT:
        
        1. INVESTMENT MEMO SUMMARY:
        {json.dumps(memo_context, indent=2)[:5000]}
        
        2. RAW PITCH DECK CONTENT (Excerpt):
        {extracted_text[:10000]}
        
        3. CHAT HISTORY:
        {formatted_history}
        
        USER QUESTION: {user_message}
        
        INSTRUCTIONS:
        - Answer the user's question directly and professionally.
        - Base your answer PRIMARILY on the provided Pitch Deck Content and Investment Memo.
        - Use Google Search to verify claims or provide external market context if the user asks about market size, competitors, or industry trends that are not fully covered in the deck.
        - If the information is not in the deck or memo, and cannot be found via search, admit that you don't have that information.
        - Be concise but thorough.
        - Do not hallucinate facts about the startup.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=GenerateContentConfig(
                tools=[Tool(google_search=GoogleSearch())],
                temperature=0.3,
                max_output_tokens=5000
            )
        )
        
        return response.text
        
    except Exception as e:
        print(f"Error in investor chat generation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate chat response: {str(e)}"
        )

async def verify_claims_with_google(extracted_text: Optional[str] = None, pdf_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    """
    Extract key claims from the pitch deck and verify them using Google Search.
    Can use extracted text OR PDF bytes (multimodal).
    Returns a list of verified claims with verdicts.
    """
    try:
        # Construct the instructions
        instructions = """
        You are a world-class investigative fact-checker with access to Google Search. Your job is to verify startup claims with the rigor of a top-tier investigative journalist.
        
        STEP 1: EXTRACT CLAIMS
        Identify 5-8 specific, verifiable claims from the pitch deck. Prioritize:
        - Quantifiable metrics (revenue, users, growth rates, market size)
        - Named entities (partnerships, customers, awards, investors, team credentials)
        - Time-bound achievements (milestones, launches, certifications)
        
        STEP 2: DEEP VERIFICATION METHODOLOGY
        For EACH claim, apply this exhaustive search process:
        
        A. QUERY FORMULATION (Try 3-5 variations):
           - Direct: "exact claim text"
           - Reverse: Search for the entity mentioned (e.g., if claim is "Won X Award", search "X Award 2023 winners")
           - Contextual: Add related keywords (company name + claim + year/location)
           - Negative: Search for contradictions or corrections
        
        B. SOURCE HIERARCHY (Check in this order):
           1. Primary sources: Official websites, press releases, verified social media of entities mentioned
           2. Secondary sources: News articles, industry publications, databases (Crunchbase, PitchBook)
           3. Tertiary sources: LinkedIn posts, blog mentions, community forums
           4. Social proof: Instagram/Twitter announcements, conference speaker lists, portfolio pages
        
        C. VERIFICATION RULES:
           - If claim mentions Company A worked with Company B, check BOTH companies' websites/social media
           - For awards/programs, find the official site and look for winner lists, even if buried in PDFs or subpages
           - For financial claims, cross-reference multiple sources (funding databases, news, filings if public)
           - For team credentials, verify via LinkedIn, university alumni pages, or past employer websites
           - If something seems off, search for corrections, retractions, or alternative perspectives
        
        D. PERSISTENCE:
           - NEVER mark as "Unverifiable" after just 1-2 searches
           - If direct search fails, try lateral searches (e.g., search for the award itself, then manually look for the company)
           - Check archived versions if current pages don't exist (mention this in explanation)
           - Consider that evidence might be in images, PDFs, or video content (Google can find these)
        
        STEP 3: VERDICT ASSIGNMENT
        Based on cumulative evidence:
        - "Verified": Found concrete evidence from authoritative sources (cite the best one)
        - "Likely True": Strong circumstantial evidence but no direct confirmation (explain why you believe it)
        - "Exaggerated": Claim is technically true but misleading in context (explain the nuance)
        - "False": Direct contradiction from credible sources
        - "Unverifiable": Exhaustively searched with no evidence (LIST all places you checked)
        
        STEP 4: TRANSPARENCY
        In the explanation field, document your research trail:
        - What searches you ran
        - What sources you checked
        - Why you arrived at this verdict
        - If "Unverifiable", explicitly state: "Searched X, Y, Z but found no evidence"

        Return ONLY this JSON structure:
        {
            "claims": [
                {
                    "claim": "The exact claim from the pitch deck",
                    "verdict": "Verified/Likely True/Exaggerated/False/Unverifiable",
                    "explanation": "Detailed research trail: what you searched, what you found, why this verdict",
                    "source_url": "Best authoritative source URL, or null if none found",
                    "confidence": "High/Medium/Low"
                }
            ]
        }
        """

        contents = []
        if pdf_bytes:
            # Multimodal Input
            contents.append(Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
            contents.append(instructions)
        elif extracted_text:
            # Text Only Input
            contents.append(f"{instructions}\n\nPITCH DECK TEXT:\n{extracted_text[:30000]}")
        else:
            raise ValueError("Either pdf_bytes or extracted_text must be provided")
        
        response = await generate_with_fallback(
            contents=contents,
            config=GenerateContentConfig(
                tools=[Tool(google_search=GoogleSearch())],
                temperature=0.1
            ),
            models=MODELS_PRO,  # Uses [gemini-3-pro-preview, gemini-2.5-pro]
            use_flash=False
        )
        
        response_text = response.text.strip()
        print(f"DEBUG: Fact Check Raw Response: {response_text[:500]}...")  # Log first 500 chars

        # Improved JSON extraction using Regex
        # Matches outermost curly braces including nested ones
        match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
             print(f"⚠️ No JSON found in response. Raw text: {response_text}")
             raise ValueError("Could not find valid JSON object in response")
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {str(e)}")
        # print(f"Bad JSON Content: {response_text}") # Removed to avoid huge log
        raise HTTPException(status_code=500, detail=f"Failed to parse fact check response: {str(e)}")
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {str(e)}")
        print(f"Bad JSON Content: {response_text}")
        raise HTTPException(status_code=500, detail=f"Failed to parse fact check response: {str(e)}")
    except Exception as e:
        print(f"Error in fact check generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to verify claims: {str(e)}")


async def extract_cma_data(raw_text: str = None, pdf_bytes: bytes = None) -> Dict[str, Any]:
    """
    Extract structured CMA data from raw text (from Excel dump) OR PDF bytes directly.
    Accepts either raw_text or pdf_bytes - if pdf_bytes provided, sends directly to Gemini.
    Returns a dictionary matching the CMAData schema with 4 sections:
    - general_info: key-value pairs
    - operating_statement: table with years and rows
    - balance_sheet: table with years and rows
    - cash_flow: table with years and rows
    """
    try:
        prompt = """
                   Role: You are a Senior Credit Officer at a financial institution.

                   Task: Extract critical financial ratios and credit metrics from the provided CMA document. Focus strictly on solvency, liquidity, and debt serviceability.

                   Output Rules:
                   Format: Return ONLY a valid JSON array.
                   Structure: Create one object for each fiscal year (column).
                   Nulls: If a ratio is not explicitly stated or calculable, return null.
                   Units: Convert all absolute figures to full numbers. Keep ratios as decimals (e.g., 1.33).

                   Schema Definition:

                   1. Classification
                   year: Fiscal Year (e.g. FY23)
                   type: One of "Audited", "Provisional", "Projected"

                   2. Credit Ratios (Priority - Extract if stated, else calculate)
                   dscr: Debt Service Coverage Ratio. (EBITDA - Tax) / (Interest + Principal Repayment).
                   iscr: Interest Service Coverage Ratio. (EBITDA / Interest Expense).
                   current_ratio: Current Assets / Current Liabilities.
                   debt_equity_ratio: Total Debt / Tangible Net Worth.
                   tol_tnw: Total Outside Liabilities / Tangible Net Worth.

                   3. Operating Performance (P&L)
                   gross_turnover: Total Operating Income / Sales.
                   ebitda: Operating Profit before interest, tax, dep, amort.
                   interest_expense: Total finance charges and interest costs.
                   pat: Profit After Tax.
                   cash_profit: PAT + Depreciation.
                   depreciation: Depreciation and Amortization.

                   4. Financial Position (Balance Sheet)
                   tangible_net_worth: Capital + Reserves - Intangible Assets.
                   total_debt: Long Term Borrowings + Short Term Borrowings.
                   net_working_capital: Current Assets - Current Liabilities.
                   unsecured_loans: Loans from promoters/family (Quasi-equity).
                   cash_and_bank_balance: Liquidity available on hand.
                   
                   5. Raw Components (REQUIRED for Data Model)
                   current_assets: Total Current Assets.
                   current_liabilities: Total Current Liabilities.
                   fixed_assets: Net Fixed Assets / PPE.
                   long_term_debt: Long Term Borrowings (excluding current maturity).
                   short_term_debt: Short Term Borrowings / Working Capital Limits.

                   Return ONLY the JSON array.
                   """

        # Build content based on input type
        if pdf_bytes:
            # Send PDF directly to Gemini (multimodal) - bypasses Document AI page limits
            print(f"📄 Sending CMA PDF directly to Gemini ({len(pdf_bytes)} bytes)")
            contents = [
                Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                prompt
            ]
        elif raw_text:
            # Use extracted text (from Excel or other sources)
            print(f"📝 Using extracted text for CMA analysis ({len(raw_text)} chars)")
            print(f"📄 Raw text sample (first 1000 chars):\n{raw_text[:1000]}\n... (truncated)")
            contents = f"{prompt}\n\n## RAW TEXT:\n{raw_text}"
        else:
            raise HTTPException(status_code=400, detail="Either pdf_bytes or raw_text must be provided for CMA extraction")

        # Config differs for PDF vs text input - response_mime_type may not work with multimodal
        if pdf_bytes:
            config = GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=32768
            )
        else:
            config = GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                max_output_tokens=32768
            )

        # Use fallback helper for automatic model switching on 503 errors
        response = await generate_with_fallback(
            contents=contents,
            config=config,
            use_flash=False  # Use pro models for CMA extraction
        )
        
        # Check if response has content
        if not response.text:
            print(f"⚠️ Gemini returned empty response for CMA extraction")
            raise HTTPException(status_code=500, detail="Gemini returned empty response for CMA extraction")
        
        response_text = response.text.strip()
        
        # Clean markdown if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        
        print(f"🔍 Raw Gemini JSON text:\n{response_text[:1500]}...") # Log first 1500 chars 
        extracted_list = json.loads(response_text)
        print(f"✅ Parsed JSON list with {len(extracted_list) if isinstance(extracted_list, list) else 'NOT A LIST'} items")
        
        # Helper to safely get numeric value (handles None/null)
        def safe_float(val, default=0.0):
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default
        
        # Post-Processing: Convert list to Structured Dict for CreditService
        cma_data = {
            "general_info": {"extracted_from": "gemini_schema_v2"},
            "audited_financials": [],
            "provisional_financials": None,
            "projected_financials": []
        }
        
        if isinstance(extracted_list, list):
            for idx, item in enumerate(extracted_list):
                print(f"📋 Raw item[{idx}]: {json.dumps(item, default=str)[:500]}")
                
                # Map keys to YearData format with safe_float for null handling
                mapped_item = {
                    "year": item.get("year") or "Unknown",
                    "revenue": safe_float(item.get("gross_turnover")),
                    "pat": safe_float(item.get("pat")),
                    # Fallback for depreciation
                    "depreciation": safe_float(item.get("depreciation")) or (safe_float(item.get("cash_profit")) - safe_float(item.get("pat"))),
                    "interest_expense": safe_float(item.get("interest_expense")),
                    "current_assets": safe_float(item.get("current_assets")),
                    "current_liabilities": safe_float(item.get("current_liabilities")),
                    "long_term_debt": safe_float(item.get("long_term_debt")),
                    "short_term_debt": safe_float(item.get("short_term_debt")),
                    "tangible_net_worth": safe_float(item.get("tangible_net_worth")),
                    "fixed_assets": safe_float(item.get("fixed_assets")),
                    
                    # --- CRITICAL: Map Ratios so they appear in Frontend ---
                    "dscr": safe_float(item.get("dscr")),
                    "iscr": safe_float(item.get("iscr")),
                    "current_ratio": safe_float(item.get("current_ratio")),
                    "tol_tnw": safe_float(item.get("tol_tnw")),
                    "debt_equity_ratio": safe_float(item.get("debt_equity_ratio")),
                    
                    "tier": "audited" # Default
                }
                
                # Determine Tier
                raw_type = str(item.get("type", "")).lower()
                if "audited" in raw_type:
                    mapped_item["tier"] = "audited"
                    cma_data["audited_financials"].append(mapped_item)
                elif "provisional" in raw_type or "estimated" in raw_type:
                    mapped_item["tier"] = "provisional"
                    cma_data["provisional_financials"] = mapped_item
                elif "projected" in raw_type:
                    mapped_item["tier"] = "projected"
                    cma_data["projected_financials"].append(mapped_item)
                else:
                    # Fallback based on year string?
                    cma_data["audited_financials"].append(mapped_item)
        
        print(f"✅ CMA data extracted successfully (v2 List Mode)")
        print(f"   - Audited Years: {len(cma_data['audited_financials'])}")
        print(f"   - Projected Years: {len(cma_data['projected_financials'])}")
        # Log a sample year to verify ratios are present
        if cma_data['audited_financials']:
             print(f"   - Sample Audited Data: {cma_data['audited_financials'][0]}")
        
        return cma_data
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error in CMA extraction: {str(e)}")
        return {
            "general_info": {},
            "audited_financials": [],
            "projected_financials": [],
            "provisional_financials": None
        }
    except Exception as e:
        print(f"❌ Error extracting CMA data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract CMA data: {str(e)}")

async def augment_cma_with_web_search(cma_text: str, cma_structured: Dict[str, Any]) -> Dict[str, Any]:
    """
    For CMA-only uploads, use Google Search to find company details and market info.
    Returns a partial Memo structure (Overview, Market, Products).
    """
    try:
        # 1. Identify Company Name/Context
        company_name = "Unknown Company"
        general_info = {}
        
        if cma_structured:
             general_info = cma_structured.get('general_info', {})
             company_name = general_info.get('Name of the Unit') or general_info.get('Name') or general_info.get('borrower_name') or "Unknown Company"
        
        # If name is unknown, we can't search effectively
        if company_name == "Unknown Company":
            # Try regex on raw text as fallback
            match = re.search(r"(?:Name of the Unit|Borrower Name|Name)\s*[:\-\s]\s*([^\n]+)", cma_text, re.IGNORECASE)
            if match:
                company_name = match.group(1).strip()

        print(f"🔍 Performing Deep Web-Augmented Analysis for: {company_name}")

        prompt = f"""
        You are an elite Investment Banker and Credit Analyst. You are analyzing a company named "{company_name}" based on a CMA report and Web Research.

        **TARGET ENTITY**: {company_name}
        **KNOWN CONTEXT**: {json.dumps(general_info, indent=2)}

        **MISSION**:
        Perform a comprehensive web search to build an Investment Memo profile. 
        You MUST fill in all fields. If specific private data is not available, you MUST:
        1. Infer reasonable estimates based on the company's size, location, and industry sector.
        2. Use Industry Intelligence to populate Market Analysis (TAM/SAM, Growth Rates).
        3. Identify 3-5 likely competitors in the same region or sector.

        **REQUIRED OUTPUT SECTIONS**:

        1. **COMPANY OVERVIEW**: 
           - Search for the company website, LinkedIn, and business directories (Zauba Corp, Indiamart).
           - Identify Promoters/Directors.
           - Determine exact Business Model (B2B/B2C, Manufacturing vs Trading).

        2. **MARKET ANALYSIS (CRITICAL)**:
           - Define the Industry Sector (e.g., "Textile Manufacturing in Gujarat" or "Auto Components").
           - ESTIMATE the Total Addressable Market (TAM) for this sector in India. (e.g. "Indian Textile Market is $150B...").
           - ESTIMATE Growth Rate (CAGR).
           - Identify granular Sub-segment opportunities.

        3. **COMPETITION**:
           - List specific competitor names. 
           - If private, list larger public proxies or typical local competitors.
           - Estimate their revenue/scale if possible.

        **JSON OUTPUT FORMAT**:
        {{
            "company_overview": {{
                "name": "{company_name}",
                "sector": "Specific Sector",
                "description": "Comprehensive description...",
                "founders": [
                    {{ "name": "Name 1", "designation": "Director", "background": "Experience..." }},
                    {{ "name": "Name 2", "designation": "Director" }}
                ],
                "business_model": [
                   {{
                       "revenue_streams": "Primary Revenue Source",
                       "description": " Detailed explanation...",
                       "target_audience": "Target Customer Profile"
                   }}
                ],
                "establishment_year": "YYYY",
                "location": "City, State",
                "technologies_used": "Relevant tech/machinery...",
                "key_problems_solved": ["Problem 1", "Problem 2"]
            }},
            "products_and_services": [
                {{
                    "name": "Core Product/Service",
                    "description": "Details...",
                    "revenue_share": "High/Medium/Low"
                }}
            ],
            "market_analysis": {{
                "industry_size_and_growth": {{
                    "total_addressable_market": {{ "name": "Indian Market Sector", "value": "₹XX,XXX Cr", "cagr": "XX%", "source": "Industry Reports" }},
                    "serviceable_obtainable_market": {{ "name": "Regional/Target Market", "value": "₹X,XXX Cr", "cagr": "XX%", "projection": "Positive" }},
                    "commentary": "Detailed industry trends, growth drivers, and headwinds..."
                }},
                "sub_segment_opportunities": ["Opportunity 1", "Opportunity 2", "Opportunity 3"],
                "competitor_details": [
                    {{
                        "name": "Competitor 1",
                        "headquarters": "Location",
                        "revenue_streams": "Similar products",
                        "market_share": "Leading/Niche",
                        "strategic_focus": "Differentiation factor"
                    }},
                    {{
                        "name": "Competitor 2",
                        "headquarters": "Location"
                    }}
                ],
                "reports": [
                    {{ "title": "Index Sector Report 2024", "source_name": "IBEF/Crisil", "summary": "Sector outlook...", "source_url": "https://example.com" }}
                ]
            }},
            "competition": {{
                 "competitive_advantage": "Key strengths vs peers",
                 "market_position": "Market Leader / Challenger / Niche Player"
            }}
        }}
        """

        # Configure with Search Tool
        tools = [Tool(google_search=GoogleSearch())]
        config = GenerateContentConfig(
            temperature=0.4, # Slightly higher for creative inference
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192, # Allow long responses
            response_mime_type="application/json",
            tools=tools
        )

        response = await generate_with_fallback(
            contents=prompt,
            config=config,
            models=MODELS_PRO
        )

        return json.loads(response.text)

    except Exception as e:
        print(f"Error in Deep Web-Augmented Analysis: {e}")
        import traceback
        traceback.print_exc()
        # Return skeleton with Company Name at least
        return {
            "company_overview": { 
                "name": company_name, 
                "description": f"Could not retrieve deep analysis. Error: {str(e)}",
                "sector": "Unknown"
            },
            "market_analysis": {},
            "products_and_services": []
        }
