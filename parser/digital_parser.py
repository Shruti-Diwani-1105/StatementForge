import os

# Dynamic imports
HAS_PDFPLUMBER = False
HAS_CAMELOT = False
HAS_TABULA = False
HAS_FITZ = False
HAS_PANDAS = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    pass

try:
    import camelot
    HAS_CAMELOT = True
except ImportError:
    pass

try:
    import tabula
    HAS_TABULA = True
except ImportError:
    pass

try:
    import fitz # PyMuPDF
    HAS_FITZ = True
except ImportError:
    pass

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pass

class DigitalParser:
    """Extracts tables from digital PDF pages using multiple python libraries (pdfplumber, camelot, tabula-py, PyMuPDF)."""

    @classmethod
    def extract_with_pdfplumber(cls, pdf_path: str, page_num: int) -> list:
        """Extracts using pdfplumber's extract_tables method."""
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber is not installed.")

        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            tables = page.extract_tables({
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_tolerance": 3
            })
            if not tables:
                tables = page.extract_tables()
            if tables:
                largest_table = max(tables, key=len)
                cleaned_table = []
                for row in largest_table:
                    cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    cleaned_table.append(cleaned_row)
                return cleaned_table
        return []

    @classmethod
    def extract_with_camelot(cls, pdf_path: str, page_num: int) -> list:
        """Extracts using camelot lattice/stream methods."""
        if not HAS_CAMELOT:
            raise ImportError("camelot-py is not installed.")

        page_str = str(page_num + 1)
        tables = camelot.read_pdf(pdf_path, pages=page_str, flavor='stream')
        if not tables or len(tables) == 0:
            tables = camelot.read_pdf(pdf_path, pages=page_str, flavor='lattice')
        
        if tables and len(tables) > 0:
            largest_table = max(tables, key=lambda t: len(t.data))
            return [[str(cell).strip() for cell in row] for row in largest_table.data]
        return []

    @classmethod
    def extract_with_tabula(cls, pdf_path: str, page_num: int) -> list:
        """Extracts using tabula-py read_pdf."""
        if not HAS_TABULA or not HAS_PANDAS:
            raise ImportError("tabula-py or pandas is not installed.")

        dfs = tabula.read_pdf(pdf_path, pages=page_num + 1, multiple_tables=True, guess=True)
        if dfs:
            largest_df = max(dfs, key=len)
            table = []
            headers = [str(c).strip() for c in largest_df.columns]
            table.append(headers)
            for _, row in largest_df.iterrows():
                row_vals = [str(val).strip() if pd.notna(val) else "" for val in row]
                table.append(row_vals)
            return table
        return []

    @classmethod
    def extract_with_fitz(cls, pdf_path: str, page_num: int) -> list:
        """Extracts using PyMuPDF (fitz) find_tables or heuristic text clustering."""
        if not HAS_FITZ:
            raise ImportError("PyMuPDF (fitz) is not installed.")

        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        if hasattr(page, "find_tables"):
            tables = page.find_tables()
            if tables and len(tables.tables) > 0:
                largest_table = max(tables.tables, key=lambda t: len(t.extract()))
                return [[str(cell).strip() if cell is not None else "" for cell in row] for row in largest_table.extract()]
        
        # Word block fallback
        words = page.get_text("words")
        if not words:
            return []
            
        blocks = []
        for w in words:
            blocks.append({
                "text": w[4],
                "x0": w[0],
                "y0": w[1],
                "x1": w[2],
                "y1": w[3]
            })
        from parser.table_extractor import TableExtractor
        return TableExtractor._cluster_text_into_grid(blocks)
