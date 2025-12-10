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
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            # Convert the dataframe to a string representation (e.g., CSV or markdown-like)
            # CSV is often good for LLMs as it preserves structure
            sheet_text = df.to_csv(index=False)
            
            full_text.append(f"--- Sheet: {sheet_name} ---\n{sheet_text}")
            
        return {
            "text": "\n\n".join(full_text),
            "pages": len(xls.sheet_names)
        }
    except Exception as e:
        print(f"Error extracting text from Excel: {e}")
        return {"text": "", "pages": 0}
