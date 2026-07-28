import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, QObject

from ui.html_screen_wrapper import HtmlScreenWrapper


class SignalHolder(QObject):
    textChanged = pyqtSignal(str)
    currentIndexChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)
    toggled = pyqtSignal(bool)
    colorChanged = pyqtSignal(str)


class FieldProxy(QObject):
    """Proxy object simulating Qt widgets for SettingsController bindings."""
    textChanged = pyqtSignal(str)
    currentIndexChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)
    toggled = pyqtSignal(bool)
    colorChanged = pyqtSignal(str)

    def __init__(self, parent_window, field_id, field_type="text"):
        super().__init__()
        self.parent_window = parent_window
        self.field_id = field_id
        self.field_type = field_type
        self._val = "" if field_type in ["text", "combo"] else False

    def text(self):
        return str(self._val)

    def setText(self, val):
        self._val = str(val)
        val_str = json.dumps(str(val))
        js = (
            f"(function(){{ "
            f"var el = document.getElementById('{self.field_id}'); "
            f"if (el) {{ "
            f"  if (el.tagName === 'INPUT' || el.tagName === 'SELECT') el.value = {val_str}; "
            f"  else el.innerText = {val_str}; "
            f"}} "
            f"if ('{self.field_id}' === 'accName') {{ "
            f"  var disp = document.getElementById('accNameDisplay'); if (disp) disp.innerText = {val_str}; "
            f"  if (typeof updateAvatarInitials === 'function') updateAvatarInitials({val_str}); "
            f"}} "
            f"if ('{self.field_id}' === 'accEmail') {{ "
            f"  var edisp = document.getElementById('accEmailDisplay'); if (edisp) edisp.innerText = {val_str}; "
            f"}} "
            f"}})();"
        )
        self.parent_window.html_wrapper.eval_js(js)

    def currentText(self):
        return str(self._val)

    def setCurrentText(self, val):
        self._val = str(val)
        val_str = json.dumps(str(val))
        js = f"(function(){{ var el = document.getElementById('{self.field_id}'); if (el) el.value = {val_str}; }})();"
        self.parent_window.html_wrapper.eval_js(js)

    def isChecked(self):
        return bool(self._val)

    def setChecked(self, val):
        self._val = bool(val)
        js = f"(function(){{ var el = document.getElementById('{self.field_id}'); if (el) el.checked = {'true' if val else 'false'}; }})();"
        self.parent_window.html_wrapper.eval_js(js)

    def set_name(self, name):
        self._val = name
        name_str = json.dumps(str(name))
        js = (
            f"(function(){{ "
            f"  if (typeof updateAvatarInitials === 'function') updateAvatarInitials({name_str}); "
            f"  var disp = document.getElementById('accNameDisplay'); if (disp) disp.innerText = {name_str}; "
            f"}})();"
        )
        self.parent_window.html_wrapper.eval_js(js)

    def set_selected_color(self, color):
        self._val = color
        color_str = json.dumps(str(color))
        js = f"(function(){{ if (typeof selectAccentColor === 'function') selectAccentColor({color_str}); }})();"
        self.parent_window.html_wrapper.eval_js(js)

    def clear(self):
        self._val = ""
        js = f"(function(){{ var el = document.getElementById('{self.field_id}'); if (el) el.value = ''; }})();"
        self.parent_window.html_wrapper.eval_js(js)


class SettingsWindow(QWidget):
    """
    Main Settings Window presenting a modern desktop suite interface built
    using HTML + CSS presentation layer integrated via QWebEngineView wrapper with Python MVC controller.
    """
    # Signals for Controller interactions
    save_clicked = pyqtSignal()
    apply_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    restore_defaults_clicked = pyqtSignal()
    
    # Test connection clicks
    test_db_clicked = pyqtSignal(str)
    test_gemini_clicked = pyqtSignal(str)
    test_email_clicked = pyqtSignal(str, str, str, str)
    
    # Action clicks
    backup_db_clicked = pyqtSignal(str)
    restore_db_clicked = pyqtSignal(str)
    export_db_clicked = pyqtSignal(str)
    view_db_stats_clicked = pyqtSignal(str)
    clear_session_clicked = pyqtSignal()
    reset_auth_clicked = pyqtSignal()
    check_updates_clicked = pyqtSignal()
    logout_clicked = pyqtSignal()
    
    # Edit profile inline
    edit_profile_clicked = pyqtSignal()
    change_password_clicked = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsScreenRoot")
        self.active_tab_key = "general"

        # General Form Proxies
        self.gen_app_name = FieldProxy(self, "genAppName", "text")
        self.gen_save_location = FieldProxy(self, "genSaveLocation", "text")
        self.gen_save_location_err = FieldProxy(self, "genSaveLocationErr", "text")
        self.gen_lang = FieldProxy(self, "genLang", "combo")
        self.gen_auto_save = FieldProxy(self, "genAutoSave", "check")

        # Account Form Proxies
        self.acc_username = FieldProxy(self, "accUsername", "text")
        self.acc_username_err = FieldProxy(self, "accUsernameErr", "text")
        self.acc_name = FieldProxy(self, "accName", "text")
        self.acc_name_err = FieldProxy(self, "accNameErr", "text")
        self.acc_email = FieldProxy(self, "accEmail", "text")
        self.acc_phone = FieldProxy(self, "accPhone", "text")
        self.acc_phone_err = FieldProxy(self, "accPhoneErr", "text")
        self.acc_role_lbl = FieldProxy(self, "accRoleLbl", "text")
        self.acc_date_lbl = FieldProxy(self, "accDateLbl", "text")
        self.acc_old_pwd = FieldProxy(self, "accOldPwd", "text")
        self.acc_new_pwd = FieldProxy(self, "accNewPwd", "text")
        self.avatar = FieldProxy(self, "accAvatar", "avatar")

        # Appearance Proxies
        self.app_theme = FieldProxy(self, "appTheme", "combo")
        self.color_selector = FieldProxy(self, "colorSelector", "color")
        self.app_font_size = FieldProxy(self, "appFontSize", "combo")
        self.app_sidebar = FieldProxy(self, "appSidebar", "combo")
        self.app_density = FieldProxy(self, "appDensity", "combo")
        self.app_animations = FieldProxy(self, "appAnimations", "check")

        # Notification Proxies
        self.nt_completed = FieldProxy(self, "ntCompleted", "check")
        self.nt_export = FieldProxy(self, "ntExport", "check")
        self.nt_errors = FieldProxy(self, "ntErrors", "check")
        self.nt_email = FieldProxy(self, "ntEmail", "check")
        self.nt_ai = FieldProxy(self, "ntAi", "check")
        self.nt_updates = FieldProxy(self, "ntUpdates", "check")

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.html_wrapper = HtmlScreenWrapper("web/settings.html", self)
        layout.addWidget(self.html_wrapper)

        # Connect WebBridge IPC commands and load finished signal
        self.html_wrapper.web_view.titleChanged.connect(self.handle_web_commands)
        self.html_wrapper.web_view.loadFinished.connect(self._on_html_loaded)

    def _on_html_loaded(self, ok):
        if ok:
            if hasattr(self, "controller") and self.controller:
                self.controller.load_user_settings()
            self.sync_user_profile_directly()
            from utils.theme_manager import ThemeManager
            self.update_theme_style(ThemeManager.get_theme())

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "controller") and self.controller:
            self.controller.load_user_settings()
        self.sync_user_profile_directly()
        from utils.theme_manager import ThemeManager
        self.update_theme_style(ThemeManager.get_theme())

    def sync_user_profile_directly(self):
        """Directly injects active user session details into HTML DOM elements for guaranteed consistency."""
        from utils.user_session import UserSession
        user = UserSession.get_current_user()
        if not user:
            return

        name = user.get("name") or user.get("full_name") or "User"
        email = user.get("email") or ""
        username = user.get("username") or (email.split("@")[0] if email else "")
        phone = user.get("phone") or ""
        role = user.get("role") or "User"
        created_at = user.get("created_at") or ""
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        elif not isinstance(created_at, str):
            created_at = str(created_at)

        created_str = str(created_at)[:10] if len(str(created_at)) >= 10 else str(created_at)

        parts = name.strip().split(" ")
        initials = "U"
        if len(parts) >= 2 and parts[0] and parts[1]:
            initials = (parts[0][0] + parts[1][0]).upper()
        elif len(parts) >= 1 and parts[0]:
            initials = parts[0][0].upper()

        name_js = json.dumps(str(name))
        email_js = json.dumps(str(email))
        username_js = json.dumps(str(username))
        phone_js = json.dumps(str(phone))
        role_js = json.dumps(str(role))
        date_js = json.dumps(f"📅 Member since: {created_str}" if created_str else "📅 Member since: Active")
        initials_js = json.dumps(str(initials))

        js = f"""
        (function() {{
            var accNameDisp = document.getElementById('accNameDisplay');
            if (accNameDisp) accNameDisp.innerText = {name_js};
            
            var accEmailDisp = document.getElementById('accEmailDisplay');
            if (accEmailDisp) accEmailDisp.innerText = {email_js};
            
            var accAvatar = document.getElementById('accAvatarCircle');
            if (accAvatar) accAvatar.innerText = {initials_js};
            
            var accRole = document.getElementById('accRoleLbl');
            if (accRole) accRole.innerText = {role_js};
            
            var accDate = document.getElementById('accDateLbl');
            if (accDate) accDate.innerText = {date_js};
            
            var accNameInp = document.getElementById('accName');
            if (accNameInp) accNameInp.value = {name_js};
            
            var accEmailInp = document.getElementById('accEmail');
            if (accEmailInp) accEmailInp.value = {email_js};
            
            var accUserInp = document.getElementById('accUsername');
            if (accUserInp) accUserInp.value = {username_js};
            
            var accPhoneInp = document.getElementById('accPhone');
            if (accPhoneInp) accPhoneInp.value = {phone_js};
        }})();
        """
        self.html_wrapper.eval_js(js)

    def update_theme_style(self, theme: str = "light"):
        """Updates HTML UI theme styling ('light' or 'dark') and syncs active theme card selection."""
        theme_str = theme.lower().strip() if isinstance(theme, str) else "light"
        js = (
            f"(function(){{ "
            f"if ('{theme_str}' === 'dark') document.body.classList.add('dark-mode'); else document.body.classList.remove('dark-mode'); "
            f"if (typeof selectThemeMode === 'function') selectThemeMode('{theme_str.capitalize()}'); "
            f"}})();"
        )
        self.html_wrapper.eval_js(js)

    def handle_web_commands(self, title: str):
        """Dispatches commands sent from JavaScript UI via document.title IPC."""
        if not title or not title.startswith("app-cmd:"):
            return

        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        raw_payload = parts[2] if len(parts) > 2 else ""

        if cmd == "settings_field_change":
            try:
                data = json.loads(raw_payload)
                field = data.get("field")
                val = data.get("value")
                self.handle_field_update(field, val)
            except Exception:
                pass
        elif cmd == "settings_browse_folder":
            self.browse_save_folder()
        elif cmd == "settings_change_password":
            try:
                data = json.loads(raw_payload)
                old_p = data.get("old_password", "")
                new_p = data.get("new_password", "")
                self.change_password_clicked.emit(old_p, new_p)
            except Exception:
                pass
        elif cmd == "settings_check_updates":
            self.check_updates_clicked.emit()
        elif cmd == "settings_save":
            self.save_clicked.emit()
        elif cmd == "settings_restore_defaults":
            self.restore_defaults_clicked.emit()
        elif cmd == "settings_cancel":
            self.cancel_clicked.emit()

    def handle_field_update(self, field, val):
        """Updates internal model proxy fields when edited in HTML UI and triggers live theme sync."""
        mapping = {
            "app_name": self.gen_app_name,
            "save_location": self.gen_save_location,
            "language": self.gen_lang,
            "auto_save": self.gen_auto_save,
            "account_username": self.acc_username,
            "account_name": self.acc_name,
            "account_email": self.acc_email,
            "account_phone": self.acc_phone,
            "app_theme": self.app_theme,
            "app_accent_color": self.color_selector,
            "app_font_size": self.app_font_size,
            "app_sidebar_layout": self.app_sidebar,
            "app_density": self.app_density,
            "app_animations": self.app_animations,
            "nt_statement_completed": self.nt_completed,
            "nt_export_completed": self.nt_export,
            "nt_errors": self.nt_errors,
            "nt_email_sent": self.nt_email,
            "nt_ai_finished": self.nt_ai,
            "nt_updates_available": self.nt_updates
        }
        proxy = mapping.get(field)
        if proxy:
            proxy._val = val
            if hasattr(self, "controller") and self.controller:
                self.controller.update_model_field(field, val)

        if field == "app_theme":
            theme_val = str(val).lower()
            from utils.theme_manager import ThemeManager
            ThemeManager.apply_theme(theme_val)
            from settings.appearance_service import AppearanceService
            accent_color = self.color_selector.text() or "blue"
            AppearanceService.apply_appearance(theme_val, accent_color)
            
            # Propagate live theme change to parent dashboard application-wide
            win = self.window()
            if win and hasattr(win, "sync_theme_styles"):
                win.sync_theme_styles(theme_val)
            elif hasattr(self, "parent_dashboard") and hasattr(self.parent_dashboard, "update_theme_styles"):
                self.parent_dashboard.update_theme_styles(theme_val)

    def browse_save_folder(self):
        """Opens native directory picker for selecting save location."""
        doc_dir = os.path.expanduser("~/Documents")
        folder = QFileDialog.getExistingDirectory(self, "Select Export Directory", doc_dir)
        if folder:
            self.gen_save_location.setText(folder)
            if hasattr(self, "controller") and self.controller:
                self.controller.update_model_field("save_location", folder)

    def set_buttons_dirty(self, dirty: bool):
        """Updates dirty save state indicator in HTML sticky footer."""
        js = f"(function(){{ if (typeof setDirtyState === 'function') setDirtyState({'true' if dirty else 'false'}); }})();"
        self.html_wrapper.eval_js(js)
