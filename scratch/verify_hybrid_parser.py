import sys
import os

# Adjust sys.path to run the script from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.bank_detector import BankDetector
from services.local_parsers.hdfc_parser import HDFCParser
from services.transaction_formatter import TransactionFormatter

def test_hdfc_parser():
    print("--- Testing HDFC Local Parser ---")
    
    mock_hdfc_text = """
    HDFC Bank Limited
    Statement of Account for the period 01-Apr-2026 to 30-Apr-2026
    Account Holder: John Doe
    Account Number: 50100098765432
    Currency: INR

    Date         Narration                             Debit       Credit      Balance
    01/04/2026   UPI-AMAZON PAY-INDIA PRIVATE LIMITED  550.00      0.00        25450.00
    04/04/2026   INTEREST CREDIT                       0.00        450.00      25900.00
    12/04/2026   ATM CASH WITHDRAWAL                   5000.00     0.00        20900.00
    15/04/2026   SALARY RECEIVED STATEMENTFORGE        0.00        75000.00    95900.00
    25/04/2026   UPI-SWIGGY FOOD DELIVERY              1250.00     0.00        94650.00
    """
    
    # 1. Test bank detection
    detected = BankDetector.detect_bank_from_text(mock_hdfc_text)
    print(f"Detected Bank: {detected}")
    assert detected == "HDFC Bank", f"Expected HDFC Bank, got: {detected}"
    
    # 2. Test get local parser
    parser_cls = BankDetector.get_local_parser(detected)
    assert parser_cls is HDFCParser, "Expected HDFCParser class"
    
    # 3. Test parsing
    result = parser_cls.parse(mock_hdfc_text)
    print(f"Parsed Metadata: {result['metadata']}")
    assert result["metadata"]["bank_name"] == "HDFC Bank"
    assert result["metadata"]["account_holder"] == "John Doe"
    assert result["metadata"]["account_number"] == "50100098765432"
    assert result["metadata"]["period"] == "01-Apr-2026 to 30-Apr-2026"
    assert result["metadata"]["currency"] == "INR"
    
    txs = result["transactions"]
    print(f"Parsed {len(txs)} transactions:")
    for tx in txs:
        print(f" - {tx['date']} | {tx['narration'][:30]:<30} | Dr: {tx['debit']:<7} | Cr: {tx['credit']:<7} | Bal: {tx['balance']}")
        
    assert len(txs) == 5, f"Expected 5 transactions, got {len(txs)}"
    assert txs[0]["date"] == "01/04/2026"
    assert "UPI-AMAZON PAY" in txs[0]["narration"]
    assert float(txs[0]["debit"]) == 550.0
    assert float(txs[0]["credit"]) == 0.0
    assert float(txs[0]["balance"]) == 25450.0
    
    # Test TransactionFormatter
    formatted_txs = TransactionFormatter.format_transactions(txs)
    assert formatted_txs[0]["debit"] == 550.0
    assert formatted_txs[0]["balance"] == 25450.0
    
    print("HDFC Local Parser tests passed successfully!\n")

def test_balance_validation():
    print("--- Testing Balance Validation Logic ---")
    from parser.validation import ValidationService
    
    # Mathematical sequence correct
    valid_txs = [
        {"date": "01/04/2026", "narration": "Tx 1", "balance": 100.0, "debit": 0.0, "credit": 0.0},
        {"date": "02/04/2026", "narration": "Tx 2", "balance": 80.0, "debit": 20.0, "credit": 0.0},
        {"date": "03/04/2026", "narration": "Tx 3", "balance": 130.0, "debit": 0.0, "credit": 50.0},
    ]
    res = ValidationService.validate_transactions(valid_txs)
    print(f"Valid Sequence Check: {res['success']}")
    assert res['success'] is True, "Expected True for valid ledger sequence"
    
    # Mathematical sequence incorrect
    invalid_txs = [
        {"date": "01/04/2026", "narration": "Tx 1", "balance": 100.0, "debit": 0.0, "credit": 0.0},
        {"date": "02/04/2026", "narration": "Tx 2", "balance": 90.0, "debit": 20.0, "credit": 0.0}, # Should be 80.0
    ]
    res_invalid = ValidationService.validate_transactions(invalid_txs)
    print(f"Invalid Sequence Check (False expected): {res_invalid['success']}")
    assert res_invalid['success'] is False, "Expected False for invalid ledger sequence"
    
    print("Balance Validation tests passed successfully!\n")

if __name__ == "__main__":
    try:
        test_hdfc_parser()
        test_balance_validation()
        print("All tests completed successfully!")
    except AssertionError as e:
        print(f"Assertion failed: {e}")
        sys.exit(1)
