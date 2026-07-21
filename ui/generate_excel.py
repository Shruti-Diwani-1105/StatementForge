import os
import sys
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QSpacerItem, QSizePolicy, QProgressBar, QMessageBox, QGridLayout,
    QGraphicsDropShadowEffect, QListWidget, QListWidgetItem, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths
from PyQt6.QtGui import QPixmap, QCursor, QColor

from services.statement_service import StatementService
from services.history_service import HistoryService
from utils.user_session import UserSession
from settings.toast import Toast


class GenerateExcelWidget(QWidget):
    """
    Dedicated premium desktop page for direct PDF to Excel conversion.
    Left Panel: Drag-and-drop PDF upload zone, file details, page count, and bank name.
    Right Panel: Timeline progress, transaction preview grid, Generate & Download buttons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.page_count = 0
        self.detected_bank = "Unknown Bank"
        self.doc_type_desc = "Digital PDF"
        self.parsed_payload = None
        self.excel_output_path = None
        self.current_theme = "light"
        self.active_thread = None

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # ==========================================
        # LEFT PANEL: UPLOAD & PDF METADATA
        # ==========================================
        left_panel = QFrame()
        left_panel.setFixedWidth(360)
        left_panel.setObjectName("LeftPanel")
        left_panel.setStyleSheet("""
            QFrame#LeftPanel {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)
        
        # Soft shadow for left panel
        shadow_l = QGraphicsDropShadowEffect()
        shadow_l.setBlurRadius(16)
        shadow_l.setColor(QColor(0, 0, 0, 15))
        shadow_l.setOffset(0, 4)
        left_panel.setGraphicsEffect(shadow_l)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(16)

        left_title = QLabel("Convert PDF Statement")
        left_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A; font-family: 'Times New Roman';")
        left_layout.addWidget(left_title)

        # Drag & Drop Box inside Left Panel
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("DropZone")
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.setMinimumHeight(180)
        self.drop_zone.setStyleSheet("""
            QFrame#DropZone {
                background-color: #F8FAFC;
                border: 2px dashed #CBD5E1;
                border-radius: 12px;
            }
            QFrame#DropZone:hover {
                border-color: #0037b0;
                background-color: #EFF6FF;
            }
        """)
        self.drop_zone.dragEnterEvent = self.zone_drag_enter
        self.drop_zone.dragLeaveEvent = self.zone_drag_leave
        self.drop_zone.dropEvent = self.zone_drop

        drop_lay = QVBoxLayout(self.drop_zone)
        drop_lay.setContentsMargins(16, 20, 16, 20)
        drop_lay.setSpacing(8)
        drop_lay.addStretch()

        up_icon = QLabel()
        up_icon.setFixedSize(36, 36)
        pix = QPixmap("assets/icons/upload.png")
        if not pix.isNull():
            up_icon.setPixmap(pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        drop_lay.addWidget(up_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        self.prompt_lbl = QLabel("Drag & Drop PDF Statement")
        self.prompt_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B; font-family: 'Times New Roman';")
        drop_lay.addWidget(self.prompt_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self.browse_btn = QPushButton("Select File")
        self.browse_btn.setFixedSize(110, 30)
        self.browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.browse_btn.clicked.connect(self.browse_pdf_file)
        drop_lay.addWidget(self.browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        drop_lay.addStretch()
        left_layout.addWidget(self.drop_zone)

        # PDF Details Card
        self.details_card = QFrame()
        self.details_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #EFF6FF; border-radius: 12px;")
        grid = QGridLayout(self.details_card)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(12)

        def make_row(grid_w, r_idx, label, attr):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B; text-transform: uppercase; font-family: 'Times New Roman';")
            val = QLabel("-")
            val.setStyleSheet("font-size: 12px; font-weight: bold; color: #0F172A; font-family: 'Times New Roman';")
            setattr(self, attr, val)
            grid_w.addWidget(lbl, r_idx, 0)
            grid_w.addWidget(val, r_idx, 1)

        make_row(grid, 0, "File Name:", "lbl_filename")
        make_row(grid, 1, "Detected Bank:", "lbl_bank")
        make_row(grid, 2, "Page Count:", "lbl_pages")
        make_row(grid, 3, "Doc Type:", "lbl_doctype")

        left_layout.addWidget(self.details_card)
        left_layout.addStretch()

        main_layout.addWidget(left_panel)

        # ==========================================
        # RIGHT PANEL: CONVERSION, PROGRESS, & PREVIEW
        # ==========================================
        right_panel = QFrame()
        right_panel.setObjectName("RightPanel")
        right_panel.setStyleSheet("""
            QFrame#RightPanel {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)
        
        # Soft shadow for right panel
        shadow_r = QGraphicsDropShadowEffect()
        shadow_r.setBlurRadius(16)
        shadow_r.setColor(QColor(0, 0, 0, 15))
        shadow_r.setOffset(0, 4)
        right_panel.setGraphicsEffect(shadow_r)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(16)

        # Right Header & Actions
        top_bar = QHBoxLayout()
        right_title = QLabel("Conversion Monitor & Excel Preview")
        right_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A; font-family: 'Times New Roman';")
        top_bar.addWidget(right_title)
        top_bar.addStretch()

        self.generate_btn = QPushButton("Generate Excel")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover { background-color: #15803d; }
            QPushButton:disabled { background-color: #E2E8F0; color: #94A3B8; }
        """)
        self.generate_btn.clicked.connect(self.start_parsing_process)
        top_bar.addWidget(self.generate_btn)

        self.download_btn = QPushButton("Open Excel")
        self.download_btn.setEnabled(False)
        self.download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #E2E8F0; color: #94A3B8; }
        """)
        self.download_btn.clicked.connect(self.open_generated_excel)
        top_bar.addWidget(self.download_btn)

        self.email_btn = QPushButton("✉ Send via Email")
        self.email_btn.setEnabled(False)
        self.email_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.email_btn.setStyleSheet("""
            QPushButton {
                background-color: #7C3AED;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover { background-color: #6D28D9; }
            QPushButton:disabled { background-color: #E2E8F0; color: #94A3B8; }
        """)
        self.email_btn.clicked.connect(self.open_email_composer)
        top_bar.addWidget(self.email_btn)

        right_layout.addLayout(top_bar)

        # Progress / Status Card
        self.progress_card = QFrame()
        self.progress_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        prog_lay = QVBoxLayout(self.progress_card)
        prog_lay.setContentsMargins(16, 12, 16, 12)
        prog_lay.setSpacing(8)

        prog_status_row = QHBoxLayout()
        self.lbl_status = QLabel("Status: Waiting for Statement PDF...")
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: bold; color: #475569; font-family: 'Times New Roman';")
        prog_status_row.addWidget(self.lbl_status)
        prog_status_row.addStretch()

        self.lbl_tx_count = QLabel("Transactions: 0")
        self.lbl_tx_count.setStyleSheet("font-size: 12px; font-weight: bold; color: #0F172A; font-family: 'Times New Roman';")
        prog_status_row.addWidget(self.lbl_tx_count)
        prog_lay.addLayout(prog_status_row)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(6)
        self.pbar.setValue(0)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #0037b0;
                border-radius: 3px;
            }
        """)
        prog_lay.addWidget(self.pbar)
        right_layout.addWidget(self.progress_card)

        # Table Excel Preview
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(5)
        self.preview_table.setHorizontalHeaderLabels(["Date", "Narration", "Debit", "Credit", "Balance"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.preview_table, stretch=1)

        # Recent outputs list
        recent_box = QHBoxLayout()
        recent_box.setSpacing(12)
        
        recent_lbl = QLabel("Recent Generated Sheets:")
        recent_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B; text-transform: uppercase; font-family: 'Times New Roman';")
        recent_box.addWidget(recent_lbl)

        self.recent_list = QComboBox()
        self.recent_list.setMinimumWidth(300)
        self.recent_list.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                font-size: 12px;
            }
        """)
        self.recent_list.currentIndexChanged.connect(self.on_recent_sheet_selected)
        recent_box.addWidget(self.recent_list)
        recent_box.addStretch()
        right_layout.addLayout(recent_box)

        main_layout.addWidget(right_panel, stretch=1)

        # Initial Load
        self.load_recent_generated_sheets()

    # ==========================================
    # DRAG & DROP LOGIC
    # ==========================================
    
    def zone_drag_enter(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().lower().endswith('.pdf'):
                event.acceptProposedAction()
                self.drop_zone.setStyleSheet("""
                    QFrame#DropZone {
                        background-color: #EFF6FF;
                        border: 2px dashed #0037b0;
                        border-radius: 12px;
                    }
                """)

    def zone_drag_leave(self, event):
        self.reset_drop_zone_style()

    def zone_drop(self, event):
        self.reset_drop_zone_style()
        urls = event.mimeData().urls()
        if urls:
            self.load_pdf_statement(urls[0].toLocalFile())

    def browse_pdf_file(self):
        doc_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Bank Statement PDF", doc_dir, "PDF Files (*.pdf)"
        )
        if path:
            self.load_pdf_statement(path)

    def reset_drop_zone_style(self):
        theme = getattr(self, "current_theme", "light")
        if theme == "dark":
            self.drop_zone.setStyleSheet("""
                QFrame#DropZone {
                    background-color: #1E293B;
                    border: 2px dashed #334155;
                    border-radius: 12px;
                }
                QFrame#DropZone:hover {
                    border-color: #3B82F6;
                    background-color: #0F172A;
                }
            """)
        else:
            self.drop_zone.setStyleSheet("""
                QFrame#DropZone {
                    background-color: #F8FAFC;
                    border: 2px dashed #CBD5E1;
                    border-radius: 12px;
                }
                QFrame#DropZone:hover {
                    border-color: #0037b0;
                    background-color: #EFF6FF;
                }
            """)

    # ==========================================
    # WORKFLOW STAGE 1: METADATA & BANK DETECTION
    # ==========================================
    
    def load_pdf_statement(self, file_path):
        """Validates layout and page structures and detects the bank metadata."""
        if not file_path or not os.path.exists(file_path):
            return

        self.file_path = file_path
        self.lbl_status.setText("Status: Reading document metadata...")
        self.pbar.setValue(0)
        self.lbl_tx_count.setText("Transactions: -")
        self.generate_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.preview_table.setRowCount(0)

        # Show load values
        self.lbl_filename.setText(os.path.basename(file_path))
        self.lbl_bank.setText("Identifying...")
        self.lbl_pages.setText("Calculating...")
        self.lbl_doctype.setText("Scanning...")

        def on_started():
            pass

        def on_finished(meta):
            self.page_count = meta["page_count"]
            self.detected_bank = meta["bank_name"]
            
            # Scanned vs digital
            from services.pdf_reader import PDFReader
            is_digital = PDFReader.is_digital_pdf(self.file_path)
            self.doc_type_desc = "Digital PDF" if is_digital else "Scanned PDF"

            # Populate preview panels
            self.lbl_bank.setText(self.detected_bank)
            self.lbl_pages.setText(f"{self.page_count} pages")
            self.lbl_doctype.setText(self.doc_type_desc)
            
            self.lbl_status.setText("Status: PDF verified successfully. Ready to generate Excel.")
            self.generate_btn.setEnabled(True)
            Toast.success(self, "✓ Statement verification successful!")

        def on_error(err):
            self.lbl_status.setText("Status: Verification failed.")
            self.lbl_filename.setText("-")
            self.lbl_bank.setText("-")
            self.lbl_pages.setText("-")
            self.lbl_doctype.setText("-")
            QMessageBox.critical(self, "PDF Load Failed", f"Could not inspect the document layout:\n{err}")

        self.active_thread = StatementService.start_validate(
            file_path, on_started, on_finished, on_error
        )

    # ==========================================
    # WORKFLOW STAGE 2: PARSE & EXCEL GENERATION
    # ==========================================
    
    def start_parsing_process(self):
        """Launches background transaction parsing worker."""
        if not self.file_path or not os.path.exists(self.file_path):
            return

        self.generate_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.lbl_status.setText("Status: Initializing parsing engines...")
        self.pbar.setValue(0)

        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"

        # Start background parse thread
        self.history_record_id = HistoryService.create_record(
            user_id=user_id,
            pdf_path=self.file_path,
            bank_name=self.detected_bank,
            status="Processing",
            output_format="Excel"
        )

        def on_started():
            pass

        def on_step_started(idx):
            if idx == 1:
                self.lbl_status.setText("Status: Pre-processing PDF...")
            elif idx == 2:
                self.lbl_status.setText("Status: Reading pages layout...")
            elif idx == 3:
                self.lbl_status.setText("Status: Running OCR alignment...")

        def on_step_completed(idx, status):
            pass

        def on_progress(cur, tot, tx_count):
            self.lbl_status.setText(f"Status: Processing Page {cur} of {tot}...")
            self.lbl_tx_count.setText(f"Transactions: {tx_count}")
            self.pbar.setValue(int(cur / tot * 100))

        def on_finished(payload):
            self.parsed_payload = payload
            if not payload or not payload.get("transactions"):
                self.lbl_status.setText("Status: Extraction failed (0 transactions).")
                self.generate_btn.setEnabled(True)
                if hasattr(self, "history_record_id"):
                    HistoryService.update_record_status(self.history_record_id, status="Failed")
                QMessageBox.critical(self, "Extraction Failed", "No transactions could be extracted from this PDF statement.")
                return

            self.lbl_tx_count.setText(f"Transactions: {len(payload['transactions'])}")
            
            # Re-populate the preview grid with parsed rows
            self.populate_preview_table(payload["transactions"])
            
            # Start Excel write step
            self.start_excel_generation(user_id)

        def on_error(err):
            self.lbl_status.setText("Status: Extraction error.")
            self.generate_btn.setEnabled(True)
            if hasattr(self, "history_record_id"):
                HistoryService.update_record_status(self.history_record_id, status="Failed")
            QMessageBox.critical(self, "Parsing Failed", f"An error occurred during extraction:\n{err}")

        self.active_thread = StatementService.start_parse(
            self.file_path, on_started, on_step_started, on_step_completed, on_progress, on_finished, on_error
        )

    def start_excel_generation(self, user_id):
        self.lbl_status.setText("Status: Generating stylized Excel sheet...")
        record_id = getattr(self, "history_record_id", None)

        def on_started():
            pass

        def on_step_started(idx):
            if idx == 6:
                self.lbl_status.setText("Status: Saving workbook and logs...")

        def on_step_completed(idx, status):
            pass

        def on_finished(excel_path):
            self.excel_output_path = excel_path
            self.lbl_status.setText("Status: Conversion completed successfully!")
            self.pbar.setValue(100)
            self.download_btn.setEnabled(True)
            self.email_btn.setEnabled(True)
            self.generate_btn.setEnabled(True)
            self.load_recent_generated_sheets()
            Toast.success(self, "✓ Excel workbook compiled successfully!")

        def on_error(err):
            self.lbl_status.setText("Status: Excel generation failed.")
            self.generate_btn.setEnabled(True)
            if hasattr(self, "history_record_id"):
                HistoryService.update_record_status(self.history_record_id, status="Failed")
            QMessageBox.critical(self, "Excel Compilation Failed", f"Could not create spreadsheet:\n{err}")

        self.active_thread = StatementService.start_generate_excel(
            user_id, self.parsed_payload, record_id, on_started, on_step_started, on_step_completed, on_finished, on_error
        )

    def populate_preview_table(self, transactions):
        """Populates the QTableWidget with the parsed transaction records."""
        self.preview_table.setRowCount(0)
        self.preview_table.setRowCount(len(transactions))
        
        for idx, tx in enumerate(transactions):
            self.preview_table.setItem(idx, 0, QTableWidgetItem(str(tx.get("date", ""))))
            self.preview_table.setItem(idx, 1, QTableWidgetItem(str(tx.get("narration", ""))))
            self.preview_table.setItem(idx, 2, QTableWidgetItem(str(tx.get("debit", ""))))
            self.preview_table.setItem(idx, 3, QTableWidgetItem(str(tx.get("credit", ""))))
            self.preview_table.setItem(idx, 4, QTableWidgetItem(str(tx.get("balance", ""))))

    def open_generated_excel(self):
        if not self.excel_output_path or not os.path.exists(self.excel_output_path):
            return
        try:
            if os.name == 'nt':
                os.startfile(self.excel_output_path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(["open", self.excel_output_path])
            else:
                import subprocess
                subprocess.run(["xdg-open", self.excel_output_path])
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Could not open spreadsheet file:\n{e}")

    # ==========================================
    # HISTORY LOADS
    # ==========================================
    
    def load_recent_generated_sheets(self):
        """Populates dropdown selector with recently generated Excel sheets."""
        self.recent_list.blockSignals(True)
        self.recent_list.clear()
        
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        logs = HistoryService.get_history_logs(user_id=user_id)
        
        completed_logs = [log for log in logs if log.get("status") == "Completed" and log.get("excel_path")]
        
        if not completed_logs:
            self.recent_list.addItem("No Excel files found in history.", None)
        else:
            self.recent_list.addItem("Choose a recently generated Excel...", None)
            for log in completed_logs:
                excel_path = log.get("excel_path", "")
                filename = os.path.basename(excel_path) if excel_path else "Parsed_Sheet.xlsx"
                upload_date = log.get("upload_date")
                if hasattr(upload_date, "strftime"):
                    date_str = upload_date.strftime("%Y-%m-%d")
                elif isinstance(upload_date, str):
                    date_str = upload_date[:10]
                else:
                    date_str = str(upload_date or "")[:10]
                bank = log.get("bank_name", "Unknown Bank")
                display_text = f"{bank} ({date_str}) - {filename}"
                self.recent_list.addItem(display_text, excel_path)
                
        self.recent_list.blockSignals(False)

    def on_recent_sheet_selected(self, index):
        excel_path = self.recent_list.currentData()
        if not excel_path:
            return

        if os.path.exists(excel_path):
            self.excel_output_path = excel_path
            self.download_btn.setEnabled(True)
            
            # Optionally populate preview table from historical file
            try:
                # Reuse load method from ui/ai_auditor
                from ui.ai_auditor import AIAuditorWidget
                dummy = AIAuditorWidget(self)
                txs = dummy.load_transactions_from_excel(excel_path)
                self.populate_preview_table(txs)
                self.lbl_tx_count.setText(f"Transactions: {len(txs)}")
                self.lbl_status.setText("Status: Loaded historical spreadsheet preview.")
            except:
                pass

    def update_theme_style(self, theme):
        self.current_theme = theme
        self.reset_drop_zone_style()
        
        if theme == "dark":
            left_panel = self.findChild(QFrame, "LeftPanel")
            if left_panel:
                left_panel.setStyleSheet("QFrame#LeftPanel { background-color: #1E293B; border: 1px solid #334155; border-radius: 16px; }")
            right_panel = self.findChild(QFrame, "RightPanel")
            if right_panel:
                right_panel.setStyleSheet("QFrame#RightPanel { background-color: #1E293B; border: 1px solid #334155; border-radius: 16px; }")
            
            self.details_card.setStyleSheet("background-color: #334155; border: 1px solid #475569; border-radius: 12px;")
            self.progress_card.setStyleSheet("background-color: #334155; border: 1px solid #475569; border-radius: 12px;")
            self.preview_table.setStyleSheet("QTableWidget { background-color: #1E293B; border: none; gridline-color: #334155; color: #F8FAFC; }")
            
            self.recent_list.setStyleSheet("""
                QComboBox {
                    padding: 4px 8px;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    background-color: #1E293B;
                    color: #F8FAFC;
                    font-size: 12px;
                }
            """)
            
            for label in self.findChildren(QLabel):
                style = label.styleSheet()
                if "color: #0F172A" in style:
                    label.setStyleSheet(style.replace("color: #0F172A", "color: #F8FAFC"))
        else:
            left_panel = self.findChild(QFrame, "LeftPanel")
            if left_panel:
                left_panel.setStyleSheet("QFrame#LeftPanel { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; }")
            right_panel = self.findChild(QFrame, "RightPanel")
            if right_panel:
                right_panel.setStyleSheet("QFrame#RightPanel { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; }")
                
            self.details_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #EFF6FF; border-radius: 12px;")
            self.progress_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
            self.preview_table.setStyleSheet("QTableWidget { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; color: #0F172A; }")
            
            self.recent_list.setStyleSheet("""
                QComboBox {
                    padding: 4px 8px;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    background-color: #FFFFFF;
                    color: #0F172A;
                    font-size: 12px;
                }
            """)
            
            for label in self.findChildren(QLabel):
                style = label.styleSheet()
                if "color: #F8FAFC" in style:
                    label.setStyleSheet(style.replace("color: #F8FAFC", "color: #0F172A"))

    def open_email_composer(self):
        """Opens Email Composer pre-attaching generated Excel sheet."""
        from ui.email_composer_dialog import EmailComposerDialog
        
        attachment = getattr(self, "excel_output_path", None)
        bank = getattr(self, "detected_bank", "") or ""

        dialog = EmailComposerDialog(
            report_type="Excel Export Report",
            default_attachment=attachment,
            bank_name=bank,
            parent=self
        )
        dialog.exec()
