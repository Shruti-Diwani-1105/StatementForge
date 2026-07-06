import re
import pdfplumber
import datetime

class PDFParser:
    """Extracts text and parses transaction records from digital PDFs using pdfplumber."""

    DATE_PATTERNS = [
        # 01/06/2026 or 01-06-2026
        re.compile(r"^(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b"),
        # 01-Jun-2026 or 1-Jun-26
        re.compile(r"^(\d{1,2}\-[a-zA-Z]{3}\-\d{2,4})\b"),
        # 01 Jun 2026 or 1 Jun 22
        re.compile(r"^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{0,4})\b", re.IGNORECASE)
    ]

    AMOUNT_PATTERN = re.compile(r"\b\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?\b")

    @classmethod
    def extract_raw_text(cls, pdf_path):
        """Extracts all raw text from the PDF."""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"PDFParser: Error extracting text ({e})")
        return text

    @classmethod
    def get_page_count(cls, pdf_path):
        """Returns the number of pages in the PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0

    @classmethod
    def parse_transactions(cls, pdf_path):
        """
        Parses transaction rows. Returns a list of dictionaries:
        [{'date': '...', 'narration': '...', 'debit': 0.0, 'credit': 0.0, 'balance': 0.0}]
        """
        transactions = []
        previous_balance = None

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if not page_text:
                        continue
                    
                    lines = page_text.split("\n")
                    for line in lines:
                        line = line.strip()
                        # Check if line starts with a date
                        matched_date = None
                        for pat in cls.DATE_PATTERNS:
                            m = pat.match(line)
                            if m:
                                matched_date = m.group(1)
                                break
                        
                        if not matched_date:
                            continue
                            
                        # Extract amounts from the rest of the line
                        rest = line[len(matched_date):].strip()
                        # Find all numbers that look like currency (with decimals or 3+ digits)
                        numbers = []
                        # Clean line representation of standard formatting to scan amounts
                        num_matches = cls.AMOUNT_PATTERN.findall(rest)
                        for num_str in num_matches:
                            # Verify if it is a number and not a year
                            val_str = num_str.replace(",", "")
                            try:
                                val = float(val_str)
                                # Exclude numbers that look like years (e.g. 2026) unless they have decimal parts
                                if "." in num_str or val > 9999 or val < 1000:
                                    numbers.append((num_str, val))
                            except ValueError:
                                pass

                        if not numbers:
                            continue

                        # Standard parse: Narration is the middle part
                        narration = rest
                        for num_str, _ in numbers:
                            narration = narration.replace(num_str, "")
                        narration = re.sub(r"\s+", " ", narration).strip()

                        # Reconstruct columns: Date, Narration, Debit, Credit, Balance
                        debit = 0.0
                        credit = 0.0
                        balance = 0.0

                        # Case A: We found 3 amounts (likely Debit, Credit, Balance or vice versa)
                        if len(numbers) >= 3:
                            val1 = numbers[-3][1]
                            val2 = numbers[-2][1]
                            balance = numbers[-1][1]
                            
                            # Decide which is debit and credit based on keywords or balance changes
                            if previous_balance is not None:
                                diff = balance - previous_balance
                                if abs(diff - val2) < 0.05:
                                    credit = val2
                                    debit = 0.0
                                elif abs(diff + val1) < 0.05:
                                    debit = val1
                                    credit = 0.0
                                else:
                                    debit = val1
                                    credit = val2
                            else:
                                # Fallback: assume first is debit, second is credit if we can't verify
                                debit = val1
                                credit = val2

                        # Case B: We found 2 amounts (Amount and Balance)
                        elif len(numbers) == 2:
                            amount = numbers[0][1]
                            balance = numbers[1][1]
                            
                            # Use balance difference to compute debit vs credit
                            if previous_balance is not None:
                                diff = balance - previous_balance
                                if diff > 0:
                                    credit = amount
                                else:
                                    debit = amount
                            else:
                                # Keyword indicators
                                line_lower = line.lower()
                                if any(x in line_lower for x in ["deposit", "cr", "credit", "interest"]):
                                    credit = amount
                                else:
                                    debit = amount

                        # Case C: We found only 1 amount (likely Balance, or no amount columns parsed)
                        elif len(numbers) == 1:
                            balance = numbers[0][1]

                        # Store and update state
                        previous_balance = balance
                        transactions.append({
                            "date": matched_date,
                            "narration": narration if narration else "Transaction Details",
                            "debit": debit,
                            "credit": credit,
                            "balance": balance
                        })
        except Exception as e:
            print(f"PDFParser: Error parsing transactions ({e})")

        return transactions
