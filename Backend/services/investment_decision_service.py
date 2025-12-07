import json
from typing import Dict, Any
from datetime import datetime
from fastapi import HTTPException
from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch
from config.settings import settings

# Initialize Google Gen AI client
client = genai.Client(api_key=settings.GEMINI_API_KEY)

async def generate_investment_decision(
    deal_id: str,
    memo: Dict[str, Any],
    extracted_text: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Generate comprehensive investment decision and funding plan using Gemini AI.
    
    Args:
        deal_id: Unique deal identifier
        memo: Complete investment memo with analysis
        extracted_text: Original pitch deck text
        user_id: ID of the user generating the decision
    
    Returns:
        Complete investment decision structure
    """
    try:
        # Extract key information from memo
        company_name = memo.get('company_overview', {}).get('name', 'Unknown')
        sector = memo.get('company_overview', {}).get('sector', 'Unknown')
        risk_score = memo.get('risk_metrics', {}).get('composite_risk_score', 50)
        
        # Get financial data
        financials = memo.get('financials', {})
        funding_ask = financials.get('burn_and_runway', {}).get('funding_ask', 'Not specified')
        current_arr = financials.get('arr_mrr', {}).get('current_booked_arr', 'Not available')
        burn_rate = financials.get('burn_and_runway', {}).get('implied_net_burn', 'Not available')
        runway = financials.get('burn_and_runway', {}).get('stated_runway', 'Not available')
        
        # Get market and team data
        market_size = memo.get('market_analysis', {}).get('industry_size_and_growth', {}).get('total_addressable_market', {}).get('value', 'Not available')
        founders = memo.get('company_overview', {}).get('founders', [])
        
        prompt = f"""
You are a SENIOR INVESTOR with 15+ years backing early-stage companies. You've invested in over 50 startups with multiple successful exits. You're known for asking tough questions, spotting patterns others miss, and making clear, decisive recommendations.

YOUR INVESTMENT PHILOSOPHY: Back exceptional founders solving real problems in large markets. Look for businesses that can grow 10x in value within 5-7 years.

==================== COMPANY UNDER REVIEW ====================

**Company:** {company_name}
**Industry:** {sector}
**Risk Assessment Score:** {risk_score}/100 (lower = less risky)
**They're Asking For:** {funding_ask}

**Current Business Metrics:**
- Annual Recurring Revenue: {current_arr}
- Monthly Cash Burn: {burn_rate}
- Cash Runway: {runway}
- Market Size: {market_size}

**Our Analysis Summary:**
{json.dumps(memo.get('conclusion', {}), indent=2)}

**Financial Details:**
{json.dumps(financials, indent=2)[:1500]}

**Market Understanding:**
{json.dumps(memo.get('market_analysis', {}), indent=2)[:2000]}

**The Team:**
{json.dumps(founders, indent=2)[:1000]}

**From Their Pitch:**
{extracted_text[:5000]}

==================== HOW TO MAKE THIS DECISION ====================

### 1. THE THREE PATHS: PROCEED, CONDITIONAL, or PASS

**Choose PROCEED when:**
- Risk score under 40 AND the team has both expertise AND customers already
- They're solving a painful problem people will actually pay for
- The market timing is right (not too early, not too crowded)
- This could realistically become a category-defining company
- You can clearly see the path to 50-100x value creation
- Your rationale must answer: WHY NOW? WHY THIS TEAM? WHY WILL THIS WIN?

**Choose CONDITIONAL when:**
- Risk score 40-70 BUT the risks are fixable with our help
- Good team with gaps we can fill (we help them hire key people)
- The market is proven but execution is uncertain
- We need to see specific proof points before committing full capital
- Your rationale must explain: WHAT WORRIES US? WHAT MILESTONES PROVE IT WORKS? HOW DO WE HELP?

**Choose PASS when:**
- Risk score over 70 with fundamental problems (weak team, saturated market, unsustainable burn)
- Asking for unrealistic amounts given their traction (e.g., $5M at idea stage)
- Market too small for venture-scale returns (under $1B potential)
- Better opportunities exist for our capital
- Your rationale must explain: WHY NOT NOW? WHAT WOULD CHANGE OUR MIND?

### 2. HOW MUCH MONEY TO INVEST

**Think about:**
- **Runway Calculation**: How many months does this money actually buy them? (their monthly burn × months)
- **Milestone Thinking**: Is it enough to reach the NEXT major value milestone, not just survive?
- **Market Comparison**: What do similar companies at this stage typically raise?
- **Ownership**: Are we getting meaningful ownership (typically 15-25%) for our check size?
- **Follow-On Strategy**: This is just the first investment - we'll need to reserve 2-3x for future rounds

**Your recommendation must explain:**
- Why this specific amount gets them to the next big milestone
- How it compares to what they asked for (if different, explain the business logic)
- What they can achieve with this money in terms of REAL PROGRESS
- Whether we need a board seat to protect this investment

### 3. HOW TO STRUCTURE THE INVESTMENT (Tranches)

**Investment Philosophy - Give Money as They Prove the Business:**

**FIRST PAYMENT (40-50% of total):**
- Covers their first 6-9 months
- Enough to hit the first major proof point
- Released upon standard closing (legal docs, contracts signed)

**SECOND PAYMENT (25-35% of total):**
- Triggered by REVENUE milestones (not just building product)
- Proves their business model actually works
- Timing: 6-9 months after closing

**THIRD PAYMENT (remaining %):**
- Only if they've proven they can sell and scale
- Prepares them for next funding round
- Timing: 12-18 months after closing

**Each condition must be:**
- MEASURABLE in numbers (not subjective opinions)
- REALISTIC given their resources and timeline
- MEANINGFUL (actually proves something important about the business)

### 4. THE ROADMAP - What Success Looks Like

**Four Categories to Plan:**
- **Revenue & Sales**: Customer acquisition, pricing validation, revenue growth
- **Product**: What gets built, when, and why it drives revenue
- **Team**: Critical hires that unlock the next stage of growth
- **Market Position**: Partnerships, market share, competitive wins

**Each milestone must answer:**
- **Why This Matters**: Why is THIS goal important RIGHT NOW?
- **How We Measure Success**: Specific numbers that prove it's achieved
- **What It Proves**: What does this tell us about the business viability?

**Think Like an Experienced Investor:**
- Don't just repeat their plan - add milestones they haven't considered
- Put revenue goals first (that's what matters for exits)
- Only include technical goals if they directly drive revenue
- Be specific about hires (not "hire salespeople" but "hire VP Sales with 10+ years enterprise experience")

### 5. NEXT FUNDING ROUND - What They Need for Series A

**What bigger investors will want to see:**
- Revenue targets with specific numbers ("$3M annual revenue" not "strong growth")
- Growth rates that matter (at least 40% year-over-year)
- Proven business model (they make more from customers than it costs to acquire them)
- Market validation (real customers, high retention, strong references)
- Complete team (key positions filled with experienced people)

**Ask: Would Sequoia, Benchmark, or Andreessen Horowitz fund this at Series A? What do they need to see?**

### 6. WARNING SIGNS - What Could Go Wrong

**Financial Risks:**
- Cash burn increasing without revenue increasing
- Customers canceling or not paying
- Cost to acquire customers higher than their value

**Team Risks:**
- Founder conflicts or departures
- Can't hire key people they need
- Critical dependency on one person

**Market Risks:**
- Competitors raising large rounds
- Too much revenue from one customer (concentration risk)
- Market moving away from their solution

**Execution Risks:**
- Missing important milestones repeatedly
- Major product delays
- Talk of pivoting the business model

**These warnings should trigger board discussions and possible intervention.**

### 7. SUCCESS DASHBOARD - What to Track Monthly

**Define 5-7 metrics we watch every month:**
- Revenue metrics (monthly revenue, annual revenue, growth rates)
- Customer metrics (new customers, lost customers, customer value)
- Efficiency metrics (cost to acquire customer, customer lifetime value, payback time)
- Product metrics (users, engagement, retention)
- Team metrics (key hires made, critical roles open)

==================== YOUR INVESTMENT DECISION ====================

Write your complete decision as JSON. Make your RATIONALE read like you're explaining this to a fellow investor in plain business language - no jargon, just clear thinking:

{{
    "recommendation": "PROCEED|CONDITIONAL|PASS",
    
    "funding_amount_recommended": "$X.XM - [explain in one sentence: based on runway needs, milestone funding, or market standards]",
    
    "funding_amount_requested": "{funding_ask}",
    
    "rationale": "Write 3-4 clear, well-structured paragraphs explaining your investment thinking in plain business language:
    
    First, explain THE OPPORTUNITY - why this company, why this market, why invest now. Use specific numbers from their traction data. Compare to similar successful companies if relevant. What's their unfair advantage or unique insight that makes this compelling?
    
    Second, assess THE TEAM honestly - do the founders have real domain expertise? What's their track record? What concerns you about the team? What gives you confidence they can execute? Be specific about their backgrounds and any gaps that worry you.
    
    Third, break down THE BUSINESS CASE simply - can they make significantly more money from customers than it costs to acquire them? What's the realistic path to profitability? What could this company be worth in 5-7 years and why is that realistic?
    
    Finally, explain YOUR DECISION clearly - why PROCEED, CONDITIONAL, or PASS? If CONDITIONAL, which specific milestones matter most and why? If PASS, what would need to change for you to reconsider? If PROCEED, why is this opportunity better than alternatives?
    
    Write these as natural paragraphs without labels or section headers - just clear, flowing business reasoning.",
    
    "disbursement_schedule": [
        {{
            "tranche_number": 1,
            "amount": "$XXXk (calculation: X months of burn at $Y/month gives them runway to [milestone])",
            "percentage": 45.0,
            "timing": "When deal closes and paperwork is complete",
            "conditions": ["Legal documents finalized", "Key employment contracts signed", "Standard due diligence complete"]
        }},
        {{
            "tranche_number": 2,
            "amount": "$XXXk",
            "percentage": 30.0,
            "timing": "Month 6 OR when they hit revenue milestone (whichever first)",
            "conditions": [
                "Achieve $[X] monthly revenue from [Y] paying customers",
                "Customer cancellation rate below 15% monthly",
                "Making more from customers than spending to acquire them (3x ratio minimum)"
            ]
        }},
        {{
            "tranche_number": 3,
            "amount": "$XXXk",
            "percentage": 25.0,
            "timing": "Month 12-15 OR ready for Series A",
            "conditions": [
                "$[X] in annual revenue growing 30%+ year-over-year",
                "Product-market fit proven (customer satisfaction high, retention above 85%)",
                "Key leadership hired (sales leader, engineering leader)"
            ]
        }}
    ],
    
    "milestone_roadmap": [
        {{
            "category": "Revenue & Customer Growth",
            "overall_timeline": "0-18 months",
            "milestones": [
                {{
                    "title": "First $100k Annual Revenue",
                    "description": "Prove the business model works - focus on REPEATABLE sales, not one-off custom deals",
                    "timeline": "Month 4-6",
                    "success_criteria": "$100k annual revenue from 15+ customers, average deal size $7k, customer cancellation under 10%, typical 3-month sales cycle",
                    "priority": "High"
                }},
                {{
                    "title": "Reach $500k Annual Revenue",
                    "description": "Prove they can SCALE - this shows it's not just pilot projects anymore",
                    "timeline": "Month 10-12",
                    "success_criteria": "$500k annual revenue, 50+ customers, customer acquisition cost under $5k, customer value 4x+ acquisition cost, healthy 40%+ margins",
                    "priority": "High"
                }}
            ]
        }},
        {{
            "category": "Product & Technology",
            "overall_timeline": "0-12 months",
            "milestones": [
                {{
                    "title": "Production-Ready Platform",
                    "description": "NOT an MVP - this means enterprise-grade quality that customers will actually pay for",
                    "timeline": "Month 6",
                    "success_criteria": "99.9% uptime, security certification started, documented APIs, handles 1000+ users smoothly",
                    "priority": "High"
                }}
            ]
        }},
        {{
            "category": "Team Building",
            "overall_timeline": "0-12 months",
            "milestones": [
                {{
                    "title": "Hire Sales Leader",
                    "description": "CRITICAL - founders alone can't scale sales. Need proven enterprise seller.",
                    "timeline": "Month 3-6",
                    "success_criteria": "10+ years experience selling B2B software, has previously scaled a company from $0 to $10M revenue, strong references",
                    "priority": "High"
                }}
            ]
        }},
        {{
            "category": "Market Position",
            "overall_timeline": "0-18 months",
            "milestones": [
                {{
                    "title": "Strategic Partnership",
                    "description": "De-risk customer acquisition - partner with established player for easier market access",
                    "timeline": "Month 8-12",
                    "success_criteria": "Signed partnership with recognized brand in their industry, generated 10+ qualified customer leads through partner",
                    "priority": "Medium"
                }}
            ]
        }}
    ],
    
    "next_round_criteria": [
        "REVENUE: $3M+ annual revenue growing 40%+ yearly (quarter-over-quarter acceleration)",
        "BUSINESS MODEL: Customers worth 5x+ what they cost to acquire, get money back within 6 months, margins above 70%",
        "CUSTOMERS: Keep more than 95% of customers annually, actually expanding revenue from existing customers (110%+ retention in dollars)",
        "MARKET PROOF: 100+ customers spread across 5 different verticals (proves it's not just one niche)",
        "TEAM: Sales leader, engineering leader, 2 account executives, 3 engineers minimum - proven they can scale the organization",
        "MOMENTUM: Adding $100k+ in monthly revenue consistently for 6 straight months (proves it's repeatable)"
    ],
    
    "red_flags": [
        "BURN WARNING: Monthly burn up 20%+ without revenue up proportionally (burning money inefficiently)",
        "CUSTOMER LOSS: Losing more than 3% of customers monthly OR any single customer over 15% of revenue leaves",
        "HIRING FAIL: Can't hire sales leader within 6 months (shows wrong priorities or can't recruit)",
        "PRODUCT DELAYS: Major features delayed 2+ months OR considering major business pivot (questions product-market fit)",
        "FOUNDER ISSUES: Co-founder leaves OR ongoing conflicts in board meetings (team falling apart)",
        "COMPETITION: Competitor raises $20M+ round (makes our next funding round harder)"
    ],
    
    "success_metrics": {{
        "Annual Revenue": "Target path: $100k at Month 6, $500k at Month 12, $1.5M at Month 18 (tripling yearly)",
        "Monthly Revenue Growth": "Consistent 15%+ monthly growth compounds to huge annual numbers",
        "Customer Acquisition Cost": "Target under $5k per customer, trending down as we optimize our approach",
        "Customer Lifetime Value": "Target $25k+ per customer (5x what it costs), growing through upsells",
        "Gross Profit Margin": "Target 70%+ consistently (standard for scalable software businesses)",
        "Burn Efficiency": "For every dollar of new annual revenue, spend less than $1.50 (shows capital efficiency)",
        "Sales Productivity": "Each dollar spent on sales & marketing should return $0.75+ in revenue quarterly (payback under 18 months)"
    }}
}}

==================== CRITICAL INSTRUCTIONS ====================

1. **BE SPECIFIC WITH NUMBERS**: Use actual values ($100k revenue, not "good traction")
2. **THINK ABOUT THE EXIT**: This investment needs to return 10x+ in 5-7 years - is that realistic?
3. **USE COMPARISONS**: Google Search comparable companies - what did they achieve at this stage?
4. **RATIONALE = BUSINESS CONVERSATION**: Write like you're explaining to a smart friend, not writing a finance textbook
5. **MILESTONES = PROOF POINTS**: Each milestone should PROVE something critical about whether this business works
6. **BE HONEST**: If it's PASS, explain why respectfully. If CONDITIONAL, be clear what concerns you.
7. **CHECK YOUR MATH**: Percentages must add to 100%. Dollar amounts must match your recommendation.
8. **BE REALISTIC**: Don't promise $1M revenue in 3 months if they're at zero today
9. **ADD VALUE**: Include insights THEY didn't mention - that's what experienced investors provide

Return ONLY valid JSON. No markdown formatting.
"""


        # Call Gemini with Google Search grounding
        response = client.models.generate_content(
            model='gemini-3-pro-preview',
            contents=prompt,
            config=GenerateContentConfig(
                tools=[Tool(google_search=GoogleSearch())],
                temperature=0.3,
                top_p=0.9,
                max_output_tokens=8192,
                response_mime_type="application/json"
            )
        )
        
        # Parse response
        response_text = response.text.strip()
        
        # Remove markdown if present
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
        
        decision = json.loads(response_text)
        
        # Add metadata
        decision['deal_id'] = deal_id
        decision['generated_at'] = datetime.utcnow().isoformat() + "Z"
        decision['generated_by'] = user_id
        
        # Validate required fields
        required_fields = [
            'recommendation', 'funding_amount_recommended', 'funding_amount_requested',
            'rationale', 'disbursement_schedule', 'milestone_roadmap',
            'next_round_criteria', 'red_flags', 'success_metrics'
        ]
        
        for field in required_fields:
            if field not in decision:
                raise ValueError(f"Missing required field: {field}")
        
        return decision
        
    except json.JSONDecodeError as e:
        print(f"Error parsing investment decision JSON: {str(e)}")
        print(f"Response text: {response_text[:500]}")
        raise HTTPException(
            status_code=500,
            detail="Failed to parse investment decision response"
        )
    except Exception as e:
        print(f"Error generating investment decision: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate investment decision: {str(e)}"
        )
