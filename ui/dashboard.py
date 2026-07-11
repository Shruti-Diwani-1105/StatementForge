import os
import sys
import datetime
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

            if key == "history":
                self.load_history_table()

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
            
        # Load and apply user settings
        if hasattr(self, "settings_controller") and self.settings_controller is not None:
            self.settings_controller.load_user_settings()
            from settings.settings_service import SettingsService
            SettingsService.apply_settings_instantly(self.settings_controller.model.to_dict())
            
        # Refresh dashboard stats dynamically
        self.update_dashboard_stats()
        self.load_history_table()

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
        act_title.setObjectName("ActivityTitle")
        act_title.setStyleSheet("font-size: 16px; font-weight: 700; margin-bottom: 8px;")
        self.activity_layout.addWidget(act_title)

        # Fetch recent items
        from services.history_service import HistoryService
        import datetime
        
        recent = HistoryService.get_recent_activity(user_id, limit=5)
        
        if not recent:
            self.activity_layout.addStretch()
            empty_lbl = QLabel("No recent activity.")
            empty_lbl.setObjectName("ActivityEmptyLabel")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("font-size: 13px; font-weight: 500;")
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
        self.cards = []
        
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
        self.welcome_lbl.setObjectName("WelcomeTitle")
        self.welcome_lbl.setStyleSheet("font-size: 26px; font-weight: 700; letter-spacing: -0.5px;")
        
        self.sub_lbl = QLabel("Here's an overview of your local financial statements parser activities.")
        self.sub_lbl.setObjectName("WelcomeSubtitle")
        self.sub_lbl.setStyleSheet("font-size: 13px;")
        
        header_layout.addWidget(self.welcome_lbl)
        header_layout.addWidget(self.sub_lbl)
        page_layout.addLayout(header_layout)
        
        # 1. Statistics / Metric Cards Row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(24)
        
        # Statements Processed
        self.card1 = QFrame()
        self.card1.setObjectName("MetricCardBlue")
        self.card1.setStyleSheet("QFrame#MetricCardBlue { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #2563EB; border-radius: 12px; }")
        card1_layout = QVBoxLayout(self.card1)
        card1_layout.setContentsMargins(20, 20, 20, 20)
        card1_layout.setSpacing(8)
        t_lbl1 = QLabel("Statements Processed")
        t_lbl1.setObjectName("MetricTitle")
        t_lbl1.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.stats_processed_lbl = QLabel("0")
        self.stats_processed_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #2563EB;")
        card1_layout.addWidget(t_lbl1)
        card1_layout.addWidget(self.stats_processed_lbl)
        metrics_layout.addWidget(self.card1)
        
        # Transactions Verified
        self.card2 = QFrame()
        self.card2.setObjectName("MetricCardGreen")
        self.card2.setStyleSheet("QFrame#MetricCardGreen { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #16A34A; border-radius: 12px; }")
        card2_layout = QVBoxLayout(self.card2)
        card2_layout.setContentsMargins(20, 20, 20, 20)
        card2_layout.setSpacing(8)
        t_lbl2 = QLabel("Transactions Verified")
        t_lbl2.setObjectName("MetricTitle")
        t_lbl2.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.stats_verified_lbl = QLabel("0")
        self.stats_verified_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #16A34A;")
        card2_layout.addWidget(t_lbl2)
        card2_layout.addWidget(self.stats_verified_lbl)
        metrics_layout.addWidget(self.card2)
        
        # Reports Exported
        self.card3 = QFrame()
        self.card3.setObjectName("MetricCardOrange")
        self.card3.setStyleSheet("QFrame#MetricCardOrange { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #EA580C; border-radius: 12px; }")
        card3_layout = QVBoxLayout(self.card3)
        card3_layout.setContentsMargins(20, 20, 20, 20)
        card3_layout.setSpacing(8)
        t_lbl3 = QLabel("Reports Exported")
        t_lbl3.setObjectName("MetricTitle")
        t_lbl3.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.stats_exported_lbl = QLabel("0")
        self.stats_exported_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #EA580C;")
        card3_layout.addWidget(t_lbl3)
        card3_layout.addWidget(self.stats_exported_lbl)
        metrics_layout.addWidget(self.card3)
        
        page_layout.addLayout(metrics_layout)
        
        # Initial population of recent activities
        self.update_dashboard_stats()
        
        # 2. Main content split (Module Grid on left, Recent Activity on right)
        content_split = QHBoxLayout()
        content_split.setSpacing(24)
        
        # Left: Modules Grid Container
        modules_container = QWidget()
        modules_layout = QVBoxLayout(modules_container)
        modules_layout.setContentsMargins(0, 0, 0, 0)
        modules_layout.setSpacing(12)
        
        self.section_title = QLabel("System Modules")
        self.section_title.setObjectName("SectionTitle")
        self.section_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        modules_layout.addWidget(self.section_title)
        
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
            self.cards.append(card)
            
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
        """History Page presenting actual processed transaction logs."""
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
        self.history_table.setHorizontalHeaderLabels(["Upload Date", "File Name", "Bank Name", "Status", "Output Format", "Action"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setStyleSheet("border: none; gridline-color: #F1F5F9;")
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        
        tc_layout.addWidget(self.history_table)
        page_layout.addWidget(table_container)
        
        page_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.page_stack.addWidget(page)

    def load_history_table(self):
        """Loads actual user-generated statement log history from database/local file."""
        from services.history_service import HistoryService
        from utils.user_session import UserSession
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        
        logs = HistoryService.get_history_logs(user_id=user_id)
        
        self.history_table.setRowCount(0)
        self.history_table.setRowCount(len(logs))
        
        from PyQt6.QtGui import QCursor
        
        for row_idx, log in enumerate(logs):
            # 1. Upload Date
            upload_date = log.get("upload_date", "")
            if isinstance(upload_date, str) and "T" in upload_date:
                try:
                    dt = datetime.datetime.fromisoformat(upload_date)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = upload_date.replace("T", " ")[:16]
            elif hasattr(upload_date, "strftime"):
                date_str = upload_date.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = str(upload_date)[:16]
                
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row_idx, 0, date_item)
            
            # 2. File Name
            pdf_path = log.get("pdf_path", "")
            file_name = os.path.basename(pdf_path) if pdf_path else "Unknown.pdf"
            file_item = QTableWidgetItem(file_name)
            file_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row_idx, 1, file_item)
            
            # 3. Bank Name
            bank_name = log.get("bank_name", "Unknown Bank")
            bank_item = QTableWidgetItem(bank_name)
            bank_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row_idx, 2, bank_item)
            
            # 4. Status (Processing, Completed, Failed, Cancelled)
            status = log.get("status", "Completed")
            status_colors = {
                "Completed": "#16A34A",
                "Processing": "#2563EB",
                "Failed": "#EF4444",
                "Cancelled": "#4B5563"
            }
            color = status_colors.get(status, "#4B5563")
            
            status_container = QWidget()
            sc_layout = QHBoxLayout(status_container)
            sc_layout.setContentsMargins(4, 4, 4, 4)
            sc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            status_badge = QLabel(status)
            status_badge.setFixedSize(100, 22)
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
            self.history_table.setCellWidget(row_idx, 3, status_container)
            
            # 5. Output Format
            out_fmt = log.get("output_format", "Excel") if status == "Completed" else "-"
            fmt_item = QTableWidgetItem(out_fmt)
            fmt_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row_idx, 4, fmt_item)
            
            # 6. Action
            action_container = QWidget()
            ac_layout = QHBoxLayout(action_container)
            ac_layout.setContentsMargins(4, 4, 4, 4)
            ac_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if status == "Completed":
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
                excel_path = log.get("excel_path", "")
                view_btn.clicked.connect(lambda checked, ep=excel_path: self.open_history_file(ep))
                ac_layout.addWidget(view_btn)
            else:
                act_lbl = QLabel(status)
                act_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 500;")
                ac_layout.addWidget(act_lbl)
                
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

    def create_reports_page(self):
        """Reports Page presenting downloadable report options."""
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
        
        # Downloadable Cards List - Full Width Layout
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
        
        page_layout.addWidget(reports_list)
        self.page_stack.addWidget(page)

    def create_settings_page(self):
        """Instantiates the premium MVC Settings view and controller."""
        from settings.settings_window import SettingsWindow
        from settings.settings_controller import SettingsController
        
        self.settings_window = SettingsWindow(self)
        self.settings_controller = SettingsController(self.settings_window)
        self.page_stack.addWidget(self.settings_window)

    def update_theme_styles(self, theme):
        """Updates internal card components to match active theme stylesheet parameters."""
        for card in self.cards:
            card.update_theme_style(theme)
            
        if theme == "dark":
            self.card1.setStyleSheet("QFrame#MetricCardBlue { background-color: #1E293B; border: 1px solid #334155; border-top: 4px solid #3B82F6; border-radius: 12px; }")
            self.card2.setStyleSheet("QFrame#MetricCardGreen { background-color: #1E293B; border: 1px solid #334155; border-top: 4px solid #10B981; border-radius: 12px; }")
            self.card3.setStyleSheet("QFrame#MetricCardOrange { background-color: #1E293B; border: 1px solid #334155; border-top: 4px solid #F97316; border-radius: 12px; }")
            self.activity_card.setStyleSheet("QFrame#ActivityCard { background-color: #1E293B; border: 1px solid #334155; border-radius: 12px; }")
        else:
            self.card1.setStyleSheet("QFrame#MetricCardBlue { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #2563EB; border-radius: 12px; }")
            self.card2.setStyleSheet("QFrame#MetricCardGreen { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #16A34A; border-radius: 12px; }")
            self.card3.setStyleSheet("QFrame#MetricCardOrange { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #EA580C; border-radius: 12px; }")
            self.activity_card.setStyleSheet("QFrame#ActivityCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }")

        # Dynamically update labels and frames to prevent text visibility and section color bugs in dark mode
        for label in self.findChildren(QLabel):
            style = label.styleSheet()
            if theme == "dark" and "color: #0F172A" in style:
                label.setStyleSheet(style.replace("color: #0F172A", "color: #F8FAFC"))
            elif theme == "light" and "color: #F8FAFC" in style:
                label.setStyleSheet(style.replace("color: #F8FAFC", "color: #0F172A"))
                
        for frame in self.findChildren(QFrame):
            if frame.objectName() in ["CardFrame", "SettingCardFrame", "SidebarFrame", "TopBar"]:
                continue
            style = frame.styleSheet()
            if theme == "dark" and "background-color: #FFFFFF" in style:
                new_style = style.replace("background-color: #FFFFFF", "background-color: #1E293B")
                new_style = new_style.replace("border: 1px solid #E2E8F0", "border: 1px solid #334155")
                frame.setStyleSheet(new_style)
            elif theme == "light" and "background-color: #1E293B" in style:
                new_style = style.replace("background-color: #1E293B", "background-color: #FFFFFF")
                new_style = new_style.replace("border: 1px solid #334155", "border: 1px solid #E2E8F0")
                frame.setStyleSheet(new_style)
            
        if hasattr(self, "settings_controller") and self.settings_controller is not None:
            self.settings_controller.model.set("app_theme", theme.capitalize())
            self.settings_controller.model.set("theme", theme.capitalize())
            
        if hasattr(self, "settings_window") and self.settings_window is not None:
            self.settings_window.update_theme_style(theme)

        if hasattr(self, "upload_widget") and self.upload_widget is not None:
            self.upload_widget.update_theme_style(theme)


