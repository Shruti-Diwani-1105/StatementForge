import pdfplumber

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page_idx in [1, 7]: # Page 2 and Page 8
        page = pdf.pages[page_idx]
        tables = page.extract_tables()
        print(f"\n=== Page {page_idx+1} Rows ===")
        if tables:
            largest_table = max(tables, key=len)
            for r_idx, row in enumerate(largest_table[:5]):
                print(f"Row {r_idx}: {row}")
        else:
            print("No tables found.")
