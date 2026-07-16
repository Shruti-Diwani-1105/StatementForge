import pdfplumber

pdf_path = "/Users/shrutidiwani/Desktop/Bank_Statement_Converter/sample_files/Bandhan.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    for i in range(min(5, len(pdf.pages))):
        print(f"\n--- Page {i+1} Text ---")
        text = pdf.pages[i].extract_text()
        if text:
            print(text[:1000])
        else:
            print("[Empty Page]")
