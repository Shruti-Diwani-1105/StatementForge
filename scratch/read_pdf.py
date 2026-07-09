import pdfplumber
import sys

def main():
    pdf_path = "/Users/shrutidiwani/Downloads/Devika CA.pdf"
    print(f"Reading PDF: {pdf_path}")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            first_page_text = pdf.pages[0].extract_text()
            print("\nFirst Page Text (first 1500 chars):")
            print("-" * 50)
            print(first_page_text[:1500])
            print("-" * 50)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
