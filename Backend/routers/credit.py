# Backend/routers/credit.py
"""
Credit Decision Engine API Endpoints.
Provides endpoints for credit analysis, overrides, and audit logs.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime
from google.cloud import firestore

from config.settings import settings
from config.auth import get_current_user
from models.credit_schemas import (
    CreditResult, UserProfile, OverrideRequest, CMAModel
)
from services.credit_service import CreditService, parse_cma_to_model

router = APIRouter(prefix="/api/v1/credit", tags=["credit"])

# Initialize Firestore
db = firestore.Client(project=settings.GCP_PROJECT_ID)


@router.get("/analyze/{deal_id}", response_model=CreditResult)
async def analyze_credit(
    deal_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Run credit analysis on an existing deal.
    Fetches CMA data from the deal and returns a complete credit assessment.
    """
    try:
        # Fetch deal
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        # Verify ownership
        if deal_data.get('metadata', {}).get('user_id') != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if CMA data exists
        raw_cma = deal_data.get('cma_data')
        if not raw_cma:
            raise HTTPException(
                status_code=400, 
                detail="CMA data not available. Please upload a CMA report first."
            )
        
        # Parse CMA data to model
        cma_model = parse_cma_to_model(raw_cma)
        
        # Build user profile from deal metadata
        metadata = deal_data.get('metadata', {})
        memo = deal_data.get('memo', {}).get('draft_v1', {})
        
        # Extract financial ask from memo
        financials = memo.get('financials', {})
        funding_ask = financials.get('current_raise', {})
        
        # Parse amount (handle string like "₹50 Lakhs" or "2 Crores")
        amount_str = funding_ask.get('amount', '0')
        loan_amount = parse_amount_string(amount_str)
        
        # Determine if DPIIT registered (from memo or metadata)
        company = memo.get('company_overview', {})
        is_dpiit = 'dpiit' in str(company).lower() or 'startup india' in str(company).lower()
        
        # Estimate vintage from founding year
        founding_year = company.get('founding_year', datetime.now().year)
        vintage = datetime.now().year - int(founding_year) if founding_year else 0
        
        user_profile = UserProfile(
            deal_id=deal_id,
            entity_type=company.get('legal_structure', 'Pvt Ltd'),
            vintage_years=vintage,
            loan_amount_requested=loan_amount,
            has_collateral=False,  # Default, would need user input
            dpiit_recognized=is_dpiit,
            industry_sector=metadata.get('sector', ''),
            is_profitable_2_years=False  # Would need to check from financials
        )
        
        # Run analysis
        service = CreditService()
        result = service.analyze(cma_model, user_profile)
        
        # Save result to deal
        deal_ref.update({
            'credit_analysis': result.dict(),
            'metadata.credit_analyzed_at': datetime.utcnow().isoformat() + "Z"
        })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in credit analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/override")
async def override_credit_decision(
    request: OverrideRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Apply a human-in-the-loop override to a credit decision.
    Logs the override for compliance audit.
    """
    try:
        # Verify deal exists and user has access
        deal_ref = db.collection('deals').document(request.deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        if deal_data.get('metadata', {}).get('user_id') != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if credit analysis exists
        if 'credit_analysis' not in deal_data:
            raise HTTPException(
                status_code=400,
                detail="No credit analysis found. Run analysis first."
            )
        
        # Apply override
        service = CreditService()
        result = service.apply_override(
            deal_id=request.deal_id,
            rule_id=request.rule_id,
            justification=request.justification,
            analyst_id=request.analyst_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in credit override: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-log/{deal_id}")
async def get_audit_log(
    deal_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Retrieve compliance audit log for a deal.
    """
    try:
        # Verify deal access
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        if deal_data.get('metadata', {}).get('user_id') != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Fetch audit logs
        logs = db.collection('compliance_audit_log').where(
            'deal_id', '==', deal_id
        ).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        
        audit_entries = [log.to_dict() for log in logs]
        
        return {
            "deal_id": deal_id,
            "entries": audit_entries,
            "count": len(audit_entries)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual-analyze")
async def manual_credit_analysis(
    deal_id: str,
    profile: UserProfile,
    current_user: str = Depends(get_current_user)
):
    """
    Run credit analysis with manually provided user profile.
    Useful for testing different scenarios.
    """
    try:
        # Fetch deal
        deal_ref = db.collection('deals').document(deal_id)
        deal_doc = deal_ref.get()
        
        if not deal_doc.exists:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal_data = deal_doc.to_dict()
        
        if deal_data.get('metadata', {}).get('user_id') != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
        raw_cma = deal_data.get('cma_data')
        if not raw_cma:
            raise HTTPException(
                status_code=400,
                detail="CMA data not available."
            )
        
        cma_model = parse_cma_to_model(raw_cma)
        
        # Override deal_id in profile
        profile.deal_id = deal_id
        
        service = CreditService()
        result = service.analyze(cma_model, profile)
        
        # Save result
        deal_ref.update({
            'credit_analysis': result.dict(),
            'metadata.credit_analyzed_at': datetime.utcnow().isoformat() + "Z"
        })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def parse_amount_string(amount_str: str) -> float:
    """
    Parse amount strings like '₹50 Lakhs', '2 Crores', '10L' to float INR.
    """
    if not amount_str:
        return 0.0
    
    # Clean the string
    amount_str = str(amount_str).lower().replace('₹', '').replace('rs', '').replace(',', '').strip()
    
    try:
        # Check for multipliers
        if 'crore' in amount_str or 'cr' in amount_str:
            num = float(''.join(c for c in amount_str if c.isdigit() or c == '.'))
            return num * 1_00_00_000
        elif 'lakh' in amount_str or 'lac' in amount_str or amount_str.endswith('l'):
            num = float(''.join(c for c in amount_str if c.isdigit() or c == '.'))
            return num * 1_00_000
        elif 'k' in amount_str:
            num = float(''.join(c for c in amount_str if c.isdigit() or c == '.'))
            return num * 1_000
        else:
            # Try to parse as-is
            return float(''.join(c for c in amount_str if c.isdigit() or c == '.'))
    except:
        return 0.0
