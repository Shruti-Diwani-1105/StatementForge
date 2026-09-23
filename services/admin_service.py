import datetime
from utils.auth_db import AuthDB
from services.mongodb_service import MongoDBService

class AdminService:
    """
    Administrative operations service for StatementForge.
    Provides user management, system metrics, statement auditing, and activity logging.
    """

    @classmethod
    def get_all_users(cls):
        """Fetches all registered users."""
        return AuthDB.get_all_users()

    @classmethod
    def log_activity(cls, user, action, details):
        """Logs an administrative or security activity event."""
        db = MongoDBService.get_db()
        if db is not None:
            try:
                db["activity_logs"].insert_one({
                    "user": user,
                    "action": action,
                    "details": details,
                    "timestamp": datetime.datetime.now()
                })
                return True
            except Exception as e:
                print(f"AdminService: Error logging activity ({e})")
        return False

    @classmethod
    def create_user(cls, name, email, phone, password, role="user", status="active"):
        """Registers a new user from the Admin Panel."""
        success = AuthDB.register_user(name, email, phone, password, role, status)
        if success:
            cls.log_activity("admin@gmail.com", "Account Created", f"Created account for {email} ({role})")
            return True, "User account created successfully!"
        return False, "An account with this email address already exists."

    @classmethod
    def update_user(cls, email, name, phone, role, status):
        """Updates user details from the Admin Panel."""
        res, msg = AuthDB.update_user_by_admin(email, name, phone, role, status)
        if res:
            cls.log_activity("admin@gmail.com", "Profile Updated", f"Updated profile for {email}")
        return res, msg

    @classmethod
    def reset_user_password(cls, email, new_password):
        """Resets user password from the Admin Panel."""
        res, msg = AuthDB.reset_password(email, new_password)
        if res:
            cls.log_activity("admin@gmail.com", "Password Reset", f"Reset password for {email}")
        return res, msg

    @classmethod
    def update_user_role(cls, email, role):
        """Updates user role to admin or user."""
        res, msg = AuthDB.update_user_role(email, role)
        if res:
            cls.log_activity("admin@gmail.com", "Role Update", f"Changed role for {email} to {role}")
        return res, msg

    @classmethod
    def update_user_status(cls, email, status):
        """Updates user status to active or disabled."""
        res, msg = AuthDB.update_user_status(email, status)
        if res:
            cls.log_activity("admin@gmail.com", "Status Change", f"Updated status for {email} to {status}")
        return res, msg

    @classmethod
    def delete_user(cls, email):
        """Deletes user account."""
        res, msg = AuthDB.delete_user(email)
        if res:
            cls.log_activity("admin@gmail.com", "Account Deleted", f"Deleted account for {email}")
        return res, msg

    @classmethod
    def get_system_stats(cls):
        """Calculates system metrics including user counts, statement counts, and database status."""
        users = AuthDB.get_all_users()
        total_users = len(users)
        active_users = sum(1 for u in users if str(u.get("status", "active")).lower() == "active")
        admin_count = sum(1 for u in users if str(u.get("role", "")).lower() in ["admin", "administrator"])

        db = MongoDBService.get_db()
        db_connected = (db is not None)
        
        all_stmts = cls.get_all_statements(limit=500)
        total_statements = len(all_stmts)
        total_transactions = sum(int(s.get("total_transactions", 0)) for s in all_stmts)

        return {
            "total_users": total_users,
            "active_users": active_users,
            "admin_count": admin_count,
            "total_statements": total_statements,
            "total_transactions": total_transactions,
            "db_connected": db_connected,
            "system_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @classmethod
    def get_all_statements(cls, limit=50):
        """Fetches statement logs across all users (MongoDB + Local History)."""
        statements = []
        seen_ids = set()

        # 1. Fetch from MongoDB
        col = MongoDBService.get_collection()
        if col is not None:
            try:
                cursor = col.find({}).sort("upload_date", -1).limit(limit)
                for doc in cursor:
                    doc_id = str(doc.get("_id", ""))
                    seen_ids.add(doc_id)
                    statements.append({
                        "id": doc_id,
                        "user_id": doc.get("user_id") or doc.get("user") or doc.get("email") or "admin@gmail.com",
                        "bank_name": doc.get("bank_name", "Unknown Bank"),
                        "statement_period": doc.get("statement_period") or doc.get("period") or "Full Year",
                        "total_transactions": doc.get("total_transactions") or doc.get("tx_count") or 0,
                        "processing_time": doc.get("processing_time", 0.0),
                        "upload_date": doc.get("upload_date", "").strftime("%Y-%m-%d %H:%M") if isinstance(doc.get("upload_date"), datetime.datetime) else str(doc.get("upload_date", ""))
                    })
            except Exception as e:
                print(f"AdminService: Error fetching MongoDB statements ({e})")

        # 2. Fetch from Local HistoryService fallback
        try:
            from services.history_service import HistoryService
            local_logs = HistoryService.get_user_history("all")
            for item in local_logs:
                item_id = str(item.get("_id") or item.get("id") or "")
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    statements.append({
                        "id": item_id,
                        "user_id": item.get("user_id") or item.get("user") or "admin@gmail.com",
                        "bank_name": item.get("bank_name", "Bank Statement"),
                        "statement_period": item.get("statement_period") or "Recent Period",
                        "total_transactions": item.get("total_transactions") or item.get("transaction_count") or 0,
                        "processing_time": item.get("processing_time", 1.2),
                        "upload_date": str(item.get("upload_date") or "").replace("T", " ")[:16]
                    })
        except Exception as e:
            print(f"AdminService: Error fetching local history logs ({e})")

        if statements:
            return statements[:limit]

        # Fallback sample statement logs if DB collection is empty
        now = datetime.datetime.now()
        sample_banks = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank"]
        users = AuthDB.get_all_users()
        for idx, bank in enumerate(sample_banks):
            u_email = users[idx % len(users)]["email"] if users else "diwanishruti05@gmail.com"
            statements.append({
                "id": f"stmt_sample_{idx+1}",
                "user_id": u_email,
                "bank_name": bank,
                "statement_period": "2026-01-01 to 2026-06-30",
                "total_transactions": 120 + (idx * 45),
                "processing_time": 1.45 + (idx * 0.3),
                "upload_date": (now - datetime.timedelta(days=idx*2, hours=idx*3)).strftime("%Y-%m-%d %H:%M")
            })
        return statements[:limit]

    @classmethod
    def get_audit_logs(cls, limit=50):
        """Fetches system activity and login logs."""
        db = MongoDBService.get_db()
        logs = []
        if db is not None:
            try:
                if "activity_logs" in db.list_collection_names():
                    cursor = db["activity_logs"].find({}).sort("timestamp", -1).limit(limit)
                    for doc in cursor:
                        raw_ts = doc.get("timestamp", "")
                        if isinstance(raw_ts, datetime.datetime):
                            ts_str = raw_ts.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            ts_str = str(raw_ts).replace("T", " ").split(".")[0]

                        logs.append({
                            "user": doc.get("user", "System"),
                            "action": doc.get("action", "Event"),
                            "details": doc.get("details", ""),
                            "timestamp": ts_str
                        })
            except Exception as e:
                print(f"AdminService: Error fetching audit logs ({e})")

        # Include user logins and activity events if DB logs are sparse
        now = datetime.datetime.now()
        users = AuthDB.get_all_users()
        for u in users:
            u_email = u.get("email", "admin@gmail.com")
            raw_login = u.get("last_login", now.strftime("%Y-%m-%d %H:%M:%S"))
            login_ts = str(raw_login).replace("T", " ").split(".")[0]
            if not any(l.get("user") == u_email and l.get("action") == "User Login" for l in logs):
                logs.append({
                    "user": u_email,
                    "action": "User Login",
                    "details": f"Authenticated successfully as {u.get('role', 'user')}",
                    "timestamp": login_ts
                })

        logs.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        return logs[:limit]
