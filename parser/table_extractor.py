from parser.digital_parser import DigitalParser, HAS_PDFPLUMBER, HAS_CAMELOT, HAS_TABULA, HAS_FITZ
from parser.ocr_parser import OCRParser

class TableExtractor:
    """Aligns unstructured bounding boxes of text/words into a structured 2D grid."""

    @classmethod
    def has_selectable_text(cls, pdf_path: str, page_num: int) -> bool:
        """Checks if page has selectable text using fitz or pdfplumber."""
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
    def extract_table_digitally(cls, pdf_path: str, page_num: int, logger=None) -> list:
        """Extracts 2D grid table digitally using pdfplumber, Camelot, Tabula-py, or PyMuPDF."""
        if HAS_PDFPLUMBER:
            try:
                table = DigitalParser.extract_with_pdfplumber(pdf_path, page_num)
                if table and len(table) > 1 and any(any(cell for cell in row) for row in table):
                    return table
            except Exception as e:
                if logger:
                    logger.log(f"pdfplumber failed: {e}")

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
    def extract_table_via_ocr(cls, pdf_path: str, page_num: int, logger=None) -> list:
        """Extracts 2D grid table via OCR image parsing and bounding box clustering."""
        try:
            blocks = OCRParser.extract_text_blocks(pdf_path, page_num, logger)
            if blocks:
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
