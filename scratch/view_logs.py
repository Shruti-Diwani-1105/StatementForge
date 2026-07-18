import sys
sys.path.append('.')
from services.mongodb_service import MongoDBService

col = MongoDBService.get_collection()
if col is not None:
    records = list(col.find().sort("upload_date", -1))
    for r in records:
        print("--- LOG ENTRY ---")
        for k, v in r.items():
            if k not in ["transactions"]:
                print(f"{k}: {v}")
else:
    print("History collection is not available.")
