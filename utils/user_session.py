import json
import os
import datetime

class UserSession:
    """Active session container holding currently logged-in user details."""
    _current_user = None
    _session_file = os.path.join(os.path.expanduser("~"), ".statementforge_session.json")

    @classmethod
    def start_session(cls, user_data):
        """Starts a session with user details dict."""
        cls._current_user = user_data
        cls.save_session(user_data)

    @classmethod
    def get_current_user(cls):
        """Returns active user details dict or None."""
        return cls._current_user

    @classmethod
    def clear_session(cls):
        """Clears active session on logout."""
        cls._current_user = None
        if os.path.exists(cls._session_file):
            try:
                os.remove(cls._session_file)
            except Exception as e:
                print(f"Error removing session file: {e}")

    @classmethod
    def is_active(cls):
        """Checks if there is an active session."""
        return cls._current_user is not None

    @classmethod
    def save_session(cls, user_data):
        """Persists the user session to disk."""
        try:
            # Serialize datetimes
            serializable_data = {}
            for k, v in user_data.items():
                if isinstance(v, datetime.datetime):
                    serializable_data[k] = {"__datetime__": v.isoformat()}
                else:
                    serializable_data[k] = v
            
            with open(cls._session_file, "w", encoding="utf-8") as f:
                json.dump(serializable_data, f)
        except Exception as e:
            print(f"Error saving session: {e}")

    @classmethod
    def load_session(cls):
        """Loads a persisted session from disk and sets active user."""
        if not os.path.exists(cls._session_file):
            return None
        try:
            with open(cls._session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Deserialize datetimes
            user_data = {}
            for k, v in data.items():
                if isinstance(v, dict) and "__datetime__" in v:
                    user_data[k] = datetime.datetime.fromisoformat(v["__datetime__"])
                else:
                    user_data[k] = v
            
            cls._current_user = user_data
            return user_data
        except Exception as e:
            print(f"Error loading session: {e}")
            return None
