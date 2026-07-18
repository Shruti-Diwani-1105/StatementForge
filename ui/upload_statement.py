import os
import sys
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QSpacerItem, QSizePolicy, QStackedWidget, QDialog, QProgressBar, QMessageBox, QGridLayout,
    QGraphicsDropShadowEffect, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths
from PyQt6.QtGui import QPixmap, QCursor, QColor

from services.statement_service import StatementService
from services.history_service import HistoryService
from utils.user_session import UserSession
from widgets.custom_card import CustomCard
from settings.toast import Toast


class ErrorDialog(QDialog):
    """Beautiful, custom-styled error dialog for specific exception messages."""
    def __init__(self, error_type, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(error_type)
        self.setFixedSize(460, 240)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; border-radius: 12px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(14)
        
        icon = QLabel("⚠️")
        icon.setStyleSheet("font-size: 28px; color: #EF4444;")
        header.addWidget(icon)
        
        title_lbl = QLabel(error_type)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #1E293B;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("font-size: 13px; color: #475569; line-height: 18px;")
        layout.addWidget(msg_lbl)

        layout.addStretch()

        btn = QPushButton("OK")
        btn.setFixedSize(100, 34)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        btn.clicked.connect(self.accept)
        
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        btn_lay.addWidget(btn)
        layout.addLayout(btn_lay)



class UploadStatementWidget(QWidget):
    """
    Redesigned, premium enterprise drag-and-drop upload screen.
    Checks PDF layout validation, detects bank metadata, displays action selectors,
    and runs local OCR/Vision pipelines asynchronously.
    """
    processingCompleted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.page_count = 0
        self.detected_bank = "Unknown Bank"
        self.doc_type_desc = "Digital PDF"
        
        self.parsed_payload = None
        self.active_thread = None
        self.post_process_action = "excel"
        self.current_theme = "light"
        
        # Stacked layout
        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.init_upload_page()
        self.init_choice_page()
        self.init_processing_page()
        self.init_success_page()

    # ==========================================
    # PAGE 0: REDESIGNED ENTERPRISE UPLOAD PAGE
    # ==========================================
    def init_upload_page(self):
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        page.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        # Title block
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        self.header_lbl = QLabel("Upload Bank Statement")
        self.header_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #0F172A; font-family: 'Times New Roman';")
        self.sub_lbl = QLabel("Parse, structure, and audit bank statements with local engine fallbacks.")
        self.sub_lbl.setStyleSheet("color: #64748B; font-size: 13px; font-family: 'Times New Roman';")
        header_lay.addWidget(self.header_lbl)
        header_lay.addWidget(self.sub_lbl)
        layout.addLayout(header_lay)

        # Drop Zone Frame
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("DropZone")
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.setMinimumHeight(260)
        
        # Soft shadow for drop zone
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 4)
        self.drop_zone.setGraphicsEffect(shadow)
        
        self.drop_zone.setStyleSheet("""
            QFrame#DropZone {
                background-color: #FFFFFF;
                border: 2px dashed #CBD5E1;
                border-radius: 16px;
            }
            QFrame#DropZone:hover {
                border-color: #3B82F6;
                background-color: #EFF6FF;
            }
        """)
        self.drop_zone.dragEnterEvent = self.zone_drag_enter
        self.drop_zone.dragLeaveEvent = self.zone_drag_leave
        self.drop_zone.dropEvent = self.zone_drop

        zone_layout = QVBoxLayout(self.drop_zone)
        zone_layout.setContentsMargins(32, 32, 32, 32)
        zone_layout.setSpacing(12)
        
        zone_layout.addStretch()

        upload_icon = QLabel()
        upload_icon.setFixedSize(48, 48)
        upload_pixmap = QPixmap("assets/icons/upload.png")
        if not upload_pixmap.isNull():
            upload_icon.setPixmap(upload_pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        zone_layout.addWidget(upload_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        prompt_lbl = QLabel("Drag & Drop statement statement PDF here")
        prompt_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E293B; font-family: 'Times New Roman';")
        zone_layout.addWidget(prompt_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        help_lbl = QLabel("Supports only PDF statement formats")
        help_lbl.setStyleSheet("font-size: 12px; color: #64748B; font-family: 'Times New Roman';")
        zone_layout.addWidget(help_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self.browse_btn = QPushButton("Browse File")
        self.browse_btn.setFixedSize(140, 36)
        self.browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        self.browse_btn.clicked.connect(self.browse_pdf_file)
        zone_layout.addWidget(self.browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        zone_layout.addStretch()
        layout.addWidget(self.drop_zone)

        # Supported banks card list
        supported_card = QFrame()
        supported_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        sup_lay = QVBoxLayout(supported_card)
        sup_lay.setContentsMargins(16, 14, 16, 14)
        sup_lay.setSpacing(8)
        
        sup_title = QLabel("Supported Institutions & Formats")
        sup_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        sup_lay.addWidget(sup_title)
        
        pills = QHBoxLayout()
        pills.setSpacing(8)
        for b_name in ["HDFC", "SBI", "ICICI", "Axis Bank", "Kotak", "BoB", "Canara", "Union Bank", "PNB", "IndusInd"]:
            pill = QLabel(b_name)
            pill.setStyleSheet("""
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
                color: #475569;
            """)
            pills.addWidget(pill)
        pills.addStretch()
        sup_lay.addLayout(pills)
        layout.addWidget(supported_card)

        # Recent Uploads Card
        layout.addSpacing(8)
        recent_header = QLabel("Recent Processing Activity")
        recent_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #1E293B; font-family: 'Times New Roman';")
        layout.addWidget(recent_header)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["Detected Bank", "File Name", "Transactions", "Time", "Status"])
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.recent_table.setFixedHeight(140)
        self.recent_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.recent_table)

        page.setWidget(scroll_content)
        self.stack.addWidget(page)

    def zone_drag_enter(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().lower().endswith('.pdf'):
                event.acceptProposedAction()
                self.drop_zone.setStyleSheet("""
                    QFrame#DropZone {
                        background-color: #EFF6FF;
                        border: 2px dashed #2563EB;
                        border-radius: 16px;
                    }
                """)

    def zone_drag_leave(self, event):
        self.reset_drop_zone_style()

    def zone_drop(self, event):
        self.reset_drop_zone_style()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.start_validation_flow(path)

    def browse_pdf_file(self):
        doc_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Bank Statement PDF", doc_dir, "PDF Files (*.pdf)"
        )
        if path:
            self.start_validation_flow(path)

    def reset_drop_zone_style(self):
        theme = getattr(self, "current_theme", "light")
        if theme == "dark":
            self.drop_zone.setStyleSheet("""
                QFrame#DropZone {
                    background-color: #1E293B;
                    border: 2px dashed #334155;
                    border-radius: 16px;
                }
                QFrame#DropZone:hover {
                    border-color: #3B82F6;
                    background-color: #0F172A;
                }
            """)
        else:
            self.drop_zone.setStyleSheet("""
                QFrame#DropZone {
                    background-color: #FFFFFF;
                    border: 2px dashed #CBD5E1;
                    border-radius: 16px;
                }
                QFrame#DropZone:hover {
                    border-color: #3B82F6;
                    background-color: #EFF6FF;
                }
            """)

    def show_error_popup(self, err_msg):
        dialog = ErrorDialog("Validation Error", err_msg, self)
        dialog.exec()

    def show_coming_soon(self, module_name):
        """Displays a professional message box for unimplemented features."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Coming Soon")
        msg_box.setText(f"{module_name} - Feature Coming Soon!")
        msg_box.setInformativeText("This feature is scheduled for development in the next sprint.")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setStyleSheet("""
            QMessageBox { background-color: #FFFFFF; }
            QPushButton { background-color: #2563EB; color: white; border-radius: 6px; padding: 6px 12px; }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        msg_box.exec()

    # ==========================================
    # WORKFLOW STEP 1: VALIDATION & BANK DETECTION ONLY
    # ==========================================
    def start_validation_flow(self, file_path):
        """Spawns background worker to extract pages count and detect bank name."""
        self.file_path = file_path

        # Show temporary verification popup
        self.progress_box = QMessageBox(self)
        self.progress_box.setWindowTitle("Validating PDF")
        self.progress_box.setText("Reading statement metadata and running bank detector...")
        self.progress_box.setStandardButtons(QMessageBox.StandardButton.NoButton)
        self.progress_box.setStyleSheet("QMessageBox { background-color: #FFFFFF; }")

        def on_started():
            self.progress_box.show()

        def on_finished(meta):
            self.progress_box.accept()
            self.file_path = meta["file_path"]
            self.page_count = meta["page_count"]
            self.detected_bank = meta["bank_name"]
            
            # Detect scanned vs digital
            from services.pdf_reader import PDFReader
            is_digital = PDFReader.is_digital_pdf(self.file_path)
            self.doc_type_desc = "Digital PDF" if is_digital else "Scanned PDF"

            # Launch Feature Selection dialogue
            self.show_feature_selection()

        def on_error(err):
            self.progress_box.reject()
            self.show_error_popup(err)

        self.active_thread = StatementService.start_validate(
            file_path, on_started, on_finished, on_error
        )

    def init_choice_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Header info card
        self.choice_header = QFrame()
        self.choice_header.setObjectName("ChoiceHeader")
        self.choice_header.setStyleSheet("""
            QFrame#ChoiceHeader {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        
        header_shadow = QGraphicsDropShadowEffect()
        header_shadow.setBlurRadius(12)
        header_shadow.setColor(QColor(0, 0, 0, 15))
        header_shadow.setOffset(0, 2)
        self.choice_header.setGraphicsEffect(header_shadow)

        header_lay = QHBoxLayout(self.choice_header)
        header_lay.setContentsMargins(20, 16, 20, 16)
        
        self.choice_info_lbl = QLabel("📂 Statement Loaded")
        self.choice_info_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E293B;")
        header_lay.addWidget(self.choice_info_lbl)
        header_lay.addStretch()
        layout.addWidget(self.choice_header)

        # Prompt Subtitle
        sub_lbl = QLabel("Select an action module to process this statement:")
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(sub_lbl)

        # Grid layout for selection
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(20)

        # Card 1: Generate Excel
        self.choice_excel_card = CustomCard(
            "Generate Excel",
            "Parse PDF tables directly into structured spreadsheets.",
            "assets/icons/excel.png",
            "#F0FDF4"
        )
        self.choice_excel_card.clicked.connect(self.choice_generate_excel)
        grid_layout.addWidget(self.choice_excel_card, 0, 0)

        # Card 2: AI Report
        self.choice_ai_card = CustomCard(
            "AI Report",
            "Generate wealth reports and audit transactions via AI.",
            "assets/icons/ai.png",
            "#F5F3FF"
        )
        self.choice_ai_card.clicked.connect(self.choice_ai_report)
        grid_layout.addWidget(self.choice_ai_card, 0, 1)

        # Card 3: GST Report
        self.choice_gst_card = CustomCard(
            "GST Report",
            "Prepare statements for tax filings.",
            "assets/icons/gst.png",
            "#FFFBEB"
        )
        self.choice_gst_card.clicked.connect(lambda: self.show_coming_soon("GST Report"))
        grid_layout.addWidget(self.choice_gst_card, 0, 2)

        # Card 4: Tally Export
        self.choice_tally_card = CustomCard(
            "Tally Export",
            "Export ready for Tally integration.",
            "assets/icons/tally.png",
            "#FFF7ED"
        )
        self.choice_tally_card.clicked.connect(lambda: self.show_coming_soon("Tally Export"))
        grid_layout.addWidget(self.choice_tally_card, 0, 3)

        # Card 5: Duplicate Finder
        self.choice_duplicate_card = CustomCard(
            "Duplicate Finder",
            "Find double entry transactions.",
            "assets/icons/duplicate.png",
            "#FEF2F2"
        )
        self.choice_duplicate_card.clicked.connect(lambda: self.show_coming_soon("Duplicate Finder"))
        grid_layout.addWidget(self.choice_duplicate_card, 1, 0)

        # Card 6: Statement History
        self.choice_history_card = CustomCard(
            "Statement History",
            "View processing activity logs and past parsed statements.",
            "assets/icons/history.png",
            "#EFF6FF"
        )
        self.choice_history_card.clicked.connect(self.choice_history)
        grid_layout.addWidget(self.choice_history_card, 1, 1)

        # Card 7: Email Report
        self.choice_email_card = CustomCard(
            "Email Report",
            "Send parsed summaries safely.",
            "assets/icons/email.png",
            "#ECFDF5"
        )
        self.choice_email_card.clicked.connect(lambda: self.show_coming_soon("Email Report"))
        grid_layout.addWidget(self.choice_email_card, 1, 2)

        # Card 8: Cancel & Upload New
        self.choice_cancel_card = CustomCard(
            "Cancel & Upload New",
            "Discard this statement and select a different file.",
            "assets/icons/logout.png",
            "#FEF2F2"
        )
        self.choice_cancel_card.clicked.connect(self.reset_to_upload)
        grid_layout.addWidget(self.choice_cancel_card, 1, 3)

        layout.addWidget(grid_widget)
        layout.addStretch()

        self.stack.addWidget(page)

    def show_feature_selection(self):
        """Displays selection dashboard-style view for choosing next step."""
        filename = os.path.basename(self.file_path)
        self.choice_info_lbl.setText(f"📂 File: {filename}   |   🏦 Bank: {self.detected_bank}   |   📄 Pages: {self.page_count} ({self.doc_type_desc})")
        self.stack.setCurrentIndex(1)

    # ==========================================
    # PAGE 1: PROCESSING LOADING SCREEN
    # ==========================================
    def init_processing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.proc_title = QLabel("Extracting & Analyzing PDF Statement")
        self.proc_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #0F172A;")
        self.proc_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.proc_title)

        details_box = QFrame()
        details_box.setFixedWidth(500)
        details_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        grid = QGridLayout(details_box)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(12)

        def add_row(grid_w, r_idx, label, attr):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748B;")
            val = QLabel("-")
            val.setStyleSheet("font-size: 13px; font-weight: 600; color: #0F172A;")
            setattr(self, attr, val)
            grid_w.addWidget(lbl, r_idx, 0)
            grid_w.addWidget(val, r_idx, 1)

        add_row(grid, 0, "Detected Bank:", "proc_bank_lbl")
        add_row(grid, 1, "Total Pages:", "proc_pages_lbl")
        add_row(grid, 2, "Current Status:", "proc_status_lbl")
        add_row(grid, 3, "Transactions Extracted:", "proc_txs_lbl")

        layout.addWidget(details_box)

        self.proc_bar = QProgressBar()
        self.proc_bar.setFixedWidth(500)
        self.proc_bar.setFixedHeight(8)
        self.proc_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 4px;
            }
        """)
        self.proc_bar.setTextVisible(False)
        self.proc_bar.setValue(0)
        layout.addWidget(self.proc_bar)

        self.proc_cancel_btn = QPushButton("Cancel Processing")
        self.proc_cancel_btn.setFixedSize(160, 36)
        self.proc_cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.proc_cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #EF4444;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
            }
        """)
        self.proc_cancel_btn.clicked.connect(self.cancel_processing)
        layout.addWidget(self.proc_cancel_btn)

        self.stack.addWidget(page)

    def cancel_processing(self):
        from services.history_service import HistoryService
        if self.active_thread and self.active_thread.isRunning():
            self.active_thread.terminate()
            self.active_thread.wait()
        if hasattr(self, "history_record_id"):
            HistoryService.update_record_status(self.history_record_id, status="Cancelled")
        self.reset_to_upload()

    # ==========================================
    # WORKFLOW STEP 2: PARSE & COMPILE EXCEL
    # ==========================================
    def start_processing_flow(self):
        """Launches the sequential processing steps 1-4."""
        from services.history_service import HistoryService
        self.proc_bank_lbl.setText(self.detected_bank)
        self.proc_pages_lbl.setText(f"{self.page_count} pages")
        self.proc_status_lbl.setText("Initializing parse engines...")
        self.proc_txs_lbl.setText("0 records")
        self.proc_bar.setValue(0)
        self.stack.setCurrentIndex(2) # Switch to processing screen

        # Create history record
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
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
                self.proc_status_lbl.setText("Pre-processing document...")
            elif idx == 2:
                self.proc_status_lbl.setText("Reading layout pages...")
            elif idx == 3:
                self.proc_status_lbl.setText("Configuring OCR alignments...")

        def on_step_completed(idx, status):
            pass

        def on_progress(cur, tot, tx_count):
            self.proc_status_lbl.setText(f"Processing Page {cur} of {tot}...")
            self.proc_txs_lbl.setText(f"{tx_count} records")
            self.proc_bar.setValue(int(cur / tot * 100))

        def on_finished(payload):
            from services.history_service import HistoryService
            self.parsed_payload = payload
            if not payload or not payload.get("transactions"):
                self.reset_to_upload()
                if hasattr(self, "history_record_id"):
                    HistoryService.update_record_status(self.history_record_id, status="Failed")
                logs = payload.get("logs") if payload else "No log output available."
                self.show_error_popup(
                    "No transactions could be extracted from this PDF statement.\n\n"
                    f"Detailed Engine Logs:\n{logs}"
                )
                return
            
            action = getattr(self, "post_process_action", "excel")
            if action == "ai_report":
                self.generate_excel_in_background(payload)
                p = self.parent()
                dashboard = None
                while p:
                    if hasattr(p, "page_stack") and hasattr(p, "ai_auditor_widget"):
                        dashboard = p
                        break
                    p = p.parent()
                if dashboard:
                    dashboard.ai_auditor_widget.set_active_statement(payload)
                    dashboard.switch_dashboard_page("ai_auditor")
                    dashboard.ai_auditor_widget.run_ai_task("report")
                self.reset_to_upload()
            else:
                self.generate_excel_flow()

        def on_error(err):
            from services.history_service import HistoryService
            self.reset_to_upload()
            if hasattr(self, "history_record_id"):
                HistoryService.update_record_status(self.history_record_id, status="Failed")
            self.show_error_popup(err)

        self.active_thread = StatementService.start_parse(
            self.file_path, on_started, on_step_started, on_step_completed, on_progress, on_finished, on_error
        )

    def generate_excel_flow(self):
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        self.proc_status_lbl.setText("Formatting and writing Excel worksheets...")

        def on_started():
            pass

        def on_step_started(idx):
            if idx == 6:
                self.proc_status_lbl.setText("Saving workbook and logging stats...")

        def on_step_completed(idx, status):
            pass

        def on_finished(excel_path):
            self.transition_to_success(excel_path)

        def on_error(err):
                from services.history_service import HistoryService
                self.reset_to_upload()
                if hasattr(self, "history_record_id"):
                    HistoryService.update_record_status(self.history_record_id, status="Failed")
                self.show_error_popup(err)

        record_id = getattr(self, "history_record_id", None)
        self.active_thread = StatementService.start_generate_excel(
            user_id, self.parsed_payload, record_id, on_started, on_step_started, on_step_completed, on_finished, on_error
        )

    # ==========================================
    # PAGE 2: SUCCESS SCREEN
    # ==========================================
    def init_success_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("✓")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(64, 64)
        icon.setStyleSheet("""
            background-color: #ECFDF5;
            color: #10B981;
            font-size: 32px;
            font-weight: bold;
            border-radius: 32px;
            border: 1px solid #A7F3D0;
        """)
        layout.addWidget(icon)

        title = QLabel("Excel Generated Successfully")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #059669;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        details_box = QFrame()
        details_box.setFixedWidth(540)
        details_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        grid = QGridLayout(details_box)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(12)

        def add_row(grid_w, r_idx, label, attr):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
            val = QLabel("")
            val.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")
            setattr(self, attr, val)
            grid_w.addWidget(lbl, r_idx, 0)
            grid_w.addWidget(val, r_idx, 1)

        add_row(grid, 0, "File Name:", "suc_file_lbl")
        add_row(grid, 1, "Excel Location:", "suc_loc_lbl")
        add_row(grid, 2, "Detected Bank:", "suc_bank_lbl")
        add_row(grid, 3, "Total Pages:", "suc_pages_lbl")
        add_row(grid, 4, "Transactions Extracted:", "suc_txs_lbl")
        add_row(grid, 5, "Processing Time:", "suc_time_lbl")

        layout.addWidget(details_box)

        # Action bar buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def make_btn(text, style, callback):
            btn = QPushButton(text)
            btn.setFixedHeight(38)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(style)
            btn.clicked.connect(callback)
            btn_box.addWidget(btn)
            return btn

        style_p = "QPushButton { background-color: #2563EB; color: white; border-radius: 6px; font-weight: 600; font-size: 13px; border: none; padding: 0 16px; } QPushButton:hover { background-color: #1D4ED8; }"
        style_s = "QPushButton { background-color: #FFFFFF; color: #475569; border: 1px solid #CBD5E1; border-radius: 6px; font-weight: 600; font-size: 13px; padding: 0 16px; } QPushButton:hover { background-color: #F8FAFC; color: #0F172A; }"
        
        make_btn("Open Excel", style_p, self.open_generated_excel)
        make_btn("Open Folder", style_s, self.open_output_folder)
        make_btn("Return to Dashboard", style_s, self.return_to_dashboard)

        layout.addLayout(btn_box)
        self.stack.addWidget(page)

    def transition_to_success(self, excel_path):
        self.excel_output_path = excel_path
        self.suc_file_lbl.setText(os.path.basename(excel_path))
        self.suc_loc_lbl.setText(excel_path.replace("\\", "/"))
        self.suc_bank_lbl.setText(self.parsed_payload["bank_name"])
        self.suc_pages_lbl.setText(f"{self.parsed_payload['page_count']} pages")
        self.suc_txs_lbl.setText(f"{len(self.parsed_payload['transactions'])} transactions")
        self.suc_time_lbl.setText(f"{self.parsed_payload['processing_time']:.2f} seconds")
        self.stack.setCurrentIndex(3)

    def open_generated_excel(self):
        try:
            if os.path.exists(self.excel_output_path):
                if os.name == 'nt':
                    os.startfile(self.excel_output_path)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.run(["open", self.excel_output_path])
                else:
                    import subprocess
                    subprocess.run(["xdg-open", self.excel_output_path])
        except Exception as e:
            print(f"Error opening Excel: {e}")

    def open_output_folder(self):
        try:
            folder = os.path.dirname(self.excel_output_path)
            if os.path.exists(folder):
                if os.name == 'nt':
                    os.startfile(folder)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.run(["open", folder])
                else:
                    import subprocess
                    subprocess.run(["xdg-open", folder])
        except Exception as e:
            print(f"Error opening folder: {e}")

    def return_to_dashboard(self):
        self.reset_to_upload()
        self.processingCompleted.emit()
        p = self.parent()
        while p:
            if hasattr(p, "switch_dashboard_page"):
                p.switch_dashboard_page("dashboard")
                break
            p = p.parent()

    def reset_to_upload(self):
        self.file_path = None
        self.page_count = 0
        self.detected_bank = "Unknown Bank"
        self.parsed_payload = None
        self.post_process_action = "excel"
        self.stack.setCurrentIndex(0)
        self.load_recent_uploads()

    def start_ai_report_flow(self):
        self.post_process_action = "ai_report"
        self.start_processing_flow()

    def generate_excel_in_background(self, payload):
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        record_id = getattr(self, "history_record_id", None)
        
        self.bg_excel_thread = StatementService.start_generate_excel(
            user_id, payload, record_id,
            lambda: None, lambda idx: None, lambda idx, status: None,
            lambda path: print(f"Excel generated silently in background: {path}"),
            lambda err: print(f"Silent excel generation error: {err}")
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.load_recent_uploads()

    def update_theme_style(self, theme):
        self.current_theme = theme
        self.reset_drop_zone_style()
        if theme == "dark":
            self.header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #F8FAFC;")
            self.sub_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
            self.recent_table.setStyleSheet("""
                QTableWidget {
                    background-color: #1E293B;
                    border: none;
                    gridline-color: #334155;
                    color: #F8FAFC;
                }
            """)
        else:
            self.header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
            self.sub_lbl.setStyleSheet("color: #64748B; font-size: 13px;")
            self.recent_table.setStyleSheet("""
                QTableWidget {
                    background-color: #FFFFFF;
                    border: none;
                    gridline-color: #F3F4F6;
                    color: #111827;
                }
            """)
        
        if theme == "dark":
            if hasattr(self, "choice_header"):
                self.choice_header.setStyleSheet("""
                    QFrame#ChoiceHeader {
                        background-color: #1E293B;
                        border: 1px solid #334155;
                        border-radius: 12px;
                    }
                """)
                self.choice_info_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
            for card_attr in ["choice_excel_card", "choice_ai_card", "choice_gst_card", "choice_tally_card", "choice_duplicate_card", "choice_history_card", "choice_email_card", "choice_cancel_card"]:
                if hasattr(self, card_attr):
                    card = getattr(self, card_attr)
                    if card is not None:
                        card.update_theme_style(theme)
        else:
            if hasattr(self, "choice_header"):
                self.choice_header.setStyleSheet("""
                    QFrame#ChoiceHeader {
                        background-color: #F8FAFC;
                        border: 1px solid #E2E8F0;
                        border-radius: 12px;
                    }
                """)
                self.choice_info_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E293B;")
            for card_attr in ["choice_excel_card", "choice_ai_card", "choice_gst_card", "choice_tally_card", "choice_duplicate_card", "choice_history_card", "choice_email_card", "choice_cancel_card"]:
                if hasattr(self, card_attr):
                    card = getattr(self, card_attr)
                    if card is not None:
                        card.update_theme_style(theme)
    # Choice Page callbacks
    def choice_generate_excel(self):
        p = self.parent()
        dashboard = None
        while p:
            if hasattr(p, "page_stack") and hasattr(p, "generate_excel_widget"):
                dashboard = p
                break
            p = p.parent()

        if dashboard:
            # Switch dashboard page to generate_excel
            dashboard.switch_dashboard_page("generate_excel")
            
            # Feed metadata directly to GenerateExcelWidget to avoid double validation
            dashboard.generate_excel_widget.file_path = self.file_path
            dashboard.generate_excel_widget.page_count = self.page_count
            dashboard.generate_excel_widget.detected_bank = self.detected_bank
            dashboard.generate_excel_widget.doc_type_desc = self.doc_type_desc
            
            dashboard.generate_excel_widget.lbl_filename.setText(os.path.basename(self.file_path))
            dashboard.generate_excel_widget.lbl_bank.setText(self.detected_bank)
            dashboard.generate_excel_widget.lbl_pages.setText(f"{self.page_count} pages")
            dashboard.generate_excel_widget.lbl_doctype.setText(self.doc_type_desc)
            
            dashboard.generate_excel_widget.lbl_status.setText("Status: PDF imported from upload. Ready to generate Excel.")
            dashboard.generate_excel_widget.generate_btn.setEnabled(True)
            
            # Trigger parsing automatically!
            dashboard.generate_excel_widget.start_parsing_process()
            
            # Reset upload widget to initial state
            self.reset_to_upload()

    def choice_ai_report(self):
        self.post_process_action = "ai_report"
        self.start_processing_flow()

    def choice_history(self):
        p = self.parent()
        while p:
            if hasattr(p, "switch_dashboard_page"):
                p.switch_dashboard_page("history")
                break
            p = p.parent()


    def load_recent_uploads(self):
        from services.history_service import HistoryService
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        logs = HistoryService.get_history_logs(user_id=user_id)[:5]
        
        self.recent_table.setRowCount(0)
        self.recent_table.setRowCount(len(logs))
        
        for row_idx, log in enumerate(logs):
            bank = log.get("bank_name", "Unknown Bank")
            bank_item = QTableWidgetItem(bank)
            bank_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.recent_table.setItem(row_idx, 0, bank_item)
            
            pdf_path = log.get("pdf_path", "")
            file_name = os.path.basename(pdf_path) if pdf_path else "Unknown.pdf"
            file_item = QTableWidgetItem(file_name)
            file_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.recent_table.setItem(row_idx, 1, file_item)
            
            status = log.get("status", "Completed")
            tx_count = log.get("total_transactions", 0)
            tx_str = str(tx_count) if status == "Completed" else "-"
            tx_item = QTableWidgetItem(tx_str)
            tx_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.recent_table.setItem(row_idx, 2, tx_item)
            
            p_time = log.get("processing_time", 0.0)
            time_str = f"{p_time:.2f}s" if status == "Completed" else "-"
            time_item = QTableWidgetItem(time_str)
            time_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.recent_table.setItem(row_idx, 3, time_item)
            
            status_item = QTableWidgetItem(status)
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.recent_table.setItem(row_idx, 4, status_item)

# Refactored / updated upload_statement module and service integration
