import os
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSizePolicy, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont

from database.email_repository import EmailRepository
from ui.email_composer_dialog import EmailComposerDialog
from utils.user_session import UserSession
from ui.email_settings_page import EmailSettingsPage

class EmailHistoryPage(QWidget):
    """
    Unified Email Hub displaying logged sent/failed dispatches and drafts,
    search/filters, Draft management with receiver ID, and embedded Email Configuration settings.
    Uses QStackedWidget and modern typography to prevent layout squashing or font clipping.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "light"
        self.init_ui()
        self.load_email_history()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 32)
        main_layout.setSpacing(18)

        # Header Title & New Email Action
        top_hdr_lay = QHBoxLayout()
        text_lay = QVBoxLayout()
        text_lay.setSpacing(4)
        
        self.header_lbl = QLabel("Email Center & Dispatches")
        self.header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A; font-family: 'Manrope', sans-serif;")
        
        self.sub_lbl = QLabel("Manage SMTP email settings, review transmission logs, draft reports to recipients, and retry failed dispatches.")
        self.sub_lbl.setStyleSheet("color: #64748B; font-size: 13.5px; font-family: 'Inter', sans-serif;")
        
        text_lay.addWidget(self.header_lbl)
        text_lay.addWidget(self.sub_lbl)
        top_hdr_lay.addLayout(text_lay, stretch=1)

        self.compose_btn = QPushButton("✉ + Compose Email")
        self.compose_btn.setFixedHeight(38)
        self.compose_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.compose_btn.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.compose_btn.clicked.connect(self.open_new_composer)
        top_hdr_lay.addWidget(self.compose_btn)

        main_layout.addLayout(top_hdr_lay)

        # Segmented Navigation Bar (History vs Settings)
        self.nav_frame = QFrame()
        self.nav_frame.setStyleSheet("""
            QFrame {
                background-color: #F1F5F9;
                border-radius: 10px;
                border: 1px solid #E2E8F0;
            }
        """)
        nav_lay = QHBoxLayout(self.nav_frame)
        nav_lay.setContentsMargins(4, 4, 4, 4)
        nav_lay.setSpacing(6)

        self.btn_tab_history = QPushButton("📊 History & Dispatches")
        self.btn_tab_history.setCheckable(True)
        self.btn_tab_history.setChecked(True)
        self.btn_tab_history.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.btn_tab_config = QPushButton("⚙ Email Configuration")
        self.btn_tab_config.setCheckable(True)
        self.btn_tab_config.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        tab_style = """
            QPushButton {
                background-color: transparent;
                color: #64748B;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:checked {
                background-color: #FFFFFF;
                color: #0037b0;
                border: 1px solid #CBD5E1;
            }
            QPushButton:hover:!checked {
                background-color: #E2E8F0;
                color: #0F172A;
            }
        """
        self.btn_tab_history.setStyleSheet(tab_style)
        self.btn_tab_config.setStyleSheet(tab_style)

        self.btn_tab_history.clicked.connect(lambda: self.switch_tab(0))
        self.btn_tab_config.clicked.connect(lambda: self.switch_tab(1))

        nav_lay.addWidget(self.btn_tab_history)
        nav_lay.addWidget(self.btn_tab_config)
        nav_lay.addStretch()

        main_layout.addWidget(self.nav_frame)

        # Stack Widget for Tab Switching (Prevents Layout Overlap & Squashing)
        self.hub_stack = QStackedWidget(self)
        self.hub_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # TAB 0: HISTORY VIEW
        self.history_widget = QWidget()
        hw_lay = QVBoxLayout(self.history_widget)
        hw_lay.setContentsMargins(0, 0, 0, 0)
        hw_lay.setSpacing(16)

        # Filter Control Bar Card
        self.filter_card = QFrame()
        self.filter_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;")
        filter_lay = QHBoxLayout(self.filter_card)
        filter_lay.setContentsMargins(16, 12, 16, 12)
        filter_lay.setSpacing(12)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setFixedHeight(36)
        self.search_input.setPlaceholderText("🔍 Search by receiver email or subject...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                background-color: #F8FAFC;
                color: #0F172A;
                font-family: 'Inter', sans-serif;
            }
            QLineEdit:focus { border-color: #2563EB; }
        """)
        self.search_input.textChanged.connect(self.load_email_history)
        filter_lay.addWidget(self.search_input, stretch=2)

        # Report Type Filter
        lbl_r = QLabel("Report:")
        lbl_r.setStyleSheet("font-weight: 600; font-size: 12.5px; color: #475569; font-family: 'Inter', sans-serif;")
        filter_lay.addWidget(lbl_r)

        self.report_filter_combo = QComboBox()
        self.report_filter_combo.setFixedHeight(36)
        self.report_filter_combo.addItems([
            "All", "Bank Statement Report", "GST Reconciliation & Analysis Report",
            "AI Financial Analysis Report", "Duplicate Transaction Report", "Excel Export Report"
        ])
        self.report_filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12.5px;
                background-color: #F8FAFC;
                color: #0F172A;
                font-family: 'Inter', sans-serif;
            }
        """)
        self.report_filter_combo.currentTextChanged.connect(self.load_email_history)
        filter_lay.addWidget(self.report_filter_combo)

        # Status Filter
        lbl_s = QLabel("Status:")
        lbl_s.setStyleSheet("font-weight: 600; font-size: 12.5px; color: #475569; font-family: 'Inter', sans-serif;")
        filter_lay.addWidget(lbl_s)

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.setFixedHeight(36)
        self.status_filter_combo.addItems(["All", "Sent", "Failed", "Draft"])
        self.status_filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12.5px;
                background-color: #F8FAFC;
                color: #0F172A;
                font-family: 'Inter', sans-serif;
            }
        """)
        self.status_filter_combo.currentTextChanged.connect(self.load_email_history)
        filter_lay.addWidget(self.status_filter_combo)

        # Refresh Button
        self.refresh_btn = QPushButton("↻ Refresh")
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 600;
                font-size: 12.5px;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:hover { background-color: #DBEAFE; }
        """)
        self.refresh_btn.clicked.connect(self.load_email_history)
        filter_lay.addWidget(self.refresh_btn)

        hw_lay.addWidget(self.filter_card)

        # History Table Container
        self.table_container = QFrame()
        self.table_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_container.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;")
        tc_layout = QVBoxLayout(self.table_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date", "Receiver ID (Recipient)", "Report Type", "Subject", "Status", "Action"])

        header = self.table.horizontalHeader()
        header.setFixedHeight(42)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)

        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 180)
        self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(5, 160)

        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        self.apply_table_style()
        tc_layout.addWidget(self.table)
        hw_lay.addWidget(self.table_container)

        self.hub_stack.addWidget(self.history_widget)

        # TAB 1: EMAIL CONFIGURATION VIEW
        self.config_page = EmailSettingsPage(self)
        self.hub_stack.addWidget(self.config_page)

        main_layout.addWidget(self.hub_stack)

    def apply_table_style(self):
        if self.current_theme == "dark":
            self.table.setStyleSheet("""
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
                QTableWidget::item:hover { background-color: #334155; }
            """)
        else:
            self.table.setStyleSheet("""
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
                QTableWidget::item:hover { background-color: #F8FAFC; }
            """)

    def apply_theme(self, theme):
        self.current_theme = theme.lower().strip() if isinstance(theme, str) else "light"
        self.apply_table_style()
        if hasattr(self, "config_page") and self.config_page:
            self.config_page.apply_theme(self.current_theme)

    def switch_tab(self, index):
        """Switches between Email History (0) and Email Configuration (1)."""
        if index == 0:
            self.btn_tab_history.setChecked(True)
            self.btn_tab_config.setChecked(False)
            self.hub_stack.setCurrentIndex(0)
            self.load_email_history()
        else:
            self.btn_tab_history.setChecked(False)
            self.btn_tab_config.setChecked(True)
            self.hub_stack.setCurrentIndex(1)

    def open_new_composer(self):
        """Opens a blank Email Composer dialog."""
        dialog = EmailComposerDialog(parent=self)
        dialog.emailSentSuccess.connect(lambda meta: self.load_email_history())
        dialog.exec()

    def load_email_history(self):
        """Fetches and displays email history logs based on active filters."""
        user = UserSession.get_current_user()
        user_id = user["id"] if user else None

        recipient_term = self.search_input.text().strip()
        report_term = self.report_filter_combo.currentText()
        status_term = self.status_filter_combo.currentText()

        try:
            logs = EmailRepository.get_email_logs(
                user_id=user_id,
                recipient_filter=recipient_term,
                report_type_filter=report_term,
                status_filter=status_term
            )
        except Exception as e:
            print(f"EmailHistoryPage error: {e}")
            logs = []

        self.table.setRowCount(0)
        self.table.setRowCount(len(logs))

        for row_idx, log in enumerate(logs):
            # 1. Date
            sent_at = log.get("sent_at", "")
            if isinstance(sent_at, str) and "T" in sent_at:
                try:
                    dt = datetime.datetime.fromisoformat(sent_at)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = sent_at.replace("T", " ")[:16]
            elif hasattr(sent_at, "strftime"):
                date_str = sent_at.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = str(sent_at)[:16] if sent_at else "N/A"

            item_date = QTableWidgetItem(date_str)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 0, item_date)

            # 2. Recipient
            recip = log.get("recipient_email", "")
            item_recip = QTableWidgetItem(recip)
            item_recip.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, item_recip)

            # 3. Report Type
            rtype = log.get("report_type", "Report")
            item_rtype = QTableWidgetItem(rtype)
            item_rtype.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 2, item_rtype)

            # 4. Subject
            subj = log.get("subject", "")
            item_subj = QTableWidgetItem(subj)
            item_subj.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 3, item_subj)

            # 5. Status Badge
            status = log.get("status", "Sent")
            status_container = QWidget()
            sc_layout = QHBoxLayout(status_container)
            sc_layout.setContentsMargins(4, 4, 4, 4)
            sc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            badge = QLabel(status)
            badge.setFixedSize(85, 24)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if status == "Sent":
                badge.setStyleSheet("""
                    background-color: #ECFDF5;
                    color: #059669;
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 12px;
                    border: 1px solid #A7F3D0;
                    font-family: 'Inter', sans-serif;
                """)
            elif status == "Draft":
                badge.setStyleSheet("""
                    background-color: #FFFBEB;
                    color: #D97706;
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 12px;
                    border: 1px solid #FDE68A;
                    font-family: 'Inter', sans-serif;
                """)
            else:
                badge.setStyleSheet("""
                    background-color: #FEF2F2;
                    color: #DC2626;
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 12px;
                    border: 1px solid #FECACA;
                    font-family: 'Inter', sans-serif;
                """)
            sc_layout.addWidget(badge)
            self.table.setCellWidget(row_idx, 4, status_container)

            # 6. Action Buttons
            action_container = QWidget()
            ac_layout = QHBoxLayout(action_container)
            ac_layout.setContentsMargins(4, 4, 4, 4)
            ac_layout.setSpacing(6)
            ac_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if status == "Draft":
                edit_btn = QPushButton("✏ Edit")
                edit_btn.setFixedSize(64, 24)
                edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFBEB;
                        color: #D97706;
                        border: 1px solid #FDE68A;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                        font-family: 'Inter', sans-serif;
                    }
                    QPushButton:hover { background-color: #FDE68A; }
                """)
                edit_btn.clicked.connect(lambda checked, l=log: self.retry_email(l))
                ac_layout.addWidget(edit_btn)
            elif status == "Failed":
                retry_btn = QPushButton("Retry")
                retry_btn.setFixedSize(60, 24)
                retry_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                retry_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FEF2F2;
                        color: #DC2626;
                        border: 1px solid #FECACA;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                        font-family: 'Inter', sans-serif;
                    }
                    QPushButton:hover { background-color: #FEE2E2; }
                """)
                retry_btn.clicked.connect(lambda checked, l=log: self.retry_email(l))
                ac_layout.addWidget(retry_btn)
            else:
                resend_btn = QPushButton("Resend")
                resend_btn.setFixedSize(62, 24)
                resend_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                resend_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #EFF6FF;
                        color: #2563EB;
                        border: 1px solid #BFDBFE;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                        font-family: 'Inter', sans-serif;
                    }
                    QPushButton:hover { background-color: #DBEAFE; }
                """)
                resend_btn.clicked.connect(lambda checked, l=log: self.retry_email(l))
                ac_layout.addWidget(resend_btn)

            # Delete Log Button
            del_btn = QPushButton("Delete")
            del_btn.setFixedSize(58, 24)
            del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEF2F2;
                    color: #DC2626;
                    border: 1px solid #FECDD3;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 11px;
                    font-family: 'Inter', sans-serif;
                }
                QPushButton:hover { background-color: #FEE2E2; }
            """)
            log_id = log.get("id")
            del_btn.clicked.connect(lambda checked, lid=log_id: self.delete_email_log(lid))
            ac_layout.addWidget(del_btn)

            self.table.setCellWidget(row_idx, 5, action_container)

    def delete_email_log(self, log_id):
        if not log_id:
            return
        confirm = QMessageBox.question(
            self,
            "Delete Email Log",
            "Are you sure you want to delete this email dispatch log?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                EmailRepository.delete_email_log(log_id)
                self.load_email_history()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete email log: {e}")

    def retry_email(self, log_entry):
        att_paths_raw = log_entry.get("attachment_paths", "")
        att_paths = [p.strip() for p in att_paths_raw.split(";") if p.strip() and os.path.exists(p.strip())]
        default_att = att_paths if att_paths else None

        dialog = EmailComposerDialog(
            report_type=log_entry.get("report_type", "Financial Report"),
            default_attachment=default_att,
            recipient=log_entry.get("recipient_email", ""),
            message=log_entry.get("body", ""),
            draft_id=log_entry.get("id"),
            parent=self
        )

        if log_entry.get("cc"):
            dialog.cc_input.setText(log_entry.get("cc"))
        if log_entry.get("bcc"):
            dialog.bcc_input.setText(log_entry.get("bcc"))
        if log_entry.get("subject"):
            dialog.subject_input.setText(log_entry.get("subject"))

        dialog.emailSentSuccess.connect(lambda meta: self.load_email_history())
        dialog.exec()
