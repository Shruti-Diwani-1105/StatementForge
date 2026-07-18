import sys
import os

# Add workspace directory to python path
sys.path.insert(0, "/Users/shrutidiwani/Desktop/StatementForge-main")

from parser.table_extractor import TableExtractor
from parser.transaction_parser import TransactionParser

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/AU.pdf"

table_default = TableExtractor.extract_table_digitally_default(pdf_path, 0)
print(f"Default table rows: {len(table_default)}")
if table_default:
    print("Row 0 (headers):", table_default[0])
    if len(table_default) > 1:
        print("Row 1:", table_default[1])
    
    mapping = TransactionParser.detect_columns(table_default)
    print(f"Detected mapping: {mapping}")
