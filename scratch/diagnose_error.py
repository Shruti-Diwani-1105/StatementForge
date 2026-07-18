import os
import sys
import traceback
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from utils.user_session import UserSession
from settings.settings_service import SettingsService

def diagnose():
    print("Running diagnostic session check...")
    user = UserSession.load_session()
    if not user:
        print("No active local session file. Trying to load a user from AuthDB/MongoDB...")
        from utils.auth_db import AuthDB
        users = AuthDB.get_collection().find()
        user = next(users, None)
        if user:
            print(f"Loaded mock user: {user.get('email')}")
            UserSession.start_session(user)
        else:
            print("No users found in database.")
            return

    print("\n--- USER SESSION KEYS AND TYPES ---")
    for k, v in user.items():
        print(f"Key: {k} | Type: {type(v)} | Value: {str(v)[:100]}")

    print("\n--- LOADING SETTINGS ---")
    try:
        # Load settings
        from pymongo import MongoClient
        uri = os.getenv("MONGODB_URI")
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        db = client["statementforge"]
        collection = db["settings"]
        doc = collection.find_one({"email": user["email"]})
        if doc:
            print("\n--- MONGODB SETTINGS DOCUMENT KEYS AND TYPES ---")
            for k, v in doc.items():
                print(f"Key: {k} | Type: {type(v)} | Value: {str(v)[:100]}")
        else:
            print("No settings document found in MongoDB settings collection.")
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()
