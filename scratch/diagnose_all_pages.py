import sys
sys.path.append('.')
from parser.logger import ParserLogger
from parser.table_extractor import TableExtractor

class SimpleLogger(ParserLogger):
    def log(self, message):
        print(f"[LOG] {message}")

pdf_path = "D:/Kotak Mahindra Somaiya.pdf"
logger = SimpleLogger()

for page_idx in range(3):
    print(f"\n============================ PAGE {page_idx} ============================")
    grid_table = TableExtractor.extract_table_via_ocr(pdf_path, page_idx, logger)
    if not grid_table:
        print("Grid table is empty!")
    else:
        for idx, row in enumerate(grid_table):
            print(f"Row {idx:02d}: {row}")
