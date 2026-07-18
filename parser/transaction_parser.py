import re
from parser.utils import ParserUtils

class TransactionParser:
    """Parses raw table rows into structured transactions, mapping columns and merging multi-line narrations."""

    META_KEYWORDS = [
        "page", "opening balance", "closing balance", "carried forward", "brought forward",
        "b/f", "c/f", "total", "subtotal", "summary", "statement period", "account summary",
        "date  narration", "date narration", "date description", "date  description"
    ]

    @classmethod
    def detect_columns(cls, rows: list, bank_layout: dict = None) -> dict:
        """Detects which column indexes map to Date, Value Date, Narration, Ref, Debit, Credit, Balance."""
        mapping = {}
        if not rows:
            return mapping

        header_row_idx = -1
        header_row = None
        
        # Try finding header row in first 5 rows
        for idx in range(min(5, len(rows))):
            row = [str(c).lower().strip() for c in rows[idx]]
            hit_count = 0
            for cell in row:
                if any(term in cell for term in ["date", "narration", "description", "debit", "credit", "balance", "withdrawal", "deposit", "amount"]):
                    hit_count += 1
            if hit_count >= 2:
                header_row_idx = idx
                header_row = row
                break

        if header_row is not None:
            for col_idx, cell in enumerate(header_row):
                cell_clean = cell.replace("_", " ").replace("\n", " ").strip()
                cell_no_space = cell_clean.replace(" ", "")
                if "value date" in cell_clean or "val date" in cell_clean or "valuedate" in cell_no_space or "valdate" in cell_no_space:
                    mapping["value_date"] = col_idx
                elif "date" in cell_clean and "date" not in mapping:
                    mapping["date"] = col_idx
                elif any(x in cell_clean for x in ["narration", "description", "particulars", "remarks"]) or any(x in cell_no_space for x in ["narration", "description", "particulars", "remarks"]):
                    mapping["narration"] = col_idx
                elif any(x in cell_clean for x in ["chq no", "cheque", "ref no", "reference", "utr", "instrument"]) or any(x in cell_no_space for x in ["chqno", "cheque", "refno", "reference", "utr", "instrument"]):
                    mapping["ref_no"] = col_idx
                elif any(x in cell_clean for x in ["debit", "withdrawal", "amount dr", "withdraw"]) or any(x in cell_no_space for x in ["debit", "withdrawal", "amountdr", "withdraw"]):
                    mapping["debit"] = col_idx
                elif any(x in cell_clean for x in ["credit", "deposit", "amount cr", "depo"]) or any(x in cell_no_space for x in ["credit", "deposit", "amountcr", "depo"]):
                    mapping["credit"] = col_idx
                elif "balance" in cell_clean or cell_clean == "bal" or "balance" in cell_no_space or cell_no_space == "bal":
                    mapping["balance"] = col_idx
                elif any(x in cell_clean for x in ["dr/cr", "dr / cr", "type"]) or any(x in cell_no_space for x in ["dr/cr", "drcr", "type"]):
                    mapping["type"] = col_idx

            # Single amount column fallback check if no separate debit/credit columns were matched
            if "debit" not in mapping and "credit" not in mapping:
                for col_idx, cell in enumerate(header_row):
                    cell_clean = cell.replace("_", " ").replace("\n", " ").strip()
                    if any(x in cell_clean for x in ["amount dr / cr", "amount dr/cr", "amount (dr/cr)", "dr/cr", "dr / cr", "transaction amount", "amount"]):
                        mapping["debit"] = col_idx
                        mapping["credit"] = col_idx
                        break

        # Heuristics Fallback if missing Date or Narration
        required_keys = ["date", "narration"]
        is_incomplete = any(k not in mapping for k in required_keys)
        
        if is_incomplete:
            num_cols = len(rows[0])
            col_types = {i: {"dates": 0, "numeric": 0, "text_len": 0} for i in range(num_cols)}
            sample_rows = rows[header_row_idx + 1 : header_row_idx + 21] if header_row_idx != -1 else rows[:20]
            
            for row in sample_rows:
                for col_idx, cell in enumerate(row[:num_cols]):
                    cell_str = str(cell).strip()
                    if ParserUtils.is_valid_date(cell_str):
                        col_types[col_idx]["dates"] += 1
                    
                    clean_num = re.sub(r"[^\d\.\-]", "", cell_str)
                    if clean_num and clean_num != "-":
                        try:
                            float(clean_num)
                            if len(cell_str) <= len(clean_num) + 4:
                                col_types[col_idx]["numeric"] += 1
                        except ValueError:
                            pass
                    col_types[col_idx]["text_len"] += len(cell_str)

            # Map Date (only if not found)
            if "date" not in mapping:
                date_col = max(col_types.keys(), key=lambda i: col_types[i]["dates"])
                if col_types[date_col]["dates"] > 1:
                    mapping["date"] = date_col

            # Map Balance and Debit/Credit (only if not found)
            taken_indices = [mapping[k] for k in ["date", "value_date"] if k in mapping]
            numeric_cols = [i for i, scores in col_types.items() if scores["numeric"] > 1 and i not in taken_indices and scores["dates"] == 0]
            
            if "balance" not in mapping and numeric_cols:
                mapping["balance"] = numeric_cols[-1]
                numeric_cols = numeric_cols[:-1]
                
            if ("debit" not in mapping or "credit" not in mapping) and numeric_cols:
                other_numerics = [i for i in numeric_cols if i != mapping.get("balance")]
                if "debit" not in mapping and "credit" not in mapping:
                    if len(other_numerics) >= 2:
                        mapping["debit"] = other_numerics[0]
                        mapping["credit"] = other_numerics[1]
                    elif len(other_numerics) == 1:
                        mapping["debit"] = other_numerics[0]
                        mapping["credit"] = other_numerics[0]
                elif "debit" not in mapping:
                    mapping["debit"] = other_numerics[-1]
                elif "credit" not in mapping:
                    mapping["credit"] = other_numerics[-1]

            # Map Narration (only if not found)
            if "narration" not in mapping:
                taken = [mapping.get(k) for k in ["date", "value_date", "balance", "debit", "credit"] if mapping.get(k) is not None]
                remaining_cols = [i for i in col_types.keys() if i not in taken]
                if remaining_cols:
                    narration_col = max(remaining_cols, key=lambda i: col_types[i]["text_len"])
                    mapping["narration"] = narration_col

        # Default fallback assignments
        if "date" not in mapping and len(rows[0]) > 0:
            mapping["date"] = 0
        if "narration" not in mapping and len(rows[0]) > 1:
            mapping["narration"] = 1
        if "debit" not in mapping and len(rows[0]) > 2:
            mapping["debit"] = 2
        if "credit" not in mapping and len(rows[0]) > 3:
            mapping["credit"] = 3
        if "balance" not in mapping and len(rows[0]) > 4:
            mapping["balance"] = 4

        return mapping

    @classmethod
    def parse_rows(cls, rows: list, column_mapping: dict) -> list:
        """Converts raw table rows into structured dict records, merging multi-line narrations."""
        transactions = []
        if not rows or not column_mapping:
            return transactions

        date_idx = column_mapping.get("date")
        val_date_idx = column_mapping.get("value_date")
        narration_idx = column_mapping.get("narration")
        ref_idx = column_mapping.get("ref_no")
        debit_idx = column_mapping.get("debit")
        credit_idx = column_mapping.get("credit")
        balance_idx = column_mapping.get("balance")

        current_tx = None

        for row in rows:
            def get_cell(idx):
                if idx is not None and idx < len(row):
                    return str(row[idx]).strip()
                return ""

            cell_date = get_cell(date_idx)
            
            # Merge all text columns between the date column(s) and the amount column(s)
            narration_cells = []
            max_date_col = max(x for x in [date_idx, val_date_idx] if x is not None) if any(x is not None for x in [date_idx, val_date_idx]) else -1
            min_num_col = min(x for x in [debit_idx, credit_idx, balance_idx] if x is not None) if any(x is not None for x in [debit_idx, credit_idx, balance_idx]) else len(row)
            
            for idx in range(max_date_col + 1, min_num_col):
                if idx == ref_idx:
                    continue
                val = get_cell(idx)
                if val:
                    if ParserUtils.is_valid_date(val):
                        continue
                    narration_cells.append(val)
            
            if narration_cells:
                cell_narration = " ".join(narration_cells)
            else:
                cell_narration = get_cell(narration_idx)
            cell_debit = get_cell(debit_idx)
            cell_credit = get_cell(credit_idx)
            cell_balance = get_cell(balance_idx)
            cell_val_date = get_cell(val_date_idx)
            cell_ref = get_cell(ref_idx)

            # If debit and credit are mapped to the same column (single amount column)
            if debit_idx is not None and credit_idx is not None and debit_idx == credit_idx:
                amt_str = cell_debit
                
                # Check if there is an explicit type (Dr/Cr) column mapped
                type_idx = column_mapping.get("type")
                if type_idx is not None:
                    type_str = get_cell(type_idx).lower()
                else:
                    type_str = amt_str.lower()
                    
                is_credit = False
                is_debit = False
                if "cr" in type_str:
                    is_credit = True
                elif "dr" in type_str:
                    is_debit = True
                else:
                    # Fallback to checking narration for keywords if no explicit Dr/Cr suffix
                    narr_lower = cell_narration.lower()
                    if any(kw in narr_lower for kw in ["salary", "credit", "interest", "refund", "deposit", "cr-"]):
                        is_credit = True
                    else:
                        is_debit = True
                
                if is_credit:
                    cell_debit = ""
                    cell_credit = amt_str
                else:
                    cell_debit = amt_str
                    cell_credit = ""

            row_str = " ".join(str(c).lower() for c in row)
            if any(kw in row_str for kw in cls.META_KEYWORDS):
                continue
            
            if not ParserUtils.is_valid_date(cell_date) and not cell_narration:
                continue

            # Identify if this is a new transaction starting
            if ParserUtils.is_valid_date(cell_date):
                if current_tx:
                    transactions.append(current_tx)

                # Initialize new transaction. Original values in narration are preserved intact
                # (UPI IDs, UTRs, timestamps, reference numbers are never removed/stripped)
                current_tx = {
                    "date": cell_date,
                    "narration": cell_narration,
                    "debit": ParserUtils.clean_amount(cell_debit),
                    "credit": ParserUtils.clean_amount(cell_credit),
                    "balance": ParserUtils.clean_balance(cell_balance)
                }
                if val_date_idx is not None:
                    current_tx["value_date"] = cell_val_date
                if ref_idx is not None:
                    current_tx["ref_no"] = cell_ref
            else:
                # Continuation narration row
                if current_tx:
                    if not any(kw in cell_narration.lower() for kw in cls.META_KEYWORDS):
                        if current_tx["narration"]:
                            current_tx["narration"] += " " + cell_narration
                        else:
                            current_tx["narration"] = cell_narration
                        
                        # Populate missing debit/credit/balance if they wrapped to continuation rows
                        if not current_tx["debit"] and cell_debit:
                            current_tx["debit"] = ParserUtils.clean_amount(cell_debit)
                        if not current_tx["credit"] and cell_credit:
                            current_tx["credit"] = ParserUtils.clean_amount(cell_credit)
                        if not current_tx["balance"] and cell_balance:
                            current_tx["balance"] = ParserUtils.clean_balance(cell_balance)

        if current_tx:
            transactions.append(current_tx)

        # Standard cleanups
        for tx in transactions:
            tx["narration"] = re.sub(r"\s+", " ", tx["narration"]).strip()
            if tx["debit"] == "0.00" or tx["debit"] == "0":
                tx["debit"] = ""
            if tx["credit"] == "0.00" or tx["credit"] == "0":
                tx["credit"] = ""

        return transactions
