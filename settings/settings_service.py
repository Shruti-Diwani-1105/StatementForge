import os
import json
from pymongo import MongoClient
from utils.auth_db import AuthDB
from settings.appearance_service import AppearanceService

class SettingsService:
    """
    Coordinates loading, caching, syncing, and persisting settings
    between MongoDB Atlas, local JSON backup files, and the application.
    """
    _cached_settings = {}
    _local_backup_dir = os.path.expanduser("~")

    @classmethod
    def get_local_path(cls, user_email):
        """Generates a user-specific local cache filename."""
        clean_email = user_email.replace("@", "_").replace(".", "_")
        return os.path.join(cls._local_backup_dir, f".statementforge_settings_{clean_email}.json")

    @classmethod
    def load_settings(cls, user_details):
        """
        Loads settings for a user. Attempts MongoDB Atlas first,
        then falls back to local JSON cache, and finally returns empty dict.
        """
        if not user_details:
            return {}

        email = user_details.get("email")
        if not email:
            return {}

        # 1. Try to read from MongoDB Atlas settings collection
        collection = cls._get_settings_collection()
        if collection is not None:
            try:
                doc = collection.find_one({"email": email})
                if doc:
                    # Strip mongo metadata
                    if "_id" in doc:
                        del doc["_id"]
                    # Force default theme to Light on login load
                    doc["app_theme"] = "Light"
                    doc["theme"] = "Light"
                    cls._cached_settings = doc
                    cls._save_local_cache(email, doc) # keep local copy updated
                    return doc
            except Exception as e:
                print(f"SettingsService: MongoDB read failed ({e}). Falling back to local cache.")

        # 2. Fall back to local JSON backup
        local_data = cls._load_local_cache(email)
        if local_data:
            local_data["app_theme"] = "Light"
            local_data["theme"] = "Light"
            cls._cached_settings = local_data
            return local_data

        # 3. No configurations found (use model defaults)
        return {}

    @classmethod
    def save_settings(cls, user_details, settings_dict):
        """
        Saves settings for the logged-in user.
        Persists to MongoDB Atlas and also writes to local JSON cache backup.
        """
        if not user_details:
            return False, "No active user session."

        email = user_details.get("email")
        if not email:
            return False, "Invalid user email."

        # Keep email synced in settings document
        settings_dict["account_email"] = email
        settings_dict["account_username"] = user_details.get("username", "")
        settings_dict["account_name"] = user_details.get("name", "")
        settings_dict["account_phone"] = user_details.get("phone", "")
        settings_dict["account_role"] = user_details.get("role", "User")
        
        # Cache in memory
        cls._cached_settings = settings_dict

        # Save to local JSON backup (always, so offline state is maintained)
        cls._save_local_cache(email, settings_dict)

        # Save to MongoDB Atlas settings collection
        collection = cls._get_settings_collection()
        if collection is not None:
            try:
                # Upsert settings
                collection.update_one(
                    {"email": email},
                    {"$set": settings_dict},
                    upsert=True
                )
                return True, "✓ Settings saved and synced with MongoDB Atlas successfully!"
            except Exception as e:
                print(f"SettingsService: MongoDB save failed: {e}")
                return True, "✓ Settings saved locally (database currently offline)."

        return True, "✓ Settings saved locally (database connection unavailable)."

    @classmethod
    def apply_settings_instantly(cls, settings_dict):
        """Applies layout, visual, and theme settings immediately."""
        theme = (settings_dict.get("app_theme") or settings_dict.get("theme") or "System").lower()
        if theme == "system":
            # For system theme, read current global application theme
            from utils.theme_manager import ThemeManager
            theme = ThemeManager.get_theme()
            
        accent = settings_dict.get("app_accent_color", "blue")
        font_size = settings_dict.get("app_font_size", "Medium")
        
        # Apply theme stylesheet, custom color, and font scale immediately
        AppearanceService.apply_appearance(theme, accent, font_size)

        # Sync with global ThemeManager and persist in theme setting json
        from utils.theme_manager import ThemeManager
        ThemeManager._current_theme = theme
        try:
            with open(ThemeManager._theme_file, "w", encoding="utf-8") as f:
                json.dump({"theme": theme}, f)
        except Exception:
            pass

        # Propagate theme styles to navigation windows
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if hasattr(widget, "sync_theme_styles"):
                    widget.sync_theme_styles(theme)

    @classmethod
    def get_cached_settings(cls):
        """Returns in-memory settings cache."""
        return cls._cached_settings

    # --- Private Helpers ---

    @classmethod
    def _get_settings_collection(cls):
        """Initializes and returns settings collection client."""
        # Try to reuse MongoClient connection from AuthDB
        uri = os.getenv("MONGODB_URI")
        if not uri or not uri.strip():
            return None
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            client.admin.command('ping')
            db = client["statementforge"]
            return db["settings"]
        except Exception:
            return None

    @classmethod
    def _save_local_cache(cls, email, data):
        """Saves configuration copy to local JSON file."""
        try:
            path = cls.get_local_path(email)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"SettingsService: Error saving local cache: {e}")

    @classmethod
    def _load_local_cache(cls, email):
        """Loads configuration from local JSON backup."""
        path = cls.get_local_path(email)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"SettingsService: Error reading local cache: {e}")
            return None
