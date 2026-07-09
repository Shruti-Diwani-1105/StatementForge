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
            cls._db = cls._mongo_client["statementforge"]
            cls._collection = cls._db["users"]
            cls._mongo_available = True
            print("AuthDB: Successfully connected to MongoDB Atlas!")
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
                            "last_login": now
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
                "last_login": now
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
    def get_or_create_google_user(cls, email, name):
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
            # Generate a secure random password for the user record
            random_password = secrets.token_urlsafe(16) + "A1!"
            registered = cls.register_user(name, email_clean, "", random_password)
            if not registered:
                return False, "Failed to auto-register Google account.", None

        # Login/validate user details without checking password
        collection = cls.get_mongo_collection()
        now = datetime.datetime.utcnow()
        if collection is not None:
            try:
                user = collection.find_one({"email": email_clean})
                if user:
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
                        "last_login": now
                    }
                    return True, "Google login successful!", user_details
            except Exception as e:
                print(f"AuthDB: MongoDB google login error ({e}). Falling back to in-memory.")

        # Fallback to local memory validation
        if email_clean in cls._users:
            user = cls._users[email_clean]
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
                "last_login": now
            }
            return True, "Google login successful!", user_details

        return False, "Failed to retrieve Google user details.", None


