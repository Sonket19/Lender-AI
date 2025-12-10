# from pydantic import BaseModel, validator
# from typing import List, Dict, Optional

# New Chat Code
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# class WeightageUpdate(BaseModel):
#     team_strength: int = 20
#     market_opportunity: int = 20
#     traction: int = 20
#     claim_credibility: int = 20
#     financial_health: int = 20
    
#     @validator('*')
#     def check_percentage(cls, v):
#         if not 0 <= v <= 100:
#             raise ValueError('Weightage must be between 0 and 100')
#         return v
    
#     @validator('financial_health')
#     def check_total(cls, v, values):
#         total = v + sum(values.values())
#         if total != 100:
#             raise ValueError(f'Total weightage must equal 100, got {total}')
#         return v

class FounderInfo(BaseModel):
    name: str
    education: str
    professional_background: str
    previous_ventures: str

class InterviewRequest(BaseModel):
    founder_email: str
    founder_name: Optional[str] = None

# class ChatMessage(BaseModel):
#     text: str

# New Chat Code


class InitiateInterviewRequest(BaseModel):
    deal_id: str
    founder_email: EmailStr
    founder_name: Optional[str] = None

class ChatMessage(BaseModel):
    message: str
    interview_token: str

class ChatResponse(BaseModel):
    message: str
    is_complete: bool
    gathered_fields: List[str]
    missing_fields: List[str]

# Investment Decision Models
class FundingTranche(BaseModel):
    tranche_number: int
    amount: str
    percentage: float
    timing: str  # e.g., "Upon signing", "Month 6", "Upon ARR $500k"
    conditions: List[str]

class Milestone(BaseModel):
    title: str
    description: str
    timeline: str
    success_criteria: str
    priority: str  # High, Medium, Low

class MilestoneCategory(BaseModel):
    category: str  # Product, Revenue, Team, Market
    milestones: List[Milestone]
    overall_timeline: str

class InvestmentDecision(BaseModel):
    deal_id: str
    recommendation: str  # PROCEED / PASS / CONDITIONAL
    funding_amount_recommended: str
    funding_amount_requested: str
# from pydantic import BaseModel, validator
# from typing import List, Dict, Optional

# New Chat Code
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# class WeightageUpdate(BaseModel):
#     team_strength: int = 20
#     market_opportunity: int = 20
#     traction: int = 20
#     claim_credibility: int = 20
#     financial_health: int = 20
    
#     @validator('*')
#     def check_percentage(cls, v):
#         if not 0 <= v <= 100:
#             raise ValueError('Weightage must be between 0 and 100')
#         return v
    
#     @validator('financial_health')
#     def check_total(cls, v, values):
#         total = v + sum(values.values())
#         if total != 100:
#             raise ValueError(f'Total weightage must equal 100, got {total}')
#         return v

class FounderInfo(BaseModel):
    name: str
    education: str
    professional_background: str
    previous_ventures: str

class InterviewRequest(BaseModel):
    founder_email: str
    founder_name: Optional[str] = None

# class ChatMessage(BaseModel):
#     text: str

# New Chat Code


class InitiateInterviewRequest(BaseModel):
    deal_id: str
    founder_email: EmailStr
    founder_name: Optional[str] = None

class ChatMessage(BaseModel):
    message: str
    interview_token: str

class ChatResponse(BaseModel):
    message: str
    is_complete: bool
    gathered_fields: List[str]
    missing_fields: List[str]

# Investment Decision Models
class FundingTranche(BaseModel):
    tranche_number: int
    amount: str
    percentage: float
    timing: str  # e.g., "Upon signing", "Month 6", "Upon ARR $500k"
    conditions: List[str]

class Milestone(BaseModel):
    title: str
    description: str
    timeline: str
    success_criteria: str
    priority: str  # High, Medium, Low

class MilestoneCategory(BaseModel):
    category: str  # Product, Revenue, Team, Market
    milestones: List[Milestone]
    overall_timeline: str

class InvestmentDecision(BaseModel):
    deal_id: str
    recommendation: str  # PROCEED / PASS / CONDITIONAL
    funding_amount_recommended: str
    funding_amount_requested: str
    rationale: str
    disbursement_schedule: List[FundingTranche]
    milestone_roadmap: List[MilestoneCategory]
    next_round_criteria: List[str]
    red_flags: List[str]
    success_metrics: Dict[str, str]
    generated_at: Optional[str] = None
    generated_by: Optional[str] = None

class FactCheck(BaseModel):
    claim: str
    verdict: str  # Verified, Exaggerated, False, Unverifiable
    explanation: str
    source_url: Optional[str] = None
    confidence: str # High, Medium, Low

class FactCheckResponse(BaseModel):
    deal_id: str
    claims: List[FactCheck]
    checked_at: str

# CMA Report Data Models
class CMARow(BaseModel):
    """A single row in a CMA table (e.g., 'Revenue from Operations')"""
    particulars: str
    values: List[str]  # Values for each year/period

class CMATable(BaseModel):
    """A table section (Operating Statement, Balance Sheet, Cash Flow)"""
    years: List[str]  # Column headers (e.g., ['FY24 (Audited)', 'FY25 (Estimated)'])
    rows: List[CMARow]  # All rows in the table

class CMAData(BaseModel):
    """Complete structured CMA report data"""
    general_info: Dict[str, str]  # Key-value pairs for general information
    operating_statement: CMATable
    balance_sheet: CMATable
    cash_flow: CMATable

# Credit Analysis Models (4-Gate Digital Underwriting Framework)
class GateCheck(BaseModel):
    """Individual check within a gate"""
    name: str  # e.g., "Negative List Check", "DSCR"
    status: str  # "Pass", "Fail", "Review"
    result: str  # e.g., "1.45", "SaaS / Technology"
    details: str  # Detailed explanation
    flags: List[str] = []  # Red flags if any

class Gate(BaseModel):
    """A complete gate with multiple checks"""
    gate_number: int
    gate_name: str  # e.g., "Policy & Market Knock-Out"
    status: str  # Overall gate status: "Pass", "Fail", "Review"
    checks: List[GateCheck]

class CreditAnalysis(BaseModel):
    """Complete credit analysis following 4-Gate Algorithm"""
    gates: List[Gate]  # All 4 gates
    
    # Summary metrics
    loan_amount_requested: str  # From pitch deck
    max_permissible_limit: str  # Calculated MPBF
    dscr: str  # Debt Service Coverage Ratio
    current_ratio: str
    tol_tnw_ratio: str  # Total Outside Liabilities / Tangible Net Worth
    runway_months: str  # Cash runway after loan
    
    # Final verdict
    recommendation: str  # "SANCTION", "REJECT", "CONDITIONAL"
    sanction_amount: str  # If approved, the amount
    conditions: List[str]  # Conditions for sanction
    rejection_reasons: List[str]  # If rejected, why
    cgtmse_eligible: bool  # Government guarantee eligibility
    
    # Summary table entries
    summary_table: List[Dict[str, str]]  # [{parameter, result, status}]