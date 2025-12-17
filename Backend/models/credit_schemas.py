from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class TrustTier(str, Enum):
    """Data trust classification based on audit status"""
    AUDITED = "audited"
    PROVISIONAL = "provisional"
    PROJECTED = "projected"


class YearData(BaseModel):
    """Financial data for a single fiscal year"""
    year: str = Field(..., description="Fiscal year e.g., 'FY24'")
    tier: TrustTier = Field(..., description="Trust classification")
    
    # Income Statement
    revenue: float = Field(0.0, description="Total Revenue/Turnover in INR")
    pat: float = Field(0.0, description="Profit After Tax in INR")
    depreciation: float = Field(0.0, description="Depreciation expense in INR")
    interest_expense: float = Field(0.0, description="Interest on borrowings in INR")
    
    # Balance Sheet - Assets
    current_assets: float = Field(0.0, description="Total Current Assets in INR")
    fixed_assets: float = Field(0.0, description="Net Fixed Assets in INR")
    
    # Balance Sheet - Liabilities
    current_liabilities: float = Field(0.0, description="Total Current Liabilities in INR")
    long_term_debt: float = Field(0.0, description="Long Term Borrowings in INR")
    short_term_debt: float = Field(0.0, description="Short Term Borrowings/Working Capital in INR")
    
    # Equity
    tangible_net_worth: float = Field(0.0, description="TNW = Equity - Intangibles")
    
    # Calculated fields
    @property
    def total_outside_liabilities(self) -> float:
        """TOL = Long Term Debt + Short Term Debt + Current Liabilities (excluding bank)"""
        return self.long_term_debt + self.short_term_debt + self.current_liabilities
    
    @property
    def cash_accrual(self) -> float:
        """Cash Accrual = PAT + Depreciation"""
        return self.pat + self.depreciation

    model_config = {"use_enum_values": True, "extra": "ignore"}


class CMAModel(BaseModel):
    """
    Complete CMA (Credit Monitoring Arrangement) Data Model.
    Implements tiered trust levels for banking compliance.
    """
    audited_financials: List[YearData] = Field(default_factory=list, description="High Trust - CA Audited")
    provisional_financials: Optional[YearData] = Field(None, description="Medium Trust - Management Estimates")
    projected_financials: List[YearData] = Field(default_factory=list, description="Low Trust - Future Projections")
    
    # Flags for guardrails
    optimism_warning: Optional[str] = None
    adjusted_projections: bool = False
    
    @model_validator(mode='after')
    def apply_optimism_guardrail(self):
        """
        ICICI Guardrail: If projected revenue growth > 300% YoY AND historical revenue > 0,
        cap the growth at 50% and flag a warning.
        """
        audited = self.audited_financials
        projected = self.projected_financials
        
        if not audited or not projected:
            return self
        
        # Get last audited revenue as baseline
        last_audited = audited[-1] if audited else None
        if not last_audited or last_audited.revenue <= 0:
            return self
        
        baseline_revenue = last_audited.revenue
        
        # Check each projection year
        adjusted = False
        for i, proj in enumerate(projected):
            if i == 0:
                prev_revenue = baseline_revenue
            else:
                prev_revenue = projected[i-1].revenue
            
            if prev_revenue > 0:
                growth_rate = (proj.revenue - prev_revenue) / prev_revenue
                
                # If growth > 300%, cap at 50%
                if growth_rate > 3.0:  # 300%
                    capped_revenue = prev_revenue * 1.5  # 50% growth
                    proj.revenue = capped_revenue
                    adjusted = True
        
        if adjusted:
            self.optimism_warning = "Optimism Bias Detected: Projected growth exceeded 300% YoY and was capped at 50%."
            self.adjusted_projections = True
        
        return self
    
    def get_latest_financials(self) -> Optional[YearData]:
        """Returns the most recent financial data (provisional > audited)"""
        if self.provisional_financials:
            return self.provisional_financials
        if self.audited_financials:
            return self.audited_financials[-1]
        return None


class SchemeType(str, Enum):
    """ICICI Bank Loan Schemes"""
    MUDRA = "Mudra Yojana"
    CGTMSE = "CGTMSE"
    CGSS = "CGSS (Startup India)"
    NEW_ENTITY = "Loans for New Entities"
    BIL = "Business Installment Loan"
    ADVISORY = "iStartup 2.0 Current Account"


class EligibilityStatus(str, Enum):
    """Credit Decision Status"""
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CONDITIONAL = "Conditional"
    REFERRAL = "Referral"
    INELIGIBLE = "Ineligible"


class WaterfallStep(BaseModel):
    """A single step in the product router waterfall"""
    step_number: int
    scheme_name: str
    rule_checked: str
    result: str  # "Pass" or "Fail"
    reason: str


class CreditResult(BaseModel):
    """Complete Credit Analysis Result"""
    deal_id: str
    analyzed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    # Recommendation
    eligible_scheme: SchemeType
    status: EligibilityStatus
    max_permissible_limit: float = Field(..., description="MPBF in INR")
    recommended_amount: float = Field(0.0, description="Recommended sanction amount")
    
    # Core Ratios
    current_ratio: float = Field(..., description="Current Assets / Current Liabilities")
    current_ratio_status: str = Field(..., description="Eligible/Restricted/Ineligible")
    
    tol_tnw: float = Field(..., description="Total Outside Liabilities / Tangible Net Worth")
    leverage_status: str = Field(..., description="Safe/High Risk/Critical")
    
    avg_dscr: float = Field(..., description="Average Debt Service Coverage Ratio")
    dscr_status: str = Field(..., description="Approved/Rejected for Term Loan")
    
    yearly_dscr: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Flags & Notes
    flags: List[str] = Field(default_factory=list)
    compliance_notes: List[str] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)
    
    # Visualization Data
    radar_chart_data: Dict[str, float] = Field(default_factory=dict)
    working_capital_analysis: Dict[str, Any] = Field(default_factory=dict, description="Breakdown: Gross CA, OCL, WC Gap, Margin, MPBF")
    waterfall_data: List[WaterfallStep] = Field(default_factory=list)
    
    # Government Scheme Eligibility
    cgtmse_eligible: bool = False
    mudra_eligible: bool = False
    cgss_eligible: bool = False
    
    # Guarantee Fee (for CGTMSE)
    guarantee_fee_percent: float = 0.0
    guarantee_fee_amount: float = 0.0

    model_config = {"use_enum_values": True}


class UserProfile(BaseModel):
    """User/Entity profile for scheme eligibility"""
    deal_id: str
    entity_type: str = Field("Pvt Ltd", description="Proprietorship/Partnership/Pvt Ltd/LLP")
    vintage_years: float = Field(0.0, description="Years since incorporation")
    loan_amount_requested: float = Field(0.0, description="Requested loan amount in INR")
    has_collateral: bool = False
    dpiit_recognized: bool = False
    industry_sector: str = ""
    is_profitable_2_years: bool = False


class OverrideRequest(BaseModel):
    """Request to override a credit decision"""
    deal_id: str
    rule_id: str = Field(..., description="e.g., 'dscr_check', 'leverage_check'")
    justification: str = Field(..., min_length=20, description="Detailed reason for override")
    analyst_id: str


class OverrideAuditLog(BaseModel):
    """Audit log entry for compliance"""
    deal_id: str
    rule_id: str
    original_status: str
    new_status: str
    justification: str
    analyst_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    ip_address: Optional[str] = None
