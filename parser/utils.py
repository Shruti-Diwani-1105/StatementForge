import re
import datetime

class ParserUtils:
    """Shared utility functions for date parsing, number cleaning, and format standardizations."""

    DATE_PATTERNS = [
        r"^\d{1,2}[/\-\.\s]\d{1,2}[/\-\.\s]\d{2,4}$",         # 12/04/2026, 12-04-2026, 12.04.2026, 12 04 26
        r"^\d{1,2}[/\-\.\s][a-zA-Z]{3,9}[/\-\.\s]\d{2,4}$",   # 12-Apr-2026, 12/Apr/26, 12.Apr.2026
        r"^\d{4}[/\-\.\s]\d{1,2}[/\-\.\s]\d{1,2}$",           # 2026-04-12, 2026.04.12
        r"^[a-zA-Z]{3,9}\s*\d{1,2}[,\s/\-\.]+\d{2,4}$",      # March 31, 2026 or March31, 2026
        r"^\d{1,2}\s*[a-zA-Z]{3,9}[,\s/\-\.]+\d{2,4}$",      # 31March, 2026 or 31 March, 2026
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
        val_str = str(val).replace('\n', '').replace('\r', '').strip()
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
        val_str = str(val).replace('\n', '').replace('\r', '').strip()
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
        val_str = str(val).replace('\n', '').replace('\r', '').strip()
        if val_str == "" or val_str.lower() in ["none", "null", "-", "cr", "dr"]:
            return None
            
        clean_test = val_str.replace(",", "").replace("₹", "").replace("$", "").replace("£", "").replace("€", "").strip()
        clean_test = clean_test.replace(" ", "")
        
        if clean_test.lower().endswith("cr"):
            clean_test = clean_test[:-2].strip()
        elif clean_test.lower().endswith("dr"):
            clean_test = clean_test[:-2].strip()
            
        if re.match(r"^[+\-]?\d+(\.\d+)?$", clean_test):
            try:
                if "." in clean_test:
                    return float(clean_test)
                return int(clean_test)
            except ValueError:
                pass
        return val_str

    @classmethod
    def parse_date(cls, val):
        """Attempts to parse standard date strings to datetime.date."""
        if val is None:
            return None
        val_str = str(val).replace('\n', '').replace('\r', '').strip()
        val_str = re.sub(r"\s+", " ", val_str)
        val_str = val_str.title()
        date_formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%Y.%m.%d",
            "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
            "%d %b %Y", "%d-%b-%Y", "%d-%b-%y", "%d.%b.%Y", "%d.%b.%y",
            "%B %d, %Y", "%b %d, %Y",
            "%B%d, %Y", "%b%d, %Y",
            "%B %d %Y", "%b %d %Y",
            "%B%d %Y", "%b%d %Y",
            "%d %B %Y", "%d %b %Y",
            "%d%B, %Y", "%d%b, %Y",
            "%d%B %Y", "%d%b %Y"
        ]
        for fmt in date_formats:
            try:
                dt = datetime.datetime.strptime(val_str, fmt)
                return dt.date()
            except ValueError:
                pass
        return val_str

    @classmethod
    def split_merged_columns(cls, rows: list) -> list:
        """Detects if columns are merged in the digital table (e.g. Serial + Date) and splits them."""
        if not rows:
            return rows
            
        date_pattern = r"^(\d+)\s+(\d{2}[-\/\.]\d{2}[-\/\.]\d{4}|\d{2}[-\/\.]\w{3}[-\/\.]\d{4})$"
        match_count = 0
        for row in rows:
            if row and len(row) > 0:
                cell = str(row[0]).strip()
                if re.match(date_pattern, cell):
                    match_count += 1
                    
        if match_count >= max(1, len(rows) * 0.15):
            new_rows = []
            for row in rows:
                if not row:
                    new_rows.append(row)
                    continue
                new_row = list(row)
                cell0 = str(new_row[0]).strip()
                match = re.match(date_pattern, cell0)
                if match:
                    val_serial = match.group(1)
                    val_date = match.group(2)
                    new_row[0] = val_serial
                    new_row.insert(1, val_date)
                else:
                    if any(x in cell0.lower() for x in ["serial", "no", "date", "transaction", "erial"]):
                        parts = cell0.split(None, 1)
                        if len(parts) == 2:
                            new_row[0] = parts[0]
                            new_row.insert(1, parts[1])
                        else:
                            new_row.insert(1, "")
                    else:
                        new_row.insert(1, "")
                new_rows.append(new_row)
            return new_rows
        return rows
