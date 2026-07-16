import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.parser import PDFStatementParser
from services.excel_generator import ExcelGenerator

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"

try:
    payload = PDFStatementParser.parse(pdf_path)
    print("=== Parsing Success ===")
    print(f"Bank Detected   : {payload['bank_name']}")
    print(f"Account Holder  : {payload['account_holder']}")
    print(f"Account Number  : {payload['account_number']}")
    print(f"Period          : {payload['period']}")
    print(f"Transactions Count: {len(payload['transactions'])}")
    
    # Print first 5 transactions
    for tx in payload['transactions'][:5]:
        print(f" - {tx['date']} | {tx['narration'][:30]:<30} | Dr: {tx['debit']:<8} | Cr: {tx['credit']:<8} | Bal: {tx['balance']}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
