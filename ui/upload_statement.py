import os
import sys
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QSpacerItem, QSizePolicy, QStackedWidget, QDialog, QProgressBar, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths
from PyQt6.QtGui import QPixmap, QCursor

from services.statement_service import StatementService
from utils.user_session import UserSession


class LoadingProgressDialog(QDialog):
    """Centered progress dialog displaying a vertical checklist of steps (1-6)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing Statement")
        self.setFixedSize(400, 360)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; border-radius: 12px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        self.title_label = QLabel("Parsing financial statement...")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.steps = [
            "Step 1: Uploading PDF",
            "Step 2: Reading PDF",
            "Step 3: OCR (if required)",
            "Step 4: AI Analysis",
            "Step 5: Generating Excel",
            "Step 6: Saving File"
        ]

        self.step_labels = []
        self.step_icons = []

        for step in self.steps:
            row = QHBoxLayout()
            row.setSpacing(10)
            
            icon = QLabel("○")
            icon.setStyleSheet("font-size: 15px; color: #94A3B8;")
            icon.setFixedWidth(20)
            row.addWidget(icon)
            
            label = QLabel(step)
            label.setStyleSheet("font-size: 13px; color: #94A3B8; font-weight: 500;")
            row.addWidget(label)
            row.addStretch()
            
            layout.addLayout(row)
            self.step_icons.append(icon)
            self.step_labels.append(label)

        layout.addSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Initializing...")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedSize(90, 28)
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0F172A;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.cancel_btn)
        btn_container.addStretch()
        layout.addLayout(btn_container)

    def set_step_status(self, step_idx, status):
        """
        Updates step status indicators.
        step_idx is 1-indexed (1 to 6)
        status can be: "pending", "running", "success", "skipped", "failed"
        """
        i = step_idx - 1
        if i < 0 or i >= len(self.step_labels):
            return

        if status == "running":
            self.step_icons[i].setText("⚡")
            self.step_icons[i].setStyleSheet("font-size: 15px; color: #2563EB; font-weight: bold;")
            self.step_labels[i].setStyleSheet("font-size: 13px; color: #0F172A; font-weight: 600;")
            self.status_lbl.setText(f"Running: {self.steps[i]}...")
            self.progress_bar.setValue(int((step_idx - 0.5) / 6.0 * 100))
        elif status == "success":
            self.step_icons[i].setText("✓")
            self.step_icons[i].setStyleSheet("font-size: 15px; color: #10B981; font-weight: bold;")
            self.step_labels[i].setStyleSheet("font-size: 13px; color: #10B981; font-weight: 500;")
            self.progress_bar.setValue(int(step_idx / 6.0 * 100))
        elif status == "skipped":
            self.step_icons[i].setText("✓")
            self.step_icons[i].setStyleSheet("font-size: 15px; color: #94A3B8; font-weight: bold;")
            self.step_labels[i].setStyleSheet("font-size: 13px; color: #94A3B8; font-style: italic;")
            self.progress_bar.setValue(int(step_idx / 6.0 * 100))
        elif status == "failed":
            self.step_icons[i].setText("✗")
            self.step_icons[i].setStyleSheet("font-size: 15px; color: #EF4444; font-weight: bold;")
            self.step_labels[i].setStyleSheet("font-size: 13px; color: #EF4444; font-weight: 600;")
            self.status_lbl.setText(f"Failed at: {self.steps[i]}")


class ErrorDialog(QDialog):
    """Beautiful, custom styled error dialog for specific exception messages."""
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
        
        # Red warning icon
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


class SuccessDialog(QDialog):
    """Beautiful dialog displaying file extraction statistics and action buttons."""
    def __init__(self, file_name, file_location, processing_time, bank_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Excel Generated Successfully")
        self.setFixedSize(500, 380)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; border-radius: 12px; }")

        self.excel_path = file_location
        self.folder_path = os.path.dirname(file_location)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        icon = QLabel("✓")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(54, 54)
        icon.setStyleSheet("""
            background-color: #ECFDF5;
            color: #10B981;
            font-size: 28px;
            font-weight: bold;
            border-radius: 27px;
            border: 1px solid #A7F3D0;
        """)
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Excel Generated Successfully")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #059669;")
        layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        grid_lay = QGridLayout(card)
        grid_lay.setContentsMargins(16, 16, 16, 16)
        grid_lay.setSpacing(10)

        labels = [
            ("File Name:", file_name),
            ("Excel Location:", file_location.replace("\\", "/")),
            ("Processing Time:", f"{processing_time:.2f} seconds"),
            ("Detected Bank:", bank_name)
        ]

        for row, (lbl, val) in enumerate(labels):
            l = QLabel(lbl)
            l.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
            v = QLabel(val)
            v.setWordWrap(True)
            v.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")
            
            grid_lay.addWidget(l, row, 0)
            grid_lay.addWidget(v, row, 1)

        layout.addWidget(card)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.open_excel_btn = QPushButton("Open Excel")
        self.open_excel_btn.setFixedHeight(38)
        self.open_excel_btn.setFixedWidth(130)
        self.open_excel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_excel_btn.setStyleSheet("""
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
        self.open_excel_btn.clicked.connect(self.open_excel)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setFixedHeight(38)
        self.open_folder_btn.setFixedWidth(120)
        self.open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_folder_btn.setStyleSheet("""
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
        self.open_folder_btn.clicked.connect(self.open_folder)

        self.close_btn = QPushButton("Close")
        self.close_btn.setFixedHeight(38)
        self.close_btn.setFixedWidth(90)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setStyleSheet("""
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
        self.close_btn.clicked.connect(self.accept)

        btn_box.addWidget(self.open_excel_btn)
        btn_box.addWidget(self.open_folder_btn)
        btn_box.addWidget(self.close_btn)
        layout.addLayout(btn_box)

    def open_excel(self):
        try:
            if os.path.exists(self.excel_path):
                if os.name == 'nt':
                    os.startfile(self.excel_path)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.run(["open", self.excel_path])
                else:
                    import subprocess
                    subprocess.run(["xdg-open", self.excel_path])
        except Exception as e:
            print(f"Error opening Excel: {e}")

    def open_folder(self):
        try:
            if os.path.exists(self.folder_path):
                if os.name == 'nt':
                    os.startfile(self.folder_path)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.run(["open", self.folder_path])
                else:
                    import subprocess
                    subprocess.run(["xdg-open", self.folder_path])
        except Exception as e:
            print(f"Error opening folder: {e}")


class UploadStatementWidget(QWidget):
    """
    Main widget module for statement uploads, parsing, table preview, and Excel generation.
    """
    processingCompleted = pyqtSignal() # Emitted to notify dashboard to update stats

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.parsed_data = None
        self.active_thread = None
        
        # Pagination variables
        self.current_page = 0
        self.page_size = 20
        self.filtered_transactions = []
        self.sort_column = -1
        self.sort_ascending = True

        # Stacked layout
        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.init_upload_page()
        self.init_preview_page()

    # ==========================================
    # PAGE 1: UPLOAD & DROP ZONE
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
        # Install drag drop event filters
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
            self.process_selected_file(path)

    def browse_pdf_file(self):
        doc_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Bank Statement PDF", doc_dir, "PDF Files (*.pdf)"
        )
        if path:
            self.process_selected_file(path)

    def process_selected_file(self, path):
        self.file_path = path
        self.loading_dialog = LoadingProgressDialog(self)
        self.loading_dialog.title_label.setText("Extracting & Analyzing PDF Statement")

        # Step tracking signals
        def on_started():
            # Initial states
            for i in range(1, 7):
                self.loading_dialog.set_step_status(i, "pending")
            self.loading_dialog.show()

        def on_step_started(step_idx):
            self.loading_dialog.set_step_status(step_idx, "running")

        def on_step_completed(step_idx, status):
            self.loading_dialog.set_step_status(step_idx, status)

        def on_finished(payload):
            self.loading_dialog.accept()
            self.parsed_data = payload
            self.show_preview_card()

        def on_error(err_msg):
            self.loading_dialog.reject()
            self.show_error_popup(err_msg)

        # Start background QThread
        self.active_thread = StatementService.start_parse(
            path, on_started, on_step_started, on_step_completed, on_finished, on_error
        )

    def show_error_popup(self, err_msg):
        # Dynamically determine the error type for title mapping
        err_lower = err_msg.lower()
        if "password" in err_lower:
            title = "Password Protected PDF"
        elif "corrupt" in err_lower or "empty" in err_lower:
            title = "Corrupted PDF"
        elif "extension" in err_lower or "support" in err_lower:
            title = "Unsupported PDF"
        elif "gemini" in err_lower and "key" in err_lower:
            title = "Gemini API Error"
        elif "quota" in err_lower or "billing" in err_lower:
            title = "Gemini API Error"
        elif "connection" in err_lower or "internet" in err_lower or "network" in err_lower:
            title = "Internet Error"
        elif "tesseract" in err_lower or "ocr failure" in err_lower:
            title = "OCR Failure"
        elif "json" in err_lower or "xml" in err_lower:
            title = "JSON Parsing Error"
        elif "save" in err_lower or "write" in err_lower or "permission" in err_lower:
            title = "Excel Save Error"
        elif "mongo" in err_lower or "pymongo" in err_lower:
            title = "MongoDB Error"
        else:
            title = "Processing Failure"

        dialog = ErrorDialog(title, err_msg, self)
        dialog.exec()

    # ==========================================
    # PAGE 2: METADATA & PREVIEW TABLE
    # ==========================================
    def init_preview_page(self):
        self.preview_page = QWidget()
        layout = QVBoxLayout(self.preview_page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Upper Card Preview Info
        self.preview_card = QFrame()
        self.preview_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        card_layout = QHBoxLayout(self.preview_card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(20)

        # PDF icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(48, 48)
        pix = QPixmap("assets/icons/reports.png")
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        card_layout.addWidget(icon_lbl)

        # Details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        
        self.file_name_lbl = QLabel("Filename.pdf")
        self.file_name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #0F172A; border: none;")
        self.meta_lbl = QLabel("Pages: 0  |  Size: 0 KB")
        self.meta_lbl.setStyleSheet("font-size: 12px; color: #64748B; border: none;")
        
        details_layout.addWidget(self.file_name_lbl)
        details_layout.addWidget(self.meta_lbl)
        card_layout.addLayout(details_layout)
        card_layout.addStretch()

        # Detection results
        detect_layout = QVBoxLayout()
        detect_layout.setSpacing(4)
        self.bank_lbl = QLabel("Bank: Unknown")
        self.bank_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #2563EB; border: none;")
        self.type_lbl = QLabel("Type: Digital PDF")
        self.type_lbl.setStyleSheet("font-size: 12px; color: #64748B; border: none;")
        
        detect_layout.addWidget(self.bank_lbl)
        detect_layout.addWidget(self.type_lbl)
        card_layout.addLayout(detect_layout)
        
        layout.addWidget(self.preview_card)

        # Table Section (Search + Table + Pagination)
        table_section = QWidget()
        ts_layout = QVBoxLayout(table_section)
        ts_layout.setContentsMargins(0, 0, 0, 0)
        ts_layout.setSpacing(10)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search transactions (Date, Narration)...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)
        ts_layout.addLayout(search_layout)

        # QTableWidget (5 columns: Date, Narration, Debit, Credit, Balance)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Narration", "Debit", "Credit", "Balance"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("border: 1px solid #E2E8F0; background-color: #FFFFFF; gridline-color: #F1F5F9;")
        
        # Connect header clicked for custom paginated sorting
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        ts_layout.addWidget(self.table)

        # Pagination controls
        pag_layout = QHBoxLayout()
        pag_layout.setSpacing(12)
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.setFixedSize(80, 28)
        self.prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #F1F5F9; }
            QPushButton:disabled { background-color: #F8FAFC; color: #CBD5E1; }
        """)
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_lbl = QLabel("Page 1 of 1")
        self.page_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        
        self.next_btn = QPushButton("Next")
        self.next_btn.setFixedSize(80, 28)
        self.next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #F1F5F9; }
            QPushButton:disabled { background-color: #F8FAFC; color: #CBD5E1; }
        """)
        self.next_btn.clicked.connect(self.next_page)

        pag_layout.addWidget(self.prev_btn)
        pag_layout.addStretch()
        pag_layout.addWidget(self.page_lbl)
        pag_layout.addStretch()
        pag_layout.addWidget(self.next_btn)
        ts_layout.addLayout(pag_layout)

        layout.addWidget(table_section)

        # Bottom Buttons Layout (Modular layout)
        btn_wrapper = QVBoxLayout()
        btn_wrapper.setSpacing(10)

        # Primary actions & Coming soon buttons
        row1_lay = QHBoxLayout()
        row1_lay.setSpacing(12)

        self.generate_btn = QPushButton("Generate Excel")
        self.generate_btn.setFixedHeight(40)
        self.generate_btn.setFixedWidth(150)
        self.generate_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1D4ED8);
                color: white;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #1E40AF);
            }
        """)
        self.generate_btn.clicked.connect(self.generate_excel_sheet)
        row1_lay.addWidget(self.generate_btn)

        coming_soon_buttons = [
            "AI Report", "GST Report", "Tally Export", 
            "Duplicate Finder", "History Logs", "Email Report"
        ]
        
        self.cs_btn_widgets = []
        for name in coming_soon_buttons:
            btn = QPushButton(name)
            btn.setFixedHeight(40)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            # Styled visually to convey 'Coming Soon' and disabled style
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F8FAFC;
                    color: #94A3B8;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #F1F5F9;
                    color: #475569;
                }
            """)
            btn.clicked.connect(lambda checked, n=name: self.show_coming_soon_popup(n))
            row1_lay.addWidget(btn)
            self.cs_btn_widgets.append(btn)

        btn_wrapper.addLayout(row1_lay)

        # Standard navigation buttons (Cancel/Upload another)
        row2_lay = QHBoxLayout()
        row2_lay.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(34)
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
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
        self.cancel_btn.clicked.connect(self.reset_to_upload)
        row2_lay.addWidget(self.cancel_btn)

        btn_wrapper.addLayout(row2_lay)
        layout.addLayout(btn_wrapper)

        self.stack.addWidget(self.preview_page)

    def show_coming_soon_popup(self, feature_name):
        """Displays a beautiful QMessageBox to denote coming soon modules."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Coming Soon")
        msg_box.setText(f"{feature_name} - Coming Soon")
        msg_box.setInformativeText("This feature is currently under development and will be available in the next release.")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setStyleSheet("""
            QMessageBox { background-color: #FFFFFF; }
            QPushButton { background-color: #2563EB; color: white; border-radius: 6px; padding: 6px 12px; }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        msg_box.exec()

    def show_preview_card(self):
        # 1. Update Preview Card labels
        payload = self.parsed_data
        self.file_name_lbl.setText(payload["file_name"])
        
        # File Size formatting
        size_bytes = 0
        if os.path.exists(payload["file_path"]):
            size_bytes = os.path.getsize(payload["file_path"])
        size_kb = size_bytes / 1024
        self.meta_lbl.setText(f"Pages: {payload['page_count']}  |  Size: {size_kb:.1f} KB")
        
        self.bank_lbl.setText(f"Bank: {payload['bank_name']}")
        type_str = "Scanned PDF (OCR)" if payload["is_scanned"] else "Digital PDF"
        
        if payload.get("ocr_simulated"):
            type_str += " [Simulated]"
            self.type_lbl.setText(f"Type: {type_str}\n(Tesseract OCR not found)")
            self.type_lbl.setStyleSheet("font-size: 11px; color: #EF4444; border: none; font-weight: 600;")
        else:
            self.type_lbl.setText(f"Type: {type_str}")
            self.type_lbl.setStyleSheet("font-size: 12px; color: #64748B; border: none;")

        # 2. Reset table filters and sorting
        self.search_input.clear()
        self.filtered_transactions = list(payload["transactions"])
        self.current_page = 0
        self.sort_column = -1
        self.sort_ascending = True

        self.update_table_view()
        self.stack.setCurrentIndex(1)

    def update_table_view(self):
        # Clear previous items
        self.table.setRowCount(0)
        
        total_items = len(self.filtered_transactions)
        self.total_pages = (total_items - 1) // self.page_size + 1 if total_items > 0 else 1
        
        # Edge case check
        if self.current_page >= self.total_pages:
            self.current_page = max(0, self.total_pages - 1)

        # Slice data
        start = self.current_page * self.page_size
        end = min(start + self.page_size, total_items)
        page_items = self.filtered_transactions[start:end]

        self.table.setRowCount(len(page_items))

        for row_idx, tx in enumerate(page_items):
            # Date
            date_item = QTableWidgetItem(tx["date"])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 0, date_item)

            # Narration
            narr_item = QTableWidgetItem(tx["narration"])
            narr_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 1, narr_item)

            # Debit
            deb = tx.get("debit", 0.0)
            deb_val = f"₹ {deb:,.2f}" if deb > 0 else "-"
            deb_item = QTableWidgetItem(deb_val)
            deb_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            deb_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 2, deb_item)

            # Credit
            cred = tx.get("credit", 0.0)
            cred_val = f"₹ {cred:,.2f}" if cred > 0 else "-"
            cred_item = QTableWidgetItem(cred_val)
            cred_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cred_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 3, cred_item)

            # Balance
            bal_val = tx.get("balance")
            if bal_val is not None:
                bal_str = f"₹ {bal_val:,.2f}"
            else:
                bal_str = "-"
            bal_item = QTableWidgetItem(bal_str)
            bal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bal_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 4, bal_item)

        # Update labels and pagination buttons
        self.page_lbl.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < self.total_pages - 1)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table_view()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_table_view()

    def on_search_changed(self, text):
        query = text.strip().lower()
        if not query:
            self.filtered_transactions = list(self.parsed_data["transactions"])
        else:
            self.filtered_transactions = [
                tx for tx in self.parsed_data["transactions"]
                if query in tx["date"].lower() or query in tx["narration"].lower()
            ]
        self.current_page = 0
        self.update_table_view()

    def on_header_clicked(self, logical_index):
        # Toggle sort order
        if self.sort_column == logical_index:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = logical_index
            self.sort_ascending = True

        # Sort filtered transactions list in memory
        def get_sort_key(tx):
            if logical_index == 0: # Date
                return tx["date"]
            elif logical_index == 1: # Narration
                return tx["narration"].lower()
            elif logical_index == 2: # Debit
                return tx.get("debit", 0.0)
            elif logical_index == 3: # Credit
                return tx.get("credit", 0.0)
            elif logical_index == 4: # Balance
                val = tx.get("balance")
                return val if val is not None else -9999999.0
            return 0

        self.filtered_transactions.sort(key=get_sort_key, reverse=not self.sort_ascending)
        self.current_page = 0
        self.update_table_view()

    def generate_excel_sheet(self):
        """Launches background thread for Excel workbook formatting and storage."""
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"

        self.loading_dialog = LoadingProgressDialog(self)
        self.loading_dialog.title_label.setText("Formatting & Saving Excel Sheet")

        # Step tracking callbacks
        def on_started():
            # Steps 1-4 are pre-checked as complete
            for i in range(1, 5):
                self.loading_dialog.set_step_status(i, "success")
            # Steps 5-6 are pending
            self.loading_dialog.set_step_status(5, "pending")
            self.loading_dialog.set_step_status(6, "pending")
            self.loading_dialog.show()

        def on_step_started(step_idx):
            self.loading_dialog.set_step_status(step_idx, "running")

        def on_step_completed(step_idx, status):
            self.loading_dialog.set_step_status(step_idx, status)

        def on_finished(excel_path):
            self.loading_dialog.accept()
            
            # Show the beautiful custom success dialog
            success = SuccessDialog(
                file_name=os.path.basename(excel_path),
                file_location=excel_path,
                processing_time=self.parsed_data["processing_time"],
                bank_name=self.parsed_data["bank_name"],
                parent=self
            )
            success.exec()
            
            # Reset view back to upload screen and emit finished
            self.reset_to_upload()
            self.processingCompleted.emit()

        def on_error(err_msg):
            self.loading_dialog.reject()
            self.show_error_popup(err_msg)

        # Spawns generating & saving QThread worker
        self.active_thread = StatementService.start_generate_excel(
            user_id, self.parsed_data, on_started, on_step_started, on_step_completed, on_finished, on_error
        )

    def reset_to_upload(self):
        self.file_path = None
        self.parsed_data = None
        self.search_input.clear()
        self.stack.setCurrentIndex(0)
