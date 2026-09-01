import os
import sys
import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
from ui.html_screen_wrapper import HtmlScreenWrapper
from services.statement_service import StatementService
from services.history_service import HistoryService
from utils.user_session import UserSession


class UploadStatementWidget(QWidget):
    """
    Upload Statement module powered strictly by HTML + CSS frontend interface
    integrated via QWebEngineView wrapper with Python backend processing pipeline.
    """
    processingCompleted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.page_count = 0
        self.detected_bank = "Unknown Bank"
        self.doc_type_desc = "Digital PDF"
        self.target_flow_preset = None
        
        self.parsed_payload = None
        self.active_thread = None
        self.post_process_action = "excel"
        self.auto_detect = False

        # Embed HTML + CSS presentation layer
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.html_wrapper = HtmlScreenWrapper("web/upload_statement.html", self)
        layout.addWidget(self.html_wrapper)

        # Connect document title / WebBridge IPC commands
        self.html_wrapper.web_view.titleChanged.connect(self.handle_web_commands)

    def update_theme_style(self, theme: str = "light"):
        """Updates HTML UI theme styling ('light' or 'dark')."""
        theme_str = theme.lower().strip() if isinstance(theme, str) else "light"
        if theme_str == "dark":
            self.html_wrapper.eval_js("document.body.classList.add('dark-mode');")
        else:
            self.html_wrapper.eval_js("document.body.classList.remove('dark-mode');")

    def handle_web_commands(self, title: str):
        """Dispatches commands sent from JavaScript UI via document.title IPC."""
        if not title or not title.startswith("app-cmd:"):
            return

        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        raw_payload = parts[2] if len(parts) > 2 else ""

        if cmd in ["upload_browse", "upload_browse_csv", "upload_browse_json", "upload_browse_excel"]:
            try:
                import json
                data = json.loads(raw_payload) if raw_payload else {}
                self.auto_detect = data.get("autoDetect", False)
            except Exception:
                pass
                
            if cmd == "upload_browse_csv":
                self.post_process_action = "csv"
            elif cmd == "upload_browse_json":
                self.post_process_action = "json"
            elif cmd == "upload_browse_excel":
                self.post_process_action = "excel"
                
            self.browse_pdf_file()
        elif cmd == "upload_file_selected":
            try:
                import json
                data = json.loads(raw_payload)
                self.auto_detect = data.get("autoDetect", True)
            except Exception:
                pass
        elif cmd == "upload_cancel":
            self.cancel_processing()
        elif cmd == "upload_module_click":
            try:
                import json
                data = json.loads(raw_payload)
                module_key = data.get("module", "excel")
                self.handle_module_selection(module_key)
            except Exception:
                pass

    def browse_pdf_file(self):
        """Opens native file picker for selecting a PDF statement."""
        from PyQt6.QtCore import QStandardPaths
        doc_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Bank Statement PDF", doc_dir, "PDF Files (*.pdf)"
        )
        if path:
            self.start_validation_flow(path)

    # ==========================================
    # BACKEND WORKFLOW STEP 1: VALIDATION & BANK DETECTION
    # ==========================================
    def start_validation_flow(self, file_path):
        """Executes PDF layout validation and bank metadata detector."""
        self.file_path = file_path

        def on_started():
            self.html_wrapper.eval_js("if(typeof startProcessingUI==='function') startProcessingUI('" + os.path.basename(file_path).replace("'", "\\'") + "');")

        def on_finished(meta):
            self.file_path = meta["file_path"]
            self.page_count = meta["page_count"]
            self.detected_bank = meta["bank_name"]
            
            from services.pdf_reader import PDFReader
            is_digital = PDFReader.is_digital_pdf(self.file_path)
            self.doc_type_desc = "Digital PDF" if is_digital else "Scanned PDF"

            bank_str = self.detected_bank.replace("'", "\\'")
            doc_str = self.doc_type_desc.replace("'", "\\'")
            self.html_wrapper.eval_js(f"if(document.getElementById('procBankName')) document.getElementById('procBankName').innerText = '{bank_str}';")
            self.html_wrapper.eval_js(f"if(document.getElementById('procPageCount')) document.getElementById('procPageCount').innerText = '{self.page_count} pages ({doc_str})';")

            selected_flow = getattr(self, "target_flow_preset", "excel") or "excel"
            if hasattr(self, "target_flow_preset") and self.target_flow_preset:
                self.target_flow_preset = None

            if self.auto_detect:
                self.start_processing_flow(target_flow=selected_flow)
            else:
                info_str = f"Bank: {self.detected_bank} | Pages: {self.page_count} ({self.doc_type_desc})"
                file_str = os.path.basename(self.file_path).replace("'", "\\'")
                self.html_wrapper.eval_js(f"document.getElementById('choiceFileName').innerText = '📂 {file_str}';")
                self.html_wrapper.eval_js(f"document.getElementById('choiceFileInfo').innerText = '{info_str}';")
                self.html_wrapper.eval_js("switchView('view-choice');")

        def on_error(err):
            escaped_err = str(err).replace("'", "\\'").replace("\n", " ")
            self.html_wrapper.eval_js(f"alert('Validation Error: {escaped_err}'); resetToUpload();")

        self.active_thread = StatementService.start_validate(
            file_path, on_started, on_finished, on_error
        )

    def handle_module_selection(self, module_key):
        """Handles choice card button actions."""
        if module_key in ["excel", "gst", "csv", "json"]:
            self.post_process_action = module_key
            self.start_processing_flow(target_flow=module_key)
        elif module_key == "tally":
            self.post_process_action = "tally"
            self.start_processing_flow(target_flow="excel")
        elif module_key == "ai_report":
            self.post_process_action = "ai_report"
            self.start_processing_flow(target_flow="excel")
        elif module_key == "history":
            p = self.parent()
            while p:
                if hasattr(p, "switch_dashboard_page"):
                    p.switch_dashboard_page("history")
                    break
                p = p.parent()
        elif module_key == "email":
            from ui.email_composer_dialog import EmailComposerDialog
            att_path = getattr(self, "file_path", None)
            dialog = EmailComposerDialog(
                report_type="Bank Statement",
                default_attachment=att_path,
                bank_name=getattr(self, "detected_bank", ""),
                parent=self
            )
            dialog.exec()

    # ==========================================
    # BACKEND WORKFLOW STEP 2: PARSE & COMPILE EXCEL/CSV/JSON
    # ==========================================
    def start_processing_flow(self, target_flow="excel"):
        """Launches the backend extraction and parsing engine thread."""
        self.target_flow = target_flow
        
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        self.history_record_id = HistoryService.create_record(
            user_id=user_id,
            pdf_path=self.file_path,
            bank_name=self.detected_bank,
            status="Processing",
            output_format=target_flow.upper()
        )

        def on_started():
            file_str = os.path.basename(self.file_path).replace("'", "\\'") if self.file_path else "Statement"
            bank_str = self.detected_bank.replace("'", "\\'")
            doc_str = getattr(self, "doc_type_desc", "PDF").replace("'", "\\'")
            self.html_wrapper.eval_js("switchView('view-processing');")
            self.html_wrapper.eval_js(f"if(document.getElementById('procBankName')) document.getElementById('procBankName').innerText = '{bank_str}';")
            self.html_wrapper.eval_js(f"if(document.getElementById('procPageCount')) document.getElementById('procPageCount').innerText = '{self.page_count} pages ({doc_str})';")

        def on_step_started(idx):
            msg = "Pre-processing document..." if idx == 1 else ("Reading layout pages..." if idx == 2 else "Configuring OCR alignments...")
            escaped = msg.replace("'", "\\'")
            self.html_wrapper.eval_js(f"if(document.getElementById('procStatusText')) document.getElementById('procStatusText').innerText = '{escaped}';")

        def on_step_completed(idx, status):
            pass

        def on_progress(cur, tot, tx_count):
            pct = int(cur / tot * 100) if tot > 0 else 0
            self.html_wrapper.eval_js(f"if(document.getElementById('progressBar')) document.getElementById('progressBar').style.width = '{pct}%';")
            self.html_wrapper.eval_js(f"if(document.getElementById('procStatusText')) document.getElementById('procStatusText').innerText = 'Processing Page {cur} of {tot}...';")
            self.html_wrapper.eval_js(f"if(document.getElementById('procTxCount')) document.getElementById('procTxCount').innerText = '{tx_count} records';")

        def on_finished(payload):
            self.parsed_payload = payload
            if not payload or not payload.get("transactions"):
                self.reset_to_upload()
                if hasattr(self, "history_record_id"):
                    HistoryService.update_record_status(self.history_record_id, status="Failed")
                self.html_wrapper.eval_js("alert('No transactions could be extracted from this PDF statement.');")
                return

            action = getattr(self, "post_process_action", "excel")
            if action == "ai_report":
                self.generate_excel_in_background(payload)
                p = self.parent()
                dashboard = None
                while p:
                    if hasattr(p, "page_stack") and hasattr(p, "ai_auditor_widget"):
                        dashboard = p
                        break
                    p = p.parent()
                if dashboard:
                    dashboard.ai_auditor_widget.set_active_statement(payload)
                    dashboard.switch_dashboard_page("ai_auditor")
                    dashboard.ai_auditor_widget.run_ai_task("report")
                self.reset_to_upload()
            elif action == "csv":
                self.export_csv_flow(payload)
            elif action == "json":
                self.export_json_flow(payload)
            else:
                self.generate_excel_flow()

        def on_error(err):
            self.reset_to_upload()
            if hasattr(self, "history_record_id"):
                HistoryService.update_record_status(self.history_record_id, status="Failed")
            escaped_err = str(err).replace("'", "\\'").replace("\n", " ")
            self.html_wrapper.eval_js(f"alert('{escaped_err}');")

        self.active_thread = StatementService.start_parse(
            self.file_path, on_started, on_step_started, on_step_completed, on_progress, on_finished, on_error
        )

    def export_csv_flow(self, payload):
        """Prompts native save dialog and exports parsed statement payload to CSV."""
        if not payload or not payload.get("transactions"):
            self.reset_to_upload()
            self.html_wrapper.eval_js("alert('No valid transactions found in this statement for CSV export.');")
            return

        from PyQt6.QtCore import QStandardPaths
        doc_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        
        bank_clean = "".join(c for c in self.detected_bank if c.isalnum()) or "Bank"
        date_stamp = datetime.datetime.now().strftime("%Y-%m-%d")
        default_filename = f"StatementForge_{bank_clean}_{date_stamp}.csv"
        default_path = os.path.join(doc_dir, default_filename)

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Statement as CSV", default_path, "CSV Files (*.csv)"
        )

        if not save_path:
            self.reset_to_upload()
            return

        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        record_id = getattr(self, "history_record_id", None)

        def on_started():
            pass

        def on_finished(csv_path):
            if hasattr(self, "history_record_id"):
                HistoryService.update_record_completed(
                    record_id=self.history_record_id,
                    excel_path=csv_path,
                    period=self.parsed_payload.get("period", "Unknown"),
                    processing_time=self.parsed_payload.get("processing_time", 0),
                    total_transactions=len(self.parsed_payload.get("transactions", []))
                )
            
            tx_len = len(self.parsed_payload.get("transactions", []))
            time_str = datetime.datetime.now().strftime("%H:%M")
            file_name = os.path.basename(self.file_path).replace("'", "\\'")
            bank_name = self.detected_bank.replace("'", "\\'")
            
            try:
                from services.notification_service import NotificationService
                NotificationService.create_notification(
                    user_id=user_id,
                    category="parsing_export",
                    title="CSV Export Completed",
                    message=f"CSV exported successfully to {os.path.basename(csv_path)} ({tx_len} transactions).",
                    action_type="view_statement"
                )
            except Exception as e:
                print(f"CSV Export notification error: {e}")

            self.html_wrapper.eval_js(f"addRecentActivity('{bank_name}', '{file_name}', {tx_len}, '{time_str}', 'Completed');")
            self.processingCompleted.emit()
            self.reset_to_upload()
            
            ans = QMessageBox.question(
                self,
                "CSV Export Completed",
                f"✓ CSV statement exported successfully:\n{os.path.basename(csv_path)}\n\nWould you like to send this CSV file via Email / Google Mail?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if ans == QMessageBox.StandardButton.Yes:
                from ui.email_composer_dialog import EmailComposerDialog
                dialog = EmailComposerDialog(
                    report_type="Bank Statement CSV Export",
                    default_attachment=csv_path,
                    bank_name=self.detected_bank,
                    parent=self
                )
                dialog.exec()

        def on_error(err):
            self.reset_to_upload()
            escaped_err = str(err).replace("'", "\\'").replace("\n", " ")
            self.html_wrapper.eval_js(f"alert('CSV export failed: {escaped_err}');")

        StatementService.start_generate_csv(
            user_id, payload, save_path, record_id, on_started, on_finished, on_error
        )

    def export_json_flow(self, payload):
        """Prompts native save dialog and exports parsed statement payload to JSON."""
        if not payload or not payload.get("transactions"):
            self.reset_to_upload()
            self.html_wrapper.eval_js("alert('No valid transactions found in this statement for JSON export.');")
            return

        from PyQt6.QtCore import QStandardPaths
        doc_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        
        bank_clean = "".join(c for c in self.detected_bank if c.isalnum()) or "Bank"
        date_stamp = datetime.datetime.now().strftime("%Y-%m-%d")
        default_filename = f"StatementForge_{bank_clean}_{date_stamp}.json"
        default_path = os.path.join(doc_dir, default_filename)

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Statement as JSON", default_path, "JSON Files (*.json)"
        )

        if not save_path:
            self.reset_to_upload()
            return

        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        record_id = getattr(self, "history_record_id", None)

        def on_started():
            pass

        def on_finished(json_path):
            if hasattr(self, "history_record_id"):
                HistoryService.update_record_completed(
                    record_id=self.history_record_id,
                    excel_path=json_path,
                    period=self.parsed_payload.get("period", "Unknown"),
                    processing_time=self.parsed_payload.get("processing_time", 0),
                    total_transactions=len(self.parsed_payload.get("transactions", []))
                )
            
            tx_len = len(self.parsed_payload.get("transactions", []))
            time_str = datetime.datetime.now().strftime("%H:%M")
            file_name = os.path.basename(self.file_path).replace("'", "\\'")
            bank_name = self.detected_bank.replace("'", "\\'")
            
            try:
                from services.notification_service import NotificationService
                NotificationService.create_notification(
                    user_id=user_id,
                    category="parsing_export",
                    title="JSON Export Completed",
                    message=f"JSON exported successfully to {os.path.basename(json_path)} ({tx_len} transactions).",
                    action_type="view_statement"
                )
            except Exception as e:
                print(f"JSON Export notification error: {e}")

            self.html_wrapper.eval_js(f"addRecentActivity('{bank_name}', '{file_name}', {tx_len}, '{time_str}', 'Completed');")
            self.processingCompleted.emit()
            self.reset_to_upload()
            
            ans = QMessageBox.question(
                self,
                "JSON Export Completed",
                f"✓ JSON statement exported successfully:\n{os.path.basename(json_path)}\n\nWould you like to send this JSON file via Email / Google Mail?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if ans == QMessageBox.StandardButton.Yes:
                from ui.email_composer_dialog import EmailComposerDialog
                dialog = EmailComposerDialog(
                    report_type="Bank Statement JSON Export",
                    default_attachment=json_path,
                    bank_name=self.detected_bank,
                    parent=self
                )
                dialog.exec()

        def on_error(err):
            self.reset_to_upload()
            escaped_err = str(err).replace("'", "\\'").replace("\n", " ")
            self.html_wrapper.eval_js(f"alert('JSON export failed: {escaped_err}');")

        StatementService.start_generate_json(
            user_id, payload, save_path, record_id, on_started, on_finished, on_error
        )

    def generate_excel_flow(self):
        """Writes parsed transactions into Excel workbook."""
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        record_id = getattr(self, "history_record_id", None)

        def on_started():
            pass

        def on_step_started(idx):
            pass

        def on_step_completed(idx, status):
            pass

        def on_finished(excel_path):
            if hasattr(self, "history_record_id"):
                HistoryService.update_record_status(self.history_record_id, status="Completed")
            
            tx_len = len(self.parsed_payload.get("transactions", []))
            time_str = datetime.datetime.now().strftime("%H:%M")
            file_name = os.path.basename(self.file_path).replace("'", "\\'")
            bank_name = self.detected_bank.replace("'", "\\'")
            
            # Auto-create Parsing Completed & Excel Export Notifications
            try:
                from services.notification_service import NotificationService
                NotificationService.create_notification(
                    user_id=user_id,
                    category="parsing_export",
                    title="Statement Parsing Completed",
                    message=f"Your statement '{file_name}' ({bank_name}, {tx_len} transactions) was parsed successfully.",
                    action_type="view_statement"
                )
                NotificationService.create_notification(
                    user_id=user_id,
                    category="parsing_export",
                    title="Excel Export Completed",
                    message=f"Excel workbook generated successfully: {os.path.basename(excel_path)}",
                    action_type="view_statement"
                )
            except Exception as e:
                print(f"UploadStatementWidget: Notification trigger error: {e}")

            self.html_wrapper.eval_js(f"addRecentActivity('{bank_name}', '{file_name}', {tx_len}, '{time_str}', 'Completed');")
            self.processingCompleted.emit()
            
            # Sync Dashboard Stats and TopBar Badge in real time
            p = self.parent()
            while p:
                if hasattr(p, "update_dashboard_stats"):
                    p.update_dashboard_stats()
                if hasattr(p, "update_notification_badge"):
                    p.update_notification_badge()
                p = p.parent()
            action = getattr(self, "post_process_action", "excel")
            self.reset_to_upload()
            
            if action == "tally":
                p = self.parent()
                dashboard = None
                while p:
                    if hasattr(p, "page_stack") and hasattr(p, "tally_export_widget"):
                        dashboard = p
                        break
                    p = p.parent()
                if dashboard:
                    dashboard.switch_dashboard_page("tally")
                    dashboard.tally_export_widget.on_statement_selected_by_path(excel_path)

        def on_error(err):
            self.reset_to_upload()
            if hasattr(self, "history_record_id"):
                HistoryService.update_record_status(self.history_record_id, status="Failed")
            escaped_err = str(err).replace("'", "\\'").replace("\n", " ")
            try:
                from services.notification_service import NotificationService
                NotificationService.create_notification(
                    user_id=user_id,
                    category="parsing_export",
                    title="Parsing Error",
                    message=f"Failed to extract transactions from '{os.path.basename(self.file_path)}'. Error: {escaped_err}"
                )
            except Exception:
                pass
            self.html_wrapper.eval_js(f"alert('{escaped_err}');")

        self.active_thread = StatementService.start_generate_excel(
            user_id, self.parsed_payload, record_id, on_started, on_step_started, on_step_completed, on_finished, on_error
        )

    def generate_excel_in_background(self, payload):
        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"
        record_id = getattr(self, "history_record_id", None)
        StatementService.start_generate_excel(
            user_id, payload, record_id, lambda: None, lambda i: None, lambda i, s: None, lambda path: None, lambda err: None
        )


    def cancel_processing(self):
        """Terminates active parsing thread and updates record status."""
        if self.active_thread and self.active_thread.isRunning():
            self.active_thread.terminate()
            self.active_thread.wait()
        if hasattr(self, "history_record_id"):
            HistoryService.update_record_status(self.history_record_id, status="Cancelled")
        self.reset_to_upload()

    def reset_to_upload(self):
        """Resets HTML UI back to main upload dropzone view."""
        self.html_wrapper.eval_js("resetToUpload();")
