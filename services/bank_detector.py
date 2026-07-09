import re

class BankDetector:
    """Helper to detect and extract statement metadata fields from AI JSON response."""

    # Key-value mapping of bank names to text keywords/signatures
    SIGNATURES = {
        "HDFC Bank": ["hdfc bank", "hdfcbank", "housing development finance corporation"],
        "SBI": ["state bank of india", "sbi statement"],
        "ICICI Bank": ["icici bank", "icicibank"],
        "Axis Bank": ["axis bank", "axisbank"],
        "Bank of Baroda": ["bank of baroda", "bob statement"],
        "Kotak Mahindra Bank": ["kotak mahindra", "kotak bank"],
        "Canara Bank": ["canara bank"],
        "Punjab National Bank": ["punjab national bank", "pnb"],
        "Union Bank of India": ["union bank of india", "union bank"],
        "Indian Bank": ["indian bank"],
        "IDBI Bank": ["idbi bank"],
        "Federal Bank": ["federal bank"],
        "IndusInd Bank": ["indusind bank", "indusind"],
        "AU Small Finance Bank": ["au small finance", "au bank"],
        "Yes Bank": ["yes bank", "yesbank"]
    }

    @classmethod
    def detect_bank_from_text(cls, text: str) -> str:
        """Detects the bank name from raw text by matching unique signatures."""
        if not text:
            return "Unknown Bank"
        
        text_lower = text.lower()
        for bank_name, keywords in cls.SIGNATURES.items():
            if any(kw in text_lower for kw in keywords):
                return bank_name
                
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
