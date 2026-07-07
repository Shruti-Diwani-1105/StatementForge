import sys
import os

# Ensure UTF-8 output on Windows terminal
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.gemini_service import GeminiService

try:
    print("Testing Gemini Connection with configured key...")
    text = "HDFC Bank Statement.\n01/04/2026 UPI Rent Payment Debit: 12000.00 Credit: 0.00 Balance: 45000.00"
    res = GeminiService.parse_statement_text(text)
    print("\n--- Gemini Response ---")
    print(res)
    print("\nConnection Successful!")
except Exception as e:
    print(f"\nConnection Error: {e}")
