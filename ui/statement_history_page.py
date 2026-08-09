import os
import sys
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QColor

from services.history_service import HistoryService
from utils.user_session import UserSession

class StatementHistoryPage(QWidget):
    """
    Dedicated Statement History widget providing a clean, enterprise-grade,
    dynamic table view for past parsed bank statements. Supports search filtering,
    no font clipping, responsive column widths, and light/dark theme adaptability.
    """
    recordDeleted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_logs = []
        self.current_theme = "light"
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 32)
        main_layout.setSpacing(20)

        # 1. Header & Actions Bar
        header_bar = QHBoxLayout()
        header_bar.setSpacing(16)

        # Header Titles
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        self.header_lbl = QLabel("Statement History")
        self.header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A; font-family: 'Manrope', sans-serif;")
        
        self.sub_lbl = QLabel("Review previously uploaded and parsed financial statements.")
        self.sub_lbl.setStyleSheet("font-size: 13.5px; color: #64748B; font-family: 'Inter', sans-serif;")

        title_box.addWidget(self.header_lbl)
        title_box.addWidget(self.sub_lbl)
        header_bar.addLayout(title_box, stretch=1)

        # Actions (Search, Refresh, Clear All)
        actions_box = QHBoxLayout()
        actions_box.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by filename or bank...")
        self.search_input.setFixedWidth(260)
        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                font-family: 'Inter', sans-serif;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
        """)
        self.search_input.textChanged.connect(self.filter_table)
        actions_box.addWidget(self.search_input)

        self.refresh_btn = QPushButton("↻ Refresh")
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12.5px;
                font-weight: 600;
                font-family: 'Inter', sans-serif;
                color: #334155;
            }
            QPushButton:hover {
                background-color: #EFF6FF;
                border-color: #93C5FD;
                color: #2563EB;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_history_data)
        actions_box.addWidget(self.refresh_btn)

        self.clear_btn = QPushButton("🗑 Clear History")
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEF2F2;
                border: 1px solid #FECDD3;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12.5px;
                font-weight: 600;
                font-family: 'Inter', sans-serif;
                color: #DC2626;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
                border-color: #FCA5A5;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_all_history)
        actions_box.addWidget(self.clear_btn)

        header_bar.addLayout(actions_box)
        main_layout.addLayout(header_bar)

        # 2. Main Table Container Frame
        self.table_container = QFrame()
        self.table_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_container.setObjectName("HistoryTableContainer")
        self.table_container.setStyleSheet("""
            QFrame#HistoryTableContainer {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
        """)
        tc_layout = QVBoxLayout(self.table_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(0)

        # Table Widget
        self.history_table = QTableWidget()
        self.history_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Upload Date", "File Name", "Bank Name", "Status", "Output Format", "Action"
        ])
        
        # Configure Header Modes & Widths to Prevent Text Cutoffs
        header = self.history_table.horizontalHeader()
        header.setFixedHeight(42)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Upload Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)     # File Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)     # Bank Name
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # Status
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive) # Output Format
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive) # Action

        self.history_table.setColumnWidth(0, 170) # Upload Date
        self.history_table.setColumnWidth(1, 230) # File Name
        self.history_table.setColumnWidth(2, 180) # Bank Name
        self.history_table.setColumnWidth(3, 130) # Status
        self.history_table.setColumnWidth(4, 160) # Output Format (Ensures "Output Format" never clips)
        self.history_table.setColumnWidth(5, 170) # Action

        # Align Headers Explicitly
        alignments = [
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        ]
        for col_idx, alignment in enumerate(alignments):
            item = self.history_table.horizontalHeaderItem(col_idx)
            if item:
                item.setTextAlignment(alignment)

        self.history_table.verticalHeader().setDefaultSectionSize(48)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.history_table.setShowGrid(True)

        self.apply_table_style()
        tc_layout.addWidget(self.history_table)

        # 3. Empty State Label Overlay
        self.empty_state_lbl = QLabel("No statement history logs found.\nUpload a bank statement to get started.", self.table_container)
        self.empty_state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_lbl.setStyleSheet("font-size: 14px; font-weight: 500; color: #64748B; font-family: 'Inter', sans-serif; line-height: 22px;")
        self.empty_state_lbl.hide()

        main_layout.addWidget(self.table_container)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'empty_state_lbl') and self.empty_state_lbl:
            self.empty_state_lbl.setGeometry(self.table_container.rect())

    def apply_table_style(self):
        if self.current_theme == "dark":
            self.header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #F8FAFC; font-family: 'Manrope', sans-serif;")
            self.sub_lbl.setStyleSheet("font-size: 13.5px; color: #94A3B8; font-family: 'Inter', sans-serif;")
            self.table_container.setStyleSheet("""
                QFrame#HistoryTableContainer {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 14px;
                }
            """)
            self.search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 0 12px;
                    font-size: 13px;
                    font-family: 'Inter', sans-serif;
                    color: #F8FAFC;
                }
                QLineEdit:focus {
                    border-color: #3B82F6;
                }
            """)
            self.refresh_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 0 14px;
                    font-size: 12.5px;
                    font-weight: 600;
                    font-family: 'Inter', sans-serif;
                    color: #94A3B8;
                }
                QPushButton:hover {
                    background-color: #1E293B;
                    border-color: #3B82F6;
                    color: #3B82F6;
                }
            """)
            self.history_table.setStyleSheet("""
                QTableWidget {
                    background-color: #1E293B;
                    border: none;
                    gridline-color: #334155;
                    font-family: 'Inter', sans-serif;
                    font-size: 13px;
                    color: #F8FAFC;
                }
                QHeaderView::section {
                    background-color: #0F172A;
                    color: #94A3B8;
                    font-family: 'Inter', sans-serif;
                    font-size: 11.5px;
                    font-weight: 700;
                    text-transform: uppercase;
                    padding: 10px 14px;
                    border: none;
                    border-bottom: 1px solid #334155;
                    border-right: 1px solid #1E293B;
                }
                QTableWidget::item {
                    padding: 8px 12px;
                    border-bottom: 1px solid #334155;
                }
                QTableWidget::item:hover {
                    background-color: #334155;
                }
            """)
        else:
            self.header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A; font-family: 'Manrope', sans-serif;")
            self.sub_lbl.setStyleSheet("font-size: 13.5px; color: #64748B; font-family: 'Inter', sans-serif;")
            self.table_container.setStyleSheet("""
                QFrame#HistoryTableContainer {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 14px;
                }
            """)
            self.search_input.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 0 12px;
                    font-size: 13px;
                    font-family: 'Inter', sans-serif;
                    color: #0F172A;
                }
                QLineEdit:focus {
                    border-color: #2563EB;
                }
            """)
            self.refresh_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 0 14px;
                    font-size: 12.5px;
                    font-weight: 600;
                    font-family: 'Inter', sans-serif;
                    color: #334155;
                }
                QPushButton:hover {
                    background-color: #EFF6FF;
                    border-color: #93C5FD;
                    color: #2563EB;
                }
            """)
            self.history_table.setStyleSheet("""
                QTableWidget {
                    background-color: #FFFFFF;
                    border: none;
                    gridline-color: #F1F5F9;
                    font-family: 'Inter', sans-serif;
                    font-size: 13px;
                    color: #0F172A;
                }
                QHeaderView::section {
                    background-color: #F8FAFC;
                    color: #475569;
                    font-family: 'Inter', sans-serif;
                    font-size: 11.5px;
                    font-weight: 700;
                    text-transform: uppercase;
                    padding: 10px 14px;
                    border: none;
                    border-bottom: 1px solid #E2E8F0;
                    border-right: 1px solid #F1F5F9;
                }
                QTableWidget::item {
                    padding: 8px 12px;
                    border-bottom: 1px solid #F1F5F9;
                }
                QTableWidget::item:hover {
                    background-color: #F8FAFC;
                }
            """)

    def load_history_data(self):
        """Fetches history records asynchronously and populates the table."""
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        
        try:
            logs = HistoryService.get_history_logs(user_id=user_id)
            self.all_logs = logs if isinstance(logs, list) else []
        except Exception as e:
            print(f"StatementHistoryPage: Failed to load logs: {e}")
            self.all_logs = []

        self.filter_table()

    def filter_table(self):
        """Populates rows matching current search filter text."""
        query = self.search_input.text().strip().lower()
        if query:
            filtered = []
            for log in self.all_logs:
                pdf_path = log.get("pdf_path", "")
                fname = os.path.basename(pdf_path).lower()
                bname = str(log.get("bank_name", "")).lower()
                status = str(log.get("status", "")).lower()
                fmt = str(log.get("output_format", "")).lower()
                if query in fname or query in bname or query in status or query in fmt:
                    filtered.append(log)
        else:
            filtered = self.all_logs

        self.populate_table(filtered)

    def populate_table(self, logs):
        self.history_table.setRowCount(0)
        
        if not logs:
            self.empty_state_lbl.setGeometry(self.table_container.rect())
            self.empty_state_lbl.show()
            return
        else:
            self.empty_state_lbl.hide()

        self.history_table.setRowCount(len(logs))

        for row_idx, log in enumerate(logs):
            # 1. Upload Date
            upload_date = log.get("upload_date", "")
            if isinstance(upload_date, str) and "T" in upload_date:
                try:
                    dt = datetime.datetime.fromisoformat(upload_date)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = upload_date.replace("T", " ")[:16]
            elif hasattr(upload_date, "strftime"):
                date_str = upload_date.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = str(upload_date)[:16] if upload_date else "N/A"

            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.history_table.setItem(row_idx, 0, date_item)

            # 2. File Name
            pdf_path = log.get("pdf_path", "")
            file_name = os.path.basename(pdf_path) if pdf_path else "Statement.pdf"
            file_item = QTableWidgetItem(file_name)
            file_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            file_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.history_table.setItem(row_idx, 1, file_item)

            # 3. Bank Name
            bank_name = log.get("bank_name", "Unknown Bank")
            bank_item = QTableWidgetItem(bank_name)
            bank_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            bank_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.history_table.setItem(row_idx, 2, bank_item)

            # 4. Status Badge
            status = log.get("status", "Completed")
            status_styles = {
                "Completed": ("#ECFDF5", "#059669", "#A7F3D0"),
                "Processing": ("#EFF6FF", "#2563EB", "#BFDBFE"),
                "Failed": ("#FEF2F2", "#DC2626", "#FECACA"),
                "Cancelled": ("#F1F5F9", "#64748B", "#E2E8F0")
            }
            bg_c, txt_c, brd_c = status_styles.get(status, ("#F1F5F9", "#64748B", "#E2E8F0"))

            status_container = QWidget()
            sc_layout = QHBoxLayout(status_container)
            sc_layout.setContentsMargins(4, 4, 4, 4)
            sc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            status_badge = QLabel(status)
            status_badge.setFixedSize(100, 24)
            status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg_c};
                    color: {txt_c};
                    border: 1px solid {brd_c};
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 12px;
                    font-family: 'Inter', sans-serif;
                }}
            """)
            sc_layout.addWidget(status_badge)
            self.history_table.setCellWidget(row_idx, 3, status_container)

            # 5. Output Format
            out_fmt = log.get("output_format", "Excel") if status == "Completed" else "-"
            fmt_item = QTableWidgetItem(out_fmt)
            fmt_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            fmt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.history_table.setItem(row_idx, 4, fmt_item)

            # 6. Actions (View & Delete)
            action_container = QWidget()
            ac_layout = QHBoxLayout(action_container)
            ac_layout.setContentsMargins(4, 4, 4, 4)
            ac_layout.setSpacing(8)
            ac_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Delete Button
            delete_btn = QPushButton("Delete")
            delete_btn.setFixedSize(62, 24)
            delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEF2F2;
                    color: #DC2626;
                    border: 1px solid #FECDD3;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 11px;
                    font-family: 'Inter', sans-serif;
                }
                QPushButton:hover {
                    background-color: #FEE2E2;
                    border-color: #FCA5A5;
                }
            """)
            rec_id = log.get("_id")
            delete_btn.clicked.connect(lambda checked, rid=rec_id: self.delete_history_record(rid))

            if status == "Completed":
                view_btn = QPushButton("View")
                view_btn.setFixedSize(62, 24)
                view_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                view_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #EFF6FF;
                        color: #2563EB;
                        border: 1px solid #BFDBFE;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                        font-family: 'Inter', sans-serif;
                    }
                    QPushButton:hover {
                        background-color: #DBEAFE;
                    }
                """)
                excel_path = log.get("excel_path", "")
                view_btn.clicked.connect(lambda checked, ep=excel_path: self.open_history_file(ep))
                ac_layout.addWidget(view_btn)

            ac_layout.addWidget(delete_btn)
            self.history_table.setCellWidget(row_idx, 5, action_container)

    def open_history_file(self, filepath):
        if not filepath or not os.path.exists(filepath):
            QMessageBox.warning(self, "File Not Found", f"The generated file could not be found at:\n{filepath}")
            return
            
        try:
            if os.name == 'nt':
                os.startfile(filepath)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(["open", filepath])
            else:
                import subprocess
                subprocess.run(["xdg-open", filepath])
        except Exception as e:
            QMessageBox.critical(self, "Error Opening File", f"An error occurred while opening the file:\n{e}")

    def delete_history_record(self, record_id):
        if not record_id:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this statement history log?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                success = HistoryService.delete_record(record_id)
                if success:
                    self.load_history_data()
                    self.recordDeleted.emit()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete history record.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete record: {e}")

    def clear_all_history(self):
        user = UserSession.get_current_user()
        user_id = user["id"] if user else None
        if not user_id:
            return

        if not self.all_logs:
            QMessageBox.information(self, "History Empty", "There are no history records to clear.")
            return

        confirm = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all statement history records?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                success = HistoryService.clear_all_recent_activity(user_id=user_id)
                if success:
                    self.load_history_data()
                    self.recordDeleted.emit()
                    QMessageBox.information(self, "Success", "Statement history cleared successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to clear statement history.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not clear history: {e}")

    def apply_theme(self, theme):
        """Applies light/dark theme to the history page elements."""
        self.current_theme = theme.lower().strip() if isinstance(theme, str) else "light"
        self.apply_table_style()

