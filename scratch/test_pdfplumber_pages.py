import pdfplumber
import time

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"

print("Opening PDF with pdfplumber...")
with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    for idx, page in enumerate(pdf.pages):
        print(f"Processing Page {idx+1}...", end=" ", flush=True)
        start = time.time()
        try:
            # Run default extract_tables
            tables = page.extract_tables()
            print(f"Done in {time.time() - start:.2f}s | Found {len(tables)} tables.")
        except Exception as e:
            print(f"Error: {e}")
