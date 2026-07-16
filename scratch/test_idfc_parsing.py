import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.utils import ParserUtils
from parser.transaction_parser import TransactionParser
import pdfplumber

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/IDFC.pdf"

# 1. Test clean date helper
test_date = '27/07\n/2025'
clean_val = str(test_date).replace('\n', '').replace('\r', '').strip()
print(f"Clean date: {clean_val}")

# 2. Extract tables using pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    for page_idx in range(len(pdf.pages)):
        page = pdf.pages[page_idx]
        tables = page.extract_tables()
        if not tables:
            continue
        print(f"\n--- Page {page_idx+1} Tables ---")
        for t_idx, table in enumerate(tables):
            # Let's clean the grid rows (emulate TableExtractor behaviour)
            cleaned_table = []
            for row in table:
                cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                cleaned_table.append(cleaned_row)
                
            # Run column detection
            mapping = TransactionParser.detect_columns(cleaned_table)
            print(f"Detected columns: {mapping}")
            
            # Let's print the first row with a valid date (using clean date check)
            for row in cleaned_table:
                # Clean date check
                date_cell = row[0] if len(row) > 0 else ""
                clean_date = date_cell.replace('\n', '').replace('\r', '').strip()
                if ParserUtils.is_valid_date(clean_date):
                    print(f"Sample Row: {row}")
                    break
