import sys
sys.path.append('.')
import pdfplumber
import fitz

pdf_path = "D:/Kotak Mahindra Somaiya.pdf"
print("Testing pdfplumber...")
try:
    with pdfplumber.open(pdf_path) as pdf:
        print("Pages count:", len(pdf.pages))
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            print(f"Page {i} text length: {len(text) if text else 0}")
            if text:
                print(f"Page {i} sample text:")
                print(text[:200])
except Exception as e:
    print("pdfplumber error:", e)

print("\nTesting fitz (PyMuPDF)...")
try:
    doc = fitz.open(pdf_path)
    print("Pages count:", len(doc))
    for i, page in enumerate(doc):
        text = page.get_text()
        print(f"Page {i} text length: {len(text) if text else 0}")
        if text:
            print(f"Page {i} sample text:")
            print(text[:200])
except Exception as e:
    print("fitz error:", e)
