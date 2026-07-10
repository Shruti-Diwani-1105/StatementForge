import re
from parser.utils import ParserUtils

class ValidationService:
    """Validates statement parsing integrity, columns existence, date formats, and running balances."""

    COUNT_PATTERNS = [
        r"total transactions\s*:\s*(\d+)",
        r"no\. of transactions\s*:\s*(\d+)",
        r"transaction count\s*:\s*(\d+)",
        r"total transaction\s*:\s*(\d+)",
        r"number of transactions\s*:\s*(\d+)",
        r"no\. of txns\s*:\s*(\d+)"
    ]

    @classmethod
    def extract_expected_count(cls, pdf_text: str) -> int:
        """Looks for transactions summary count statements in the text."""
        if not pdf_text:
            return -1
        text_lower = pdf_text.lower()
        for pattern in cls.COUNT_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        return -1

    @classmethod
    def validate_transactions(cls, transactions: list, expected_count: int = -1) -> dict:
        """
        Runs detailed validation checks:
        1. Count > 0
        2. Required columns exist (date, narration, debit, credit, balance)
        3. Dates are valid format
        4. Debit/Credit are numeric floats or empty strings
        5. Running balance is mathematically consistent (where available)
        """
        result = {
            "success": True,
            "mismatch_warning": None,
            "failed_math_indices": [],
            "invalid_date_indices": [],
            "invalid_format_indices": [],
            "total_extracted": len(transactions),
            "expected_count": expected_count
        }

        # Check 1: Count > 0
        if len(transactions) == 0:
            result["success"] = False
            result["mismatch_warning"] = "No transactions were extracted from the PDF statement."
            return result

        # Check 2: Row count validation vs statement summaries
        if expected_count > 0 and len(transactions) != expected_count:
            result["success"] = False
            result["mismatch_warning"] = (
                f"Count Mismatch: Expected {expected_count} transactions from PDF, "
                f"but extracted {len(transactions)}."
            )

        # Check 3, 4, 5: Row-level column formats & math verification
        required_keys = ["date", "narration", "debit", "credit", "balance"]
        
        for i, tx in enumerate(transactions):
            # Key checks
            if any(k not in tx for k in required_keys):
                result["success"] = False
                result["mismatch_warning"] = "Required columns are missing from the parsed transaction records."
                return result

            # Date format check
            if not ParserUtils.is_valid_date(tx["date"]):
                result["invalid_date_indices"].append(i)

            # Amount format check: must be float values or empty string
            for key in ["debit", "credit"]:
                val = tx[key]
                if val != "":
                    try:
                        float(val)
                    except ValueError:
                        result["invalid_format_indices"].append((i, key))

            # Running balance format check
            bal = tx["balance"]
            if bal != "":
                try:
                    float(bal)
                except ValueError:
                    result["invalid_format_indices"].append((i, "balance"))

        if result["invalid_date_indices"]:
            result["success"] = False
            result["mismatch_warning"] = f"Invalid date formatting found on {len(result['invalid_date_indices'])} transaction rows."
            return result

        if result["invalid_format_indices"]:
            result["success"] = False
            result["mismatch_warning"] = f"Non-numeric amount formats found in columns on {len(result['invalid_format_indices'])} rows."
            return result

        # Check 5: Running balance mathematical consistency
        if len(transactions) > 1:
            for i in range(1, len(transactions)):
                prev = transactions[i - 1]
                curr = transactions[i]
                
                try:
                    prev_bal = float(prev.get("balance") or 0)
                    curr_bal = float(curr.get("balance") or 0)
                    curr_debit = float(curr.get("debit") or 0) if curr.get("debit") else 0.0
                    curr_credit = float(curr.get("credit") or 0) if curr.get("credit") else 0.0
                    
                    if curr.get("balance") != "" and prev.get("balance") != "":
                        expected_bal = round(prev_bal - curr_debit + curr_credit, 2)
                        actual_bal = round(curr_bal, 2)
                        
                        if abs(actual_bal - expected_bal) > 0.05:
                            result["failed_math_indices"].append(i)
                except Exception:
                    pass

        if result["failed_math_indices"]:
            result["success"] = False
            if not result["mismatch_warning"]:
                result["mismatch_warning"] = (
                    f"Balance verification math failed at {len(result['failed_math_indices'])} transaction rows. "
                    "Ledger statements do not calculate consistently."
                )

        return result
