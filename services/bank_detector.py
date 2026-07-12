import re

class BankDetector:
    """Helper to detect and extract statement metadata fields from AI JSON response."""

    # Key-value mapping of bank names to text keywords/signatures
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

    @classmethod
    def detect_bank_from_text(cls, text: str) -> str:
        """Detects the bank name from raw text by matching unique signatures."""
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

        # 3. Last-resort fallback: check for any IFSC code prefix anywhere on the page
        ifsc_pattern = r"\b(HDFC|SBIN|ICIC|UTIB|BARB|KKBK|CNRB|PUNB|UBIN|FDRL|INDB|YESB|IDFB|BDBL|BKID|AUBL)[A-Z0-9]{4,8}\b"
        match = re.search(ifsc_pattern, text.upper())
        if match:
            prefix = match.group(1)
            if prefix in mapping:
                scores[mapping[prefix]] += 80

        # Select the bank with the highest score
        best_bank = "Unknown Bank"
        max_score = 0
        for bank, score in scores.items():
            if score > max_score:
                max_score = score
                best_bank = bank
                
        if max_score >= 10:
            return best_bank
            
        return "Unknown Bank"


    @classmethod
    def get_local_parser(cls, bank_name: str):
        """Returns the local parser class for a given bank name, if available."""
        from services.local_parsers.hdfc_parser import HDFCParser
        
        parsers = {
            "HDFC Bank": HDFCParser,
            # Add other local parsers here as they are developed
        }
        return parsers.get(bank_name)


    @classmethod
    def clean_name(cls, name):
        """Cleans formatting spaces and casing of names."""
        if not name:
            return "Unknown"
        name = str(name).strip()
        name = re.sub(r"\s+", " ", name)
        return name

    @classmethod
    def clean_period(cls, period):
        """Cleans the statement period string."""
        if not period:
            return "Unknown Period"
        return str(period).strip()

    @classmethod
    def extract_metadata(cls, ai_json):
        """
        Extracts metadata fields from the Gemini JSON response.
        Provides robust defaults if fields are missing.
        """
        if not isinstance(ai_json, dict):
            ai_json = {}

        # 1. Bank Name detection
        bank_name = ai_json.get("bank_name") or ai_json.get("Bank Name") or ai_json.get("bank") or "Unknown Bank"
        bank_name = cls.clean_name(bank_name)
        
        # 2. Account Holder detection
        account_holder = ai_json.get("account_holder") or ai_json.get("Account Holder") or ai_json.get("holder_name") or "Unknown"
        account_holder = cls.clean_name(account_holder)
        
        # 3. Account Number detection
        account_number = ai_json.get("account_number") or ai_json.get("Account Number") or ai_json.get("account_no") or "Unknown"
        account_number = str(account_number).strip()
        
        # 4. Period detection
        period = ai_json.get("statement_period") or ai_json.get("Statement Period") or ai_json.get("period") or "Unknown Period"
        period = cls.clean_period(period)
        
        # 5. Currency detection
        currency = ai_json.get("currency") or ai_json.get("Currency") or "INR"
        currency = str(currency).strip()

        return {
            "bank_name": bank_name,
            "account_holder": account_holder,
            "account_number": account_number,
            "period": period,
            "currency": currency
        }
