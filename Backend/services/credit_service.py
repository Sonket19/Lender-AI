# Backend/services/credit_service.py
"""
ICICI Bank Credit Decision Engine
Deterministic financial analysis for loan eligibility.

This module runs parallel to memo_service.py and handles quantitative CMA analysis.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from google.cloud import firestore
from config.settings import settings

from models.credit_schemas import (
    CMAModel, YearData, TrustTier,
    CreditResult, UserProfile, SchemeType, EligibilityStatus,
    WaterfallStep, OverrideRequest, OverrideAuditLog
)

# Initialize Firestore
db = firestore.Client(project=settings.GCP_PROJECT_ID)


class CreditService:
    """
    Core Credit Analysis Service.
    Implements ICICI Bank's lending covenants with deterministic logic.
    """
    
    # ========== BENCHMARK CONSTANTS ==========
    CR_ELIGIBLE_THRESHOLD = 1.33      # Current Ratio for standard eligibility
    CR_RESTRICTED_THRESHOLD = 1.0     # Below this = Ineligible
    
    TOL_TNW_HIGH_RISK = 3.0           # Leverage threshold for high risk
    TOL_TNW_CRITICAL = 4.0            # Hard reject threshold
    
    DSCR_APPROVE_THRESHOLD = 1.25     # Approve term loan
    DSCR_REJECT_THRESHOLD = 1.15      # Reject term loan
    
    # MPBF Constants - RBI Guidelines
    TURNOVER_METHOD_THRESHOLD = 5_00_00_000  # ₹5 Crores - threshold for method selection
    
    # Nayak Committee (Turnover Method) - for turnover < ₹5Cr
    NAYAK_GROSS_WC_PERCENT = 0.25     # 25% of projected turnover
    NAYAK_PROMOTER_MARGIN = 0.05      # 5% promoter contribution
    # Effective MPBF = 20% of turnover (25% - 5%)
    
    # Tandon Committee (Method II) - for turnover >= ₹5Cr
    TANDON_MARGIN_PERCENT = 0.25      # 25% margin on Total Current Assets
    
    MUDRA_MAX_AMOUNT = 10_00_000      # 10 Lakhs
    CGTMSE_MAX_AMOUNT = 2_00_00_000   # 2 Crores
    CGTMSE_FEE_PERCENT = 0.0085       # 0.85%

    def __init__(self):
        self.flags: List[str] = []
        self.waterfall_steps: List[WaterfallStep] = []

    # ========== MAIN ANALYSIS FUNCTION ==========
    def analyze(self, cma_data: CMAModel, user_profile: UserProfile) -> CreditResult:
        """
        Main entry point for credit analysis.
        Returns a complete CreditResult with all ratios and recommendations.
        """
        self.flags = []
        self.waterfall_steps = []
        
        # Check if we have any data
        if not cma_data.get_latest_financials():
            return self._create_rejection_result(
                user_profile.deal_id,
                "No financial data available for analysis"
            )
        
        # Add optimism warning if triggered
        if cma_data.optimism_warning:
            self.flags.append(cma_data.optimism_warning)
        
        # 1. Calculate Core Ratios
        cr, cr_status = self._calculate_current_ratio(cma_data)
        tol_tnw, leverage_status = self._calculate_leverage(cma_data, user_profile)
        yearly_dscr, avg_dscr, dscr_status = self._calculate_dscr(cma_data)
        
        # 2. Calculate MPBF (Maximum Permissible Bank Finance)
        mpbf_data = self._calculate_mpbf(cma_data, user_profile.loan_amount_requested)
        mpbf = mpbf_data["mpbf"]
        
        # 3. Run Product Router (Waterfall)
        scheme, status, rejection_reasons = self._determine_eligible_scheme(
            cma_data, user_profile, cr, tol_tnw, avg_dscr
        )
        
        # 4. Calculate Eligible Sanction Amount (Based on Figures)
        # Logic: Lower of (MPBF, Requested Amount)
        # This represents the "amount of loan which can be sanctioned based on the figures"
        eligible_amount = min(mpbf, user_profile.loan_amount_requested)
        
        # If rejected, we typically sanction 0, but for "Eligibility" display we might want to show what was possible mathematically?
        # Standard practice: If Rejected, sanctioned = 0.
        recommended = eligible_amount if status != EligibilityStatus.REJECTED else 0
        
        # 5. Build visualization data
        radar_data = {
            "user_cr": cr,
            "benchmark_cr": self.CR_ELIGIBLE_THRESHOLD,
            "user_tol_tnw": tol_tnw,
            "benchmark_tol_tnw": self.TOL_TNW_HIGH_RISK,
            "user_dscr": avg_dscr,
            "benchmark_dscr": self.DSCR_APPROVE_THRESHOLD
        }
        
        # 6. Determine scheme-specific eligibility
        cgtmse_eligible = (
            user_profile.loan_amount_requested <= self.CGTMSE_MAX_AMOUNT and
            not user_profile.has_collateral and
            cr >= self.CR_RESTRICTED_THRESHOLD
        )
        
        mudra_eligible = user_profile.loan_amount_requested <= self.MUDRA_MAX_AMOUNT
        
        cgss_eligible = (
            user_profile.dpiit_recognized and
            user_profile.loan_amount_requested > self.CGTMSE_MAX_AMOUNT
        )
        
        # Calculate guarantee fee if CGTMSE eligible
        guarantee_fee = 0.0
        if scheme == SchemeType.CGTMSE:
            guarantee_fee = recommended * self.CGTMSE_FEE_PERCENT
        
        return CreditResult(
            deal_id=user_profile.deal_id,
            eligible_scheme=scheme,
            status=status,
            max_permissible_limit=mpbf,
            recommended_amount=recommended,
            
            current_ratio=cr,
            current_ratio_status=cr_status,
            
            tol_tnw=tol_tnw,
            leverage_status=leverage_status,
            
            avg_dscr=avg_dscr,
            dscr_status=dscr_status,
            yearly_dscr=yearly_dscr,
            
            flags=self.flags,
            compliance_notes=[],
            rejection_reasons=rejection_reasons,
            
            radar_chart_data=radar_data,
            working_capital_analysis=mpbf_data,
            waterfall_data=self.waterfall_steps,
            
            cgtmse_eligible=cgtmse_eligible,
            mudra_eligible=mudra_eligible,
            cgss_eligible=cgss_eligible,
            
            guarantee_fee_percent=self.CGTMSE_FEE_PERCENT * 100 if scheme == SchemeType.CGTMSE else 0,
            guarantee_fee_amount=guarantee_fee
        )

    # ========== A. LIQUIDITY ENGINE ==========
    def _calculate_current_ratio(self, data: CMAModel) -> Tuple[float, str]:
        """
        Current Ratio = Current Assets / Current Liabilities
        
        Logic:
        - CR < 1.0: Ineligible (Critical Risk)
        - 1.0 <= CR < 1.33: Restricted (Govt Schemes only)
        - CR >= 1.33: Eligible (Standard Credit)
        """
        latest = data.get_latest_financials()
        if not latest or latest.current_liabilities == 0:
            return 0.0, "Ineligible"
        
        cr = round(latest.current_assets / latest.current_liabilities, 2)
        
        if cr < self.CR_RESTRICTED_THRESHOLD:
            status = "Ineligible"
            self.flags.append(f"Critical: Current Ratio ({cr}) below 1.0 - High liquidity risk")
        elif cr < self.CR_ELIGIBLE_THRESHOLD:
            status = "Restricted"
            self.flags.append(f"Warning: Current Ratio ({cr}) below 1.33 - Eligible only for Govt schemes")
        else:
            status = "Eligible"
        
        return cr, status

    # ========== B. SOLVENCY ENGINE ==========
    def _calculate_leverage(self, data: CMAModel, profile: UserProfile = None) -> Tuple[float, str]:
        """
        TOL/TNW = Total Outside Liabilities / Tangible Net Worth
        
        Logic:
        - > 4.0: Critical Risk (Hard Reject)
        - > 3.0: High Risk (Reject unless Startup scheme)
        - <= 3.0: Acceptable
        
        Exception: If DPIIT Recognized, Critical Threshold relaxed to 4.5x [Venture Debt Norms]
        """
        latest = data.get_latest_financials()
        if not latest or latest.tangible_net_worth == 0:
            return 99.9, "Critical"
        
        tol = latest.total_outside_liabilities
        tnw = latest.tangible_net_worth
        
        ratio = round(tol / tnw, 2)
        
        # Determine strictness based on profile
        critical_threshold = self.TOL_TNW_CRITICAL
        if profile and profile.dpiit_recognized:
            critical_threshold = 4.5  # Relaxed for Startups
            if ratio > critical_threshold:
                 self.flags.append(f"Info: Leverage ({ratio}x) evaluated against relaxed startup threshold (4.5x)")

        if ratio > critical_threshold:
            status = "Critical"
            self.flags.append(f"Critical: Leverage ({ratio}x) exceeds limit ({critical_threshold}) - Hard reject")
        elif ratio > self.TOL_TNW_HIGH_RISK:
            # If it's a startup between 3.0 and 4.5, it's "High Risk" but not "Critical" (Reject)
            # This allows it to pass the Hard Reject check in Waterfall (which checks > critical)
            # but might still fail standard BIL checks.
            status = "High Risk"
            self.flags.append(f"Warning: Leverage ({ratio}x) exceeds 3.0 - High debt burden")
        else:
            status = "Safe"
        
        return ratio, status

    # ========== C. REPAYMENT ENGINE (DSCR) ==========
    def _calculate_dscr(self, data: CMAModel) -> Tuple[List[Dict], float, str]:
        """
        DSCR = (PAT + Depreciation + Interest) / (Interest + Principal Repayment)
        
        For projections, we calculate DSCR and average (ADSCR).
        
        Logic:
        - ADSCR < 1.15: Reject Term Loan
        - ADSCR >= 1.25: Approve Term Loan
        - 1.15 <= ADSCR < 1.25: Conditional
        """
        yearly_dscr = []
        
        if not data.projected_financials:
            # Use audited if no projections
            if data.audited_financials:
                for year_data in data.audited_financials[-2:]:  # Last 2 years
                    dscr = self._compute_single_dscr(year_data)
                    yearly_dscr.append({
                        "year": year_data.year,
                        "dscr": dscr,
                        "tier": year_data.tier
                    })
            else:
                return [], 0.0, "No Data"
        else:
            for year_data in data.projected_financials:
                dscr = self._compute_single_dscr(year_data)
                yearly_dscr.append({
                    "year": year_data.year,
                    "dscr": dscr,
                    "tier": year_data.tier
                })
        
        if not yearly_dscr:
            return [], 0.0, "No Data"
        
        avg_dscr = round(sum(d["dscr"] for d in yearly_dscr) / len(yearly_dscr), 2)
        
        if avg_dscr < self.DSCR_REJECT_THRESHOLD:
            status = "Rejected"
            self.flags.append(f"Critical: Average DSCR ({avg_dscr}) below 1.15 - Cannot service debt")
        elif avg_dscr < self.DSCR_APPROVE_THRESHOLD:
            status = "Conditional"
            self.flags.append(f"Warning: Average DSCR ({avg_dscr}) below 1.25 - Marginal repayment capacity")
        else:
            status = "Approved"
        
        return yearly_dscr, avg_dscr, status

    def _compute_single_dscr(self, year_data: YearData) -> float:
        """Compute DSCR for a single year"""
        # Cash available for debt service
        cash_accrual = year_data.pat + year_data.depreciation + year_data.interest_expense
        
        # Debt obligation (simplified - assumes interest only for now)
        # In production, this would include principal repayment schedule
        debt_obligation = year_data.interest_expense if year_data.interest_expense > 0 else 1
        
        return round(cash_accrual / debt_obligation, 2)

    # ========== D. MPBF CALCULATOR (RBI-Compliant) ==========
    def _calculate_mpbf(self, data: CMAModel, requested_amount: float) -> Dict[str, Any]:
        """
        Maximum Permissible Bank Finance - RBI Guidelines
        
        Method Selection (based on Projected Annual Turnover):
        - Turnover < ₹5 Crores: Nayak Committee (Turnover Method)
        - Turnover >= ₹5 Crores: Tandon Committee (Method II - Asset-Based)
        
        Returns dict with calculation details and visualization chart data.
        """
        projected = data.projected_financials[0] if data.projected_financials else None
        provisional = data.provisional_financials
        latest = data.get_latest_financials()
        
        if not latest:
            return self._empty_mpbf_result()
        
        # Get projected turnover for method selection
        projected_turnover = projected.revenue if projected else latest.revenue
        
        # Conservative handling: Compare provisional vs projected
        conservative_flag = None
        if provisional and projected:
            prov_revenue = provisional.revenue
            proj_revenue = projected.revenue
            if prov_revenue > 0 and proj_revenue > 0:
                diff_percent = abs(proj_revenue - prov_revenue) / prov_revenue
                if diff_percent > 0.20:  # >20% difference
                    # Use the lower figure
                    projected_turnover = min(prov_revenue, proj_revenue)
                    conservative_flag = f"Provisional (₹{prov_revenue/1e7:.2f}Cr) vs Projected (₹{proj_revenue/1e7:.2f}Cr) differ by {diff_percent*100:.1f}%. Using lower value."
                    self.flags.append(f"⚠️ Conservative: {conservative_flag}")
        
        # ========== METHOD ROUTER ==========
        if projected_turnover < self.TURNOVER_METHOD_THRESHOLD:
            # Use Nayak Committee (Turnover Method)
            result = self._nayak_turnover_method(projected_turnover)
        else:
            # Use Tandon Committee (Method II)
            result = self._tandon_method_ii(latest)
        
        # Add conservative flag if applicable
        if conservative_flag:
            result["conservative_adjustment"] = conservative_flag
        
        # Round MPBF down to nearest ₹1,000
        result["eligible_bank_finance"] = self._round_down_to_thousand(result["eligible_bank_finance"])
        
        return result
    
    def _nayak_turnover_method(self, projected_turnover: float) -> Dict[str, Any]:
        """
        Nayak Committee (Turnover Method) - for units with turnover < ₹5 Crores
        
        Formula:
        - Gross WC Requirement = 25% of Projected Turnover
        - Promoter Margin = 5% of Projected Turnover
        - MPBF = Gross WC - Promoter Margin = 20% of Projected Turnover
        """
        gross_wc_requirement = projected_turnover * self.NAYAK_GROSS_WC_PERCENT
        promoter_contribution = projected_turnover * self.NAYAK_PROMOTER_MARGIN
        eligible_bank_finance = gross_wc_requirement - promoter_contribution
        
        self.flags.append(f"MPBF (Turnover Method - Nayak): ₹{eligible_bank_finance:,.0f}")
        
        return {
            "method_used": "Turnover Method (Nayak Committee)",
            "method_code": "NAYAK",
            "projected_turnover": projected_turnover,
            "gross_working_capital_need": gross_wc_requirement,
            "promoter_contribution_5_percent": promoter_contribution,
            "eligible_bank_finance": eligible_bank_finance,
            # Visualization data for bar chart
            "chart_data": [
                {"label": "Total Requirement (25%)", "value": gross_wc_requirement, "type": "primary"},
                {"label": "Less: Promoter Margin (5%)", "value": -promoter_contribution, "type": "warning"},
                {"label": "Bank Finance (20%)", "value": eligible_bank_finance, "type": "success"}
            ],
            # Legacy fields for backward compatibility
            "gross_wc": gross_wc_requirement,
            "margin": promoter_contribution,
            "mpbf": eligible_bank_finance,
            "method": "Turnover (20% of Sales)"
        }
    
    def _tandon_method_ii(self, latest: 'YearData') -> Dict[str, Any]:
        """
        Tandon Committee (Method II) - for units with turnover >= ₹5 Crores
        
        Formula:
        - Total Current Assets (TCA) = Inventory + Receivables + Cash + Advances
        - Other Current Liabilities (OCL) = Trade Creditors + Statutory Dues (excluding bank borrowings)
        - Working Capital Gap (WCG) = TCA - OCL
        - Margin = 25% of TCA
        - MPBF = WCG - Margin (if positive, else 0)
        """
        total_current_assets = latest.current_assets
        
        # OCL = Current Liabilities - Short Term Bank Borrowings
        other_current_liabilities = max(0, latest.current_liabilities - latest.short_term_debt)
        
        working_capital_gap = total_current_assets - other_current_liabilities
        margin_on_assets = total_current_assets * self.TANDON_MARGIN_PERCENT
        
        eligible_bank_finance = working_capital_gap - margin_on_assets
        
        # Validation: MPBF cannot be negative
        surplus_liquidity = False
        if eligible_bank_finance < 0:
            surplus_liquidity = True
            self.flags.append("ℹ️ Surplus Liquidity: Working Capital Gap covered by OCL and margin. No bank finance needed.")
            eligible_bank_finance = 0
        else:
            self.flags.append(f"MPBF (Method II - Tandon): ₹{eligible_bank_finance:,.0f}")
        
        return {
            "method_used": "MPBF Method II (Tandon Committee)",
            "method_code": "TANDON",
            "total_current_assets": total_current_assets,
            "other_current_liabilities": other_current_liabilities,
            "working_capital_gap": working_capital_gap,
            "margin_on_assets_25_percent": margin_on_assets,
            "eligible_bank_finance": eligible_bank_finance,
            "surplus_liquidity": surplus_liquidity,
            # Visualization data for waterfall chart
            "chart_data": [
                {"label": "Total Current Assets", "value": total_current_assets, "type": "primary"},
                {"label": "Less: Other Current Liabilities", "value": -other_current_liabilities, "type": "danger"},
                {"label": "Less: Margin (25% of TCA)", "value": -margin_on_assets, "type": "warning"},
                {"label": "Bank Finance (MPBF)", "value": eligible_bank_finance, "type": "success"}
            ],
            # Legacy fields for backward compatibility
            "gross_wc": total_current_assets,
            "other_current_liabilities": other_current_liabilities,
            "wc_gap": working_capital_gap,
            "margin": margin_on_assets,
            "mpbf": eligible_bank_finance,
            "method": "MPBF Method II (Tandon)"
        }
    
    def _round_down_to_thousand(self, value: float) -> float:
        """Round down to nearest ₹1,000"""
        return (int(value) // 1000) * 1000
    
    def _empty_mpbf_result(self) -> Dict[str, Any]:
        """Return empty result when no financial data available"""
        return {
            "method_used": "N/A",
            "method_code": "NONE",
            "eligible_bank_finance": 0.0,
            "gross_wc": 0.0,
            "margin": 0.0,
            "mpbf": 0.0,
            "chart_data": [],
            "error": "No financial data available for MPBF calculation"
        }

    # ========== 3. PRODUCT ROUTER (WATERFALL) ==========
    def _determine_eligible_scheme(
        self,
        data: CMAModel,
        profile: UserProfile,
        cr: float,
        tol_tnw: float,
        avg_dscr: float
    ) -> Tuple[SchemeType, EligibilityStatus, List[str]]:
        """
        Waterfall filter to determine the best-fit scheme.
        Runs ALL filters for complete UI display, tracks first eligible scheme.
        """
        rejection_reasons = []
        step = 1
        hard_rejection = False
        eligible_scheme = None
        
        # ===== GATE 1: POLICY & MARKET (Hard Rejections) =====
        
        # Check Critical Leverage
        leverage_pass = tol_tnw <= self.TOL_TNW_CRITICAL
        if leverage_pass:
            self._add_waterfall_step(step, "Leverage Check", "TOL/TNW <= 4.0", "Pass", f"TOL/TNW = {tol_tnw}")
        else:
            self._add_waterfall_step(step, "Leverage Check", "TOL/TNW <= 4.0", "Fail", f"TOL/TNW = {tol_tnw}")
            rejection_reasons.append(f"Leverage ratio ({tol_tnw}x) exceeds maximum threshold of 4.0")
            hard_rejection = True
        step += 1
        
        # Check Critical Liquidity
        liquidity_pass = cr >= self.CR_RESTRICTED_THRESHOLD
        if liquidity_pass:
            self._add_waterfall_step(step, "Liquidity Check", "CR >= 1.0", "Pass", f"CR = {cr}")
        else:
            self._add_waterfall_step(step, "Liquidity Check", "CR >= 1.0", "Fail", f"CR = {cr}")
            rejection_reasons.append(f"Current Ratio ({cr}) below minimum threshold of 1.0")
            hard_rejection = True
        step += 1
        
        # ===== GATE 2: DATA INTEGRITY =====
        
        # Check DSCR
        dscr_pass = avg_dscr >= self.DSCR_REJECT_THRESHOLD
        if dscr_pass:
            self._add_waterfall_step(step, "DSCR Check", "DSCR >= 1.15", "Pass", f"DSCR = {avg_dscr}")
        else:
            self._add_waterfall_step(step, "DSCR Check", "DSCR >= 1.15", "Fail", f"DSCR = {avg_dscr}")
        step += 1
        
        # ===== GATE 3: SCHEME ELIGIBILITY =====
        
        # Filter 1: Mudra (Micro)
        mudra_pass = False
        if profile.loan_amount_requested <= self.MUDRA_MAX_AMOUNT:
            if profile.entity_type in ["Proprietorship", "Partnership"]:
                self._add_waterfall_step(step, "Mudra Yojana", "Request <= ₹10L + Non-Corporate", "Pass", "Eligible for Mudra")
                mudra_pass = True
                if not hard_rejection and not eligible_scheme:
                    eligible_scheme = SchemeType.MUDRA
            else:
                self._add_waterfall_step(step, "Mudra Yojana", "Non-Corporate Check", "Fail", f"Entity: {profile.entity_type}")
        else:
            self._add_waterfall_step(step, "Mudra Yojana", "Request <= ₹10L", "Fail", f"Request: ₹{profile.loan_amount_requested:,.0f}")
        step += 1
        
        # Filter 2: CGTMSE (Collateral-Free)
        cgtmse_pass = False
        if profile.loan_amount_requested <= self.CGTMSE_MAX_AMOUNT and not profile.has_collateral:
            excluded_industries = ["agriculture", "retail trade", "educational", "self help groups"]
            if profile.industry_sector.lower() not in excluded_industries:
                self._add_waterfall_step(step, "CGTMSE", "Request <= ₹2Cr + No Collateral", "Pass", "Eligible for CGTMSE")
                cgtmse_pass = True
                if not hard_rejection and not eligible_scheme:
                    eligible_scheme = SchemeType.CGTMSE
            else:
                self._add_waterfall_step(step, "CGTMSE", "Industry check", "Fail", f"Industry: {profile.industry_sector}")
        else:
            reason = "Has Collateral" if profile.has_collateral else f"Request: ₹{profile.loan_amount_requested:,.0f}"
            self._add_waterfall_step(step, "CGTMSE", "Request <= ₹2Cr + No Collateral", "Fail", reason)
        step += 1
        
        # Filter 3: CGSS (Venture Debt for DPIIT Startups)
        cgss_pass = False
        if profile.dpiit_recognized:
            if data.projected_financials and len(data.projected_financials) > 0:
                latest = data.get_latest_financials()
                proj = data.projected_financials[0]
                if latest and latest.revenue > 0:
                    growth = (proj.revenue - latest.revenue) / latest.revenue
                    if growth > 0.20:
                        self._add_waterfall_step(step, "CGSS (Startup India)", "DPIIT + Growth > 20%", "Pass", "Venture Debt Eligible")
                        cgss_pass = True
                        if not hard_rejection and not eligible_scheme:
                            eligible_scheme = SchemeType.CGSS
                    else:
                        self._add_waterfall_step(step, "CGSS (Startup India)", "Growth > 20%", "Fail", f"Growth = {growth*100:.1f}%")
                else:
                    self._add_waterfall_step(step, "CGSS (Startup India)", "Revenue Data", "Fail", "No revenue data")
            else:
                self._add_waterfall_step(step, "CGSS (Startup India)", "Projections", "Fail", "No projected financials")
        else:
            self._add_waterfall_step(step, "CGSS (Startup India)", "DPIIT Recognized", "Fail", "Not DPIIT registered")
        step += 1
        
        # Filter 4: New Entity Loan
        new_entity_pass = False
        if 1 <= profile.vintage_years <= 3 and profile.has_collateral:
            self._add_waterfall_step(step, "New Entity Loan", "Vintage 1-3 years + Collateral", "Pass", "Bridge Loan Eligible")
            new_entity_pass = True
            if not hard_rejection and not eligible_scheme:
                eligible_scheme = SchemeType.NEW_ENTITY
        else:
            reason = f"Vintage: {profile.vintage_years}y, Collateral: {profile.has_collateral}"
            self._add_waterfall_step(step, "New Entity Loan", "Vintage 1-3 years + Collateral", "Fail", reason)
        step += 1
        
        # Filter 5: BIL (Standard - Established Business)
        bil_pass = False
        if profile.vintage_years > 3 and profile.is_profitable_2_years:
            if avg_dscr >= self.DSCR_APPROVE_THRESHOLD:
                self._add_waterfall_step(step, "Business Installment Loan", "Vintage > 3y + Profitable + DSCR >= 1.25", "Pass", "BIL Eligible")
                bil_pass = True
                if not hard_rejection and not eligible_scheme:
                    eligible_scheme = SchemeType.BIL
            else:
                self._add_waterfall_step(step, "Business Installment Loan", "DSCR >= 1.25", "Fail", f"DSCR = {avg_dscr}")
        else:
            reason = f"Vintage: {profile.vintage_years}y, Profitable 2Y: {profile.is_profitable_2_years}"
            self._add_waterfall_step(step, "Business Installment Loan", "Vintage > 3y + Profitable", "Fail", reason)
        step += 1
        
        # ===== GATE 4: FINAL VERDICT =====
        
        if hard_rejection:
            self._add_waterfall_step(step, "Final Verdict", "Hard rejection check", "Fail", "Does not meet basic eligibility criteria")
            return SchemeType.ADVISORY, EligibilityStatus.REJECTED, rejection_reasons
        
        if eligible_scheme:
            self._add_waterfall_step(step, "Final Verdict", "Scheme matched", "Pass", f"Eligible for {eligible_scheme.value}")
            return eligible_scheme, EligibilityStatus.APPROVED, []
        
        # Fallback: Advisory Only
        self._add_waterfall_step(step, "Final Verdict", "No scheme matched", "Referral", "Advisory services recommended")
        rejection_reasons.append("No standard lending scheme matched the applicant's profile")
        rejection_reasons.append("Recommended: Open iStartup 2.0 Current Account for banking relationship")
        
        return SchemeType.ADVISORY, EligibilityStatus.REFERRAL, rejection_reasons

    def _add_waterfall_step(self, step: int, scheme: str, rule: str, result: str, reason: str):
        """Helper to add a waterfall step"""
        self.waterfall_steps.append(WaterfallStep(
            step_number=step,
            scheme_name=scheme,
            rule_checked=rule,
            result=result,
            reason=reason
        ))

    def _create_rejection_result(self, deal_id: str, reason: str) -> CreditResult:
        """Create a rejection result with minimal data"""
        return CreditResult(
            deal_id=deal_id,
            eligible_scheme=SchemeType.ADVISORY,
            status=EligibilityStatus.REJECTED,
            max_permissible_limit=0,
            recommended_amount=0,
            current_ratio=0,
            current_ratio_status="No Data",
            tol_tnw=0,
            leverage_status="No Data",
            avg_dscr=0,
            dscr_status="No Data",
            rejection_reasons=[reason],
            flags=[reason]
        )

    # ========== 4. EXCEPTION/OVERRIDE SYSTEM ==========
    def apply_override(
        self,
        deal_id: str,
        rule_id: str,
        justification: str,
        analyst_id: str,
        bypass_flags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a human-in-the-loop override to a credit decision.
        
        1. Logs the override to compliance audit
        2. Re-runs analysis with specified bypasses
        3. Returns new result with compliance note
        """
        # 1. Fetch existing analysis
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise ValueError(f"Deal {deal_id} not found")
        
        deal_data = deal_doc.to_dict()
        existing_analysis = deal_data.get('credit_analysis', {})
        
        # 2. Log to audit
        audit_log = OverrideAuditLog(
            deal_id=deal_id,
            rule_id=rule_id,
            original_status=existing_analysis.get('status', 'Unknown'),
            new_status="Conditional",
            justification=justification,
            analyst_id=analyst_id
        )
        
        # Save audit log to Firestore
        db.collection('compliance_audit_log').add(audit_log.dict())
        
        # 3. Update the credit analysis with compliance note
        compliance_note = f"Approved via Exception by [{analyst_id}]: {justification}"
        
        updated_analysis = existing_analysis.copy()
        updated_analysis['status'] = "Conditional"
        updated_analysis['compliance_notes'] = updated_analysis.get('compliance_notes', []) + [compliance_note]
        updated_analysis['flags'] = updated_analysis.get('flags', []) + [f"Override applied: {rule_id}"]
        
        # 4. Save updated analysis
        deal_ref.update({
            'credit_analysis': updated_analysis
        })
        
        return {
            "success": True,
            "deal_id": deal_id,
            "new_status": "Conditional",
            "compliance_note": compliance_note,
            "audit_id": audit_log.timestamp
        }


# ========== HELPER FUNCTION FOR PARSING CMA DATA ==========
def parse_cma_to_model(raw_cma_data: Dict[str, Any]) -> CMAModel:
    """
    Convert raw CMA data (from Gemini extraction) to CMAModel.
    
    The raw CMA data has this structure:
    {
        "general_info": {...},
        "operating_statement": {"years": [...], "rows": [...]},
        "balance_sheet": {"years": [...], "rows": [...]}
    }
    
    We need to convert to:
    {
        "audited_financials": [YearData, ...],
        "projected_financials": [YearData, ...]
    }
    """
    audited = []
    provisional = None
    projected = []
    
    # CHECK: If the data is already in the structured format (from new Prompt)
    if "audited_financials" in raw_cma_data or "projected_financials" in raw_cma_data:
        try:
            print("✅ Detected pre-structured CMA data format.")
            import json
            print(f"📊 RAW CMA STRUCTURED INPUT:\n{json.dumps(raw_cma_data, indent=2, default=str)}")
            
            # Helper to normalize tier values
            def normalize_tier(item: dict) -> None:
                """Normalize tier values from Gemini to valid enum values"""
                tier = item.get("tier", "").lower() if item.get("tier") else ""
                if tier in ["estimated", "estimate", "current"]:
                    item["tier"] = TrustTier.PROVISIONAL
                elif tier in ["projected", "projection", "forecast", "target"]:
                    item["tier"] = TrustTier.PROJECTED
                elif tier in ["audited", "actual", "historical"]:
                    item["tier"] = TrustTier.AUDITED
            
            # 1. Audited
            raw_audited = raw_cma_data.get("audited_financials", [])
            print(f"📋 Audited financials count: {len(raw_audited) if isinstance(raw_audited, list) else 'not a list'}")
            if isinstance(raw_audited, list):
                for i, item in enumerate(raw_audited):
                    normalize_tier(item)
                    if "tier" not in item: item["tier"] = TrustTier.AUDITED
                    try: 
                        yd = YearData(**item)
                        audited.append(yd)
                        print(f"   ✅ Audited[{i}]: year={yd.year}, CA={yd.current_assets}, CL={yd.current_liabilities}, TNW={yd.tangible_net_worth}")
                    except Exception as e: 
                        print(f"   ❌ Skipping invalid audited item {i}: {e}")
                        print(f"      Item data: {item}")
            
            # 2. Provisional
            raw_prov = raw_cma_data.get("provisional_financials")
            if isinstance(raw_prov, dict):
                normalize_tier(raw_prov)
                if "tier" not in raw_prov: raw_prov["tier"] = TrustTier.PROVISIONAL
                try: 
                    provisional = YearData(**raw_prov)
                    print(f"   ✅ Provisional: year={provisional.year}")
                except Exception as e: print(f"   ❌ Invalid provisional item: {e}")
            elif isinstance(raw_prov, list) and raw_prov:
                # Handle case where provisional is a list
                item = raw_prov[0]
                normalize_tier(item)
                if "tier" not in item: item["tier"] = TrustTier.PROVISIONAL
                try: 
                    provisional = YearData(**item)
                    print(f"   ✅ Provisional (from list): year={provisional.year}")
                except Exception as e: print(f"   ❌ Invalid provisional item from list: {e}")

            # 3. Projected
            raw_proj = raw_cma_data.get("projected_financials", [])
            print(f"📋 Projected financials count: {len(raw_proj) if isinstance(raw_proj, list) else 'not a list'}")
            if isinstance(raw_proj, list):
                for i, item in enumerate(raw_proj):
                    normalize_tier(item)
                    if "tier" not in item: item["tier"] = TrustTier.PROJECTED
                    try: 
                        yd = YearData(**item)
                        projected.append(yd)
                        print(f"   ✅ Projected[{i}]: year={yd.year}")
                    except Exception as e: 
                        print(f"   ❌ Skipping invalid projected item {i}: {e}")
            
            print(f"✅ Parsed Structured CMA: {len(audited)} audited, {1 if provisional else 0} provisional, {len(projected)} projected")
            
            cma_model = CMAModel(
                audited_financials=audited,
                provisional_financials=provisional,
                projected_financials=projected
            )
            latest = cma_model.get_latest_financials()
            if latest:
                print(f"📈 Latest Financials: year={latest.year}, CA={latest.current_assets}, CL={latest.current_liabilities}, TOL={latest.total_outside_liabilities}, TNW={latest.tangible_net_worth}")
            else:
                print(f"⚠️ get_latest_financials() returned None!")
            
            return cma_model
        except Exception as e:
            print(f"❌ Error parsing structured data: {e}. Falling back to legacy parser.")
            import traceback
            traceback.print_exc()

    # Get years from operating statement or balance sheet
    operating = raw_cma_data.get('operating_statement', {})
    balance = raw_cma_data.get('balance_sheet', {})
    
    op_rows = operating.get('rows', [])
    bs_rows = balance.get('rows', [])
    
    years = operating.get('years') or balance.get('years') or []
    
    # Rescue: If years missing but rows exist, try to infer
    if not years and (op_rows or bs_rows):
        print("⚠️ 'years' metadata missing, attempting to infer from data rows...")
        max_cols = 0
        for row in op_rows + bs_rows:
            if row.get('values'):
                max_cols = max(max_cols, len(row.get('values')))
        
        if max_cols > 0:
            # Heuristic: Assume typical 5 year CMA (2 past, 3 future)
            # Or just generic labeling
            current_year = 2024 # Approximate base
            years = []
            for i in range(max_cols):
                # If 5 cols: Audited, Audited, Prov/Est, Proj, Proj
                # Simple Fallback: Just label them sequentially
                # Better: Guess Audited if index < 2?
                offset = i - 2 # -2, -1, 0, 1, 2
                label = f"FY{current_year + offset}"
                if i < max_cols - 2:
                    label += " (Audited)" 
                else:
                    label += " (Projected)"
                years.append(label)
            print(f"✅ Inferred years: {years}")

    if not years:
        print("❌ No years found in CMA data and could not infer from rows.")
        return CMAModel(audited_financials=[], projected_financials=[])
    
    # Create mapping helpers
    def get_row_value(rows: list, particulars_keywords: list, year_index: int) -> float:
        """Find a row by keywords and return value at given year index"""
        for row in rows:
            particulars = row.get('particulars', '').lower()
            if any(kw.lower() in particulars for kw in particulars_keywords):
                values = row.get('values', [])
                if year_index < len(values):
                    val = values[year_index]
                    try:
                        # Handle string values with commas, brackets, etc
                        if isinstance(val, str):
                            val = val.replace(',', '').replace('(', '-').replace(')', '').strip()
                            if val in ['', '-', 'N/A', 'nil', 'null']:
                                return 0.0
                        return float(val)
                    except (ValueError, TypeError):
                        pass # return 0.0 at end
        return 0.0
    
    # Process each year
    for idx, year_label in enumerate(years):
        year_lower = year_label.lower()
        
        # Determine tier based on year label
        if 'audited' in year_lower or 'actual' in year_lower:
            tier = TrustTier.AUDITED
        elif 'estimated' in year_lower or 'provisional' in year_lower:
            tier = TrustTier.PROVISIONAL
        elif 'projected' in year_lower or 'target' in year_lower:
            tier = TrustTier.PROJECTED
        else:
            # Default based on position - first 1-2 are typically audited
            tier = TrustTier.AUDITED if idx < 2 else TrustTier.PROJECTED
        
        # Extract values from Operating Statement
        revenue = get_row_value(op_rows, ['revenue', 'turnover', 'sales', 'income from operations'], idx)
        pat = get_row_value(op_rows, ['profit after tax', 'pat', 'net profit'], idx)
        depreciation = get_row_value(op_rows, ['depreciation', 'amortization', 'depreciation & amortization'], idx)
        interest = get_row_value(op_rows, ['interest', 'finance cost', 'interest expense'], idx)
        
        # Extract values from Balance Sheet
        current_assets = get_row_value(bs_rows, ['current assets', 'total current assets'], idx)
        current_liabilities = get_row_value(bs_rows, ['current liabilities', 'total current liabilities'], idx)
        long_term_debt = get_row_value(bs_rows, ['term loan', 'long term borrowing', 'long term debt'], idx)
        short_term_debt = get_row_value(bs_rows, ['working capital', 'short term borrowing', 'cc/od', 'bank borrowing'], idx)
        net_worth = get_row_value(bs_rows, ['net worth', 'equity', 'shareholders fund', 'tangible net worth', 'tnw'], idx)
        fixed_assets = get_row_value(bs_rows, ['fixed assets', 'property plant', 'ppe', 'gross block'], idx)
        
        # Create YearData
        year_data = YearData(
            year=year_label,
            tier=tier,
            revenue=revenue,
            pat=pat,
            depreciation=depreciation,
            interest_expense=interest,
            current_assets=current_assets,
            current_liabilities=current_liabilities,
            long_term_debt=long_term_debt,
            short_term_debt=short_term_debt,
            tangible_net_worth=net_worth,
            fixed_assets=fixed_assets
        )
        
        # Add to appropriate list based on tier
        if tier == TrustTier.AUDITED:
            audited.append(year_data)
        elif tier == TrustTier.PROVISIONAL:
            provisional = year_data
        else:
            projected.append(year_data)
    
    print(f"Parsed CMA: {len(audited)} audited, {1 if provisional else 0} provisional, {len(projected)} projected years")
    
    return CMAModel(
        audited_financials=audited,
        provisional_financials=provisional,
        projected_financials=projected
    )


# ========== SYSTEM PROMPT FOR CMA EXTRACTION ==========
CMA_EXTRACTION_SYSTEM_PROMPT = """
You are a Senior Credit Analyst at ICICI Bank. Your task is to extract financial data from the provided CMA Report (Excel/PDF) into a structured JSON format.

**STRICT RULES:**

1. **CLASSIFY YEARS**: Identify each column as one of:
   - "audited" - If marked as "Audited", "Actual", or year is in the past and verified
   - "provisional" - If marked as "Estimated", "Provisional", or current year estimate
   - "projected" - If marked as "Projected", "Target", or future year

2. **STANDARDIZE FIELDS**: Map the following to exact keys:
   - Revenue/Turnover/Sales → "revenue"
   - Profit After Tax/PAT/Net Profit → "pat"
   - Depreciation/Depreciation & Amortization → "depreciation"
   - Interest/Finance Costs/Interest Expense → "interest_expense"
   - Current Assets/Total Current Assets → "current_assets"
   - Current Liabilities/Total CL → "current_liabilities"
   - Term Loans/Long Term Debt → "long_term_debt"
   - Working Capital Loans/CC/OD → "short_term_debt"
   - Net Worth/Equity/TNW → "tangible_net_worth"
   - Fixed Assets/PPE → "fixed_assets"

3. **UNITS**: Convert ALL numbers to **INR absolute values** (not in Lakhs/Crores).
   - If the document says "in Lakhs", multiply by 100,000
   - If the document says "in Crores", multiply by 10,000,000
   - If no unit specified, assume absolute INR

4. **ZERO-FILL**: If a field is missing or blank, set it to 0.0 (not null, not "N/A")

5. **VERIFY TOL**: Total Outside Liabilities = long_term_debt + short_term_debt + (current_liabilities excluding bank borrowings)

**OUTPUT FORMAT (JSON):**
```json
{
  "audited_financials": [
    {
      "year": "FY23",
      "revenue": 50000000.0,
      "pat": 2000000.0,
      "depreciation": 500000.0,
      "interest_expense": 300000.0,
      "current_assets": 10000000.0,
      "current_liabilities": 8000000.0,
      "long_term_debt": 5000000.0,
      "short_term_debt": 3000000.0,
      "tangible_net_worth": 7000000.0,
      "fixed_assets": 15000000.0
    }
  ],
  "provisional_financials": {
    "year": "FY24E",
    "revenue": 65000000.0,
    ...
  },
  "projected_financials": [
    {
      "year": "FY25P",
      ...
    },
    {
      "year": "FY26P",
      ...
    }
  ]
}
```

Return ONLY the JSON, no explanations or markdown formatting.
"""
