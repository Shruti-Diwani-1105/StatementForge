import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.history_service import HistoryService
from database.email_repository import EmailRepository
from services.mongodb_service import MongoDBService

print("--- TESTING USER DATA ISOLATION ---")

# 1. Test None / Unauthenticated User
none_stats = HistoryService.get_stats(user_id=None)
none_activity = HistoryService.get_recent_activity(user_id=None)
none_history = HistoryService.get_history_logs(user_id=None)
none_emails = EmailRepository.get_email_logs(user_id=None)
none_statements = MongoDBService.get_user_statements(user_id=None)

assert none_stats["processed"] == 0, f"Vulnerability: Unauthenticated user saw processed stats {none_stats}"
assert len(none_activity) == 0, f"Vulnerability: Unauthenticated user saw activity logs: {none_activity}"
assert len(none_history) == 0, f"Vulnerability: Unauthenticated user saw history logs: {none_history}"
assert len(none_emails) == 0, f"Vulnerability: Unauthenticated user saw email logs: {none_emails}"
assert len(none_statements) == 0, f"Vulnerability: Unauthenticated user saw statements: {none_statements}"

print("PASSED: Unauthenticated / null user_id returned 0 records across all services.")

# 2. Test User A Isolation
user_a_id = "user_A_id_123"
HistoryService.save_record(
    user_id=user_a_id,
    pdf_path="C:/statements/user_a_statement.pdf",
    excel_path="C:/statements/user_a_statement.xlsx",
    bank_name="User A HDFC Bank",
    statement_period="Jan 2026",
    processing_time=1.2,
    total_transactions=15
)

EmailRepository.save_email_log(
    user_id=user_a_id,
    recipient_email="user_a_client@domain.com",
    cc="", bcc="",
    subject="User A Audit Report",
    report_type="GST Audit",
    attachment_name="UserA_GST.xlsx",
    attachment_paths=["C:/reports/UserA_GST.xlsx"],
    status="Sent"
)

# 3. Test User B Isolation
user_b_id = "user_B_id_456"
HistoryService.save_record(
    user_id=user_b_id,
    pdf_path="C:/statements/user_b_statement.pdf",
    excel_path="C:/statements/user_b_statement.xlsx",
    bank_name="User B ICICI Bank",
    statement_period="Feb 2026",
    processing_time=0.9,
    total_transactions=42
)

EmailRepository.save_email_log(
    user_id=user_b_id,
    recipient_email="user_b_client@domain.com",
    cc="", bcc="",
    subject="User B Financial Audit",
    report_type="Financial Audit",
    attachment_name="UserB_Audit.xlsx",
    attachment_paths=["C:/reports/UserB_Audit.xlsx"],
    status="Sent"
)

# 4. Verify User A Access Scope
user_a_logs = HistoryService.get_history_logs(user_id=user_a_id)
user_a_emails = EmailRepository.get_email_logs(user_id=user_a_id)

for log in user_a_logs:
    assert str(log.get("user_id")) == user_a_id, f"Vulnerability: User A accessed User B record {log}"
for email in user_a_emails:
    assert str(email.get("user_id")) == user_a_id, f"Vulnerability: User A accessed User B email {email}"

print(f"PASSED: User A accessed exactly {len(user_a_logs)} statement logs and {len(user_a_emails)} email logs (100% User A data).")

# 5. Verify User B Access Scope
user_b_logs = HistoryService.get_history_logs(user_id=user_b_id)
user_b_emails = EmailRepository.get_email_logs(user_id=user_b_id)

for log in user_b_logs:
    assert str(log.get("user_id")) == user_b_id, f"Vulnerability: User B accessed User A record {log}"
for email in user_b_emails:
    assert str(email.get("user_id")) == user_b_id, f"Vulnerability: User B accessed User A email {email}"

print(f"PASSED: User B accessed exactly {len(user_b_logs)} statement logs and {len(user_b_emails)} email logs (100% User B data).")

print("--- ALL USER ISOLATION VERIFICATION CHECKS PASSED PERFECTLY ---")
