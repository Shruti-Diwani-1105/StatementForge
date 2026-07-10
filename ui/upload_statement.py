import os
import sys
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QSpacerItem, QSizePolicy, QStackedWidget, QDialog, QProgressBar, QMessageBox, QGridLayout,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths
from PyQt6.QtGui import QPixmap, QCursor, QColor


from services.statement_service import StatementService
from utils.user_session import UserSession
from widgets.custom_card import CustomCard


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
    Main widget module for statement uploads.
    Manages validation, module selection, progress tracking, and success summaries.
    """
    processingCompleted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.page_count = 0
        self.detected_bank = "Unknown Bank"
        
        self.parsed_payload = None
        self.active_thread = None
        
        # Stacked layout
        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.init_upload_page()
        self.init_choose_action_page()
        self.init_processing_page()
        self.init_success_page()

    # ==========================================
    # PAGE 0: UPLOAD & DROP ZONE
    # ==========================================
    def init_upload_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        header_lbl = QLabel("Upload Bank Statement")
        header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        sub_lbl = QLabel("Upload digital or scanned bank statements to extract details offline using AI Analysis.")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 13px;")
        
        layout.addWidget(header_lbl)
        layout.addWidget(sub_lbl)

        # Dashed drop zone frame
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("DropZone")
        self.drop_zone.setAcceptDrops(True)
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
        self.drop_zone.dropEvent = self.zone_drop

        zone_layout = QVBoxLayout(self.drop_zone)
        zone_layout.setContentsMargins(40, 60, 40, 60)
        zone_layout.setSpacing(16)
        zone_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        upload_icon = QLabel()
        upload_pixmap = QPixmap("assets/icons/upload.png")
        if not upload_pixmap.isNull():
            upload_icon.setPixmap(upload_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        upload_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.addWidget(upload_icon)

        prompt_lbl = QLabel("Drag & Drop your statement PDF here")
        prompt_lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #0F172A;")
        prompt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.addWidget(prompt_lbl)

        help_lbl = QLabel("Supports PDF files (.pdf) only")
        help_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        help_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_layout.addWidget(help_lbl)

        browse_btn = QPushButton("Browse Files")
        browse_btn.setFixedSize(160, 38)
        browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        browse_btn.clicked.connect(self.browse_pdf_file)
        zone_layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.drop_zone)
        
        # Bottom Institutions list
        banks_layout = QVBoxLayout()
        banks_layout.setSpacing(12)
        banks_title = QLabel("Automatically Detects Indian Financial Institutions")
        banks_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #64748B; margin-top: 10px;")
        banks_layout.addWidget(banks_title)
        
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(10)
        
        banks_list = ["HDFC", "SBI", "ICICI", "Axis", "Kotak", "Canara", "BoB", "IndusInd"]
        for name in banks_list:
            pill = QLabel(name)
            pill.setStyleSheet("""
                QLabel {
                    background-color: #EFF6FF;
                    color: #2563EB;
                    font-weight: 600;
                    font-size: 12px;
                    padding: 6px 14px;
                    border-radius: 14px;
                    border: 1px solid #DBEAFE;
                }
            """)
            pills_layout.addWidget(pill)
        pills_layout.addStretch()
        banks_layout.addLayout(pills_layout)
        layout.addLayout(banks_layout)

        layout.addStretch()
        self.stack.addWidget(page)

    def zone_drag_enter(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().lower().endswith('.pdf'):
                event.acceptProposedAction()

    def zone_drop(self, event):
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

    def show_error_popup(self, err_msg):
        err_lower = err_msg.lower()
        if "password" in err_lower:
            title = "Password Protected PDF"
        elif "corrupt" in err_lower or "empty" in err_lower:
            title = "Corrupted PDF"
        elif "extension" in err_lower or "support" in err_lower:
            title = "Unsupported PDF"
        else:
            title = "File Verification Error"

        dialog = ErrorDialog(title, err_msg, self)
        dialog.exec()

    # ==========================================
    # STAGE 1: VALIDATE PDF & DETECT BANK
    # ==========================================
    def start_validation_flow(self, file_path):
        """Triggers quick background thread validation."""
        self.file_path = file_path

        # Construct temporary indicator QMessageBox
        self.progress_box = QMessageBox(self)
        self.progress_box.setWindowTitle("Verifying PDF")
        self.progress_box.setText("Validating statement structure and detecting bank...")
        self.progress_box.setStandardButtons(QMessageBox.StandardButton.NoButton)
        
        def on_started():
            self.progress_box.show()

        def on_finished(meta):
            self.progress_box.accept()
            self.file_path = meta["file_path"]
            self.page_count = meta["page_count"]
            self.detected_bank = meta["bank_name"]
            self.transition_to_choose_action()

        def on_error(err):
            self.progress_box.reject()
            self.show_error_popup(err)

        self.active_thread = StatementService.start_validate(
            file_path, on_started, on_finished, on_error
        )

    # ==========================================
    # PAGE 1: CHOOSE ACTION SCREEN
    # ==========================================
    def init_choose_action_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(24)

        header_lbl = QLabel("Choose Module Action")
        header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        sub_lbl = QLabel("Select which module you want to apply to the uploaded bank statement.")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 13px;")
        
        layout.addWidget(header_lbl)
        layout.addWidget(sub_lbl)

        # File metadata card
        self.meta_card = QFrame()
        self.meta_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        card_layout = QHBoxLayout(self.meta_card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(16)

        pdf_icon = QLabel()
        pdf_icon.setFixedSize(36, 36)
        pix = QPixmap("assets/icons/reports.png")
        if not pix.isNull():
            pdf_icon.setPixmap(pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        card_layout.addWidget(pdf_icon)

        self.file_info_lbl = QLabel("File details loading...")
        self.file_info_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E293B; border: none;")
        card_layout.addWidget(self.file_info_lbl)
        card_layout.addStretch()
        
        layout.addWidget(self.meta_card)

        # Grid of Modules
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(16)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        modules = [
            ("Generate Excel", "excel", "Export statement rows to clean stylized spreadsheets.", "#F0FDF4"),
            ("AI Report", "ai", "Generate intelligent insights and charts via LLM fallbacks.", "#F5F3FF"),
            ("GST Report", "gst", "Prepare transaction statements ready for tax filing.", "#FFFBEB"),
            ("Tally Export", "tally", "Export structured journal entries for Tally imports.", "#FFF7ED"),
            ("Duplicate Finder", "duplicate", "Locate double entry and duplicate transaction logs.", "#FEF2F2"),
            ("History Logs", "history", "Browse localized SQLite processing histories.", "#EFF6FF"),
            ("Email Report", "email", "Email parsed summary sheets securely.", "#ECFDF5")
        ]

        cols = 3
        for idx, (title, icon, desc, icon_bg) in enumerate(modules):
            row = idx // cols
            col = idx % cols
            card = CustomCard(title, desc, f"assets/icons/{icon}.png", icon_bg)
            
            if title == "Generate Excel":
                card.clicked.connect(self.start_processing_flow)
            else:
                card.clicked.connect(lambda checked, t=title: self.show_coming_soon_popup(t))
                
            grid_layout.addWidget(card, row, col)

        layout.addWidget(grid_container)

        # Back Navigation button
        nav_lay = QHBoxLayout()
        back_btn = QPushButton("Upload Different Statement")
        back_btn.setFixedSize(220, 36)
        back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2563EB;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
            }
        """)
        back_btn.clicked.connect(self.reset_to_upload)
        nav_lay.addWidget(back_btn)
        nav_lay.addStretch()
        layout.addLayout(nav_lay)

        layout.addStretch()
        self.stack.addWidget(page)

    def transition_to_choose_action(self):
        size_bytes = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
        size_kb = size_bytes / 1024
        
        info_str = f"Uploaded PDF: {os.path.basename(self.file_path)} ({self.page_count} pages, {size_kb:.1f} KB) | Detected Bank: {self.detected_bank}"
        self.file_info_lbl.setText(info_str)
        self.stack.setCurrentIndex(1)

    def show_coming_soon_popup(self, feature_name):
        """Displays a clean QMessageBox to denote coming soon modules."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Coming Soon")
        msg_box.setText(f"{feature_name} - Module Under Development")
        msg_box.setInformativeText("This module is visually configured. Its core processing layer will be enabled in a future release.")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setStyleSheet("""
            QMessageBox { background-color: #FFFFFF; }
            QPushButton { background-color: #2563EB; color: white; border-radius: 6px; padding: 6px 12px; }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        msg_box.exec()

    # ==========================================
    # PAGE 2: PROCESSING / LOADING SCREEN
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

        # Loading details card
        details_box = QFrame()
        details_box.setFixedWidth(500)
        details_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        grid = QGridLayout(details_box)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(12)

        l_bank = QLabel("Detected Bank:")
        l_bank.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748B;")
        self.proc_bank_lbl = QLabel("Unknown Bank")
        self.proc_bank_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #0F172A;")
        
        l_total = QLabel("Total Pages:")
        l_total.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748B;")
        self.proc_pages_lbl = QLabel("0 pages")
        self.proc_pages_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #0F172A;")

        l_cur = QLabel("Current Status:")
        l_cur.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748B;")
        self.proc_status_lbl = QLabel("Processing Page 1...")
        self.proc_status_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #2563EB;")

        l_txs = QLabel("Transactions Extracted:")
        l_txs.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748B;")
        self.proc_txs_lbl = QLabel("0 records")
        self.proc_txs_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #16A34A;")

        grid.addWidget(l_bank, 0, 0)
        grid.addWidget(self.proc_bank_lbl, 0, 1)
        grid.addWidget(l_total, 1, 0)
        grid.addWidget(self.proc_pages_lbl, 1, 1)
        grid.addWidget(l_cur, 2, 0)
        grid.addWidget(self.proc_status_lbl, 2, 1)
        grid.addWidget(l_txs, 3, 0)
        grid.addWidget(self.proc_txs_lbl, 3, 1)

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
        if self.active_thread and self.active_thread.isRunning():
            self.active_thread.terminate()
            self.active_thread.wait()
        self.stack.setCurrentIndex(1)

    # ==========================================
    # STAGE 2: EXECUTE PDF TABLE PARSING FLOW
    # ==========================================
    def start_processing_flow(self):
        """Launches the sequential processing steps 1-4."""
        self.proc_bank_lbl.setText(self.detected_bank)
        self.proc_pages_lbl.setText(f"{self.page_count} pages")
        self.proc_status_lbl.setText("Initializing parse engines...")
        self.proc_txs_lbl.setText("0 records")
        self.proc_bar.setValue(0)
        
        self.stack.setCurrentIndex(2)

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
            self.parsed_payload = payload
            if not payload or not payload.get("transactions"):
                self.stack.setCurrentIndex(1)
                logs = payload.get("logs") if payload else "No log output available."
                self.show_error_popup(
                    "No transactions could be extracted from this PDF statement.\n\n"
                    f"Detailed Engine Logs:\n{logs}"
                )
                return
            # Immediately generate Excel on parser completion
            self.generate_excel_flow()


        def on_error(err):
            self.stack.setCurrentIndex(1)
            self.show_error_popup(err)

        self.active_thread = StatementService.start_parse(
            self.file_path, on_started, on_step_started, on_step_completed, on_progress, on_finished, on_error
        )

    def generate_excel_flow(self):
        """Starts step 5-6 (Excel generation & History database logging)."""
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
            self.stack.setCurrentIndex(1)
            self.show_error_popup(err)

        self.active_thread = StatementService.start_generate_excel(
            user_id, self.parsed_payload, on_started, on_step_started, on_step_completed, on_finished, on_error
        )

    # ==========================================
    # PAGE 3: SUCCESS SCREEN
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

        # Details Grid
        details_box = QFrame()
        details_box.setFixedWidth(540)
        details_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        grid = QGridLayout(details_box)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(12)

        lbl_fn = QLabel("File Name:")
        lbl_fn.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        self.suc_file_lbl = QLabel("")
        self.suc_file_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")

        lbl_loc = QLabel("Excel Location:")
        lbl_loc.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        self.suc_loc_lbl = QLabel("")
        self.suc_loc_lbl.setWordWrap(True)
        self.suc_loc_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")

        lbl_bank = QLabel("Detected Bank:")
        lbl_bank.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        self.suc_bank_lbl = QLabel("")
        self.suc_bank_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")

        lbl_pages = QLabel("Total Pages:")
        lbl_pages.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        self.suc_pages_lbl = QLabel("")
        self.suc_pages_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")

        lbl_txs = QLabel("Transactions Extracted:")
        lbl_txs.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        self.suc_txs_lbl = QLabel("")
        self.suc_txs_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #16A34A;")

        lbl_time = QLabel("Processing Time:")
        lbl_time.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        self.suc_time_lbl = QLabel("")
        self.suc_time_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")

        grid.addWidget(lbl_fn, 0, 0)
        grid.addWidget(self.suc_file_lbl, 0, 1)
        grid.addWidget(lbl_loc, 1, 0)
        grid.addWidget(self.suc_loc_lbl, 1, 1)
        grid.addWidget(lbl_bank, 2, 0)
        grid.addWidget(self.suc_bank_lbl, 2, 1)
        grid.addWidget(lbl_pages, 3, 0)
        grid.addWidget(self.suc_pages_lbl, 3, 1)
        grid.addWidget(lbl_txs, 4, 0)
        grid.addWidget(self.suc_txs_lbl, 4, 1)
        grid.addWidget(lbl_time, 5, 0)
        grid.addWidget(self.suc_time_lbl, 5, 1)

        layout.addWidget(details_box)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        open_btn = QPushButton("Open Excel")
        open_btn.setFixedHeight(38)
        open_btn.setFixedWidth(130)
        open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        open_btn.clicked.connect(self.open_generated_excel)
        btn_box.addWidget(open_btn)

        folder_btn = QPushButton("Open Folder")
        folder_btn.setFixedHeight(38)
        folder_btn.setFixedWidth(120)
        folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #F8FAFC; color: #0F172A; }
        """)
        folder_btn.clicked.connect(self.open_output_folder)
        btn_box.addWidget(folder_btn)

        close_btn = QPushButton("Return to Dashboard")
        close_btn.setFixedHeight(38)
        close_btn.setFixedWidth(160)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }
        """)
        close_btn.clicked.connect(self.return_to_dashboard)
        btn_box.addWidget(close_btn)

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
        
        # Walk parent tree to switch dashboard page to default view
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
        self.stack.setCurrentIndex(0)
