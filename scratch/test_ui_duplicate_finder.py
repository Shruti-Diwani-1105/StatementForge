import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from ui.duplicate_finder import DuplicateFinderWidget

def test_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    print("Instantiating DuplicateFinderWidget...")
    widget = DuplicateFinderWidget()
    widget.show()

    # Create dummy loaded statement
    sample_txs = [
        {"date": "10/05/2026", "narration": "UPI/123456789/AMAZON PAY", "debit": "1500.00", "credit": "", "balance": "45000.00", "ref_no": "123456789"},
        {"date": "10/05/2026", "narration": "UPI/123456789/AMAZON PAY", "debit": "1500.00", "credit": "", "balance": "45000.00", "ref_no": "123456789"},
        {"date": "12/05/2026", "narration": "POS SWIPE STARBUCKS COFFEE MUMBAI", "debit": "450.00", "credit": "", "balance": "44550.00", "ref_no": "POS9981"},
        {"date": "12/05/2026", "narration": "POS SWIPE STARBUCKS COFFEE", "debit": "450.00", "credit": "", "balance": "44100.00", "ref_no": "POS9982"},
    ]

    widget.loaded_statements = [{
        "file_name": "Test_Statement.pdf",
        "bank_name": "Test Bank",
        "transactions": sample_txs
    }]

    print("Running scan...")
    widget.run_duplicate_scan()
    print("Scan complete.")

    print("Rendering clusters again (testing clear layout)...")
    widget.render_clusters()
    print("Re-render complete.")

    print("Testing preset resolution...")
    widget.apply_preset_resolution("keep_last")
    print("Preset resolution complete.")

    print("UI Test finished successfully!")

if __name__ == "__main__":
    test_ui()
