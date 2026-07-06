import datetime
import bcrypt
from utils.auth_db import AuthDB

class ProfileService:
    @classmethod
    def update_profile(cls, email, name, phone, username):
        """Updates user's personal details in MongoDB Atlas or local fallback."""
        collection = AuthDB.get_mongo_collection()
        if collection is not None:
            try:
                # Update in MongoDB Atlas
                result = collection.update_one(
                    {"email": email.strip().lower()},
                    {"$set": {
                        "full_name": name.strip(),
                        "phone": phone.strip(),
                        "username": username.strip()
                    }}
                )
                return True
            except Exception as e:
                print(f"ProfileService: MongoDB update error: {e}")
                return False
                
        # Local fallback update
        email_clean = email.strip().lower()
        if email_clean in AuthDB._users:
            AuthDB._users[email_clean]["name"] = name.strip()
            AuthDB._users[email_clean]["phone"] = phone.strip()
            AuthDB._users[email_clean]["username"] = username.strip()
            return True
        return False

    @classmethod
    def change_password(cls, email, old_password, new_password):
        """Changes user password after verification. Returns (success_bool, message)."""
        collection = AuthDB.get_mongo_collection()
        if collection is not None:
            try:
                user = collection.find_one({"email": email.strip().lower()})
                if not user:
                    return False, "User account not found."
                
                stored_hash_str = user.get("password", "")
                # Verify old password using bcrypt
                try:
                    if not bcrypt.checkpw(old_password.encode('utf-8'), stored_hash_str.encode('utf-8')):
                        return False, "Incorrect old password."
                except Exception as ex:
                    print(f"Bcrypt verification error: {ex}")
                    # If bcrypt checkpw fails (e.g. invalid format or old password plain text), fallback check:
                    if stored_hash_str != old_password:
                        return False, "Incorrect old password."
                
                # Hash new password
                salt = bcrypt.gensalt()
                new_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
                
                # Update in MongoDB
                collection.update_one(
                    {"email": email.strip().lower()},
                    {"$set": {"password": new_hash}}
                )
                return True, "Password changed successfully."
            except Exception as e:
                print(f"ProfileService: MongoDB password change error: {e}")
                return False, f"Database error: {e}"

        # Local fallback password change
        email_clean = email.strip().lower()
        if email_clean not in AuthDB._users:
            return False, "User account not found."
        
        user = AuthDB._users[email_clean]
        stored_hash = user.get("hashed_password")
        
        valid = False
        # Verify old password
        if stored_hash:
            try:
                if bcrypt.checkpw(old_password.encode('utf-8'), stored_hash):
                    valid = True
            except Exception:
                pass
        elif user["password"] == old_password:
            valid = True

        if not valid:
            return False, "Incorrect old password."
                
        # Hash and set new password
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt)
        AuthDB._users[email_clean]["password"] = new_password
        AuthDB._users[email_clean]["hashed_password"] = new_hash
        return True, "Password changed successfully."
