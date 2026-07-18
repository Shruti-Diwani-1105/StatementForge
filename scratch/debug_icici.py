import sys
import os

# Add workspace directory to python path
sys.path.insert(0, "/Users/shrutidiwani/Desktop/StatementForge-main")

from parser.parser import PDFStatementParser

files = [
    "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/ICICI.pdf",
    "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/ICICI2.pdf",
    "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/AU.pdf"
]

for f in files:
    if os.path.exists(f):
        print(f"\n==================================================")
        print(f"Parsing file: {f}")
        print(f"==================================================")
        try:
            payload = PDFStatementParser.parse(f)
            print(f"Bank Detected: {payload['bank_name']}")
            print(f"Total Transactions Extracted: {len(payload['transactions'])}")
            print("\nDetailed Logs:")
            print(payload["logs"])
        except Exception as e:
            print(f"Parsing error: {e}")
            import traceback
            traceback.print_exc()
