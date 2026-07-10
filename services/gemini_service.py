import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class GeminiService:
    """Communicates with the Google Gemini API, OpenAI API, or uses a local rule-based parser."""
    
    @classmethod
    def get_api_key(cls):
        """Fetches the Gemini API Key from the environment variables."""
        load_dotenv(override=True)
        return os.getenv("GEMINI_API_KEY")

    @classmethod
    def _get_prompt(cls):
        return """You are an expert Financial Statement Parser.
Analyze the uploaded bank statement.

Automatically identify:
Bank Name
Account Holder
Account Number
Statement Period
Currency

Extract ALL transactions.

Requirements
Merge narration spanning multiple lines into ONE single narration.
Do not split one transaction into multiple rows.
Ignore page headers.
Ignore page footers.
Ignore watermark.
Ignore page numbers.
Return only transactions.
Return valid JSON only.

Each transaction must contain
Date
Narration
Debit
Credit
Balance

If Debit is empty return 0.
If Credit is empty return 0.
If Balance is empty return null.

Do not explain anything.
Return JSON only."""

    @classmethod
    def parse_statement_text(cls, text):
        """
        Sends the statement text to Gemini/OpenAI API, or uses a local parser, and gets structured JSON.
        Returns a dictionary containing statement details and transaction rows.
        """
        # Reload environment dynamically
        load_dotenv(override=True)
        
        use_local = os.getenv("USE_LOCAL_PARSER", "false").lower() == "true"
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = cls.get_api_key()

        # If explicitly told to use local parser, or if no keys are configured
        if use_local or (not openai_key and not gemini_key):
            print("GeminiService: Using local regex-based parser (no AI)...")
            return cls._parse_rule_based(text)

        # If OPENAI_API_KEY is configured and not empty, use OpenAI
        if openai_key and openai_key.strip():
            print("GeminiService: OPENAI_API_KEY detected. Parsing with OpenAI GPT-4o-mini...")
            return cls._parse_with_openai(text, openai_key.strip())

        # Otherwise fallback/default to Gemini
        print("GeminiService: Parsing with Google Gemini...")
        return cls._parse_with_gemini(text, gemini_key.strip())

    @classmethod
    def _parse_rule_based(cls, text):
        """
        Runs local rule-based regex parsing on the raw statement text.
        Extracts metadata and transactions without calling any external API.
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 1. Detect Bank Name
        bank_name = "Unknown Bank"
        banks = ["HDFC", "State Bank of India", "SBI", "ICICI", "Axis Bank", "Kotak", "Canara Bank", "Bank of Baroda", "BoB", "IndusInd"]
        for bank in banks:
            if re.search(r'\b' + re.escape(bank) + r'\b', text, re.IGNORECASE):
                bank_name = bank
                break
                
        # 2. Detect Account Holder
        account_holder = "Unknown"
        holder_patterns = [
            r"(?:Account Holder|Customer Name|Name)\s*:\s*([A-Za-z \t\.]+)",
            r"Holder\s*:\s*([A-Za-z \t\.]+)"
        ]
        for pattern in holder_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                account_holder = m.group(1).strip()
                break
                
        # 3. Detect Account Number
        account_number = "Unknown"
        acc_patterns = [
            r"(?:Account Number|A/c No\.?|Account No\.?)\s*:\s*(\d+)",
            r"Account\s+No\s+(\d+)"
        ]
        for pattern in acc_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                account_number = m.group(1).strip()
                break
                
        # 4. Detect Statement Period
        statement_period = "Unknown Period"
        period_patterns = [
            r"(?:Period|Statement Period)\s*:\s*([A-Za-z0-9\-\ \t/to]+)",
            r"for the period\s+([A-Za-z0-9\-\ \t/to]+)"
        ]
        for pattern in period_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                statement_period = m.group(1).strip()
                break
                
        # 5. Detect Currency
        currency = "INR"
        if "USD" in text or "$" in text:
            currency = "USD"
        elif "EUR" in text or "€" in text:
            currency = "EUR"

        # 6. Extract Transactions
        transactions = []
        
        # Date regex matches dd/mm/yyyy, dd-mm-yyyy, dd-mmm-yyyy, dd-mmm-yy
        date_pattern = r"(?:\b|^)(\d{1,2}[/\-\s](?:\d{1,2}|[A-Za-z]{3})[/\-\s]\d{2,4})(?:\b|$)"
        
        for line in lines:
            # Check if line contains a date
            match_date = re.search(date_pattern, line)
            if not match_date:
                continue
                
            date_str = match_date.group(1)
            
            # Skip header, footer, or metadata lines
            lower_line = line.lower()
            if any(term in lower_line for term in ["statement period", "statement of account", "page of", "statement for the period", "period:"]):
                continue
            
            # Remove date from the line to parse narration and amounts
            remaining = line.replace(date_str, "", 1).strip()
            
            # Find all numbers (including decimals and commas) in the remaining string
            amounts = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b|\b\d+(?:\.\d{2})?\b", remaining)
            
            valid_amounts = []
            for amt in amounts:
                clean_amt = amt.replace(",", "")
                try:
                    val = float(clean_amt)
                    # Exclude year numbers or small numbers unless they represent standard money
                    if "." in amt or val == 0.0:
                        valid_amounts.append((amt, val))
                    elif val > 100 or val == 0:
                        valid_amounts.append((amt, val))
                except ValueError:
                    pass
            
            # Extract narration by removing the detected amount strings
            narration_str = remaining
            for amt, _ in valid_amounts:
                narration_str = narration_str.replace(amt, "", 1)
            
            narration_str = re.sub(r"\s+", " ", narration_str).strip()
            narration_str = re.sub(r"^[\-\s\.,]+|[\-\s\.,]+$", "", narration_str).strip()
            
            if not narration_str:
                narration_str = "Transaction Details"

            debit = 0.0
            credit = 0.0
            balance = None
            
            if len(valid_amounts) >= 3:
                val1 = valid_amounts[0][1]
                val2 = valid_amounts[1][1]
                val3 = valid_amounts[2][1]
                
                if val1 > 0 and val2 == 0:
                    debit = val1
                elif val2 > 0 and val1 == 0:
                    credit = val2
                else:
                    is_credit = any(kw in narration_str.lower() for kw in ["salary", "credit", "interest", "refund", "deposit", "cr"])
                    if is_credit:
                        credit = val1
                        debit = val2
                    else:
                        debit = val1
                        credit = val2
                balance = val3
                
            elif len(valid_amounts) == 2:
                val1 = valid_amounts[0][1]
                balance = valid_amounts[1][1]
                
                is_credit = any(kw in narration_str.lower() for kw in ["salary", "credit", "interest", "refund", "deposit", "cr"])
                if is_credit:
                    credit = val1
                else:
                    debit = val1
                    
            elif len(valid_amounts) == 1:
                val1 = valid_amounts[0][1]
                is_credit = any(kw in narration_str.lower() for kw in ["salary", "credit", "interest", "refund", "deposit", "cr"])
                if is_credit:
                    credit = val1
                else:
                    debit = val1

            transactions.append({
                "date": date_str,
                "narration": narration_str,
                "debit": debit,
                "credit": credit,
                "balance": balance
            })

        return {
            "bank_name": bank_name,
            "account_holder": account_holder,
            "account_number": account_number,
            "statement_period": statement_period,
            "currency": currency,
            "transactions": transactions
        }

    @classmethod
    def _parse_with_gemini(cls, text, api_key):
        try:
            # Configure Google Generative AI
            genai.configure(api_key=api_key)
            
            # Using production model: gemini-2.0-flash
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            prompt = cls._get_prompt()
            
            # We request JSON specifically using generation_config
            generation_config = {
                "response_mime_type": "application/json"
            }
            
            # Combine system prompt with raw text content
            response = model.generate_content(
                contents=[prompt, f"Statement text to parse:\n{text}"],
                generation_config=generation_config
            )
            
            response_text = response.text.strip()
            
            # Clean potential markdown wrappers if returned
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "", 1)
            if response_text.endswith("```"):
                response_text = response_text.rsplit("```", 1)[0]
            response_text = response_text.strip()
            
            # Parse response as JSON to validate structure
            data = json.loads(response_text)
            return data
            
        except json.JSONDecodeError as je:
            raise RuntimeError(
                f"Failed to parse transaction data from Gemini. The AI model output was not valid JSON:\n{je}\n\nRaw Output:\n{response_text[:300]}..."
            )
        except Exception as e:
            # Handle rate limit, connection, auth issues
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg:
                raise RuntimeError("Invalid Google Gemini API Key. Please verify the key set in your .env file.")
            elif "Quota exceeded" in err_msg or "429" in err_msg:
                raise RuntimeError(
                    "Google Gemini API quota exceeded (Rate Limit/Usage Cap hit).\n\n"
                    "To fix this error:\n"
                    "1. Go to Google AI Studio (https://aistudio.google.com/) and create a new free API Key.\n"
                    "2. Standard keys start with 'AIzaSy'. Copy it and update GEMINI_API_KEY in your .env file.\n"
                    "3. Alternatively, enable pay-as-you-go billing in AI Studio for higher limits, or set OPENAI_API_KEY in your .env file to use OpenAI."
                )
            else:
                raise RuntimeError(f"Google Gemini API connection error: {e}")


    @classmethod
    def _parse_with_openai(cls, text, api_key):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            prompt = cls._get_prompt()
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Statement text to parse:\n{text}"}
                ],
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content.strip()
            
            data = json.loads(response_text)
            return data
            
        except json.JSONDecodeError as je:
            raise RuntimeError(
                f"Failed to parse transaction data from OpenAI. The AI model output was not valid JSON:\n{je}\n\nRaw Output:\n{response_text[:300]}..."
            )
        except Exception as e:
            err_msg = str(e)
            if "invalid_api_key" in err_msg or "Incorrect API key" in err_msg or "invalid api key" in err_msg.lower():
                raise RuntimeError("Invalid OpenAI API Key. Please verify the key set in your .env file.")
            elif "rate_limit" in err_msg or "429" in err_msg or "quota" in err_msg.lower():
                raise RuntimeError("OpenAI API quota exceeded or rate limit hit. Please check your billing status or retry later.")
            else:
                raise RuntimeError(f"OpenAI API connection error: {e}")

    @classmethod
    def parse_page_image(cls, pil_image) -> dict:
        """
        Sends the PIL image of the scanned PDF page to Gemini/OpenAI API as a last-resort fallback.
        Includes automatic retry backoff for 429 rate limits.
        """
        load_dotenv(override=True)
        gemini_key = cls.get_api_key()
        openai_key = os.getenv("OPENAI_API_KEY")

        if not gemini_key and not openai_key:
            raise RuntimeError("No AI API Keys are configured. Cannot run fallback vision parser.")

        if gemini_key and gemini_key.strip():
            import time
            max_retries = 5
            base_delay = 5  # start with 5 seconds
            
            for attempt in range(max_retries):
                try:
                    genai.configure(api_key=gemini_key.strip())
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    prompt = cls._get_prompt()
                    generation_config = {
                        "response_mime_type": "application/json"
                    }
                    
                    response = model.generate_content(
                        contents=[prompt, pil_image],
                        generation_config=generation_config
                    )
                    
                    response_text = response.text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text.replace("```json", "", 1)
                    if response_text.endswith("```"):
                        response_text = response_text.rsplit("```", 1)[0]
                    response_text = response_text.strip()
                    
                    data = json.loads(response_text)
                    return data
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "Quota exceeded" in err_msg or "ResourceExhausted" in err_msg or "rate limit" in err_msg.lower():
                        if attempt < max_retries - 1:
                            sleep_time = base_delay * (2 ** attempt)
                            print(f"[Gemini] Rate limit hit. Retrying in {sleep_time} seconds (Attempt {attempt+1}/{max_retries})...")
                            time.sleep(sleep_time)
                            continue
                    raise RuntimeError(f"Gemini Vision fallback failed: {e}")

        elif openai_key and openai_key.strip():
            try:
                import base64
                from io import BytesIO
                from openai import OpenAI
                
                client = OpenAI(api_key=openai_key.strip())
                prompt = cls._get_prompt()
                
                buffered = BytesIO()
                if pil_image.mode == 'RGBA':
                    pil_image = pil_image.convert('RGB')
                pil_image.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract transactions from this bank statement page image."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_str}"
                                    }
                                }
                            ]
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                response_text = response.choices[0].message.content.strip()
                data = json.loads(response_text)
                return data
            except Exception as e:
                raise RuntimeError(f"OpenAI Vision fallback failed: {e}")

        raise RuntimeError("No AI API Keys are configured.")

    @classmethod
    def detect_bank_from_image(cls, pil_image) -> str:
        """
        Sends the PIL image of the first page to Gemini Vision to identify the bank name.
        Includes automatic retry backoff.
        """
        load_dotenv(override=True)
        gemini_key = cls.get_api_key()
        if not gemini_key or not gemini_key.strip():
            return "Unknown Bank"

        import time
        max_retries = 5
        base_delay = 5

        for attempt in range(max_retries):
            try:
                genai.configure(api_key=gemini_key.strip())
                model = genai.GenerativeModel("gemini-2.0-flash")
                prompt = (
                    "Analyze this bank statement page image. "
                    "Identify which bank it belongs to (e.g. HDFC Bank, State Bank of India, ICICI Bank, Axis Bank, Kotak Mahindra Bank, Bank of Baroda, etc.). "
                    "Return ONLY the bank name as plain text (e.g. 'HDFC Bank'). Do not include any formatting or other words."
                )
                response = model.generate_content(contents=[prompt, pil_image])
                bank_name = response.text.strip()
                
                # Match detected text against standard list
                for standard_name in [
                    "HDFC Bank", "State Bank of India", "ICICI Bank", "Axis Bank", 
                    "Kotak Mahindra Bank", "Bank of Baroda", "Canara Bank", 
                    "Union Bank of India", "Punjab National Bank", "IDFC First Bank", 
                    "IndusInd Bank", "Yes Bank", "Federal Bank", "UCO Bank", 
                    "Central Bank of India", "Indian Bank", "Indian Overseas Bank", 
                    "AU Small Finance Bank", "Bandhan Bank", "RBL Bank", "South Indian Bank"
                ]:
                    if standard_name.lower() in bank_name.lower():
                        return standard_name
                return bank_name
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "Quota exceeded" in err_msg or "ResourceExhausted" in err_msg or "rate limit" in err_msg.lower():
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt)
                        time.sleep(sleep_time)
                        continue
                pass
        return "Unknown Bank"



