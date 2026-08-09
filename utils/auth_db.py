import os
import datetime
import bcrypt
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class AuthDB:
    # Dictionary to store registered accounts in memory as a fallback
    _users = {
        "xyz@gmail.com": {
            "name": "Default User",
            "phone": "9999999999",
            "password": "Password123!",
            "hashed_password": None,
            "username": "defaultuser",
            "role": "user",
            "status": "active",
            "created_at": datetime.datetime.utcnow() - datetime.timedelta(days=2)
        }
    }

    _mongo_client = None
    _db = None
    _collection = None
    _mongo_available = False

    @classmethod
    def reset_connection(cls):
        """Resets the cached MongoDB client and database collection references."""
        cls._mongo_client = None
        cls._db = None
        cls._collection = None
        cls._mongo_available = False
        print("AuthDB: Connection references reset.")

    @classmethod
    def get_mongo_collection(cls):
        """Initializes and returns MongoDB collection, or None if unavailable."""
        if cls._mongo_client is not None:
            if cls._mongo_available:
                return cls._collection
            else:
                return None

        # Try to initialize
        uri = os.getenv("MONGODB_URI")
        if not uri or not uri.strip():
            print("AuthDB: MONGODB_URI not found or empty in environment. Using in-memory fallback.")
            cls._mongo_client = "none"
            cls._mongo_available = False
            return None

        try:
            # Short timeout to avoid freezing the UI thread for too long
            cls._mongo_client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            # Run a ping check to verify connectability
            cls._mongo_client.admin.command('ping')
            db_name = os.getenv("MONGODB_DB_NAME", "statementforge")
            cls._db = cls._mongo_client[db_name]
            cls._collection = cls._db["users"]
            cls._mongo_available = True
            print(f"AuthDB: Successfully connected to MongoDB Atlas! (Database: {db_name})")
            return cls._collection
        except Exception as e:
            print(f"AuthDB: Failed to connect to MongoDB Atlas ({e}). Using in-memory fallback.")
            cls._mongo_available = False
            cls._collection = None
            return None

    @classmethod
    def register_user(cls, name, email, phone, password):
        """Registers a user. Returns True if successful, False if email already registered."""
        email_clean = email.strip().lower()

        # Hash password using bcrypt
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)

        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                existing = collection.find_one({"email": email_clean})
                if existing:
                    return False

                user_doc = {
                    "full_name": name.strip(),
                    "email": email_clean,
                    "phone": phone.strip(),
                    "username": email_clean.split('@')[0],
                    "password": hashed_password.decode('utf-8'),
                    "created_at": datetime.datetime.utcnow(),
                    "role": "user",
                    "status": "active"
                }
                collection.insert_one(user_doc)
                return True
            except Exception as e:
                print(f"AuthDB: MongoDB register error ({e}). Falling back to in-memory.")

        # Fallback to local memory dictionary
        if email_clean in cls._users:
            return False
        cls._users[email_clean] = {
            "name": name.strip(),
            "phone": phone.strip(),
            "username": email_clean.split('@')[0],
            "password": password,
            "hashed_password": hashed_password,
            "role": "user",
            "status": "active",
            "created_at": datetime.datetime.utcnow()
        }
        return True

    @classmethod
    def validate_user(cls, email, password):
        """Validates credentials. Returns (success_bool, message_str, user_details_dict)."""
        email_clean = email.strip().lower()
        if not email_clean:
            return False, "Email address is required.", None
        if not password:
            return False, "Password is required.", None

        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                user = collection.find_one({"email": email_clean})
                if not user:
                    if email_clean == "xyz@gmail.com" and password == "Password123!":
                        cls.register_user("Default User", "xyz@gmail.com", "9999999999", "Password123!")
                        user = collection.find_one({"email": email_clean})
                    if not user:
                        return False, f"Account with email '{email}' does not exist.", None

                stored_hash_str = user.get("password", "")
                if not stored_hash_str:
                    return False, "Invalid account state (no password stored).", None

                try:
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash_str.encode('utf-8')):
                        now = datetime.datetime.utcnow()
                        is_first = (user.get("last_login") is None)
                        # Update last_login in MongoDB Atlas
                        collection.update_one({"_id": user["_id"]}, {"$set": {"last_login": now}})
                        
                        user_details = {
                            "id": str(user.get("_id", "")),
                            "name": user.get("full_name", ""),
                            "email": user.get("email", ""),
                            "phone": user.get("phone", ""),
                            "username": user.get("username", user.get("email", "").split('@')[0]),
                            "role": user.get("role", "user"),
                            "status": user.get("status", "active"),
                            "created_at": user.get("created_at", now),
                            "last_login": now,
                            "is_first_login": is_first
                        }
                        return True, "Login successful!", user_details
                except Exception as ex:
                    print(f"Bcrypt verification error: {ex}")

                return False, "Incorrect password. Please try again.", None
            except Exception as e:
                print(f"AuthDB: MongoDB validate error ({e}). Falling back to in-memory.")

        # Fallback to local memory validation
        if email_clean not in cls._users:
            return False, f"Account with email '{email}' does not exist.", None

        user = cls._users[email_clean]
        stored_hash = user.get("hashed_password")
        valid = False
        if stored_hash:
            try:
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                    valid = True
            except Exception:
                pass
        elif user["password"] == password:
            valid = True

        if valid:
            now = datetime.datetime.utcnow()
            is_first = (user.get("last_login") is None)
            user["last_login"] = now
            if "created_at" not in user:
                user["created_at"] = now - datetime.timedelta(days=2)
                
            user_details = {
                "id": email_clean,
                "name": user.get("name", "User"),
                "email": email_clean,
                "phone": user.get("phone", ""),
                "username": user.get("username", email_clean.split('@')[0]),
                "role": user.get("role", "user"),
                "status": user.get("status", "active"),
                "created_at": user.get("created_at", now),
                "last_login": now,
                "is_first_login": is_first
            }
            return True, "Login successful!", user_details

        return False, "Incorrect password. Please try again.", None

    @classmethod
    def user_exists(cls, email):
        """Checks if a user with the specified email address exists."""
        email_clean = email.strip().lower()
        if not email_clean:
            return False

        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                user = collection.find_one({"email": email_clean})
                if user:
                    return True
            except Exception as e:
                print(f"AuthDB: MongoDB user_exists error ({e}).")

        # Fallback to local memory dictionary
        return email_clean in cls._users

    @classmethod
    def reset_password(cls, email, new_password):
        """Resets the password for the specified email. Returns (success, message)."""
        email_clean = email.strip().lower()
        if not email_clean:
            return False, "Email address is required."
        if not new_password:
            return False, "New password is required."

        # Hash password using bcrypt
        password_bytes = new_password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)

        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                user = collection.find_one({"email": email_clean})
                if not user:
                    return False, f"Account with email '{email}' does not exist."
                
                collection.update_one({"email": email_clean}, {"$set": {"password": hashed_password.decode('utf-8')}})
                return True, "Password reset successfully!"
            except Exception as e:
                print(f"AuthDB: MongoDB reset error ({e}). Falling back to in-memory.")

        # Fallback to local memory dictionary
        if email_clean not in cls._users:
            return False, f"Account with email '{email}' does not exist."
        
        cls._users[email_clean]["password"] = new_password
        cls._users[email_clean]["hashed_password"] = hashed_password
        return True, "Password reset successfully!"

    @classmethod
    def get_user_profile(cls, email_or_id):
        """
        Fetches normalized user profile record for the current user.
        Ensures default fallback values for optional profile fields.
        """
        email_clean = str(email_or_id).strip().lower()
        now = datetime.datetime.utcnow()

        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                # Query by email or string _id
                user = collection.find_one({"email": email_clean})
                if not user:
                    # Attempt ObjectId query if needed
                    from bson.objectid import ObjectId
                    try:
                        user = collection.find_one({"_id": ObjectId(email_or_id)})
                    except Exception:
                        pass
                
                if user:
                    has_pwd = bool(user.get("password")) and not user.get("is_google_only", False)
                    return {
                        "id": str(user.get("_id", "")),
                        "name": user.get("full_name", user.get("name", "User")),
                        "email": user.get("email", email_clean),
                        "phone": user.get("phone", ""),
                        "username": user.get("username", user.get("email", "").split('@')[0]),
                        "role": user.get("role", "Administrator" if user.get("role") == "admin" else "User"),
                        "status": user.get("status", "active"),
                        "job_title": user.get("job_title", ""),
                        "department": user.get("department", ""),
                        "bio": user.get("bio", ""),
                        "profile_picture": user.get("profile_picture", ""),
                        "profile_color": user.get("profile_color", "#0037b0"),
                        "timezone": user.get("timezone", "UTC (Coordinated Universal Time)"),
                        "google_id": user.get("google_id", None),
                        "has_password": has_pwd,
                        "email_notifications": user.get("email_notifications", True),
                        "desktop_notifications": user.get("desktop_notifications", True),
                        "statement_notifications": user.get("statement_notifications", True),
                        "created_at": user.get("created_at", now),
                        "last_login": user.get("last_login", now)
                    }
            except Exception as e:
                print(f"AuthDB: Error fetching profile for {email_clean}: {e}")

        # Fallback to local memory dictionary
        if email_clean in cls._users:
            u = cls._users[email_clean]
            has_pwd = bool(u.get("password") or u.get("hashed_password"))
            return {
                "id": email_clean,
                "name": u.get("name", "User"),
                "email": email_clean,
                "phone": u.get("phone", ""),
                "username": u.get("username", email_clean.split('@')[0]),
                "role": u.get("role", "User"),
                "status": u.get("status", "active"),
                "job_title": u.get("job_title", ""),
                "department": u.get("department", ""),
                "bio": u.get("bio", ""),
                "profile_picture": u.get("profile_picture", ""),
                "profile_color": u.get("profile_color", "#0037b0"),
                "timezone": u.get("timezone", "UTC (Coordinated Universal Time)"),
                "google_id": u.get("google_id", None),
                "has_password": has_pwd,
                "email_notifications": u.get("email_notifications", True),
                "desktop_notifications": u.get("desktop_notifications", True),
                "statement_notifications": u.get("statement_notifications", True),
                "created_at": u.get("created_at", now),
                "last_login": u.get("last_login", now)
            }

        # Clean empty fallback structure if user record isn't found
        return {
            "id": email_clean,
            "name": "User",
            "email": email_clean,
            "phone": "",
            "username": email_clean.split('@')[0] if '@' in email_clean else email_clean,
            "role": "User",
            "status": "active",
            "job_title": "",
            "department": "",
            "bio": "",
            "profile_picture": "",
            "profile_color": "#0037b0",
            "timezone": "UTC (Coordinated Universal Time)",
            "google_id": None,
            "has_password": False,
            "email_notifications": True,
            "desktop_notifications": True,
            "statement_notifications": True,
            "created_at": now,
            "last_login": now
        }

    @classmethod
    def update_user_profile(cls, email, profile_dict):
        """
        Updates profile fields for the user identified by email.
        Refuses to update sensitive security credentials (e.g., _id, password).
        """
        email_clean = email.strip().lower()
        allowed_fields = {
            "full_name", "name", "phone", "username", "job_title", 
            "department", "bio", "profile_picture", "profile_color", 
            "timezone", "email_notifications", "desktop_notifications", 
            "statement_notifications", "google_id"
        }
        
        update_payload = {}
        for k, v in profile_dict.items():
            if k in allowed_fields:
                if k == "name":
                    update_payload["full_name"] = v
                else:
                    update_payload[k] = v

        if not update_payload:
            return True

        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                collection.update_one({"email": email_clean}, {"$set": update_payload})
                return True
            except Exception as e:
                print(f"AuthDB: Error updating profile for {email_clean}: {e}")
                return False

        # In-memory fallback
        if email_clean in cls._users:
            for k, v in update_payload.items():
                if k == "full_name":
                    cls._users[email_clean]["name"] = v
                else:
                    cls._users[email_clean][k] = v
            return True
        return False

    @classmethod
    def get_or_create_google_user(cls, email, name, google_id=None, profile_pic=None):
        """
        Authenticates a user via Google.
        If the email is not registered, automatically registers a new account with a random password.
        Returns (success_bool, message_str, user_details_dict).
        """
        import secrets
        email_clean = email.strip().lower()
        if not email_clean:
            return False, "Google account email is missing.", None

        # Check if user exists
        exists = cls.user_exists(email_clean)
        if not exists:
            random_password = secrets.token_urlsafe(16) + "A1!"
            registered = cls.register_user(name, email_clean, "", random_password)
            if not registered:
                return False, "Failed to auto-register Google account.", None

        collection = cls.get_mongo_collection()
        now = datetime.datetime.utcnow()
        if collection is not None:
            try:
                user = collection.find_one({"email": email_clean})
                if user:
                    updates = {"last_login": now}
                    if google_id and not user.get("google_id"):
                        updates["google_id"] = google_id
                    if profile_pic and not user.get("profile_picture"):
                        updates["profile_picture"] = profile_pic
                    collection.update_one({"_id": user["_id"]}, {"$set": updates})
                    
                    profile_details = cls.get_user_profile(email_clean)
                    return True, "Google login successful!", profile_details
            except Exception as e:
                print(f"AuthDB: MongoDB google login error ({e}). Falling back to in-memory.")

        # Fallback to local memory validation
        if email_clean in cls._users:
            user = cls._users[email_clean]
            user["last_login"] = now
            if google_id:
                user["google_id"] = google_id
            if profile_pic and not user.get("profile_picture"):
                user["profile_picture"] = profile_pic
            profile_details = cls.get_user_profile(email_clean)
            return True, "Google login successful!", profile_details

        return False, "Failed to retrieve Google user details.", None

    @classmethod
    def reset_last_login(cls, email):
        """Resets the last_login field for a user back to None."""
        email_clean = email.strip().lower()
        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                collection.update_one({"email": email_clean}, {"$unset": {"last_login": ""}})
                return True
            except Exception as e:
                print(f"AuthDB: Failed to reset last_login ({e})")
        
        # Fallback to local memory dictionary
        if email_clean in cls._users:
            cls._users[email_clean]["last_login"] = None
            return True
        return False



