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
    def extract_with_pdfplumber_default(cls, pdf_path: str, page_num: int) -> list:
        """Extracts using pdfplumber's default (border lines) strategy."""
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber is not installed.")
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
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
    def crop_page_to_table(cls, page):
        """Crops a pdfplumber page to the transaction table area to avoid header/footer interference."""
        import re
        try:
            words = page.extract_words()
            if not words:
                return page
                
            # 1. Find the header row
            header_keywords = ["date", "narration", "description", "particulars", "debit", "credit", "balance", "withdrawal", "deposit", "amount"]
            header_words = [w for w in words if any(kw in w["text"].lower() for kw in header_keywords)]
            
            lines = {}
            for w in header_words:
                found = False
                for line_top in lines:
                    if abs(w["top"] - line_top) < 5:
                        lines[line_top].append(w)
                        found = True
                        break
                if not found:
                    lines[w["top"]] = [w]
                    
            header_line_top = None
            header_line_bottom = None
            for line_top in sorted(lines.keys()):
                line_words = lines[line_top]
                unique_kws = set()
                for lw in line_words:
                    for kw in header_keywords:
                        if kw in lw["text"].lower():
                            unique_kws.add(kw)
                if len(unique_kws) >= 2:
                    header_line_top = min(w["top"] for w in line_words)
                    header_line_bottom = max(w["bottom"] for w in line_words)
                    break
            
            # 2. Find footer top
            footer_keywords = ["closing balance", "page", "note", "clerk", "officer", "signature", "total debit", "total credit"]
            start_y = header_line_bottom if header_line_bottom else 0
            footer_words = [w for w in words if any(kw in w["text"].lower() for kw in footer_keywords) and w["top"] > start_y]
            
            footer_top = page.height
            if footer_words:
                footer_lines = {}
                for w in footer_words:
                    found = False
                    for line_top in footer_lines:
                        if abs(w["top"] - line_top) < 5:
                            footer_lines[line_top].append(w)
                            found = True
                            break
                    if not found:
                        footer_lines[w["top"]] = [w]
                
                for lt in sorted(footer_lines.keys()):
                    line_words = footer_lines[lt]
                    is_footer = False
                    for lw in line_words:
                        txt = lw["text"].lower()
                        if any(kw in txt for kw in ["page", "note", "clerk", "officer", "signature", "closing balance"]):
                            is_footer = True
                            break
                    if lt > page.height * 0.8:
                        is_footer = True
                        
                    if is_footer:
                        # If there are date-like transaction words below this footer, the table continues
                        has_data_below = False
                        date_pattern = re.compile(r"\b\d{1,2}[/\-\.\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*[/\-\.\s]+\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*[/\-\.\s]+\d{1,2}[/\-\.\s]+\d{2,4}\b|\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s*\d{1,2}\b|\b\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\b", re.IGNORECASE)
                        for w in words:
                            if w["top"] > lt + 10:
                                if date_pattern.search(w["text"]):
                                    has_data_below = True
                                    break
                        if not has_data_below:
                            footer_top = lt
                            break
                        
            crop_top = 0
            date_pattern = re.compile(r"\b\d{1,2}[/\-\.\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*[/\-\.\s]+\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*[/\-\.\s]+\d{1,2}[/\-\.\s]+\d{2,4}\b|\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s*\d{1,2}\b|\b\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\b", re.IGNORECASE)
            if header_line_top is not None:
                # If there are date-like transaction words above the header, the table continues from the top
                has_data_above = False
                for w in words:
                    if w["top"] < header_line_top - 10:
                        if date_pattern.search(w["text"]):
                            has_data_above = True
                            break
                if has_data_above:
                    crop_top = 0
                else:
                    crop_top = max(0, header_line_top - 20)
            else:
                # Find the first date-like text block to start crop just above it
                date_words = []
                for w in words:
                    if date_pattern.search(w["text"]):
                        date_words.append(w)
                if date_words:
                    first_date_y = min(w["top"] for w in date_words)
                    crop_top = max(0, first_date_y - 20)
                else:
                    crop_top = 80
                
            crop_bottom = min(page.height, footer_top - 2)
            
            if crop_bottom > crop_top:
                return page.crop((0, crop_top, page.width, crop_bottom))
        except Exception:
            pass
        return page

    @classmethod
    def get_explicit_lines(cls, pdf, pdf_path: str, bank_name: str, page_width: float) -> list:
        """Finds explicit vertical divider lines using bank heuristics or dynamic table header word alignments."""
        # 1. Bhuj Mercantile Co Op Bank
        if bank_name and "mercantile" in bank_name.lower():
            return [65, 120, 240, 300, 380, 455, 513, 530]
            
        # 1b. Bhuj Commercial Co-op Bank
        if bank_name and "commercial" in bank_name.lower() and "junagadh" not in bank_name.lower():
            return [75, 320, 415, 470, 522]
            
        # 2. State Bank of India (Portrait)
        if bank_name and "state bank of india" in bank_name.lower():
            if abs(page_width - 595) < 30: # Portrait A4
                return [75, 130, 290, 335, 410, 490]
                
        # 3. Dynamic header-based detection fallback (scans first 3 pages)
        try:
            import re
            for page in pdf.pages[:3]:
                words = page.extract_words()
                if not words:
                    continue
                header_keywords = ["date", "narration", "description", "particulars", "debit", "credit", "balance", "withdrawal", "deposit", "amount"]
                header_words = [w for w in words if any(kw in w["text"].lower() for kw in header_keywords)]
                
                lines = {}
                for w in header_words:
                    found = False
                    for line_top in lines:
                        if abs(w["top"] - line_top) < 5:
                            lines[line_top].append(w)
                            found = True
                            break
                    if not found:
                        lines[w["top"]] = [w]
                        
                header_line_top = None
                header_line_bottom = None
                for line_top in sorted(lines.keys()):
                    line_words = lines[line_top]
                    unique_kws = set()
                    for lw in line_words:
                        for kw in header_keywords:
                            if kw in lw["text"].lower():
                                unique_kws.add(kw)
                    if len(unique_kws) >= 3:
                        header_line_top = min(w["top"] for w in line_words)
                        header_line_bottom = max(w["bottom"] for w in line_words)
                        break
                        
                if header_line_top is not None:
                    all_header_words = [w for w in words if header_line_top - 3 <= w["top"] <= header_line_bottom + 3]
                    # Filter out symbol-only words to prevent dashed/dotted lines from merging columns
                    all_header_words = [w for w in all_header_words if re.sub(r"[^a-zA-Z0-9]", "", w["text"])]
                    
                    header_cols = []
                    for w in sorted(all_header_words, key=lambda x: x["x0"]):
                        if not header_cols:
                            header_cols.append([w])
                        else:
                            last_col = header_cols[-1]
                            if w["x0"] - last_col[-1]["x1"] < 10:
                                last_col.append(w)
                            else:
                                header_cols.append([w])
                    
                    col_bounds = []
                    for col in header_cols:
                        x0 = min(w["x0"] for w in col)
                        x1 = max(w["x1"] for w in col)
                        col_bounds.append((x0, x1))
                        
                    dividers = []
                    for i in range(len(col_bounds) - 1):
                        # Place the divider 3 points to the left of the start of the next column to avoid cutting values
                        div = col_bounds[i+1][0] - 3.0
                        dividers.append(round(div, 1))
                    if len(dividers) >= 4:
                        return dividers
        except Exception:
            pass
        return []

    @classmethod
    def extract_clean_words(cls, page):
        """Groups character objects sequentially in the PDF stream into words, splitting when coordinate jumps occur."""
        chars = page.chars
        if not chars:
            return []
            
        lines = {}
        for c in chars:
            found = False
            for line_top in lines:
                if abs(c["top"] - line_top) < 3:
                    lines[line_top].append(c)
                    found = True
                    break
            if not found:
                lines[c["top"]] = [c]
                
        words = []
        char_to_idx = {id(c): idx for idx, c in enumerate(chars)}
        
        for line_top in sorted(lines.keys()):
            line_chars = lines[line_top]
            line_chars_sorted = sorted(line_chars, key=lambda x: char_to_idx[id(x)])
            
            current_word_chars = []
            for c in line_chars_sorted:
                if not current_word_chars:
                    current_word_chars.append(c)
                else:
                    prev = current_word_chars[-1]
                    gap = c["x0"] - prev["x1"]
                    # Split word if coordinate jumps backwards (meaning overlapping field starting) or horizontal gap > 10 points
                    if c["x0"] < prev["x0"] - 2 or gap > 10:
                        word_text = "".join(x["text"] for x in current_word_chars)
                        words.append({
                            "text": word_text,
                            "x0": min(x["x0"] for x in current_word_chars),
                            "x1": max(x["x1"] for x in current_word_chars),
                            "top": min(x["top"] for x in current_word_chars),
                            "bottom": max(x["bottom"] for x in current_word_chars)
                        })
                        current_word_chars = [c]
                    else:
                        current_word_chars.append(c)
            if current_word_chars:
                word_text = "".join(x["text"] for x in current_word_chars)
                words.append({
                    "text": word_text,
                    "x0": min(x["x0"] for x in current_word_chars),
                    "x1": max(x["x1"] for x in current_word_chars),
                    "top": min(x["top"] for x in current_word_chars),
                    "bottom": max(x["bottom"] for x in current_word_chars)
                })
        return words

    @classmethod
    def extract_table_by_dividers(cls, page, dividers) -> list:
        """Extracts table rows from a page by grouping words vertically and assigning them horizontally to columns using dividers."""
        bank_name = ""
        try:
            from parser.bank_detector import BankDetector
            text_full = page.extract_text() or ""
            bank_name = BankDetector.detect_bank(text_full, "")
        except Exception:
            pass
            
        is_layout_shifted = bool(bank_name and ("mercantile" in bank_name.lower() or ("commercial" in bank_name.lower() and "junagadh" not in bank_name.lower())))
        
        if is_layout_shifted:
            words = cls.extract_clean_words(page)
        else:
            words = page.extract_words()
            
        if not words:
            return []
        
        lines = {}
        for w in words:
            found = False
            for line_top in lines:
                if abs(w["top"] - line_top) < 6:
                    lines[line_top].append(w)
                    found = True
                    break
            if not found:
                lines[w["top"]] = [w]
                
        sorted_tops = sorted(lines.keys())
        grid = []
        num_cols = len(dividers) + 1
        
        for top in sorted_tops:
            line_words = lines[top]
            row_cells = [[] for _ in range(num_cols)]
            
            for w in line_words:
                if is_layout_shifted:
                    pos = w["x0"] + 2
                else:
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
    def extract_with_pdfplumber_text(cls, pdf_path: str, page_num: int) -> list:
        """Extracts using pdfplumber's text-alignment strategy after cropping to table region."""
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber is not installed.")
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            cropped_page = cls.crop_page_to_table(page)
            
            # Detect bank name to apply explicit vertical dividers if needed
            bank_name = ""
            try:
                from parser.bank_detector import BankDetector
                first_page_text = pdf.pages[0].extract_text() or ""
                bank_name = BankDetector.detect_bank(first_page_text, pdf_path)
            except Exception:
                pass

            explicit_lines = cls.get_explicit_lines(pdf, pdf_path, bank_name, page.width)

            if explicit_lines:
                return cls.extract_table_by_dividers(cropped_page, explicit_lines)

            settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_tolerance": 3
            }
            if explicit_lines:
                settings["vertical_strategy"] = "explicit"
                settings["explicit_vertical_lines"] = explicit_lines

            tables = cropped_page.extract_tables(settings)
            if tables:
                max_cols = max(len(t[0]) for t in tables)
                merged_table = []
                for table in tables:
                    for row in table:
                        if len(row) < max_cols:
                            row = list(row) + [""] * (max_cols - len(row))
                        merged_table.append(row)
                
                cleaned_table = []
                for row in merged_table:
                    cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    cleaned_table.append(cleaned_row)
                return cleaned_table
        return []

    @classmethod
    def extract_with_pdfplumber(cls, pdf_path: str, page_num: int) -> list:
        """Wrapper for backward compatibility. Tries default then text fallback."""
        table = cls.extract_with_pdfplumber_default(pdf_path, page_num)
        if not table:
            table = cls.extract_with_pdfplumber_text(pdf_path, page_num)
        return table

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
