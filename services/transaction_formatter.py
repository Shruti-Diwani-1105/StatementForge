import re

class TransactionFormatter:
    """Formats and validates transaction data extracted by the AI."""

    @classmethod
    def clean_amount(cls, value):
        """Cleans and parses a numeric amount string or number to a float."""
        if value is None:
            return 0.0
            
        if isinstance(value, (int, float)):
            return float(value)
            
        # If it is a string, remove currency symbols and commas
        val_str = str(value).strip()
        val_str = re.sub(r"[^\d\.\-]", "", val_str)
        
        try:
            return float(val_str)
        except ValueError:
            return 0.0

    @classmethod
    def clean_balance(cls, value):
        """Cleans and parses the balance field. Returns float or None."""
        if value is None or str(value).strip().lower() in ["", "null", "none"]:
            return None
            
        if isinstance(value, (int, float)):
            return float(value)
            
        val_str = str(value).strip()
        val_str = re.sub(r"[^\d\.\-]", "", val_str)
        
        try:
            return float(val_str)
        except ValueError:
            return None

    @classmethod
    def format_transactions(cls, raw_transactions):
        """
        Cleans, casts, and validates a list of raw transaction dictionaries.
        Ensures each transaction has Date, Narration, Debit, Credit, Balance.
        """
        formatted = []
        if not raw_transactions or not isinstance(raw_transactions, list):
            return formatted

        for tx in raw_transactions:
            if not isinstance(tx, dict):
                continue
                
            # Date check: fallback to empty string if missing
            date_str = str(tx.get("date") or tx.get("Date") or "").strip()
            
            # Narration check: merge multiple spaces/newlines
            narration_str = str(tx.get("narration") or tx.get("Narration") or "Transaction Details").strip()
            narration_str = re.sub(r"\s+", " ", narration_str)
            
            # Debit & Credit formatting (default to 0.0 if empty)
            debit_val = cls.clean_amount(tx.get("debit") if "debit" in tx else tx.get("Debit", 0.0))
            credit_val = cls.clean_amount(tx.get("credit") if "credit" in tx else tx.get("Credit", 0.0))
            
            # Balance formatting (returns float or None)
            balance_val = cls.clean_balance(tx.get("balance") if "balance" in tx else tx.get("Balance"))
            
            formatted.append({
                "date": date_str,
                "narration": narration_str,
                "debit": debit_val,
                "credit": credit_val,
                "balance": balance_val
            })
            
        return formatted
