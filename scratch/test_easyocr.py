import os
import sys

sys.path.append(os.path.abspath("."))

from parser.ocr_parser import OCRParser
from parser.table_extractor import TableExtractor

pdf_path = "D:/Devika CA.pdf"
if not os.path.exists(pdf_path):
    pdf_path = "Devika CA.pdf"

print(f"Testing EasyOCR on: {pdf_path}")
if os.path.exists(pdf_path):
    try:
        # Extract table via OCR (calls EasyOCR because pytesseract fails)
        print("Extracting table blocks via local OCR...")
        blocks = OCRParser.extract_text_blocks(pdf_path, 0)
        print(f"Blocks extracted: {len(blocks)}")
        if blocks:
            print("Clustering words into grid...")
            grid = TableExtractor._cluster_text_into_grid(blocks)
            print(f"Rows extracted: {len(grid)}")
            print("First 3 rows:")
            for row in grid[:3]:
                print(row)
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("File not found.")
