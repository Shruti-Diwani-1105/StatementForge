import datetime
import json
import os
import uuid
from bson.objectid import ObjectId
from services.mongodb_service import MongoDBService

HISTORY_FALLBACK_FILE = os.path.expanduser("~/.statementforge_history.json")

class HistoryService:
    """Manages statement parsing runs history and aggregates dashboard metrics."""

    _local_fallback_logs = []
    _loaded = False

    @classmethod
    def _load_local_fallback(cls):
        if cls._loaded:
            return
        cls._loaded = True
        if os.path.exists(HISTORY_FALLBACK_FILE):
            try:
                with open(HISTORY_FALLBACK_FILE, "r") as f:
                    cls._local_fallback_logs = json.load(f)
            except Exception as e:
                print(f"HistoryService: Error loading fallback history: {e}")

    @classmethod
    def _save_local_fallback(cls):
        try:
            with open(HISTORY_FALLBACK_FILE, "w") as f:
                json.dump(cls._local_fallback_logs, f, indent=4)
        except Exception as e:
            print(f"HistoryService: Error saving fallback history: {e}")

    @classmethod
    def create_record(cls, user_id, pdf_path, bank_name, status="Processing", output_format="Excel"):
        """Creates a new history entry at the start of processing."""
        cls._load_local_fallback()
        now = datetime.datetime.utcnow()
        
        doc = {
            "user_id": user_id,
            "pdf_path": pdf_path,
            "excel_path": "",
            "bank_name": bank_name,
            "statement_period": "",
            "processing_time": 0.0,
            "upload_date": now.isoformat(),
            "total_transactions": 0,
            "status": status,
            "output_format": output_format
        }

        # 1. MongoDB Save
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                # Insert document directly with datetime object in MongoDB
                mongo_doc = doc.copy()
                mongo_doc["upload_date"] = now
                res = col.insert_one(mongo_doc)
                return str(res.inserted_id)
            except Exception as e:
                print(f"HistoryService: Failed to save initial MongoDB record: {e}")

        # 2. Local Fallback
        record_id = str(uuid.uuid4())
        doc["_id"] = record_id
        cls._local_fallback_logs.append(doc)
        cls._save_local_fallback()
        return record_id

    @classmethod
    def update_record_status(cls, record_id, status):
        """Updates the status of a history log (e.g. Failed or Cancelled)."""
        cls._load_local_fallback()
        
        # 1. MongoDB Update
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                col.update_one({"_id": ObjectId(record_id)}, {"$set": {"status": status}})
                return True
            except Exception:
                # If ObjectId fails, it might be a local fallback record_id string
                try:
                    col.update_one({"_id": record_id}, {"$set": {"status": status}})
                    return True
                except Exception as e:
                    print(f"HistoryService: Failed to update MongoDB record status: {e}")

        # 2. Local Fallback Update
        for log in cls._local_fallback_logs:
            if log.get("_id") == record_id:
                log["status"] = status
                cls._save_local_fallback()
                return True
        return False

    @classmethod
    def update_record_completed(cls, record_id, excel_path, period, processing_time, total_transactions):
        """Updates status to Completed and fills parsing statistics."""
        cls._load_local_fallback()
        
        updates = {
            "status": "Completed",
            "excel_path": excel_path,
            "statement_period": period,
            "processing_time": float(processing_time),
            "total_transactions": int(total_transactions)
        }

        # 1. MongoDB Update
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                col.update_one({"_id": ObjectId(record_id)}, {"$set": updates})
                return True
            except Exception:
                try:
                    col.update_one({"_id": record_id}, {"$set": updates})
                    return True
                except Exception as e:
                    print(f"HistoryService: Failed to update MongoDB record completion: {e}")

        # 2. Local Fallback Update
        for log in cls._local_fallback_logs:
            if log.get("_id") == record_id:
                log.update(updates)
                cls._save_local_fallback()
                return True
        return False

    @classmethod
    def get_stats(cls, user_id=None):
        """Returns aggregates only for Completed parse entries."""
        cls._load_local_fallback()
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                query = {"status": "Completed"}
                if user_id:
                    query["user_id"] = user_id
                
                processed = col.count_documents(query)
                
                pipeline = [
                    {"$match": query},
                    {"$group": {"_id": None, "total": {"$sum": "$total_transactions"}}}
                ]
                agg = list(col.aggregate(pipeline))
                verified = agg[0]["total"] if agg else 0
                
                return {
                    "processed": processed,
                    "verified": verified,
                    "exported": processed
                }
            except Exception as e:
                print(f"HistoryService: MongoDB stats fetch failed: {e}. Using local fallback stats.")

        # Local fallback metrics
        filtered = [log for log in cls._local_fallback_logs if log.get("status") == "Completed"]
        if user_id:
            filtered = [log for log in filtered if log.get("user_id") == user_id]

        processed = len(filtered)
        verified = sum(log.get("total_transactions", 0) for log in filtered)

        return {
            "processed": processed,
            "verified": verified,
            "exported": processed
        }

    @classmethod
    def get_recent_activity(cls, user_id=None, limit=5):
        """Fetches recent statement activity list for the dashboard."""
        cls._load_local_fallback()
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                query = {"user_id": user_id} if user_id else {}
                records = list(col.find(query).sort("upload_date", -1).limit(limit))
                mapped = []
                for doc in records:
                    mapped.append({
                        "file_name": os.path.basename(doc.get("pdf_path", "")) or "Statement.pdf",
                        "bank_name": doc.get("bank_name", "Unknown Bank"),
                        "upload_date": doc.get("upload_date"),
                        "status": doc.get("status", "Completed")
                    })
                return mapped
            except Exception as e:
                print(f"HistoryService: MongoDB recent activity fetch failed: {e}")

        # Local fallback recent activity
        filtered = cls._local_fallback_logs
        if user_id:
            filtered = [log for log in cls._local_fallback_logs if log.get("user_id") == user_id]

        # Sort by upload date descending
        filtered = sorted(filtered, key=lambda x: x.get("upload_date", ""), reverse=True)[:limit]

        mapped = []
        for log in filtered:
            mapped.append({
                "file_name": os.path.basename(log.get("pdf_path", "")) or "Statement.pdf",
                "bank_name": log.get("bank_name", "Unknown Bank"),
                "upload_date": log.get("upload_date"),
                "status": log.get("status", "Completed")
            })
        return mapped

    @classmethod
    def get_history_logs(cls, user_id=None):
        """Fetches all history logs."""
        cls._load_local_fallback()
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                query = {"user_id": user_id} if user_id else {}
                records = list(col.find(query).sort("upload_date", -1))
                return records
            except Exception as e:
                print(f"HistoryService: MongoDB history fetch failed: {e}")

        # Local fallback history logs
        filtered = cls._local_fallback_logs
        if user_id:
            filtered = [log for log in cls._local_fallback_logs if log.get("user_id") == user_id]
        return sorted(filtered, key=lambda x: x.get("upload_date", ""), reverse=True)

    @classmethod
    def save_record(cls, user_id, pdf_path, excel_path, bank_name, statement_period, processing_time, total_transactions):
        """Kept for backward compatibility, automatically creates a Completed record."""
        record_id = cls.create_record(user_id, pdf_path, bank_name, status="Completed")
        cls.update_record_completed(record_id, excel_path, statement_period, processing_time, total_transactions)
        return True
