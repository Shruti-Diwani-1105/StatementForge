import os
import re
from parser.utils import PDF_LOCK

class PositionalTableBuilder:
    """Reconstructs text grids from coordinate-based word bounding boxes."""

    @classmethod
    def get_words_digital(cls, pdf_path: str, page_num: int) -> tuple:
        """
        Extracts words with exact bounding boxes using pdfplumber or PyMuPDF.
        Returns a tuple: (words_list, page_width, page_height)
        """
        words = []
        page_width = 595.0 # Default A4 width
        page_height = 842.0 # Default A4 height

        with PDF_LOCK:
            # 1. Try pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    if page_num < len(pdf.pages):
                        page = pdf.pages[page_num]
                        page_width = float(page.width)
                        page_height = float(page.height)
                        extracted = page.extract_words()
                        if extracted:
                            for w in extracted:
                                words.append({
                                    "text": w["text"],
                                    "x0": float(w["x0"]),
                                    "y0": float(w["top"]),
                                    "x1": float(w["x1"]),
                                    "y1": float(w["bottom"])
                                })
                            return words, page_width, page_height
            except Exception:
                pass

            # 2. Try fitz (PyMuPDF) fallback
            try:
                import fitz
                doc = fitz.open(pdf_path)
                if page_num < len(doc):
                    page = doc[page_num]
                    rect = page.rect
                    page_width = float(rect.width)
                    page_height = float(rect.height)
                    extracted = page.get_text("words")
                    if extracted:
                        for w in extracted:
                            words.append({
                                "text": w[4],
                                "x0": float(w[0]),
                                "y0": float(w[1]),
                                "x1": float(w[2]),
                                "y1": float(w[3])
                            })
                        return words, page_width, page_height
            except Exception:
                pass

        return words, page_width, page_height

    @classmethod
    def detect_table_boundaries(cls, words: list, page_height: float) -> tuple:
        """
        Detects header row position and footer boundaries.
        Returns (table_top, table_bottom, headers_detected_list, dividers)
        """
        if not words:
            return 0.0, page_height, None, []

        header_keywords = [
            "date", "particulars", "narration", "description", "details", 
            "withdraw", "deposit", "amount", "debit", "credit", "balance", 
            "chq", "ref", "value date", "val dt", "txn dt"
        ]

        # 1. Locate header line by finding y-coordinates with highest header-word concentration
        lines = {}
        for w in words:
            text_lower = w["text"].lower()
            if any(kw in text_lower for kw in header_keywords):
                found = False
                for line_y in lines:
                    if abs(w["y0"] - line_y) < 6:
                        lines[line_y].append(w)
                        found = True
                        break
                if not found:
                    lines[w["y0"]] = [w]

        header_top = None
        header_bottom = None
        header_words = []

        # Find line with at least 3 distinct keyword words
        for line_y in sorted(lines.keys()):
            line_w = lines[line_y]
            kw_matches = set()
            for w in line_w:
                for kw in header_keywords:
                    if kw in w["text"].lower():
                        kw_matches.add(kw)
            if len(kw_matches) >= 3:
                header_top = min(w["y0"] for w in line_w)
                header_bottom = max(w["y1"] for w in line_w)
                # Expand to grab any overlapping header words in that line region
                header_words = [w for w in words if header_top - 5 <= w["y0"] <= header_bottom + 5]
                break

        table_top = header_bottom if header_bottom is not None else 50.0

        # 2. Find footer boundary to cut off summaries or details
        footer_keywords = ["closing balance", "page", "note", "clerk", "officer", "signature", "total debit", "total credit", "carried forward", "brought forward"]
        footer_top = page_height

        for w in words:
            if w["y0"] > table_top:
                text_lower = w["text"].lower()
                if any(kw in text_lower for kw in footer_keywords):
                    if w["y0"] < footer_top:
                        footer_top = w["y0"]

        table_bottom = max(table_top + 10.0, footer_top - 5.0)

        # 3. Build Column Dividers from Header Positions
        dividers = []
        headers_list = []
        if header_words:
            # Group header words horizontally
            sorted_header_words = sorted(header_words, key=lambda x: x["x0"])
            columns_data = []
            for w in sorted_header_words:
                if not columns_data:
                    columns_data.append([w])
                else:
                    last_col = columns_data[-1]
                    # If words are close horizontally, they belong to the same header column (e.g. "Value" and "Date")
                    if w["x0"] - last_col[-1]["x1"] < 15.0:
                        last_col.append(w)
                    else:
                        columns_data.append([w])

            col_bounds = []
            for col in columns_data:
                x0 = min(w["x0"] for w in col)
                x1 = max(w["x1"] for w in col)
                label = " ".join(w["text"] for w in col)
                col_bounds.append((x0, x1))
                headers_list.append(label)

            for i in range(len(col_bounds) - 1):
                # Divider placed 2 points to the left of the next column boundary
                div = col_bounds[i+1][0] - 2.0
                dividers.append(div)

        return table_top, table_bottom, headers_list if headers_list else None, dividers

    @classmethod
    def build_grid(cls, pdf_path: str, page_num: int, shared_dividers: list = None) -> dict:
        """
        Reconstructs the original table on a page into a 2D list grid.
        Returns a dict: {"headers": headers, "grid": grid, "dividers": dividers, "method": method}
        """
        words, page_width, page_height = cls.get_words_digital(pdf_path, page_num)
        method = "digital"
        
        # Fallback to OCR if no words found digitally
        if not words:
            from parser.ocr_parser import OCRParser
            try:
                blocks = OCRParser.extract_text_blocks(pdf_path, page_num)
                if blocks:
                    for b in blocks:
                        words.append({
                            "text": b["text"],
                            "x0": float(b["x0"]),
                            "y0": float(b["y0"]),
                            "x1": float(b["x1"]),
                            "y1": float(b["y1"])
                        })
                    method = "ocr"
            except Exception:
                pass

        if not words:
            return {"headers": None, "grid": [], "dividers": [], "method": "failed"}

        # Boundaries & Column Dividers Detection
        table_top, table_bottom, headers, dividers = cls.detect_table_boundaries(words, page_height)
        
        # Use shared column dividers if headers not detected on this page (continuation page)
        if not dividers and shared_dividers:
            dividers = shared_dividers
            table_top = 0.0 # No headers on this page, start from top

        if not dividers:
            # Fallback dividers if none detected (equally partition page width into 5 columns)
            dividers = [page_width * 0.15, page_width * 0.55, page_width * 0.70, page_width * 0.85]

        # Group words vertically into rows using tolerance
        data_words = [w for w in words if table_top <= w["y0"] <= table_bottom]
        sorted_by_y = sorted(data_words, key=lambda w: w["y0"])
        
        rows = []
        for w in sorted_by_y:
            placed = False
            for r in rows:
                row_y = r[0]["y0"]
                # 5.0 pt tolerance for grouping words on the same physical row line
                if abs(w["y0"] - row_y) < 5.0:
                    r.append(w)
                    placed = True
                    break
            if not placed:
                rows.append([w])

        # Assign cell contents horizontally using x-coordinate dividers
        grid = []
        num_cols = len(dividers) + 1
        for r in rows:
            row_cells = [[] for _ in range(num_cols)]
            for w in r:
                center_x = (w["x0"] + w["x1"]) / 2
                col_idx = 0
                for i, div in enumerate(dividers):
                    if center_x > div:
                        col_idx = i + 1
                    else:
                        break
                row_cells[col_idx].append(w)

            grid_row = []
            for cell in row_cells:
                sorted_cell = sorted(cell, key=lambda x: x["x0"])
                cell_text = " ".join(w["text"] for w in sorted_cell).strip()
                grid_row.append(cell_text)
            
            # Avoid completely empty rows
            if any(grid_row):
                grid.append(grid_row)

        return {
            "headers": headers,
            "grid": grid,
            "dividers": dividers,
            "method": method
        }
