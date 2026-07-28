import re
from parser.utils import ParserUtils

class TransactionParser:
    """Parses raw table rows into structured transactions, mapping columns and merging multi-line narrations."""

    META_KEYWORDS = [
        "page", "opening balance", "closing balance", "carried forward", "brought forward",
        "b/f", "c/f", "total", "subtotal", "summary", "statement period", "account summary",
        "date  narration", "date narration", "date description", "date  description"
    ]

    META_REGEX = re.compile(
        r"\b(page|opening\s+balance|closing\s+balance|carried\s+forward|brought\s+forward|b/f|c/f|total|subtotal|summary|statement\s+period|account\s+summary|date\s+narration|date\s+description|discrepancy|kindly\s+report|report\s+to|authorise|signature|manager|clerk|officer|generated\s+output|requires\s+signature|discrepanc|maintain|kindly|transaction\s+count|txn\s+count|total\s+transactions|transaction\s+details)\b",
        re.IGNORECASE
    )

    @classmethod
    def detect_columns(cls, rows: list, bank_layout: dict = None) -> dict:
        """Detects which column indexes map to Date, Value Date, Narration, Ref, Debit, Credit, Balance."""
        mapping = {}
        if not rows:
            return mapping

        header_row_idx = -1
        header_row = []
        for idx, row in enumerate(rows):
            row_str = " ".join(str(c).lower() for c in row)
            has_date = "date" in row_str or "val dt" in row_str or "txn dt" in row_str
            has_other = any(k in row_str for k in ["particulars", "narration", "description", "details", "withdraw", "deposit", "amount", "balance", "debit", "credit"])
            if has_date and has_other:
                header_row_idx = idx
                start_h = max(0, idx - 2)
                combined_header = [""] * len(row)
                for h_idx in range(start_h, idx + 1):
                    for col_idx, cell in enumerate(rows[h_idx]):
                        if col_idx < len(combined_header):
                            val = str(cell).strip()
                            if val:
                                if combined_header[col_idx]:
                                    combined_header[col_idx] += " " + val
                                else:
                                    combined_header[col_idx] = val
                header_row = combined_header
                break

        # If header row found, detect columns by keywords
        if header_row_idx != -1:
            for col_idx, cell in enumerate(header_row):
                cell_clean = cell.replace("_", " ").replace("\n", " ").strip().lower()
                cell_no_space = cell_clean.replace(" ", "")
                
                # Use bank-specific header mappings if present
                if bank_layout:
                    if any(h in cell_clean for h in bank_layout.get("date_headers", [])):
                        if "value" not in cell_clean and "val" not in cell_clean:
                            mapping["date"] = col_idx
                    if any(h in cell_clean for h in bank_layout.get("value_date_headers", ["value date", "val date"])):
                        mapping["value_date"] = col_idx
                    if any(h in cell_clean for h in bank_layout.get("narration_headers", [])):
                        mapping["narration"] = col_idx
                    if any(h in cell_clean for h in bank_layout.get("debit_headers", [])):
                        mapping["debit"] = col_idx
                    if any(h in cell_clean for h in bank_layout.get("credit_headers", [])):
                        mapping["credit"] = col_idx
                    if any(h in cell_clean for h in bank_layout.get("balance_headers", [])):
                        mapping["balance"] = col_idx
                    continue

                if any(x in cell_clean for x in ["balance", "bal"]) or any(x in cell_no_space for x in ["balance", "bal"]):
                    mapping["balance"] = col_idx
                elif "value date" in cell_clean or "val date" in cell_clean or "valuedate" in cell_no_space or "valdate" in cell_no_space or "alue date" in cell_clean:
                    mapping["value_date"] = col_idx
                elif "date" in cell_clean:
                    if "date" not in mapping:
                        mapping["date"] = col_idx
                    else:
                        mapping["value_date"] = col_idx
                elif any(x in cell_clean for x in ["narration", "description", "particulars", "remarks"]) or any(x in cell_no_space for x in ["narration", "description", "particulars", "remarks"]):
                    mapping["narration"] = col_idx
                elif any(x in cell_clean for x in ["chq no", "cheque", "ref no", "reference", "utr", "instrument"]) or any(x in cell_no_space for x in ["chqno", "cheque", "refno", "reference", "utr", "instrument"]):
                    mapping["ref_no"] = col_idx
                elif any(x in cell_clean for x in ["debit", "withdrawal", "withdraw", "payment", "increased"]) or any(w == "dr" for w in cell_clean.replace("/", " ").split()):
                    mapping["debit"] = col_idx
                elif any(x in cell_clean for x in ["credit", "deposit", "receipt", "decreased"]) or any(w == "cr" for w in cell_clean.replace("/", " ").split()):
                    mapping["credit"] = col_idx

            # Single amount column fallback check if no separate debit/credit columns were matched
            if "debit" not in mapping and "credit" not in mapping:
                for col_idx, cell in enumerate(header_row):
                    cell_clean = cell.replace("_", " ").replace("\n", " ").strip().lower()
                    if any(x in cell_clean for x in ["amount dr / cr", "amount dr/cr", "amount(dr/cr)", "amount", "amt"]):
                        mapping["debit"] = col_idx
                        mapping["credit"] = col_idx
                        break

        # Heuristics Fallback if missing Date or Narration
        required_keys = ["date", "narration"]
        is_incomplete = any(k not in mapping for k in required_keys)
        
        if is_incomplete:
            col_types = {i: {"dates": 0, "numeric": 0, "non_empty": 0, "text_len": 0} for i in range(len(rows[0]))}
            num_cols = len(rows[0])
            
            sample_rows = rows[header_row_idx + 1 : header_row_idx + 21] if header_row_idx != -1 else rows[:20]
            for row in sample_rows:
                for col_idx, cell in enumerate(row[:num_cols]):
                    cell_str = str(cell).strip()
                    if ParserUtils.is_valid_date(cell_str):
                        col_types[col_idx]["dates"] += 1
                    elif cell_str:
                        col_types[col_idx]["non_empty"] += 1
                        clean_num = ParserUtils.clean_amount(cell_str)
                        is_num = False
                        if clean_num and clean_num.replace(".", "").isdigit():
                            is_num = True
                        elif cell_str.strip() in ["0", "0.0", "0.00"]:
                            is_num = True
                            
                        if is_num:
                            val_to_check = clean_num if clean_num else "0"
                            if len(val_to_check.split(".")[0]) < 9:
                                col_types[col_idx]["numeric"] += 1
                        col_types[col_idx]["text_len"] += len(cell_str)

            # Map Date (only if not found)
            if "date" not in mapping:
                date_col = max(col_types.keys(), key=lambda i: col_types[i]["dates"])
                if col_types[date_col]["dates"] > 0:
                    mapping["date"] = date_col

            # Map Balance and Debit/Credit (only if not found)
            taken_indices = [mapping[k] for k in ["date", "value_date"] if k in mapping]
            
            numeric_cols = []
            for i, scores in col_types.items():
                non_empty = scores["non_empty"]
                if non_empty > 0:
                    ratio = scores["numeric"] / non_empty
                    if ratio >= 0.7 and scores["numeric"] >= 1 and i not in taken_indices and scores["dates"] == 0:
                        numeric_cols.append(i)
            
            if "balance" not in mapping and numeric_cols:
                mapping["balance"] = numeric_cols[-1]
                numeric_cols = numeric_cols[:-1]
                
            if ("debit" not in mapping or "credit" not in mapping) and numeric_cols:
                taken_all = [mapping[k] for k in ["date", "value_date", "balance", "debit", "credit"] if k in mapping]
                other_numerics = [i for i in numeric_cols if i not in taken_all]
                if "debit" not in mapping and "credit" not in mapping:
                    if len(other_numerics) >= 2:
                        mapping["debit"] = other_numerics[0]
                        mapping["credit"] = other_numerics[1]
                    elif len(other_numerics) == 1:
                        mapping["debit"] = other_numerics[0]
                        mapping["credit"] = other_numerics[0]
                elif "debit" not in mapping and other_numerics:
                    mapping["debit"] = other_numerics[0]
                elif "credit" not in mapping and other_numerics:
                    mapping["credit"] = other_numerics[0]

            # Map Narration (only if not found)
            if "narration" not in mapping:
                taken = [mapping.get(k) for k in ["date", "value_date", "balance", "debit", "credit"] if mapping.get(k) is not None]
                remaining_cols = [i for i in col_types.keys() if i not in taken]
                if remaining_cols:
                    narration_col = max(remaining_cols, key=lambda i: col_types[i]["text_len"])
                    mapping["narration"] = narration_col

        return mapping

    @classmethod
    def parse_rows(cls, rows: list, mapping: dict) -> list:
        """Parses rows using mapping and merges multi-line narration blocks."""
        if not rows or not mapping:
            return []

        date_idx = mapping.get("date")
        narration_idx = mapping.get("narration")
        debit_idx = mapping.get("debit")
        credit_idx = mapping.get("credit")
        balance_idx = mapping.get("balance")
        val_date_idx = mapping.get("value_date")
        ref_idx = mapping.get("ref_no")

        transactions = []
        current_tx = None

        for r_idx, row in enumerate(rows):
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
            if balance_idx is not None and balance_idx + 1 < len(row):
                indicator = str(row[balance_idx + 1]).strip().upper()
                if "DR" in indicator:
                    cell_balance += " DR"
                elif "CR" in indicator:
                    cell_balance += " CR"
            cell_val_date = get_cell(val_date_idx)
            cell_ref = get_cell(ref_idx)
            row_str = " ".join(str(c).lower() for c in row)

            # If debit and credit are mapped to the same column (single amount column)
            if debit_idx is not None and credit_idx is not None and debit_idx == credit_idx:
                amt_str = ParserUtils.clean_amount(cell_debit)
                is_credit = False
                
                # Check for CR indicator or credit keywords in narration
                narr_lower = cell_narration.lower()
                if "cr" in row_str.lower() or "credit" in row_str.lower() or "deposit" in row_str.lower() or "refund" in row_str.lower():
                    is_credit = True
                
                if amt_str:
                    if is_credit:
                        cell_debit = ""
                        cell_credit = amt_str
                    else:
                        cell_debit = amt_str
                        cell_credit = ""
                else:
                    cell_debit = ""
                    cell_credit = ""
                
            if cls.META_REGEX.search(row_str):
                if not (ParserUtils.is_valid_date(cell_date) or ParserUtils.is_valid_date(cell_val_date)):
                    continue
            
            # Determine if this row starts a new transaction
            is_new_tx = bool(ParserUtils.is_valid_date(cell_date) or ParserUtils.is_valid_date(cell_val_date))
            if not is_new_tx and current_tx:
                has_amount = False
                if cell_debit and ParserUtils.clean_amount(cell_debit):
                    has_amount = True
                if cell_credit and ParserUtils.clean_amount(cell_credit):
                    has_amount = True
                if has_amount:
                    is_new_tx = True

            if not is_new_tx and not cell_narration and not cell_debit and not cell_credit and not cell_balance:
                continue

            if is_new_tx:
                if current_tx:
                    transactions.append(current_tx)

                # Determine the date for the new transaction (inherit from previous if blank)
                tx_date = ""
                if ParserUtils.is_valid_date(cell_date):
                    tx_date = cell_date.replace('\n', '').replace('\r', '').replace(' ', '').strip()
                elif ParserUtils.is_valid_date(cell_val_date):
                    tx_date = cell_val_date.replace('\n', '').replace('\r', '').replace(' ', '').strip()
                elif current_tx:
                    tx_date = current_tx["date"]
                    
                # Determine value date
                tx_val_date = ""
                if val_date_idx is not None:
                    if ParserUtils.is_valid_date(cell_val_date):
                        tx_val_date = cell_val_date.replace('\n', '').replace('\r', '').replace(' ', '').strip()
                    elif ParserUtils.is_valid_date(cell_date):
                        tx_val_date = cell_date.replace('\n', '').replace('\r', '').replace(' ', '').strip()
                    elif current_tx:
                        tx_val_date = current_tx.get("value_date", "")

                current_tx = {
                    "date": tx_date,
                    "narration": cell_narration,
                    "debit": ParserUtils.clean_amount(cell_debit),
                    "credit": ParserUtils.clean_amount(cell_credit),
                    "balance": ParserUtils.clean_balance(cell_balance),
                    "_grid_row_idx": r_idx
                }
                if val_date_idx is not None:
                    current_tx["value_date"] = tx_val_date
                if ref_idx is not None:
                    current_tx["ref_no"] = cell_ref
            else:
                # Continuation narration row
                if current_tx:
                    if not cls.META_REGEX.search(cell_narration):
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
