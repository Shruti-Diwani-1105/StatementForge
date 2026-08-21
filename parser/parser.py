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

        transactions = []
        column_mapping = None
        failed_pages = []

        is_scanned = True
        if first_page_text and len(first_page_text.strip()) > 100:
            is_scanned = False

        # Define thread-safe page processing target for parallel phase
        def process_single_page(idx, shared_mapping):
            try:
                page_txs, page_mapping, method_used = PageProcessor.process_page(pdf_path, idx, shared_mapping, None)
                return idx, True, page_txs, page_mapping, method_used, None
            except Exception as e:
                # Retry strategy
                try:
                    from parser.ocr_parser import OCRParser
                    from services.gemini_service import GeminiService
                    from parser.utils import ParserUtils
                    pil_image = OCRParser.render_pdf_page_to_pil(pdf_path, idx)
                    ai_data = GeminiService.parse_page_image(pil_image)
                    if ai_data and "transactions" in ai_data:
                        raw_txs = ai_data["transactions"]
                        page_txs = []
                        for tx in raw_txs:
                            date_val = tx.get("Date") or tx.get("date") or ""
                            narr_val = tx.get("Narration") or tx.get("narration") or tx.get("Description") or tx.get("description") or ""
                            debit_val = tx.get("Debit") or tx.get("debit") or ""
                            credit_val = tx.get("Credit") or tx.get("credit") or ""
                            bal_val = tx.get("Balance") or tx.get("balance") or ""
                            page_txs.append({
                                "date": str(date_val),
                                "narration": str(narr_val),
                                "debit": ParserUtils.clean_amount(debit_val),
                                "credit": ParserUtils.clean_amount(credit_val),
                                "balance": ParserUtils.clean_balance(bal_val)
                            })
                        return idx, True, page_txs, None, "AI Vision Fallback", None
                except Exception as retry_err:
                    return idx, False, [], None, None, f"{e} (AI Vision retry failed: {retry_err})"
                return idx, False, [], None, None, str(e)

        results = [None] * page_count
        first_tx_page_idx = -1

        # Sequential Phase: Process pages sequentially until we get a column mapping
        for idx in range(page_count):
            if progress_callback:
                try:
                    import inspect
                    sig = inspect.signature(progress_callback)
                    if len(sig.parameters) >= 3:
                        progress_callback(idx + 1, page_count, len(transactions))
                    else:
                        progress_callback(idx + 1, page_count)
                except Exception:
                    progress_callback(idx + 1, page_count)

            is_page_digital = TableExtractor.has_selectable_text(pdf_path, idx)
            try:
                page_txs, page_mapping, method_used = PageProcessor.process_page(pdf_path, idx, None, logger)
                results[idx] = (True, page_txs, page_mapping, method_used, None)
                logger.log_page_success(idx + 1, is_page_digital, len(page_txs), method_used)
                
                if page_txs:
                    transactions.extend(page_txs)
                    column_mapping = page_mapping
                    first_tx_page_idx = idx
                    break
            except Exception as e:
                # Retry strategy for sequential phase if it fails
                try:
                    from parser.ocr_parser import OCRParser
                    from services.gemini_service import GeminiService
                    from parser.utils import ParserUtils
                    pil_image = OCRParser.render_pdf_page_to_pil(pdf_path, idx)
                    ai_data = GeminiService.parse_page_image(pil_image)
                    if ai_data and "transactions" in ai_data:
                        raw_txs = ai_data["transactions"]
                        page_txs = []
                        for tx in raw_txs:
                            date_val = tx.get("Date") or tx.get("date") or ""
                            narr_val = tx.get("Narration") or tx.get("narration") or tx.get("Description") or tx.get("description") or ""
                            debit_val = tx.get("Debit") or tx.get("debit") or ""
                            credit_val = tx.get("Credit") or tx.get("credit") or ""
                            bal_val = tx.get("Balance") or tx.get("balance") or ""
                            page_txs.append({
                                "date": str(date_val),
                                "narration": str(narr_val),
                                "debit": ParserUtils.clean_amount(debit_val),
                                "credit": ParserUtils.clean_amount(credit_val),
                                "balance": ParserUtils.clean_balance(bal_val)
                            })
                        results[idx] = (True, page_txs, None, "AI Vision Fallback", None)
                        logger.log_page_success(idx + 1, is_page_digital, len(page_txs), "AI Vision Fallback")
                        if page_txs:
                            transactions.extend(page_txs)
                            first_tx_page_idx = idx
                            break
                except Exception as retry_err:
                    results[idx] = (False, [], None, None, f"{e} (AI Vision retry failed: {retry_err})")
                    failed_pages.append(idx + 1)
                    logger.log_page_failure(idx + 1, f"{e} (AI Vision retry failed: {retry_err})")

        # Parallel Phase: Process remaining pages concurrently using the detected column mapping
        remaining_pages = range(first_tx_page_idx + 1, page_count)
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
                    idx, success, page_txs, page_mapping, method_used, error_msg = future.result()
                    results[idx] = (success, page_txs, page_mapping, method_used, error_msg)
                    completed_count += 1
                    
                    if progress_callback:
                        try:
                            curr_tx_count = len(transactions) + sum(len(results[r][1]) for r in remaining_pages if results[r] is not None)
                            import inspect
                            sig = inspect.signature(progress_callback)
                            if len(sig.parameters) >= 3:
                                progress_callback(completed_count, page_count, curr_tx_count)
                            else:
                                progress_callback(completed_count, page_count)
                        except Exception:
                            progress_callback(completed_count, page_count)

            # Assemble and log in sequential order
            for idx in remaining_pages:
                success, page_txs, page_mapping, method_used, error_msg = results[idx]
                is_page_digital = TableExtractor.has_selectable_text(pdf_path, idx)
                
                if success:
                    logger.log_page_success(idx + 1, is_page_digital, len(page_txs), method_used)
                    if page_txs:
                        transactions.extend(page_txs)
                else:
                    failed_pages.append(idx + 1)
                    logger.log_page_failure(idx + 1, error_msg)


        # Post-processing deduplication
        initial_count = len(transactions)
        transactions = DuplicateChecker.remove_duplicates(transactions)
        
        # Run Gemini AI validation on extracted transactions to correct typos and align columns
        try:
            from services.gemini_service import GeminiService
            transactions = GeminiService.validate_extracted_transactions(first_page_text, transactions, meta.get("currency", "INR"))
        except Exception as e:
            logger.log(f"AI Enhancement failed or skipped: {e}")
            
        # Chronological year correction post-processing
        try:
            import datetime
            from parser.utils import ParserUtils
            valid_dates = []
            for tx in transactions:
                parsed = ParserUtils.parse_date(tx.get("date"))
                if isinstance(parsed, datetime.date):
                    valid_dates.append(parsed)
                else:
                    valid_dates.append(None)
                    
            period_years = [int(y) for y in re.findall(r"\b(20\d{2})\b", meta.get("period", ""))]
            if period_years:
                min_year = min(period_years)
                max_year = max(period_years)
                
                for idx in range(len(transactions)):
                    d = valid_dates[idx]
                    if d and isinstance(d, datetime.date):
                        if d.year < min_year or d.year > max_year:
                            prev_year = None
                            for j in range(idx - 1, -1, -1):
                                if valid_dates[j] and isinstance(valid_dates[j], datetime.date) and min_year <= valid_dates[j].year <= max_year:
                                    prev_year = valid_dates[j].year
                                    break
                            next_year = None
                            for j in range(idx + 1, len(transactions)):
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
                                            
                            orig_str = transactions[idx]["date"]
                            corrected_str = orig_str.replace(str(d.year), str(inferred_year))
                            transactions[idx]["date"] = corrected_str
                            valid_dates[idx] = d.replace(year=inferred_year)
        except Exception as date_err:
            logger.log(f"Date post-processing correction failed: {date_err}")

        dedup_count = len(transactions)

        # Expected transactions check
        expected_count = ValidationService.extract_expected_count(first_page_text)
        if expected_count < 0 and page_count > 1:
            try:
                last_page_text = OCRParser.extract_raw_text(pdf_path, page_count - 1) if is_scanned else fitz.open(pdf_path)[page_count - 1].get_text()
                expected_count = ValidationService.extract_expected_count(last_page_text)
            except Exception:
                pass

        validation_res = ValidationService.validate_transactions(transactions, expected_count)
        
        logger.log_summary(page_count, len(failed_pages), initial_count, dedup_count)

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
            "transactions": transactions,
            "processing_time": processing_time,
            "parse_method": "Modular Parsing Engine",
            "balance_verified": validation_res["success"],
            "validation_msg": validation_res["mismatch_warning"],
            "failed_pages": failed_pages,
            "logs": logger.get_logs()
        }

        return payload

# Refactored / updated upload_statement module and service integration
