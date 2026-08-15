import os
import sys
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QStackedWidget, QScrollArea, QGridLayout, QFrame, 
                             QSpacerItem, QSizePolicy, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLineEdit, QPushButton,
                             QComboBox, QCheckBox, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

class DBQueryWorker(QThread):
    result_ready = pyqtSignal(object)

    def __init__(self, query_fn, parent=None):
        super().__init__(parent)
        self.query_fn = query_fn

    def run(self):
        try:
            res = self.query_fn()
            self.result_ready.emit(res)
        except Exception as e:
            print(f"DBQueryWorker error: {e}")
            self.result_ready.emit(None)
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
        
        # Create the main dashboard overview page immediately (index 0)
        self.create_main_dashboard_page()
        
        # Add placeholders for the other 12 pages
        for _ in range(12):
            placeholder = QWidget()
            placeholder.setProperty("is_placeholder", True)
            self.page_stack.addWidget(placeholder)
        
        right_layout.addWidget(self.page_stack)
        layout.addWidget(right_container)

    def ensure_page_loaded(self, key):
        """Lazily instantiates the sub-page if it is currently a placeholder QWidget."""
        mapping = {
            "dashboard": 0,
            "upload": 1,
            "ai_auditor": 2,
            "ai_report": 2,
            "history": 3,
            "reports": 4,
            "settings": 5,
            "generate_excel": 6,
            "duplicate_finder": 8,
            "email_history": 9,
            "ai_chatbot": 10,
            "notifications": 11,
            "tally": 12
        }
        if key not in mapping:
            return
        idx = mapping[key]
        
        current_widget = self.page_stack.widget(idx)
        # Check if the widget at idx is a basic QWidget (placeholder) rather than a specialized sub-page widget subclass
        if current_widget and current_widget.property("is_placeholder"):
            # Load and instantiate target widget
            if key == "upload":
                from ui.upload_statement import UploadStatementWidget
                self.upload_widget = UploadStatementWidget(self)
                self.upload_widget.processingCompleted.connect(self.update_dashboard_stats)
                new_widget = self.upload_widget
            elif key in ["ai_auditor", "ai_report"]:
                from ui.ai_report import AIReportWidget
                self.ai_report_widget = AIReportWidget(self)
                self.ai_auditor_widget = self.ai_report_widget
                new_widget = self.ai_report_widget
            elif key == "ai_chatbot":
                from ui.ai_chatbot import AIChatbotWidget
                self.ai_chatbot_widget = AIChatbotWidget(self)
                new_widget = self.ai_chatbot_widget
            elif key == "history":
                new_widget = self.instantiate_history_page()
            elif key == "reports":
                new_widget = self.instantiate_reports_page()
            elif key == "settings":
                from settings.settings_window import SettingsWindow
                from settings.settings_controller import SettingsController
                self.settings_window = SettingsWindow(self)
                self.settings_controller = SettingsController(self.settings_window)
                new_widget = self.settings_window
            elif key == "generate_excel":
                from ui.generate_excel import GenerateExcelWidget
                self.generate_excel_widget = GenerateExcelWidget(self)
                new_widget = self.generate_excel_widget
            elif key == "duplicate_finder":
                from ui.duplicate_finder import DuplicateFinderWidget
                self.duplicate_finder_widget = DuplicateFinderWidget(self)
                self.duplicate_finder_widget.closed.connect(lambda: self.switch_dashboard_page("dashboard"))
                new_widget = self.duplicate_finder_widget
            elif key == "email_history":
                from ui.email_history_page import EmailHistoryPage
                self.email_history_widget = EmailHistoryPage(self)
                new_widget = self.email_history_widget
            elif key == "notifications":
                from ui.notifications_page import NotificationsPageWidget
                self.notifications_page_widget = NotificationsPageWidget(self)
                new_widget = self.notifications_page_widget
            elif key == "tally":
                from ui.tally_export import TallyExportWidget
                self.tally_export_widget = TallyExportWidget(self)
                new_widget = self.tally_export_widget
            else:
                return
            
            # Replace placeholder in the stacked widget
            self.page_stack.removeWidget(current_widget)
            current_widget.deleteLater()
            self.page_stack.insertWidget(idx, new_widget)

    def switch_dashboard_page(self, key):
        """Switches the sub-page stacked widget index based on the clicked sidebar option."""
        mapping = {
            "dashboard": 0,
            "upload": 1,
            "ai_auditor": 2,
            "ai_report": 2,
            "history": 3,
            "reports": 4,
            "settings": 5,
            "generate_excel": 6,
            "duplicate_finder": 8,
            "email_history": 9,
            "ai_chatbot": 10,
            "notifications": 11,
            "tally": 12
        }
        if key in mapping:
            self.ensure_page_loaded(key)
            self.page_stack.setCurrentIndex(mapping[key])
            
            # Sync sidebar checked state if called programmatically
            self.sidebar.set_active_page(key)

            if key == "history":
                self.load_history_table()
            elif key in ["ai_auditor", "ai_report"]:
                if hasattr(self, "ai_report_widget") and self.ai_report_widget:
                    self.ai_report_widget.load_history_dropdown()
            elif key == "ai_chatbot":
                if hasattr(self, "ai_chatbot_widget") and self.ai_chatbot_widget:
                    self.ai_chatbot_widget.load_history_dropdown()
            elif key == "generate_excel":
                self.generate_excel_widget.load_recent_generated_sheets()
            elif key == "duplicate_finder":
                self.duplicate_finder_widget.load_history_dropdown()
            elif key == "email_history":
                self.email_history_widget.load_email_history()
            elif key == "notifications":
                if hasattr(self, "notifications_page_widget") and self.notifications_page_widget:
                    self.notifications_page_widget.load_user_notifications()
            elif key == "tally":
                self.tally_export_widget.load_statements_dropdown()
            elif key == "settings":
                if hasattr(self, "settings_window") and self.settings_window:
                    self.settings_window.sync_user_profile_directly()
                if hasattr(self, "settings_controller") and self.settings_controller:
                    self.settings_controller.load_user_settings()

    def switch_to_upload_with_preset(self, flow):
        """Pre-sets the format selection on the upload widget before switching pages."""
        self.ensure_page_loaded("upload")
        if hasattr(self, "upload_widget"):
            self.upload_widget.target_flow_preset = flow
        self.switch_dashboard_page("upload")

    def set_user_profile(self, user_details):
        """Updates the dashboard greeting and topbar initials avatar with user details."""
        full_name = user_details.get("name", "User")
        profile_color = user_details.get("profile_color", "#0037b0")
        
        # Update TopBar details
        if hasattr(self, "topbar") and self.topbar is not None:
            self.topbar.update_profile(full_name, profile_color)
            
        # Update Welcome Greeting first name
        first_name = full_name.split()[0] if full_name.strip() else "User"
        if hasattr(self, "welcome_lbl") and self.welcome_lbl is not None:
            self.welcome_lbl.setText(f"Welcome Back, {first_name}!")

        if hasattr(self, "dashboard_web_view") and self.dashboard_web_view is not None:
            script = f"var el = document.getElementById('welcome-title'); if (el) el.textContent = 'Welcome Back, {first_name}!';"
            self.dashboard_web_view.page().runJavaScript(script)
            
        # Load and apply user settings
        if hasattr(self, "settings_controller") and self.settings_controller is not None:
            self.settings_controller.load_user_settings()
            from settings.settings_service import SettingsService
            SettingsService.apply_settings_instantly(self.settings_controller.model.to_dict())
        else:
            from settings.settings_service import SettingsService
            settings_dict = SettingsService.load_settings(user_details)
            if settings_dict:
                SettingsService.apply_settings_instantly(settings_dict)
            
        # Refresh dashboard stats dynamically
        self.update_dashboard_stats()
        self.load_history_table()

    def _safe_run_query(self, query_fn, callback_fn):
        worker = DBQueryWorker(query_fn, self)
        if not hasattr(self, "_active_workers"):
            self._active_workers = []
        self._active_workers.append(worker)
        
        def handle_result(res):
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            if res is not None:
                callback_fn(res)
                
        worker.result_ready.connect(handle_result)
        worker.start()

    def update_dashboard_stats(self):
        """Fetches dynamic metrics from HistoryService and updates dashboard labels and HTML stats."""
        from utils.user_session import UserSession
        
        user = UserSession.get_current_user()
        user_id = user["id"] if user else None
        if not user_id:
            return
            
        def db_query():
            from services.history_service import HistoryService
            return HistoryService.get_stats(user_id)
            
        def db_callback(stats):
            if hasattr(self, "stats_processed_lbl") and self.stats_processed_lbl is not None:
                self.stats_processed_lbl.setText(str(stats["processed"]))
            if hasattr(self, "stats_verified_lbl") and self.stats_verified_lbl is not None:
                self.stats_verified_lbl.setText(f"{stats['verified']:,}")
            if hasattr(self, "stats_exported_lbl") and self.stats_exported_lbl is not None:
                self.stats_exported_lbl.setText(str(stats["exported"]))

            if hasattr(self, "dashboard_web_view") and self.dashboard_web_view is not None:
                script = f"""
                var p = document.getElementById('stat-processed'); if (p) p.textContent = '{stats["processed"]}';
                var v = document.getElementById('stat-verified'); if (v) v.textContent = '{stats["verified"]:,}';
                var e = document.getElementById('stat-exported'); if (e) e.textContent = '{stats["exported"]}';
                """
                self.dashboard_web_view.page().runJavaScript(script)
                
            if hasattr(self, "update_recent_activity_ui"):
                self.update_recent_activity_ui(user_id)

        self._safe_run_query(db_query, db_callback)

    def update_recent_activity_ui(self, user_id):
        """Rebuilds the Recent Activity list widgets dynamically for HTML dashboard."""
        if not user_id:
            return
            
        def db_query():
            from services.history_service import HistoryService
            return HistoryService.get_recent_activity(user_id, limit=5)
            
        def db_callback(recent):
            import json
            if hasattr(self, "dashboard_web_view") and self.dashboard_web_view is not None:
                formatted_recent = []
                for item in recent:
                    upload_dt = item.get("upload_date", "")
                    if hasattr(upload_dt, "isoformat"):
                        upload_dt = upload_dt.isoformat()
                    formatted_recent.append({
                        "id": str(item.get("id", "")),
                        "file_name": item.get("file_name", "Statement.pdf"),
                        "bank_name": item.get("bank_name", "Unknown Bank"),
                        "upload_date": str(upload_dt)
                    })
                json_str = json.dumps(formatted_recent)
                script = f"""
                var listEl = document.getElementById('activity-list');
                var clearAllBtn = document.getElementById('btn-clear-all-activity');
                if (listEl) {{
                    listEl.innerHTML = '';
                    var items = {json_str};
                    if (!items || items.length === 0) {{
                        if (clearAllBtn) clearAllBtn.style.display = 'none';
                        listEl.innerHTML = '<p style="color:#64748B;font-size:13px;padding:8px 0;">No recent statement activity recorded.</p>';
                    }} else {{
                        if (clearAllBtn) clearAllBtn.style.display = 'inline-block';
                        items.forEach(function(item) {{
                            var div = document.createElement('div');
                            div.className = 'activity-item';
                            div.innerHTML = '<span class="activity-bullet">✓</span>' +
                                '<div class="activity-info">' +
                                    '<span class="activity-filename">' + (item.file_name || 'Statement.pdf') + '</span>' +
                                    '<span class="activity-sub">' + (item.bank_name || 'Unknown Bank') + '</span>' +
                                '</div>' +
                                '<button type="button" class="btn-delete-activity" onclick="event.stopPropagation(); sendAppCommand(\\'dash_clear_activity_item\\', \\'' + item.id + '\\')" title="Delete activity entry">✕</button>';
                            listEl.appendChild(div);
                        }});
                    }}
                }}
                """
                self.dashboard_web_view.page().runJavaScript(script)

        self._safe_run_query(db_query, db_callback)

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
        """Dashboard overview showing metrics, module card shortcuts, and recent activity via HTML+CSS."""
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtCore import QUrl, Qt
        
        self.dashboard_web_view = QWebEngineView(self)
        self.dashboard_web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        # Connect IPC Listener
        self.dashboard_web_view.titleChanged.connect(self.handle_dashboard_title_changed)
        
        # Load HTML
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, "web", "dashboard.html")
        if os.path.exists(html_path):
            self.dashboard_web_view.setUrl(QUrl.fromLocalFile(html_path))
            self.dashboard_web_view.loadFinished.connect(self._on_dashboard_html_loaded)
        else:
            print(f"Error: Dashboard HTML file not found at {html_path}")

        # Dummy fallback objects for 100% backward compatibility
        self.cards = []
        self.welcome_lbl = QLabel("Welcome Back, User!")
        self.sub_lbl = QLabel("")
        self.stats_processed_lbl = QLabel("0")
        self.stats_verified_lbl = QLabel("0")
        self.stats_exported_lbl = QLabel("0")
        self.activity_card = QFrame()
        self.activity_layout = QVBoxLayout(self.activity_card)
        self.card1 = QFrame()
        self.card2 = QFrame()
        self.card3 = QFrame()

        self.page_stack.addWidget(self.dashboard_web_view)

    def _on_dashboard_html_loaded(self, success):
        """Called when web/dashboard.html finishes loading inside QWebEngineView."""
        if success:
            from utils.user_session import UserSession
            user = UserSession.get_current_user()
            if user:
                first_name = user.get("name", "User").split()[0] if user.get("name", "").strip() else "User"
                self.dashboard_web_view.page().runJavaScript(f"var el = document.getElementById('welcome-title'); if (el) el.textContent = 'Welcome Back, {first_name}!';")
            self.update_dashboard_stats()
            from utils.theme_manager import ThemeManager
            theme = ThemeManager.get_theme()
            script = f"if ('{theme}' === 'dark') document.body.classList.add('dark-mode'); else document.body.classList.remove('dark-mode');"
            self.dashboard_web_view.page().runJavaScript(script)

    def handle_dashboard_title_changed(self, title: str):
        """Processes document.title IPC commands sent from JavaScript inside Dashboard HTML."""
        if not title or not title.startswith("app-cmd:"):
            return
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._process_dashboard_title_changed(title))

    def _process_dashboard_title_changed(self, title: str):
        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        payload = parts[2] if len(parts) > 2 else ""

        if cmd == "dash_module":
            key = payload.strip().lower()
            if key == "upload":
                self.switch_to_upload_with_preset("excel")
            elif key in ["generate_excel", "ai_auditor", "ai_report", "ai_chatbot", "duplicate_finder", "history", "email_history", "notifications", "tally"]:
                self.switch_dashboard_page(key)
            elif key in ["gst", "gst_report"]:
                self.show_coming_soon("GST Report")
            else:
                self.show_coming_soon(payload)
        elif cmd == "dash_clear_activity_item":
            record_id = payload.strip()
            if record_id:
                from services.history_service import HistoryService
                HistoryService.delete_record(record_id)
                self.update_dashboard_stats()
        elif cmd == "dash_clear_all_activity":
            from utils.user_session import UserSession
            user = UserSession.get_current_user()
            if user:
                from services.history_service import HistoryService
                HistoryService.clear_all_recent_activity(user.get("id"))
                self.update_dashboard_stats()

    def create_upload_page(self):
        """Creates the interactive PDF Upload Statement module."""
        from ui.upload_statement import UploadStatementWidget
        self.upload_widget = UploadStatementWidget(self)
        self.upload_widget.processingCompleted.connect(self.update_dashboard_stats)
        self.page_stack.addWidget(self.upload_widget)

    def create_ai_auditor_page(self):
        """Creates the interactive AI Auditor and recommendations module."""
        from ui.ai_auditor import AIAuditorWidget
        self.ai_auditor_widget = AIAuditorWidget(self)
        self.page_stack.addWidget(self.ai_auditor_widget)

    def create_generate_excel_page(self):
        """Creates the dedicated Generate Excel module."""
        from ui.generate_excel import GenerateExcelWidget
        self.generate_excel_widget = GenerateExcelWidget(self)
        self.page_stack.addWidget(self.generate_excel_widget)

    def create_gst_report_page(self):
        """Creates the GST Report module."""
        from ui.gst_report import GSTReportWidget
        self.gst_report_widget = GSTReportWidget(self)
        self.page_stack.addWidget(self.gst_report_widget)

    def create_duplicate_finder_page(self):
        """Creates the Duplicate Finder module."""
        from ui.duplicate_finder import DuplicateFinderWidget
        self.duplicate_finder_widget = DuplicateFinderWidget(self)
        self.duplicate_finder_widget.closed.connect(lambda: self.switch_dashboard_page("dashboard"))
        self.page_stack.addWidget(self.duplicate_finder_widget)
    def create_email_history_page(self):
        """Creates the Email History page."""
        from ui.email_history_page import EmailHistoryPage
        self.email_history_widget = EmailHistoryPage(self)
        self.page_stack.addWidget(self.email_history_widget)

    def instantiate_history_page(self):
        """History Page presenting actual processed transaction logs."""
        from ui.statement_history_page import StatementHistoryPage
        self.statement_history_widget = StatementHistoryPage(self)
        self.statement_history_widget.recordDeleted.connect(self.update_dashboard_stats)
        return self.statement_history_widget

    def load_history_table(self):
        """Loads actual user-generated statement log history from database/local file."""
        self.ensure_page_loaded("history")
        if hasattr(self, "statement_history_widget") and self.statement_history_widget:
            self.statement_history_widget.load_history_data()

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
        """Displays confirmation dialog and handles deletion of statement log."""
        if not record_id:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to permanently delete this statement log from history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            def db_query():
                from services.history_service import HistoryService
                return HistoryService.delete_record(record_id)
                
            def db_callback(success):
                if success:
                    # Refresh dashboard statistics and history log table list
                    self.update_dashboard_stats()
                    self.load_history_table()
                    QMessageBox.information(self, "Success", "Record deleted successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete the history record.")
                    
            self._safe_run_query(db_query, db_callback)

    def instantiate_reports_page(self):
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
            if r_title == "Duplicate Transaction Log":
                dl_btn.clicked.connect(lambda checked: self.switch_dashboard_page("duplicate_finder"))
            else:
                dl_btn.clicked.connect(lambda checked, t=r_title: self.show_coming_soon(t))
            rc_layout.addWidget(dl_btn)

            # Email Action Button
            email_card_btn = QPushButton("✉ Send Email")
            email_card_btn.setFixedSize(110, 30)
            email_card_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            email_card_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F5F3FF;
                    color: #7C3AED;
                    font-weight: bold;
                    font-size: 12px;
                    border: 1px solid #DDD6FE;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #EDE9FE; }
            """)
            email_card_btn.clicked.connect(lambda checked, t=r_title: self.open_email_composer_for_report(t))
            rc_layout.addWidget(email_card_btn)

            rl_layout.addWidget(r_card)
            
        rl_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        page_layout.addWidget(reports_list)
        return page



    def open_email_composer_for_report(self, report_title):
        """Opens Email Composer dialog for reports page cards."""
        from ui.email_composer_dialog import EmailComposerDialog
        dialog = EmailComposerDialog(
            report_type=report_title,
            parent=self
        )
        dialog.exec()

    def create_settings_page(self):
        """Instantiates the premium MVC Settings view and controller."""
        from settings.settings_window import SettingsWindow
        from settings.settings_controller import SettingsController
        
        self.settings_window = SettingsWindow(self)
        self.settings_controller = SettingsController(self.settings_window)
        self.page_stack.addWidget(self.settings_window)

    def update_theme_styles(self, theme):
        """Updates internal card components and QSS stylesheets to match active theme parameters."""
        theme_clean = theme.lower().strip() if isinstance(theme, str) else "light"
        
        from utils.theme_manager import ThemeManager
        ThemeManager.apply_theme(theme_clean)

        if hasattr(self, "sidebar") and self.sidebar is not None:
            self.sidebar.update_theme_styles(theme_clean)

        if hasattr(self, "topbar") and self.topbar is not None:
            self.topbar.update_theme_icon(theme_clean)

        if hasattr(self, "dashboard_web_view") and self.dashboard_web_view is not None:
            script = f"if ('{theme_clean}' === 'dark') document.body.classList.add('dark-mode'); else document.body.classList.remove('dark-mode');"
            self.dashboard_web_view.page().runJavaScript(script)

        for card in self.cards:
            card.update_theme_style(theme)
            
        if theme == "dark":
            self.card1.setStyleSheet("QFrame#MetricCardBlue { background-color: #1E293B; border: 1px solid #334155; border-top: 4px solid #3B82F6; border-radius: 12px; }")
            self.card2.setStyleSheet("QFrame#MetricCardGreen { background-color: #1E293B; border: 1px solid #334155; border-top: 4px solid #10B981; border-radius: 12px; }")
            self.card3.setStyleSheet("QFrame#MetricCardOrange { background-color: #1E293B; border: 1px solid #334155; border-top: 4px solid #F97316; border-radius: 12px; }")
            self.activity_card.setStyleSheet("QFrame#ActivityCard { background-color: #1E293B; border: 1px solid #334155; border-radius: 12px; }")
        else:
            self.card1.setStyleSheet("QFrame#MetricCardBlue { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #0037b0; border-radius: 12px; }")
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

        if hasattr(self, "ai_report_widget") and self.ai_report_widget is not None:
            self.ai_report_widget.update_theme_style(theme)

        if hasattr(self, "ai_chatbot_widget") and self.ai_chatbot_widget is not None:
            self.ai_chatbot_widget.update_theme_style(theme)

        if hasattr(self, "ai_auditor_widget") and self.ai_auditor_widget is not None and self.ai_auditor_widget != getattr(self, "ai_report_widget", None):
            self.ai_auditor_widget.update_theme_style(theme)

        if hasattr(self, "generate_excel_widget") and self.generate_excel_widget is not None:
            self.generate_excel_widget.update_theme_style(theme)

        if hasattr(self, "tally_export_widget") and self.tally_export_widget is not None:
            self.tally_export_widget.update_theme_style(theme)
        if hasattr(self, "statement_history_widget") and self.statement_history_widget is not None:
            self.statement_history_widget.apply_theme(theme_clean)

        if hasattr(self, "email_history_widget") and self.email_history_widget is not None:
            self.email_history_widget.apply_theme(theme_clean)

        if hasattr(self, "notifications_page_widget") and self.notifications_page_widget is not None:
            self.notifications_page_widget.update_theme_style(theme)

    def update_notification_badge(self):
        """Updates the TopBar unread badge count."""
        if hasattr(self, "topbar") and self.topbar is not None:
            self.topbar.update_notification_badge()

    def reset_screen_data(self):
        """Purges cached dashboard metrics, tables, and HTML elements on user logout."""
        if hasattr(self, "stats_processed_lbl") and self.stats_processed_lbl is not None:
            self.stats_processed_lbl.setText("0")
        if hasattr(self, "stats_verified_lbl") and self.stats_verified_lbl is not None:
            self.stats_verified_lbl.setText("0")
        if hasattr(self, "stats_exported_lbl") and self.stats_exported_lbl is not None:
            self.stats_exported_lbl.setText("0")
            
        if hasattr(self, "dashboard_web_view") and self.dashboard_web_view is not None:
            script = """
            var p = document.getElementById('stat-processed'); if (p) p.textContent = '0';
            var v = document.getElementById('stat-verified'); if (v) v.textContent = '0';
            var e = document.getElementById('stat-exported'); if (e) e.textContent = '0';
            var title = document.getElementById('welcome-title'); if (title) title.textContent = 'Welcome Back';
            """
            self.dashboard_web_view.page().runJavaScript(script)
            
        if hasattr(self, "history_table") and self.history_table is not None:
            self.history_table.setRowCount(0)
            
        if hasattr(self, "duplicate_finder_widget") and self.duplicate_finder_widget is not None:
            if hasattr(self.duplicate_finder_widget, "loaded_statements"):
                self.duplicate_finder_widget.loaded_statements = []
            if hasattr(self.duplicate_finder_widget, "load_history_dropdown"):
                self.duplicate_finder_widget.history_combo.clear()

        if hasattr(self, "ai_auditor_widget") and self.ai_auditor_widget is not None:
            if hasattr(self.ai_auditor_widget, "load_history_dropdown"):
                self.ai_auditor_widget.load_history_dropdown()

# Refactored / updated upload_statement module and service integration


