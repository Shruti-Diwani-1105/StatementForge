import os
import datetime
import re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class ExcelGenerator:
    """Generates a professional two-sheet Excel file matching StatementForge styling guidelines."""

    @classmethod
    def _parse_numeric(cls, val):
        """Attempts to parse a value to int or float. Returns parsed number, or original string if not numeric, or None if empty."""
        if val is None:
            return None
        val_str = str(val).strip()
        if val_str == "" or val_str.lower() in ["none", "null", "-", "cr", "dr"]:
            return None
        # Remove commas and currency symbols
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
    def _parse_date(cls, val):
        """Attempts to parse standard date strings. Returns datetime.date, or original string."""
        if val is None:
            return None
        val_str = str(val).strip()
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

    @classmethod
    def generate_excel(cls, pdf_path, bank_name, account_holder, period, transactions):
        """
        Generates and saves the formatted Excel spreadsheet beside the original PDF.
        Handles filename collisions by adding (1), (2), etc.
        Returns the absolute path to the generated Excel file.
        """
        from parser.excel_writer import ExcelWriter
        return ExcelWriter.write_excel(pdf_path, bank_name, account_holder, period, transactions)

