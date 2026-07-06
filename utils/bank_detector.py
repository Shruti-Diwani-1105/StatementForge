import re
import datetime

class BankDetector:
    """Helper to detect Indian banks and parse statement periods from raw text."""
    
    # List of supported banks with detection keywords
    BANKS_METADATA = [
        {"name": "SBI", "keywords": ["state bank of india", "sbi"]},
        {"name": "HDFC", "keywords": ["hdfc bank", "hdfc"]},
        {"name": "ICICI", "keywords": ["icici bank", "icici"]},
        {"name": "Axis", "keywords": ["axis bank"]},
        {"name": "Bank of Baroda", "keywords": ["bank of baroda", "bob "]},
        {"name": "Kotak", "keywords": ["kotak mahindra", "kotak bank"]},
        {"name": "Canara", "keywords": ["canara bank"]},
        {"name": "Union Bank", "keywords": ["union bank of india", "union bank"]},
        {"name": "Punjab National Bank", "keywords": ["punjab national bank", "pnb"]},
        {"name": "Indian Bank", "keywords": ["indian bank"]},
        {"name": "IDBI", "keywords": ["idbi bank", "idbi"]},
        {"name": "Federal Bank", "keywords": ["federal bank"]},
        {"name": "IndusInd", "keywords": ["indusind bank", "indusind"]},
        {"name": "AU Bank", "keywords": ["au small finance", "au bank"]},
        {"name": "Yes Bank", "keywords": ["yes bank"]}
    ]

    @classmethod
    def detect_bank(cls, text):
        """Detects bank name. Returns name string or 'Unknown Bank'."""
        if not text:
            return "Unknown Bank"
            
        text_lower = text.lower()
        for bank in cls.BANKS_METADATA:
            for keyword in bank["keywords"]:
                if keyword in text_lower:
                    return bank["name"]
        return "Unknown Bank"

    @classmethod
    def detect_period(cls, text):
        """
        Detects statement period by scanning for date patterns.
        Returns a string representation of the period, e.g. 'Jun 01, 2026 - Jun 30, 2026'.
        """
        if not text:
            return "Unknown Period"

        # Regex for dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy, etc.
        pattern1 = re.compile(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b")
        # Regex for dd MMM yyyy, e.g. '01 Jun 2026' or '15-Dec-2025'
        months_pattern = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
        pattern2 = re.compile(
            rf"\b(\d{1,2})[\s\-\.](?:{months_pattern})[a-z]*[\s\-\.](\d{2,4})\b", re.IGNORECASE
        )

        dates = []

        # Parse pattern 1 dates
        for match in pattern1.finditer(text):
            day, month, year = match.groups()
            day, month = int(day), int(month)
            year = int(year)
            if year < 100:
                year += 2000
            try:
                dt = datetime.datetime(year, month, day)
                dates.append(dt)
            except ValueError:
                pass

        # Parse pattern 2 dates (simplified month mapper)
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        for match in pattern2.finditer(text):
            day, year = match.groups()
            day = int(day)
            year = int(year)
            if year < 100:
                year += 2000
            
            # Find the matched month word in string
            start, end = match.span()
            matched_str = text[start:end].lower()
            month = 1
            for m_name, m_val in month_map.items():
                if m_name in matched_str:
                    month = m_val
                    break
            try:
                dt = datetime.datetime(year, month, day)
                dates.append(dt)
            except ValueError:
                pass

        if not dates:
            return "Unknown Period"

        # Sort dates to find start and end dates
        dates.sort()
        
        # Filter dates to ensure they make logical sense (e.g. not in the far future or past)
        valid_dates = [d for d in dates if 2000 <= d.year <= datetime.datetime.now().year + 1]
        if not valid_dates:
            return "Unknown Period"

        start_date = valid_dates[0]
        end_date = valid_dates[-1]

        # If only one date is found or they are the same
        if start_date == end_date:
            return start_date.strftime("%b %d, %Y")

        return f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"

    @classmethod
    def detect_account_holder(cls, text, default_name="User"):
        """Attempts to extract account holder name from standard keywords, or returns default."""
        if not text:
            return default_name

        patterns = [
            r"(?:name|account holder|customer name)\s*:\s*([a-zA-Z\s\.]{3,35})\b",
            r"(?:mr\.|ms\.|m/s\.)\s+([a-zA-Z\s\.]{3,35})\b"
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up name if it has line breaks or extra spaces
                name = re.sub(r"\s+", " ", name)
                if len(name) > 3:
                    return name
        return default_name
