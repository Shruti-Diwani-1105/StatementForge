import sys
sys.path.append('.')
import logging
from parser.parser import PDFStatementParser
from parser.logger import ParserLogger

class ConsoleLogger(ParserLogger):
    def __init__(self):
        super().__init__()
    def log(self, message):
        print(f"[LOG] {message}")
    def log_page_success(self, page_num, is_digital, count, method):
        print(f"[PAGE {page_num} SUCCESS] digital={is_digital}, transactions={count}, method={method}")
    def log_page_failure(self, page_num, error):
        print(f"[PAGE {page_num} FAILURE] error={error}")
    def log_summary(self, total_pages, failed_count, initial_count, dedup_count):
        print(f"[SUMMARY] total_pages={total_pages}, failed={failed_count}, initial={initial_count}, dedup={dedup_count}")

print("Instantiating parser...")
parser = PDFStatementParser()
logger = ConsoleLogger()

pdf_path = "D:/Kotak Mahindra Somaiya.pdf"
print(f"Parsing statement: {pdf_path}")
try:
    payload = parser.parse(pdf_path, progress_callback=lambda cur, tot, tx_count=0: print(f"Progress: {cur}/{tot} ({tx_count} txs)"))
    print("\n--- PAYLOAD RESULTS ---")
    print("Bank Name:", payload.get("bank_name"))
    print("Account Holder:", payload.get("account_holder"))
    print("Period:", payload.get("period"))
    print("Transactions Count:", len(payload.get("transactions", [])))
    if payload.get("transactions"):
        print("Sample Transactions:")
        for tx in payload["transactions"][:5]:
            print(tx)
except Exception as e:
    import traceback
    traceback.print_exc()
