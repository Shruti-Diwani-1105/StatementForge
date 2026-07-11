import copy

class SettingsModel:
    """
    Data model representing all configurations inside the Settings module.
    Organized into logical groups. Tracks original state to check if modified.
    """
    def __init__(self):
        self._defaults = {
            # General
            "app_name": "StatementForge",
            "app_version": "1.0",
            "save_location": "exports",
            "language": "English (US/UK)",
            "theme": "Light",  # Light, Dark, System
            "auto_save": True,
            
            # Account (Cached from active UserSession usually, but managed here)
            "account_username": "",
            "account_name": "",
            "account_email": "",
            "account_phone": "",
            "account_role": "User",
            "account_created_at": "",
            
            # AI Configuration
            "ai_enabled": False,
            "ai_api_key": "",
            "ai_model": "Gemini 2.5 Flash",
            "ai_temperature": 70,  # mapped to slider (0-200) representing 0.7
            "ai_max_tokens": 2048,
            "ai_top_p": 95,  # mapped to slider (0-100) representing 0.95
            "ai_top_k": 40,
            "ai_system_prompt": (
                "You are a professional financial statements parser. "
                "Extract transaction rows accurately including Date, Narration, Reference, Debit, Credit, and Balance."
            ),
            
            # Statement Processing
            "sp_ocr_enabled": True,
            "sp_ocr_engine": "Tesseract",
            "sp_deskew": True,
            "sp_noise_removal": True,
            "sp_threshold": True,
            "sp_auto_detect_bank": True,
            "sp_merge_narration": True,
            "sp_remove_duplicate_spaces": True,
            "sp_detect_period": True,
            "sp_date_format_detection": True,
            "sp_currency_detection": True,
            "sp_confidence_score": 85,
            
            # Export Settings
            "exp_format": "Excel",
            "exp_freeze_header": True,
            "exp_auto_width": True,
            "exp_bold_header": True,
            "exp_alt_row_color": True,
            "exp_currency_formatting": True,
            "exp_summary_sheet": True,
            "exp_filename_pattern": "{Bank}{Month}{Year}",
            "exp_save_folder": "exports",
            
            # Database
            "db_mongodb_uri": "",
            "db_name": "statementforge",
            "db_cluster": "Cluster0",
            
            # Email
            "email_smtp_server": "smtp.gmail.com",
            "email_smtp_port": "587",
            "email_sender": "",
            "email_password": "",
            "email_subject": "Parsed Bank Statement Report",
            "email_signature": "Sent automatically via StatementForge Accounting Hub.",
            
            # Appearance
            "app_theme": "Light",  # Light, Dark, System
            "app_accent_color": "blue",  # blue, green, purple, orange
            "app_font_size": "Medium",  # Small, Medium, Large
            "app_sidebar_layout": "Expanded",  # Expanded, Compact
            "app_animations": True,
            "app_density": "Comfortable",  # Comfortable, Compact
            
            # Notifications
            "nt_statement_completed": True,
            "nt_export_completed": True,
            "nt_errors": True,
            "nt_email_sent": True,
            "nt_ai_finished": True,
            "nt_updates_available": True,
            
            # Security
            "sec_remember_login": True,
            "sec_auto_logout": "Never",  # 15 minutes, 30 minutes, 1 hour, Never
            "sec_password_encryption": "bcrypt",
            "sec_session_timeout": 30,
        }
        
        # Load default state
        self._current_state = copy.deepcopy(self._defaults)
        self._original_state = copy.deepcopy(self._defaults)

    def load_from_dict(self, data_dict):
        """Loads settings from database dictionary representation."""
        if not data_dict:
            return
            
        for key in self._defaults:
            if key in data_dict:
                self._current_state[key] = copy.deepcopy(data_dict[key])
                
        # Set original state to loaded state to reset dirty checks
        self._original_state = copy.deepcopy(self._current_state)

    def to_dict(self):
        """Serializes current settings to dictionary."""
        return copy.deepcopy(self._current_state)

    def get(self, key):
        """Retrieves a configuration value."""
        return self._current_state.get(key, self._defaults.get(key))

    def set(self, key, value):
        """Sets a configuration value."""
        if key in self._current_state:
            self._current_state[key] = value

    def restore_defaults(self):
        """Resets current state to original default values."""
        self._current_state = copy.deepcopy(self._defaults)

    def is_dirty(self):
        """Checks if current state differs from the original (saved) state."""
        for key in self._defaults:
            if self._current_state[key] != self._original_state[key]:
                return True
        return False

    def commit_changes(self):
        """Syncs original state to current state (after successful save)."""
        self._original_state = copy.deepcopy(self._current_state)

    def rollback_changes(self):
        """Rollbacks current modifications to last saved original state."""
        self._current_state = copy.deepcopy(self._original_state)
