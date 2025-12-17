import pandas as pd
import io

def extract_text_from_excel(file_content: bytes) -> dict:
    """
    Extracts text from an Excel file (bytes).
    Returns a dictionary with 'text' and 'pages' (sheets).
    """
    try:
        # Load the Excel file from bytes
        excel_file = io.BytesIO(file_content)
        xls = pd.ExcelFile(excel_file)
        
        full_text = []
        
        # Iterate through each sheet
        for sheet_name in xls.sheet_names:
            # Read with header=None to preserve all rows as data (including top metadata)
            # This is better for LLM extraction as it avoids "Unnamed: X" headers
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            # Convert to CSV string without headers (pure grid)
            sheet_text = df.to_csv(index=False, header=False)
            
            full_text.append(f"--- Sheet: {sheet_name} ---\n{sheet_text}")
            
        return {
            "text": "\n\n".join(full_text),
            "pages": len(xls.sheet_names)
        }
    except Exception as e:
        print(f"Error extracting text from Excel: {e}")
        return {"text": "", "pages": 0}


def extract_sheets_from_excel(file_content: bytes) -> dict:
    """
    Extracts structured data from each Excel sheet.
    Returns a dictionary with 'sheets' array containing each sheet's data.
    This enables dynamic tab rendering in the frontend.
    """
    try:
        excel_file = io.BytesIO(file_content)
        xls = pd.ExcelFile(excel_file)
        
        sheets = []
        
        for sheet_name in xls.sheet_names:
            # Read first with no header to inspect rows
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            if df_raw.empty:
                continue

            # Detect Header Row:
            # Look for row containing "Particulars" or distinct year patterns
            header_idx = 0
            found_header = False
            
            for idx, row in df_raw.head(20).iterrows(): # Check first 20 rows
                row_str = " ".join([str(v).lower() for v in row.values])
                if "particulars" in row_str or "liabilities" in row_str or "assets" in row_str:
                    header_idx = idx
                    found_header = True
                    break
            
            # If no keyword found, look for row with most non-null values (heuristic)
            if not found_header:
                max_non_null = 0
                for idx, row in df_raw.head(10).iterrows():
                   non_null_count = row.count()
                   if non_null_count > max_non_null:
                       max_non_null = non_null_count
                       header_idx = idx

            # Re-read with detected header
            df = pd.read_excel(xls, sheet_name=sheet_name, header=header_idx)
            
            # Clean up headers
            columns = []
            for col in df.columns.tolist():
                if pd.isna(col) or str(col).startswith('Unnamed:'):
                    columns.append('') # Replace Unnamed columns with empty string
                elif isinstance(col, (int, float)):
                     columns.append(str(int(col)) if col == int(col) else str(col))
                else:
                    columns.append(str(col).strip())

            # Convert rows to structured format
            rows = []
            for idx, row in df.iterrows():
                row_values = []
                for val in row.values:
                    if pd.isna(val) or val == '':
                        row_values.append('')
                    elif isinstance(val, (int, float)):
                        if val == int(val):
                            row_values.append(str(int(val)))
                        else:
                            row_values.append(f"{val:.2f}")
                    elif hasattr(val, 'strftime'):
                        row_values.append(val.strftime('%Y-%m-%d'))
                    else:
                        row_values.append(str(val).strip())
                
                # Logic to identify if this is a valid data row
                # Must have at least one valid value besides the label
                particulars = row_values[0] if len(row_values) > 0 else ""
                values = row_values[1:] if len(row_values) > 1 else []
                
                # Include row if it has content
                if particulars or any(v != '' for v in values):
                     rows.append({
                        "particulars": particulars,
                        "values": values
                    })
            
            # Determine headers
            col_headers = columns[1:] if len(columns) > 1 else []
            first_col_name = columns[0] if columns and columns[0] != '' else "Particulars"
            
            sheets.append({
                "name": sheet_name,
                "first_column_header": first_col_name,
                "years": col_headers, 
                "rows": rows
            })
        
        print(f"✅ Extracted {len(sheets)} sheets from Excel")
        for s in sheets:
            print(f"   - {s['name']}: {len(s['rows'])} rows, {len(s['years'])} columns")
        
        return {
            "sheets": sheets,
            "sheet_count": len(sheets)
        }
    except Exception as e:
        print(f"Error extracting sheets from Excel: {e}")
        import traceback
        traceback.print_exc()
        return {"sheets": [], "sheet_count": 0}


