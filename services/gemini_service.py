import os
import json
import re
import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from settings.settings_service import SettingsService

# Ensure environment variables are loaded
load_dotenv()

class GeminiService:
    """
    Communicates with the Google Gemini API using google-genai,
    providing advanced financial auditing, risk detection, and business recommendations.
    """
    _client = None
    _current_api_key = None
    
    @classmethod
    def get_api_key(cls):
        """Fetches the Gemini API Key from the environment variables or cache."""
        load_dotenv(override=True)
        # Try local settings first
        settings = SettingsService.get_cached_settings()
        api_key = settings.get("ai_api_key") or os.getenv("GEMINI_API_KEY")
        return api_key

    @classmethod
    def get_client(cls):
        """Initializes and returns the singleton Google Gemini Client."""
        api_key = cls.get_api_key()
        if not api_key or not api_key.strip():
            raise RuntimeError("Missing Google Gemini API Key. Please add GEMINI_API_KEY in your .env file or Settings.")
            
        api_key_clean = api_key.strip()
        # Initialize or reinitialize if key changed
        if cls._client is None or cls._current_api_key != api_key_clean:
            cls._client = genai.Client(api_key=api_key_clean)
            cls._current_api_key = api_key_clean
            print("GeminiService: Initialized new google-genai Client instance.")
            
        return cls._client

    @classmethod
    def _get_prompt(cls):
        """Default financial statement transaction extraction prompt."""
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
    def _handle_exception(cls, e):
        """Maps API exceptions into user-friendly error messages."""
        err_msg = str(e)
        print(f"GeminiService Error Detail: {err_msg}")
        
        if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg or "invalid api key" in err_msg.lower() or "unauthorized" in err_msg.lower():
            raise RuntimeError(
                "Invalid Google Gemini API Key. Please verify the key set in your settings or .env file."
            )
        elif "quota" in err_msg.lower() or "429" in err_msg or "resource_exhausted" in err_msg.lower() or "exhausted" in err_msg.lower():
            raise RuntimeError(
                "Google Gemini API quota exceeded (Rate Limit/Usage Cap hit).\n\n"
                "To fix this error:\n"
                "1. If you are on the free tier, wait 1-2 minutes and retry.\n"
                "2. Visit Google AI Studio (https://aistudio.google.com/) and create a new API Key.\n"
                "3. Consider enabling pay-as-you-go billing in AI Studio for higher limit quotas."
            )
        elif "timeout" in err_msg.lower() or "504" in err_msg or "deadline" in err_msg.lower() or "timed out" in err_msg.lower():
            raise RuntimeError(
                "Google Gemini API request timed out. The server took too long to respond. Please try again."
            )
        elif "conn" in err_msg.lower() or "dns" in err_msg.lower() or "reach" in err_msg.lower() or "socket" in err_msg.lower() or "http_request" in err_msg.lower():
            raise RuntimeError(
                "Internet connection failure. Could not connect to Google Gemini API servers.\n\n"
                "Please verify your network connection and check if proxy settings are blocking the request."
            )
        elif "empty response" in err_msg.lower():
            raise RuntimeError(
                "Google Gemini returned an empty response. Please try modifying your query or statement data."
            )
        else:
            raise RuntimeError(f"Google Gemini API Error: {err_msg}")

    @classmethod
    def _call_gemini(cls, prompt: str, system_instruction: str = None) -> str:
        """Helper to invoke Gemini API with automatic model fallback."""
        try:
            client = cls.get_client()
            
            # Retrieve parameters from settings
            settings = SettingsService.get_cached_settings()
            model_name = settings.get("ai_model", "Gemini 2.5 Flash")
            
            # Map user-friendly model strings to API identifiers
            model_map = {
                "Gemini 2.5 Flash": "gemini-2.5-flash",
                "Gemini 2.5 Pro": "gemini-2.5-pro",
                "Gemini 1.5 Flash": "gemini-1.5-flash",
                "Gemini 1.5 Pro": "gemini-1.5-pro",
                "Gemini 3.5 Flash (High)": "gemini-3.5-flash",
                "Gemini 3.5 Flash": "gemini-3.5-flash"
            }
            api_model = model_map.get(model_name, "gemini-2.5-flash")
            
            temp_val = settings.get("ai_temperature", 70)
            temp = float(temp_val) / 100.0 if temp_val is not None else 0.7
            
            max_tokens_val = settings.get("ai_max_tokens", 2048)
            max_tokens = int(max_tokens_val) if max_tokens_val is not None else 2048
            
            top_p_val = settings.get("ai_top_p", 95)
            top_p = float(top_p_val) / 100.0 if top_p_val is not None else 0.95
            
            top_k_val = settings.get("ai_top_k", 40)
            top_k = int(top_k_val) if top_k_val is not None else 40
            
            config = types.GenerateContentConfig(
                temperature=temp,
                max_output_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                system_instruction=system_instruction
            )
            
            # Set up fallbacks for deprecation 404
            models_to_try = [api_model]
            # fallback order
            for fallback in ["gemini-2.0-flash", "gemini-3.5-flash", "gemini-1.5-flash"]:
                if fallback not in models_to_try:
                    models_to_try.append(fallback)
            
            last_error = None
            for m in models_to_try:
                try:
                    print(f"GeminiService: Invoking model {m}...")
                    response = client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=config
                    )
                    if response and response.text:
                        return response.text.strip()
                    else:
                        raise ValueError("Received empty response from Gemini API.")
                except Exception as e:
                    last_error = e
                    err_msg = str(e)
                    # If model is not found (404), continue fallback loop
                    if "404" in err_msg or "not found" in err_msg.lower() or "no longer available" in err_msg.lower():
                        print(f"GeminiService: Model {m} failed with 404 (Not Found/Deprecated). Attempting next model...")
                        continue
                    else:
                        raise e
            if last_error:
                raise last_error
                
        except Exception as e:
            cls._handle_exception(e)

    @classmethod
    def _format_transactions(cls, transactions, currency="INR") -> str:
        """Converts transaction dictionary list to a structured text format for prompt parsing."""
        formatted = []
        for i, tx in enumerate(transactions):
            date = tx.get("date", "")
            narration = tx.get("narration", "")
            debit = tx.get("debit", "")
            credit = tx.get("credit", "")
            balance = tx.get("balance", "")
            
            debit_str = f"{currency} {debit}" if (debit and float(debit) > 0) else "-"
            credit_str = f"{currency} {credit}" if (credit and float(credit) > 0) else "-"
            balance_str = f"{currency} {balance}" if balance else "-"
            
            formatted.append(
                f"Tx #{i+1} | Date: {date} | Narration: {narration} | Debit: {debit_str} | Credit: {credit_str} | Balance: {balance_str}"
            )
        return "\n".join(formatted)

    # ====================================================
    # EXISTING PARSING CORE (RE-ENGINEERED TO NEW SDK CLIENT)
    # ====================================================
    
    @classmethod
    def parse_statement_text(cls, text):
        """Sends the statement text to Gemini/OpenAI API and gets structured JSON."""
        load_dotenv(override=True)
        use_local = os.getenv("USE_LOCAL_PARSER", "false").lower() == "true"
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = cls.get_api_key()

        if use_local or (not openai_key and not gemini_key):
            print("GeminiService: Using local regex-based parser (no AI)...")
            return cls._parse_rule_based(text)

        if openai_key and openai_key.strip():
            print("GeminiService: OPENAI_API_KEY detected. Parsing with OpenAI GPT-4o-mini...")
            return cls._parse_with_openai(text, openai_key.strip())

        print("GeminiService: Parsing with Google Gemini...")
        return cls._parse_with_gemini(text, gemini_key.strip())

    @classmethod
    def _parse_rule_based(cls, text):
        """Runs local rule-based regex parsing on the raw statement text."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        bank_name = "Unknown Bank"
        banks = ["HDFC", "State Bank of India", "SBI", "ICICI", "Axis Bank", "Kotak", "Canara Bank", "Bank of Baroda", "BoB", "IndusInd"]
        for bank in banks:
            if re.search(r'\b' + re.escape(bank) + r'\b', text, re.IGNORECASE):
                bank_name = bank
                break
                
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
                
        currency = "INR"
        if "USD" in text or "$" in text:
            currency = "USD"
        elif "EUR" in text or "€" in text:
            currency = "EUR"

        transactions = []
        date_pattern = r"(?:\b|^)(\d{1,2}[/\-\s](?:\d{1,2}|[A-Za-z]{3})[/\-\s]\d{2,4})(?:\b|$)"
        
        for line in lines:
            match_date = re.search(date_pattern, line)
            if not match_date:
                continue
                
            date_str = match_date.group(1)
            lower_line = line.lower()
            if any(term in lower_line for term in ["statement period", "statement of account", "page of", "statement for the period", "period:"]):
                continue
            
            remaining = line.replace(date_str, "", 1).strip()
            amounts = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b|\b\d+(?:\.\d{2})?\b", remaining)
            
            valid_amounts = []
            for amt in amounts:
                clean_amt = amt.replace(",", "")
                try:
                    val = float(clean_amt)
                    if "." in amt or val == 0.0:
                        valid_amounts.append((amt, val))
                    elif val > 100 or val == 0:
                        valid_amounts.append((amt, val))
                except ValueError:
                    pass
            
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
            client = cls.get_client()
            prompt = cls._get_prompt()
            
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            
            # Using stable model for structural JSON parsing
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, f"Statement text to parse:\n{text}"],
                config=config
            )
            
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "", 1)
            if response_text.endswith("```"):
                response_text = response_text.rsplit("```", 1)[0]
            response_text = response_text.strip()
            
            data = json.loads(response_text)
            return data
            
        except json.JSONDecodeError as je:
            raise RuntimeError(
                f"Failed to parse transaction data from Gemini. The AI model output was not valid JSON:\n{je}\n\nRaw Output:\n{response_text[:300]}..."
            )
        except Exception as e:
            cls._handle_exception(e)

    @classmethod
    def _parse_with_openai(cls, text, api_key):
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)
            prompt = cls._get_prompt()
            
            response = openai_client.chat.completions.create(
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
            raise RuntimeError(f"OpenAI response was not valid JSON: {je}")
        except Exception as e:
            err_msg = str(e)
            if "invalid_api_key" in err_msg or "Incorrect API key" in err_msg or "invalid api key" in err_msg.lower():
                raise RuntimeError("Invalid OpenAI API Key. Please verify the key set in your .env file.")
            elif "rate_limit" in err_msg or "429" in err_msg or "quota" in err_msg.lower():
                raise RuntimeError("OpenAI API quota exceeded or rate limit hit. Please check your billing status or retry later.")
            else:
                raise RuntimeError(f"OpenAI API connection error: {e}")

    @classmethod
    def _ensure_png_image(cls, pil_image):
        """Converts raw/PPM PIL images (like those from pdfium) into standard PNG format."""
        if pil_image is None:
            return None
        try:
            import io
            from PIL import Image
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            buffer.seek(0)
            return Image.open(buffer)
        except Exception as e:
            print(f"GeminiService: Failed to convert image to standard PNG format: {e}")
            return pil_image

    @classmethod
    def parse_page_image(cls, pil_image) -> dict:
        """Sends scanned PIL image to Gemini Vision to extract transactions with auto-fallback."""
        try:
            client = cls.get_client()
            prompt = cls._get_prompt()
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            
            # Format to PNG format to avoid SDK format unsupported errors
            img_to_send = cls._ensure_png_image(pil_image)
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, img_to_send],
                config=config
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
            cls._handle_exception(e)

    @classmethod
    def detect_bank_from_image(cls, pil_image) -> str:
        """Identifies bank name from PIL page image."""
        try:
            client = cls.get_client()
            prompt = (
                "Analyze this bank statement page image. "
                "Identify which bank it belongs to (e.g. HDFC Bank, State Bank of India, ICICI Bank, Axis Bank, Kotak Mahindra Bank, Bank of Baroda, etc.). "
                "Return ONLY the bank name as plain text (e.g. 'HDFC Bank'). Do not include any formatting or other words."
            )
            # Format to PNG format to avoid SDK format unsupported errors
            img_to_send = cls._ensure_png_image(pil_image)
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, img_to_send]
            )
            bank_name = response.text.strip()
            
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
        except Exception:
            return "Unknown Bank"

    # ====================================================
    # NEW FEATURE METHODS: FINANCIAL AUDITOR & BUSINESS ADVISOR
    # ====================================================

    @classmethod
    def _get_report_styles(cls) -> str:
        return """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                color: #1E293B;
                background-color: #F8FAFC;
                margin: 0;
                padding: 24px;
                font-size: 13px;
                line-height: 1.5;
            }
            .report-container {
                max-width: 850px;
                margin: 0 auto;
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 30px;
            }
            .report-header {
                border-bottom: 2px solid #0F172A;
                padding-bottom: 16px;
                margin-bottom: 24px;
            }
            .report-title-block h1 {
                font-family: 'Times New Roman', Georgia, serif;
                font-size: 26px;
                font-weight: bold;
                color: #0F172A;
                margin: 0;
            }
            .report-subtitle {
                font-size: 12px;
                color: #2563EB;
                margin-top: 4px;
                margin-bottom: 0;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-weight: 700;
            }
            .auditor-badge {
                display: inline-block;
                background-color: #0037b0;
                color: #FFFFFF;
                font-size: 10px;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 15px;
                text-transform: uppercase;
                margin-top: 8px;
            }
            .card {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px 14px;
                background: #F8FAFC;
            }
            .card-metric { border-top: 4px solid #0037b0; }
            .card-success { border-top: 4px solid #059669; }
            .card-danger { border-top: 4px solid #DC2626; }
            .card-warning { border-top: 4px solid #D97706; }
            
            .card-label {
                font-size: 10px;
                font-weight: 700;
                color: #64748B;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }
            .card-value {
                font-family: 'Times New Roman', Georgia, serif;
                font-size: 20px;
                font-weight: bold;
                color: #0F172A;
            }
            .section-title {
                font-family: 'Times New Roman', Georgia, serif;
                font-size: 16px;
                font-weight: bold;
                color: #0F172A;
                border-left: 4px solid #0037b0;
                padding-left: 8px;
                margin-top: 24px;
                margin-bottom: 12px;
            }
            .data-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 16px;
                font-size: 12px;
            }
            .data-table th {
                background-color: #F8FAFC;
                color: #475569;
                font-weight: 700;
                border-bottom: 2px solid #E2E8F0;
                padding: 8px 10px;
                text-align: left;
            }
            .data-table td {
                padding: 8px 10px;
                border-bottom: 1px solid #E2E8F0;
                color: #334155;
            }
            .data-table tr:nth-child(even) {
                background-color: #F8FAFC;
            }
            .badge {
                display: inline-block;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 700;
                border-radius: 4px;
                text-transform: uppercase;
            }
            .badge-high { background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; }
            .badge-medium { background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }
            .badge-low { background-color: #D1FAE5; color: #065F46; border: 1px solid #6EE7B7; }
            
            .recommendation-box {
                background-color: #EFF6FF;
                border-left: 4px solid #2563EB;
                padding: 12px 14px;
                border-radius: 0 6px 6px 0;
                margin-bottom: 14px;
                color: #1E3A8A;
            }
            .recommendation-title {
                font-weight: 700;
                font-size: 12px;
                margin-bottom: 4px;
            }
            .progress-bar-container {
                background-color: #E2E8F0;
                border-radius: 4px;
                height: 6px;
                width: 100%;
                margin-top: 4px;
                overflow: hidden;
            }
            .progress-bar-fill {
                height: 100%;
                background-color: #0037b0;
                border-radius: 4px;
            }
            .progress-bar-fill-success { background-color: #059669; }
            .progress-bar-fill-warning { background-color: #D97706; }
            .progress-bar-fill-danger { background-color: #DC2626; }
        </style>
        """

    @classmethod
    def generate_financial_summary(cls, transactions, bank_name, statement_period, currency="INR") -> str:
        """Provides high-level audit summary metrics and indicators with local fallback."""
        try:
            tx_text = cls._format_transactions(transactions, currency)
            prompt = f"""
You are a senior Deloitte forensic auditor.
Analyze the following parsed bank statement details and provide a professional, premium, executive-level **Financial Summary Report**.

Statement Info:
- Bank: {bank_name}
- Period: {statement_period}
- Currency: {currency}

Transaction Records:
{tx_text}

Requirements:
1. Return a **completely self-contained HTML document** (starting with `<html>` and ending with `</html>`).
2. Do NOT use markdown formatting outside the HTML or wrap the HTML in backticks (like ```html). Return the raw HTML string directly.
3. Apply standard Deloitte-style corporate formatting. Include:
   - **Executive Header**: Styled logo/banner, auditor badge ('AI Financial Summary'), and statement metadata card.
   - **KPI Cards Section**: Lay this out using an HTML `<table>` with borders hidden (to guarantee rendering in PyQt's QTextBrowser). Include:
     - Total Inflows (Credits)
     - Total Outflows (Debits)
     - Net Savings / Cash Flow (with positive growth or warning indicator)
     - Financial Health Score (e.g. 90/100)
   - **Statement Overview table**: detailed stats (opening/closing balance, averages, largest transactions, transaction counts).
   - **Top 3 Strategic Insights**: analytical observations on cash flows, major inflow/outflow sources.
   - **Auditor Recommendations**: actionable guidance.

Use the following CSS style block at the top:
{cls._get_report_styles()}
"""
            return cls._call_gemini(prompt, system_instruction="You are a senior financial advisor and auditor.")
        except Exception as e:
            print(f"GeminiService: API call failed for generate_financial_summary. Using local fallback. Error: {e}")
            return cls._generate_local_financial_summary(transactions, bank_name, statement_period, currency)

    @classmethod
    def _generate_local_financial_summary(cls, transactions, bank_name, statement_period, currency="INR") -> str:
        """Fallback local calculation for financial summary."""
        total_credit = 0.0
        total_debit = 0.0
        max_debit = 0.0
        max_debit_desc = "N/A"
        max_credit = 0.0
        max_credit_desc = "N/A"
        balances = []
        
        for tx in transactions:
            try:
                d = float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                c = float(str(tx.get("credit") or 0.0).replace(",", "").strip())
                total_debit += d
                total_credit += c
                if d > max_debit:
                    max_debit = d
                    max_debit_desc = tx.get("narration", "Debit transaction")
                if c > max_credit:
                    max_credit = c
                    max_credit_desc = tx.get("narration", "Credit transaction")
                
                bal = tx.get("balance")
                if bal is not None:
                    try:
                        balances.append(float(str(bal).replace(",", "").replace("₹", "").strip()))
                    except:
                        pass
            except:
                pass
                
        net_savings = total_credit - total_debit
        savings_rate = (net_savings / total_credit * 100) if total_credit > 0 else 0.0
        avg_balance = sum(balances) / len(balances) if balances else 0.0
        
        debits_list = [float(str(tx.get("debit") or 0.0).replace(",", "").strip()) for tx in transactions if float(str(tx.get("debit") or 0.0).replace(",", "").strip()) > 0]
        credits_list = [float(str(tx.get("credit") or 0.0).replace(",", "").strip()) for tx in transactions if float(str(tx.get("credit") or 0.0).replace(",", "").strip()) > 0]
        avg_debit = sum(debits_list) / len(debits_list) if debits_list else 0.0
        avg_credit = sum(credits_list) / len(credits_list) if credits_list else 0.0
        tx_count = len(transactions)
        
        # Calculate financial health score
        score = 80
        if total_credit > 0:
            ratio = total_debit / total_credit
            if ratio > 1.0:
                score -= min(30, int((ratio - 1.0) * 50))
            else:
                score += min(20, int(savings_rate * 0.4))
        else:
            score = 50
        score = max(10, min(100, score))
        
        symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)
        
        # Insights
        insight_1 = f"Primary Outflow: The largest single debit is <strong>{symbol} {max_debit:,.2f}</strong> for <em>'{max_debit_desc}'</em>." if max_debit > 0 else "No debit outflows recorded."
        insight_2 = f"Primary Inflow: The largest single credit is <strong>{symbol} {max_credit:,.2f}</strong> for <em>'{max_credit_desc}'</em>." if max_credit > 0 else "No credit inflows recorded."
        if net_savings >= 0:
            insight_3 = f"Cash Flow Trend: The statement shows a positive net cash flow of <strong>{symbol} {net_savings:,.2f}</strong> indicating a stable account posture."
        else:
            insight_3 = f"Cash Flow Trend: Warning - Outflows exceed inflows by <strong>{symbol} {abs(net_savings):,.2f}</strong>, which may deplete reserves over time."

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {cls._get_report_styles()}
        </head>
        <body>
            <div class="report-container">
                <div class="report-header">
                    <div class="report-title-block">
                        <h1>Financial Summary &amp; Analysis</h1>
                        <p class="report-subtitle">{bank_name} • Statement Audit summary</p>
                    </div>
                    <div class="auditor-badge">StatementForge AI Fallback Auditor</div>
                </div>
                
                <div class="recommendation-box">
                    <div class="recommendation-title">💡 Rule-Based Summary Notice</div>
                    Currently using the offline rule-based parser engine due to AI service connection status.
                </div>

                <h2 class="section-title">Executive Summary</h2>
                <p>
                    The financial statement for the period of <strong>{statement_period}</strong> has been audited. 
                    Based on local analysis, the account has a savings rate of <strong>{savings_rate:.1f}%</strong>. 
                    {"Cash flow is positive and indicates healthy reserve margins." if net_savings >= 0 else "Negative net cash flow requires immediate attention to avoid liquidity exhaustion."}
                </p>

                <h2 class="section-title">Core Metrics</h2>
                <table style="width: 100%; border-collapse: collapse; border: none; margin-bottom: 20px;">
                    <tr>
                        <td style="width: 25%; padding: 6px; border: none;">
                            <div class="card card-metric">
                                <div class="card-label">Total Credits</div>
                                <div class="card-value" style="color: #059669;">{symbol} {total_credit:,.2f}</div>
                            </div>
                        </td>
                        <td style="width: 25%; padding: 6px; border: none;">
                            <div class="card card-metric">
                                <div class="card-label">Total Debits</div>
                                <div class="card-value" style="color: #DC2626;">{symbol} {total_debit:,.2f}</div>
                            </div>
                        </td>
                        <td style="width: 25%; padding: 6px; border: none;">
                            <div class="card card-metric">
                                <div class="card-label">Net Savings</div>
                                <div class="card-value" style="color: {'#059669' if net_savings >= 0 else '#DC2626'};">{symbol} {net_savings:,.2f}</div>
                            </div>
                        </td>
                        <td style="width: 25%; padding: 6px; border: none;">
                            <div class="card card-success" style="background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1D4ED8, stop:1 #7C3AED);">
                                <div class="card-label" style="color: rgba(255,255,255,0.8);">Health Score</div>
                                <div class="card-value" style="color: white;">{score}/100</div>
                            </div>
                        </td>
                    </tr>
                </table>

                <h2 class="section-title">Statement Details</h2>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>Value</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><strong>Total Inflows (Credits)</strong></td><td style="color:#059669; font-weight:700;">{symbol} {total_credit:,.2f}</td><td>Aggregate deposits and credits.</td></tr>
                        <tr><td><strong>Total Outflows (Debits)</strong></td><td style="color:#EF4444; font-weight:700;">{symbol} {total_debit:,.2f}</td><td>Aggregate expenditures, transfers, and cash debits.</td></tr>
                        <tr><td><strong>Average Running Balance</strong></td><td>{symbol} {avg_balance:,.2f}</td><td>Mean account balance over the period.</td></tr>
                        <tr><td><strong>Average Credit / Debit</strong></td><td>Inflow: {symbol}{avg_credit:,.2f} / Outflow: {symbol}{avg_debit:,.2f}</td><td>Mean transaction sizes.</td></tr>
                        <tr><td><strong>Total Transaction Count</strong></td><td>{tx_count}</td><td>Number of records logged.</td></tr>
                    </tbody>
                </table>

                <h2 class="section-title">Key Insights</h2>
                <ul>
                    <li style="margin-bottom: 8px;"><strong>Inflow Profile:</strong> {insight_2}</li>
                    <li style="margin-bottom: 8px;"><strong>Outflow Profile:</strong> {insight_1}</li>
                    <li style="margin-bottom: 8px;"><strong>Cash Flow Trend:</strong> {insight_3}</li>
                </ul>

                <h2 class="section-title">Actionable Recommendations</h2>
                <div class="recommendation-box">
                    <div class="recommendation-title">1. Spending Moderation</div>
                    Review discretionary expenses (e.g. food delivery, shopping) to increase the net savings rate.
                </div>
                <div class="recommendation-box">
                    <div class="recommendation-title">2. Reserve Cushion</div>
                    Build or maintain an emergency cash buffer equal to at least 3-6 months of average expenses ({symbol} {total_debit:,.2f} total).
                </div>
            </div>
        </body>
        </html>
        """
        return html.strip()

    @classmethod
    def analyze_monthly_spending(cls, transactions, currency="INR", **kwargs) -> str:
        """Performs structured category-wise spending analysis and recommendations with local fallback."""
        bank_name = kwargs.get("bank_name", "Unknown Bank")
        statement_period = kwargs.get("period", "Unknown Period")
        try:
            tx_text = cls._format_transactions(transactions, currency)
            prompt = f"""
You are a senior EY budget optimization consultant.
Analyze the spending (debits) in the following transactions and generate a premium, executive-level **Spending Insights & Category Analysis Report**.

Statement Info:
- Bank: {bank_name}
- Period: {statement_period}
- Currency: {currency}

Transactions:
{tx_text}

Requirements:
1. Return a **completely self-contained HTML document** (starting with `<html>` and ending with `</html>`).
2. Do NOT use markdown formatting outside the HTML or wrap the HTML in backticks.
3. Include:
   - **EY-style Header**: Title, auditor badge ('AI Spending Insights'), metadata block.
   - **Spending by Category Table**: Group expenses (Shopping, Food & Dining, Travel, Utilities, Subscriptions, Rent, Cash/ATM, Business, Miscellaneous) showing Category, Amount, Percentage, and a visual horizontal progress bar inline.
   - **Essential vs Discretionary Analysis**: Split ratio card/table.
   - **Top Outflows Analysis**: Visual callout card highlighting the 3 largest single expenditure rows.
   - **Special Audits**: UPI spending overview, ATM cash withdrawal velocity, merchant analysis.
   - **Executive Recommendations**: Actionable suggestions.

Use the following CSS style block:
{cls._get_report_styles()}
"""
            return cls._call_gemini(prompt, system_instruction="You are a budget optimization consultant.")
        except Exception as e:
            print(f"GeminiService: API call failed for analyze_monthly_spending. Using local fallback. Error: {e}")
            return cls._generate_local_spending_insights(transactions, bank_name, statement_period, currency)

    @classmethod
    def _generate_local_spending_insights(cls, transactions, bank_name, statement_period, currency="INR") -> str:
        """Fallback local calculation for spending insights."""
        categories = {
            "Shopping": 0.0,
            "Food & Dining": 0.0,
            "Travel & Transport": 0.0,
            "Subscriptions": 0.0,
            "Rent": 0.0,
            "Cash Withdrawals": 0.0,
            "Utilities & Bills": 0.0,
            "Business": 0.0,
            "Miscellaneous": 0.0
        }
        
        total_spend = 0.0
        outflows = []
        upi_spend = 0.0
        atm_spend = 0.0
        
        for tx in transactions:
            try:
                d = float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                if d <= 0:
                    continue
                total_spend += d
                outflows.append((d, tx.get("date", "N/A"), tx.get("narration", "Debit")))
                
                narr = str(tx.get("narration", "")).lower()
                if "upi" in narr or "imps" in narr:
                    upi_spend += d
                if "atm" in narr or "cash" in narr:
                    atm_spend += d
                    
                # Categorize
                if any(kw in narr for kw in ["netflix", "spotify", "aws", "google", "microsoft", "adobe", "cloud", "saas", "github", "zoom"]):
                    categories["Subscriptions"] += d
                elif any(kw in narr for kw in ["rent", "lease", "owner", "broker"]):
                    categories["Rent"] += d
                elif any(kw in narr for kw in ["atm", "cash", "withd"]):
                    categories["Cash Withdrawals"] += d
                elif any(kw in narr for kw in ["swiggy", "zomato", "restaurant", "cafe", "hotel", "food", "dining", "eats", "grocery"]):
                    categories["Food & Dining"] += d
                elif any(kw in narr for kw in ["uber", "ola", "travel", "irctc", "rail", "metro", "cab", "flight", "airline", "fuel", "petrol"]):
                    categories["Travel & Transport"] += d
                elif any(kw in narr for kw in ["amazon", "flipkart", "myntra", "store", "shop", "mall", "market", "paytm", "retail"]):
                    categories["Shopping"] += d
                elif any(kw in narr for kw in ["electricity", "water", "recharge", "bill", "broadband", "jio", "airtel", "bsnl"]):
                    categories["Utilities & Bills"] += d
                elif any(kw in narr for kw in ["salary", "payout", "business", "invoice", "vendor", "office"]):
                    categories["Business"] += d
                else:
                    categories["Miscellaneous"] += d
            except:
                pass
                
        # Sort outflows
        outflows.sort(key=lambda x: x[0], reverse=True)
        top_3 = outflows[:3]
        
        # Calculate ratios
        discretionary = categories["Shopping"] + categories["Food & Dining"] + categories["Subscriptions"]
        essential = categories["Rent"] + categories["Utilities & Bills"] + categories["Travel & Transport"] + categories["Business"]
        
        disc_pct = (discretionary / total_spend * 100) if total_spend > 0 else 0.0
        ess_pct = (essential / total_spend * 100) if total_spend > 0 else 0.0
        misc_pct = 100.0 - disc_pct - ess_pct
        
        symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)
        
        # Build category table rows with horizontal progress bars
        cat_rows_html = ""
        bar_colors = ["#0037b0", "#059669", "#D97706", "#DC2626", "#6366F1", "#EC4899", "#8B5CF6", "#14B8A6", "#64748B"]
        for idx, (cat, amt) in enumerate(categories.items()):
            pct = (amt / total_spend * 100) if total_spend > 0 else 0.0
            color = bar_colors[idx % len(bar_colors)]
            cat_rows_html += f"""
            <tr>
                <td><strong>{cat}</strong></td>
                <td>{symbol} {amt:,.2f}</td>
                <td>{pct:.1f}%</td>
                <td style="width: 30%;">
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" style="width: {pct}%; background-color: {color};"></div>
                    </div>
                </td>
            </tr>
            """
            
        # Top 3 details
        top_rows_html = ""
        for idx, (amt, date, desc) in enumerate(top_3):
            top_rows_html += f"""
            <div class="recommendation-box" style="background-color: #FEF2F2; border-left-color: #EF4444; color: #991B1B;">
                <div class="recommendation-title">#{idx+1} Outflow: {symbol} {amt:,.2f}</div>
                Logged on <strong>{date}</strong> - Description: <em>'{desc}'</em>
            </div>
            """
        if not top_rows_html:
            top_rows_html = "<p>No outflows recorded.</p>"
            
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {cls._get_report_styles()}
        </head>
        <body>
            <div class="report-container">
                <div class="report-header">
                    <div class="report-title-block">
                        <h1>Spending Insights &amp; Budget Optimization</h1>
                        <p class="report-subtitle">{bank_name} • Category Audit</p>
                    </div>
                    <div class="auditor-badge" style="background-color: #EA580C;">Spending Report</div>
                </div>
                
                <div class="recommendation-box" style="background-color: #FFFBEB; border-left-color: #D97706; color: #92400E;">
                    <div class="recommendation-title">💡 Rule-Based spending Insights Notice</div>
                    Currently using the offline rule-based parser engine due to AI service connection status.
                </div>

                <h2 class="section-title">Spending Category Allocation</h2>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Expense Category</th>
                            <th>Total Amount</th>
                            <th>Allocation (%)</th>
                            <th>Distribution Chart</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cat_rows_html}
                        <tr style="background-color: #F1F5F9; font-weight: bold;">
                            <td>Total Audited Debits</td>
                            <td>{symbol} {total_spend:,.2f}</td>
                            <td>100.0%</td>
                            <td></td>
                        </tr>
                    </tbody>
                </table>

                <h2 class="section-title">Essential vs Discretionary Ratio</h2>
                <table style="width: 100%; border-collapse: collapse; border: none; margin-bottom: 20px;">
                    <tr>
                        <td style="width: 50%; padding: 6px; border: none;">
                            <div class="card card-metric">
                                <div class="card-label">Essential Needs Ratio</div>
                                <div class="card-value" style="color: #0037b0;">{ess_pct:.1f}%</div>
                                <p style="font-size: 11px; color:#64748B; margin: 4px 0 0 0;">Rent, Utilities, Transport, Business</p>
                            </div>
                        </td>
                        <td style="width: 50%; padding: 6px; border: none;">
                            <div class="card card-warning">
                                <div class="card-label">Discretionary Choice Ratio</div>
                                <div class="card-value" style="color: #D97706;">{disc_pct:.1f}%</div>
                                <p style="font-size: 11px; color:#64748B; margin: 4px 0 0 0;">Shopping, Dining Out, Subscriptions</p>
                            </div>
                        </td>
                    </tr>
                </table>

                <h2 class="section-title">Top 3 Largest Single Expenditures</h2>
                {top_rows_html}

                <h2 class="section-title">Channel &amp; Merchant Analysis</h2>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Channel Category</th>
                            <th>Audited Outlay</th>
                            <th>Percentage of Expenditure (%)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><strong>UPI &amp; Digital Transfers</strong></td><td>{symbol} {upi_spend:,.2f}</td><td>{((upi_spend / total_spend * 100) if total_spend > 0 else 0):.1f}%</td></tr>
                        <tr><td><strong>ATM &amp; Cash Withdrawals</strong></td><td>{symbol} {atm_spend:,.2f}</td><td>{((atm_spend / total_spend * 100) if total_spend > 0 else 0):.1f}%</td></tr>
                    </tbody>
                </table>

                <h2 class="section-title">Executive Budget recommendations</h2>
                <div class="recommendation-box">
                    <div class="recommendation-title">1. Discretionary Spending Capping</div>
                    Your discretionary choices represent <strong>{disc_pct:.1f}%</strong> of total expenditures. Aim to cap lifestyle shopping and dining at 20% to free up savings.
                </div>
                <div class="recommendation-box">
                    <div class="recommendation-title">2. UPI Spend Auditing</div>
                    UPI transfers account for <strong>{((upi_spend / total_spend * 100) if total_spend > 0 else 0):.1f}%</strong> of spending. Digital micro-transactions accumulate rapidly; implement weekly transaction tracking.
                </div>
            </div>
        </body>
        </html>
        """
        return html.strip()

    @classmethod
    def analyze_income_vs_expense(cls, transactions, currency="INR") -> str:
        """Compares overall income inflows against expense outflows."""
        tx_text = cls._format_transactions(transactions, currency)
        prompt = f"""
Compare the cash inflows (credits) against cash outflows (debits) for these transactions:
{tx_text}

Requirements:
1. **Inflow vs Outflow Table**: Present a summary table showing Total Inflow (Credits) vs Total Outflow (Debits).
2. **Net Savings Trend**: Report the exact Net Cash Flow (Inflow minus Outflow). If negative, flag it with warning indicators.
3. **Cash Flow Quality**: Evaluate the frequency and stability of inflows (e.g., steady salary vs irregular deposits) versus the velocity of outflows.
4. **Sustainability Analysis**: State whether this current pattern is sustainable for long-term financial health.

Format in clean GitHub-flavored Markdown.
"""
        return cls._call_gemini(prompt, system_instruction="You are a cash-flow analyst.")

    @classmethod
    def categorize_expenses(cls, transactions, currency="INR") -> str:
        """Labels all transactions and provides business vs personal separation recommendations."""
        tx_text = cls._format_transactions(transactions, currency)
        prompt = f"""
Analyze the transactions below:
{tx_text}

Requirements:
1. Group every debit transaction into one of these buckets: [Food, Utilities, Travel, Shopping, Fuel, Rent, Subscriptions, Business, Personal, Unknown].
2. Identify which expenses appear to be **Business Expenses** (e.g., Cloud bills, office rent, internet bills, SaaS subscriptions like Google Cloud, AWS, Adobe, Microsoft 365, etc.) vs **Personal Expenses** (e.g., dining out, Netflix, personal clothing). Write a detailed log of identified business transactions.
3. Suggest which expenses could be claimed as business tax deductions.

Provide a clear, structured Markdown report.
"""
        return cls._call_gemini(prompt, system_instruction="You are an corporate tax advisor and accountant.")

    @classmethod
    def analyze_cash_flow(cls, transactions, currency="INR") -> str:
        """Inspects velocity and consistency of running balances."""
        tx_text = cls._format_transactions(transactions, currency)
        prompt = f"""
Analyze the cash flow velocity and balance consistency of the account based on:
{tx_text}

Requirements:
1. Evaluate how the running balance changes over the period (growth percentage from opening to closing).
2. Identify periods of 'cash crunch' (when balance drops to its lowest) and peak balance days.
3. Assess the liquidity profile and provide a cash runway projection (how many months the average balance would last if inflows stopped).

Write a professional financial analysis in Markdown.
"""
        return cls._call_gemini(prompt, system_instruction="You are a corporate liquidity and treasury manager.")

    @classmethod
    def detect_unusual_transactions(cls, transactions, currency="INR") -> str:
        """Flags large amounts, off-hours activity, and potential duplicate transaction anomalies."""
        tx_text = cls._format_transactions(transactions, currency)
        prompt = f"""
Audit these transactions for risk, unusual patterns, or potential errors:
{tx_text}

Requirements:
1. **Unusual Off-Hours or Large Withdrawals**: Flag withdrawals of unusually large amounts or transactions made at odd hours (e.g., late night transfers).
2. **Refund Errors**: Scan for transactions where a refund or credit narration appears but was processed as a debit, or vice versa.
3. **Hidden Subscription Burdens**: Group and list all recurring software, streaming, or membership subscriptions (e.g. Netflix, Amazon Prime, Google Workspace, AWS, Spotify). Indicate monthly/annual billing estimation and highlight potential savings.
4. **General Financial Risk Profile**: Assess overall transaction risk (Low, Medium, High).

Format in Markdown. Be direct and list items clearly with warning/risk emojis where appropriate.
"""
        return cls._call_gemini(prompt, system_instruction="You are a forensic fraud investigator and financial auditor.")

    @classmethod
    def get_savings_suggestions(cls, transactions, currency="INR") -> str:
        """Finds direct leakages and suggests smart household or business budget hacks."""
        tx_text = cls._format_transactions(transactions, currency)
        prompt = f"""
Suggest savings strategies based on:
{tx_text}

Identify specific spend categories that show waste or leakage (e.g. high dining frequency, overlapping subscriptions).
Provide 5 hyper-specific, actionable recommendations to improve savings this month (e.g. 'Cut dining spend by 10% to save {currency} 2,000').

Format in Markdown.
"""
        return cls._call_gemini(prompt, system_instruction="You are a personal finance wealth advisor.")

    @classmethod
    def get_investment_suggestions(cls, transactions, currency="INR") -> str:
        """Recommends asset allocation based on net cash margins."""
        tx_text = cls._format_transactions(transactions, currency)
        prompt = f"""
Recommend customized investment assets based on this cash statement:
{tx_text}

1. Calculate available net monthly investable surplus.
2. Provide a suggested investment allocation split (e.g. 50% Mutual Funds / Equities, 30% Fixed Deposits/Low-risk, 20% Liquid Emergency Fund).
3. Recommend specific financial instruments suited to this surplus profile (Fds, Recurring Deposits, Index Funds, ETFs). Include risk-return explanations.

Format in Markdown.
"""
        return cls._call_gemini(prompt, system_instruction="You are a certified financial planner and investment advisor.")

    @classmethod
    def analyze_risks(cls, transactions, currency="INR", **kwargs) -> str:
        """Synthesizes duplicates, subscription burdens, and balance checks into a risk report with local fallback."""
        bank_name = kwargs.get("bank_name", "Unknown Bank")
        statement_period = kwargs.get("period", "Unknown Period")
        try:
            tx_text = cls._format_transactions(transactions, currency)
            prompt = f"""
You are a senior forensic auditor at a Big-4 accounting firm (PwC/EY).
Audit the statement transactions for risk detection and generate a premium, executive-level **Forensic Audit & Risk Analysis Report** in HTML.

Statement Details:
- Bank: {bank_name}
- Period: {statement_period}
- Currency: {currency}

Transactions:
{tx_text}

Requirements:
1. Return a **completely self-contained HTML document** (starting with `<html>` and ending with `</html>`).
2. Do NOT wrap the HTML in backticks or markdown formatting.
3. Include:
   - **Auditor Header**: Title, badge ('Forensic Risk Analysis'), metadata block.
   - **Executive Risk Score Card**: Display a colored score badge (e.g. Risk Level: Medium, score: 35/100).
   - **Identified Risk Factors Table/List**: Check and list indicators with severity badges (High/Medium/Low), explanations, and recommendations:
     - Subscription Burdens & Recurring Outflows
     - Duplicate payment checks (double entry anomalies)
     - Suspicious amount detection (round figures, rapid consecutive transfers)
     - Large transaction warnings (above threshold)
     - Running balance integrity & low liquidity checks
     - Unusual transaction timing
   - **AML / compliance notes** and money flow analysis.
   - **Final Audit Opinion** and advisory action steps.

Use the following CSS style block:
{cls._get_report_styles()}
"""
            return cls._call_gemini(prompt, system_instruction="You are a risk management consultant.")
        except Exception as e:
            print(f"GeminiService: API call failed for analyze_risks. Using local fallback. Error: {e}")
            return cls._generate_local_risk_analysis(transactions, bank_name, statement_period, currency)

    @classmethod
    def _generate_local_risk_analysis(cls, transactions, bank_name, statement_period, currency="INR") -> str:
        """Fallback local calculation for risk assessment."""
        subscriptions = []
        duplicates = {}
        balance_drops = []
        large_withdrawals = []
        round_figures = []
        rapid_transfers = {}
        unusual_timing = []
        
        for idx, tx in enumerate(transactions):
            try:
                d = float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                c = float(str(tx.get("credit") or 0.0).replace(",", "").strip())
                date = tx.get("date", "N/A")
                narr = tx.get("narration", "")
                bal = tx.get("balance")
                
                # Check large withdrawal (>=50,000)
                if d >= 50000:
                    large_withdrawals.append((d, date, narr))
                    
                # Track duplicates
                if d > 0:
                    dup_key = (date, d)
                    duplicates.setdefault(dup_key, []).append(narr)
                    
                    # Track round figures
                    if d >= 5000 and d % 1000 == 0:
                        round_figures.append((d, date, narr))
                    
                    # Track rapid consecutive transfers (group by date)
                    rapid_transfers.setdefault(date, []).append(d)
                    
                # Check subscriptions
                narr_lower = narr.lower()
                if d > 0 and any(kw in narr_lower for kw in ["netflix", "spotify", "aws", "google", "microsoft", "adobe", "cloud", "saas", "github", "zoom"]):
                    subscriptions.append((d, date, narr))
                    
                # Check low balance
                if bal is not None:
                    try:
                        b_val = float(str(bal).replace(",", "").replace("₹", "").strip())
                        if b_val < 5000:
                            balance_drops.append((b_val, date))
                    except:
                        pass
            except:
                pass
                
        # Group duplicates
        dup_alerts_html = ""
        dup_count = 0
        for (date, amt), narr_list in duplicates.items():
            if len(narr_list) > 1:
                dup_count += 1
                dup_alerts_html += f"<li><strong>{currency} {amt:,.2f}</strong> on <em>{date}</em> (Narrations: " + " &amp; ".join([f"'{n}'" for n in narr_list]) + ")</li>"
        if not dup_alerts_html:
            dup_alerts_html = "<li>No duplicate transaction anomalies detected.</li>"
            
        # Group large transactions
        large_html = ""
        for amt, date, desc in large_withdrawals:
            large_html += f"<li><strong>{currency} {amt:,.2f}</strong> on <em>{date}</em> (Merchant: <em>'{desc}'</em>)</li>"
        if not large_html:
            large_html = "<li>No large outflows detected.</li>"
            
        # Group subscriptions
        sub_html = ""
        annual_est = 0.0
        for amt, date, desc in subscriptions:
            sub_html += f"<li><strong>{currency} {amt:,.2f}</strong> on <em>{date}</em> - Recurring <em>'{desc}'</em></li>"
            annual_est += amt * 12
        if not sub_html:
            sub_html = "<li>No active subscription items identified.</li>"
            
        # Group round figures
        round_html = ""
        for amt, date, desc in round_figures[:5]:
            round_html += f"<li><strong>{currency} {amt:,.2f}</strong> on <em>{date}</em> - <em>'{desc}'</em></li>"
        if not round_html:
            round_html = "<li>No round figure transfers detected.</li>"
            
        # Group rapid transfers
        rapid_count = sum(1 for d, txs in rapid_transfers.items() if len(txs) >= 3)
        
        # Risk score calculation
        risk_score_num = 15
        risk_score_num += len(large_withdrawals) * 10
        risk_score_num += dup_count * 15
        risk_score_num += (15 if balance_drops else 0)
        risk_score_num += rapid_count * 10
        risk_score_num = min(99, risk_score_num)
        
        if risk_score_num > 60:
            risk_badge = '<span class="badge badge-high">High Risk</span>'
            badge_class = "card-danger"
            val_color = "#DC2626"
        elif risk_score_num > 30:
            risk_badge = '<span class="badge badge-medium">Medium Risk</span>'
            badge_class = "card-warning"
            val_color = "#D97706"
        else:
            risk_badge = '<span class="badge badge-low">Low Risk</span>'
            badge_class = "card-success"
            val_color = "#059669"
            
        symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {cls._get_report_styles()}
        </head>
        <body>
            <div class="report-container">
                <div class="report-header">
                    <div class="report-title-block">
                        <h1>Forensic Audit &amp; Risk Analysis</h1>
                        <p class="report-subtitle">{bank_name} • Risk Profile Summary</p>
                    </div>
                    <div class="auditor-badge" style="background-color: #DC2626;">Forensic Audit</div>
                </div>
                
                <div class="recommendation-box" style="background-color: #FEF2F2; border-left-color: #EF4444; color: #991B1B;">
                    <div class="recommendation-title">⚠️ Rule-Based forensic Analysis Notice</div>
                    Currently using the offline rule-based parser engine due to AI service connection status.
                </div>

                <h2 class="section-title">Risk Assessment Dashboard</h2>
                <table style="width: 100%; border-collapse: collapse; border: none; margin-bottom: 20px;">
                    <tr>
                        <td style="width: 50%; padding: 6px; border: none;">
                            <div class="card {badge_class}">
                                <div class="card-label">Forensic Risk Score</div>
                                <div class="card-value" style="color: {val_color};">{risk_score_num} / 100</div>
                                <p style="font-size: 11px; color:#64748B; margin: 4px 0 0 0;">Overall Risk Assessment: {risk_badge}</p>
                            </div>
                        </td>
                        <td style="width: 50%; padding: 6px; border: none;">
                            <div class="card card-metric">
                                <div class="card-label">Annualized Subscription Leakage</div>
                                <div class="card-value">{symbol} {annual_est:,.2f}</div>
                                <p style="font-size: 11px; color:#64748B; margin: 4px 0 0 0;">Estimated recurring SaaS / media expense</p>
                            </div>
                        </td>
                    </tr>
                </table>

                <h2 class="section-title">Forensic Audit Logs</h2>
                
                <div class="card" style="margin-bottom: 12px;">
                    <div class="card-label" style="color:#B91C1C;">1. Subscription Burdens &amp; Leakages</div>
                    <ul style="margin: 6px 0 0 0; padding-left: 20px;">
                        {sub_html}
                    </ul>
                </div>
                
                <div class="card" style="margin-bottom: 12px;">
                    <div class="card-label" style="color:#B91C1C;">2. Duplicate Payment / Double Charges</div>
                    <ul style="margin: 6px 0 0 0; padding-left: 20px;">
                        {dup_alerts_html}
                    </ul>
                </div>
                
                <div class="card" style="margin-bottom: 12px;">
                    <div class="card-label" style="color:#B91C1C;">3. High-Value Transfers (>= 50,000)</div>
                    <ul style="margin: 6px 0 0 0; padding-left: 20px;">
                        {large_html}
                    </ul>
                </div>
                
                <div class="card" style="margin-bottom: 12px;">
                    <div class="card-label" style="color:#B91C1C;">4. Round-Figure Outflow Detection</div>
                    <ul style="margin: 6px 0 0 0; padding-left: 20px;">
                        {round_html}
                    </ul>
                </div>

                <h2 class="section-title">Risk Mitigation &amp; Auditor Opinion</h2>
                <div class="recommendation-box">
                    <div class="recommendation-title">Advisory Recommendation (Duplicates)</div>
                    If duplicate payment alerts are listed, check with the card processor or bank immediately to dispute possible double transactions.
                </div>
                <div class="recommendation-box">
                    <div class="recommendation-title">Advisory Recommendation (Subscriptions)</div>
                    Cancel unused recurring charges to reclaim <strong>{symbol} {annual_est:,.2f}</strong> in annual runway.
                </div>
            </div>
        </body>
        </html>
        """
        return html.strip()

    @classmethod
    def generate_executive_report(cls, transactions, bank_name, account_holder, account_number, statement_period, currency="INR") -> str:
        """Generates a complete, beautiful HTML financial auditing report resembling Deloitte or PwC outputs with local fallback."""
        try:
            tx_text = cls._format_transactions(transactions, currency)
            total_debit = 0.0
            total_credit = 0.0
            for tx in transactions:
                try:
                    total_debit += float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                    total_credit += float(str(tx.get("credit") or 0.0).replace(",", "").strip())
                except:
                    pass
            net_savings = total_credit - total_debit
            savings_ratio = (net_savings / total_credit * 100) if total_credit > 0 else 0
            
            prompt = f"""
You are a senior Principal Auditor at a Big-4 accounting firm (Deloitte/PwC style).
Generate a professional, premium, executive-level **AI Financial Audit & Advisor Report** in HTML format.

Details:
- Account Holder: {account_holder}
- Account Number: {account_number}
- Bank Name: {bank_name}
- Statement Period: {statement_period}
- Currency: {currency}
- Total Credits: {currency} {total_credit:,.2f}
- Total Debits: {currency} {total_debit:,.2f}
- Net Savings: {currency} {net_savings:,.2f}
- Savings Ratio: {savings_ratio:.1f}%

Extracted Transactions:
{tx_text}

Requirements:
1. Return a **completely self-contained HTML document** (starting with `<html>` and ending with `</html>`).
2. Do NOT use markdown formatting outside the HTML or wrap the HTML in backticks.
3. Use a premium, corporate aesthetic color scheme.
4. Include:
   - **Executive Header**: Styled logo banner, auditor stamp ('StatementForge AI Auditor'), and metadata card.
   - **Financial Health Score Section**: Display a large, beautiful badge containing an AI calculated score.
   - **Spending Profile Section**: Category table and key findings.
   - **Risk & Fraud Audit Section**: Flag unusual transactions, potential duplicate payments, subscription leakages, and refund inconsistencies.
   - **Business Deductions & Recommendations**: Business vs Personal expense suggestions, plus 4 strategic advisor recommendations to improve cash reserves.
5. Apply professional CSS styling.

Use the following CSS style block:
{cls._get_report_styles()}
"""
            return cls._call_gemini(prompt, system_instruction="You are a Big-4 senior forensic auditor and wealth manager.")
        except Exception as e:
            print(f"GeminiService: API call failed for generate_executive_report. Using local fallback. Error: {e}")
            return cls._generate_local_executive_report(transactions, bank_name, account_holder, account_number, statement_period, currency)

    @classmethod
    def _generate_local_executive_report(cls, transactions, bank_name, account_holder, account_number, statement_period, currency="INR") -> str:
        """Fallback local calculation to generate Deloitte-style HTML report."""
        total_debit = 0.0
        total_credit = 0.0
        categories = {
            "Shopping": 0.0, "Food & Dining": 0.0, "Travel & Transport": 0.0,
            "Subscriptions": 0.0, "Rent": 0.0, "Cash Withdrawals": 0.0,
            "Utilities & Bills": 0.0, "Business": 0.0, "Miscellaneous": 0.0
        }
        subscriptions = []
        duplicates = {}
        large_withdrawals = []
        
        for tx in transactions:
            try:
                d = float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                c = float(str(tx.get("credit") or 0.0).replace(",", "").strip())
                date = tx.get("date", "N/A")
                narr = tx.get("narration", "")
                
                total_debit += d
                total_credit += c
                
                if d > 0:
                    if d >= 50000:
                        large_withdrawals.append((d, date, narr))
                        
                    # Track duplicates
                    dup_key = (date, d)
                    duplicates.setdefault(dup_key, []).append(narr)
                        
                    # Categorize
                    narr_lower = narr.lower()
                    if any(kw in narr_lower for kw in ["netflix", "spotify", "aws", "google", "microsoft", "adobe", "cloud", "saas", "github", "zoom"]):
                        categories["Subscriptions"] += d
                        subscriptions.append((d, date, narr))
                    elif any(kw in narr_lower for kw in ["rent", "lease", "owner", "broker"]):
                        categories["Rent"] += d
                    elif any(kw in narr_lower for kw in ["atm", "cash", "withd"]):
                        categories["Cash Withdrawals"] += d
                    elif any(kw in narr_lower for kw in ["swiggy", "zomato", "restaurant", "cafe", "hotel", "food", "dining", "eats", "grocery"]):
                        categories["Food & Dining"] += d
                    elif any(kw in narr_lower for kw in ["uber", "ola", "travel", "irctc", "rail", "metro", "cab", "flight", "airline", "fuel", "petrol"]):
                        categories["Travel & Transport"] += d
                    elif any(kw in narr_lower for kw in ["amazon", "flipkart", "myntra", "store", "shop", "mall", "market", "paytm", "retail"]):
                        categories["Shopping"] += d
                    elif any(kw in narr_lower for kw in ["electricity", "water", "recharge", "bill", "broadband", "jio", "airtel", "bsnl"]):
                        categories["Utilities & Bills"] += d
                    elif any(kw in narr_lower for kw in ["salary", "payout", "business", "invoice", "vendor", "office"]):
                        categories["Business"] += d
                    else:
                        categories["Miscellaneous"] += d
            except:
                pass
                
        net_savings = total_credit - total_debit
        score = 80 # simplified
        
        dup_alerts_html = "".join([f"<li><strong>{currency} {amt:,.2f}</strong> on <em>{date}</em> (Narrations: " + " &amp; ".join([f"'{n}'" for n in narr_list]) + ")</li>" for (date, amt), narr_list in duplicates.items() if len(narr_list) > 1])
        large_txs_html = "".join([f"<li><strong>{currency} {amt:,.2f}</strong> on <em>{date}</em> - <em>'{desc}'</em></li>" for amt, date, desc in large_withdrawals])
        sub_html = "".join([f"<li><strong>{currency} {amt:,.2f}</strong> recurring for <em>'{desc}'</em></li>" for amt, date, desc in subscriptions])
        annual_est = sum(amt * 12 for amt, d, desc in subscriptions)
            
        cat_rows_html = ""
        for cat, amt in categories.items():
            pct = (amt / total_debit * 100) if total_debit > 0 else 0.0
            cat_rows_html += f"<tr><td>{cat}</td><td>{currency} {amt:,.2f}</td><td>{pct:.1f}%</td></tr>"
            
        symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {cls._get_report_styles()}
        </head>
        <body>
            <div class="report-container">
                <div class="report-header">
                    <div class="report-title-block">
                        <h1>Executive Audit &amp; Business Report</h1>
                        <p class="report-subtitle">{bank_name} • Comprehensive Audit</p>
                    </div>
                    <div class="auditor-badge" style="background-color: #1E3A8A;">Big-4 Auditor Report</div>
                </div>
                
                <div class="recommendation-box" style="background-color: #FFFBEB; border-left-color: #D97706; color: #92400E;">
                    <div class="recommendation-title">💡 Rule-Based Report Notice</div>
                    Currently using the offline rule-based parser engine due to AI service connection status.
                </div>

                <h2 class="section-title">Statement Metadata</h2>
                <table class="data-table">
                    <tbody>
                        <tr><td><strong>Account Holder:</strong></td><td>{account_holder}</td></tr>
                        <tr><td><strong>Account Number:</strong></td><td>{account_number}</td></tr>
                        <tr><td><strong>Bank Name:</strong></td><td>{bank_name}</td></tr>
                        <tr><td><strong>Statement Period:</strong></td><td>{statement_period}</td></tr>
                    </tbody>
                </table>

                <h2 class="section-title">Financial Health &amp; Core Metrics</h2>
                <table style="width: 100%; border-collapse: collapse; border: none; margin-bottom: 20px;">
                    <tr>
                        <td style="width: 25%; padding: 6px; border: none;">
                            <div class="card card-metric">
                                <div class="card-label">Total Credits</div>
                                <div class="card-value" style="color: #059669;">{symbol} {total_credit:,.2f}</div>
                            </div>
                        </td>
                        <td style="width: 25%; padding: 6px; border: none;">
                            <div class="card card-metric">
                                <div class="card-label">Total Debits</div>
                                <div class="card-value" style="color: #DC2626;">{symbol} {total_debit:,.2f}</div>
                            </div>
                        </td>
                        <td style="width: 25%; padding: 6px; border: none;">
                            <div class="card card-metric">
                                <div class="card-label">Net Savings</div>
                                <div class="card-value" style="color: {'#059669' if net_savings >= 0 else '#DC2626'};">{symbol} {net_savings:,.2f}</div>
                            </div>
                        </td>
                        <td style="width: 25%; padding: 6px; border: none;">
                            <div class="card card-success">
                                <div class="card-label">Health Score</div>
                                <div class="card-value">{score}/100</div>
                            </div>
                        </td>
                    </tr>
                </table>

                <h2 class="section-title">Spending Breakdown</h2>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th>Total Outlay</th>
                            <th>Allocation (%)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cat_rows_html}
                    </tbody>
                </table>

                <h2 class="section-title">Forensic Audits Summary</h2>
                
                <h3>Recurring Subscription Leakages</h3>
                <ul>
                    {sub_html if sub_html else "<li>None identified.</li>"}
                </ul>
                <p style="font-size: 11px; color: #64748B;">Estimated Annualized Subscription Leakage: <strong>{symbol} {annual_est:,.2f}</strong></p>

                <h3>Duplicate Payment Detections</h3>
                <ul>
                    {dup_alerts_html if dup_alerts_html else "<li>None detected.</li>"}
                </ul>

                <h3>Large Outflows Detections</h3>
                <ul>
                    {large_txs_html if large_txs_html else "<li>None detected.</li>"}
                </ul>

                <h2 class="section-title">Strategic Tax Deductions &amp; Advisory Action Items</h2>
                <ul>
                    <li style="margin-bottom: 8px;"><strong>Tax Write-Off optimization:</strong> Maintain systematic logs of business transactions to reduce aggregate corporate tax exposure.</li>
                    <li style="margin-bottom: 8px;"><strong>Subscription Scrubbing:</strong> Review and prune active monthly service subscriptions to retain <strong>{symbol} {annual_est:,.2f}</strong> in reserve margins.</li>
                    <li style="margin-bottom: 8px;"><strong>Cash Buffer allocations:</strong> Automate deposits to direct 10% of monthly inflows into secure yield-bearing reserve certificates.</li>
                </ul>

                <div style="margin-top: 40px; font-size: 11px; text-align: center; color: #94A3B8; border-top: 1px solid #E2E8F0; padding-top: 15px;">
                    Report generated by StatementForge AI Auditor Fallback Engine on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.
                </div>
            </div>
        </body>
        </html>
        """
        return html.strip()

    @classmethod
    def chat_with_statement(cls, transactions, chat_history, user_message, currency="INR") -> str:
        """Answers contextual questions regarding transactions while preserving history with retries and fallback."""
        max_retries = 2
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                tx_text = cls._format_transactions(transactions, currency)
                
                # Format chat history
                history_formatted = []
                for msg in chat_history[-10:]: # Keep last 10 messages for context
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    history_formatted.append(f"{role.upper()}: {content}")
                history_text = "\n".join(history_formatted)
                
                prompt = f"""
You are a senior Big-4 AI Financial Auditor and Business Advisor chatbot.
You are helping the user analyze their bank statement.

Extracted Transaction Logs:
{tx_text}

Chat History:
{history_text}

New Question:
{user_message}

Guidelines:
- Respond naturally, professionally, and helpfully like a financial auditor.
- Answer ONLY based on the uploaded statement transactions. Do not make up external information.
- If the question cannot be answered from the statement, politely state so.
- If they ask for specific transaction details (e.g. "how much did I spend on Amazon?"), calculate the sum and list the individual rows with dates.
- Format numbers with the appropriate currency symbol ({currency}).
- Keep the response concise, clear, and formatted in clean Markdown.
- Never expose technical errors, developer instructions, or database structures.
"""
                return cls._call_gemini(prompt, system_instruction="You are a senior Big-4 financial advisor chatbot.")
            except Exception as e:
                last_error = e
                print(f"GeminiService: chat_with_statement attempt {attempt} failed: {e}")
                
        # If all retries failed, fall back to rule-based analysis
        print("GeminiService: chat_with_statement falling back to local offline analysis.")
        return cls.chat_with_statement_fallback(transactions, user_message, currency)

    @classmethod
    def chat_with_statement_fallback(cls, transactions, user_message, currency="INR") -> str:
        """Offline rule-based fallback chat assistant to answer queries when Gemini is unavailable."""
        msg = user_message.lower().strip()
        
        # Calculate key metrics
        total_credit = 0.0
        total_debit = 0.0
        max_debit = 0.0
        max_debit_desc = "N/A"
        max_credit = 0.0
        max_credit_desc = "N/A"
        last_balance = None
        
        for tx in transactions:
            try:
                d = float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                c = float(str(tx.get("credit") or 0.0).replace(",", "").strip())
                total_debit += d
                total_credit += c
                if d > max_debit:
                    max_debit = d
                    max_debit_desc = tx.get("narration", "Debit")
                if c > max_credit:
                    max_credit = c
                    max_credit_desc = tx.get("narration", "Credit")
                bal = tx.get("balance")
                if bal is not None:
                    try:
                        last_balance = float(str(bal).replace(",", "").replace("₹", "").strip())
                    except:
                        pass
            except:
                pass
                
        symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)
        net_savings = total_credit - total_debit
        
        # Subscriptions check
        subscriptions = []
        for tx in transactions:
            try:
                d = float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                narr = tx.get("narration", "")
                if d > 0 and any(kw in narr.lower() for kw in ["netflix", "spotify", "aws", "google", "microsoft", "adobe", "cloud", "saas", "github", "zoom"]):
                    subscriptions.append(f"• **{symbol}{d:,.2f}** - {narr} ({tx.get('date', 'N/A')})")
            except:
                pass
                
        # Duplicates check
        duplicates = {}
        for tx in transactions:
            try:
                d = float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                date = tx.get("date", "N/A")
                narr = tx.get("narration", "")
                if d > 0:
                    key = (date, d)
                    duplicates.setdefault(key, []).append(narr)
            except:
                pass
        dup_alerts = []
        for (date, amt), narrs in duplicates.items():
            if len(narrs) > 1:
                dup_alerts.append(f"• **{symbol}{amt:,.2f}** on {date} (Matched: {', '.join(narrs)})")

        fallback_prefix = "AI service is temporarily unavailable. Displaying analysis generated using the built-in financial audit engine.\n\n"

        # Match intents
        if any(w in msg for w in ["balance", "money", "much do i have", "left in", "remaining"]):
            bal_str = f"{symbol}{last_balance:,.2f}" if last_balance is not None else f"Net savings of {symbol}{net_savings:,.2f}"
            return f"{fallback_prefix}Your available balance (or net cash flow balance) on this statement is **{bal_str}**.\n\nSummary info:\n- Total Inflow: **{symbol}{total_credit:,.2f}**\n- Total Outflow: **{symbol}{total_debit:,.2f}**"
            
        elif any(w in msg for w in ["subscription", "recurring", "saas", "netflix", "spotify", "aws"]):
            if subscriptions:
                sub_list = "\n".join(subscriptions[:10])
                total_sub_amt = 0.0
                for s in subscriptions:
                    try:
                        clean_num = s.split('**')[1].replace(symbol,'').replace(',','').strip()
                        total_sub_amt += float(clean_num)
                    except:
                        pass
                return f"{fallback_prefix}I found the following recurring or subscription-like expenses in this statement:\n\n{sub_list}\n\nTotal estimated monthly subscription outlay: **{symbol}{total_sub_amt:,.2f}**."
            else:
                return f"{fallback_prefix}No active software or entertainment subscriptions were detected on this statement."
                
        elif any(w in msg for w in ["top expense", "largest expense", "highest spend", "most spend", "spent most", "biggest debit"]):
            debits_list = []
            for tx in transactions:
                try:
                    d = float(str(tx.get("debit") or 0.0).replace(",", "").strip())
                    if d > 0:
                        debits_list.append((d, tx.get("date", ""), tx.get("narration", "")))
                except:
                    pass
            debits_list.sort(key=lambda x: x[0], reverse=True)
            if debits_list:
                top_five = "\n".join([f"{i+1}. **{symbol}{amt:,.2f}** on {date} - *{narr}*" for i, (amt, date, narr) in enumerate(debits_list[:5])])
                return f"{fallback_prefix}Your top 5 largest debit transactions are:\n\n{top_five}"
            else:
                return f"{fallback_prefix}No debit transactions were found in this statement."
                
        elif any(w in msg for w in ["duplicate", "double charge", "double entry", "twice"]):
            if dup_alerts:
                dup_list = "\n".join(dup_alerts[:10])
                return f"{fallback_prefix}Yes, I detected potential duplicate transactions (same date and amount) that might be double charges:\n\n{dup_list}\n\nPlease verify with the merchant or bank."
            else:
                return f"{fallback_prefix}I did not find any duplicate transactions (same date and amount) in this statement."
                
        else:
            search_terms = [w for w in msg.split() if len(w) > 3 and w not in ["show", "find", "search", "what", "where", "when", "about", "transaction", "payment", "spend", "received", "from", "with", "have"]]
            if search_terms:
                results = []
                for term in search_terms:
                    for tx in transactions:
                        if term in tx.get("narration", "").lower():
                            d = tx.get("debit") or 0.0
                            c = tx.get("credit") or 0.0
                            amt_str = f"-{symbol}{d}" if float(d) > 0 else f"+{symbol}{c}"
                            results.append(f"• **{tx.get('date')}**: *{tx.get('narration')}* -> **{amt_str}**")
                if results:
                    res_list = "\n".join(results[:15])
                    return f"{fallback_prefix}Found the following matching transactions for **'{', '.join(search_terms)}'**:\n\n{res_list}"
            
            status_text = "healthy savings posture" if net_savings >= 0 else "deficit cash flow"
            return f"{fallback_prefix}Here is an overview of the active statement:\n- **Total Inflow (Credits)**: {symbol}{total_credit:,.2f}\n- **Total Outflow (Debits)**: {symbol}{total_debit:,.2f}\n- **Net Savings**: {symbol}{net_savings:,.2f} ({status_text})\n\nHow can I help you search or analyze these transactions?"

    @classmethod
    def validate_extracted_transactions(cls, raw_text, transactions, currency="INR") -> list:
        """
        Bypassed to preserve transaction records exactly as they are extracted from the PDF
        without any AI modifications, as requested by the user.
        """
        return transactions

        # Format transactions for Gemini
        tx_text = cls._format_transactions(transactions, currency)
        
        # Limit raw text to first 3000 chars to avoid token bloat/slowness
        raw_text_sample = str(raw_text)[:3000]

        prompt = f"""
You are a forensic data clean-up assistant.
Review the raw text snippet and the locally parsed transaction list. Your job is to improve the accuracy of the transactions by matching them to the raw text snippet.

Raw Text Snippet:
{raw_text_sample}

Parsed Transactions:
{tx_text}

Guidelines:
1. Reconstruct narrations that were split across multiple lines.
2. Correct OCR typos in date, narration, and amount fields based on the raw text.
3. Ensure no transaction is removed.
4. Align shifted columns (e.g. if a debit was placed in credit, or vice versa, correct it based on standard accounting rules).
5. Output the corrected transactions in valid JSON format only as a list of objects containing date, narration, debit, credit, and balance.
6. If the parsed transactions look correct, return them as is.

Return valid JSON list only. Do not wrap in markdown or write explanation text.
"""
        try:
            client = cls.get_client()
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            # Use stable fast model
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config
            )
            
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "", 1)
            if response_text.endswith("```"):
                response_text = response_text.rsplit("```", 1)[0]
            response_text = response_text.strip()
            
            cleaned = json.loads(response_text)
            
            # Map keys back to lowercase
            result = []
            for tx in cleaned:
                # Get fields case-insensitively
                date_val = tx.get("Date") or tx.get("date") or ""
                narr_val = tx.get("Narration") or tx.get("narration") or tx.get("Description") or tx.get("description") or ""
                debit_val = tx.get("Debit") or tx.get("debit") or ""
                credit_val = tx.get("Credit") or tx.get("credit") or ""
                bal_val = tx.get("Balance") or tx.get("balance") or ""
                
                result.append({
                    "date": str(date_val),
                    "narration": str(narr_val),
                    "debit": str(debit_val),
                    "credit": str(credit_val),
                    "balance": str(bal_val)
                })
            
            if len(result) > 0:
                print(f"GeminiService: Successfully validated and enhanced {len(result)} transactions.")
                return result
                
        except Exception as e:
            print(f"GeminiService: Validation failed, falling back to local result. Error: {e}")
            
        return transactions
