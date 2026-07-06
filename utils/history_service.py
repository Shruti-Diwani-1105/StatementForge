import datetime
from utils.auth_db import AuthDB

class HistoryService:
    """Handles logging of statement parsing metadata and computing dashboard metrics."""
    
    # Local fallback storage list
    _statements = []

    @classmethod
    def get_mongo_collection(cls):
        """Initializes and returns MongoDB statements collection, or None if unavailable."""
        client = AuthDB.get_mongo_collection()
        if client is not None:
            db = AuthDB._db
            if db is not None:
                return db["statements"]
        return None

    @classmethod
    def save_record(cls, user_id, file_name, pdf_path, excel_path, bank_name, period, total_transactions, processing_time, ocr_used):
        """Saves a statement parsing record to MongoDB Atlas or local fallback."""
        now = datetime.datetime.utcnow()
        ocr_status_str = "Yes" if ocr_used else "No"
        
        doc = {
            "user_id": user_id,
            "file_name": file_name,
            "pdf_path": pdf_path,
            "excel_path": excel_path,
            "upload_date": now,
            "bank_name": bank_name,
            "period": period,
            "total_transactions": total_transactions,
            "processing_time": float(processing_time),
            "ocr_used": ocr_status_str,
            "status": "completed"
        }

        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                collection.insert_one(doc)
                return True
            except Exception as e:
                print(f"HistoryService: MongoDB save_record error ({e}). Falling back to memory.")

        # Local fallback
        cls._statements.append(doc)
        return True

    @classmethod
    def get_stats(cls, user_id=None):
        """
        Computes dashboard stats:
        - Statements Processed (count of runs)
        - Transactions Verified (sum of transactions parsed)
        - Reports Exported (count of Excel generated)
        """
        collection = cls.get_mongo_collection()
        if collection is not None:
            try:
                # Query filter by user_id if provided
                query = {"user_id": user_id} if user_id else {}
                
                # Count total processed
                processed_count = collection.count_documents(query)
                
                # Sum transactions
                pipeline = [
                    {"$match": query},
                    {"$group": {"_id": None, "total": {"$sum": "$total_transactions"}}}
                ]
                agg_result = list(collection.aggregate(pipeline))
                verified_count = agg_result[0]["total"] if agg_result else 0
                
                # Reports exported is same as completed files count
                exported_count = processed_count
                
                return {
                    "processed": processed_count,
                    "verified": verified_count,
                    "exported": exported_count
                }
            except Exception as e:
                print(f"HistoryService: MongoDB get_stats error ({e}). Falling back to memory.")

        # Memory Fallback filtering
        user_docs = cls._statements
        if user_id:
            user_docs = [s for s in cls._statements if s["user_id"] == user_id]

        processed = len(user_docs)
        verified = sum(s["total_transactions"] for s in user_docs)
        exported = processed

        return {
            "processed": processed,
            "verified": verified,
            "exported": exported
        }
