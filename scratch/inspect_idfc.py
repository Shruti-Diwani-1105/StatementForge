import pdfplumber
import sys

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/IDFC.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages):
        print(f"\n--- Page {i+1} Text ---")
        text = page.extract_text()
        if text:
            print(text[:1500])  # Print first 1500 chars of each page
        else:
            print("[No text found on this page]")
