import pdfplumber
import os

files = [
    "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/ICICI.pdf",
    "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/ICICI2.pdf"
]

for f in files:
    if os.path.exists(f):
        with pdfplumber.open(f) as pdf:
            print(f"File: {os.path.basename(f)} | Pages: {len(pdf.pages)}")
