import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from services.history_service import HistoryService
from ui.duplicate_finder import DuplicateFinderWidget

def test_history_loading():
    app = QApplication.instance() or QApplication(sys.argv)
    print("Testing history logs loading...")
    logs = HistoryService.get_history_logs()
    print(f"Total history logs found: {len(logs)}")
    completed = [l for l in logs if l.get("status") == "Completed" and l.get("excel_path")]
    print(f"Completed history logs with excel_path: {len(completed)}")

    widget = DuplicateFinderWidget()

    for idx, log in enumerate(completed):
        path = log.get("excel_path", "")
        print(f"\n--- Checking log #{idx+1}: {log.get('bank_name')} ---")
        print(f"Path: {path}")
        print(f"Exists: {os.path.exists(path)}")
        if os.path.exists(path):
            txs = widget._read_transactions_from_excel(path)
            print(f"Parsed transactions count: {len(txs)}")
            if txs:
                print(f"First tx sample: {txs[0]}")
                res = widget.DuplicateFinderService.analyze_statement(txs) if hasattr(widget, 'DuplicateFinderService') else None
                print(f"Analysis clusters: {len(res['clusters']) if res else 'N/A'}")

    print("\nHistory loading test complete.")

if __name__ == "__main__":
    test_history_loading()
