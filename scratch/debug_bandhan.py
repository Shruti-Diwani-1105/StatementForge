import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfplumber
from parser.bank_detector import BankDetector
from parser.parser import PDFStatementParser

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"

print("[1] Opening PDF...")
with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    
    print("[2] Extracting first page text for detection...")
    first_text = pdf.pages[0].extract_text()
    print(f"First page text length: {len(first_text) if first_text else 0}")
    
    print("[3] Detecting bank...")
    bank = BankDetector.detect_bank(first_text)
    print(f"Detected Bank: {bank}")
    
    print("[4] Trying to extract tables from Page 1...")
    tables = pdf.pages[0].extract_tables()
    print(f"Extracted {len(tables)} tables from Page 1.")
