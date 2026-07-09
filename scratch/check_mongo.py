import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Adjust path to import services/mongodb_service
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

def main():
    uri = os.getenv("MONGODB_URI")
    print(f"Connecting to MongoDB with URI: {uri}")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        db = client["statementforge"]
        col = db["statements"]
        print("Statements collection counts:")
        total = col.count_documents({})
        print(f"Total records in DB: {total}")
        
        # Last 5 records
        records = list(col.find().sort("upload_date", -1).limit(5))
        for r in records:
            print(f"- Bank: {r.get('bank_name')}, Period: {r.get('statement_period')}, File: {r.get('pdf_path')}, Transactions: {r.get('total_transactions')}, Date: {r.get('upload_date')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
