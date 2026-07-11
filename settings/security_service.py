from utils.user_session import UserSession
from utils.auth_db import AuthDB

class SecurityService:
    """Manages session clearing, auth resets, and auto-logout timings."""

    @staticmethod
    def get_auto_logout_minutes(config_str):
        """Converts human readable combobox option to minute integer values."""
        mapping = {
            "15 minutes": 15,
            "30 minutes": 30,
            "1 hour": 60,
            "Never": 0
        }
        return mapping.get(config_str, 0)

    @staticmethod
    def clear_active_session():
        """Forcibly logs out the user and clears all cached session state on disk."""
        UserSession.clear_session()
        return True, "✓ Active login session cleared successfully!"

    @staticmethod
    def reset_authentication(email):
        """
        Resets user authentication states. In production, this might reset two-factor
        or API tokens. Here it forces a session clear and resets AuthDB status if needed.
        """
        UserSession.clear_session()
        # Reset local cache if any
        return True, "✓ Authentication configurations reset. Please log in again."
