import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from ui.duplicate_finder import DuplicateFinderWidget
from services.history_service import HistoryService

def test_full_history():
    app = QApplication.instance() or QApplication(sys.argv)
    print("Initializing DuplicateFinderWidget...")
    widget = DuplicateFinderWidget()

    user_id = None
    logs = HistoryService.get_history_logs(user_id)
    completed = [l for l in logs if l.get("status") == "Completed" and l.get("excel_path")]
    print(f"Total completed logs with excel_path: {len(completed)}")

    for idx, log in enumerate(completed):
        print(f"\n--- Testing Log #{idx+1}: {log.get('bank_name')} ---")
        path = log.get("excel_path", "")
        print(f"Excel path: {path}, Exists: {os.path.exists(path)}")
        if os.path.exists(path):
            txs = widget._read_transactions_from_excel(path)
            print(f"Read {len(txs)} transactions from excel.")
            widget.loaded_statements = [{
                "file_name": os.path.basename(path),
                "bank_name": log.get("bank_name", "Bank"),
                "transactions": txs
            }]
            print("Running duplicate scan on loaded file...")
            widget.run_duplicate_scan()
            print("Scan & Render succeeded!")

    print("\nFull history test finished successfully with zero crashes!")

if __name__ == "__main__":
    test_full_history()
