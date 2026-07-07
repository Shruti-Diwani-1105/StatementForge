import datetime
from services.mongodb_service import MongoDBService

class HistoryService:
    """Manages statement parsing runs history and aggregates dashboard metrics."""

    _local_fallback_logs = []

    @classmethod
    def save_record(cls, user_id, pdf_path, excel_path, bank_name, statement_period, processing_time, total_transactions):
        """
        Saves a run log record. Attempts MongoDB save, falling back to local list on failure.
        """
        # MongoDB Save
        inserted_id = MongoDBService.save_statement(
            user_id=user_id,
            pdf_path=pdf_path,
            excel_path=excel_path,
            bank_name=bank_name,
            statement_period=statement_period,
            processing_time=processing_time,
            total_transactions=total_transactions
        )

        # Always save to local fallback list for local tracking and fallback consistency
        now = datetime.datetime.utcnow()
        local_doc = {
            "user_id": user_id,
            "pdf_path": pdf_path,
            "excel_path": excel_path,
            "bank_name": bank_name,
            "statement_period": statement_period,
            "processing_time": float(processing_time),
            "upload_date": now,
            "total_transactions": int(total_transactions)
        }
        cls._local_fallback_logs.append(local_doc)

        return inserted_id is not None

    @classmethod
    def get_stats(cls, user_id=None):
        """
        Returns dashboard metrics:
        - processed: count of runs
        - verified: sum of total transaction rows parsed
        - exported: count of completed Excel sheets (equal to runs)
        """
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                query = {"user_id": user_id} if user_id else {}
                
                # Total runs count
                processed = col.count_documents(query)
                
                # Sum of transactions
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
        filtered = cls._local_fallback_logs
        if user_id:
            filtered = [log for log in cls._local_fallback_logs if log["user_id"] == user_id]

        processed = len(filtered)
        verified = sum(log["total_transactions"] for log in filtered)

        return {
            "processed": processed,
            "verified": verified,
            "exported": processed
        }

    @classmethod
    def get_recent_activity(cls, user_id=None, limit=5):
        """
        Fetches the recent statement upload activity list for the dashboard.
        """
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                records = MongoDBService.get_user_statements(user_id, limit=limit)
                # Map fields to uniform format
                mapped = []
                for doc in records:
                    mapped.append({
                        "file_name": doc.get("pdf_path", "").split("/")[-1].split("\\")[-1] or "Statement.pdf",
                        "bank_name": doc.get("bank_name", "Unknown Bank"),
                        "upload_date": doc.get("upload_date"),
                        "status": "Completed"
                    })
                return mapped
            except Exception as e:
                print(f"HistoryService: MongoDB recent activity fetch failed: {e}")

        # Local fallback recent activity
        filtered = cls._local_fallback_logs
        if user_id:
            filtered = [log for log in cls._local_fallback_logs if log["user_id"] == user_id]

        # Sort by upload date descending
        filtered = sorted(filtered, key=lambda x: x["upload_date"], reverse=True)[:limit]

        mapped = []
        for log in filtered:
            mapped.append({
                "file_name": log["pdf_path"].split("/")[-1].split("\\")[-1] or "Statement.pdf",
                "bank_name": log["bank_name"],
                "upload_date": log["upload_date"],
                "status": "Completed"
            })
        return mapped
