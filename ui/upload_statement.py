import os
import sys
import datetime
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QSpacerItem, QSizePolicy, QStackedWidget, QDialog, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QStandardPaths
from PyQt6.QtGui import QPixmap, QIcon, QCursor

from utils.statement_service import StatementService
from utils.excel_generator import ExcelGenerator
from utils.history_service import HistoryService
from utils.user_session import UserSession

class LoadingProgressDialog(QDialog):
    """Centered progress dialog displayed during background thread parsing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing Statement")
        self.setFixedSize(380, 160)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; border-radius: 12px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.label = QLabel("Extracting financial data...")
        self.label.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
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
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

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


class UploadStatementWidget(QWidget):
    """
    Main widget module for statement uploads, parsing, table preview, and Excel generation.
    """
    processingCompleted = pyqtSignal() # Emitted to notify dashboard to update stats

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.parsed_data = None
        
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
        self.init_success_page()

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
        sub_lbl = QLabel("Upload digital or scanned bank statements to extract details offline.")
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
        zone_layout.addWidget(browse_btn)

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
        # Launch QThread worker
        self.loading_dialog = LoadingProgressDialog(self)
        
        # Signals callbacks
        def on_started():
            self.loading_dialog.label.setText("Reading PDF layout...")
            self.loading_dialog.progress_bar.setValue(0)
            self.loading_dialog.show()

        def on_progress(current, total):
            pct = int((current / total) * 100)
            self.loading_dialog.label.setText(f"Extracting transactions: Page {current} of {total}...")
            self.loading_dialog.progress_bar.setValue(pct)

        def on_finished(payload):
            self.loading_dialog.accept()
            self.parsed_data = payload
            self.show_preview_card()

        def on_error(err_msg):
            self.loading_dialog.reject()
            self.show_error_dialog("Parsing Failure", err_msg)

        # Start thread
        self.active_thread = StatementService.start_parse(
            path, on_started, on_progress, on_finished, on_error
        )

    def show_error_dialog(self, title, message):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setStyleSheet("""
            QMessageBox { background-color: #FFFFFF; }
            QPushButton { background-color: #2563EB; color: white; border-radius: 6px; padding: 6px 12px; }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        msg.exec()

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

        # QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Row", "Date", "Narration", "Debit (Withdrawals)", "Credit (Deposits)", "Balance"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
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

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.generate_btn = QPushButton("Generate Excel")
        self.generate_btn.setFixedHeight(42)
        self.generate_btn.setFixedWidth(160)
        self.generate_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
                color: white;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.generate_btn.clicked.connect(self.generate_excel_sheet)

        self.upload_another_btn = QPushButton("Upload Another")
        self.upload_another_btn.setFixedHeight(42)
        self.upload_another_btn.setFixedWidth(140)
        self.upload_another_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.upload_another_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                color: #0F172A;
            }
        """)
        self.upload_another_btn.clicked.connect(self.reset_to_upload)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(42)
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
            }
        """)
        self.cancel_btn.clicked.connect(self.reset_to_upload)

        btn_row.addWidget(self.generate_btn)
        btn_row.addWidget(self.upload_another_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

        self.stack.addWidget(self.preview_page)

    def show_preview_card(self):
        # 1. Update Preview Card labels
        payload = self.parsed_data
        self.file_name_lbl.setText(payload["file_name"])
        
        # File Size formatting
        size_bytes = os.path.path.getsize(payload["file_path"]) if os.path.exists(payload["file_path"]) else 0
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
            # Row index number
            num_item = QTableWidgetItem(str(start + row_idx + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 0, num_item)

            # Date
            date_item = QTableWidgetItem(tx["date"])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 1, date_item)

            # Narration
            narr_item = QTableWidgetItem(tx["narration"])
            narr_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 2, narr_item)

            # Debit
            deb_val = f"₹ {tx['debit']:,.2f}" if tx['debit'] > 0 else "-"
            deb_item = QTableWidgetItem(deb_val)
            deb_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            deb_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 3, deb_item)

            # Credit
            cred_val = f"₹ {tx['credit']:,.2f}" if tx['credit'] > 0 else "-"
            cred_item = QTableWidgetItem(cred_val)
            cred_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cred_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 4, cred_item)

            # Balance
            bal_val = f"₹ {tx['balance']:,.2f}"
            bal_item = QTableWidgetItem(bal_val)
            bal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bal_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row_idx, 5, bal_item)

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
        if logical_index == 0:
            # Row index clicked, don't sort
            return
            
        # Toggle sort order
        if self.sort_column == logical_index:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = logical_index
            self.sort_ascending = True

        # Sort filtered transactions list in memory
        def get_sort_key(tx):
            if logical_index == 1: # Date
                return tx["date"]
            elif logical_index == 2: # Narration
                return tx["narration"].lower()
            elif logical_index == 3: # Debit
                return tx["debit"]
            elif logical_index == 4: # Credit
                return tx["credit"]
            elif logical_index == 5: # Balance
                return tx["balance"]
            return 0

        self.filtered_transactions.sort(key=get_sort_key, reverse=not self.sort_ascending)
        self.current_page = 0
        self.update_table_view()

    def generate_excel_sheet(self):
        try:
            payload = self.parsed_data
            
            # Run excel generator
            excel_path = ExcelGenerator.generate_excel(
                payload["file_path"],
                payload["bank_name"],
                payload["account_holder"],
                payload["period"],
                payload["transactions"]
            )
            
            # Save parsing run into MongoDB
            user = UserSession.get_current_user()
            user_id = user["id"] if user else "guest"
            
            HistoryService.save_record(
                user_id=user_id,
                file_name=payload["file_name"],
                pdf_path=payload["file_path"],
                excel_path=excel_path,
                bank_name=payload["bank_name"],
                period=payload["period"],
                total_transactions=len(payload["transactions"]),
                processing_time=payload["processing_time"],
                ocr_used=payload["ocr_used"]
            )
            
            # Show success page
            self.show_success_page(excel_path)
            
            # Notify dashboard to refresh statistics counter in real time
            self.processingCompleted.emit()

        except Exception as e:
            self.show_error_dialog("Excel Generation Error", f"Could not create Excel spreadsheet:\n{e}")

    def reset_to_upload(self):
        self.file_path = None
        self.parsed_data = None
        self.search_input.clear()
        self.stack.setCurrentIndex(0)

    # ==========================================
    # PAGE 3: EXPORT SUCCESS
    # ==========================================
    def init_success_page(self):
        self.success_page = QWidget()
        layout = QVBoxLayout(self.success_page)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        success_icon = QLabel("✓")
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_icon.setFixedSize(64, 64)
        success_icon.setStyleSheet("""
            background-color: #ECFDF5;
            color: #10B981;
            font-size: 32px;
            font-weight: bold;
            border-radius: 32px;
            border: 1px solid #A7F3D0;
        """)
        layout.addWidget(success_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        success_title = QLabel("Excel Generated Successfully")
        success_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #059669;")
        layout.addWidget(success_title)

        self.success_desc = QLabel("Your bank statement transactions have been saved.")
        self.success_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.success_desc.setStyleSheet("font-size: 13px; color: #64748B; font-weight: 500;")
        layout.addWidget(self.success_desc)

        # Info card for Path
        path_card = QFrame()
        path_card.setFixedWidth(550)
        path_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        path_lay = QVBoxLayout(path_card)
        path_lay.setContentsMargins(14, 12, 14, 12)
        
        path_title = QLabel("Destination Path:")
        path_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        self.path_val = QLabel("C:/")
        self.path_val.setWordWrap(True)
        self.path_val.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")
        
        path_lay.addWidget(path_title)
        path_lay.addWidget(self.path_val)
        layout.addWidget(path_card, alignment=Qt.AlignmentFlag.AlignCenter)

        # OS Action buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.open_excel_btn = QPushButton("Open Excel Sheet")
        self.open_excel_btn.setFixedHeight(40)
        self.open_excel_btn.setFixedWidth(160)
        self.open_excel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        self.open_excel_btn.clicked.connect(self.open_excel_file)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setFixedHeight(40)
        self.open_folder_btn.setFixedWidth(140)
        self.open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #F8FAFC; color: #0F172A; }
        """)
        self.open_folder_btn.clicked.connect(self.open_excel_folder)

        self.close_success_btn = QPushButton("Close")
        self.close_success_btn.setFixedHeight(40)
        self.close_success_btn.setFixedWidth(100)
        self.close_success_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_success_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }
        """)
        self.close_success_btn.clicked.connect(self.reset_to_upload)

        btn_box.addWidget(self.open_excel_btn)
        btn_box.addWidget(self.open_folder_btn)
        btn_box.addWidget(self.close_success_btn)
        layout.addLayout(btn_box)

        self.stack.addWidget(self.success_page)

    def show_success_page(self, path):
        self.generated_excel_path = path
        # Normalize display path slashes
        clean_path = path.replace("\\", "/")
        self.path_val.setText(clean_path)
        self.stack.setCurrentIndex(2)

    def open_excel_file(self):
        try:
            if os.path.exists(self.generated_excel_path):
                # Cross-platform open
                if os.name == 'nt':
                    os.startfile(self.generated_excel_path)
                elif sys.platform == 'darwin':
                    subprocess.run(["open", self.generated_excel_path])
                else:
                    subprocess.run(["xdg-open", self.generated_excel_path])
        except Exception as e:
            self.show_error_dialog("File Open Error", f"Could not launch spreadsheet application:\n{e}")

    def open_excel_folder(self):
        try:
            folder = os.path.dirname(self.generated_excel_path)
            if os.path.exists(folder):
                if os.name == 'nt':
                    os.startfile(folder)
                elif sys.platform == 'darwin':
                    subprocess.run(["open", folder])
                else:
                    subprocess.run(["xdg-open", folder])
        except Exception as e:
            self.show_error_dialog("Folder Open Error", f"Could not open containing directory:\n{e}")
