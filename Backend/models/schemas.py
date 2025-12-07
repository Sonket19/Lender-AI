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
class WeightageUpdate(BaseModel):
    team_strength: int
    market_opportunity: int
    traction: int
    claim_credibility: int
    financial_health: int

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
class WeightageUpdate(BaseModel):
    team_strength: int
    market_opportunity: int
    traction: int
    claim_credibility: int
    financial_health: int

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