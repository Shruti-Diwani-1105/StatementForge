import os
import time
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from services.pdf_reader import PDFReader
from services.ocr_service import OCRService
from services.gemini_service import GeminiService
from services.transaction_formatter import TransactionFormatter
from services.bank_detector import BankDetector
from services.excel_generator import ExcelGenerator
from services.history_service import HistoryService

class ParseWorker(QObject):
    """Worker object that runs the statement parsing steps 1-4 in a background QThread."""
    started = pyqtSignal()
    step_started = pyqtSignal(int)      # Emits step index (1-4)
    step_completed = pyqtSignal(int, str) # Emits step index (1-4), status ("success", "skipped")
    progress = pyqtSignal(int, int, int) # Emits (current_page, total_pages, tx_count)
    finished = pyqtSignal(dict)         # Emits final parsed metadata and transactions payload
    error = pyqtSignal(str)             # Emits error message

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.started.emit()
            start_time = time.time()

            # --- STEP 1: Uploading PDF ---
            self.step_started.emit(1)
            time.sleep(0.5) # Quick simulated upload pause to show step-by-step progress
            self.step_completed.emit(1, "success")

            # --- STEP 2: Reading PDF ---
            self.step_started.emit(2)
            
            # File check
            if not os.path.exists(self.file_path):
                raise FileNotFoundError("The selected file does not exist.")
                
            page_count = PDFReader.get_page_count(self.file_path)
            if page_count == 0:
                raise ValueError("The selected PDF file is empty or corrupted.")
                
            if PDFReader.is_password_protected(self.file_path):
                raise ValueError("The selected PDF statement is password-protected.\nPlease remove the password before uploading.")

            is_digital = PDFReader.is_digital_pdf(self.file_path)
            self.step_completed.emit(2, "success")

            # --- STEP 3: OCR (if required) ---
            self.step_started.emit(3)
            if is_digital:
                self.step_completed.emit(3, "skipped")
            else:
                self.step_completed.emit(3, "success")

            # --- STEP 4: Hybrid Auto Detection & Parsing ---
            self.step_started.emit(4)
            
            from parser.parser import PDFStatementParser
            
            def prog_cb(cur, tot, tx_count):
                self.progress.emit(cur, tot, tx_count)

            # Run page-by-page streaming extraction fallback pipeline
            payload = PDFStatementParser.parse(self.file_path, progress_callback=prog_cb)
            payload["processing_time"] = time.time() - start_time
            
            self.step_completed.emit(4, "success")
            self.finished.emit(payload)

        except Exception as e:
            self.error.emit(str(e))





class ValidateWorker(QObject):
    """Worker object that performs quick PDF validation and bank detection in a background QThread."""
    started = pyqtSignal()
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.started.emit()
            if not os.path.exists(self.file_path):
                raise FileNotFoundError("The selected file does not exist.")
            
            from services.pdf_reader import PDFReader
            if PDFReader.is_password_protected(self.file_path):
                raise ValueError("The selected PDF statement is password-protected.\nPlease remove the password before uploading.")

            page_count = PDFReader.get_page_count(self.file_path)
            if page_count == 0:
                raise ValueError("The selected PDF file is empty or corrupted.")

            from parser.parser import PDFStatementParser
            
            bank_name = PDFStatementParser.detect_bank_from_pdf(self.file_path)


            self.finished.emit({
                "file_path": self.file_path,
                "file_name": os.path.basename(self.file_path),
                "page_count": page_count,
                "bank_name": bank_name
            })
        except Exception as e:
            self.error.emit(str(e))


class ExcelWorker(QObject):
    """Worker object that runs Excel generation and DB logging (steps 5-6) in a background QThread."""
    started = pyqtSignal()
    step_started = pyqtSignal(int)        # Emits step index (5-6)
    step_completed = pyqtSignal(int, str)  # Emits step index (5-6), status ("success")
    finished = pyqtSignal(str)            # Emits output Excel file path
    error = pyqtSignal(str)               # Emits error message

    def __init__(self, user_id, payload, history_record_id=None):
        super().__init__()
        self.user_id = user_id
        self.payload = payload
        self.history_record_id = history_record_id

    def run(self):
        try:
            self.started.emit()

            # --- STEP 5: Generating Excel ---
            self.step_started.emit(5)
            
            excel_path = ExcelGenerator.generate_excel(
                pdf_path=self.payload["file_path"],
                bank_name=self.payload["bank_name"],
                account_holder=self.payload["account_holder"],
                period=self.payload["period"],
                transactions=self.payload["transactions"]
            )
            time.sleep(0.3) # Slower UI animation update feel
            self.step_completed.emit(5, "success")

            # --- STEP 6: Saving File & DB logging ---
            self.step_started.emit(6)
            
            if self.history_record_id:
                HistoryService.update_record_completed(
                    record_id=self.history_record_id,
                    excel_path=excel_path,
                    period=self.payload["period"],
                    processing_time=self.payload["processing_time"],
                    total_transactions=len(self.payload["transactions"])
                )
            else:
                # Save parsing log into MongoDB history collection or fallback
                HistoryService.save_record(
                    user_id=self.user_id,
                    pdf_path=self.payload["file_path"],
                    excel_path=excel_path,
                    bank_name=self.payload["bank_name"],
                    statement_period=self.payload["period"],
                    processing_time=self.payload["processing_time"],
                    total_transactions=len(self.payload["transactions"])
                )
            time.sleep(0.3)
            self.step_completed.emit(6, "success")

            self.finished.emit(excel_path)

        except Exception as e:
            self.error.emit(str(e))


class StatementService:
    """Service to spawn thread workers for statement processing."""
    
    @classmethod
    def start_validate(cls, file_path, on_started, on_finished, on_error):
        """Spawns a ValidateWorker in a background thread."""
        thread = QThread()
        worker = ValidateWorker(file_path)
        worker.moveToThread(thread)

        thread.worker = worker

        thread.started.connect(worker.run)
        worker.started.connect(on_started)
        
        def cleanup():
            thread.quit()
            thread.wait()

        def handle_finished(meta):
            on_finished(meta)
            cleanup()

        def handle_error(err_msg):
            on_error(err_msg)
            cleanup()

        worker.finished.connect(handle_finished)
        worker.error.connect(handle_error)

        thread.start()
        return thread

    @classmethod
    def start_parse(cls, file_path, on_started, on_step_started, on_step_completed, on_progress, on_finished, on_error):
        """Spawns a ParseWorker in a background thread."""
        thread = QThread()
        worker = ParseWorker(file_path)
        worker.moveToThread(thread)

        thread.worker = worker # Keep references to prevent GC

        # Wire signals
        thread.started.connect(worker.run)
        worker.started.connect(on_started)
        worker.step_started.connect(on_step_started)
        worker.step_completed.connect(on_step_completed)
        if on_progress:
            worker.progress.connect(on_progress)
        
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


    @classmethod
    def start_generate_excel(cls, user_id, payload, history_record_id, on_started, on_step_started, on_step_completed, on_finished, on_error):
        """Spawns an ExcelWorker in a background thread."""
        thread = QThread()
        worker = ExcelWorker(user_id, payload, history_record_id)
        worker.moveToThread(thread)

        thread.worker = worker # Keep references to prevent GC

        thread.started.connect(worker.run)
        worker.started.connect(on_started)
        worker.step_started.connect(on_step_started)
        worker.step_completed.connect(on_step_completed)

        def cleanup():
            thread.quit()
            thread.wait()

        def handle_finished(excel_path):
            on_finished(excel_path)
            cleanup()

        def handle_error(err_msg):
            on_error(err_msg)
            cleanup()

        worker.finished.connect(handle_finished)
        worker.error.connect(handle_error)

        thread.start()
        return thread

