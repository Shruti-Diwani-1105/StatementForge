import sys
sys.path.append('.')
from parser.page_processor import PageProcessor
from parser.logger import ParserLogger
from parser.table_extractor import TableExtractor

class SimpleLogger(ParserLogger):
    def log(self, message):
        print(f"[LOG] {message}")

pdf_path = "D:/Kotak Mahindra Somaiya.pdf"
logger = SimpleLogger()

print("Extracting grid table from page 1...")
grid_table = TableExtractor.extract_table_via_ocr(pdf_path, 1, logger)
print("\n--- GRID TABLE (PAGE 1) ---")
if not grid_table:
    print("Grid table is empty!")
else:
    for idx, row in enumerate(grid_table):
        print(f"Row {idx:02d}: {row}")

print("\nRunning process_page on page 1...")
txs, mapping, method = PageProcessor.process_page(pdf_path, 1, None, logger)
print("\n--- RESULTS ---")
print("Method used:", method)
print("Detected mapping:", mapping)
print("Transactions count:", len(txs))
if txs:
    print("Transactions:")
    for tx in txs:
        print(tx)
