"""
LenderAI Credit Engine - Logic Verification Script
Tests the deterministic credit logic against Master Prompt specifications.
"""

import sys
sys.path.insert(0, '.')

from services.credit_service import CreditService, parse_cma_to_model
from models.credit_schemas import (
    CMAModel, YearData, TrustTier, UserProfile, 
    SchemeType, EligibilityStatus
)

def print_result(name: str, passed: bool, details: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")
    if details:
        print(f"       └─ {details}")


def test_optimism_guardrail():
    """
    Master Prompt Rule: If Projected Revenue Growth > 300% YoY, cap at 50%.
    """
    print("\n" + "="*60)
    print("TEST 1: Optimism Guardrail (Shadow Cap)")
    print("="*60)
    
    # Create CMA with >300% growth projection
    audited = YearData(year="FY23", tier=TrustTier.AUDITED, revenue=10_00_000)  # 10 Lakhs
    projected = YearData(year="FY24P", tier=TrustTier.PROJECTED, revenue=50_00_000)  # 50 Lakhs = 400% growth
    
    cma = CMAModel(
        audited_financials=[audited],
        projected_financials=[projected]
    )
    
    # The guardrail should cap to 50% growth = 15 Lakhs
    expected_capped = 10_00_000 * 1.5  # 15 Lakhs
    actual = cma.projected_financials[0].revenue
    
    passed = abs(actual - expected_capped) < 1  # Allow rounding
    print_result(
        "400% growth capped to 50%",
        passed,
        f"Expected: ₹{expected_capped:,.0f}, Got: ₹{actual:,.0f}"
    )
    print_result(
        "Optimism Warning Flag Set",
        cma.optimism_warning is not None,
        cma.optimism_warning or "No warning"
    )
    return passed


def test_dpiit_leverage_exception():
    """
    Master Prompt Rule: DPIIT startups get relaxed leverage threshold (4.5x vs 4.0x).
    """
    print("\n" + "="*60)
    print("TEST 2: DPIIT Leverage Exception")
    print("="*60)
    
    # Create CMA with 4.2x leverage (would fail standard 4.0x, but pass 4.5x DPIIT)
    # TOL = long_term_debt + short_term_debt + current_liabilities = 12L + 8L + 22L = 42L
    # TNW = 10L
    # TOL/TNW = 4.2x
    audited = YearData(
        year="FY23", 
        tier=TrustTier.AUDITED,
        revenue=1_00_00_000,
        current_assets=50_00_000,
        current_liabilities=22_00_000,
        long_term_debt=12_00_000,
        short_term_debt=8_00_000,
        tangible_net_worth=10_00_000,
        pat=5_00_000,
        depreciation=1_00_000,
        interest_expense=2_00_000
    )
    
    cma = CMAModel(audited_financials=[audited])
    
    # Test with DPIIT = True (should pass)
    profile_dpiit = UserProfile(
        deal_id="test-dpiit",
        loan_amount_requested=50_00_000,
        dpiit_recognized=True,
        entity_type="Pvt Ltd",
        vintage_years=2,
        industry_sector="technology"
    )
    
    service = CreditService()
    result = service.analyze(cma, profile_dpiit)
    
    # With DPIIT, 4.2x should NOT trigger "Critical" leverage (threshold is 4.5x)
    # It should show "High Risk" instead of "Critical"
    passed = result.leverage_status != "Critical"
    print_result(
        "4.2x Leverage with DPIIT = NOT Critical (High Risk OK)",
        passed,
        f"Status: {result.status}, TOL/TNW: {result.tol_tnw}x, Leverage Status: {result.leverage_status}"
    )
    
    # Test with DPIIT = False (should fail at 4.0x, marking as "Critical")
    profile_no_dpiit = UserProfile(
        deal_id="test-no-dpiit",
        loan_amount_requested=50_00_000,
        dpiit_recognized=False,
        entity_type="Pvt Ltd",
        vintage_years=2,
        industry_sector="technology"
    )
    
    service2 = CreditService()
    result2 = service2.analyze(cma, profile_no_dpiit)
    
    # Without DPIIT, 4.2x SHOULD be Critical (> 4.0 threshold)
    passed2 = result2.leverage_status == "Critical"
    print_result(
        "4.2x Leverage without DPIIT = Critical",
        passed2,
        f"Status: {result2.status}, Leverage Status: {result2.leverage_status}"
    )
    
    return passed and passed2


def test_mudra_entity_exclusion():
    """
    Master Prompt Rule: Mudra is for Proprietorship/Partnership ONLY - excludes Pvt Ltd.
    """
    print("\n" + "="*60)
    print("TEST 3: Mudra Entity Exclusion")
    print("="*60)
    
    # Create minimal valid CMA
    audited = YearData(
        year="FY23", 
        tier=TrustTier.AUDITED,
        revenue=50_00_000,
        current_assets=20_00_000,
        current_liabilities=10_00_000,
        tangible_net_worth=15_00_000,
        pat=3_00_000,
        depreciation=50_000,
        interest_expense=1_00_000
    )
    cma = CMAModel(audited_financials=[audited])
    
    # Test Pvt Ltd requesting ₹8 Lakhs (< 10L threshold but wrong entity)
    profile_pvt = UserProfile(
        deal_id="test-mudra-pvt",
        loan_amount_requested=8_00_000,  # 8 Lakhs
        entity_type="Pvt Ltd",
        vintage_years=2,
        industry_sector="retail"
    )
    
    service = CreditService()
    result = service.analyze(cma, profile_pvt)
    
    # Pvt Ltd should NOT get Mudra
    passed_pvt = result.eligible_scheme != SchemeType.MUDRA
    print_result(
        "Pvt Ltd < 10L = NOT Mudra",
        passed_pvt,
        f"Entity: Pvt Ltd, Amount: ₹8L, Scheme: {result.eligible_scheme}"
    )
    
    # Test Proprietorship requesting ₹8 Lakhs (should get Mudra)
    profile_prop = UserProfile(
        deal_id="test-mudra-prop",
        loan_amount_requested=8_00_000,
        entity_type="Proprietorship",
        vintage_years=2,
        industry_sector="retail"
    )
    
    service2 = CreditService()
    result2 = service2.analyze(cma, profile_prop)
    
    passed_prop = result2.eligible_scheme == SchemeType.MUDRA
    print_result(
        "Proprietorship < 10L = Mudra Approved",
        passed_prop,
        f"Entity: Proprietorship, Amount: ₹8L, Scheme: {result2.eligible_scheme}"
    )
    
    return passed_pvt and passed_prop


def test_mpbf_method_selection():
    """
    Master Prompt Rule: < 5Cr uses Turnover Method, >= 5Cr uses Asset-Based.
    """
    print("\n" + "="*60)
    print("TEST 4: MPBF Method Selection")
    print("="*60)
    
    audited = YearData(
        year="FY23", 
        tier=TrustTier.AUDITED,
        revenue=10_00_00_000,  # 10 Crores
        current_assets=5_00_00_000,
        current_liabilities=2_00_00_000,
        short_term_debt=50_00_000,
        tangible_net_worth=3_00_00_000,
        pat=50_00_000,
        depreciation=10_00_000,
        interest_expense=20_00_000
    )
    cma = CMAModel(audited_financials=[audited])
    
    # Test small ticket (< 5Cr) - should use Turnover Method
    profile_small = UserProfile(
        deal_id="test-mpbf-small",
        loan_amount_requested=3_00_00_000,  # 3 Crores
        entity_type="Pvt Ltd",
        vintage_years=5,
        is_profitable_2_years=True
    )
    
    service = CreditService()
    result = service.analyze(cma, profile_small)
    
    turnover_method_used = "Turnover" in str(result.flags)
    print_result(
        "3Cr Request = Turnover Method",
        turnover_method_used,
        f"Flags: {[f for f in result.flags if 'MPBF' in f]}"
    )
    
    # Test large ticket (>= 5Cr) - should use Asset-Based Method
    profile_large = UserProfile(
        deal_id="test-mpbf-large",
        loan_amount_requested=6_00_00_000,  # 6 Crores
        entity_type="Pvt Ltd",
        vintage_years=5,
        is_profitable_2_years=True
    )
    
    service2 = CreditService()
    result2 = service2.analyze(cma, profile_large)
    
    asset_method_used = "Asset-Based" in str(result2.flags)
    print_result(
        "6Cr Request = Asset-Based Method",
        asset_method_used,
        f"Flags: {[f for f in result2.flags if 'MPBF' in f]}"
    )
    
    return turnover_method_used and asset_method_used


if __name__ == "__main__":
    print("\n" + "🏦 LenderAI Credit Engine - Logic Verification 🏦".center(60))
    print("="*60)
    
    results = []
    
    results.append(("Optimism Guardrail", test_optimism_guardrail()))
    results.append(("DPIIT Leverage Exception", test_dpiit_leverage_exception()))
    results.append(("Mudra Entity Exclusion", test_mudra_entity_exclusion()))
    results.append(("MPBF Method Selection", test_mpbf_method_selection()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    print(f"\nResult: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 All Master Prompt rules verified!")
        sys.exit(0)
    else:
        print("⚠️  Some rules failed verification. Review the output above.")
        sys.exit(1)
