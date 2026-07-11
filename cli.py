#!/usr/bin/env python3
import sys
import os
import argparse
import time

# Ensure project root is in the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser.parser import PDFStatementParser
from services.excel_generator import ExcelGenerator
from services.history_service import HistoryService

def progress_cb(current, total, tx_count=0):
    print(f"[*] Processing page {current}/{total}... (Found {tx_count} transactions so far)", end="\r", flush=True)

def main():
    parser = argparse.ArgumentParser(description="StatementForge Headless Auto-Detection and Excel Converter")
    parser.add_argument("pdf_path", help="Path to the bank statement PDF file")
    parser.add_argument("-o", "--output", help="Custom output path for the generated Excel file")
    
    args = parser.parse_args()
    
    pdf_path = os.path.abspath(args.pdf_path)
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)
        
    print(f"[*] Starting automatic analysis of: {os.path.basename(pdf_path)}")
    print("[*] Detecting bank and format...")
    
    try:
        start_time = time.time()
        
        # 1. Parse statement
        payload = PDFStatementParser.parse(pdf_path, progress_callback=progress_cb)
        print("\n[*] Parsing completed successfully.")
        
        # 2. Get details
        bank_name = payload.get("bank_name", "Unknown Bank")
        account_holder = payload.get("account_holder", "Unknown")
        account_number = payload.get("account_number", "Unknown")
        period = payload.get("period", "Unknown Period")
        transactions = payload.get("transactions", [])
        
        print("-" * 50)
        print(f"Bank Detected      : {bank_name}")
        print(f"Account Holder     : {account_holder}")
        print(f"Account Number     : {account_number}")
        print(f"Statement Period   : {period}")
        print(f"Total Transactions : {len(transactions)}")
        print("-" * 50)
        
        if not transactions:
            print("Warning: No transactions were extracted. Excel file will not be generated.")
            sys.exit(0)
            
        print("[*] Generating formatted Excel report...")
        excel_path = ExcelGenerator.generate_excel(
            pdf_path=pdf_path,
            bank_name=bank_name,
            account_holder=account_holder,
            period=period,
            transactions=transactions
        )
        
        # Save custom output path if requested
        if args.output:
            dest_path = os.path.abspath(args.output)
            # Ensure folder exists
            dest_dir = os.path.dirname(dest_path)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
            import shutil
            shutil.move(excel_path, dest_path)
            excel_path = dest_path
            
        elapsed = time.time() - start_time
        print(f"[+] Conversion complete! Excel saved to: {excel_path}")
        print(f"[+] Total execution time: {elapsed:.2f} seconds")
        
        # Optional: save run locally in the history fallback log
        HistoryService.save_record(
            user_id="cli_user",
            pdf_path=pdf_path,
            excel_path=excel_path,
            bank_name=bank_name,
            statement_period=period,
            processing_time=elapsed,
            total_transactions=len(transactions)
        )
        
    except Exception as e:
        print(f"\nError: Conversion failed. {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
