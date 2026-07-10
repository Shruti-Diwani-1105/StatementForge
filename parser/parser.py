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
            "SIBL": "South Indian Bank"
        }

        pages_text = []

        # 1. Extract digital text from all pages and match signatures
        if HAS_FITZ:
            try:
                doc = fitz.open(pdf_path)
                for idx in range(len(doc)):
                    text = doc[idx].get_text()
                    if text:
                        text_upper = text.upper()
                        # Check IFSC first
                        match = re.search(r"\b([A-Z]{4})0\d{6}\b", text_upper)
                        if match:
                            prefix = match.group(1)
                            if prefix in ifsc_prefixes:
                                return ifsc_prefixes[prefix]
                        
                        # Match signatures
                        bank = BankDetector.detect_bank(text)
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
                            text_upper = text.upper()
                            # Check IFSC
                            match = re.search(r"\b([A-Z]{4})0\d{6}\b", text_upper)
                            if match:
                                prefix = match.group(1)
                                if prefix in ifsc_prefixes:
                                    return ifsc_prefixes[prefix]
                            
                            bank = BankDetector.detect_bank(text)
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
                        
                        bank = BankDetector.detect_bank(text)
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

        # 4. Relaxed keyword checks on combined pages text
        combined = "\n".join(pages_text).lower()
        if "hdfc" in combined:
            return "HDFC Bank"
        if "sbi" in combined or "state bank" in combined:
            return "State Bank of India"
        if "icici" in combined:
            return "ICICI Bank"
        if "axis" in combined:
            return "Axis Bank"
        if "kotak" in combined:
            return "Kotak Mahindra Bank"
        if "bob" in combined or "baroda" in combined:
            return "Bank of Baroda"
        if "canara" in combined:
            return "Canara Bank"
        if "union" in combined:
            return "Union Bank of India"
        if "pnb" in combined or "punjab" in combined:
            return "Punjab National Bank"
        if "idfc" in combined:
            return "IDFC First Bank"
        if "indusind" in combined:
            return "IndusInd Bank"
        if "yes bank" in combined or "yesbank" in combined:
            return "Yes Bank"

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
            metadata["bank_name"] = BankDetector.detect_bank(text)

        holder_patterns = [
            r"(?:Account Holder|Customer Name|Name|Primary Holder)\s*:\s*([A-Za-z \t\.]+)",
            r"Holder\s*:\s*([A-Za-z \t\.]+)"
        ]
        for pattern in holder_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["account_holder"] = match.group(1).strip()
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
            r"statement of account for\s*(.*?)(?:\n|$)"
        ]
        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["period"] = match.group(1).strip()
                break

        if "USD" in text or "$" in text:
            metadata["currency"] = "USD"
        elif "EUR" in text or "€" in text:
            metadata["currency"] = "EUR"

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
                page_txs, page_mapping, method_used = PageProcessor.process_page(pdf_path, idx, column_mapping, logger)
                
                # Log success using requested layout format
                logger.log_page_success(idx + 1, is_page_digital, len(page_txs), method_used)
                
                if page_txs:
                    transactions.extend(page_txs)
                    if not column_mapping:
                        column_mapping = page_mapping

                # Pacing delay to avoid exceeding standard 15 RPM free tier limits on vision calls
                if method_used == "AI Vision Fallback" and idx < page_count - 1:
                    time.sleep(3.5)
            except Exception as e:
                failed_pages.append(idx + 1)
                logger.log_page_failure(idx + 1, str(e))


        # Post-processing deduplication
        initial_count = len(transactions)
        transactions = DuplicateChecker.remove_duplicates(transactions)
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
