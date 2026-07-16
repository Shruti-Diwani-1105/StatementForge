import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.parser import PDFStatementParser

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"

print("[1] Starting PDFStatementParser.parse...")
try:
    payload = PDFStatementParser.parse(pdf_path)
    print("=== Success ===")
    print(f"Transactions: {len(payload['transactions'])}")
except Exception as e:
    print(f"Error: {e}")
