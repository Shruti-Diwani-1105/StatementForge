import sys
sys.path.append('.')
from parser.page_processor import PageProcessor
from parser.logger import ParserLogger

class SimpleLogger(ParserLogger):
    def log(self, message):
        print(f"[LOG] {message}")

pdf_path = "D:/Kotak Mahindra Somaiya.pdf"
logger = SimpleLogger()

print("Processing page 0...")
txs, mapping, method = PageProcessor.process_page(pdf_path, 0, None, logger)
print("\n--- RESULTS ---")
print("Method used:", method)
print("Detected mapping:", mapping)
print("Transactions count:", len(txs))
if txs:
    print("Transactions:")
    for tx in txs:
        print(tx)
