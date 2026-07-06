class UserSession:
    """Active session container holding currently logged-in user details."""
    _current_user = None

    @classmethod
    def start_session(cls, user_data):
        """Starts a session with user details dict."""
        cls._current_user = user_data

    @classmethod
    def get_current_user(cls):
        """Returns active user details dict or None."""
        return cls._current_user

    @classmethod
    def clear_session(cls):
        """Clears active session on logout."""
        cls._current_user = None

    @classmethod
    def is_active(cls):
        """Checks if there is an active session."""
        return cls._current_user is not None
