import os
import datetime
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QTextBrowser, QLineEdit, QScrollArea, QProgressBar,
    QFileDialog, QListWidget, QListWidgetItem, QSizePolicy, QSpacerItem, QMessageBox,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize, QTimer
from PyQt6.QtGui import QCursor, QTextDocument, QColor
from PyQt6.QtPrintSupport import QPrinter

from services.gemini_service import GeminiService
from services.history_service import HistoryService
from utils.user_session import UserSession
from settings.toast import Toast

class AIWorker(QThread):
    """
    Background worker thread to execute Gemini analysis methods without blocking the UI.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, action, transactions, currency="INR", **kwargs):
        super().__init__()
        self.action = action
        self.transactions = transactions
        self.currency = currency
        self.kwargs = kwargs

    def run(self):
        try:
            if not self.transactions:
                raise ValueError("No transaction data loaded. Please upload or select a bank statement first.")

            if self.action == "summary":
                bank_name = self.kwargs.get("bank_name", "Unknown Bank")
                period = self.kwargs.get("period", "Unknown Period")
                result = GeminiService.generate_financial_summary(
                    self.transactions, bank_name, period, self.currency
                )
            elif self.action == "spending":
                bank_name = self.kwargs.get("bank_name", "Unknown Bank")
                period = self.kwargs.get("period", "Unknown Period")
                result = GeminiService.analyze_monthly_spending(
                    self.transactions, self.currency, bank_name=bank_name, period=period
                )
            elif self.action == "risk":
                bank_name = self.kwargs.get("bank_name", "Unknown Bank")
                period = self.kwargs.get("period", "Unknown Period")
                result = GeminiService.analyze_risks(
                    self.transactions, self.currency, bank_name=bank_name, period=period
                )
            elif self.action == "report":
                bank_name = self.kwargs.get("bank_name", "Unknown Bank")
                holder = self.kwargs.get("holder", "Unknown")
                acc_num = self.kwargs.get("acc_num", "Unknown")
                period = self.kwargs.get("period", "Unknown Period")
                result = GeminiService.generate_executive_report(
                    self.transactions, bank_name, holder, acc_num, period, self.currency
                )
            elif self.action == "chat":
                chat_history = self.kwargs.get("chat_history", [])
                message = self.kwargs.get("message", "")
                result = GeminiService.chat_with_statement(
                    self.transactions, chat_history, message, self.currency
                )
            else:
                raise ValueError(f"Unknown AI action: {self.action}")

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AIAuditorWidget(QWidget):
    """
    Main UI section for the AI Financial Auditor & Business Advisor.
    Integrates metrics dashboard, report actions, scrollable report viewer,
    and a side chat window.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "light"
        
        # State Data
        self.active_transactions = []
        self.active_metadata = {
            "bank_name": "Unknown Bank",
            "account_holder": "Unknown",
            "period": "Unknown Period",
            "currency": "INR",
            "total_credit": 0.0,
            "total_debit": 0.0,
            "net_savings": 0.0
        }
        self.chat_history = []
        self.active_thread = None

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # ==========================================
        # LEFT AREA: AUDIT CONTROLS & REPORT VIEW
        # ==========================================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        # 1. Header
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        self.title_lbl = QLabel("AI Financial Auditor & Business Advisor")
        self.title_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        
        self.subtitle_lbl = QLabel("Big-4 Style Forensic Audit & Executive Recommendations powered by AI.")
        self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
        
        header_lay.addWidget(self.title_lbl)
        header_lay.addWidget(self.subtitle_lbl)
        left_layout.addLayout(header_lay)

        # 2. Selection & Preview Card
        self.preview_card = QFrame()
        self.preview_card.setObjectName("PreviewCard")
        self.preview_card.setStyleSheet("""
            QFrame#PreviewCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        
        card_layout = QVBoxLayout(self.preview_card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # Selection Row
        sel_row = QHBoxLayout()
        sel_row.setSpacing(12)
        
        sel_lbl = QLabel("Statement:")
        sel_lbl.setStyleSheet("font-weight: 600; color: #475569;")
        sel_row.addWidget(sel_lbl)

        self.statement_cb = QComboBox()
        self.statement_cb.setMinimumWidth(320)
        self.statement_cb.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
            }
        """)
        self.statement_cb.currentIndexChanged.connect(self.on_statement_selected)
        sel_row.addWidget(self.statement_cb)

        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_history_dropdown)
        sel_row.addWidget(self.refresh_btn)
        sel_row.addStretch()
        card_layout.addLayout(sel_row)

        # Info Stats Layout
        self.stats_box = QWidget()
        stats_layout = QHBoxLayout(self.stats_box)
        stats_layout.setContentsMargins(0, 8, 0, 0)
        stats_layout.setSpacing(16)

        def make_metric(title, value_attr):
            box = QFrame()
            box.setObjectName(value_attr + "_box")
            l = QVBoxLayout(box)
            l.setContentsMargins(12, 10, 12, 10)
            l.setSpacing(4)
            lbl = QLabel(title)
            lbl.setStyleSheet("font-size: 11px; color: #64748B; text-transform: uppercase; font-weight: 700; font-family: 'Times New Roman';")
            lbl.setWordWrap(True)
            val = QLabel("-")
            val.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A; font-family: 'Times New Roman';")
            val.setWordWrap(True)
            setattr(self, value_attr, val)
            l.addWidget(lbl)
            l.addWidget(val)
            return box

        stats_layout.addWidget(make_metric("Bank Name", "lbl_bank"))
        stats_layout.addWidget(make_metric("Statement Period", "lbl_period"))
        stats_layout.addWidget(make_metric("Total Credits", "lbl_credits"))
        stats_layout.addWidget(make_metric("Total Debits", "lbl_debits"))
        stats_layout.addWidget(make_metric("Net Savings", "lbl_savings"))
        
        # Health Score card
        score_box = QFrame()
        score_box.setFixedWidth(110)
        score_box.setObjectName("ScoreBoxWidget")
        score_box.setStyleSheet("""
            QFrame#ScoreBoxWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1D4ED8, stop:1 #7C3AED);
                border: none;
                border-radius: 12px;
            }
        """)
        l_score = QVBoxLayout(score_box)
        l_score.setContentsMargins(10, 10, 10, 10)
        l_score.setSpacing(6)
        l_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        score_lbl = QLabel("Audit Score")
        score_lbl.setStyleSheet("font-size: 9px; color: rgba(255, 255, 255, 0.85); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; font-family: 'Times New Roman';")
        score_lbl.setWordWrap(True)
        
        self.lbl_score = QLabel("-")
        self.lbl_score.setFixedSize(48, 48)
        self.lbl_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_score.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                border-radius: 24px;
                font-size: 18px;
                font-weight: 800;
                border: 2px dashed rgba(255, 255, 255, 0.5);
                font-family: 'Times New Roman';
            }
        """)
        l_score.addWidget(score_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        l_score.addWidget(self.lbl_score, alignment=Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(score_box)


        card_layout.addWidget(self.stats_box)
        left_layout.addWidget(self.preview_card)

        # 3. Action Buttons Section styled as a Premium Segmented Tab Bar
        self.action_tab_bar = QFrame()
        self.action_tab_bar.setObjectName("AuditorTabBar")
        
        btn_bar = QHBoxLayout(self.action_tab_bar)
        btn_bar.setContentsMargins(4, 4, 4, 4)
        btn_bar.setSpacing(4)

        def make_action_btn(text, action_key):
            btn = QPushButton(text)
            btn.setObjectName("AuditorTabButton")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda: self.run_ai_task(action_key))
            btn_bar.addWidget(btn)
            return btn

        from PyQt6.QtWidgets import QButtonGroup
        self.action_btn_group = QButtonGroup(self)
        self.action_btn_group.setExclusive(True)
        
        self.btn_summary = make_action_btn("Financial Summary", "summary")
        self.btn_spending = make_action_btn("Spending Insights", "spending")
        self.btn_risk = make_action_btn("Risk Analysis", "risk")
        self.btn_report = make_action_btn("Generate AI Report", "report")
        
        self.action_btn_group.addButton(self.btn_summary)
        self.action_btn_group.addButton(self.btn_spending)
        self.action_btn_group.addButton(self.btn_risk)
        self.action_btn_group.addButton(self.btn_report)
        
        left_layout.addWidget(self.action_tab_bar)

        # Progress / Loading Indicator (overlay style container)
        self.loading_box = QFrame()
        self.loading_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        l_load = QHBoxLayout(self.loading_box)
        l_load.setContentsMargins(12, 8, 12, 8)
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 0) # Infinite scrolling
        self.pbar.setTextVisible(False)
        self.pbar.setFixedHeight(6)
        self.loading_lbl = QLabel("AI is analyzing transaction data...")
        self.loading_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        l_load.addWidget(self.loading_lbl)
        l_load.addWidget(self.pbar, stretch=1)
        
        self.loading_box.setVisible(False)
        left_layout.addWidget(self.loading_box)

        # 4. Report Viewer Card
        viewer_card = QFrame()
        viewer_card.setObjectName("ViewerCard")
        viewer_card.setStyleSheet("""
            QFrame#ViewerCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        v_layout = QVBoxLayout(viewer_card)
        v_layout.setContentsMargins(16, 16, 16, 16)
        v_layout.setSpacing(12)

        viewer_title_bar = QHBoxLayout()
        v_title = QLabel("Audit Report Viewer")
        v_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E293B;")
        viewer_title_bar.addWidget(v_title)
        viewer_title_bar.addStretch()

        self.btn_send_ai_email = QPushButton("✉ Send via Email")
        self.btn_send_ai_email.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_send_ai_email.setStyleSheet("""
            QPushButton {
                background-color: #F5F3FF;
                color: #7C3AED;
                border: 1px solid #DDD6FE;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #EDE9FE; }
        """)
        self.btn_send_ai_email.clicked.connect(self.open_email_composer)
        viewer_title_bar.addWidget(self.btn_send_ai_email)

        v_layout.addLayout(viewer_title_bar)

        self.report_viewer = QTextBrowser()
        self.report_viewer.setOpenExternalLinks(True)
        self.report_viewer.setHtml("<div style='color:#64748B; font-family: \"Times New Roman\", Times, serif; font-size:14px; text-align:center; padding-top:40px;'>Select a statement above and click an analysis button to generate a report.</div>")
        self.report_viewer.setStyleSheet("border: none; background-color: transparent;")
        v_layout.addWidget(self.report_viewer)

        left_layout.addWidget(viewer_card, stretch=1)
        main_layout.addWidget(left_widget, stretch=3)

        # ==========================================
        # RIGHT AREA: INTERACTIVE ADVISOR CHAT
        # ==========================================
        chat_card = QFrame()
        chat_card.setObjectName("ChatCard")
        chat_card.setFixedWidth(340)
        chat_card.setStyleSheet("""
            QFrame#ChatCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(16, 16, 16, 16)
        chat_layout.setSpacing(12)

        chat_header = QLabel("Ask AI Financial Advisor")
        chat_header.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E293B;")
        chat_layout.addWidget(chat_header)

        # Scroll Area for Chat Bubbles
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.chat_widget = QWidget()
        self.chat_widget.setObjectName("ChatWidget")
        self.chat_widget.setStyleSheet("background: transparent;")
        
        self.chat_container_layout = QVBoxLayout(self.chat_widget)
        self.chat_container_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_container_layout.setSpacing(12)
        self.chat_container_layout.addStretch() # Push messages to bottom
        
        self.chat_scroll.setWidget(self.chat_widget)
        chat_layout.addWidget(self.chat_scroll, stretch=1)

        # Suggestions panel
        self.suggestions_box = QWidget()
        suggestions_layout = QHBoxLayout(self.suggestions_box)
        suggestions_layout.setContentsMargins(0, 0, 0, 4)
        suggestions_layout.setSpacing(6)
        
        suggestions = ["Top Expenses", "Duplicate UPIs", "Active Subscriptions"]
        for s in suggestions:
            s_btn = QPushButton(s)
            s_btn.setObjectName("ChatSuggestionButton")
            s_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            s_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    color: #475569;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    color: #0F172A;
                }
            """)
            s_btn.clicked.connect(lambda checked, text=s: self.on_suggestion_clicked(text))
            suggestions_layout.addWidget(s_btn)
        chat_layout.addWidget(self.suggestions_box)

        # Chat inputs
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask a question about this statement...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 14px;
                border: 1px solid #CBD5E1;
                border-radius: 20px;
                background-color: #F8FAFC;
                color: #0F172A;
                font-size: 12px;
                font-family: 'Times New Roman';
            }
            QLineEdit:focus {
                border: 1px solid #1D4ED8;
                background-color: #FFFFFF;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        input_layout.addWidget(self.chat_input)

        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #1D4ED8;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover {
                background-color: #0037B0;
            }
        """)
        self.send_btn.clicked.connect(self.send_chat_message)
        input_layout.addWidget(self.send_btn)

        chat_layout.addLayout(input_layout)
        main_layout.addWidget(chat_card, stretch=1)

        # Apply shadows to cards
        self.apply_card_shadow(self.preview_card)
        self.apply_card_shadow(viewer_card)
        self.apply_card_shadow(chat_card)

        # Set default empty chat greeting
        self.append_chat_bubble("advisor", "Hello! I am your AI Business Advisor. Select a statement and ask me any questions like:\n- What are my top expenses?\n- Is there any duplicate UPI transactions?\n- What subscriptions did I pay for?")

    def on_suggestion_clicked(self, text):
        self.chat_input.setText(text)
        self.send_chat_message()

    def apply_card_shadow(self, card):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        if self.current_theme == "light":
            shadow.setColor(QColor(0, 0, 0, 15))
        else:
            shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

    # ==========================================
    # CORE LOGIC
    # ==========================================
    
    def set_active_statement(self, payload):
        """Allows direct programmatic insertion of parsed statements (e.g. from Upload)."""
        if not payload or not payload.get("transactions"):
            return

        self.active_transactions = payload["transactions"]
        
        # Extract metadata
        self.active_metadata = {
            "bank_name": payload.get("bank_name", "Unknown Bank"),
            "account_holder": payload.get("account_holder", "Unknown"),
            "period": payload.get("period", "Unknown Period"),
            "account_number": payload.get("account_number", "Unknown"),
            "currency": payload.get("currency", "INR")
        }
        
        # Populate metric totals in python
        credits = 0.0
        debits = 0.0
        for tx in self.active_transactions:
            try:
                debits += float(tx.get("debit") or 0.0)
                credits += float(tx.get("credit") or 0.0)
            except:
                pass
        self.active_metadata["total_credit"] = credits
        self.active_metadata["total_debit"] = debits
        self.active_metadata["net_savings"] = credits - debits

        # Update metrics preview widgets
        self.update_metrics_ui()

    def update_metrics_ui(self):
        """Fills UI metric values from active statement details."""
        curr = self.active_metadata.get("currency", "INR")
        symbol = "₹" if curr == "INR" else ("$" if curr == "USD" else curr)
        
        self.lbl_bank.setText(self.active_metadata.get("bank_name", "-"))
        self.lbl_period.setText(self.active_metadata.get("period", "-"))
        self.lbl_credits.setText(f"{symbol} {self.active_metadata['total_credit']:,.2f}")
        self.lbl_debits.setText(f"{symbol} {self.active_metadata['total_debit']:,.2f}")
        
        net = self.active_metadata["net_savings"]
        sign = "+" if net >= 0 else "-"
        self.lbl_savings.setText(f"{sign}{symbol} {abs(net):,.2f}")
        self.lbl_savings.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {'#16A34A' if net >= 0 else '#EF4444'};")
        
        # Reset health score until audit report generated
        self.lbl_score.setText("-")

    def load_history_dropdown(self):
        """Queries local history database logs and updates dropdown list."""
        self.statement_cb.blockSignals(True)
        self.statement_cb.clear()
        
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        logs = HistoryService.get_history_logs(user_id=user_id)
        
        completed_logs = [log for log in logs if log.get("status") == "Completed" and log.get("excel_path")]
        
        if not completed_logs:
            self.statement_cb.addItem("No parsed statements found in history.", None)
        else:
            self.statement_cb.addItem("Select from parsed statement history...", None)
            for log in completed_logs:
                pdf_path = log.get("pdf_path", "")
                excel_path = log.get("excel_path", "")
                filename = os.path.basename(pdf_path) if pdf_path else "Statement.pdf"
                upload_date = log.get("upload_date")
                if hasattr(upload_date, "strftime"):
                    date_str = upload_date.strftime("%Y-%m-%d")
                elif isinstance(upload_date, str):
                    date_str = upload_date[:10]
                else:
                    date_str = str(upload_date or "")[:10]
                bank = log.get("bank_name", "Unknown Bank")
                display_text = f"{bank} ({date_str}) - {filename}"
                self.statement_cb.addItem(display_text, excel_path)
                
        self.statement_cb.blockSignals(False)

    def on_statement_selected(self, index):
        """Loads and processes transaction details from history Excel path when selected."""
        excel_path = self.statement_cb.currentData()
        if not excel_path:
            return

        try:
            # Show quick loading popup
            self.lbl_bank.setText("Loading...")
            self.lbl_period.setText("Loading...")
            self.lbl_credits.setText("-")
            self.lbl_debits.setText("-")
            self.lbl_savings.setText("-")
            self.lbl_score.setText("-")
            
            # Read transactions from excel workbook
            transactions = self.load_transactions_from_excel(excel_path)
            meta = self.load_summary_from_excel(excel_path)
            
            payload = {
                "transactions": transactions,
                "bank_name": meta.get("bank_name", "Unknown Bank"),
                "account_holder": meta.get("account_holder", "Unknown"),
                "account_number": meta.get("account_number", "Unknown"),
                "period": meta.get("period", "Unknown Period"),
                "currency": meta.get("currency", "INR")
            }
            
            self.set_active_statement(payload)
            Toast.success(self, "✓ Statement loaded successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Excel", f"Could not load transaction sheets from Excel archive:\n{e}")
            self.load_history_dropdown()

    def load_transactions_from_excel(self, excel_path):
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        if "Transactions" not in wb.sheetnames:
            raise ValueError("Spreadsheet does not contain 'Transactions' ledger sheet.")
            
        ws = wb["Transactions"]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
            
        headers = rows[0]
        data_rows = rows[1:]
        
        # Build index mapping
        col_mapping = {}
        for idx, header in enumerate(headers):
            if header is None:
                continue
            h_lower = str(header).lower()
            if "date" in h_lower and "value" not in h_lower:
                col_mapping["date"] = idx
            elif "description" in h_lower or "narration" in h_lower or "particulars" in h_lower:
                col_mapping["narration"] = idx
            elif "debit" in h_lower:
                col_mapping["debit"] = idx
            elif "credit" in h_lower:
                col_mapping["credit"] = idx
            elif "balance" in h_lower:
                col_mapping["balance"] = idx
                
        transactions = []
        for r in data_rows:
            tx = {}
            has_val = False
            for k in ["date", "narration", "debit", "credit", "balance"]:
                idx = col_mapping.get(k)
                if idx is not None and idx < len(r):
                    val = r[idx]
                    if val is not None:
                        has_val = True
                        if k == "date" and hasattr(val, "strftime"):
                            tx[k] = val.strftime("%Y-%m-%d")
                        elif k in ["debit", "credit", "balance"]:
                            try:
                                tx[k] = float(str(val).replace(",", "").replace("₹", "").strip())
                            except:
                                tx[k] = val
                        else:
                            tx[k] = str(val).strip()
                    else:
                        tx[k] = ""
                else:
                    tx[k] = ""
            if has_val and any(tx[x] != "" for x in ["debit", "credit", "balance"]):
                transactions.append(tx)
        return transactions

    def load_summary_from_excel(self, excel_path):
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        meta = {
            "bank_name": "Unknown Bank",
            "account_holder": "Unknown",
            "account_number": "Unknown",
            "period": "Unknown Period",
            "currency": "INR"
        }
        if "Summary" in wb.sheetnames:
            ws_sum = wb["Summary"]
            for row in ws_sum.iter_rows(values_only=True):
                if len(row) >= 2:
                    label = str(row[0]).strip() if row[0] is not None else ""
                    val = row[1]
                    if "Bank Name" in label:
                        meta["bank_name"] = str(val)
                    elif "Account Holder" in label:
                        meta["account_holder"] = str(val)
                    elif "Statement Period" in label:
                        meta["period"] = str(val)
        return meta

    # ==========================================
    # ASYNC TASK HANDLERS
    # ==========================================
    
    def run_ai_task(self, action_key):
        """Starts a background thread worker to call Gemini API endpoints."""
        if not self.active_transactions:
            QMessageBox.warning(self, "No Statement Loaded", "Please upload a statement or select one from history first.")
            return

        # Check API Key exists
        api_key = GeminiService.get_api_key()
        if not api_key or not api_key.strip():
            QMessageBox.critical(self, "API Key Missing", "AI API Key is missing.\n\nPlease go to Settings and enter a valid API Key first.")
            return

        self.set_buttons_enabled(False)
        self.loading_box.setVisible(True)
        self.report_viewer.setHtml("<div style='color:#3B82F6; font-family: \"Times New Roman\", Times, serif; font-size:14px; text-align:center; padding-top:40px;'><b>AI is analyzing transactions...</b><br>Please hold, compiling executive auditing sheets...</div>")
        
        # Build worker parameters
        kwargs = {
            "bank_name": self.active_metadata.get("bank_name", "Unknown Bank"),
            "holder": self.active_metadata.get("account_holder", "Unknown"),
            "acc_num": self.active_metadata.get("account_number", "Unknown"),
            "period": self.active_metadata.get("period", "Unknown Period")
        }

        # Spawn Thread
        self.active_thread = AIWorker(
            action_key, 
            self.active_transactions, 
            self.active_metadata.get("currency", "INR"), 
            **kwargs
        )
        
        def handle_finished(result):
            self.loading_box.setVisible(False)
            self.set_buttons_enabled(True)
            self.active_thread.deleteLater()
            self.active_thread = None

            # Clean markdown code block wrapping HTML if present
            cleaned_result = result.strip()
            if cleaned_result.startswith("```"):
                lines = cleaned_result.splitlines()
                if len(lines) > 2 and lines[0].startswith("```"):
                    end_idx = len(lines) - 1
                    while end_idx > 0 and not lines[end_idx].strip() == "```":
                        end_idx -= 1
                    if end_idx > 0:
                        cleaned_result = "\n".join(lines[1:end_idx]).strip()
            result = cleaned_result

            # Render HTML result (all report methods now generate HTML)
            self.report_viewer.setHtml(result)
            
            # Select correct button check status
            if action_key == "summary":
                self.btn_summary.setChecked(True)
            elif action_key == "spending":
                self.btn_spending.setChecked(True)
            elif action_key == "risk":
                self.btn_risk.setChecked(True)
            elif action_key == "report":
                self.btn_report.setChecked(True)
                
            # Parse Health Score from HTML if present
            match = re.search(r"(\d{2,3})\s*/\s*100", result)
            if match:
                self.lbl_score.setText(f"{match.group(1)}")
                
            Toast.success(self, "✓ Analysis completed!")

        def handle_error(err_msg):
            self.loading_box.setVisible(False)
            self.set_buttons_enabled(True)
            self.active_thread.deleteLater()
            self.active_thread = None
            
            # Reset button checks on error
            if self.action_btn_group.checkedButton():
                self.action_btn_group.checkedButton().setChecked(False)
            
            # Show stylized error details
            self.report_viewer.setHtml(f"<div style='color:#EF4444; font-family: \"Times New Roman\", Times, serif; font-size:14px; padding:20px;'><b>AI Audit Failed</b><br><br>{err_msg}</div>")
            QMessageBox.critical(self, "AI Connection Failed", f"An error occurred while compiling AI insights:\n\n{err_msg}")

        self.active_thread.finished.connect(handle_finished)
        self.active_thread.error.connect(handle_error)
        self.active_thread.start()

    def send_chat_message(self):
        """Sends user text message contextually to Gemini alongside current transaction logs."""
        msg = self.chat_input.text().strip()
        if not msg:
            return

        if not self.active_transactions:
            QMessageBox.warning(self, "No Statement Loaded", "Please upload a statement or select one from history first.")
            return

        self.chat_input.clear()
        
        # Log message in UI
        self.append_chat_bubble("user", msg)
        self.chat_history.append({"role": "user", "content": msg})
        
        # Add thinking placeholder bubble with cycling dot typing animation
        self.thinking_bubble = QFrame()
        thinking_lay = QVBoxLayout(self.thinking_bubble)
        thinking_lay.setContentsMargins(12, 10, 12, 10)
        thinking_lbl = QLabel("Thinking")
        thinking_lbl.setStyleSheet("font-size: 11px; font-style: italic; color: #7C3AED; font-family: 'Times New Roman';")
        thinking_lay.addWidget(thinking_lbl)
        if self.current_theme == "light":
            self.thinking_bubble.setStyleSheet("background-color: #F5F3FF; border: 1px dashed #DDD6FE; border-radius: 12px; border-bottom-left-radius: 2px;")
        else:
            self.thinking_bubble.setStyleSheet("background-color: #2E1065; border: 1px dashed #581C87; border-radius: 12px; border-bottom-left-radius: 2px;")
        
        self.chat_container_layout.insertWidget(self.chat_container_layout.count() - 1, self.thinking_bubble, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # Setup typing timer
        self.thinking_dots_count = 0
        def update_dots():
            self.thinking_dots_count = (self.thinking_dots_count + 1) % 4
            dots = "." * self.thinking_dots_count
            thinking_lbl.setText(f"Thinking{dots:<3}")
            
        self.thinking_timer = QTimer(self)
        self.thinking_timer.timeout.connect(update_dots)
        self.thinking_timer.start(400)

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

        self.chat_input.setEnabled(False)
        self.send_btn.setEnabled(False)

        # Trigger background chat thread
        self.chat_thread = AIWorker(
            "chat",
            self.active_transactions,
            self.active_metadata.get("currency", "INR"),
            chat_history=self.chat_history,
            message=msg
        )

        def on_finished(reply):
            # Stop timer and remove thinking bubble
            if hasattr(self, "thinking_timer") and self.thinking_timer:
                self.thinking_timer.stop()
                self.thinking_timer.deleteLater()
                self.thinking_timer = None
            if hasattr(self, "thinking_bubble") and self.thinking_bubble:
                self.chat_container_layout.removeWidget(self.thinking_bubble)
                self.thinking_bubble.deleteLater()
                self.thinking_bubble = None
            
            self.chat_input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.chat_input.setFocus()
            self.chat_thread.deleteLater()

            self.append_chat_bubble("advisor", reply)
            self.chat_history.append({"role": "assistant", "content": reply})

        def on_error(err):
            # Stop timer and remove thinking bubble
            if hasattr(self, "thinking_timer") and self.thinking_timer:
                self.thinking_timer.stop()
                self.thinking_timer.deleteLater()
                self.thinking_timer = None
            if hasattr(self, "thinking_bubble") and self.thinking_bubble:
                self.chat_container_layout.removeWidget(self.thinking_bubble)
                self.thinking_bubble.deleteLater()
                self.thinking_bubble = None
                
            self.chat_input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.chat_thread.deleteLater()
            
            self.append_chat_bubble("advisor", f"⚠️ Failed to get advice: {err}")

        self.chat_thread.finished.connect(on_finished)
        self.chat_thread.error.connect(on_error)
        self.chat_thread.start()

    # ==========================================
    # EXPORT REPORT (PDF PRINTING)
    # ==========================================
    
    def export_pdf_report(self):
        """Prints the report viewer HTML contents into a beautiful PDF file."""
        html_content = self.report_viewer.toHtml()
        if not html_content or "Select a statement" in html_content:
            return

        # Prompt save location
        filename = f"AI_Financial_Audit_Report_{self.active_metadata.get('bank_name')}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
        doc_dir = os.path.expanduser("~/Documents")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save AI Financial Audit PDF Report", os.path.join(doc_dir, filename), "PDF Files (*.pdf)"
        )
        
        if not filepath:
            return

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(filepath)
            
            # Setup standard margins
            printer.setPageMargins(
                QSize(15, 15), QPrinter.Unit.Millimeter
            )
            
            doc = QTextDocument()
            doc.setHtml(html_content)
            doc.print_(printer)
            
            Toast.success(self, "✓ Professional PDF Report exported successfully!")
            
            # Open file
            if os.path.exists(filepath):
                if os.name == 'nt':
                    os.startfile(filepath)
                else:
                    import subprocess
                    subprocess.run(["open", filepath] if os.name == 'posix' else ["xdg-open", filepath])
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not render and print PDF workbook:\n{e}")

    # ==========================================
    # HELPERS
    # ==========================================
    
    def append_chat_bubble(self, sender, text):
        """Appends a bubble representing conversation items in the advisor pane."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 4, 0, 4)
        row_layout.setSpacing(8)
        
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(28, 28)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        bubble_frame = QFrame()
        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(12, 10, 12, 10)
        bubble_layout.setSpacing(4)
        
        sender_lbl = QLabel("Business Advisor" if sender == "advisor" else "You")
        
        time_str = datetime.datetime.now().strftime("%I:%M %p")
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet("font-size: 8px; color: #94A3B8;")
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(sender_lbl)
        header_layout.addStretch()
        header_layout.addWidget(time_lbl)
        bubble_layout.addLayout(header_layout)
        
        msg_lbl = QLabel()
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Simple Markdown-to-HTML helper for bubble message rendering
        if "\n" in text or "**" in text or "*" in text:
            html_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html_text)
            html_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", html_text)
            html_text = html_text.replace("\n", "<br>")
            msg_lbl.setText(html_text)
        else:
            msg_lbl.setText(text)
            
        bubble_layout.addWidget(msg_lbl)
        
        if sender == "advisor":
            avatar_lbl.setText("🤖")
            if self.current_theme == "light":
                avatar_lbl.setStyleSheet("background-color: #F5F3FF; border: 1px solid #DDD6FE; border-radius: 14px; font-size: 14px;")
                bubble_frame.setStyleSheet("background-color: #F5F3FF; border: 1px solid #DDD6FE; border-radius: 12px; border-bottom-left-radius: 2px;")
                msg_lbl.setStyleSheet("font-size: 12px; color: #4C1D95; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
                sender_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #7C3AED; text-transform: uppercase;")
            else:
                avatar_lbl.setStyleSheet("background-color: #2E1065; border: 1px solid #581C87; border-radius: 14px; font-size: 14px;")
                bubble_frame.setStyleSheet("background-color: #2E1065; border: 1px solid #581C87; border-radius: 12px; border-bottom-left-radius: 2px;")
                msg_lbl.setStyleSheet("font-size: 12px; color: #F5F3FF; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
                sender_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #A78BFA; text-transform: uppercase;")
                
            row_layout.addWidget(avatar_lbl, alignment=Qt.AlignmentFlag.AlignTop)
            row_layout.addWidget(bubble_frame, stretch=1)
            row_layout.addStretch()
        else:
            avatar_lbl.setText("👤")
            if self.current_theme == "light":
                avatar_lbl.setStyleSheet("background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 14px; font-size: 14px;")
                bubble_frame.setStyleSheet("background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 12px; border-bottom-right-radius: 2px;")
                msg_lbl.setStyleSheet("font-size: 12px; color: #1E3A8A; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
                sender_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #2563EB; text-transform: uppercase;")
            else:
                avatar_lbl.setStyleSheet("background-color: #172554; border: 1px solid #1E3A8A; border-radius: 14px; font-size: 14px;")
                bubble_frame.setStyleSheet("background-color: #172554; border: 1px solid #1E3A8A; border-radius: 12px; border-bottom-right-radius: 2px;")
                msg_lbl.setStyleSheet("font-size: 12px; color: #EFF6FF; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
                sender_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #60A5FA; text-transform: uppercase;")
                
            row_layout.addStretch()
            row_layout.addWidget(bubble_frame, stretch=1)
            row_layout.addWidget(avatar_lbl, alignment=Qt.AlignmentFlag.AlignTop)
            
        self.chat_container_layout.insertWidget(self.chat_container_layout.count() - 1, row_widget)
        
        # Smoothly scroll to bottom
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def set_buttons_enabled(self, enabled):
        self.btn_summary.setEnabled(enabled)
        self.btn_spending.setEnabled(enabled)
        self.btn_risk.setEnabled(enabled)
        self.btn_report.setEnabled(enabled)
        self.statement_cb.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)

    def convert_markdown_to_html(self, md):
        """Simple regex-based markdown to HTML converter for rendering reports locally."""
        html = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        html = re.sub(r"^### (.*?)$", r"<h3 style='color:#1E3A8A; font-family:\"Times New Roman\",Times,serif; margin-top:12px;'>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.*?)$", r"<h2 style='color:#1E3A8A; font-family:\"Times New Roman\",Times,serif; border-bottom:1px solid #E2E8F0; padding-bottom:4px; margin-top:16px;'>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.*?)$", r"<h1 style='color:#0F172A; font-family:\"Times New Roman\",Times,serif; margin-top:20px;'>\1</h1>", html, flags=re.MULTILINE)
        
        html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html)
        html = re.sub(r"^\-\s*(.*?)$", r"<li style='margin-left:15px; font-family:\"Times New Roman\",Times,serif; font-size:13px; line-height:1.4;'>\1</li>", html, flags=re.MULTILINE)
        
        lines = html.split('\n')
        in_table = False
        table_html = []
        for line in lines:
            if line.strip().startswith('|'):
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if not parts:
                    continue
                if "---" in parts[0]:
                    continue
                if not in_table:
                    in_table = True
                    table_html.append("<table style='width:100%; border-collapse:collapse; margin-top:10px; margin-bottom:10px; font-family:\"Times New Roman\",Times,serif; font-size:13px;'>")
                    table_html.append("<tr>" + "".join(f"<th style='background-color:#F1F5F9; color:#1E293B; border:1px solid #CBD5E1; padding:6px; text-align:left;'>{p}</th>" for p in parts) + "</tr>")
                else:
                    table_html.append("<tr>" + "".join(f"<td style='border:1px solid #E2E8F0; padding:6px; color:#334155;'>{p}</td>" for p in parts) + "</tr>")
            else:
                if in_table:
                    in_table = False
                    table_html.append("</table>")
                table_html.append(line + "<br>")
                
        if in_table:
            table_html.append("</table>")
            
        final_html = "".join(table_html)
        final_html = f"<div style='font-family:\"Times New Roman\",Times,serif; font-size:13px; line-height:1.5; color:#1E293B;'>{final_html}</div>"
        return final_html

    def update_theme_style(self, theme):
        """Adapts UI components to application theme changes."""
        self.current_theme = theme
        if theme == "dark":
            self.title_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #F8FAFC;")
            self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #94A3B8;")
            self.preview_card.setStyleSheet("""
                QFrame#PreviewCard {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }
            """)
            self.statement_cb.setStyleSheet("""
                QComboBox {
                    padding: 6px 12px;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    background-color: #1E293B;
                    color: #F8FAFC;
                }
            """)
            self.refresh_btn.setStyleSheet("""
                QPushButton {
                    background-color: #334155;
                    color: #F8FAFC;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #475569;
                }
            """)
            
            for label in self.stats_box.findChildren(QLabel):
                style = label.styleSheet()
                if "color: #0F172A" in style:
                    label.setStyleSheet(style.replace("color: #0F172A", "color: #F8FAFC"))
            
            self.loading_box.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; border-radius: 8px;")
            self.loading_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #94A3B8;")
            
            viewer_card = self.findChild(QFrame, "ViewerCard")
            if viewer_card:
                viewer_card.setStyleSheet("""
                    QFrame#ViewerCard {
                        background-color: #1E293B;
                        border: 1px solid #334155;
                        border-radius: 12px;
                    }
                """)
            
            chat_card = self.findChild(QFrame, "ChatCard")
            if chat_card:
                chat_card.setStyleSheet("""
                    QFrame#ChatCard {
                        background-color: #1E293B;
                        border: 1px solid #334155;
                        border-radius: 12px;
                    }
                """)
                
            self.chat_input.setStyleSheet("""
                QLineEdit {
                    padding: 10px 14px;
                    border: 1px solid #475569;
                    border-radius: 20px;
                    background-color: #1E293B;
                    color: #F8FAFC;
                    font-size: 12px;
                    font-family: 'Times New Roman';
                }
                QLineEdit:focus {
                    border: 1px solid #3B82F6;
                    background-color: #0F172A;
                }
            """)
            
            self.suggestions_box.setStyleSheet("""
                QPushButton#ChatSuggestionButton {
                    background-color: #334155;
                    color: #F8FAFC;
                    border: 1px solid #475569;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton#ChatSuggestionButton:hover {
                    background-color: #475569;
                    color: #FFFFFF;
                }
            """)
        else:
            self.title_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
            self.subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
            self.preview_card.setStyleSheet("""
                QFrame#PreviewCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """)
            self.statement_cb.setStyleSheet("""
                QComboBox {
                    padding: 6px 12px;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    background-color: #FFFFFF;
                    color: #0F172A;
                }
            """)
            self.refresh_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    color: #475569;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                }
            """)
            
            for label in self.stats_box.findChildren(QLabel):
                style = label.styleSheet()
                if "color: #F8FAFC" in style:
                    label.setStyleSheet(style.replace("color: #F8FAFC", "color: #0F172A"))
                    
            self.loading_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
            self.loading_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
            
            viewer_card = self.findChild(QFrame, "ViewerCard")
            if viewer_card:
                viewer_card.setStyleSheet("""
                    QFrame#ViewerCard {
                        background-color: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 12px;
                    }
                """)
            
            chat_card = self.findChild(QFrame, "ChatCard")
            if chat_card:
                chat_card.setStyleSheet("""
                    QFrame#ChatCard {
                        background-color: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 12px;
                    }
                """)
                
            self.chat_input.setStyleSheet("""
                QLineEdit {
                    padding: 10px 14px;
                    border: 1px solid #CBD5E1;
                    border-radius: 20px;
                    background-color: #F8FAFC;
                    color: #0F172A;
                    font-size: 12px;
                    font-family: 'Times New Roman';
                }
                QLineEdit:focus {
                    border: 1px solid #1D4ED8;
                    background-color: #FFFFFF;
                }
            """)
            
            self.suggestions_box.setStyleSheet("""
                QPushButton#ChatSuggestionButton {
                    background-color: #F1F5F9;
                    color: #475569;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton#ChatSuggestionButton:hover {
                    background-color: #E2E8F0;
                    color: #0F172A;
                }
            """)

        # Re-apply shadow effects to update shadow color for theme
        self.apply_card_shadow(self.preview_card)
        viewer_card = self.findChild(QFrame, "ViewerCard")
        if viewer_card:
            self.apply_card_shadow(viewer_card)
        chat_card = self.findChild(QFrame, "ChatCard")
        if chat_card:
            self.apply_card_shadow(chat_card)

        html = self.report_viewer.toHtml()
        if "Select a statement" in html or "No Statement Loaded" in html:
            pass
        else:
            body_color = "#F8FAFC" if theme == "dark" else "#1E293B"
            self.report_viewer.setStyleSheet(f"border: none; background-color: transparent; color: {body_color};")

    def open_email_composer(self):
        """Opens Email Composer pre-attaching active AI report."""
        from ui.email_composer_dialog import EmailComposerDialog
        
        attachment = getattr(self, "excel_path", None) or getattr(self, "pdf_path", None)
        period = getattr(self, "statement_period", "") or ""
        bank = getattr(self, "detected_bank", "") or ""

        dialog = EmailComposerDialog(
            report_type="AI Financial Analysis Report",
            default_attachment=attachment,
            period=period,
            bank_name=bank,
            parent=self
        )
        dialog.exec()
