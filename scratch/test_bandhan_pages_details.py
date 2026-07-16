import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfplumber
from parser.bank_detector import BankDetector
from parser.transaction_parser import TransactionParser
from parser.utils import ParserUtils

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"

print("Opening PDF...")
with pdfplumber.open(pdf_path) as pdf:
    for idx in range(len(pdf.pages)):
        page = pdf.pages[idx]
        tables = page.extract_tables()
        if not tables:
            print(f"Page {idx+1}: No tables found.")
            continue
            
        print(f"\n--- Page {idx+1} ---")
        largest_table = max(tables, key=len)
        cleaned_table = []
        for row in largest_table:
            cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
            cleaned_table.append(cleaned_row)
            
        mapping = TransactionParser.detect_columns(cleaned_table)
        print(f"Mapped columns: {mapping}")
        
        txs = TransactionParser.parse_rows(cleaned_table, mapping)
        print(f"Found {len(txs)} transactions.")
        if txs:
            print(f"Sample 1st tx: {txs[0]}")
