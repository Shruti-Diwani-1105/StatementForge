import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfplumber
from parser.bank_detector import BankDetector

folder = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/"
for entry in os.listdir(folder):
    if entry.lower().endswith(".pdf"):
        path = os.path.join(folder, entry)
        try:
            with pdfplumber.open(path) as pdf:
                # Extract first page text to see bank
                first_text = pdf.pages[0].extract_text() or ""
                bank = BankDetector.detect_bank(first_text)
                print(f"File: {entry:<30} | Pages: {len(pdf.pages):<3} | Detected Bank: {bank}")
        except Exception as e:
            print(f"File: {entry:<30} | Error: {e}")
