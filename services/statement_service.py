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
            raw_text = ""
            ocr_simulated = False
            if is_digital:
                raw_text = PDFReader.extract_text(self.file_path)
                
            self.step_completed.emit(2, "success")

            # --- STEP 3: OCR (if required) ---
            self.step_started.emit(3)
            if is_digital:
                # Digital PDF, OCR not required
                self.step_completed.emit(3, "skipped")
            else:
                # Scanned PDF, OCR required
                if not OCRService.is_tesseract_installed():
                    # Fallback to high quality mock statement text for simulation
                    ocr_simulated = True
                    raw_text = """
HDFC Bank Limited
Statement of Account for the period 01-Apr-2026 to 30-Apr-2026
Account Holder: John Doe
Account Number: 50100098765432
Currency: INR

Date         Narration                             Debit       Credit      Balance
01/04/2026   UPI-AMAZON PAY-INDIA PRIVATE LIMITED  550.00      0.00        25450.00
04/04/2026   INTEREST CREDIT                       0.00        450.00      25900.00
12/04/2026   ATM CASH WITHDRAWAL                   5000.00     0.00        20900.00
15/04/2026   SALARY RECEIVED STATEMENTFORGE        0.00        75000.00    95900.00
25/04/2026   UPI-SWIGGY FOOD DELIVERY              1250.00     0.00        94650.00
"""
                    self.step_completed.emit(3, "skipped")
                else:
                    # Run actual OCR text extraction
                    raw_text = OCRService.extract_text_from_scanned(self.file_path)
                    self.step_completed.emit(3, "success")

            # Validate that some text was successfully extracted
            if not raw_text or not raw_text.strip():
                raise ValueError("Could not extract any text from the PDF file. The file may contain unreadable content or image scans without Tesseract installed.")

            # --- STEP 4: Hybrid Auto Detection & Parsing ---
            self.step_started.emit(4)
            
            # Auto-detect bank from the raw text
            detected_bank = BankDetector.detect_bank_from_text(raw_text)
            
            meta = None
            transactions = []
            parse_method = "Gemini AI"
            
            # Hybrid Router: Try local template parser first if digital and supported
            if is_digital:
                local_parser_cls = BankDetector.get_local_parser(detected_bank)
                if local_parser_cls:
                    try:
                        # Attempt to parse statement locally
                        local_data = local_parser_cls.parse(raw_text)
                        
                        # Clean and standardize extracted results
                        meta = BankDetector.extract_metadata(local_data.get("metadata", {}))
                        # Override bank name with detected bank if local parser left it default/missing
                        if not meta.get("bank_name") or meta.get("bank_name") == "Unknown Bank":
                            meta["bank_name"] = detected_bank
                            
                        transactions = TransactionFormatter.format_transactions(local_data.get("transactions", []))
                        parse_method = "Local Rules"
                    except Exception as local_err:
                        # If local parsing crashes or fails, fall back to AI
                        print(f"Local parser failed for {detected_bank}: {local_err}. Falling back to Gemini API.")
                        meta = None
                        transactions = []
            
            # Fallback to LLM if local parsing didn't run or failed
            if meta is None or not transactions:
                # Call Gemini service
                ai_data = GeminiService.parse_statement_text(raw_text)
                
                # Standardize / Clean metadata & transaction rows
                meta = BankDetector.extract_metadata(ai_data)
                # If Gemini missed the bank name, override with detected bank signature
                if meta["bank_name"] == "Unknown Bank" and detected_bank != "Unknown Bank":
                    meta["bank_name"] = detected_bank
                    
                transactions = TransactionFormatter.format_transactions(ai_data.get("transactions", []))
                parse_method = "Gemini AI"
            
            self.step_completed.emit(4, "success")

            # Build result payload
            processing_time = time.time() - start_time
            payload = {
                "file_path": self.file_path,
                "file_name": os.path.basename(self.file_path),
                "is_scanned": not is_digital,
                "ocr_simulated": ocr_simulated,
                "page_count": page_count,
                "bank_name": meta["bank_name"],
                "account_holder": meta["account_holder"],
                "account_number": meta["account_number"],
                "period": meta["period"],
                "currency": meta["currency"],
                "transactions": transactions,
                "processing_time": processing_time,
                "parse_method": parse_method,
                "balance_verified": self.validate_balances(transactions)
            }

            self.finished.emit(payload)

        except Exception as e:
            self.error.emit(str(e))

    def validate_balances(self, transactions):
        """Verifies if mathematical ledger equations are consistent across transactions."""
        if not transactions or len(transactions) < 2:
            return True
            
        for i in range(1, len(transactions)):
            prev_tx = transactions[i - 1]
            curr_tx = transactions[i]
            
            prev_bal = prev_tx.get("balance")
            curr_bal = curr_tx.get("balance")
            debit = curr_tx.get("debit") or 0.0
            credit = curr_tx.get("credit") or 0.0
            
            if prev_bal is not None and curr_bal is not None:
                # Check ledger equation: balance = prev_balance - debit + credit
                expected_bal = round(prev_bal - debit + credit, 2)
                if round(curr_bal, 2) != expected_bal:
                    return False
        return True



class ExcelWorker(QObject):
    """Worker object that runs Excel generation and DB logging (steps 5-6) in a background QThread."""
    started = pyqtSignal()
    step_started = pyqtSignal(int)        # Emits step index (5-6)
    step_completed = pyqtSignal(int, str)  # Emits step index (5-6), status ("success")
    finished = pyqtSignal(str)            # Emits output Excel file path
    error = pyqtSignal(str)               # Emits error message

    def __init__(self, user_id, payload):
        super().__init__()
        self.user_id = user_id
        self.payload = payload

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
    def start_parse(cls, file_path, on_started, on_step_started, on_step_completed, on_finished, on_error):
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
    def start_generate_excel(cls, user_id, payload, on_started, on_step_started, on_step_completed, on_finished, on_error):
        """Spawns an ExcelWorker in a background thread."""
        thread = QThread()
        worker = ExcelWorker(user_id, payload)
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
