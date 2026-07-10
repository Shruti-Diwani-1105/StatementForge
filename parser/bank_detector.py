import re

class BankDetector:
    """Detects major Indian banks from text content and provides layout signatures."""

    # Keywords/Signatures for each supported bank
    SIGNATURES = {
        "HDFC Bank": ["hdfc bank", "hdfcbank", "housing development finance corporation", "hdfc", "wexunaerstandouiiorla", "we understand your world"],
        "State Bank of India": ["state bank of india", "sbi statement", "sbin", "state bank", "sbi"],
        "ICICI Bank": ["icici bank", "icicibank", "icici"],
        "Axis Bank": ["axis bank", "axisbank", "axis", "utib"],
        "Bank of Baroda": ["bank of baroda", "bob statement", "bob", "baroda", "barb"],
        "Kotak Mahindra Bank": ["kotak mahindra", "kotak bank", "kotak", "kkbk"],
        "Canara Bank": ["canara bank", "canara", "cnrb"],
        "Punjab National Bank": ["punjab national bank", "pnb", "punjab", "punb"],
        "Union Bank of India": ["union bank of india", "union bank", "ubin"],
        "Federal Bank": ["federal bank", "federal", "fdrl"],
        "IndusInd Bank": ["indusind bank", "indusind", "indb"],
        "AU Small Finance Bank": ["au small finance", "au bank", "au small"],
        "Yes Bank": ["yes bank", "yesbank", "yesb"],
        "IDFC First Bank": ["idfc first", "idfc bank", "idfc", "idfb"]
    }

    # Bank-specific header mappings to help layout extraction
    BANK_LAYOUTS = {
        "HDFC Bank": {
            "date_headers": ["date", "txn date", "transaction date"],
            "narration_headers": ["narration", "description", "chq/ref no", "transaction description"],
            "debit_headers": ["debit", "withdrawal", "withdrawal (dr)"],
            "credit_headers": ["credit", "deposit", "deposit (cr)"],
            "balance_headers": ["balance"]
        },
        "State Bank of India": {
            "date_headers": ["txn date", "date", "value date"],
            "narration_headers": ["description", "narration"],
            "debit_headers": ["debit", "withdrawal"],
            "credit_headers": ["credit", "deposit"],
            "balance_headers": ["balance"]
        },
        "ICICI Bank": {
            "date_headers": ["value date", "transaction date", "date"],
            "narration_headers": ["description", "particulars", "narration"],
            "debit_headers": ["debit", "withdrawal"],
            "credit_headers": ["credit", "deposit"],
            "balance_headers": ["balance"]
        }
        # Generic layouts can handle other banks automatically via fallback logic
    }

    @classmethod
    def detect_bank(cls, text: str) -> str:
        """
        Detects the bank name from text by checking case-insensitive keywords and IFSC codes.
        Returns the matching bank name, or 'Unknown Bank' if no match.
        """
        if not text:
            return "Unknown Bank"
        
        text_upper = text.upper()
        # 1. Regex check for IFSC code patterns (highly robust)
        ifsc_pattern = r"\b(HDFC|SBIN|ICIC|UTIB|BARB|KKBK|CNRB|PUNB|UBIN|FDRL|INDB|YESB|IDFB)[A-Z0-9]{4,8}\b"
        match = re.search(ifsc_pattern, text_upper)
        if match:
            prefix = match.group(1)
            mapping = {
                "HDFC": "HDFC Bank",
                "SBIN": "State Bank of India",
                "ICIC": "ICICI Bank",
                "UTIB": "Axis Bank",
                "BARB": "Bank of Baroda",
                "KKBK": "Kotak Mahindra Bank",
                "CNRB": "Canara Bank",
                "PUNB": "Punjab National Bank",
                "UBIN": "Union Bank of India",
                "FDRL": "Federal Bank",
                "INDB": "IndusInd Bank",
                "YESB": "Yes Bank",
                "IDFB": "IDFC First Bank"
            }
            if prefix in mapping:
                return mapping[prefix]

        # 2. Case-insensitive keyword checks
        text_lower = text.lower()
        for bank_name, keywords in cls.SIGNATURES.items():
            if any(kw in text_lower for kw in keywords):
                return bank_name
                
        return "Unknown Bank"


    @classmethod
    def get_layout(cls, bank_name: str) -> dict:
        """Returns bank-specific headers if configured, else returns generic patterns."""
        return cls.BANK_LAYOUTS.get(bank_name, {
            "date_headers": ["date", "txn date", "value date", "post date"],
            "narration_headers": ["narration", "description", "particulars", "remarks"],
            "debit_headers": ["debit", "withdrawal", "amount dr", "dr"],
            "credit_headers": ["credit", "deposit", "amount cr", "cr"],
            "balance_headers": ["balance", "bal"]
        })
