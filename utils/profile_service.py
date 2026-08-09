import datetime
import bcrypt
from utils.auth_db import AuthDB
from utils.user_session import UserSession

class ProfileService:
    """
    Business service layer managing user profile retrieval, full field updates,
    password modification/creation, notification preferences, and Google linking.
    """

    @classmethod
    def get_profile(cls, email):
        """
        Retrieves real normalized user profile dictionary from the database/AuthDB.
        """
        if not email:
            user = UserSession.get_current_user()
            if user:
                email = user.get("email", "")
            else:
                return AuthDB.get_user_profile("")
        
        return AuthDB.get_user_profile(email)

    @classmethod
    def update_profile(cls, email, name, phone, username, job_title="", department="", bio="", profile_picture="", profile_color="#0037b0", timezone="UTC (Coordinated Universal Time)"):
        """
        Updates user's personal details in MongoDB Atlas or local fallback.
        Also synchronizes active session data.
        """
        email_clean = email.strip().lower() if email else ""
        if not email_clean:
            user = UserSession.get_current_user()
            if user:
                email_clean = user.get("email", "").strip().lower()
            else:
                return False, "No active user email provided."

        update_dict = {
            "name": name.strip(),
            "full_name": name.strip(),
            "phone": phone.strip(),
            "username": username.strip(),
            "job_title": job_title.strip(),
            "department": department.strip(),
            "bio": bio.strip(),
            "profile_picture": profile_picture.strip(),
            "profile_color": profile_color.strip() if profile_color else "#0037b0",
            "timezone": timezone.strip() if timezone else "UTC (Coordinated Universal Time)"
        }

        success = AuthDB.update_user_profile(email_clean, update_dict)
        if success:
            # Sync active session immediately
            UserSession.update_session_user({
                "name": name.strip(),
                "phone": phone.strip(),
                "username": username.strip(),
                "job_title": job_title.strip(),
                "department": department.strip(),
                "bio": bio.strip(),
                "profile_picture": profile_picture.strip(),
                "profile_color": profile_color.strip() if profile_color else "#0037b0",
                "timezone": timezone.strip() if timezone else "UTC (Coordinated Universal Time)"
            })
            return True, "Profile updated successfully!"
        return False, "Failed to save profile changes to database."

    @classmethod
    def set_password(cls, email, new_password):
        """
        Sets a new local password for users originally created via Google OAuth.
        Returns (success_bool, message_str).
        """
        if not new_password or len(new_password) < 8:
            return False, "Password must be at least 8 characters long."

        email_clean = email.strip().lower() if email else ""
        if not email_clean:
            user = UserSession.get_current_user()
            if user:
                email_clean = user.get("email", "").strip().lower()
            else:
                return False, "No active user session."

        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')

        collection = AuthDB.get_mongo_collection()
        if collection is not None:
            try:
                collection.update_one(
                    {"email": email_clean},
                    {"$set": {"password": new_hash, "is_google_only": False}}
                )
                UserSession.update_session_user({"has_password": True})
                return True, "Password configured successfully!"
            except Exception as e:
                print(f"ProfileService: MongoDB set_password error: {e}")
                return False, f"Database error: {e}"

        # Local memory dictionary fallback
        if email_clean in AuthDB._users:
            AuthDB._users[email_clean]["password"] = new_password
            AuthDB._users[email_clean]["hashed_password"] = new_hash.encode('utf-8')
            UserSession.update_session_user({"has_password": True})
            return True, "Password configured successfully!"

        return False, "User account not found."

    @classmethod
    def change_password(cls, email, old_password, new_password):
        """
        Changes user password after verifying current password. Returns (success_bool, message_str).
        """
        if not new_password or len(new_password) < 8:
            return False, "New password must be at least 8 characters long."

        email_clean = email.strip().lower() if email else ""
        if not email_clean:
            user = UserSession.get_current_user()
            if user:
                email_clean = user.get("email", "").strip().lower()
            else:
                return False, "No active user session."

        collection = AuthDB.get_mongo_collection()
        if collection is not None:
            try:
                user_doc = collection.find_one({"email": email_clean})
                if not user_doc:
                    return False, "User account not found."

                stored_hash_str = user_doc.get("password", "")
                if stored_hash_str:
                    try:
                        if not bcrypt.checkpw(old_password.encode('utf-8'), stored_hash_str.encode('utf-8')):
                            return False, "Incorrect current password."
                    except Exception as ex:
                        print(f"Bcrypt verification error: {ex}")
                        if stored_hash_str != old_password:
                            return False, "Incorrect current password."
                
                # Hash and save new password
                salt = bcrypt.gensalt()
                new_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
                
                collection.update_one(
                    {"email": email_clean},
                    {"$set": {"password": new_hash, "is_google_only": False}}
                )
                UserSession.update_session_user({"has_password": True})
                return True, "Password updated successfully!"
            except Exception as e:
                print(f"ProfileService: MongoDB password change error: {e}")
                return False, f"Database error: {e}"

        # Local fallback password change
        if email_clean not in AuthDB._users:
            return False, "User account not found."
        
        user_item = AuthDB._users[email_clean]
        stored_hash = user_item.get("hashed_password")
        
        valid = False
        if stored_hash:
            try:
                if bcrypt.checkpw(old_password.encode('utf-8'), stored_hash):
                    valid = True
            except Exception:
                pass
        elif user_item.get("password") == old_password:
            valid = True

        if not valid:
            return False, "Incorrect current password."
                
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt)
        AuthDB._users[email_clean]["password"] = new_password
        AuthDB._users[email_clean]["hashed_password"] = new_hash
        UserSession.update_session_user({"has_password": True})
        return True, "Password updated successfully!"

    @classmethod
    def update_notifications(cls, email, email_notif, desktop_notif, statement_notif):
        """
        Updates notification settings preferences in database and active session.
        """
        email_clean = email.strip().lower() if email else ""
        if not email_clean:
            user = UserSession.get_current_user()
            if user:
                email_clean = user.get("email", "").strip().lower()

        notif_dict = {
            "email_notifications": bool(email_notif),
            "desktop_notifications": bool(desktop_notif),
            "statement_notifications": bool(statement_notif)
        }
        
        success = AuthDB.update_user_profile(email_clean, notif_dict)
        if success:
            UserSession.update_session_user(notif_dict)
            return True, "Notification preferences saved!"
        return False, "Failed to update notification preferences."

    @classmethod
    def disconnect_google(cls, email):
        """
        Disconnects Google OAuth linking from user account if a local password exists.
        """
        email_clean = email.strip().lower() if email else ""
        if not email_clean:
            user = UserSession.get_current_user()
            if user:
                email_clean = user.get("email", "").strip().lower()

        profile = AuthDB.get_user_profile(email_clean)
        if not profile.get("has_password"):
            return False, "Cannot disconnect Google account without setting a local password first."

        collection = AuthDB.get_mongo_collection()
        if collection is not None:
            try:
                collection.update_one({"email": email_clean}, {"$unset": {"google_id": ""}})
                UserSession.update_session_user({"google_id": None})
                return True, "Google account disconnected successfully."
            except Exception as e:
                return False, f"Failed to disconnect Google account: {e}"

        if email_clean in AuthDB._users:
            AuthDB._users[email_clean]["google_id"] = None
            UserSession.update_session_user({"google_id": None})
            return True, "Google account disconnected successfully."

        return False, "User record not found."
