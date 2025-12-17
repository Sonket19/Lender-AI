from typing import Dict, Any
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
from fastapi import HTTPException
from config.settings import settings
from .storage_service import upload_to_gcs
import json

async def extract_text_from_pdf(file_content: bytes, deal_id: str) -> Dict[str, Any]:
    """
    Extract text from PDF using Document AI synchronous processing with imageless mode
    Fast: completes in 10-30 seconds for 16-30 page documents
    """
    try:
        # Upload to GCS (for reference/backup)
        gcs_path = f"deals/{deal_id}/pitch_deck.pdf"
        gcs_uri = upload_to_gcs(file_content, gcs_path)
        
        print(f"Starting Document AI processing for deal {deal_id} (imageless mode)...")
        
        # Initialize Document AI client
        opts = ClientOptions(
            api_endpoint=f"{settings.DOCUMENT_AI_LOCATION}-documentai.googleapis.com"
        )
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        # Configure the process request
        processor_name = f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.DOCUMENT_AI_LOCATION}/processors/{settings.DOCUMENT_AI_PROCESSOR_ID}"
        
        # Create raw document
        raw_document = documentai.RawDocument(
            content=file_content,
            mime_type="application/pdf"
        )
        
        # Create request with imageless_mode enabled
        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=raw_document,
            skip_human_review=True,
            imageless_mode=True,  # ✅ Enables support for up to 30 pages
        )
        
        print(f"Sending synchronous request to Document AI with imageless_mode=True...")
        
        # Process document synchronously (returns in 10-30 seconds)
        result = client.process_document(request=request)
        document = result.document
        
        print(f"Document AI processing completed! Pages: {len(document.pages)}")
        
        # Extract text and structure
        extracted_data = {
            "text": document.text,
            "pages": len(document.pages),
            "entities": []
        }
        
        # Extract entities if available
        for entity in document.entities:
            extracted_data["entities"].append({
                "type": entity.type_,
                "mention_text": entity.mention_text,
                "confidence": entity.confidence
            })
        
        print(f"Extracted {len(extracted_data['entities'])} entities")
        
        return extracted_data
    
    except Exception as e:
        error_msg = str(e)
        print(f"Error in Document AI extraction: {error_msg}")
        
        # Check if it's a page limit error
        if "PAGE_LIMIT_EXCEEDED" in error_msg or "pages exceed the limit" in error_msg.lower():
            raise HTTPException(
                status_code=400, 
                detail="Document exceeds 30-page limit for fast processing. Please use a smaller document or contact support for batch processing."
            )
        
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {error_msg}")


async def extract_cma_with_docai(file_content: bytes, mime_type: str = "application/pdf") -> Dict[str, Any]:
    """
    Extract CMA financial data using Document AI Form Parser.
    Extracts tables and text, then maps to our financial schema.
    
    Returns structured data with audited_financials, provisional_financials, projected_financials.
    """
    try:
        print(f"📄 Starting Document AI CMA extraction ({len(file_content)} bytes, {mime_type})...")
        
        # Initialize Document AI client
        opts = ClientOptions(
            api_endpoint=f"{settings.DOCUMENT_AI_LOCATION}-documentai.googleapis.com"
        )
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        # Configure the process request
        processor_name = f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.DOCUMENT_AI_LOCATION}/processors/{settings.DOCUMENT_AI_PROCESSOR_ID}"
        
        # Create raw document
        raw_document = documentai.RawDocument(
            content=file_content,
            mime_type=mime_type
        )
        
        # Create request
        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=raw_document,
            skip_human_review=True,
        )
        
        print(f"📤 Sending request to Document AI processor...")
        
        # Process document
        result = client.process_document(request=request)
        document = result.document
        
        print(f"✅ Document AI processing completed! Pages: {len(document.pages)}")
        
        # Extract tables from all pages
        all_tables = []
        for page_idx, page in enumerate(document.pages):
            for table in page.tables:
                table_data = extract_table_data(document, table)
                if table_data:
                    table_data["page"] = page_idx + 1
                    all_tables.append(table_data)
        
        print(f"📊 Extracted {len(all_tables)} tables from document")
        
        # Map tables to financial schema
        cma_data = map_tables_to_cma_schema(all_tables, document.text)
        
        return cma_data
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error in Document AI CMA extraction: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Return empty structure on error
        return {
            "general_info": {"error": error_msg},
            "audited_financials": [],
            "provisional_financials": None,
            "projected_financials": []
        }


def extract_table_data(document, table) -> Dict[str, Any]:
    """Extract data from a Document AI table object."""
    try:
        headers = []
        rows = []
        
        # Extract header row
        if table.header_rows:
            for cell in table.header_rows[0].cells:
                cell_text = get_cell_text(document, cell)
                headers.append(cell_text)
        
        # Extract body rows
        for row in table.body_rows:
            row_data = []
            for cell in row.cells:
                cell_text = get_cell_text(document, cell)
                row_data.append(cell_text)
            if row_data:
                rows.append(row_data)
        
        return {
            "headers": headers,
            "rows": rows
        }
    except Exception as e:
        print(f"Error extracting table: {e}")
        return None


def get_cell_text(document, cell) -> str:
    """Get text content from a table cell."""
    text = ""
    if cell.layout and cell.layout.text_anchor and cell.layout.text_anchor.text_segments:
        for segment in cell.layout.text_anchor.text_segments:
            start = int(segment.start_index) if segment.start_index else 0
            end = int(segment.end_index) if segment.end_index else 0
            text += document.text[start:end]
    return text.strip()


def map_tables_to_cma_schema(tables: list, full_text: str) -> Dict[str, Any]:
    """
    Map extracted tables to our CMA financial schema.
    Looks for keywords to identify financial line items.
    """
    print(f"🔄 Mapping {len(tables)} tables to CMA schema...")
    
    # Initialize result structure
    cma_data = {
        "general_info": {"extracted_from": "document_ai"},
        "audited_financials": [],
        "provisional_financials": None,
        "projected_financials": []
    }
    
    # Keywords to identify financial fields (case-insensitive)
    field_mappings = {
        "revenue": ["revenue", "turnover", "sales", "gross sales", "net sales", "income from operations"],
        "pat": ["profit after tax", "pat", "net profit", "net income"],
        "depreciation": ["depreciation", "dep", "amortization", "depreciation & amortization"],
        "interest_expense": ["interest", "finance cost", "interest expense", "finance charges"],
        "current_assets": ["current assets", "total current assets", "gross current assets"],
        "current_liabilities": ["current liabilities", "total current liabilities"],
        "long_term_debt": ["term loan", "long term debt", "long term borrowing", "secured loans"],
        "short_term_debt": ["working capital", "short term debt", "cc/od", "bank borrowing", "cash credit"],
        "tangible_net_worth": ["net worth", "tangible net worth", "tnw", "shareholders fund", "equity"],
        "fixed_assets": ["fixed assets", "gross block", "net fixed assets", "ppe", "property plant"]
    }
    
    # Try to identify years from headers
    years = []
    year_to_tier = {}  # Map year to audited/provisional/projected
    
    for table in tables:
        headers = table.get("headers", [])
        for h in headers:
            h_lower = h.lower()
            # Look for year patterns like "FY23", "2023-24", "Mar-24"
            import re
            year_matches = re.findall(r'(fy\d{2,4}|20\d{2}[-/]\d{2,4}|mar[-/]\d{2,4}|\d{4})', h_lower)
            for ym in year_matches:
                if ym not in years:
                    years.append(ym.upper())
                    
                    # Determine tier based on keywords
                    if "audited" in h_lower or "actual" in h_lower:
                        year_to_tier[ym.upper()] = "audited"
                    elif "provisional" in h_lower or "estimated" in h_lower:
                        year_to_tier[ym.upper()] = "provisional"
                    elif "projected" in h_lower or "forecast" in h_lower:
                        year_to_tier[ym.upper()] = "projected"
                    else:
                        year_to_tier[ym.upper()] = "audited"  # Default
    
    print(f"📅 Identified years: {years}")
    
    # Build year-based financial data
    year_data = {year: {"year": year, "tier": year_to_tier.get(year, "audited")} for year in years}
    
    # Parse rows from all tables
    for table in tables:
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        
        for row in rows:
            if not row:
                continue
                
            # First column is typically the label
            label = row[0].lower() if row else ""
            values = row[1:] if len(row) > 1 else []
            
            # Match label to our schema fields
            matched_field = None
            for field, keywords in field_mappings.items():
                if any(kw in label for kw in keywords):
                    matched_field = field
                    break
            
            if matched_field and values:
                # Map values to years
                for i, value in enumerate(values):
                    if i < len(years):
                        year = years[i]
                        # Parse numeric value
                        parsed_val = parse_numeric_value(value)
                        if year in year_data:
                            year_data[year][matched_field] = parsed_val
    
    # Organize into audited/provisional/projected
    for year, data in year_data.items():
        tier = data.get("tier", "audited")
        
        # Ensure all required fields exist with defaults
        complete_data = {
            "year": year,
            "tier": tier,
            "revenue": data.get("revenue", 0.0),
            "pat": data.get("pat", 0.0),
            "depreciation": data.get("depreciation", 0.0),
            "interest_expense": data.get("interest_expense", 0.0),
            "current_assets": data.get("current_assets", 0.0),
            "current_liabilities": data.get("current_liabilities", 0.0),
            "long_term_debt": data.get("long_term_debt", 0.0),
            "short_term_debt": data.get("short_term_debt", 0.0),
            "tangible_net_worth": data.get("tangible_net_worth", 0.0),
            "fixed_assets": data.get("fixed_assets", 0.0)
        }
        
        if tier == "audited":
            cma_data["audited_financials"].append(complete_data)
        elif tier == "provisional":
            cma_data["provisional_financials"] = complete_data
        else:
            cma_data["projected_financials"].append(complete_data)
    
    print(f"✅ Mapped CMA data: {len(cma_data['audited_financials'])} audited, "
          f"{1 if cma_data['provisional_financials'] else 0} provisional, "
          f"{len(cma_data['projected_financials'])} projected")
    
    return cma_data


def parse_numeric_value(value: str) -> float:
    """Parse a string value to float, handling common formats."""
    if not value or value.strip() in ['', '-', 'N/A', 'nil', 'null']:
        return 0.0
    
    try:
        # Remove commas, brackets (for negatives), and whitespace
        cleaned = value.strip()
        cleaned = cleaned.replace(',', '')
        cleaned = cleaned.replace(' ', '')
        
        # Handle brackets for negative numbers
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        # Handle lakhs/crores notation
        if 'cr' in cleaned.lower():
            cleaned = cleaned.lower().replace('cr', '').replace('crore', '').replace('crores', '')
            return float(cleaned) * 10000000
        elif 'lakh' in cleaned.lower() or 'lac' in cleaned.lower():
            cleaned = cleaned.lower().replace('lakh', '').replace('lakhs', '').replace('lac', '').replace('lacs', '')
            return float(cleaned) * 100000
        
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def map_excel_sheets_to_cma_schema(sheets_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Excel sheet data (from extract_sheets_from_excel) to CMA financial schema.
    This is deterministic mapping - no AI involved.
    
    sheets_data structure:
    {
        "sheets": [
            {
                "name": "Operating Statement",
                "years": ["FY22", "FY23", "FY24"],
                "rows": [
                    {"particulars": "Revenue", "values": ["1000", "1500", "2000"]},
                    ...
                ]
            }
        ],
        "sheet_count": N
    }
    """
    print(f"🔄 Mapping Excel sheets to CMA schema...")
    
    # Initialize result
    cma_data = {
        "general_info": {"extracted_from": "excel_sheets"},
        "audited_financials": [],
        "provisional_financials": None,
        "projected_financials": []
    }
    
    sheets = sheets_data.get("sheets", [])
    if not sheets:
        print("⚠️ No sheets found in Excel data")
        return cma_data
    
    # Keywords to identify financial fields (case-insensitive)
    field_mappings = {
        "revenue": ["revenue", "turnover", "sales", "gross sales", "net sales", "income from operations", "total income"],
        "pat": ["profit after tax", "pat", "net profit", "net income", "profit for the year"],
        "depreciation": ["depreciation", "dep", "amortization", "depreciation & amortization", "dep. & amort"],
        "interest_expense": ["interest", "finance cost", "interest expense", "finance charges", "interest paid"],
        "current_assets": ["current assets", "total current assets", "gross current assets"],
        "current_liabilities": ["current liabilities", "total current liabilities", "total cl"],
        "long_term_debt": ["term loan", "long term debt", "long term borrowing", "secured loans", "term loans"],
        "short_term_debt": ["working capital", "short term debt", "cc/od", "bank borrowing", "cash credit", "overdraft"],
        "tangible_net_worth": ["net worth", "tangible net worth", "tnw", "shareholders fund", "equity", "total equity", "capital & reserves"],
        "fixed_assets": ["fixed assets", "gross block", "net fixed assets", "ppe", "property plant", "net block"]
    }
    
    # First, identify years from all sheets
    all_years = []
    year_to_tier = {}
    
    for sheet in sheets:
        years = sheet.get("years", [])
        for y in years:
            y_str = str(y).strip()
            if y_str and y_str not in all_years:
                all_years.append(y_str)
                
                # Determine tier based on keywords
                y_lower = y_str.lower()
                if "audited" in y_lower or "actual" in y_lower:
                    year_to_tier[y_str] = "audited"
                elif "provisional" in y_lower or "estimated" in y_lower or "est" in y_lower:
                    year_to_tier[y_str] = "provisional"
                elif "projected" in y_lower or "forecast" in y_lower or "proj" in y_lower:
                    year_to_tier[y_str] = "projected"
                else:
                    # Default: assume first 2-3 years are audited, rest projected
                    year_to_tier[y_str] = "audited"  # Will refine later
    
    print(f"📅 Identified years from sheets: {all_years}")
    
    # Initialize year data
    year_data = {y: {"year": y, "tier": year_to_tier.get(y, "audited")} for y in all_years}
    
    # Parse each sheet
    for sheet in sheets:
        sheet_name = sheet.get("name", "").lower()
        years = sheet.get("years", [])
        rows = sheet.get("rows", [])
        
        print(f"   Processing sheet: {sheet.get('name')} with {len(rows)} rows")
        
        for row in rows:
            particulars = row.get("particulars", "").lower()
            values = row.get("values", [])
            
            if not particulars or not values:
                continue
            
            # Match particulars to our schema
            matched_field = None
            for field, keywords in field_mappings.items():
                if any(kw in particulars for kw in keywords):
                    matched_field = field
                    break
            
            if matched_field:
                # Map values to years
                for i, val in enumerate(values):
                    if i < len(years):
                        year = str(years[i]).strip()
                        if year in year_data:
                            parsed_val = parse_numeric_value(val)
                            if parsed_val != 0.0 or matched_field not in year_data[year]:
                                year_data[year][matched_field] = parsed_val
                                print(f"      Mapped {matched_field}={parsed_val} for {year}")
    
    # Refine tier classification based on position if not explicitly marked
    year_list = list(all_years)
    for i, year in enumerate(year_list):
        if year_to_tier.get(year) == "audited":
            # If more than 3 years and this is in latter half, mark as projected
            if len(year_list) > 3 and i >= len(year_list) - 2:
                year_data[year]["tier"] = "projected"
    
    # Organize into audited/provisional/projected
    for year, data in year_data.items():
        tier = data.get("tier", "audited")
        
        # Ensure all required fields exist with defaults
        complete_data = {
            "year": year,
            "tier": tier,
            "revenue": data.get("revenue", 0.0),
            "pat": data.get("pat", 0.0),
            "depreciation": data.get("depreciation", 0.0),
            "interest_expense": data.get("interest_expense", 0.0),
            "current_assets": data.get("current_assets", 0.0),
            "current_liabilities": data.get("current_liabilities", 0.0),
            "long_term_debt": data.get("long_term_debt", 0.0),
            "short_term_debt": data.get("short_term_debt", 0.0),
            "tangible_net_worth": data.get("tangible_net_worth", 0.0),
            "fixed_assets": data.get("fixed_assets", 0.0)
        }
        
        if tier == "audited":
            cma_data["audited_financials"].append(complete_data)
        elif tier == "provisional":
            cma_data["provisional_financials"] = complete_data
        else:
            cma_data["projected_financials"].append(complete_data)
    
    # Sort financials by year
    cma_data["audited_financials"].sort(key=lambda x: x["year"])
    cma_data["projected_financials"].sort(key=lambda x: x["year"])
    
    print(f"✅ Mapped Excel to CMA: {len(cma_data['audited_financials'])} audited, "
          f"{1 if cma_data['provisional_financials'] else 0} provisional, "
          f"{len(cma_data['projected_financials'])} projected")
    
    # Log sample data
    if cma_data["audited_financials"]:
        sample = cma_data["audited_financials"][0]
        print(f"   Sample: year={sample['year']}, revenue={sample['revenue']}, CA={sample['current_assets']}, CL={sample['current_liabilities']}")
    
    return cma_data


async def extract_cma_with_gemini(excel_text: str) -> Dict[str, Any]:
    """
    AI-powered CMA extraction using Gemini.
    Handles varying Excel layouts by using semantic understanding.
    
    Args:
        excel_text: Raw text extracted from Excel file (CSV format from extract_text_from_excel)
    
    Returns:
        Structured CMA data in the standard schema format
    """
    from google import genai
    from config.settings import settings
    
    print(f"🤖 Starting AI-powered CMA extraction with Gemini...")
    print(f"   Input text length: {len(excel_text)} characters")
    
    # Initialize Gemini client
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Get current date for context
    from datetime import datetime
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    # In India, FY runs April to March. If month >= April, current FY is current_year-next_year, else previous_year-current_year
    if current_month >= 4:  # April onwards
        current_fy = f"FY{str(current_year + 1)[-2:]}"  # e.g., FY26 for 2025-26
        current_fy_range = f"{current_year}-{str(current_year + 1)[-2:]}"
    else:
        current_fy = f"FY{str(current_year)[-2:]}"  # e.g., FY25 for 2024-25
        current_fy_range = f"{current_year - 1}-{str(current_year)[-2:]}"
    
    print(f"   Current date: {current_date.strftime('%Y-%m-%d')}, Current FY: {current_fy} ({current_fy_range})")
    
    # Construct the prompt with explicit schema requirements
    prompt = f"""You are a financial data extraction expert. Analyze this CMA (Credit Monitoring Arrangement) report data extracted from an Excel file and extract the financial information into a structured JSON format.

**CRITICAL - TODAY'S DATE IS: {current_date.strftime('%B %d, %Y')} (Year {current_year})**
**THE ACTUAL CURRENT FINANCIAL YEAR IS: {current_fy} ({current_fy_range})**

In India, the financial year runs from April to March. Based on today's date:
- Years like FY25, FY24, 2024-25, 2023-24, etc. that are BEFORE or EQUAL to {current_fy} are REAL/AUDITED data
- Years like FY26, FY27, 2025-26, 2026-27, etc. that are AFTER {current_fy} are PROJECTED/FUTURE data
- DO NOT use projected years (FY26, FY27, 2027) as the "current" year

The data contains financial statements including Operating Statement, Balance Sheet, and possibly Cash Flow across multiple fiscal years.

**INPUT DATA:**
```
{excel_text[:50000]}
```


**REQUIRED OUTPUT FORMAT:**
Extract the data into this exact JSON structure. All monetary values should be numbers (not strings). Use 0.0 if a value is not found.

```json
{{
  "general_info": {{
    "company_name": "extracted company name or 'Unknown'",
    "extracted_from": "gemini_ai",
    "current_financial_year": "{current_fy}",
    "data_unit": "lakhs or crores or absolute - specify what unit the data is in"
  }},
  "audited_financials": [
    {{
      "year": "FY22 or 2021-22 or 2022 format",
      "tier": "audited",
      "revenue": 0.0,
      "pat": 0.0,
      "depreciation": 0.0,
      "interest_expense": 0.0,
      "current_assets": 0.0,
      "current_liabilities": 0.0,
      "long_term_debt": 0.0,
      "short_term_debt": 0.0,
      "tangible_net_worth": 0.0,
      "fixed_assets": 0.0,
      "total_outside_liabilities": 0.0,
      "dscr": 0.0,
      "tol_tnw_ratio": 0.0,
      "current_ratio": 0.0
    }}
  ],
  "provisional_financials": null,
  "projected_financials": [],
  "key_ratios_summary": {{
    "current_year": {{
      "year": "most recent year label",
      "dscr": 0.0,
      "tol_tnw_ratio": 0.0,
      "current_ratio": 0.0,
      "revenue": 0.0,
      "pat": 0.0,
      "tangible_net_worth": 0.0
    }},
    "previous_year": {{
      "year": "second most recent year label",
      "dscr": 0.0,
      "tol_tnw_ratio": 0.0,
      "current_ratio": 0.0,
      "revenue": 0.0,
      "pat": 0.0,
      "tangible_net_worth": 0.0
    }},
    "year_minus_2": {{
      "year": "third most recent year label or null if not available",
      "dscr": 0.0,
      "tol_tnw_ratio": 0.0,
      "current_ratio": 0.0,
      "revenue": 0.0,
      "pat": 0.0,
      "tangible_net_worth": 0.0
    }}
  }},
  "loan_analysis_data": {{
    "current_year_financials": {{
      "year": "current year label",
      "current_assets": 0.0,
      "current_liabilities": 0.0,
      "tangible_net_worth": 0.0,
      "total_outside_liabilities": 0.0,
      "pat": 0.0,
      "depreciation": 0.0,
      "interest_expense": 0.0
    }},
    "previous_year_financials": {{
      "year": "previous year label",
      "current_assets": 0.0,
      "current_liabilities": 0.0,
      "tangible_net_worth": 0.0,
      "total_outside_liabilities": 0.0,
      "pat": 0.0,
      "depreciation": 0.0,
      "interest_expense": 0.0
    }}
  }}
}}
```

**EXTRACTION RULES:**

1. **YEAR IDENTIFICATION (CRITICAL):**
   - Identify all years in the data (FY24, FY23, 2023-24, 2022, Mar-24, etc.)
   - Determine which is the CURRENT (most recent) financial year
   - If years are in FY format (FY24, FY23), use that
   - If years are calendar years (2024, 2023), use that
   - If years are like "2023-24", use that format
   - Sort years chronologically and identify: current_year, previous_year, year_minus_2

2. **Revenue**: Look for "Revenue from Operations", "Net Sales", "Turnover", "Gross Sales", "Total Income from Operations"

3. **PAT (Profit After Tax)**: Look for "Profit After Tax", "PAT", "Net Profit", "Net Income", "Profit for the Year"

4. **Depreciation**: Look for "Depreciation", "Depreciation & Amortization", "Dep."

5. **Interest Expense**: Look for "Interest", "Finance Cost", "Interest Expense", "Interest Paid"

6. **Current Assets**: Look for "Total Current Assets", "Current Assets", "Gross Current Assets"

7. **Current Liabilities**: Look for "Total Current Liabilities", "Current Liabilities"

8. **Long Term Debt**: Look for "Term Loans", "Long Term Borrowings", "Secured Loans", "Long Term Debt"

9. **Short Term Debt**: Look for "Working Capital Loans", "Cash Credit", "CC/OD", "Bank Borrowings", "Short Term Borrowings"

10. **Tangible Net Worth**: Look for "Net Worth", "Tangible Net Worth", "TNW", "Shareholders Funds", "Total Equity"

11. **Fixed Assets**: Look for "Fixed Assets", "Net Block", "Property Plant & Equipment", "PPE"

12. **Total Outside Liabilities (TOL)**: Look for "Total Outside Liabilities", "TOL", or calculate as (Long Term Debt + Short Term Debt + Current Liabilities)

13. **DSCR (Debt Service Coverage Ratio)**: Look for "DSCR" in the data. If not found, calculate as: (PAT + Depreciation + Interest) / Interest. Round to 2 decimal places.

14. **TOL/TNW Ratio**: Look for "TOL/TNW" or "TOL to TNW". If not found, calculate as: Total Outside Liabilities / Tangible Net Worth. Round to 2 decimal places.

15. **Current Ratio**: Look for "Current Ratio". If not found, calculate as: Current Assets / Current Liabilities. Round to 2 decimal places.

**KEY SECTIONS TO POPULATE:**
- **key_ratios_summary**: Contains ratios for last 3 years (current, previous, year_minus_2). This will be displayed on UI with hover functionality.
- **loan_analysis_data**: Contains detailed financials for current and previous year, used for loan/credit analysis.

**IMPORTANT - VALUE CONVERSION:**
- Return ONLY the JSON object, no markdown formatting or explanation
- Ensure all numeric values are actual numbers from the data, not placeholder 0.0 unless truly missing
- **CONVERT ALL MONETARY VALUES TO ABSOLUTE INR:**
  - If the document says values are in "Lakhs", multiply each value by 100,000
  - If the document says values are in "Crores", multiply each value by 10,000,000
  - If no unit specified, assume absolute INR
- Ratios (DSCR, TOL/TNW, Current Ratio) should remain as ratios (not multiplied)
- Sort years chronologically (oldest to newest in audited_financials array)
- Calculate ratios if not directly available in the data
- key_ratios_summary.current_year should have data from the MOST RECENT year
- loan_analysis_data should have the 2 most recent years for credit analysis
"""


    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        response_text = response.text.strip()
        print(f"🤖 Gemini response received ({len(response_text)} chars)")
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON response
        cma_data = json.loads(response_text)
        
        # Validate and log the result
        audited_count = len(cma_data.get("audited_financials", []))
        provisional = cma_data.get("provisional_financials")
        projected_count = len(cma_data.get("projected_financials", []))
        
        print(f"✅ AI Extraction successful:")
        print(f"   - Audited years: {audited_count}")
        print(f"   - Provisional: {'Yes' if provisional else 'No'}")
        print(f"   - Projected years: {projected_count}")
        
        # Log sample data for verification
        if cma_data.get("audited_financials"):
            sample = cma_data["audited_financials"][0]
            print(f"   - Sample (first audited): year={sample.get('year')}, revenue={sample.get('revenue')}, CA={sample.get('current_assets')}, CL={sample.get('current_liabilities')}")
        
        return cma_data
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse Gemini response as JSON: {e}")
        print(f"   Response was: {response_text[:500]}...")
        return _get_empty_cma_schema()
    except Exception as e:
        print(f"❌ Error in AI CMA extraction: {e}")
        import traceback
        traceback.print_exc()
        return _get_empty_cma_schema()


def _get_empty_cma_schema() -> Dict[str, Any]:
    """Return empty CMA schema structure for fallback."""
    return {
        "general_info": {"extracted_from": "gemini_ai", "error": "extraction_failed"},
        "audited_financials": [],
        "provisional_financials": None,
        "projected_financials": []
    }
async def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """Extract company name, founders, and sector from text using Gemini"""
    from google import genai
    from config.settings import settings
    
    try:
        # Use the same client as gemini_service
        # Use API Key authentication instead of Vertex AI (ADC)
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )
        
        prompt = f"""
        Extract the following information from this pitch deck text:
        1. Company name
        2. List of founder names
        3. Primary sector/industry
        
        Text:
        {text[:10000]}
        
        Return ONLY a JSON object with this structure:
        {{
            "company_name": "extracted name",
            "founder_names": ["founder1", "founder2"],
            "sector": "primary sector"
        }}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        response_text = response.text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        elif response_text.startswith("```"):
            response_text = response_text[3:-3]
        
        metadata = json.loads(response_text)
        return metadata
    
    except Exception as e:
        print(f"Error extracting metadata: {str(e)}")
        return {
            "company_name": "Unknown",
            "founder_names": [],
            "sector": "Unknown"
        }

async def extract_content_with_gemini(gcs_uri: str, mime_type: str) -> Dict[str, Any]:
    """
    Extract content from Video, Audio, or Text files using Gemini 1.5 Flash
    """
    from google import genai
    from google.genai import types
    from config.settings import settings
    
    try:
        print(f"Starting Gemini extraction for {mime_type} file at {gcs_uri}...")
        
        # Use API Key authentication instead of Vertex AI (ADC)
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )
        
        # Create the part from GCS URI
        file_part = types.Part.from_uri(
            file_uri=gcs_uri,
            mime_type=mime_type
        )
        
        prompt = """
        You are an expert startup analyst. Your task is to extract all relevant information from this pitch deck file (video/audio/text) to prepare for a detailed investment memo.
        
        Please provide a comprehensive transcript and description of the content, focusing on:
        1. The Problem & Solution
        2. Market Size & Opportunity
        3. Business Model & Revenue Streams
        4. Traction & Financials
        5. Team Background
        6. Competition & Moat
        7. Fundraising Ask & Use of Funds
        
        If there are visual slides (in video), describe them in detail.
        If it's audio, transcribe the speech accurately.
        
        Output the result as a single block of text that can be used for downstream analysis.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[file_part, prompt]
        )
        
        extracted_text = response.text.strip()
        print(f"Gemini extraction completed. Length: {len(extracted_text)} chars")
        
        return {
            "text": extracted_text,
            "pages": 1, # Placeholder for non-PDF
            "entities": []
        }
        
    except Exception as e:
        print(f"Error in Gemini multimodal extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract content from {mime_type}: {str(e)}")
