import os
import time
import pdfplumber
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from utils.pdf_parser import PDFParser
from utils.ocr_parser import OCRParser
from utils.bank_detector import BankDetector

class ParseWorker(QObject):
    """Worker object that executes parsing logic in a background QThread."""
    started = pyqtSignal()
    progress = pyqtSignal(int, int)  # current page, total pages
    finished = pyqtSignal(dict)      # result payload dict
    error = pyqtSignal(str)          # error message string

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.started.emit()
            start_time = time.time()

            # 1. Page count and initial validation
            page_count = PDFParser.get_page_count(self.file_path)
            if page_count == 0:
                self.error.emit("The PDF file appears to be empty or corrupted.")
                return

            # 2. Check for password encryption
            try:
                with pdfplumber.open(self.file_path) as pdf:
                    if pdf.metadata and pdf.metadata.get("Encrypted") == True:
                        self.error.emit("The selected PDF statement is password-protected.\nPlease remove the password before uploading.")
                        return
                    first_page_text = pdf.pages[0].extract_text()
            except Exception as e:
                # Catch standard encryption errors from pdfplumber
                err_str = str(e).lower()
                if "password" in err_str or "encrypted" in err_str:
                    self.error.emit("The selected PDF statement is password-protected.\nPlease remove the password before uploading.")
                else:
                    self.error.emit(f"Failed to open PDF file: {e}")
                return

            # 3. Heuristic check: Digital vs Scanned PDF
            # If first page has almost zero text content, it's likely scanned
            is_scanned = False
            if not first_page_text or len(first_page_text.strip()) < 50:
                is_scanned = True

            transactions = []
            ocr_used = False
            ocr_simulated = False
            raw_text = ""

            if is_scanned:
                # Run OCR Parser
                ocr_used = True
                def ocr_prog(page_num, total):
                    self.progress.emit(page_num, total)
                
                # Check Tesseract installation
                if not OCRParser.is_tesseract_installed():
                    ocr_simulated = True

                transactions = OCRParser.parse_scanned_transactions(self.file_path, ocr_prog)
                # Compile transactions text as fallback text for bank detection
                raw_text = " ".join([t["narration"] for t in transactions])
            else:
                # Run Digital Parser
                self.progress.emit(1, page_count)
                transactions = PDFParser.parse_transactions(self.file_path)
                raw_text = PDFParser.extract_raw_text(self.file_path)
                self.progress.emit(page_count, page_count)

            if len(transactions) == 0:
                self.error.emit("The PDF statement was parsed successfully, but no transaction records were found.")
                return

            # 4. Bank & Account Holder Detection
            bank_name = BankDetector.detect_bank(raw_text)
            period = BankDetector.detect_period(raw_text)
            account_holder = BankDetector.detect_account_holder(raw_text)

            end_time = time.time()
            processing_time = end_time - start_time

            # Build result payload
            payload = {
                "file_path": self.file_path,
                "file_name": os.path.basename(self.file_path),
                "is_scanned": is_scanned,
                "ocr_used": ocr_used,
                "ocr_simulated": ocr_simulated,
                "page_count": page_count,
                "bank_name": bank_name,
                "period": period,
                "account_holder": account_holder,
                "transactions": transactions,
                "processing_time": processing_time
            }

            self.finished.emit(payload)

        except RuntimeError as re:
            self.error.emit(str(re))
        except Exception as e:
            self.error.emit(f"An unexpected parsing error occurred: {e}")


class StatementService:
    """Service class that triggers ParseWorker threads."""
    @classmethod
    def start_parse(cls, file_path, on_started, on_progress, on_finished, on_error):
        """Creates a worker thread and connects callbacks to parse a statement."""
        thread = QThread()
        worker = ParseWorker(file_path)
        worker.moveToThread(thread)

        # Keep references to prevent garbage collection
        thread.worker = worker

        # Connect signals
        thread.started.connect(worker.run)
        worker.started.connect(on_started)
        worker.progress.connect(on_progress)
        
        # Clean up thread on completion
        def cleanup():
            thread.quit()
            thread.wait()

        def handle_finished(payload):
            on_finished(payload)
            cleanup()

        def handle_error(err_msg):
            on_error(err_msg)
            cleanup()

        worker.finished.connect(handle_finished)
        worker.error.connect(handle_error)

        thread.start()
        return thread
