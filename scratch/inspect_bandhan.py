import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.parser import PDFStatementParser
from parser.validation import ValidationService

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"
res = PDFStatementParser.parse(pdf_path)
transactions = res["transactions"]
val = ValidationService.validate_transactions(transactions)

print("=== Bandhan.pdf ===")
print("Bank:", res["bank_name"])
print("Total Transactions:", len(transactions))
print("Balance Verified:", val["success"])
print("Failed count:", len(val["failed_math_indices"]))
print("Failed Indices:", val["failed_math_indices"][:10])
if val["failed_math_indices"]:
    for idx in val["failed_math_indices"][:3]:
        print(f"Failed index {idx}: {transactions[idx]}")
