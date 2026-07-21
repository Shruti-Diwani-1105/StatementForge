import os
import json
import uuid
import datetime
from bson.objectid import ObjectId
from services.mongodb_service import MongoDBService

EMAIL_HISTORY_FALLBACK_FILE = os.path.expanduser("~/.statementforge_email_history.json")

class EmailRepository:
    """
    Manages persistence for sent/failed email logs.
    Persists to MongoDB Atlas (if available) with automatic fallback to local JSON.
    Never stores email passwords or sensitive credentials.
    """

    _local_fallback_logs = []
    _loaded = False

    @classmethod
    def _load_local_fallback(cls):
        if cls._loaded:
            return
        cls._loaded = True
        if os.path.exists(EMAIL_HISTORY_FALLBACK_FILE):
            try:
                with open(EMAIL_HISTORY_FALLBACK_FILE, "r", encoding="utf-8") as f:
                    cls._local_fallback_logs = json.load(f)
            except Exception as e:
                print(f"EmailRepository: Error loading local fallback logs: {e}")

    @classmethod
    def _save_local_fallback(cls):
        try:
            with open(EMAIL_HISTORY_FALLBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(cls._local_fallback_logs, f, indent=4)
        except Exception as e:
            print(f"EmailRepository: Error saving local fallback logs: {e}")

    @classmethod
    def save_email_log(cls, user_id, recipient_email, cc, bcc, subject, report_type, attachment_name, attachment_paths, status="Sent", error_message="", body="", log_id=None):
        """
        Creates or updates an email history record (supporting 'Sent', 'Failed', 'Draft').
        """
        cls._load_local_fallback()
        now = datetime.datetime.utcnow()
        
        if isinstance(attachment_paths, list):
            att_paths_str = "; ".join(attachment_paths)
        else:
            att_paths_str = str(attachment_paths or "")

        doc_id = log_id or str(uuid.uuid4())

        doc = {
            "id": doc_id,
            "user_id": user_id or "guest",
            "recipient_email": recipient_email or "",
            "cc": cc or "",
            "bcc": bcc or "",
            "subject": subject or "",
            "body": body or "",
            "report_type": report_type or "General Report",
            "attachment_name": attachment_name or "",
            "attachment_paths": att_paths_str,
            "sent_at": now.isoformat(),
            "status": status,  # "Sent", "Failed", or "Draft"
            "error_message": error_message or ""
        }

        # 1. MongoDB Save/Update if available
        col = cls._get_collection()
        if col is not None:
            try:
                mongo_doc = doc.copy()
                mongo_doc["sent_at"] = now
                col.update_one({"id": doc_id}, {"$set": mongo_doc}, upsert=True)
            except Exception as e:
                print(f"EmailRepository: MongoDB save failed: {e}")

        # 2. Local JSON Backup Update/Insert
        existing = [idx for idx, item in enumerate(cls._local_fallback_logs) if item.get("id") == doc_id]
        if existing:
            cls._local_fallback_logs[existing[0]] = doc
        else:
            cls._local_fallback_logs.append(doc)

        cls._save_local_fallback()
        return doc["id"]

    @classmethod
    def get_email_logs(cls, user_id=None, recipient_filter=None, report_type_filter=None, status_filter=None):
        """
        Fetches email history logs with optional filtering.
        """
        cls._load_local_fallback()
        logs = []

        # 1. Try MongoDB
        col = cls._get_collection()
        if col is not None:
            try:
                query = {}
                if user_id:
                    query["user_id"] = user_id
                if status_filter and status_filter != "All":
                    query["status"] = status_filter
                if report_type_filter and report_type_filter != "All":
                    query["report_type"] = report_type_filter

                records = list(col.find(query).sort("sent_at", -1))
                for r in records:
                    if "_id" in r:
                        r["_id"] = str(r["_id"])
                    if isinstance(r.get("sent_at"), datetime.datetime):
                        r["sent_at"] = r["sent_at"].isoformat()
                    logs.append(r)
            except Exception as e:
                print(f"EmailRepository: MongoDB query failed: {e}")
                logs = []

        # 2. Fallback to Local Cache if MongoDB returns no logs or failed
        if not logs:
            logs = list(cls._local_fallback_logs)
            if user_id:
                logs = [l for l in logs if l.get("user_id") == user_id]
            if status_filter and status_filter != "All":
                logs = [l for l in logs if l.get("status") == status_filter]
            if report_type_filter and report_type_filter != "All":
                logs = [l for l in logs if l.get("report_type") == report_type_filter]

        # Apply Recipient Text Filter
        if recipient_filter and recipient_filter.strip():
            term = recipient_filter.strip().lower()
            logs = [
                l for l in logs 
                if term in l.get("recipient_email", "").lower() or term in l.get("subject", "").lower()
            ]

        # Sort descending by date
        logs = sorted(logs, key=lambda x: x.get("sent_at", ""), reverse=True)
        return logs

    @classmethod
    def delete_email_log(cls, log_id):
        """
        Deletes a draft or email log by ID.
        """
        cls._load_local_fallback()
        if not log_id:
            return False

        # 1. MongoDB delete
        col = cls._get_collection()
        if col is not None:
            try:
                col.delete_one({"id": log_id})
            except Exception as e:
                print(f"EmailRepository: MongoDB delete failed: {e}")

        # 2. Local JSON delete
        cls._local_fallback_logs = [item for item in cls._local_fallback_logs if item.get("id") != log_id]
        cls._save_local_fallback()
        return True

    @classmethod
    def _get_collection(cls):
        """Returns MongoDB email_history collection if available."""
        try:
            client = MongoDBService.get_client()
            if client:
                db = client["statementforge"]
                return db["email_history"]
        except Exception:
            pass
        return None
