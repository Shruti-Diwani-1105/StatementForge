import pdfplumber

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/IDFC.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[1]  # Page 2
    
    # Try default strategy
    print("=== Default Strategy ===")
    tables = page.extract_tables()
    print(f"Number of tables: {len(tables)}")
    if tables:
        for idx, table in enumerate(tables):
            print(f"Table {idx+1} has {len(table)} rows:")
            for row in table[:5]:
                print(row)
                
    # Try text strategy
    print("\n=== Text Strategy ===")
    tables_text = page.extract_tables({
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "intersection_tolerance": 3
    })
    print(f"Number of tables: {len(tables_text)}")
    if tables_text:
        for idx, table in enumerate(tables_text):
            print(f"Table {idx+1} has {len(table)} rows:")
            for row in table[:5]:
                print(row)
