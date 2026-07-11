import os
import sys

sys.path.append(os.path.abspath("."))

from parser.parser import PDFStatementParser

pdf_path = "D:/Devika CA.pdf"
if not os.path.exists(pdf_path):
    pdf_path = "Devika CA.pdf"

print(f"Testing bank detection on: {pdf_path}")
if os.path.exists(pdf_path):
    try:
        bank = PDFStatementParser.detect_bank_from_pdf(pdf_path)
        print(f"Detected Bank: {bank}")
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("File not found.")
