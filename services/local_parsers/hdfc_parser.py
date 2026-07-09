import re
from services.local_parsers.base_parser import BaseParser

class HDFCParser(BaseParser):
    @classmethod
    def parse(cls, raw_text: str) -> dict:
        """
        Parses raw text from HDFC digital statements.
        Handles metadata extraction (Account Holder, Number, Period)
        and transaction extraction with multi-line narration support.
        """
        metadata = {
            "bank_name": "HDFC Bank",
            "account_holder": "Unknown",
            "account_number": "Unknown",
            "period": "Unknown Period",
            "currency": "INR"
        }
        
        # 1. Extract metadata
        holder_match = re.search(r"Account Holder:\s*(.*)", raw_text, re.IGNORECASE)
        if holder_match:
            metadata["account_holder"] = holder_match.group(1).strip()
            
        acc_match = re.search(r"Account Number:\s*(\w+)", raw_text, re.IGNORECASE)
        if acc_match:
            metadata["account_number"] = acc_match.group(1).strip()
            
        period_match = re.search(
            r"period(?:\s+of)?(?:\s+account)?:\s*(.*?)(?:\n|$)|period\s+(\d{2}-\w{3}-\d{4}\s+to\s+\d{2}-\w{3}-\d{4})|period\s+([\d/]+\s+to\s+[\d/]+)",
            raw_text,
            re.IGNORECASE
        )
        if period_match:
            period_str = next((g for g in period_match.groups() if g), None)
            if period_str:
                metadata["period"] = period_str.strip()
                
        currency_match = re.search(r"Currency:\s*(\w+)", raw_text, re.IGNORECASE)
        if currency_match:
            metadata["currency"] = currency_match.group(1).strip()
            
        transactions = []
        
        # Match lines starting with a Date (e.g. DD/MM/YYYY, DD-MM-YYYY, DD-MMM-YYYY, DD/MM/YY)
        # Handles various separators: '/' or '-'
        date_pattern = r"^(\d{2}[/\-]\d{2}[/\-]\d{2,4}|\d{2}[/\-][a-zA-Z]{3}[/\-]\d{2,4})"
        
        lines = raw_text.splitlines()
        current_tx = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip table headers
            if re.match(r"^Date\s+Narration", line, re.IGNORECASE) or re.match(r"^Date\s+Description", line, re.IGNORECASE):
                continue
                
            date_match = re.match(date_pattern, line)
            if date_match:
                # Save previous transaction if complete
                if current_tx:
                    transactions.append(current_tx)
                    
                date_str = date_match.group(1)
                remaining = line[len(date_str):].strip()
                
                # We need to split the remaining text into: Narration, Debit, Credit, Balance
                # In digital PDFs, columns are separated by multiple spaces (usually 2 or more)
                parts = re.split(r"\s{2,}", remaining)
                
                # Clean up empty strings or single spaces
                parts = [p.strip() for p in parts if p.strip()]
                
                debit_val = 0.0
                credit_val = 0.0
                balance_val = None
                narration_str = remaining
                
                # Check if we have at least narration and amounts
                if len(parts) >= 2:
                    # Let's check if the last elements look like numbers/amounts
                    # An amount can look like: "550.00", "0.00", "25,450.00", "-", "0"
                    def is_numeric_field(val):
                        val_clean = re.sub(r"[^\d\.\-]", "", val)
                        if not val_clean or val_clean == "-":
                            return True
                        try:
                            float(val_clean)
                            return True
                        except ValueError:
                            return False
                            
                    # Let's check from the right end of parts
                    # Standard columns: Narration | Debit | Credit | Balance
                    if len(parts) >= 4 and is_numeric_field(parts[-1]) and is_numeric_field(parts[-2]) and is_numeric_field(parts[-3]):
                        narration_str = " ".join(parts[:-3])
                        debit_val = parts[-3]
                        credit_val = parts[-2]
                        balance_val = parts[-1]
                    elif len(parts) >= 3 and is_numeric_field(parts[-1]) and is_numeric_field(parts[-2]):
                        # Narration | Amount | Balance (some banks have single Amount column, but HDFC usually has Debit/Credit/Balance)
                        narration_str = " ".join(parts[:-2])
                        # If credit or debit is empty, we decide based on the values
                        # Let's assume the first is amount, last is balance
                        amount_str = parts[-2]
                        balance_val = parts[-1]
                        # Let's parse the amount_str sign
                        try:
                            amt_val = float(re.sub(r"[^\d\.\-]", "", amount_str))
                            if amt_val < 0:
                                debit_val = abs(amt_val)
                                credit_val = 0.0
                            else:
                                debit_val = 0.0
                                credit_val = amt_val
                        except ValueError:
                            pass
                    else:
                        # If split by spaces didn't give us clean parts, fallback to regex search from the right
                        # Find all number patterns like: 550.00, 25,450.00, 0.00
                        amount_matches = list(re.finditer(r"(-?[\d,]+\.\d{2}|0\.00|0|-)", remaining))
                        if len(amount_matches) >= 3:
                            m1, m2, m3 = amount_matches[-3], amount_matches[-2], amount_matches[-1]
                            # Make sure they are at the end of the line
                            narration_str = remaining[:m1.start()].strip()
                            debit_val = m1.group(1)
                            credit_val = m2.group(1)
                            balance_val = m3.group(1)
                
                current_tx = {
                    "date": date_str,
                    "narration": narration_str,
                    "debit": debit_val,
                    "credit": credit_val,
                    "balance": balance_val
                }
            else:
                # Continuation of narration from previous line
                if current_tx:
                    # Ignore lines with meta/header/footer content
                    meta_keywords = ["page", "opening balance", "closing balance", "carried forward", "brought forward"]
                    if not any(kw in line.lower() for kw in meta_keywords):
                        current_tx["narration"] += " " + line
                        
        if current_tx:
            transactions.append(current_tx)
            
        return {
            "metadata": metadata,
            "transactions": transactions
        }
