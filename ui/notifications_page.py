import datetime
import html
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from ui.html_screen_wrapper import HtmlScreenWrapper
from services.notification_service import NotificationService
from utils.user_session import UserSession
from utils.theme_manager import ThemeManager

class NotificationsPageWidget(QWidget):
    """
    Renders the interactive Notification Center view with category filtering,
    mark as read, dismissal, and direct action routing.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_category = "all"
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.html_wrapper = HtmlScreenWrapper("web/notifications.html", self)
        self.html_wrapper.commandReceived.connect(self.handle_app_command)
        layout.addWidget(self.html_wrapper)
        
        # Load user notifications after web view initializes
        self.html_wrapper.web_view.loadFinished.connect(lambda ok: self.load_user_notifications())

    def get_current_user_id(self):
        user = UserSession.get_current_user()
        return str(user["id"]) if user and "id" in user else "guest"

    def handle_app_command(self, cmd: str, payload: str):
        user_id = self.get_current_user_id()
        
        if cmd == "notifications_filter":
            self.active_category = payload.strip() or "all"
            self.load_user_notifications()
            
        elif cmd == "notifications_mark_read":
            nid = payload.strip()
            if nid:
                NotificationService.mark_as_read(user_id, nid)
                self.load_user_notifications()
                self.sync_topbar_badge()
                
        elif cmd == "notifications_mark_all_read":
            NotificationService.mark_all_as_read(user_id)
            self.load_user_notifications()
            self.sync_topbar_badge()
            
        elif cmd == "notifications_dismiss":
            nid = payload.strip()
            if nid:
                NotificationService.dismiss_notification(user_id, nid)
                self.load_user_notifications()
                self.sync_topbar_badge()
                
        elif cmd == "notifications_dismiss_all":
            NotificationService.dismiss_all(user_id)
            self.load_user_notifications()
            self.sync_topbar_badge()
            
        elif cmd == "notifications_action":
            parts = payload.split(":", 1)
            act_type = parts[0].strip() if len(parts) > 0 else ""
            target = parts[1].strip() if len(parts) > 1 else ""
            
            p = self.parent()
            while p:
                if hasattr(p, "switch_dashboard_page"):
                    if act_type == "view_statement" or act_type == "history":
                        p.switch_dashboard_page("history")
                    elif act_type == "review_duplicates" or act_type == "duplicate_finder":
                        p.switch_dashboard_page("duplicate_finder")
                    elif act_type == "view_report" or act_type == "ai_report":
                        p.switch_dashboard_page("ai_report")
                    elif act_type == "reports":
                        p.switch_dashboard_page("reports")
                    elif target:
                        p.switch_dashboard_page(target)
                    break
                p = p.parent()

    def sync_topbar_badge(self):
        """Syncs the TopBar unread badge count."""
        p = self.parent()
        while p:
            if hasattr(p, "update_notification_badge"):
                p.update_notification_badge()
                break
            p = p.parent()

    def format_time_ago(self, iso_str):
        if not iso_str:
            return ""
        try:
            dt = datetime.datetime.fromisoformat(iso_str)
            now = datetime.datetime.utcnow()
            diff = now - dt
            seconds = diff.total_seconds()
            
            if seconds < 60:
                return "Just now"
            elif seconds < 3600:
                mins = int(seconds / 60)
                return f"{mins}m ago"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f"{hours}h ago"
            else:
                days = int(seconds / 86400)
                if days == 1:
                    return "Yesterday"
                return f"{days}d ago"
        except Exception:
            return iso_str.split("T")[0] if "T" in iso_str else iso_str

    def load_user_notifications(self):
        """Fetches notifications for active user from NotificationService and builds HTML list."""
        user_id = self.get_current_user_id()
        notifications = NotificationService.get_user_notifications(user_id=user_id, category=self.active_category)
        
        # Calculate category counts
        all_nots = NotificationService.get_user_notifications(user_id=user_id, category="all")
        cnt_all = len(all_nots)
        cnt_ai = len([n for n in all_nots if n.get("category") == "ai_risk"])
        cnt_parse = len([n for n in all_nots if n.get("category") == "parsing_export"])
        cnt_sec = len([n for n in all_nots if n.get("category") == "system_security"])

        # Update Filter Pill Counts and Active Filter state
        js_counts = f"""
            if (document.getElementById('cnt-all')) document.getElementById('cnt-all').innerText = '{cnt_all}';
            if (document.getElementById('cnt-ai_risk')) document.getElementById('cnt-ai_risk').innerText = '{cnt_ai}';
            if (document.getElementById('cnt-parsing_export')) document.getElementById('cnt-parsing_export').innerText = '{cnt_parse}';
            if (document.getElementById('cnt-system_security')) document.getElementById('cnt-system_security').innerText = '{cnt_sec}';
            setCategoryFilter('{self.active_category}');
        """
        self.html_wrapper.eval_js(js_counts)

        # Apply Theme Style
        current_theme = ThemeManager.get_theme()
        theme_script = f"if ('{current_theme}' === 'dark') document.body.classList.add('dark-mode'); else document.body.classList.remove('dark-mode');"
        self.html_wrapper.eval_js(theme_script)

        # Render Empty State if no notifications exist
        if not notifications:
            empty_html = """
            <div class="empty-state-box">
                <div class="empty-icon">🔔</div>
                <div class="empty-title">You're all caught up!</div>
                <div class="empty-subtitle">There are no notifications in this category at the moment.</div>
            </div>
            """
            escaped_empty = empty_html.replace("\n", "").replace("'", "\\'")
            self.html_wrapper.eval_js(f"if (document.getElementById('notificationsList')) document.getElementById('notificationsList').innerHTML = '{escaped_empty}';")
            return

        # Render Cards List
        cards_html_parts = []
        for n in notifications:
            nid = html.escape(str(n.get("_id", "")))
            category = n.get("category", "parsing_export")
            title = html.escape(str(n.get("title", "Notification")))
            message = html.escape(str(n.get("message", "")))
            is_read = n.get("is_read", False)
            created_at = self.format_time_ago(n.get("created_at", ""))
            action_type = n.get("action_type", "")
            action_url = n.get("action_url", "")

            # Icon mapping
            icon_symbol = "📄"
            if category == "ai_risk":
                icon_symbol = "🔴"
            elif category == "system_security":
                icon_symbol = "🔒"

            unread_class = "unread" if not is_read else ""
            unread_dot_html = '<span class="unread-dot"></span>' if not is_read else ''

            # Action buttons
            actions_html = ""
            if action_type == "view_statement":
                actions_html += f'<button type="button" class="btn-card-action btn-action-primary" onclick="sendAppCommand(\'notifications_action\', \'view_statement:{action_url}\')">View Statement</button>'
            elif action_type == "review_duplicates":
                actions_html += f'<button type="button" class="btn-card-action btn-action-primary" onclick="sendAppCommand(\'notifications_action\', \'review_duplicates:{action_url}\')">Review Duplicates</button>'
            elif action_type == "view_report":
                actions_html += f'<button type="button" class="btn-card-action btn-action-primary" onclick="sendAppCommand(\'notifications_action\', \'view_report:{action_url}\')">View Report</button>'
            elif action_type:
                actions_html += f'<button type="button" class="btn-card-action btn-action-primary" onclick="sendAppCommand(\'notifications_action\', \'{action_type}:{action_url}\')">Open</button>'

            if not is_read:
                actions_html += f'<button type="button" class="btn-card-action btn-action-secondary" onclick="sendAppCommand(\'notifications_mark_read\', \'{nid}\')">Mark as Read</button>'

            actions_html += f'<button type="button" class="btn-card-action btn-action-dismiss" onclick="sendAppCommand(\'notifications_dismiss\', \'{nid}\')">Dismiss</button>'

            card_item = f"""
            <div class="notification-card {unread_class}">
                <div class="card-icon-box cat-{category}">
                    {icon_symbol}
                </div>
                <div class="card-body">
                    <div class="card-title-row">
                        <div class="card-title">
                            {unread_dot_html}
                            <span>{title}</span>
                        </div>
                        <div class="card-time">{created_at}</div>
                    </div>
                    <div class="card-message">{message}</div>
                    <div class="card-actions">
                        {actions_html}
                    </div>
                </div>
            </div>
            """
            cards_html_parts.append(card_item)

        full_html = "".join(cards_html_parts).replace("\n", "").replace("'", "\\'")
        self.html_wrapper.eval_js(f"if (document.getElementById('notificationsList')) document.getElementById('notificationsList').innerHTML = '{full_html}';")

    def update_theme_style(self, theme):
        theme_script = f"if ('{theme}' === 'dark') document.body.classList.add('dark-mode'); else document.body.classList.remove('dark-mode');"
        self.html_wrapper.eval_js(theme_script)
