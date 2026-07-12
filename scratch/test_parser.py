import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.bank_detector import BankDetector
from parser.transaction_parser import TransactionParser
from parser.duplicate_checker import DuplicateChecker
from parser.validation import ValidationService


def run_tests():
    print("=== Testing PDF Parsing Engine Components ===")

    # 1. Test Bank Detection
    sample_text_hdfc = "Welcome to HDFC BANK. This is your statement of account."
    sample_text_sbi = "State Bank of India - E-Statement from 01/04/2026."
    sample_text_boi = "Bank of India statement. Branch IFSC code: BKID0001234."
    sample_text_boi_with_axis_upi = "Bank of India. Transaction list: UPI/1234/REF/AXIS, payment to merchant@okaxis."
    sample_text_au_with_hdfc_upi = "AU Small Finance Bank. Transaction details: UPI/9876/HDFC, user@okhdfcbank."
    
    assert BankDetector.detect_bank(sample_text_hdfc) == "HDFC Bank"
    assert BankDetector.detect_bank(sample_text_sbi) == "State Bank of India"
    assert BankDetector.detect_bank(sample_text_boi) == "Bank of India"
    assert BankDetector.detect_bank(sample_text_boi_with_axis_upi) == "Bank of India"
    assert BankDetector.detect_bank(sample_text_au_with_hdfc_upi) == "AU Small Finance Bank"
    assert BankDetector.detect_bank("Some random content") == "Unknown Bank"
    print("[OK] BankDetector tests passed.")

    # 2. Test Transaction Parser Column Detection
    header_row = ["Txn Date", "Description / Narration", "Chq No.", "Withdrawal (Debit)", "Deposit (Credit)", "Running Balance"]
    rows = [
        header_row,
        ["01/04/2026", "UPI/12345/AMAZON", "", "550.00", "", "10000.00"],
        ["02/04/2026", "SALARY", "UTR789", "", "25000.00", "35000.00"]
    ]
    
    mapping = TransactionParser.detect_columns(rows)
    print(f"Detected columns: {mapping}")
    assert mapping["date"] == 0
    assert mapping["narration"] == 1
    assert mapping["ref_no"] == 2
    assert mapping["debit"] == 3
    assert mapping["credit"] == 4
    assert mapping["balance"] == 5
    print("[OK] TransactionParser column detection tests passed.")

    # 3. Test Transaction Row Parsing & Multi-line Narration Merging
    multi_line_rows = [
        ["01/04/2026", "UPI/12345/AMAZON PAY", "", "550.00", "", "9450.00"],
        ["", "INDIA PRIVATE LIMITED", "", "", "", ""],
        ["", "REFUND ID 999", "", "", "", ""],
        ["02/04/2026", "CASH WITHDRAWAL", "111", "1000.00", "", "8450.00"]
    ]
    
    txs = TransactionParser.parse_rows(multi_line_rows, mapping)
    print(f"Parsed transactions ({len(txs)}):")
    for tx in txs:
        print(tx)
        
    assert len(txs) == 2
    assert txs[0]["date"] == "01/04/2026"
    assert txs[0]["narration"] == "UPI/12345/AMAZON PAY INDIA PRIVATE LIMITED REFUND ID 999"
    assert txs[0]["debit"] == "550.00"
    assert txs[0]["credit"] == ""
    assert txs[0]["balance"] == "9450.00"
    print("[OK] TransactionParser row parsing and multi-line narration merging tests passed.")

    # 4. Test Duplicate Checker
    txs_with_duplicates = [
        {"date": "01/04/2026", "narration": "UPI AMAZON", "debit": "550.00", "credit": "", "balance": "9450.00"},
        {"date": "01/04/2026", "narration": "UPI AMAZON", "debit": "550.00", "credit": "", "balance": "9450.00"},  # Duplicate
        {"date": "01/04/2026", "narration": "UPI SWIGGY", "debit": "150.00", "credit": "", "balance": "9300.00"},  # Valid identical (if repeated, but balance changes)
        {"date": "02/04/2026", "narration": "UPI SWIGGY", "debit": "150.00", "credit": "", "balance": "9150.00"}   # Valid repeated
    ]
    
    deduped = DuplicateChecker.remove_duplicates(txs_with_duplicates)
    print(f"Deduplicated count: {len(deduped)} (expected 3)")
    assert len(deduped) == 3
    print("[OK] DuplicateChecker tests passed.")

    # 5. Test Validation Service
    math_valid_txs = [
        {"date": "01/04/2026", "narration": "OPENING", "debit": "", "credit": "", "balance": "10000.00"},
        {"date": "01/04/2026", "narration": "UPI AMAZON", "debit": "550.00", "credit": "", "balance": "9450.00"},
        {"date": "02/04/2026", "narration": "INTEREST", "debit": "", "credit": "150.00", "balance": "9600.00"}
    ]
    
    res1 = ValidationService.validate_transactions(math_valid_txs)
    assert res1["success"] is True
    assert len(res1["failed_math_indices"]) == 0
    
    math_invalid_txs = [
        {"date": "01/04/2026", "narration": "OPENING", "debit": "", "credit": "", "balance": "10000.00"},
        {"date": "01/04/2026", "narration": "UPI AMAZON", "debit": "550.00", "credit": "", "balance": "9450.00"},
        {"date": "02/04/2026", "narration": "INTEREST", "debit": "", "credit": "150.00", "balance": "9000.00"}  # 9450 + 150 != 9000
    ]
    
    res2 = ValidationService.validate_transactions(math_invalid_txs)
    assert res2["success"] is False
    assert 2 in res2["failed_math_indices"]
    print("[OK] ValidationService tests passed.")

    print("\n=== All Component Tests Passed Successfully ===")


if __name__ == "__main__":
    run_tests()
