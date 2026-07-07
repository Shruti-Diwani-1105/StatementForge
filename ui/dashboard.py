from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QStackedWidget, QScrollArea, QGridLayout, QFrame, 
                             QSpacerItem, QSizePolicy, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLineEdit, QPushButton,
                             QComboBox, QCheckBox, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor
from widgets.sidebar import Sidebar
from widgets.topbar import TopBar
from widgets.custom_card import CustomCard
from widgets.custom_button import PrimaryButton, SecondaryButton

class DashboardScreen(QWidget):
    """
    Main application dashboard view. Connects Sidebar selections
    to a local stacked widget containing modules.
    """
    logoutRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Main Layout (splits sidebar and main area)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Left Sidebar
        self.sidebar = Sidebar(self)
        self.sidebar.nav_changed.connect(self.switch_dashboard_page)
        self.sidebar.logout_clicked.connect(self.logoutRequested.emit)
        layout.addWidget(self.sidebar)
        
        # Right container
        right_container = QWidget()
        right_container.setObjectName("RightContainer")
        right_container.setStyleSheet("QWidget#RightContainer { background-color: #F8FAFC; }")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 2. Topbar
        self.topbar = TopBar(self)
        right_layout.addWidget(self.topbar)
        
        # 3. Main content Stacked Widget
        self.page_stack = QStackedWidget()
        
        # Create and add individual sub-pages
        self.create_main_dashboard_page()
        self.create_upload_page()
        self.create_history_page()
        self.create_reports_page()
        self.create_settings_page()
        
        right_layout.addWidget(self.page_stack)
        layout.addWidget(right_container)

    def switch_dashboard_page(self, key):
        """Switches the sub-page stacked widget index based on the clicked sidebar option."""
        mapping = {
            "dashboard": 0,
            "upload": 1,
            "history": 2,
            "reports": 3,
            "settings": 4
        }
        if key in mapping:
            self.page_stack.setCurrentIndex(mapping[key])
            
            # Sync sidebar checked state if called programmatically
            self.sidebar.set_active_page(key)

    def set_user_profile(self, user_details):
        """Updates the dashboard greeting and topbar initials avatar with user details."""
        full_name = user_details.get("name", "User")
        
        # Update TopBar details
        if hasattr(self, "topbar") and self.topbar is not None:
            self.topbar.update_profile(full_name)
            
        # Update Welcome Greeting first name
        first_name = full_name.split()[0] if full_name.strip() else "User"
        if hasattr(self, "welcome_lbl") and self.welcome_lbl is not None:
            self.welcome_lbl.setText(f"Welcome Back, {first_name}!")
            
        # Refresh dashboard stats dynamically
        self.update_dashboard_stats()

    def update_dashboard_stats(self):
        """Fetches dynamic metrics from HistoryService and updates dashboard labels."""
        from services.history_service import HistoryService
        from utils.user_session import UserSession
        
        user = UserSession.get_current_user()
        user_id = user["id"] if user else None
        
        stats = HistoryService.get_stats(user_id)
        
        if hasattr(self, "stats_processed_lbl") and self.stats_processed_lbl is not None:
            self.stats_processed_lbl.setText(str(stats["processed"]))
        if hasattr(self, "stats_verified_lbl") and self.stats_verified_lbl is not None:
            self.stats_verified_lbl.setText(f"{stats['verified']:,}")
        if hasattr(self, "stats_exported_lbl") and self.stats_exported_lbl is not None:
            self.stats_exported_lbl.setText(str(stats["exported"]))
            
        if hasattr(self, "update_recent_activity_ui"):
            self.update_recent_activity_ui(user_id)

    def update_recent_activity_ui(self, user_id):
        """Rebuilds the Recent Activity list widgets dynamically."""
        if not hasattr(self, "activity_layout") or self.activity_layout is None:
            return

        # Clear layout first
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            # If it's a spacer, taking it out is enough

        # Re-add Title
        act_title = QLabel("Recent Activity")
        act_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A; margin-bottom: 8px;")
        self.activity_layout.addWidget(act_title)

        # Fetch recent items
        from services.history_service import HistoryService
        import datetime
        
        recent = HistoryService.get_recent_activity(user_id, limit=5)
        
        if not recent:
            self.activity_layout.addStretch()
            empty_lbl = QLabel("No recent activity.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 500;")
            self.activity_layout.addWidget(empty_lbl)
            self.activity_layout.addStretch()
        else:
            # Helper for time ago
            def time_ago(dt):
                if not dt:
                    return "some time ago"
                if isinstance(dt, str):
                    try:
                        dt = datetime.datetime.fromisoformat(dt.replace("Z", "+00:00"))
                    except Exception:
                        return dt
                
                # Make naive for comparison
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                now = datetime.datetime.utcnow()
                diff = now - dt
                seconds = diff.total_seconds()
                if seconds < 60:
                    return "Just now"
                minutes = seconds / 60
                if minutes < 60:
                    return f"{int(minutes)}m ago"
                hours = minutes / 60
                if hours < 24:
                    return f"{int(hours)}h ago"
                days = hours / 24
                if days < 7:
                    return f"{int(days)}d ago"
                return dt.strftime("%b %d")

            for item in recent:
                item_widget = QFrame()
                item_widget.setObjectName("ActivityItem")
                item_widget.setStyleSheet("""
                    QFrame#ActivityItem {
                        background-color: #F8FAFC;
                        border: 1px solid #E2E8F0;
                        border-radius: 8px;
                    }
                    QFrame#ActivityItem:hover {
                        background-color: #EFF6FF;
                        border-color: #DBEAFE;
                    }
                """)
                item_lay = QHBoxLayout(item_widget)
                item_lay.setContentsMargins(10, 8, 10, 8)
                item_lay.setSpacing(10)

                # Bullet check
                bullet = QLabel("✓")
                bullet.setFixedSize(20, 20)
                bullet.setAlignment(Qt.AlignmentFlag.AlignCenter)
                bullet.setStyleSheet("""
                    background-color: #ECFDF5;
                    color: #10B981;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 10px;
                    border: 1px solid #D1FAE5;
                """)
                item_lay.addWidget(bullet)

                # Texts
                text_lay = QVBoxLayout()
                text_lay.setSpacing(2)
                
                # File Name
                fn_lbl = QLabel(item["file_name"])
                fn_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #1E293B;")
                
                # Subtitle: Bank + Time
                ago_str = time_ago(item["upload_date"])
                sub_lbl = QLabel(f"{item['bank_name']} • {ago_str}")
                sub_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
                
                text_lay.addWidget(fn_lbl)
                text_lay.addWidget(sub_lbl)
                item_lay.addLayout(text_lay, stretch=1)
                
                self.activity_layout.addWidget(item_widget)

            # Add expanding spacer at the end to push elements up
            self.activity_layout.addStretch()

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

    # --- Page Creation Methods ---

    def create_main_dashboard_page(self):
        """Dashboard overview showing metrics, module card shortcuts, and recent activity."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        page_layout = QVBoxLayout(scroll_content)
        page_layout.setContentsMargins(32, 24, 32, 32)
        page_layout.setSpacing(28)
        
        # Header Greeting
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        self.welcome_lbl = QLabel("Welcome Back, John!")
        self.welcome_lbl.setStyleSheet("font-size: 26px; font-weight: 700; color: #0F172A; letter-spacing: -0.5px;")
        sub_lbl = QLabel("Here's an overview of your local financial statements parser activities.")
        sub_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
        header_layout.addWidget(self.welcome_lbl)
        header_layout.addWidget(sub_lbl)
        page_layout.addLayout(header_layout)
        
        # 1. Statistics / Metric Cards Row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(24)
        
        # Statements Processed
        card1 = QFrame()
        card1.setObjectName("MetricCard")
        card1.setStyleSheet("QFrame#MetricCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #2563EB; border-radius: 12px; }")
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(20, 20, 20, 20)
        card1_layout.setSpacing(8)
        t_lbl1 = QLabel("Statements Processed")
        t_lbl1.setStyleSheet("font-size: 13px; font-weight: 600; color: #64748B;")
        self.stats_processed_lbl = QLabel("0")
        self.stats_processed_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #2563EB;")
        card1_layout.addWidget(t_lbl1)
        card1_layout.addWidget(self.stats_processed_lbl)
        metrics_layout.addWidget(card1)
        
        # Transactions Verified
        card2 = QFrame()
        card2.setObjectName("MetricCard")
        card2.setStyleSheet("QFrame#MetricCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #16A34A; border-radius: 12px; }")
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(20, 20, 20, 20)
        card2_layout.setSpacing(8)
        t_lbl2 = QLabel("Transactions Verified")
        t_lbl2.setStyleSheet("font-size: 13px; font-weight: 600; color: #64748B;")
        self.stats_verified_lbl = QLabel("0")
        self.stats_verified_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #16A34A;")
        card2_layout.addWidget(t_lbl2)
        card2_layout.addWidget(self.stats_verified_lbl)
        metrics_layout.addWidget(card2)
        
        # Reports Exported
        card3 = QFrame()
        card3.setObjectName("MetricCard")
        card3.setStyleSheet("QFrame#MetricCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #EA580C; border-radius: 12px; }")
        card3_layout = QVBoxLayout(card3)
        card3_layout.setContentsMargins(20, 20, 20, 20)
        card3_layout.setSpacing(8)
        t_lbl3 = QLabel("Reports Exported")
        t_lbl3.setStyleSheet("font-size: 13px; font-weight: 600; color: #64748B;")
        self.stats_exported_lbl = QLabel("0")
        self.stats_exported_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #EA580C;")
        card3_layout.addWidget(t_lbl3)
        card3_layout.addWidget(self.stats_exported_lbl)
        metrics_layout.addWidget(card3)
        
        page_layout.addLayout(metrics_layout)
        
        # Initial stats population
        self.update_dashboard_stats()
        
        # 2. Main content split (Module Grid on left, Recent Activity on right)
        content_split = QHBoxLayout()
        content_split.setSpacing(24)
        
        # Left: Modules Grid Container
        modules_container = QWidget()
        modules_layout = QVBoxLayout(modules_container)
        modules_layout.setContentsMargins(0, 0, 0, 0)
        modules_layout.setSpacing(12)
        
        section_title = QLabel("System Modules")
        section_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        modules_layout.addWidget(section_title)
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(16)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Module card definitions: (Title, Icon, Description, Backdrop Color)
        modules = [
            ("Upload Statement", "upload", "Parse and extract transactions.", "#EFF6FF"),
            ("Generate Excel", "excel", "Export to clean sheets.", "#F0FDF4"),
            ("AI Report", "ai", "Generate intelligent insights.", "#F5F3FF"),
            ("GST Report", "gst", "Prepare statements for tax filings.", "#FFFBEB"),
            ("Tally Export", "tally", "Export ready for Tally integration.", "#FFF7ED"),
            ("Duplicate Finder", "duplicate", "Find double entry transactions.", "#FEF2F2"),
            ("History Logs", "history", "Browse localized SQLite history.", "#EFF6FF"),
            ("Email Report", "email", "Send parsed summaries safely.", "#ECFDF5")
        ]
        
        cols = 3
        for idx, (title, icon, desc, icon_bg) in enumerate(modules):
            row = idx // cols
            col = idx % cols
            card = CustomCard(title, desc, f"assets/icons/{icon}.png", icon_bg)
            
            # Map dashboard cards to their respective pages, fallback to coming soon
            if title == "Upload Statement":
                card.clicked.connect(lambda: self.switch_dashboard_page("upload"))
            elif title == "History Logs":
                card.clicked.connect(lambda: self.switch_dashboard_page("history"))
            else:
                card.clicked.connect(lambda t=title: self.show_coming_soon(t))
                
            grid_layout.addWidget(card, row, col)
            
        modules_layout.addWidget(grid_widget)
        content_split.addWidget(modules_container, stretch=3)
        
        # Right: Recent Activity Container
        self.activity_card = QFrame()
        self.activity_card.setObjectName("ActivityCard")
        self.activity_card.setStyleSheet("""
            QFrame#ActivityCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        self.activity_layout = QVBoxLayout(self.activity_card)
        self.activity_layout.setContentsMargins(20, 20, 20, 20)
        self.activity_layout.setSpacing(12)
        self.activity_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Initial population of recent activities will happen during stats update
        
        content_split.addWidget(self.activity_card, stretch=1)
        page_layout.addLayout(content_split)
        
        scroll_area.setWidget(scroll_content)
        self.page_stack.addWidget(scroll_area)

    def create_upload_page(self):
        """Creates the interactive PDF Upload Statement module."""
        from ui.upload_statement import UploadStatementWidget
        self.upload_widget = UploadStatementWidget(self)
        self.upload_widget.processingCompleted.connect(self.update_dashboard_stats)
        self.page_stack.addWidget(self.upload_widget)

    def create_history_page(self):
        """History Page mockup displaying a clean, populated transactions table structure."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(32, 24, 32, 32)
        page_layout.setSpacing(20)
        
        header_lbl = QLabel("Statement History")
        header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        sub_lbl = QLabel("Review previously uploaded and parsed financial statements.")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 13px;")
        
        page_layout.addWidget(header_lbl)
        page_layout.addWidget(sub_lbl)
        
        # Table widget setup
        table_container = QFrame()
        table_container.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;")
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(12, 12, 12, 12)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["Upload Date", "File Name", "Bank Name", "Period", "Status", "Action"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setStyleSheet("border: none; gridline-color: #F1F5F9;")
        
        mock_data = [
            ("2026-07-01", "Chase_Checking_Jun2026.pdf", "Chase Bank", "Jun 01 - Jun 30, 2026", "COMPLETED", "#16A34A"),
            ("2026-07-02", "BOA_CreditCard_Jun2026.pdf", "Bank of America", "Jun 05 - Jul 02, 2026", "COMPLETED", "#16A34A"),
            ("2026-07-05", "Wells_Saving_Jun2026.pdf", "Wells Fargo", "Jun 01 - Jun 30, 2026", "FAILED", "#EF4444")
        ]
        
        self.history_table.setRowCount(len(mock_data))
        
        from PyQt6.QtGui import QCursor
        for row_idx, (upload_date, file_name, bank_name, period, status, color) in enumerate(mock_data):
            # Standard Text Items
            date_item = QTableWidgetItem(upload_date)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row_idx, 0, date_item)
            
            file_item = QTableWidgetItem(file_name)
            file_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row_idx, 1, file_item)
            
            bank_item = QTableWidgetItem(bank_name)
            bank_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row_idx, 2, bank_item)
            
            period_item = QTableWidgetItem(period)
            period_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row_idx, 3, period_item)
            
            # Status Badge container (QLabel cell widget)
            status_container = QWidget()
            sc_layout = QHBoxLayout(status_container)
            sc_layout.setContentsMargins(4, 4, 4, 4)
            sc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            status_badge = QLabel(status)
            status_badge.setFixedSize(90, 22)
            status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {color}1A;
                    color: {color};
                    font-weight: 600;
                    font-size: 11px;
                    border-radius: 11px;
                    border: 1px solid {color}33;
                }}
            """)
            sc_layout.addWidget(status_badge)
            self.history_table.setCellWidget(row_idx, 4, status_container)
            
            # Action Button cell widget
            action_container = QWidget()
            ac_layout = QHBoxLayout(action_container)
            ac_layout.setContentsMargins(4, 4, 4, 4)
            ac_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            view_btn = QPushButton("View")
            view_btn.setFixedSize(60, 22)
            view_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #EFF6FF;
                    color: #2563EB;
                    border: none;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #DBEAFE;
                }
            """)
            view_btn.clicked.connect(lambda checked, fn=file_name: self.show_coming_soon(f"Viewer for {fn}"))
            ac_layout.addWidget(view_btn)
            self.history_table.setCellWidget(row_idx, 5, action_container)
            
        tc_layout.addWidget(self.history_table)
        page_layout.addWidget(table_container)
        
        page_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.page_stack.addWidget(page)

    def create_reports_page(self):
        """Reports Page presenting visual category progress bars and downloadable report options."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(32, 24, 32, 32)
        page_layout.setSpacing(24)
        
        header_lbl = QLabel("Financial Reports")
        header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        sub_lbl = QLabel("Analyze transactions and export tax-compliant ledgers.")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 13px;")
        
        page_layout.addWidget(header_lbl)
        page_layout.addWidget(sub_lbl)
        
        # Horizontal Split Layout
        split_layout = QHBoxLayout()
        split_layout.setSpacing(24)
        
        # 1. Left Frame: Category Breakdown Chart
        chart_card = QFrame()
        chart_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;")
        cc_layout = QVBoxLayout(chart_card)
        cc_layout.setContentsMargins(24, 24, 24, 24)
        cc_layout.setSpacing(16)
        
        cc_title = QLabel("Expense Breakdown (Jun 2026)")
        cc_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        cc_layout.addWidget(cc_title)
        
        categories = [
            ("Operations & Utilities", 45, "$4,500.00", "#2563EB"),
            ("Software SaaS & Tools", 30, "$3,000.00", "#0D9488"),
            ("Office & Admin Expenses", 15, "$1,500.00", "#EA580C"),
            ("Marketing & Advertising", 10, "$1,000.00", "#16A34A")
        ]
        
        for name, percent, total, color in categories:
            cat_layout = QVBoxLayout()
            cat_layout.setSpacing(6)
            
            # Text line: Name and amount
            txt_layout = QHBoxLayout()
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569;")
            amount_lbl = QLabel(f"{total} ({percent}%)")
            amount_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #0F172A;")
            txt_layout.addWidget(name_lbl)
            txt_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
            txt_layout.addWidget(amount_lbl)
            
            # Progress Bar representation
            pbar = QProgressBar()
            pbar.setValue(percent)
            pbar.setFixedHeight(8)
            pbar.setTextVisible(False)
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #F1F5F9;
                    border: none;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
            """)
            
            cat_layout.addLayout(txt_layout)
            cat_layout.addWidget(pbar)
            cc_layout.addLayout(cat_layout)
            
        cc_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        split_layout.addWidget(chart_card, stretch=4)
        
        # 2. Right Frame: Downloadable Cards List
        reports_list = QWidget()
        rl_layout = QVBoxLayout(reports_list)
        rl_layout.setContentsMargins(0, 0, 0, 0)
        rl_layout.setSpacing(16)
        
        reports_data = [
            ("Profit & Loss Statement", "Detailed revenue vs expenditure breakdown.", "assets/icons/reports.png", "Download PDF", "#EFF6FF", "#2563EB"),
            ("GST Tax Ledger", "Clean spreadsheet formatting ready for tax filing.", "assets/icons/excel.png", "Export Excel", "#F0FDF4", "#16A34A"),
            ("Duplicate Transaction Log", "Flagged entries audit summary sheet.", "assets/icons/duplicate.png", "View Audit", "#FEF2F2", "#EF4444")
        ]
        
        from PyQt6.QtGui import QCursor
        for r_title, r_desc, r_icon, action_text, bg_col, txt_col in reports_data:
            r_card = QFrame()
            r_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;")
            rc_layout = QHBoxLayout(r_card)
            rc_layout.setContentsMargins(16, 16, 16, 16)
            rc_layout.setSpacing(16)
            
            # Icon with circular background
            r_icon_lbl = QLabel()
            r_icon_lbl.setFixedSize(40, 40)
            r_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            r_icon_lbl.setStyleSheet(f"background-color: {bg_col}; border-radius: 20px; border: none;")
            r_pixmap = QPixmap(r_icon)
            if not r_pixmap.isNull():
                r_icon_lbl.setPixmap(r_pixmap.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            rc_layout.addWidget(r_icon_lbl)
            
            # Title & Description
            text_lay = QVBoxLayout()
            text_lay.setSpacing(4)
            card_title = QLabel(r_title)
            card_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #0F172A;")
            card_desc = QLabel(r_desc)
            card_desc.setStyleSheet("font-size: 12px; color: #64748B;")
            text_lay.addWidget(card_title)
            text_lay.addWidget(card_desc)
            rc_layout.addLayout(text_lay, stretch=1)
            
            # Download Action Button
            dl_btn = QPushButton(action_text)
            dl_btn.setFixedSize(110, 30)
            dl_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            dl_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_col};
                    color: {txt_col};
                    font-weight: 600;
                    font-size: 12px;
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {txt_col}22;
                }}
            """)
            dl_btn.clicked.connect(lambda checked, t=r_title: self.show_coming_soon(t))
            rc_layout.addWidget(dl_btn)
            rl_layout.addWidget(r_card)
            
        rl_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        split_layout.addWidget(reports_list, stretch=5)
        
        page_layout.addLayout(split_layout)
        self.page_stack.addWidget(page)

    def create_settings_page(self):
        """Settings Page representation mockup showing options fields."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(32, 24, 32, 32)
        page_layout.setSpacing(24)
        
        header_lbl = QLabel("Application Settings")
        header_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #0F172A;")
        sub_lbl = QLabel("Manage localization settings, OCR configs, and local file storage paths.")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 13px;")
        
        page_layout.addWidget(header_lbl)
        page_layout.addWidget(sub_lbl)
        
        # Scroll Area for settings form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 16, 0)
        scroll_layout.setSpacing(16)
        
        # Forms frame
        settings_frame = QFrame()
        settings_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;")
        sf_layout = QVBoxLayout(settings_frame)
        sf_layout.setContentsMargins(32, 32, 32, 32)
        sf_layout.setSpacing(20)
        
        # SQLite db path settings
        db_layout = QVBoxLayout()
        db_layout.setSpacing(8)
        db_title = QLabel("SQLite Database Destination Path")
        db_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569;")
        self.db_path_input = QLineEdit()
        self.db_path_input.setText("database/history.db")
        self.db_path_input.setReadOnly(True)
        db_layout.addWidget(db_title)
        db_layout.addWidget(self.db_path_input)
        sf_layout.addLayout(db_layout)
        
        # Export Destination path settings
        export_layout = QVBoxLayout()
        export_layout.setSpacing(8)
        export_title = QLabel("Default Spreadsheet Export Directory")
        export_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569;")
        self.export_path_input = QLineEdit()
        self.export_path_input.setText("exports/")
        self.export_path_input.setReadOnly(True)
        export_layout.addWidget(export_title)
        export_layout.addWidget(self.export_path_input)
        sf_layout.addLayout(export_layout)
        
        # AI Detection Engine dropdown
        ai_layout = QVBoxLayout()
        ai_layout.setSpacing(8)
        ai_title = QLabel("AI Detection & Parsing Engine")
        ai_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569;")
        self.ai_combo = QComboBox()
        self.ai_combo.addItems(["Fast Local Parser (Regex & Rules)", "Deep OCR Engine (Tesseract)", "Cloud AI LLM Engine (GPT-4o/Claude)"])
        self.ai_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                padding: 10px 14px;
                color: #0F172A;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                selection-background-color: #2563EB;
                selection-color: #FFFFFF;
            }
        """)
        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(self.ai_combo)
        sf_layout.addLayout(ai_layout)
        
        # OCR Language dropdown
        lang_layout = QVBoxLayout()
        lang_layout.setSpacing(8)
        lang_title = QLabel("OCR Parsing Language")
        lang_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English (US/UK)", "Spanish (Español)", "French (Français)", "German (Deutsch)"])
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                padding: 10px 14px;
                color: #0F172A;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                selection-background-color: #2563EB;
                selection-color: #FFFFFF;
            }
        """)
        lang_layout.addWidget(lang_title)
        lang_layout.addWidget(self.lang_combo)
        sf_layout.addLayout(lang_layout)
        
        # Advanced options layout
        opts_layout = QVBoxLayout()
        opts_layout.setSpacing(12)
        opts_title = QLabel("Advanced Verification Rules")
        opts_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569; margin-top: 10px;")
        opts_layout.addWidget(opts_title)
        
        self.dup_cb = QCheckBox("Enable automatic duplicate transaction flagging")
        self.dup_cb.setChecked(True)
        self.email_cb = QCheckBox("Auto-email PDF statement reports on export completion")
        self.sound_cb = QCheckBox("Enable sound alerts on statement parsing completion")
        self.sound_cb.setChecked(True)
        
        opts_layout.addWidget(self.dup_cb)
        opts_layout.addWidget(self.email_cb)
        opts_layout.addWidget(self.sound_cb)
        sf_layout.addLayout(opts_layout)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        save_btn = PrimaryButton("Save Configuration")
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(lambda: self.show_coming_soon("Save Config"))
        
        reset_btn = SecondaryButton("Reset Default")
        reset_btn.setFixedWidth(120)
        reset_btn.clicked.connect(lambda: self.show_coming_soon("Reset Default"))
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        sf_layout.addLayout(btn_layout)
        
        scroll_layout.addWidget(settings_frame)
        scroll_area.setWidget(scroll_content)
        page_layout.addWidget(scroll_area)
        
        page_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.page_stack.addWidget(page)


