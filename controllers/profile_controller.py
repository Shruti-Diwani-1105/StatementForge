from PyQt6.QtCore import QObject
from utils.user_session import UserSession
from utils.profile_service import ProfileService

class ProfileController(QObject):
    """
    ProfileController mediates interactions between ProfileWindow (View)
    and ProfileService (Model), keeping UserSession synchronized.
    """
    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self.connect_signals()

    def connect_signals(self):
        self.view.save_requested.connect(self.handle_save_changes)
        self.view.password_change_requested.connect(self.handle_change_password)

    def handle_save_changes(self, name, phone, username):
        user = UserSession.get_current_user()
        if not user:
            self.view.show_error("No active user session found.")
            return

        success = ProfileService.update_profile(user["email"], name, phone, username)
        if success:
            # Sync user details in the current session
            user["name"] = name
            user["phone"] = phone
            user["username"] = username
            UserSession.start_session(user)

            # Refresh view representation
            self.view.load_user_data(user)
            
            # Show modern green success toast
            self.view.show_success_toast("Profile updated successfully")
            
            # Notify navigation system
            self.view.profile_updated.emit(user)
        else:
            self.view.show_error("Could not update profile in database.")

    def handle_change_password(self, old_pwd, new_pwd):
        user = UserSession.get_current_user()
        if not user:
            self.view.show_error("No active user session found.")
            return

        success, message = ProfileService.change_password(user["email"], old_pwd, new_pwd)
        if success:
            self.view.show_success_toast(message)
            self.view.clear_password_fields()
        else:
            self.view.show_error(message)
