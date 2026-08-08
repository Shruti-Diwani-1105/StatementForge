from parser.digital_parser import DigitalParser, HAS_PDFPLUMBER, HAS_CAMELOT, HAS_TABULA, HAS_FITZ
from parser.ocr_parser import OCRParser

from parser.utils import PDF_LOCK

class TableExtractor:
    """Aligns unstructured bounding boxes of text/words into a structured 2D grid."""

    @classmethod
    def has_selectable_text(cls, pdf_path: str, page_num: int) -> bool:
        """Checks if page has selectable text using fitz or pdfplumber."""
        with PDF_LOCK:
            if HAS_FITZ:
                try:
                    import fitz
                    doc = fitz.open(pdf_path)
                    page = doc[page_num]
                    text = page.get_text()
                    if text and len(text.strip()) > 50:
                        return True
                except Exception:
                    pass
            if HAS_PDFPLUMBER:
                try:
                    import pdfplumber
                    with pdfplumber.open(pdf_path) as pdf:
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        if text and len(text.strip()) > 50:
                            return True
                except Exception:
                    pass
            return False

    @classmethod
    def extract_table_digitally_default(cls, pdf_path: str, page_num: int, logger=None) -> list:
        """Extracts using pdfplumber's default (border lines) strategy."""
        if HAS_PDFPLUMBER:
            try:
                table = DigitalParser.extract_with_pdfplumber_default(pdf_path, page_num)
                if table and len(table) > 1 and any(any(cell for cell in row) for row in table):
                    return table
            except Exception as e:
                if logger:
                    logger.log(f"pdfplumber default failed: {e}")
        return []

    @classmethod
    def extract_table_digitally_text_fallback(cls, pdf_path: str, page_num: int, logger=None) -> list:
        """Extracts using pdfplumber's text-alignment fallback strategy."""
        if HAS_PDFPLUMBER:
            try:
                table = DigitalParser.extract_with_pdfplumber_text(pdf_path, page_num)
                if table and len(table) > 1 and any(any(cell for cell in row) for row in table):
                    return table
            except Exception as e:
                if logger:
                    logger.log(f"pdfplumber text fallback failed: {e}")
        return []

    @classmethod
    def extract_table_digitally(cls, pdf_path: str, page_num: int, logger=None) -> list:
        """Extracts 2D grid table digitally using default or text fallback strategy."""
        table = cls.extract_table_digitally_default(pdf_path, page_num, logger)
        # Enforce that a valid bank statement table should have at least 4 columns (date, narration, amount, balance)
        if table and len(table[0]) >= 4:
            return table
            
        table = cls.extract_table_digitally_text_fallback(pdf_path, page_num, logger)
        if table:
            return table

        if HAS_CAMELOT:
            try:
                table = DigitalParser.extract_with_camelot(pdf_path, page_num)
                if table and len(table) > 1:
                    return table
            except Exception as e:
                if logger:
                    logger.log(f"Camelot failed: {e}")

        if HAS_TABULA:
            try:
                table = DigitalParser.extract_with_tabula(pdf_path, page_num)
                if table and len(table) > 1:
                    return table
            except Exception as e:
                if logger:
                    logger.log(f"Tabula-py failed: {e}")

        if HAS_FITZ:
            try:
                table = DigitalParser.extract_with_fitz(pdf_path, page_num)
                if table and len(table) > 1:
                    return table
            except Exception as e:
                if logger:
                    logger.log(f"PyMuPDF failed: {e}")

        return []

    @classmethod
    def _extract_table_by_dividers(cls, blocks: list, dividers: list) -> list:
        # Group words into vertical lines
        lines = {}
        for w in blocks:
            found = False
            for line_top in lines:
                if abs(w["y0"] - line_top) < 15: # y-coordinate tolerance for OCR lines
                    lines[line_top].append(w)
                    found = True
                    break
            if not found:
                lines[w["y0"]] = [w]
                
        sorted_tops = sorted(lines.keys())
        grid = []
        num_cols = len(dividers) + 1
        
        for top in sorted_tops:
            line_words = lines[top]
            row_cells = [[] for _ in range(num_cols)]
            
            for w in line_words:
                pos = (w["x0"] + w["x1"]) / 2
                col_idx = 0
                for i, div in enumerate(dividers):
                    if pos > div:
                        col_idx = i + 1
                    else:
                        break
                row_cells[col_idx].append(w)
                
            row_text = []
            for cell in row_cells:
                cell_sorted = sorted(cell, key=lambda x: x["x0"])
                txt = " ".join(w["text"] for w in cell_sorted)
                row_text.append(txt)
            grid.append(row_text)
            
        return grid

    @classmethod
    def extract_table_via_ocr(cls, pdf_path: str, page_num: int, logger=None) -> list:
        """Extracts 2D grid table via OCR image parsing and bounding box clustering."""
        try:
            blocks = OCRParser.extract_text_blocks(pdf_path, page_num, logger)
            if blocks:
                # Detect bank name from text blocks
                from parser.bank_detector import BankDetector
                raw_text = " ".join(b["text"] for b in blocks)
                bank_name = BankDetector.detect_bank(raw_text, pdf_path)
                
                if bank_name == "Punjab National Bank":
                    # PNB custom dividers for OCR image coordinates (scale=2.5)
                    dividers = [250, 400, 1040, 1140, 1250]
                    return cls._extract_table_by_dividers(blocks, dividers)
                elif bank_name == "Kotak Mahindra Bank":
                    # Kotak custom dividers for OCR image coordinates (scale=2.5)
                    dividers = [150, 281, 297, 666, 685, 917, 1094, 1267]
                    return cls._extract_table_by_dividers(blocks, dividers)
                    
                return cls._cluster_text_into_grid(blocks)
        except Exception as e:
            if logger:
                logger.log(f"OCR Grid Extraction failed: {e}")
        return []

    @classmethod
    def extract_table_from_page(cls, pdf_path: str, page_num: int, logger=None) -> list:
        """Deprecated: retained for compatibility. Delegates to extract_table_digitally/via_ocr."""
        is_digital = cls.has_selectable_text(pdf_path, page_num)
        if is_digital:
            table = cls.extract_table_digitally(pdf_path, page_num, logger)
            if table and len(table) >= 2:
                return table
        return cls.extract_table_via_ocr(pdf_path, page_num, logger)

    @classmethod
    def _cluster_text_into_grid(cls, blocks, y_tolerance=10, x_tolerance=15) -> list:
        """Clusters bounding boxes of text blocks into columns and rows."""
        if not blocks:
            return []

        # 1. Cluster words into lines (vertical coordinates close enough)
        sorted_by_y = sorted(blocks, key=lambda b: b["y0"])
        lines = []
        for word in sorted_by_y:
            placed = False
            for line in lines:
                line_y = line[0]["y0"]
                if abs(word["y0"] - line_y) < y_tolerance:
                    line.append(word)
                    placed = True
                    break
            if not placed:
                lines.append([word])

        # 2. Sort horizontally in each line and merge close words into cells
        processed_rows = []
        for line in lines:
            sorted_line = sorted(line, key=lambda w: w["x0"])
            merged_cells = []
            current_cell = None
            for w in sorted_line:
                if current_cell is None:
                    current_cell = dict(w)
                elif w["x0"] - current_cell["x1"] < x_tolerance:
                    current_cell["text"] += " " + w["text"]
                    current_cell["x1"] = w["x1"]
                    current_cell["y1"] = max(current_cell["y1"], w["y1"])
                else:
                    merged_cells.append(current_cell)
                    current_cell = dict(w)
            if current_cell:
                merged_cells.append(current_cell)
            processed_rows.append(merged_cells)

        # 3. Find vertical boundaries (global column headers / starts)
        all_x_coords = []
        for row in processed_rows:
            for cell in row:
                all_x_coords.append(cell["x0"])
        
        if not all_x_coords:
            return []

        all_x_coords.sort()
        col_dividers = [all_x_coords[0]]
        for x in all_x_coords[1:]:
            if x - col_dividers[-1] > 35:
                col_dividers.append(x)

        # 4. Fit cells to the closest horizontal column index
        grid_table = []
        num_cols = len(col_dividers)
        for row in processed_rows:
            grid_row = [""] * num_cols
            for cell in row:
                col_idx = min(range(num_cols), key=lambda i: abs(cell["x0"] - col_dividers[i]))
                if grid_row[col_idx]:
                    grid_row[col_idx] += " " + cell["text"]
                else:
                    grid_row[col_idx] = cell["text"]
            grid_table.append(grid_row)

        return grid_table

    @classmethod
    def detect_table_headers(cls, grid_table: list) -> tuple:
        """
        Detects header row in grid_table and returns (headers, header_row_idx).
        If not found, returns (None, -1).
        """
        if not grid_table:
            return None, -1
        import re
        for idx, row in enumerate(grid_table):
            row_str = " ".join(str(c).lower() for c in row)
            has_date = "date" in row_str or "val dt" in row_str or "txn dt" in row_str
            has_other = any(k in row_str for k in ["particulars", "narration", "description", "details", "withdraw", "deposit", "amount", "balance", "debit", "credit"])
            if has_date and has_other:
                # Retrieve the header by combining preceding rows (max 2)
                start_h = max(0, idx - 2)
                combined_header = [""] * len(row)
                for h_idx in range(start_h, idx + 1):
                    for col_idx, cell in enumerate(grid_table[h_idx]):
                        if col_idx < len(combined_header):
                            val = str(cell).strip()
                            if val:
                                if combined_header[col_idx]:
                                    combined_header[col_idx] += " " + val
                                else:
                                    combined_header[col_idx] = val
                headers = [re.sub(r"\s+", " ", h).strip() for h in combined_header]
                return headers, idx
        return None, -1

    @classmethod
    def extract_structured_table(cls, pdf_path: str, page_num: int, logger=None) -> dict:
        """
        Extracts table from a page using PositionalTableBuilder.
        """
        from parser.positional_builder import PositionalTableBuilder
        
        # Cache and share dividers across pages of the same statement
        shared_dividers = getattr(cls, "_shared_dividers", None)
        
        res = PositionalTableBuilder.build_grid(pdf_path, page_num, shared_dividers)
        grid_table = res.get("grid", [])
        headers = res.get("headers")
        dividers = res.get("dividers", [])
        method = res.get("method", "digital")
        
        if dividers and not shared_dividers:
            cls._shared_dividers = dividers
            
        confidence = 0.95 if method == "digital" else 0.80
        if not grid_table:
            confidence = 0.0
            
        return {
            "headers": headers,
            "rows": grid_table,
            "page_number": page_num + 1,
            "method": method,
            "confidence": confidence,
            "header_row_idx": 0 if headers else -1,
            "raw_grid": grid_table
        }
