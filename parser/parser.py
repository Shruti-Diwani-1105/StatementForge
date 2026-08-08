import os
import time
import re

from parser.digital_parser import HAS_PDFPLUMBER, HAS_FITZ
from parser.bank_detector import BankDetector
from parser.page_processor import PageProcessor
from parser.duplicate_checker import DuplicateChecker
from parser.validation import ValidationService
from parser.ocr_parser import OCRParser
from parser.logger import ParserLogger
from parser.table_extractor import TableExtractor
from parser.transaction_parser import TransactionParser

if HAS_FITZ:
    import fitz


class PDFStatementParser:
    """Orchestrator coordinating page-by-page streaming, validation, logging, and excel generation."""

    @classmethod
    def get_page_count(cls, pdf_path: str) -> int:
        """Returns the number of pages in the PDF file."""
        if HAS_FITZ:
            try:
                doc = fitz.open(pdf_path)
                return len(doc)
            except Exception:
                pass
        if HAS_PDFPLUMBER:
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    return len(pdf.pages)
            except Exception:
                pass
        return 0

    @classmethod
    def extract_first_page_text(cls, pdf_path: str, logger=None) -> str:
        """Extracts text from the first page for metadata signature analysis."""
        if HAS_FITZ:
            try:
                doc = fitz.open(pdf_path)
                if len(doc) > 0:
                    text = doc[0].get_text().strip()
                    if len(text) > 50:
                        return text
            except Exception:
                pass
        
        if HAS_PDFPLUMBER:
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    if len(pdf.pages) > 0:
                        text = pdf.pages[0].extract_text()
                        if text and len(text.strip()) > 50:
                            return text
            except Exception:
                pass
                
        try:
            return OCRParser.extract_raw_text(pdf_path, 0, logger)
        except Exception:
            return ""

    @classmethod
    def detect_bank_from_pdf(cls, pdf_path: str) -> str:
        """
        Scans all pages of the PDF to identify the bank name.
        Looks for IFSC prefixes, signature strings, and headers/footers.
        """
        # Unique IFSC prefixes mapping
        ifsc_prefixes = {
            "SBIN": "State Bank of India",
            "HDFC": "HDFC Bank",
            "ICIC": "ICICI Bank",
            "UTIB": "Axis Bank",
            "KKBK": "Kotak Mahindra Bank",
            "BARB": "Bank of Baroda",
            "CNRB": "Canara Bank",
            "UBIN": "Union Bank of India",
            "PUNB": "Punjab National Bank",
            "IDFB": "IDFC First Bank",
            "INDB": "IndusInd Bank",
            "YESB": "Yes Bank",
            "AUBL": "AU Small Finance Bank",
            "FDRL": "Federal Bank",
            "RATN": "RBL Bank",
            "SIBL": "South Indian Bank",
            "BDBL": "Bandhan Bank",
            "BKID": "Bank of India"
        }

        # Check filename first (instant & highly reliable fallback)
        import os
        file_name_lower = os.path.basename(pdf_path).lower()
        filename_mapping = {
            "state bank of india": "State Bank of India",
            "sbi": "State Bank of India",
            "hdfc": "HDFC Bank",
            "icici": "ICICI Bank",
            "axis": "Axis Bank",
            "bank of baroda": "Bank of Baroda",
            "bob": "Bank of Baroda",
            "kotak": "Kotak Mahindra Bank",
            "canara": "Canara Bank",
            "union bank": "Union Bank of India",
            "punjab national": "Punjab National Bank",
            "pnb": "Punjab National Bank",
            "panjab": "Punjab National Bank",
            "idfc": "IDFC First Bank",
            "indusind": "IndusInd Bank",
            "yes bank": "Yes Bank",
            "yesb": "Yes Bank",
            "federal": "Federal Bank",
            "bandhan": "Bandhan Bank",
            "bank of india": "Bank of India",
            "boi": "Bank of India",
            "cbi": "Central Bank of India",
            "indian bank": "Indian Bank"
        }
        for kw, bank_name in filename_mapping.items():
            if kw in file_name_lower:
                return bank_name
        if re.search(r"\bau\b", file_name_lower):
            return "AU Small Finance Bank"

        pages_text = []

        # 1. Extract digital text from all pages and match signatures
        if HAS_FITZ:
            try:
                doc = fitz.open(pdf_path)
                for idx in range(len(doc)):
                    text = doc[idx].get_text()
                    if text:
                        # Match bank using BankDetector
                        bank = BankDetector.detect_bank(text, pdf_path)
                        if bank != "Unknown Bank":
                            return bank
                        pages_text.append(text)
            except Exception:
                pass
        
        if not pages_text and HAS_PDFPLUMBER:
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    for idx in range(len(pdf.pages)):
                        text = pdf.pages[idx].extract_text()
                        if text:
                            # Match bank using BankDetector
                            bank = BankDetector.detect_bank(text, pdf_path)
                            if bank != "Unknown Bank":
                                return bank
                            pages_text.append(text)
            except Exception:
                pass

        # 2. Run local OCR page-by-page on first 3 pages until a match is found (safe offline fallback)
        page_count = cls.get_page_count(pdf_path)
        for idx in range(min(3, page_count)):
            # Only run OCR if digital check was completely blank
            if len(pages_text) <= idx:
                try:
                    text = OCRParser.extract_raw_text(pdf_path, idx)
                    if text:
                        text_upper = text.upper()
                        # Check IFSC
                        match = re.search(r"\b([A-Z]{4})0\d{6}\b", text_upper)
                        if match:
                            prefix = match.group(1)
                            if prefix in ifsc_prefixes:
                                return ifsc_prefixes[prefix]
                        
                        bank = BankDetector.detect_bank(text, pdf_path)
                        if bank != "Unknown Bank":
                            return bank
                        pages_text.append(text)
                except Exception:
                    pass

        # 3. Vision-based detection fallback on first page image (last-resort online fallback)
        try:
            pil_image = OCRParser.render_pdf_page_to_pil(pdf_path, 0)
            from services.gemini_service import GeminiService
            bank = GeminiService.detect_bank_from_image(pil_image)
            if bank != "Unknown Bank":
                return bank
        except Exception:
            pass

        # 4. Relaxed keyword checks on combined pages text using BankDetector
        combined = "\n".join(pages_text)
        if combined.strip():
            bank = BankDetector.detect_bank(combined)
            if bank != "Unknown Bank":
                return bank

        return "Unknown Bank"




    @classmethod
    def extract_metadata(cls, text: str, pdf_path: str = None) -> dict:
        """Extracts bank name, holder, account number, period, and currency using regex."""
        metadata = {
            "bank_name": "Unknown Bank",
            "account_holder": "Unknown",
            "account_number": "Unknown",
            "period": "Unknown Period",
            "currency": "INR"
        }

        if not text:
            return metadata

        if pdf_path:
            metadata["bank_name"] = cls.detect_bank_from_pdf(pdf_path)
        else:
            metadata["bank_name"] = BankDetector.detect_bank(text, pdf_path)

        holder_patterns = [
            r"(?:Account Holder|Customer Name|Name|Primary Holder)\s*:\s*([A-Za-z \t\.]+)",
            r"Holder\s*:\s*([A-Za-z \t\.]+)"
        ]
        for pattern in holder_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["account_holder"] = match.group(1).strip()
                break

        # Cleanup/Fix for "Account holder address" or similar layout-based parsing errors
        holder_lower = metadata["account_holder"].lower()
        if holder_lower in ("", "unknown", "account holder address", "holder address") or "account holder address" in holder_lower:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            found = False
            
            # Fallback 1: Look for lines containing Indian name structures (W/O, S/O, D/O)
            for idx, line in enumerate(lines):
                if any(x in line.lower() for x in [" w/o ", " s/o ", " d/o ", " w/o:", " s/o:", " d/o:"]):
                    name_cand = line
                    if idx + 1 < len(lines):
                        next_line = lines[idx+1]
                        if "account holder" in next_line.lower() or "customer name" in next_line.lower():
                            if idx + 2 < len(lines):
                                next_line = lines[idx+2]
                        if next_line.replace(" ", "").isalpha() and len(next_line) > 2 and next_line.lower() not in ("address", "customer", "account", "holder", "number"):
                            name_cand += " " + next_line
                    metadata["account_holder"] = name_cand
                    found = True
                    break
                    
            # Fallback 2: Look at the line immediately preceding the "Account holder name" label
            if not found:
                for idx, line in enumerate(lines):
                    if "account holder name" in line.lower() or "customer name" in line.lower():
                        if idx > 0:
                            name_cand = lines[idx-1]
                            if idx + 1 < len(lines):
                                next_line = lines[idx+1]
                                if next_line.replace(" ", "").isalpha() and len(next_line) > 2 and next_line.lower() not in ("address", "customer", "account", "holder", "number"):
                                    name_cand += " " + next_line
                            metadata["account_holder"] = name_cand
                            break

        acc_patterns = [
            r"(?:Account Number|A/c No\.?|Account No\.?|Acc No\.?)\s*:\s*(\w+)",
            r"Account\s+No\s+(\w+)",
            r"a/c\s+no\s+(\w+)"
        ]
        for pattern in acc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["account_number"] = match.group(1).strip()
                break

        period_patterns = [
            r"period(?:\s+of)?(?:\s+account)?:\s*(.*?)(?:\n|$)",
            r"period\s+(\d{2}-\w{3}-\d{4}\s+to\s+\d{2}-\w{3}-\d{4})",
            r"period\s+([\d/]+\s+to\s+[\d/]+)",
            r"statement of account for\s*(.*?)(?:\n|$)",
            r"(?:From|from)\s+([\d\-/\.\w]+)\s+(?:To|to)\s+([\d\-/\.\w]+)"
        ]
        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if "from" in pattern and len(match.groups()) >= 2:
                    metadata["period"] = f"{match.group(1).strip()} to {match.group(2).strip()}"
                else:
                    metadata["period"] = match.group(1).strip()
                break

        if "USD" in text or "$" in text:
            metadata["currency"] = "USD"
        elif "EUR" in text or "€" in text:
            metadata["currency"] = "EUR"

        # Kotak Specific Fallbacks / General Regex Fallbacks
        if metadata["account_holder"] in ("", "Unknown"):
            kotak_holder_match = re.search(r"^([A-Za-z\s\.]+?)\s*(?:Account|A/c)\s*No\b", text, re.MULTILINE | re.IGNORECASE)
            if kotak_holder_match:
                metadata["account_holder"] = kotak_holder_match.group(1).strip()

        if metadata["account_number"] in ("", "Unknown"):
            kotak_acc_match = re.search(r"(?:Account|A/c)\s*No[.,\-\s]*\s*(\d+)", text, re.IGNORECASE)
            if kotak_acc_match:
                metadata["account_number"] = kotak_acc_match.group(1).strip()

        if metadata["period"] in ("", "Unknown Period"):
            kotak_period_match = re.search(r"(\d{2}\s+[A-Za-z]{3}\s+\d{4})\s*[\-to\s]+\s*(\d{2}\s+[A-Za-z]{3}\s+\d{4})", text, re.IGNORECASE)
            if kotak_period_match:
                metadata["period"] = f"{kotak_period_match.group(1).strip()} to {kotak_period_match.group(2).strip()}"

        return metadata

    @classmethod
    def get_logical_mapping(cls, headers: list) -> dict:
        mapping = {}
        for idx, h in enumerate(headers):
            h_clean = str(h).lower().replace("_", " ").replace("\n", " ").strip()
            h_no_space = h_clean.replace(" ", "")
            if any(x in h_clean for x in ["balance", "bal"]):
                mapping["balance"] = idx
            elif "value date" in h_clean or "val date" in h_clean or "valuedate" in h_no_space or "valdate" in h_no_space:
                mapping["value_date"] = idx
            elif "date" in h_clean or "dt" in h_clean:
                if "date" not in mapping:
                    mapping["date"] = idx
                else:
                    mapping["value_date"] = idx
            elif any(x in h_clean for x in ["narration", "description", "particulars", "remarks", "details"]):
                mapping["narration"] = idx
            elif any(x in h_clean for x in ["chq no", "cheque", "ref no", "reference", "utr", "instrument"]):
                mapping["ref_no"] = idx
            elif any(x in h_clean for x in ["debit", "withdrawal", "withdraw", "payment"]):
                mapping["debit"] = idx
            elif any(x in h_clean for x in ["credit", "deposit", "receipt"]):
                mapping["credit"] = idx
        return mapping

    @classmethod
    def get_column_alignment(cls, page_headers, doc_headers, page_mapping, doc_mapping):
        alignment = {}
        for doc_idx, doc_h in enumerate(doc_headers):
            logical_type = None
            for k, v in doc_mapping.items():
                if v == doc_idx:
                    logical_type = k
                    break
            
            if logical_type and page_mapping and logical_type in page_mapping:
                alignment[doc_idx] = page_mapping[logical_type]
            else:
                doc_h_clean = doc_h.lower().strip()
                best_idx = None
                if page_headers:
                    for page_idx, page_h in enumerate(page_headers):
                        if page_h.lower().strip() == doc_h_clean:
                            best_idx = page_idx
                            break
                if best_idx is not None:
                    alignment[doc_idx] = best_idx
                elif page_headers and len(page_headers) == len(doc_headers):
                    alignment[doc_idx] = doc_idx
        return alignment

    @classmethod
    def parse(cls, pdf_path: str, progress_callback=None) -> dict:
        """
        Coordinates page-by-page parsing using streaming.
        Logs details page-by-page to a ParserLogger.
        Returns the structured result payload.
        """
        logger = ParserLogger()
        start_time = time.time()
        
        logger.log("Opening PDF...")
        
        page_count = cls.get_page_count(pdf_path)
        if page_count == 0:
            raise ValueError("The PDF file appears to be empty or corrupted.")

        first_page_text = cls.extract_first_page_text(pdf_path, logger)
        meta = cls.extract_metadata(first_page_text, pdf_path)
        
        logger.log(f"Bank Detected: {meta['bank_name']}")
        logger.log(f"Total Pages: {page_count}")
        logger.log("-" * 32)

        column_mapping = None
        failed_pages = []
        document_original_headers = None

        is_scanned = True
        if first_page_text and len(first_page_text.strip()) > 100:
            is_scanned = False

        results = [None] * page_count
        first_tx_page_idx = -1

        # Sequential Phase: Process pages sequentially until we get a column mapping
        for idx in range(page_count):
            if progress_callback:
                try:
                    import inspect
                    sig = inspect.signature(progress_callback)
                    if len(sig.parameters) >= 3:
                        progress_callback(idx + 1, page_count, 0)
                    else:
                        progress_callback(idx + 1, page_count)
                except Exception:
                    try:
                        progress_callback(idx + 1, page_count, 0)
                    except Exception:
                        pass

            is_page_digital = TableExtractor.has_selectable_text(pdf_path, idx)
            try:
                page_txs, page_headers, page_mapping, method_used, grid_table, confidence = PageProcessor.process_page(pdf_path, idx, None, logger)
                
                _, h_row_idx = TableExtractor.detect_table_headers(grid_table)
                results[idx] = {
                    "success": True,
                    "transactions": page_txs,
                    "page_headers": page_headers,
                    "page_mapping": page_mapping,
                    "method": method_used,
                    "grid_table": grid_table,
                    "confidence": confidence,
                    "header_row_idx": h_row_idx,
                    "error": None
                }
                logger.log_page_success(idx + 1, is_page_digital, len(page_txs), method_used)
                
                if page_txs:
                    column_mapping = page_mapping
                    if page_headers:
                        document_original_headers = page_headers
                    first_tx_page_idx = idx
                    break
            except Exception as e:
                results[idx] = {
                    "success": False,
                    "transactions": [],
                    "page_headers": None,
                    "page_mapping": None,
                    "method": "Failed",
                    "grid_table": [],
                    "confidence": 0.0,
                    "header_row_idx": -1,
                    "error": str(e)
                }
                failed_pages.append(idx + 1)
                logger.log_page_failure(idx + 1, str(e))

        # Parallel Phase: Process remaining pages concurrently using the detected column mapping
        remaining_pages = range(first_tx_page_idx + 1, page_count)
        
        # Define thread-safe page processing target for parallel phase
        def process_single_page(page_idx, shared_mapping):
            try:
                page_txs, page_headers, page_mapping, method_used, grid_table, confidence = PageProcessor.process_page(pdf_path, page_idx, shared_mapping, None)
                _, h_row_idx = TableExtractor.detect_table_headers(grid_table)
                return page_idx, True, page_txs, page_headers, page_mapping, method_used, grid_table, confidence, h_row_idx, None
            except Exception as e:
                return page_idx, False, [], None, None, "Failed", [], 0.0, -1, str(e)

        if remaining_pages:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            max_workers = min(8, os.cpu_count() or 4)
            completed_count = first_tx_page_idx + 1
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_page = {
                    executor.submit(process_single_page, i, column_mapping): i 
                    for i in remaining_pages
                }
                
                for future in as_completed(future_to_page):
                    res_idx, success, page_txs, page_headers, page_mapping, method_used, grid_table, confidence, h_row_idx, error_msg = future.result()
                    results[res_idx] = {
                        "success": success,
                        "transactions": page_txs,
                        "page_headers": page_headers,
                        "page_mapping": page_mapping,
                        "method": method_used,
                        "grid_table": grid_table,
                        "confidence": confidence,
                        "header_row_idx": h_row_idx,
                        "error": error_msg
                    }
                    completed_count += 1
                    
                    if progress_callback:
                        try:
                            tx_count = sum(len(r["transactions"]) for r in results if r and r["success"])
                            import inspect
                            sig = inspect.signature(progress_callback)
                            if len(sig.parameters) >= 3:
                                progress_callback(completed_count, page_count, tx_count)
                            else:
                                progress_callback(completed_count, page_count)
                        except Exception:
                            try:
                                progress_callback(completed_count, page_count, 0)
                            except Exception:
                                pass

            # Log parallel results in sequential order
            for idx in remaining_pages:
                res = results[idx]
                is_page_digital = TableExtractor.has_selectable_text(pdf_path, idx)
                if res["success"]:
                    logger.log_page_success(idx + 1, is_page_digital, len(res["transactions"]), res["method"])
                else:
                    failed_pages.append(idx + 1)
                    logger.log_page_failure(idx + 1, res["error"])

        # Determine Document-Level Headers if still None
        if not document_original_headers:
            for res in results:
                if res and res["success"] and res["page_headers"]:
                    document_original_headers = res["page_headers"]
                    break
        if not document_original_headers:
            document_original_headers = ["Date", "Narration", "Debit", "Credit", "Balance"]
        
        document_original_mapping = cls.get_logical_mapping(document_original_headers)

        # 1. Cross-Page Row Reconstruction (Orphan Merging)
        for page_idx in range(1, page_count):
            prev_res = results[page_idx - 1]
            curr_res = results[page_idx]
            if not prev_res or not curr_res or not prev_res["success"] or not curr_res["success"]:
                continue
                
            prev_txs = prev_res["transactions"]
            curr_txs = curr_res["transactions"]
            curr_grid = curr_res["grid_table"]
            
            if not prev_txs or not curr_grid:
                continue
                
            header_idx = curr_res["header_row_idx"]
            start_data_idx = header_idx + 1 if header_idx != -1 else 0
            first_tx_idx = curr_txs[0].get("_grid_row_idx", len(curr_grid)) if curr_txs else len(curr_grid)
            
            orphan_rows = curr_grid[start_data_idx:first_tx_idx]
            valid_orphans = []
            for r in orphan_rows:
                r_str = " ".join(str(c).lower() for c in r)
                if not any(str(c).strip() for c in r) or TransactionParser.META_REGEX.search(r_str):
                    continue
                valid_orphans.append(r)
                
            if valid_orphans:
                last_tx = prev_txs[-1]
                curr_mapping = curr_res["page_mapping"] or {}
                narr_col_idx = curr_mapping.get("narration")
                
                orphan_texts = []
                for r in valid_orphans:
                    if narr_col_idx is not None and narr_col_idx < len(r):
                        txt = str(r[narr_col_idx]).strip()
                        if txt:
                            orphan_texts.append(txt)
                
                if orphan_texts:
                    orphan_narration = " ".join(orphan_texts)
                    last_tx["narration"] += " " + orphan_narration
                    print(f"Cross-Page Merging: Page {page_idx+1} orphans merged into page {page_idx} last transaction.")
                    
                    # Merge wrapped amount values if needed
                    for r in valid_orphans:
                        deb_idx = curr_mapping.get("debit")
                        if deb_idx is not None and deb_idx < len(r):
                            val = str(r[deb_idx]).strip()
                            if val and not last_tx["debit"]:
                                from parser.utils import ParserUtils
                                last_tx["debit"] = ParserUtils.clean_amount(val)
                        cred_idx = curr_mapping.get("credit")
                        if cred_idx is not None and cred_idx < len(r):
                            val = str(r[cred_idx]).strip()
                            if val and not last_tx["credit"]:
                                from parser.utils import ParserUtils
                                last_tx["credit"] = ParserUtils.clean_amount(val)
                        bal_idx = curr_mapping.get("balance")
                        if bal_idx is not None and bal_idx < len(r):
                            val = str(r[bal_idx]).strip()
                            if val and not last_tx["balance"]:
                                from parser.utils import ParserUtils
                                last_tx["balance"] = ParserUtils.clean_balance(val)

        # 2. Build aligned raw transactions
        all_transactions = []
        for res_idx, res in enumerate(results):
            if not res or not res["success"]:
                continue
                
            page_num = res_idx + 1
            page_txs = res["transactions"]
            grid_table = res["grid_table"]
            page_headers = res["page_headers"]
            page_mapping = res["page_mapping"]
            method = res["method"]
            confidence = res["confidence"]
            
            col_align = cls.get_column_alignment(page_headers, document_original_headers, page_mapping, document_original_mapping)
            
            for i, tx in enumerate(page_txs):
                r_start = tx.get("_grid_row_idx")
                if r_start is None:
                    r_start = i
                
                tx["_source_page"] = page_num
                tx["_source_row"] = r_start
                tx["_method"] = method
                tx["_confidence"] = confidence
                
                if grid_table and r_start is not None and r_start < len(grid_table):
                    r_end = page_txs[i+1].get("_grid_row_idx", len(grid_table)) if i+1 < len(page_txs) else len(grid_table)
                    aligned_row = []
                    for doc_idx, doc_h in enumerate(document_original_headers):
                        p_idx = col_align.get(doc_idx)
                        if p_idx is not None:
                            cells = []
                            for r_idx in range(r_start, r_end):
                                if r_idx < len(grid_table) and p_idx < len(grid_table[r_idx]):
                                    cells.append(str(grid_table[r_idx][p_idx]).strip())
                                    
                            logical_type = None
                            for k, v in document_original_mapping.items():
                                if v == doc_idx:
                                    logical_type = k
                                    break
                                    
                            if logical_type == "narration":
                                aligned_row.append(" ".join(c for c in cells if c))
                            else:
                                aligned_row.append(next((c for c in cells if c), ""))
                        else:
                            aligned_row.append("")
                    tx["_raw_row"] = aligned_row
                else:
                    # Construct raw_row from normalized keys
                    aligned_row = []
                    for doc_idx, doc_h in enumerate(document_original_headers):
                        logical_type = None
                        for k, v in document_original_mapping.items():
                            if v == doc_idx:
                                logical_type = k
                                break
                        if logical_type:
                            aligned_row.append(str(tx.get(logical_type, "")))
                        else:
                            aligned_row.append("")
                    tx["_raw_row"] = aligned_row
                
                all_transactions.append(tx)

        # 3. Post-processing deduplication
        initial_count = len(all_transactions)
        all_transactions = DuplicateChecker.remove_duplicates(all_transactions)

        # 4. Chronological year correction post-processing
        try:
            import datetime
            from parser.utils import ParserUtils
            valid_dates = []
            for tx in all_transactions:
                parsed = ParserUtils.parse_date(tx.get("date"))
                if isinstance(parsed, datetime.date):
                    valid_dates.append(parsed)
                else:
                    valid_dates.append(None)
                    
            period_years = [int(y) for y in re.findall(r"\b(20\d{2})\b", meta.get("period", ""))]
            if period_years:
                min_year = min(period_years)
                max_year = max(period_years)
                
                for idx in range(len(all_transactions)):
                    d = valid_dates[idx]
                    if d and isinstance(d, datetime.date):
                        if d.year < min_year or d.year > max_year:
                            prev_year = None
                            for j in range(idx - 1, -1, -1):
                                if valid_dates[j] and isinstance(valid_dates[j], datetime.date) and min_year <= valid_dates[j].year <= max_year:
                                    prev_year = valid_dates[j].year
                                    break
                            next_year = None
                            for j in range(idx + 1, len(all_transactions)):
                                if valid_dates[j] and isinstance(valid_dates[j], datetime.date) and min_year <= valid_dates[j].year <= max_year:
                                    next_year = valid_dates[j].year
                                    break
                                    
                            inferred_year = prev_year or next_year or min_year
                            if prev_year and next_year:
                                if prev_year == next_year:
                                    inferred_year = prev_year
                                else:
                                    if idx > 0 and valid_dates[idx-1] and isinstance(valid_dates[idx-1], datetime.date):
                                        if d.month >= valid_dates[idx-1].month:
                                            inferred_year = prev_year
                                        else:
                                            inferred_year = next_year
                                            
                            orig_str = all_transactions[idx]["date"]
                            corrected_str = orig_str.replace(str(d.year), str(inferred_year))
                            all_transactions[idx]["date"] = corrected_str
                            valid_dates[idx] = d.replace(year=inferred_year)
                            
                            # Update raw row date cell
                            if "_raw_row" in all_transactions[idx] and document_original_mapping.get("date") is not None:
                                d_col = document_original_mapping["date"]
                                if d_col < len(all_transactions[idx]["_raw_row"]):
                                    all_transactions[idx]["_raw_row"][d_col] = corrected_str
        except Exception as date_err:
            logger.log(f"Date post-processing correction failed: {date_err}")

        # Retrieve expected transaction count early
        expected_count = ValidationService.extract_expected_count(first_page_text)
        if expected_count < 0 and page_count > 1:
            try:
                last_page_text = OCRParser.extract_raw_text(pdf_path, page_count - 1) if is_scanned else fitz.open(pdf_path)[page_count - 1].get_text()
                expected_count = ValidationService.extract_expected_count(last_page_text)
            except Exception:
                pass

        # 5. AI Discrepancy Auditing
        try:
            from services.gemini_service import GeminiService
            all_transactions = GeminiService.validate_extracted_transactions(first_page_text, all_transactions, meta.get("currency", "INR"))
        except Exception as e:
            logger.log(f"AI Discrepancy Auditing failed: {e}")

        # 6. Mathematical Running Balance Verification
        review_rows = []
        balance_mismatch_count = 0
        has_running_balance = False
        non_empty_balances = [str(tx.get("balance")).strip() for tx in all_transactions if tx.get("balance")]
        if len(set(non_empty_balances)) > 1:
            has_running_balance = True

        if has_running_balance and len(all_transactions) > 1:
            from parser.utils import ParserUtils
            from decimal import Decimal
            for i in range(1, len(all_transactions)):
                prev = all_transactions[i-1]
                curr = all_transactions[i]
                
                prev_bal_raw = ParserUtils.parse_numeric(prev.get("balance"))
                curr_bal_raw = ParserUtils.parse_numeric(curr.get("balance"))
                debit_raw = ParserUtils.parse_numeric(curr.get("debit"))
                credit_raw = ParserUtils.parse_numeric(curr.get("credit"))
                
                try:
                    prev_bal = Decimal(str(prev_bal_raw)) if prev_bal_raw is not None else None
                    curr_bal = Decimal(str(curr_bal_raw)) if curr_bal_raw is not None else None
                    debit = Decimal(str(debit_raw)) if debit_raw is not None else Decimal("0.00")
                    credit = Decimal(str(credit_raw)) if credit_raw is not None else Decimal("0.00")
                    
                    if prev_bal is not None and curr_bal is not None:
                        expected_bal = prev_bal - debit + credit
                        if abs(expected_bal - curr_bal) > Decimal("0.02"):
                            balance_mismatch_count += 1
                            curr["_balance_mismatch"] = True
                            curr["_review_required"] = True
                            review_rows.append({
                                "page": curr.get("_source_page", 1),
                                "row": curr.get("_source_row", i) + 1,
                                "original_value": f"Prev Bal: {prev.get('balance')}, Debit: {curr.get('debit')}, Credit: {curr.get('credit')}, Extracted Bal: {curr.get('balance')}",
                                "issue": "Balance Mismatch",
                                "confidence": 100,
                                "suggested_correction": f"Expected Balance: {expected_bal}",
                                "status": "Review Required"
                            })
                except Exception:
                    pass

        # Strict validation checks for every transaction
        for idx, tx in enumerate(all_transactions):
            has_date = bool(str(tx.get("date", "")).strip())
            has_narration = bool(str(tx.get("narration", "")).strip())
            has_balance = bool(str(tx.get("balance", "")).strip())
            
            debit_val = str(tx.get("debit", "")).strip()
            credit_val = str(tx.get("credit", "")).strip()
            has_debit = bool(debit_val)
            has_credit = bool(credit_val)
            
            issue = None
            if not has_date:
                issue = "Missing Date"
            elif not has_narration:
                issue = "Missing Narration"
            elif not has_balance:
                issue = "Missing Balance"
            elif has_debit and has_credit:
                issue = "Both Debit & Credit Present"
            elif not has_debit and not has_credit:
                issue = "Lacks both Debit & Credit"
                
            if issue:
                tx["_review_required"] = True
                review_rows.append({
                    "page": tx.get("_source_page", 1),
                    "row": tx.get("_source_row", idx) + 1,
                    "original_value": f"Date: {tx.get('date')}, Narr: {tx.get('narration')}, Dr: {tx.get('debit')}, Cr: {tx.get('credit')}, Bal: {tx.get('balance')}",
                    "issue": issue,
                    "confidence": 75,
                    "suggested_correction": "Review transaction values",
                    "status": "Review Required"
                })

        # Cross-check transaction count
        if expected_count > 0 and len(all_transactions) != expected_count:
            review_rows.append({
                "page": 0,
                "row": 0,
                "original_value": f"Source Expected: {expected_count}, Exported: {len(all_transactions)}",
                "issue": "Transaction Count Mismatch",
                "confidence": 100,
                "suggested_correction": f"Check PDF pages to locate missing rows.",
                "status": "Review Required"
            })

        # Append AI warnings to review rows
        for idx, tx in enumerate(all_transactions):
            if tx.get("_review_required") and tx.get("_ai_review"):
                ai_rev = tx["_ai_review"]
                review_rows.append({
                    "page": tx.get("_source_page", 1),
                    "row": tx.get("_source_row", idx) + 1,
                    "original_value": f"{ai_rev.get('field')}: {ai_rev.get('original_value')}",
                    "issue": ai_rev.get("issue"),
                    "confidence": ai_rev.get("confidence", 80),
                    "suggested_correction": ai_rev.get("suggested_correction"),
                    "status": "Review Required"
                })

        # Append failed pages to review rows
        for p in failed_pages:
            review_rows.append({
                "page": p,
                "row": 0,
                "original_value": "Page failed to load",
                "issue": "Page Extraction Failed",
                "confidence": 100,
                "suggested_correction": "Review source page and extract manually",
                "status": "Review Required"
            })

        # Re-build raw rows from deduplicated all_transactions
        raw_rows = [tx["_raw_row"] for tx in all_transactions if "_raw_row" in tx]

        # 7. Audit Metadata
        digital_pages_count = sum(1 for r in results if r and r["success"] and r["method"] == "digital")
        ocr_pages_count = sum(1 for r in results if r and r["success"] and r["method"] == "ocr")
        ai_fallback_count = sum(1 for r in results if r and r["success"] and "AI" in r["method"])
        failed_pages_count = len(failed_pages)
        
        review_count = len(review_rows)
        total_tx_count = len(all_transactions)
        if total_tx_count > 0:
            integrity_score = round(100.0 * (1.0 - review_count / total_tx_count), 2)
            integrity_score = max(0.0, min(100.0, integrity_score))
        else:
            integrity_score = 100.0 if failed_pages_count == 0 else 0.0

        extraction_audit = {
            "source_pdf": os.path.basename(pdf_path),
            "detected_bank": meta["bank_name"],
            "account_holder": meta["account_holder"],
            "statement_period": meta["period"],
            "total_pages": page_count,
            "pages_processed": page_count - failed_pages_count,
            "digital_pages": digital_pages_count,
            "ocr_pages": ocr_pages_count,
            "ai_fallback_pages": ai_fallback_count,
            "failed_pages_count": failed_pages_count,
            "raw_rows_detected": len(raw_rows),
            "transactions_exported": len(all_transactions),
            "low_confidence_rows": sum(1 for tx in all_transactions if tx.get("_confidence", 1.0) < 0.95),
            "balance_mismatches": balance_mismatch_count,
            "data_integrity": integrity_score,
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "page_details": []
        }
        
        for idx in range(page_count):
            res = results[idx]
            if res and res["success"]:
                status_str = "Review" if any(tx.get("_review_required") for tx in res["transactions"]) else "Verified"
                extraction_audit["page_details"].append({
                    "page": idx + 1,
                    "method": res["method"],
                    "rows": len(res["transactions"]),
                    "confidence": f"{int(res['confidence']*100)}%",
                    "status": status_str
                })
            else:
                extraction_audit["page_details"].append({
                    "page": idx + 1,
                    "method": "N/A",
                    "rows": 0,
                    "confidence": "0%",
                    "status": "Failed"
                })

        validation_res = ValidationService.validate_transactions(all_transactions, expected_count)
        logger.log_summary(page_count, len(failed_pages), initial_count, len(all_transactions))
        processing_time = time.time() - start_time
        
        payload = {
            "file_path": pdf_path,
            "file_name": os.path.basename(pdf_path),
            "is_scanned": is_scanned,
            "ocr_simulated": False,
            "page_count": page_count,
            "bank_name": meta["bank_name"],
            "account_holder": meta["account_holder"],
            "account_number": meta["account_number"],
            "period": meta["period"],
            "currency": meta["currency"],
            "transactions": all_transactions,
            "original_headers": document_original_headers,
            "raw_rows": raw_rows,
            "review_rows": review_rows,
            "failed_pages": failed_pages,
            "extraction_audit": extraction_audit,
            "processing_time": processing_time,
            "parse_method": "Modular Parsing Engine",
            "balance_verified": validation_res["success"],
            "validation_msg": validation_res["mismatch_warning"],
            "logs": logger.get_logs()
        }

        return payload

# Refactored / updated upload_statement module and service integration
