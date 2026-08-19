import json
import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, QTimer, QThread
from ui.html_screen_wrapper import HtmlScreenWrapper
from services.budget_service import BudgetService
from utils.user_session import UserSession
from utils.theme_manager import ThemeManager

class BudgetQueryWorker(QThread):
    result_ready = pyqtSignal(str, object)

    def __init__(self, action_type, query_fn, parent=None):
        super().__init__(parent)
        self.action_type = action_type
        self.query_fn = query_fn

    def run(self):
        try:
            res = self.query_fn()
            self.result_ready.emit(self.action_type, res)
        except Exception as e:
            print(f"BudgetQueryWorker error ({self.action_type}): {e}")
            self.result_ready.emit(self.action_type, None)

class BudgetPlannerWidget(QWidget):
    """
    PyQt Widget hosting the Monthly Salary & Budget Planner Web UI (web/budget_planner.html).
    Coordinates IPC communication between JavaScript frontend and BudgetService.
    """
    budgetUpdated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.html_wrapper = HtmlScreenWrapper("web/budget_planner.html", self)
        self.html_wrapper.web_view.titleChanged.connect(self.handle_web_commands)
        layout.addWidget(self.html_wrapper)
        
        # Load active budget after web view finishes loading
        self.html_wrapper.web_view.loadFinished.connect(lambda ok: self.load_budget_data())

    def get_user_id(self):
        user = UserSession.get_current_user()
        return str(user["id"]) if user and "id" in user else "default_user"

    def handle_web_commands(self, title: str):
        """Processes document.title IPC commands sent from web view."""
        if not title or not title.startswith("app-cmd:"):
            return
        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        payload = parts[2] if len(parts) > 2 else ""
        QTimer.singleShot(0, lambda: self.process_app_command(cmd, payload))

    def process_app_command(self, cmd: str, payload: str):
        user_id = self.get_user_id()
        
        if cmd == "budget_get":
            month_key = payload.strip() or datetime.datetime.now().strftime("%Y-%m")
            self.load_budget_data(month_key)

        elif cmd == "budget_save":
            try:
                data = json.loads(payload)
                month_key = data.get("month_key")
                raw_budget = data.get("budget")
                if month_key and raw_budget:
                    BudgetService.save_user_budget(user_id, month_key, raw_budget)
                    self.load_budget_data(month_key)
            except Exception as e:
                print(f"Error saving budget payload: {e}")

        elif cmd == "budget_add_expense":
            try:
                data = json.loads(payload)
                month_key = data.get("month_key")
                expense = data.get("expense")
                if month_key and expense:
                    BudgetService.add_actual_expense(user_id, month_key, expense)
                    self.load_budget_data(month_key)
            except Exception as e:
                print(f"Error adding expense payload: {e}")

        elif cmd == "budget_delete_expense":
            try:
                data = json.loads(payload)
                month_key = data.get("month_key")
                exp_id = data.get("expense_id")
                if month_key and exp_id:
                    BudgetService.delete_actual_expense(user_id, month_key, exp_id)
                    self.load_budget_data(month_key)
            except Exception as e:
                print(f"Error deleting expense payload: {e}")

        elif cmd == "budget_lock_toggle":
            try:
                data = json.loads(payload)
                month_key = data.get("month_key")
                unlocked = data.get("unlocked", True)
                if month_key:
                    BudgetService.set_planning_lock(user_id, month_key, manual_unlocked=unlocked)
                    self.load_budget_data(month_key)
            except Exception as e:
                print(f"Error toggling lock payload: {e}")

        elif cmd == "budget_copy_next_month":
            try:
                data = json.loads(payload)
                src = data.get("source_month")
                target = data.get("target_month")
                src_type = data.get("source_type", "planned")
                if src and target:
                    BudgetService.copy_to_next_month(user_id, src, target, source_type=src_type)
                    self.load_budget_data(target)
            except Exception as e:
                print(f"Error copying budget to next month: {e}")

        elif cmd == "budget_create_next_month":
            try:
                current_month = payload.strip() or datetime.datetime.now().strftime("%Y-%m")
                parts = current_month.split('-')
                year = int(parts[0])
                month = int(parts[1]) + 1
                if month > 12:
                    month = 1
                    year += 1
                target_month = f"{year}-{month:02d}"
                # Initialize new clean month for this user
                BudgetService.get_user_budget(user_id, target_month)
                self.load_budget_data(target_month)
            except Exception as e:
                print(f"Error creating next month: {e}")

        elif cmd == "budget_ai_summary":
            month_key = payload.strip() or datetime.datetime.now().strftime("%Y-%m")
            self.generate_ai_summary(month_key)

    def load_budget_data(self, month_key=None):
        """Fetches budget data & available months for active user and pushes to JS."""
        user_id = self.get_user_id()
        if not month_key:
            month_key = datetime.datetime.now().strftime("%Y-%m")

        def query_fn():
            summary = BudgetService.get_user_budget(user_id, month_key)
            months = BudgetService.get_user_months(user_id)
            return {"summary": summary, "months": months}

        def callback_fn(action, res):
            if res is not None:
                summary = res.get("summary", {})
                months = res.get("months", [])
                
                json_summary = json.dumps(summary).replace("\\", "\\\\").replace("'", "\\'")
                json_months = json.dumps(months).replace("\\", "\\\\").replace("'", "\\'")
                
                js_script = f"""
                if (typeof renderAvailableMonths === 'function') renderAvailableMonths({json_months}, '{month_key}');
                if (typeof renderBudgetSummaryData === 'function') renderBudgetSummaryData('{json_summary}');
                """
                self.html_wrapper.eval_js(js_script)
                
                # Apply active theme
                current_theme = ThemeManager.get_theme()
                self.update_theme_style(current_theme)

        worker = BudgetQueryWorker("get", query_fn, self)
        worker.result_ready.connect(callback_fn)
        worker.start()

    def generate_ai_summary(self, month_key):
        """Generates Gemini AI summary in background worker thread."""
        user_id = self.get_user_id()

        def query_fn():
            return BudgetService.generate_ai_summary(user_id, month_key)

        def callback_fn(action, html_res):
            if html_res:
                escaped_html = html_res.replace("\n", "").replace("'", "\\'")
                js_script = f"if (typeof displayAISummary === 'function') displayAISummary('{escaped_html}');"
                self.html_wrapper.eval_js(js_script)

        worker = BudgetQueryWorker("ai_summary", query_fn, self)
        worker.result_ready.connect(callback_fn)
        worker.start()

    def update_theme_style(self, theme):
        """Propagates active theme settings to the HTML container."""
        theme_clean = theme.lower().strip() if isinstance(theme, str) else "light"
        script = f"if ('{theme_clean}' === 'dark') document.body.classList.add('dark-mode'); else document.body.classList.remove('dark-mode');"
        self.html_wrapper.eval_js(script)
