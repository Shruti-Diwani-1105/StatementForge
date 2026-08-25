import os
import csv
import json
import uuid
import datetime
from services.transaction_formatter import TransactionFormatter

class ExportService:
    """
    Dedicated service for normalizing parsed statement payloads
    and exporting canonical transaction datasets to CSV and JSON formats.
    """

    @classmethod
    def generate_statement_id(cls, bank_name="Bank", file_name="Statement", period=None):
        """Generates a unique, traceable statement identifier."""
        clean_bank = "".join(c for c in bank_name if c.isalnum()).upper() or "BANK"
        time_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_suffix = uuid.uuid4().hex[:6].upper()
        return f"STMT_{clean_bank}_{time_stamp}_{rand_suffix}"

    @classmethod
    def normalize_payload(cls, payload, statement_id=None):
        """
        Normalizes a raw parsed statement payload into a canonical structure.
        Guarantees that transactions originate strictly from the parsed PDF.
        """
        if not payload or not isinstance(payload, dict):
            raise ValueError("Invalid payload object provided for normalization.")

        raw_txs = payload.get("transactions", [])
        if not isinstance(raw_txs, list):
            raw_txs = []

        stmt_id = statement_id or payload.get("statement_id") or cls.generate_statement_id(
            payload.get("bank_name", "Bank"),
            payload.get("file_name", "Statement"),
            payload.get("period")
        )

        formatted_txs = TransactionFormatter.format_transactions(raw_txs)
        normalized_txs = []

        for tx in formatted_txs:
            date_str = str(tx.get("date", "")).strip()
            narration_str = str(tx.get("narration", "")).strip()
            
            # Extract reference / cheque no if present
            ref_str = str(
                tx.get("reference") or tx.get("Reference") or tx.get("ref_no") or 
                tx.get("Cheque No.") or tx.get("Chq/Ref No") or ""
            ).strip()

            try:
                debit_val = float(tx.get("debit", 0.0) or 0.0)
            except (ValueError, TypeError):
                debit_val = 0.0

            try:
                credit_val = float(tx.get("credit", 0.0) or 0.0)
            except (ValueError, TypeError):
                credit_val = 0.0

            balance_raw = tx.get("balance")
            if balance_raw is not None and str(balance_raw).strip() != "":
                try:
                    balance_val = float(balance_raw)
                except (ValueError, TypeError):
                    balance_val = None
            else:
                balance_val = None

            # Determine transaction type
            if debit_val > 0 and credit_val == 0:
                tx_type = "DEBIT"
            elif credit_val > 0 and debit_val == 0:
                tx_type = "CREDIT"
            else:
                tx_type = "NEUTRAL"

            category_str = str(tx.get("category") or tx.get("Category") or "").strip()

            norm_tx = {
                "date": date_str,
                "narration": narration_str,
                "reference": ref_str,
                "debit": debit_val,
                "credit": credit_val,
                "balance": balance_val,
                "transaction_type": tx_type,
                "category": category_str,
                "source_statement_id": stmt_id
            }
            normalized_txs.append(norm_tx)

        # Compute summary metrics
        total_debit = round(sum(t["debit"] for t in normalized_txs), 2)
        total_credit = round(sum(t["credit"] for t in normalized_txs), 2)
        net_change = round(total_credit - total_debit, 2)

        return {
            "statement_id": stmt_id,
            "file_name": payload.get("file_name", "Statement.pdf"),
            "file_path": payload.get("file_path", ""),
            "bank_name": payload.get("bank_name", "Unknown Bank"),
            "account_holder": payload.get("account_holder", "Unknown"),
            "account_number": payload.get("account_number", "Unknown"),
            "period": payload.get("period", "Unknown Period"),
            "currency": payload.get("currency", "INR"),
            "transaction_count": len(normalized_txs),
            "total_debit": total_debit,
            "total_credit": total_credit,
            "net_change": net_change,
            "transactions": normalized_txs
        }

    @classmethod
    def export_csv(cls, payload, output_path, statement_id=None):
        """
        Exports normalized statement transactions to a CSV file.
        Uses UTF-8 with BOM (utf-8-sig) for universal Excel compatibility.
        """
        if not output_path:
            raise ValueError("No output path specified for CSV export.")

        norm = cls.normalize_payload(payload, statement_id)
        transactions = norm["transactions"]

        if not transactions and len(payload.get("transactions", [])) > 0:
            raise ValueError("Transaction extraction failed. No CSV export created because valid transaction data could not be verified.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        fieldnames = [
            "Date", "Narration", "Reference", "Debit", "Credit", "Balance", "Transaction Type", "Category"
        ]

        with open(output_path, mode="w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for tx in transactions:
                bal_str = f"{tx['balance']:.2f}" if tx['balance'] is not None else ""
                writer.writerow({
                    "Date": tx["date"],
                    "Narration": tx["narration"],
                    "Reference": tx["reference"],
                    "Debit": f"{tx['debit']:.2f}",
                    "Credit": f"{tx['credit']:.2f}",
                    "Balance": bal_str,
                    "Transaction Type": tx["transaction_type"],
                    "Category": tx["category"]
                })

        return {
            "output_path": output_path,
            "transaction_count": len(transactions),
            "total_debit": norm["total_debit"],
            "total_credit": norm["total_credit"],
            "statement_id": norm["statement_id"]
        }

    @classmethod
    def export_json(cls, payload, output_path, statement_id=None):
        """
        Exports normalized statement metadata and transaction array to a JSON file.
        Uses UTF-8 encoding with ensure_ascii=False for full Unicode support.
        """
        if not output_path:
            raise ValueError("No output path specified for JSON export.")

        norm = cls.normalize_payload(payload, statement_id)
        transactions = norm["transactions"]

        if not transactions and len(payload.get("transactions", [])) > 0:
            raise ValueError("Transaction extraction failed. No JSON export created because valid transaction data could not be verified.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Build clean JSON schema
        json_data = {
            "statement": {
                "statement_id": norm["statement_id"],
                "file_name": norm["file_name"],
                "bank_name": norm["bank_name"],
                "account_holder": norm["account_holder"],
                "account_number": norm["account_number"],
                "statement_period": norm["period"],
                "currency": norm["currency"],
                "transaction_count": norm["transaction_count"],
                "total_debit": norm["total_debit"],
                "total_credit": norm["total_credit"],
                "net_balance_change": norm["net_change"]
            },
            "transactions": transactions
        }

        with open(output_path, mode="w", encoding="utf-8") as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)

        return {
            "output_path": output_path,
            "transaction_count": len(transactions),
            "total_debit": norm["total_debit"],
            "total_credit": norm["total_credit"],
            "statement_id": norm["statement_id"]
        }
