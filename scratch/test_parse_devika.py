import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath("."))

from parser.parser import PDFStatementParser

pdf_path = "D:/Devika CA.pdf"
if not os.path.exists(pdf_path):
    # Try current directory
    pdf_path = "Devika CA.pdf"

print(f"Checking file: {pdf_path}")
print(f"File exists: {os.path.exists(pdf_path)}")
if os.path.exists(pdf_path):
    print(f"File size: {os.path.getsize(pdf_path)} bytes")

try:
    payload = PDFStatementParser.parse(pdf_path)
    print("\n--- Payload Result ---")
    print(f"Bank Detected: {payload['bank_name']}")
    print(f"Transactions Extracted: {len(payload['transactions'])}")
    print(f"Processing Time: {payload['processing_time']:.2f} seconds")
    print("\n--- Engine Logs ---")
    print(payload['logs'])
except Exception as e:
    import traceback
    print("\n--- Parsing Crash Traceback ---")
    traceback.print_exc()
