import pdfplumber

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[3] # Page 4
    tables = page.extract_tables()
    if tables:
        largest_table = max(tables, key=len)
        print("=== Page 4 Rows ===")
        for r_idx, row in enumerate(largest_table[:5]):
            print(f"Row {r_idx}: {row}")
