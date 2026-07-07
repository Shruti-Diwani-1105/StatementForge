import sys
import os
import datetime

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure UTF-8 output on Windows terminal
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from services.gemini_service import GeminiService
from services.pdf_reader import PDFReader
from services.ocr_service import OCRService
from services.transaction_formatter import TransactionFormatter
from services.excel_generator import ExcelGenerator
from services.bank_detector import BankDetector
from services.mongodb_service import MongoDBService
from services.history_service import HistoryService

def verify():
    print("=== StatementForge Modules Verification ===")
    
    # 1. Check Gemini Service
    api_key = GeminiService.get_api_key()
    print(f"Gemini API Key configuration: {'Found (hidden)' if api_key else 'Missing from .env'}")
    
    # 2. Check MongoDB Service
    mongo_col = MongoDBService.get_collection()
    print(f"MongoDB connection check: {'Connected' if mongo_col is not None else 'Disconnected (using memory fallback)'}")

    # 3. Test Transaction Formatter
    raw_txs = [
        {"date": "01/04/2026", "narration": "UPI AMAZON PAY\nINDIA PRIVATE LIMITED", "debit": "550.00", "credit": "", "balance": "25,450.00"},
        {"date": "02/04/2026", "narration": "INTEREST RECEIVED", "debit": 0, "credit": 120.50, "balance": None}
    ]
    formatted = TransactionFormatter.format_transactions(raw_txs)
    print("\nFormatted Transactions Sample:")
    for tx in formatted:
        print(tx)
        
    assert formatted[0]["debit"] == 550.0
    assert formatted[0]["credit"] == 0.0
    assert formatted[0]["balance"] == 25450.0
    assert formatted[0]["narration"] == "UPI AMAZON PAY INDIA PRIVATE LIMITED"
    
    assert formatted[1]["debit"] == 0.0
    assert formatted[1]["credit"] == 120.50
    assert formatted[1]["balance"] is None
    print("[OK] TransactionFormatter: Success")

    # 4. Test Excel Generator & Suffix Collision Handler
    dummy_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_statement.pdf")
    # Touch dummy PDF file to simulate its existence
    with open(dummy_pdf, "w") as f:
        f.write("dummy pdf content")
        
    print(f"\nDummy PDF path: {dummy_pdf}")
    
    # Run excel generator once
    excel_path1 = ExcelGenerator.generate_excel(
        pdf_path=dummy_pdf,
        bank_name="HDFC Bank",
        account_holder="Test User",
        period="01-Apr-2026 to 30-Apr-2026",
        transactions=formatted
    )
    print(f"Generated Excel 1: {excel_path1}")
    assert os.path.exists(excel_path1)
    
    # Run excel generator a second time to test suffix collision logic
    excel_path2 = ExcelGenerator.generate_excel(
        pdf_path=dummy_pdf,
        bank_name="HDFC Bank",
        account_holder="Test User",
        period="01-Apr-2026 to 30-Apr-2026",
        transactions=formatted
    )
    print(f"Generated Excel 2 (expecting suffix): {excel_path2}")
    assert os.path.exists(excel_path2)
    assert "_(" in excel_path2
    
    # Clean up generated test files
    os.remove(dummy_pdf)
    os.remove(excel_path1)
    os.remove(excel_path2)
    print("[OK] ExcelGenerator & Suffix Collision Handler: Success")

    # 5. History Stats testing
    HistoryService.save_record(
        user_id="test_user_id",
        pdf_path="C:/dummy/path/HDFC_April.pdf",
        excel_path="C:/dummy/path/HDFC_April.xlsx",
        bank_name="HDFC Bank",
        statement_period="01-Apr-2026 to 30-Apr-2026",
        processing_time=1.5,
        total_transactions=len(formatted)
    )
    stats = HistoryService.get_stats("test_user_id")
    print(f"\nAggregated Dashboard Stats: {stats}")
    assert stats["processed"] >= 1
    assert stats["verified"] >= 2
    print("[OK] HistoryService Stats Tracking: Success")
    
    recent = HistoryService.get_recent_activity("test_user_id")
    print(f"Recent Activities list: {recent}")
    assert len(recent) >= 1
    assert recent[0]["file_name"] == "HDFC_April.pdf"
    print("[OK] HistoryService Recent Activity: Success")

    print("\n=== Verification Successful ===")

if __name__ == "__main__":
    verify()
