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
        "IDFC First Bank": ["idfc first", "idfc bank", "idfc", "idfb"],
        "Bandhan Bank": ["bandhan bank", "bandhan", "bdbl"],
        "Bank of India": ["bank of india", "boi statement", "boi", "bkid"]
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
        },
        "Bandhan Bank": {
            "date_headers": ["transaction date", "date"],
            "narration_headers": ["description", "particulars", "narration"],
            "debit_headers": ["amount dr / cr", "amount dr/cr", "amount (dr/cr)", "dr/cr", "dr / cr"],
            "credit_headers": ["amount dr / cr", "amount dr/cr", "amount (dr/cr)", "dr/cr", "dr / cr"],
            "balance_headers": ["balance"]
        }
    }

    @classmethod
    def detect_bank(cls, text: str) -> str:
        """
        Detects the bank name from text by checking case-insensitive keywords and IFSC codes.
        Returns the matching bank name, or 'Unknown Bank' if no match.
        """
        if not text:
            return "Unknown Bank"
        
        text_lower = text.lower()
        
        # 1. Search for the own IFSC code first (highly specific)
        own_ifsc_match = re.search(r"ifsc(?:\s+code)?\s*[:\-\s]?\s*\b([a-z]{4})0\d{6}\b", text_lower)
        
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
            "IDFB": "IDFC First Bank",
            "BDBL": "Bandhan Bank",
            "BKID": "Bank of India",
            "AUBL": "AU Small Finance Bank"
        }
        
        if own_ifsc_match:
            prefix = own_ifsc_match.group(1).upper()
            if prefix in mapping:
                return mapping[prefix]

        # Initialize scores for all banks
        scores = {bank: 0 for bank in cls.SIGNATURES.keys()}

        # Clean the text of common third-party references (like UPI IDs, UPI/ REF numbers)
        # to avoid them falsely triggering short keywords.
        cleaned_text = text_lower
        cleaned_text = re.sub(r'\b[a-z0-9.\-_]+@[a-z0-9.\-_]+\b', ' ', cleaned_text)
        cleaned_text = re.sub(r'\bupi/[\w/\-]+', ' ', cleaned_text)
        cleaned_text = re.sub(r'\butr/[\w/\-]+', ' ', cleaned_text)

        # Count matches for each bank using scoring
        for bank_name, keywords in cls.SIGNATURES.items():
            for kw in keywords:
                if len(kw) >= 10:
                    count = cleaned_text.count(kw)
                    if count > 0:
                        scores[bank_name] += count * 50
                else:
                    pattern = r'\b' + re.escape(kw) + r'\b'
                    matches = len(re.findall(pattern, cleaned_text))
                    if matches > 0:
                        scores[bank_name] += matches * 10

        # Select the bank with the highest score
        best_bank = "Unknown Bank"
        max_score = 0
        for bank, score in scores.items():
            if score > max_score:
                max_score = score
                best_bank = bank

        # 3. Last-resort fallback: check for any IFSC code prefix anywhere on the page
        # (Only applied if no strong signature match is found to avoid false positives from third-party IFSCs in transaction narratives)
        if max_score < 30:
            ifsc_pattern = r"\b(HDFC|SBIN|ICIC|UTIB|BARB|KKBK|CNRB|PUNB|UBIN|FDRL|INDB|YESB|IDFB|BDBL|BKID|AUBL)[A-Z0-9]{4,8}\b"
            match = re.search(ifsc_pattern, text.upper())
            if match:
                prefix = match.group(1)
                if prefix in mapping:
                    scores[mapping[prefix]] += 80
                    # Recalculate best bank
                    max_score = 0
                    for bank, score in scores.items():
                        if score > max_score:
                            max_score = score
                            best_bank = bank
                
        if max_score >= 10:
            return best_bank
            
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
