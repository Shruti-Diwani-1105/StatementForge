import datetime
import json
import os
import uuid
from bson.objectid import ObjectId
from services.mongodb_service import MongoDBService

NOTIFICATIONS_FALLBACK_FILE = os.path.expanduser("~/.statementforge_notifications.json")
PREFERENCES_FALLBACK_FILE = os.path.expanduser("~/.statementforge_notification_prefs.json")

class NotificationService:
    """Manages notification persistence, filtering, unread counting, and preferences."""

    _local_notifications = []
    _local_prefs = {}
    _loaded = False

    @classmethod
    def _load_local_fallback(cls):
        if cls._loaded:
            return
        cls._loaded = True
        if os.path.exists(NOTIFICATIONS_FALLBACK_FILE):
            try:
                with open(NOTIFICATIONS_FALLBACK_FILE, "r") as f:
                    cls._local_notifications = json.load(f)
            except Exception as e:
                print(f"NotificationService: Error loading fallback notifications: {e}")

        if os.path.exists(PREFERENCES_FALLBACK_FILE):
            try:
                with open(PREFERENCES_FALLBACK_FILE, "r") as f:
                    cls._local_prefs = json.load(f)
            except Exception as e:
                print(f"NotificationService: Error loading fallback preferences: {e}")

    @classmethod
    def _save_local_notifications(cls):
        try:
            with open(NOTIFICATIONS_FALLBACK_FILE, "w") as f:
                json.dump(cls._local_notifications, f, indent=4)
        except Exception as e:
            print(f"NotificationService: Error saving fallback notifications: {e}")

    @classmethod
    def _save_local_prefs(cls):
        try:
            with open(PREFERENCES_FALLBACK_FILE, "w") as f:
                json.dump(cls._local_prefs, f, indent=4)
        except Exception as e:
            print(f"NotificationService: Error saving fallback preferences: {e}")

    @classmethod
    def get_notification_preferences(cls, user_id="guest"):
        """Returns notification settings toggles for the specified user."""
        cls._load_local_fallback()
        
        # 1. MongoDB Check
        col = MongoDBService.get_collection("notification_preferences")
        if col is not None:
            try:
                doc = col.find_one({"user_id": str(user_id)})
                if doc:
                    return doc.get("preferences", cls.get_default_preferences())
            except Exception as e:
                print(f"NotificationService: Failed to get MongoDB preferences: {e}")

        # 2. Local Fallback Check
        return cls._local_prefs.get(str(user_id), cls.get_default_preferences())

    @classmethod
    def get_default_preferences(cls):
        return {
            "ntCompleted": True,
            "ntExport": True,
            "ntErrors": True,
            "ntEmail": True,
            "ntAi": True,
            "ntUpdates": True
        }

    @classmethod
    def save_notification_preferences(cls, user_id, prefs_dict):
        """Saves updated notification preferences for user."""
        cls._load_local_fallback()
        user_id_str = str(user_id)
        
        col = MongoDBService.get_collection("notification_preferences")
        if col is not None:
            try:
                col.update_one(
                    {"user_id": user_id_str},
                    {"$set": {"user_id": user_id_str, "preferences": prefs_dict, "updated_at": datetime.datetime.utcnow().isoformat()}},
                    upsert=True
                )
            except Exception as e:
                print(f"NotificationService: Failed to save MongoDB preferences: {e}")

        cls._local_prefs[user_id_str] = prefs_dict
        cls._save_local_prefs()
        return True

    @classmethod
    def is_notification_type_enabled(cls, user_id, category):
        """Checks if a notification category is enabled in user settings."""
        prefs = cls.get_notification_preferences(user_id)
        category_map = {
            "parsing_export": "ntCompleted",
            "ai_risk": "ntAi",
            "system_security": "ntUpdates",
            "email": "ntEmail",
            "export": "ntExport",
            "error": "ntErrors"
        }
        key = category_map.get(category, "ntCompleted")
        return prefs.get(key, True)

    @classmethod
    def create_notification(cls, user_id, category, title, message, action_type=None, action_url=None, related_statement_id=None):
        """
        Creates a new notification after checking user preferences.
        Categories: 'ai_risk', 'parsing_export', 'system_security'
        """
        if not user_id:
            user_id = "guest"
            
        cls._load_local_fallback()

        # Respect user preferences
        if not cls.is_notification_type_enabled(user_id, category):
            return None

        now = datetime.datetime.utcnow()
        doc = {
            "user_id": str(user_id),
            "category": category,
            "title": title,
            "message": message,
            "created_at": now.isoformat(),
            "is_read": False,
            "is_dismissed": False,
            "action_type": action_type or "",
            "action_url": action_url or "",
            "related_statement_id": related_statement_id or ""
        }

        # 1. MongoDB Save
        col = MongoDBService.get_collection("notifications")
        if col is not None:
            try:
                mongo_doc = doc.copy()
                mongo_doc["created_at_dt"] = now
                res = col.insert_one(mongo_doc)
                doc["_id"] = str(res.inserted_id)
                return doc["_id"]
            except Exception as e:
                print(f"NotificationService: Failed to save MongoDB notification: {e}")

        # 2. Local Fallback
        doc["_id"] = str(uuid.uuid4())
        cls._local_notifications.append(doc)
        cls._save_local_notifications()
        return doc["_id"]

    @classmethod
    def get_user_notifications(cls, user_id="guest", category="all", include_dismissed=False):
        """Retrieves notifications for a given user filtered by category."""
        cls._load_local_fallback()
        user_id_str = str(user_id)
        
        # 1. MongoDB Query
        col = MongoDBService.get_collection("notifications")
        if col is not None:
            try:
                query = {"user_id": user_id_str}
                if not include_dismissed:
                    query["is_dismissed"] = {"$ne": True}
                if category and category != "all":
                    query["category"] = category
                    
                cursor = col.find(query).sort("created_at", -1)
                results = []
                for item in cursor:
                    item["_id"] = str(item["_id"])
                    if "created_at_dt" in item:
                        del item["created_at_dt"]
                    results.append(item)
                return results
            except Exception as e:
                print(f"NotificationService: Failed to query MongoDB notifications: {e}")

        # 2. Local Fallback Query
        results = []
        for n in cls._local_notifications:
            if str(n.get("user_id")) == user_id_str:
                if not include_dismissed and n.get("is_dismissed"):
                    continue
                if category and category != "all" and n.get("category") != category:
                    continue
                results.append(n)
        
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    @classmethod
    def get_unread_count(cls, user_id="guest"):
        """Calculates active unread notifications count for the TopBar badge."""
        cls._load_local_fallback()
        user_id_str = str(user_id)
        
        col = MongoDBService.get_collection("notifications")
        if col is not None:
            try:
                return col.count_documents({
                    "user_id": user_id_str,
                    "is_read": False,
                    "is_dismissed": {"$ne": True}
                })
            except Exception:
                pass

        count = 0
        for n in cls._local_notifications:
            if str(n.get("user_id")) == user_id_str and not n.get("is_read") and not n.get("is_dismissed"):
                count += 1
        return count

    @classmethod
    def mark_as_read(cls, user_id, notification_id):
        """Marks a single notification as read."""
        cls._load_local_fallback()
        user_id_str = str(user_id)

        col = MongoDBService.get_collection("notifications")
        if col is not None:
            try:
                try:
                    obj_id = ObjectId(notification_id)
                    col.update_one({"_id": obj_id, "user_id": user_id_str}, {"$set": {"is_read": True}})
                except Exception:
                    col.update_one({"_id": notification_id, "user_id": user_id_str}, {"$set": {"is_read": True}})
            except Exception as e:
                print(f"NotificationService: Failed to mark MongoDB notification as read: {e}")

        for n in cls._local_notifications:
            if str(n.get("_id")) == str(notification_id) and str(n.get("user_id")) == user_id_str:
                n["is_read"] = True
                cls._save_local_notifications()
                break
        return True

    @classmethod
    def mark_all_as_read(cls, user_id):
        """Marks all active notifications for user as read."""
        cls._load_local_fallback()
        user_id_str = str(user_id)

        col = MongoDBService.get_collection("notifications")
        if col is not None:
            try:
                col.update_many({"user_id": user_id_str, "is_dismissed": {"$ne": True}}, {"$set": {"is_read": True}})
            except Exception as e:
                print(f"NotificationService: Failed to mark all MongoDB notifications as read: {e}")

        for n in cls._local_notifications:
            if str(n.get("user_id")) == user_id_str and not n.get("is_dismissed"):
                n["is_read"] = True
        cls._save_local_notifications()
        return True

    @classmethod
    def dismiss_notification(cls, user_id, notification_id):
        """Dismisses a single notification from view."""
        cls._load_local_fallback()
        user_id_str = str(user_id)

        col = MongoDBService.get_collection("notifications")
        if col is not None:
            try:
                try:
                    obj_id = ObjectId(notification_id)
                    col.update_one({"_id": obj_id, "user_id": user_id_str}, {"$set": {"is_dismissed": True}})
                except Exception:
                    col.update_one({"_id": notification_id, "user_id": user_id_str}, {"$set": {"is_dismissed": True}})
            except Exception as e:
                print(f"NotificationService: Failed to dismiss MongoDB notification: {e}")

        for n in cls._local_notifications:
            if str(n.get("_id")) == str(notification_id) and str(n.get("user_id")) == user_id_str:
                n["is_dismissed"] = True
                cls._save_local_notifications()
                break
        return True

    @classmethod
    def dismiss_all(cls, user_id):
        """Dismisses all active notifications for user."""
        cls._load_local_fallback()
        user_id_str = str(user_id)

        col = MongoDBService.get_collection("notifications")
        if col is not None:
            try:
                col.update_many({"user_id": user_id_str}, {"$set": {"is_dismissed": True}})
            except Exception as e:
                print(f"NotificationService: Failed to dismiss all MongoDB notifications: {e}")

        for n in cls._local_notifications:
            if str(n.get("user_id")) == user_id_str:
                n["is_dismissed"] = True
        cls._save_local_notifications()
        return True
