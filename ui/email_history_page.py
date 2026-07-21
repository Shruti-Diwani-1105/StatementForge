import os
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSizePolicy
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
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_email_history()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 32)
        main_layout.setSpacing(16)

        # Header Title & New Email Action
        top_hdr_lay = QHBoxLayout()
        text_lay = QVBoxLayout()
        text_lay.setSpacing(4)
        
        header_lbl = QLabel("Email Center & Dispatches")
        header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A; font-family: 'Times New Roman';")
        sub_lbl = QLabel("Manage SMTP email settings, review transmission logs, draft reports to recipients, and retry failed dispatches.")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 13px; font-family: 'Times New Roman';")
        text_lay.addWidget(header_lbl)
        text_lay.addWidget(sub_lbl)
        top_hdr_lay.addLayout(text_lay, stretch=1)

        compose_btn = QPushButton("✉ + Compose Email")
        compose_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        compose_btn.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 9px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        compose_btn.clicked.connect(self.open_new_composer)
        top_hdr_lay.addWidget(compose_btn)

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

        # Stack Widget for History Tab (0) and Settings Tab (1)
        self.hub_stack = QWidget()
        stack_lay = QVBoxLayout(self.hub_stack)
        stack_lay.setContentsMargins(0, 0, 0, 0)
        stack_lay.setSpacing(16)

        # TAB 0: HISTORY VIEW
        self.history_widget = QWidget()
        hw_lay = QVBoxLayout(self.history_widget)
        hw_lay.setContentsMargins(0, 0, 0, 0)
        hw_lay.setSpacing(16)

        # Filter Control Bar Card
        filter_card = QFrame()
        filter_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;")
        filter_lay = QHBoxLayout(filter_card)
        filter_lay.setContentsMargins(16, 12, 16, 12)
        filter_lay.setSpacing(12)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by receiver ID email or subject...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                background-color: #F8FAFC;
                color: #0F172A;
            }
        """)
        self.search_input.textChanged.connect(self.load_email_history)
        filter_lay.addWidget(self.search_input, stretch=2)

        # Report Type Filter
        filter_lay.addWidget(QLabel("Report:"))
        self.report_filter_combo = QComboBox()
        self.report_filter_combo.addItems([
            "All", "Bank Statement Report", "GST Reconciliation & Analysis Report",
            "AI Financial Analysis Report", "Duplicate Transaction Report", "Excel Export Report"
        ])
        self.report_filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                background-color: #F8FAFC;
                color: #0F172A;
            }
        """)
        self.report_filter_combo.currentTextChanged.connect(self.load_email_history)
        filter_lay.addWidget(self.report_filter_combo)

        # Status Filter
        filter_lay.addWidget(QLabel("Status:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["All", "Sent", "Failed", "Draft"])
        self.status_filter_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                background-color: #F8FAFC;
                color: #0F172A;
            }
        """)
        self.status_filter_combo.currentTextChanged.connect(self.load_email_history)
        filter_lay.addWidget(self.status_filter_combo)

        # Refresh Button
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #DBEAFE; }
        """)
        refresh_btn.clicked.connect(self.load_email_history)
        filter_lay.addWidget(refresh_btn)

        hw_lay.addWidget(filter_card)

        # History Table Container
        table_container = QFrame()
        table_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table_container.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;")
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(12, 12, 12, 12)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date", "Receiver ID (Recipient)", "Report Type", "Subject", "Status", "Action"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)

        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 120)

        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setStyleSheet("border: none; gridline-color: #F1F5F9; font-family: 'Times New Roman';")
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        tc_layout.addWidget(self.table)
        hw_lay.addWidget(table_container)

        stack_lay.addWidget(self.history_widget)

        # TAB 1: EMAIL CONFIGURATION VIEW
        self.config_page = EmailSettingsPage(self)
        self.config_page.hide()
        stack_lay.addWidget(self.config_page)

        main_layout.addWidget(self.hub_stack)

    def switch_tab(self, index):
        """Switches between Email History (0) and Email Configuration (1)."""
        if index == 0:
            self.btn_tab_history.setChecked(True)
            self.btn_tab_config.setChecked(False)
            self.history_widget.show()
            self.config_page.hide()
            self.load_email_history()
        else:
            self.btn_tab_history.setChecked(False)
            self.btn_tab_config.setChecked(True)
            self.history_widget.hide()
            self.config_page.show()

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

        logs = EmailRepository.get_email_logs(
            user_id=user_id,
            recipient_filter=recipient_term,
            report_type_filter=report_term,
            status_filter=status_term
        )

        self.table.setRowCount(0)
        self.table.setRowCount(len(logs))

        for row_idx, log in enumerate(logs):
            # 1. Date
            sent_at = log.get("sent_at", "")
            if isinstance(sent_at, str) and "T" in sent_at:
                date_str = sent_at.replace("T", " ")[:16]
            else:
                date_str = str(sent_at)[:16]

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
            badge.setFixedSize(80, 22)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if status == "Sent":
                badge.setStyleSheet("""
                    background-color: #ECFDF5;
                    color: #10B981;
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 11px;
                    border: 1px solid #A7F3D0;
                """)
            elif status == "Draft":
                badge.setStyleSheet("""
                    background-color: #FEF3C7;
                    color: #B45309;
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 11px;
                    border: 1px solid #FDE68A;
                """)
            else:
                badge.setStyleSheet("""
                    background-color: #FEF2F2;
                    color: #EF4444;
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 11px;
                    border: 1px solid #FECACA;
                """)
            sc_layout.addWidget(badge)
            self.table.setCellWidget(row_idx, 4, status_container)

            # 6. Action Button
            action_container = QWidget()
            ac_layout = QHBoxLayout(action_container)
            ac_layout.setContentsMargins(4, 4, 4, 4)
            ac_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if status == "Draft":
                edit_btn = QPushButton("✏ Edit Draft")
                edit_btn.setFixedSize(85, 24)
                edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FEF3C7;
                        color: #B45309;
                        border: 1px solid #FDE68A;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover { background-color: #FDE68A; }
                """)
                edit_btn.clicked.connect(lambda checked, l=log: self.retry_email(l))
                ac_layout.addWidget(edit_btn)
            elif status == "Failed":
                retry_btn = QPushButton("Retry")
                retry_btn.setFixedSize(70, 24)
                retry_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                retry_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FEF2F2;
                        color: #EF4444;
                        border: 1px solid #FECACA;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QPushButton:hover { background-color: #FEE2E2; }
                """)
                retry_btn.clicked.connect(lambda checked, l=log: self.retry_email(l))
                ac_layout.addWidget(retry_btn)
            else:
                resend_btn = QPushButton("Resend")
                resend_btn.setFixedSize(70, 24)
                resend_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                resend_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #EFF6FF;
                        color: #2563EB;
                        border: 1px solid #BFDBFE;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 11px;
                    }
                    QPushButton:hover { background-color: #DBEAFE; }
                """)
                resend_btn.clicked.connect(lambda checked, l=log: self.retry_email(l))
                ac_layout.addWidget(resend_btn)

            self.table.setCellWidget(row_idx, 5, action_container)

    def retry_email(self, log_entry):
        """
        Reopens the Email Composer popup with historical recipient (receiver ID), subject, body,
        draft_id, and attachment paths pre-filled for user review before sending or updating draft.
        """
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

        # Pre-fill CC, BCC, Subject
        if log_entry.get("cc"):
            dialog.cc_input.setText(log_entry.get("cc"))
        if log_entry.get("bcc"):
            dialog.bcc_input.setText(log_entry.get("bcc"))
        if log_entry.get("subject"):
            dialog.subject_input.setText(log_entry.get("subject"))

        dialog.emailSentSuccess.connect(lambda meta: self.load_email_history())
        dialog.exec()
