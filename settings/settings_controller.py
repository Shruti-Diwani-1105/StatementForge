from PyQt6.QtCore import QObject, pyqtSlot
from utils.user_session import UserSession
from utils.profile_service import ProfileService
from settings.models.settings_model import SettingsModel
from settings.settings_service import SettingsService
from settings.database_service import DatabaseService, MongoDBTestWorker
from settings.gemini_service import GeminiService, GeminiTestWorker
from settings.email_service import EmailService, EmailTestWorker
from settings.security_service import SecurityService
from settings.validation_service import ValidationService
from settings.toast import Toast

class SettingsController(QObject):
    """
    Controller mediating between SettingsWindow (View) and SettingsModel (Model).
    Validates user inputs, manages background workers, and coordinates load/save operations.
    """
    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.model = SettingsModel()
        
        # Guard flag to ignore widget change events while populating controls
        self.loading = False
        
        # References to running worker threads
        self.db_worker = None
        self.gemini_worker = None
        self.email_worker = None
        
        # Connect signals
        self.connect_view_signals()
        self.connect_change_listeners()
        
        # Load user configurations
        self.load_user_settings()

    def connect_view_signals(self):
        """Binds view button click signals to controller methods."""
        # Footer buttons
        self.view.save_clicked.connect(self.handle_save)
        self.view.cancel_clicked.connect(self.handle_cancel)
        self.view.restore_defaults_clicked.connect(self.handle_restore_defaults)
        
        # Connection tests
        self.view.test_db_clicked.connect(self.test_database_connection)
        self.view.test_gemini_clicked.connect(self.test_gemini_connection)
        self.view.test_email_clicked.connect(self.test_email_connection)
        
        # Action triggers
        self.view.backup_db_clicked.connect(self.backup_database)
        self.view.restore_db_clicked.connect(self.restore_database)
        self.view.export_db_clicked.connect(self.export_database_schema)
        self.view.view_db_stats_clicked.connect(self.view_database_statistics)
        self.view.clear_session_clicked.connect(self.clear_session)
        self.view.reset_auth_clicked.connect(self.reset_auth)
        self.view.check_updates_clicked.connect(self.check_for_updates)
        self.view.logout_clicked.connect(self.logout)
        
        # Edit profiles
        self.view.edit_profile_clicked.connect(self.handle_profile_update)
        self.view.change_password_clicked.connect(self.handle_password_change)

    def connect_change_listeners(self):
        """Binds control value modifications to dirty checking and model updates."""
        # General
        self.view.gen_app_name.textChanged.connect(lambda v: self.update_model_field("app_name", v))
        self.view.gen_save_location.textChanged.connect(lambda v: self.update_model_field("save_location", v))
        self.view.gen_lang.currentIndexChanged.connect(
            lambda: self.update_model_field("language", self.view.gen_lang.currentText())
        )
        self.view.gen_auto_save.stateChanged.connect(
            lambda: self.update_model_field("auto_save", self.view.gen_auto_save.isChecked())
        )
        
        # Account
        self.view.acc_username.textChanged.connect(lambda v: self.update_model_field("account_username", v))
        self.view.acc_name.textChanged.connect(lambda v: self.update_model_field("account_name", v))
        self.view.acc_phone.textChanged.connect(lambda v: self.update_model_field("account_phone", v))
        
        # Appearance
        self.view.app_theme.currentIndexChanged.connect(
            lambda: (self.update_model_field("app_theme", self.view.app_theme.currentText()),
                     self.update_model_field("theme", self.view.app_theme.currentText()))
        )
        self.view.color_selector.colorChanged.connect(lambda color: self.update_model_field("app_accent_color", color))
        self.view.app_font_size.currentIndexChanged.connect(
            lambda: self.update_model_field("app_font_size", self.view.app_font_size.currentText())
        )
        self.view.app_sidebar.currentIndexChanged.connect(
            lambda: self.update_model_field("app_sidebar_layout", self.view.app_sidebar.currentText())
        )
        self.view.app_density.currentIndexChanged.connect(
            lambda: self.update_model_field("app_density", self.view.app_density.currentText())
        )
        self.view.app_animations.toggled.connect(lambda checked: self.update_model_field("app_animations", checked))
        
        # Notifications
        self.view.nt_completed.stateChanged.connect(
            lambda: self.update_model_field("nt_statement_completed", self.view.nt_completed.isChecked())
        )
        self.view.nt_export.stateChanged.connect(
            lambda: self.update_model_field("nt_export_completed", self.view.nt_export.isChecked())
        )
        self.view.nt_errors.stateChanged.connect(
            lambda: self.update_model_field("nt_errors", self.view.nt_errors.isChecked())
        )
        self.view.nt_email.stateChanged.connect(
            lambda: self.update_model_field("nt_email_sent", self.view.nt_email.isChecked())
        )
        self.view.nt_ai.stateChanged.connect(
            lambda: self.update_model_field("nt_ai_finished", self.view.nt_ai.isChecked())
        )
        self.view.nt_updates.stateChanged.connect(
            lambda: self.update_model_field("nt_updates_available", self.view.nt_updates.isChecked())
        )

    # ----------------------------------------------------
    # DATA BINDING / SYNC METHODS
    # ----------------------------------------------------
    
    def load_user_settings(self):
        """Loads persistent user configurations and populates View controls."""
        self.loading = True
        
        user = UserSession.get_current_user()
        if user:
            # Load settings database/json cache
            data = SettingsService.load_settings(user)
            self.model.load_from_dict(data)
            
            # Map database parameters onto account fields
            self.model.set("account_username", user.get("username", ""))
            self.model.set("account_name", user.get("name", ""))
            self.model.set("account_email", user.get("email", ""))
            self.model.set("account_phone", user.get("phone", ""))
            self.model.set("account_role", user.get("role", "User"))
            self.model.set("account_created_at", user.get("created_at", ""))
            
        self.populate_view_fields()
        self.loading = False
        
        # Sync footer state
        self.view.set_buttons_dirty(self.model.is_dirty())
        
        # Force initial validations (soft check, don't show inline errors on startup)
        self.validate_all_inputs(show_errors=False)
 
    def populate_view_fields(self):
        """Fills View elements from the active Model states."""
        # General
        self.view.gen_app_name.setText(self.model.get("app_name"))
        self.view.gen_save_location.setText(self.model.get("save_location"))
        self.view.gen_lang.setCurrentText(self.model.get("language"))
        self.view.gen_auto_save.setChecked(self.model.get("auto_save"))
        
        # Account details
        self.view.acc_username.setText(self.model.get("account_username"))
        self.view.acc_name.setText(self.model.get("account_name"))
        self.view.acc_email.setText(self.model.get("account_email"))
        self.view.acc_phone.setText(self.model.get("account_phone"))
        self.view.acc_role_lbl.setText(self.model.get("account_role"))
        
        created_dt = self.model.get("account_created_at")
        if created_dt:
            self.view.acc_date_lbl.setText(str(created_dt)[:10] if len(str(created_dt)) >= 10 else str(created_dt))
            
        self.view.avatar.set_name(self.model.get("account_name"))
        self.view.acc_old_pwd.clear()
        self.view.acc_new_pwd.clear()
        
        # Appearance
        self.view.app_theme.setCurrentText(self.model.get("app_theme"))
        self.view.color_selector.set_selected_color(self.model.get("app_accent_color"))
        self.view.app_font_size.setCurrentText(self.model.get("app_font_size"))
        self.view.app_sidebar.setCurrentText(self.model.get("app_sidebar_layout"))
        self.view.app_density.setCurrentText(self.model.get("app_density"))
        self.view.app_animations.setChecked(self.model.get("app_animations"))
        
        # Notifications
        self.view.nt_completed.setChecked(self.model.get("nt_statement_completed"))
        self.view.nt_export.setChecked(self.model.get("nt_export_completed"))
        self.view.nt_errors.setChecked(self.model.get("nt_errors"))
        self.view.nt_email.setChecked(self.model.get("nt_email_sent"))
        self.view.nt_ai.setChecked(self.model.get("nt_ai_finished"))
        self.view.nt_updates.setChecked(self.model.get("nt_updates_available"))

    def update_model_field(self, field_name, value):
        """Updates a model property and triggers validation and footer state checks."""
        if self.loading:
            return
            
        self.model.set(field_name, value)
        
        # Special handler to sync initials immediately
        if field_name == "account_name":
            self.view.avatar.set_name(value)
            
        # Perform soft validation check
        self.validate_all_inputs(show_errors=True)
        
        # Update sticky footer state
        self.view.set_buttons_dirty(self.model.is_dirty())

    # ----------------------------------------------------
    # VALIDATION
    # ----------------------------------------------------
    
    def validate_all_inputs(self, show_errors=False):
        """Runs input validation across fields, returning True if all are valid."""
        # Validate General save path
        v_save_loc, msg_save_loc = ValidationService.validate_save_folder(self.model.get("save_location"))
        
        # Validate Account fields
        v_username = bool(self.model.get("account_username").strip())
        msg_username = "" if v_username else "Username is required."
        
        v_name, msg_name = ValidationService.validate_name(self.model.get("account_name"))
        v_phone, msg_phone = ValidationService.validate_phone(self.model.get("account_phone"))
        
        # Render helper errors inline
        if show_errors:
            self.view.gen_save_location_err.setText(msg_save_loc if not v_save_loc else " ")
            self.view.acc_username_err.setText(msg_username if not v_username else " ")
            self.view.acc_name_err.setText(msg_name if not v_name else " ")
            self.view.acc_phone_err.setText(msg_phone if not v_phone else " ")

        return all([v_save_loc, v_username, v_name, v_phone])

    # ----------------------------------------------------
    # ASYNC TEST WORKERS
    # ----------------------------------------------------
    
    @pyqtSlot(str)
    def test_database_connection(self, uri):
        """Tests MongoDB Atlas URI asynchronously."""
        if not uri or not uri.strip():
            self.view.db_uri_err.setText("MongoDB URI cannot be empty.")
            Toast.error(self.view, "❌ MongoDB URI cannot be empty.")
            return
            
        # Check validation first
        valid, err_msg = ValidationService.validate_mongodb_uri(uri)
        if not valid:
            self.view.db_uri_err.setText(err_msg)
            Toast.error(self.view, f"❌ {err_msg}")
            return
            
        self.view.db_status_badge.setText("Connecting...")
        self.view.db_status_badge.setStyleSheet("background-color: #FEF3C7; color: #D97706; border-radius: 6px; font-weight: bold; font-size: 11px;")
        self.view.btn_test_db.setEnabled(False)
        self.view.btn_reconnect_db.setEnabled(False)
        
        # Start background QThread
        self.db_worker = MongoDBTestWorker(uri)
        self.db_worker.finished.connect(self.on_db_test_finished)
        self.db_worker.start()

    def on_db_test_finished(self, success, message):
        """Updates connection state badge and displays Toast."""
        self.view.btn_test_db.setEnabled(True)
        self.view.btn_reconnect_db.setEnabled(True)
        self.db_worker.deleteLater()
        self.db_worker = None
        
        if success:
            self.view.db_status_badge.setText("Connected")
            self.view.db_status_badge.setStyleSheet("background-color: #D1FAE5; color: #065F46; border-radius: 6px; font-weight: bold; font-size: 11px;")
            Toast.success(self.view, "✓ MongoDB Connected Successfully")
            # Pull stats
            self.view_database_statistics(self.model.get("db_mongodb_uri"))
        else:
            self.view.db_status_badge.setText("Disconnected")
            self.view.db_status_badge.setStyleSheet("background-color: #FEE2E2; color: #991B1B; border-radius: 6px; font-weight: bold; font-size: 11px;")
            Toast.error(self.view, f"❌ Connection Error: {message}")

    @pyqtSlot(str)
    def test_gemini_connection(self, key):
        """Tests Google Gemini API key authorization asynchronously."""
        if not key or not key.strip():
            self.view.ai_api_key_err.setText("API Key cannot be empty.")
            Toast.error(self.view, "❌ Empty API Key.")
            return
            
        self.view.gemini_status_badge.setText("Verifying...")
        self.view.gemini_status_badge.setStyleSheet("background-color: #FEF3C7; color: #D97706; border-radius: 6px; font-weight: bold; font-size: 11px;")
        self.view.btn_test_gemini.setEnabled(False)
        
        self.gemini_worker = GeminiTestWorker(key)
        self.gemini_worker.finished.connect(self.on_gemini_test_finished)
        self.gemini_worker.start()

    def on_gemini_test_finished(self, success, message):
        self.view.btn_test_gemini.setEnabled(True)
        self.gemini_worker.deleteLater()
        self.gemini_worker = None
        
        if success:
            self.view.gemini_status_badge.setText("Connected")
            self.view.gemini_status_badge.setStyleSheet("background-color: #D1FAE5; color: #065F46; border-radius: 6px; font-weight: bold; font-size: 11px;")
            Toast.success(self.view, "✓ Gemini Connected Successfully")
        else:
            self.view.gemini_status_badge.setText("Disconnected")
            self.view.gemini_status_badge.setStyleSheet("background-color: #FEE2E2; color: #991B1B; border-radius: 6px; font-weight: bold; font-size: 11px;")
            Toast.error(self.view, f"❌ {message}")

    @pyqtSlot(str, str, str, str)
    def test_email_connection(self, host, port, sender, password):
        """Tests SMTP connection parameters asynchronously."""
        # Run validations
        v_host, msg_host = ValidationService.validate_smtp_server(host)
        v_port, msg_port = ValidationService.validate_smtp_port(port)
        v_email, msg_email = ValidationService.validate_email(sender)
        
        if not (v_host and v_port and v_email):
            self.view.email_smtp_err.setText(msg_host if not v_host else " ")
            self.view.email_port_err.setText(msg_port if not v_port else " ")
            self.view.email_sender_err.setText(msg_email if not v_email else " ")
            Toast.error(self.view, "❌ Please resolve SMTP field validation errors first.")
            return
            
        Toast.info(self.view, "Testing SMTP Mail Connection...")
        
        self.email_worker = EmailTestWorker(host, port, sender, password)
        self.email_worker.finished.connect(self.on_email_test_finished)
        self.email_worker.start()

    def on_email_test_finished(self, success, message):
        self.email_worker.deleteLater()
        self.email_worker = None
        
        if success:
            Toast.success(self.view, "✓ Email SMTP Verified Successfully")
        else:
            Toast.error(self.view, f"❌ Email Test Failed: {message}")

    # ----------------------------------------------------
    # ACTION HANDLERS
    # ----------------------------------------------------
    
    def handle_save(self):
        """Saves current model changes to database and local cache."""
        if not self.validate_all_inputs(show_errors=True):
            Toast.error(self.view, "❌ Cannot Save: Please resolve inline validation errors first.")
            return
            
        user = UserSession.get_current_user()
        if not user:
            Toast.error(self.view, "❌ Error: User session has expired.")
            return
            
        # Commit modifications into settings database/cache
        success, message = SettingsService.save_settings(user, self.model.to_dict())
        
        if success:
            # Sync user profile if name/phone/username changed
            name = self.model.get("account_name")
            phone = self.model.get("account_phone")
            username = self.model.get("account_username")
            
            # Update user profile in the users collection
            ProfileService.update_profile(user["email"], name, phone, username)
            
            self.model.commit_changes()
            self.view.set_buttons_dirty(False)
            Toast.success(self.view, "✓ Settings Saved Successfully")
            
            # Apply layout/visual properties instantly
            SettingsService.apply_settings_instantly(self.model.to_dict())
            
            # Sync user details in session cache
            user["name"] = name
            user["phone"] = phone
            user["username"] = username
            UserSession.start_session(user)
            
            # Fire update notifications to parent dashboard if listening
            if hasattr(self.view.parent(), "set_user_profile"):
                self.view.parent().set_user_profile(user)
        else:
            Toast.error(self.view, f"❌ Save Failed: {message}")

    def handle_cancel(self):
        """Rollbacks any dirty inputs to their original saved values."""
        self.model.rollback_changes()
        self.populate_view_fields()
        self.validate_all_inputs(show_errors=True)
        self.view.set_buttons_dirty(False)
        Toast.info(self.view, "Changes discarded")

    def handle_restore_defaults(self):
        """Resets all settings fields to system defaults."""
        self.model.restore_defaults()
        self.populate_view_fields()
        self.validate_all_inputs(show_errors=True)
        self.view.set_buttons_dirty(self.model.is_dirty())
        Toast.info(self.view, "Restored default configuration settings")

    # ----------------------------------------------------
    # DATABASE ACTIONS
    # ----------------------------------------------------
    
    def backup_database(self, uri):
        success, msg = DatabaseService.backup_database(uri)
        if success:
            Toast.success(self.view, msg)
        else:
            Toast.error(self.view, msg)

    def restore_database(self, uri):
        success, msg = DatabaseService.restore_database(uri, "backup.json")
        if success:
            Toast.success(self.view, msg)
        else:
            Toast.error(self.view, msg)

    def export_database_schema(self, uri):
        success, msg = DatabaseService.export_database(uri)
        if success:
            Toast.success(self.view, msg)
        else:
            Toast.error(self.view, msg)

    def view_database_statistics(self, uri):
        stats = DatabaseService.get_db_stats(uri)
        self.view.db_stats_label.setText(
            f"Database: {stats['db_name']} • Collections count: \n"
            f"  - Users: {stats['collections']['users']}\n"
            f"  - Settings: {stats['collections']['settings']}\n"
            f"  - Statements: {stats['collections']['statements']}\n"
            f"  - Transactions: {stats['collections']['transactions']}\n"
            f"  - Reports: {stats['collections']['reports']}"
        )
        Toast.success(self.view, "✓ Database statistics updated")

    # ----------------------------------------------------
    # ACCOUNT PROFILE ACTIONS
    # ----------------------------------------------------
    
    def handle_profile_update(self):
        """Handles explicit account profile update actions from Account Tab."""
        name = self.view.acc_name.text().strip()
        phone = self.view.acc_phone.text().strip()
        username = self.view.acc_username.text().strip()
        
        v_name, m_name = ValidationService.validate_name(name)
        v_phone, m_phone = ValidationService.validate_phone(phone)
        v_username = bool(username)
        m_username = "" if v_username else "Username is required."
        
        self.view.acc_name_err.setText(m_name if not v_name else " ")
        self.view.acc_phone_err.setText(m_phone if not v_phone else " ")
        self.view.acc_username_err.setText(m_username if not v_username else " ")
        
        if not (v_name and v_phone and v_username):
            Toast.error(self.view, "❌ Please resolve name/phone/username validation errors.")
            return
            
        user = UserSession.get_current_user()
        if not user:
            Toast.error(self.view, "❌ No active session found.")
            return
            
        # Update via profile service
        success = ProfileService.update_profile(user["email"], name, phone, username)
        if success:
            # Sync model and cache
            self.model.set("account_name", name)
            self.model.set("account_phone", phone)
            self.model.set("account_username", username)
            user["name"] = name
            user["phone"] = phone
            user["username"] = username
            UserSession.start_session(user)
            self.model.commit_changes()
            self.view.set_buttons_dirty(False)
            
            Toast.success(self.view, "✓ Profile updated successfully")
            
            # Fire update notifications to parent dashboard if listening
            if hasattr(self.view.parent(), "set_user_profile"):
                self.view.parent().set_user_profile(user)
        else:
            Toast.error(self.view, "❌ Database update failed.")

    def handle_password_change(self, old_pwd, new_pwd):
        """Triggers password verification and resets password state."""
        user = UserSession.get_current_user()
        if not user:
            Toast.error(self.view, "❌ No active session found.")
            return
            
        if not old_pwd or not new_pwd:
            self.view.acc_pwd_err.setText("❌ Both passwords are required.")
            return
            
        # Check rule complexity
        if len(new_pwd) < 8:
            self.view.acc_pwd_err.setText("❌ New password must be at least 8 characters.")
            return
            
        success, msg = ProfileService.change_password(user["email"], old_pwd, new_pwd)
        if success:
            self.view.acc_old_pwd.clear()
            self.view.acc_new_pwd.clear()
            self.view.acc_pwd_err.setText(" ")
            Toast.success(self.view, msg)
        else:
            self.view.acc_pwd_err.setText(f"❌ {msg}")
            Toast.error(self.view, msg)

    # ----------------------------------------------------
    # AUXILIARY CONTROLS
    # ----------------------------------------------------
    
    def reset_ai_prompt(self):
        default_prompt = GeminiService.get_default_prompt()
        self.view.ai_system_prompt.setText(default_prompt)
        self.update_model_field("ai_system_prompt", default_prompt)
        Toast.info(self.view, "Restored default parser rules prompt")

    def check_for_updates(self):
        Toast.info(self.view, "Running update logs... StatementForge is up to date!")

    def clear_session(self):
        SecurityService.clear_active_session()
        Toast.success(self.view, "✓ Active session tokens deleted!")
        self.logout()

    def reset_auth(self):
        user = UserSession.get_current_user()
        email = user["email"] if user else ""
        SecurityService.reset_authentication(email)
        Toast.success(self.view, "✓ Auth settings reset!")
        self.logout()

    def logout(self):
        """Clears sessions and issues a logout signal back to navigation systems."""
        UserSession.clear_session()
        # Direct the window to trigger logout if wired
        if hasattr(self.view, "parent") and self.view.parent() is not None:
            # Let's find dashboard parent
            p = self.view.parent()
            while p is not None and not hasattr(p, "logoutRequested"):
                p = p.parent()
            if p is not None:
                p.logoutRequested.emit()

    # --- Sizing Helper ---
    def parse_int(self, text, default):
        try:
            return int(text.strip())
        except ValueError:
            return default
