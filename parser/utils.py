import re
import datetime

class ParserUtils:
    """Shared utility functions for date parsing, number cleaning, and format standardizations."""

    DATE_PATTERNS = [
        r"^\d{1,2}[/\-\s]\d{1,2}[/\-\s]\d{2,4}$",         # 12/04/2026, 12-04-2026, 12 04 26
        r"^\d{1,2}[/\-\s][a-zA-Z]{3,9}[/\-\s]\d{2,4}$",   # 12-Apr-2026, 12/Apr/26
        r"^\d{4}[/\-\s]\d{1,2}[/\-\s]\d{1,2}$",           # 2026-04-12
    ]

    @classmethod
    def is_valid_date(cls, val: str) -> bool:
        """Checks if a string fits standard bank statement date patterns."""
        if not val:
            return False
        clean_val = str(val).replace('\n', '').replace('\r', '').strip()
        clean_val = re.sub(r"\s+", " ", clean_val)
        for pattern in cls.DATE_PATTERNS:
            if re.match(pattern, clean_val):
                return True
        return False

    @classmethod
    def clean_amount(cls, val) -> str:
        """Standardizes debit/credit amounts. Returns empty string if zero/blank, else float string."""
        if val is None:
            return ""
        val_str = str(val).strip()
        if val_str == "" or val_str.lower() in ["none", "null", "-", "cr", "dr", "0", "0.0", "0.00"]:
            return ""
        
        # Remove currency symbols and commas
        clean_str = re.sub(r"[^\d\.\-]", "", val_str)
        if not clean_str or clean_str == "-":
            return ""
        try:
            val_float = float(clean_str)
            if val_float == 0.0:
                return ""
            return f"{val_float:.2f}"
        except ValueError:
            return ""

    @classmethod
    def clean_balance(cls, val) -> str:
        """Standardizes running balance fields. Returns clean float string or original if invalid."""
        if val is None:
            return ""
        val_str = str(val).strip()
        if val_str == "" or val_str.lower() in ["none", "null", "-"]:
            return ""
        clean_str = re.sub(r"[^\d\.\-]", "", val_str)
        if not clean_str:
            return ""
        try:
            return f"{float(clean_str):.2f}"
        except ValueError:
            return val_str

    @classmethod
    def parse_numeric(cls, val):
        """Attempts to parse a value to int or float. Returns parsed number, or original string."""
        if val is None:
            return None
        val_str = str(val).strip()
        if val_str == "" or val_str.lower() in ["none", "null", "-", "cr", "dr"]:
            return None
        clean_str = re.sub(r"[^\d\.\-]", "", val_str)
        if not clean_str:
            return val_str
        try:
            if "." in clean_str:
                return float(clean_str)
            return int(clean_str)
        except ValueError:
            return val_str

    @classmethod
    def parse_date(cls, val):
        """Attempts to parse standard date strings to datetime.date."""
        if val is None:
            return None
        val_str = str(val).replace('\n', '').replace('\r', '').strip()
        val_str = re.sub(r"\s+", " ", val_str)
        date_formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
            "%d/%m/%y", "%d-%m-%y",
            "%d %b %Y", "%d-%b-%Y", "%d-%b-%y"
        ]
        for fmt in date_formats:
            try:
                dt = datetime.datetime.strptime(val_str, fmt)
                return dt.date()
            except ValueError:
                pass
        return val_str
