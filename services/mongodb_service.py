import os
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class MongoDBService:
    """Manages connections and storage of statement logs in MongoDB Atlas."""
    
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
        print("MongoDBService: Connection references reset.")

    @classmethod
    def get_client(cls):
        """Initializes and returns raw MongoClient instance, or None if unavailable."""
        cls.get_collection()
        return cls._mongo_client if cls._mongo_available else None

    @classmethod
    def get_db(cls):
        """Initializes and returns raw Db instance, or None if unavailable."""
        cls.get_collection()
        return cls._db if cls._mongo_available else None


    @classmethod
    def get_collection(cls):
        """Initializes and returns MongoDB statements collection, or None if unavailable."""
        if cls._mongo_client is not None:
            return cls._collection if cls._mongo_available else None

        uri = os.getenv("MONGODB_URI")
        if not uri or not uri.strip():
            print("MongoDBService: MONGODB_URI not found. MongoDB operations disabled.")
            cls._mongo_client = "none"
            cls._mongo_available = False
            return None

        try:
            # Set a 2-second timeout to avoid locking the UI thread in case of connection failure
            cls._mongo_client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            cls._mongo_client.admin.command('ping') # Verify connection
            db_name = os.getenv("MONGODB_DB_NAME", "statementforge")
            cls._db = cls._mongo_client[db_name]
            cls._collection = cls._db["statements"]
            cls._mongo_available = True
            print(f"MongoDBService: Connected to MongoDB Atlas successfully! (Database: {db_name})")
            return cls._collection
        except Exception as e:
            print(f"MongoDBService: Failed to connect to MongoDB Atlas ({e}). MongoDB fallback disabled.")
            cls._mongo_client = "failed"
            cls._mongo_available = False
            cls._collection = None
            return None

    @classmethod
    def save_statement(cls, user_id, pdf_path, excel_path, bank_name, statement_period, processing_time, total_transactions):
        """
        Saves a statement metadata record in MongoDB.
        Returns the inserted ID or None if failed.
        """
        now = datetime.datetime.utcnow()
        document = {
            "user_id": user_id,
            "pdf_path": pdf_path,
            "excel_path": excel_path,
            "bank_name": bank_name,
            "statement_period": statement_period,
            "processing_time": float(processing_time),
            "upload_date": now,
            "total_transactions": int(total_transactions)
        }

        col = cls.get_collection()
        if col is not None:
            try:
                res = col.insert_one(document)
                return str(res.inserted_id)
            except Exception as e:
                print(f"MongoDBService: Failed to insert statement document: {e}")
        return None

    @classmethod
    def get_user_statements(cls, user_id, limit=20):
        """Fetches statement logs strictly for a specific user_id, sorted by most recent."""
        if not user_id:
            return []
        user_id_str = str(user_id)
        col = cls.get_collection()
        if col is not None:
            try:
                query = {"user_id": user_id_str}
                cursor = col.find(query).sort("upload_date", -1).limit(limit)
                return list(cursor)
            except Exception as e:
                print(f"MongoDBService: Failed to fetch statements: {e}")
        return []
