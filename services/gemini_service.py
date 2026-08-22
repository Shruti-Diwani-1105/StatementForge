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
            
            # Map user-friendly model strings to valid active API identifiers
            model_map = {
                "Gemini Flash Latest": "gemini-flash-latest",
                "Gemini 3.6 Flash": "gemini-3.6-flash",
                "Gemini 3.5 Flash (High)": "gemini-3.5-flash",
                "Gemini 3.5 Flash": "gemini-3.5-flash",
                "Gemini 2.5 Flash": "gemini-flash-latest",
                "Gemini 2.5 Pro": "gemini-flash-latest",
                "Gemini 2.0 Flash": "gemini-flash-latest",
                "Gemini 1.5 Flash": "gemini-flash-latest",
                "Gemini 1.5 Pro": "gemini-flash-latest"
            }
            api_model = model_map.get(model_name, "gemini-flash-latest")
            
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
            
            # Set up fallbacks for deprecation 404 & high demand 503 (fast failover)
            models_to_try = [api_model]
            if "gemini-3.6-flash" not in models_to_try:
                models_to_try.append("gemini-3.6-flash")
            
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
                    print(f"GeminiService: Model {m} failed ({err_msg[:120]}). Attempting next model...")
                    continue
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
            
            # Using stable active model for structural JSON parsing
            response = client.models.generate_content(
                model="gemini-flash-latest",
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
                model="gemini-flash-latest",
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
                model="gemini-flash-latest",
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
            :root {
                --bg-main: #F8FAFC;
                --card-bg: #FFFFFF;
                --text-primary: #0F172A;
                --text-secondary: #475569;
                --text-muted: #64748B;
                --border-color: #E2E8F0;
                --green-accent: #059669;
                --blue-accent: #2563EB;
                --orange-accent: #D97706;
                --red-accent: #DC2626;
                --purple-accent: #7C3AED;
            }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                color: var(--text-primary);
                background-color: var(--bg-main);
                margin: 0;
                padding: 16px;
                font-size: 13px;
                line-height: 1.5;
                -webkit-font-smoothing: antialiased;
            }
            body.dark-mode {
                --bg-main: #0B0F17;
                --card-bg: #151D2A;
                --text-primary: #F9FAFB;
                --text-secondary: #CBD5E1;
                --text-muted: #94A3B8;
                --border-color: #232E42;
            }
            .report-container {
                max-width: 900px;
                margin: 0 auto;
                background-color: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 14px;
                padding: 24px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
            }
            .report-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                border-bottom: 2px solid var(--border-color);
                padding-bottom: 16px;
                margin-bottom: 20px;
            }
            .report-title {
                font-size: 22px;
                font-weight: 800;
                color: var(--text-primary);
                margin: 0 0 4px 0;
                letter-spacing: -0.3px;
            }
            .report-subtitle {
                font-size: 12px;
                color: var(--text-muted);
                margin: 0;
                font-weight: 500;
            }
            .auditor-badge {
                display: inline-block;
                background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
                color: #FFFFFF;
                font-size: 10px;
                font-weight: 700;
                padding: 5px 12px;
                border-radius: 20px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            /* KPI Cards */
            .kpi-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 12px;
                margin-bottom: 24px;
            }
            .kpi-card {
                background-color: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 14px 16px;
                display: flex;
                flex-direction: column;
                gap: 4px;
                position: relative;
                overflow: hidden;
            }
            .kpi-card::before {
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 4px;
                background-color: #CBD5E1;
            }
            .kpi-card.accent-green::before { background-color: var(--green-accent); }
            .kpi-card.accent-blue::before { background-color: var(--blue-accent); }
            .kpi-card.accent-red::before { background-color: var(--red-accent); }
            .kpi-card.accent-purple::before { background-color: var(--purple-accent); }
            .kpi-card.accent-orange::before { background-color: var(--orange-accent); }

            .kpi-label {
                font-size: 11px;
                font-weight: 700;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .kpi-value {
                font-size: 18px;
                font-weight: 800;
                color: var(--text-primary);
                line-height: 1.2;
            }
            .kpi-value.text-green { color: var(--green-accent); }
            .kpi-value.text-red { color: var(--red-accent); }
            .kpi-value.text-blue { color: var(--blue-accent); }
            .kpi-value.text-purple { color: var(--purple-accent); }

            /* Sections & Titles */
            .section-header {
                font-size: 15px;
                font-weight: 700;
                color: var(--text-primary);
                margin: 24px 0 12px 0;
                padding-bottom: 6px;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            /* AI Highlights & Recommendations Box */
            .insights-box {
                background-color: #F8FAFC;
                border: 1px solid var(--border-color);
                border-left: 4px solid var(--blue-accent);
                border-radius: 0 10px 10px 0;
                padding: 14px 18px;
                margin-bottom: 20px;
            }
            body.dark-mode .insights-box { background-color: #1E293B; }
            .insights-box ul {
                margin: 0;
                padding-left: 18px;
            }
            .insights-box li {
                margin-bottom: 6px;
                color: var(--text-secondary);
                font-size: 13px;
            }

            /* Category Chart & Progress Bars */
            .chart-section {
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                align-items: center;
                background-color: #F8FAFC;
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 18px;
                margin-bottom: 20px;
            }
            body.dark-mode .chart-section { background-color: #1E293B; }

            .chart-svg-wrapper {
                width: 170px;
                height: 170px;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }

            .category-list {
                flex: 1;
                min-width: 260px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .category-row {
                display: flex;
                flex-direction: column;
                gap: 3px;
            }
            .cat-header {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                font-weight: 600;
                color: var(--text-primary);
            }
            .cat-bar-bg {
                height: 8px;
                background-color: var(--border-color);
                border-radius: 4px;
                overflow: hidden;
            }
            .cat-bar-fill {
                height: 100%;
                border-radius: 4px;
            }

            /* Risk Gauge & Risk Cards */
            .risk-audit-block {
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                align-items: center;
                background-color: #F8FAFC;
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }
            body.dark-mode .risk-audit-block { background-color: #1E293B; }

            .gauge-wrapper {
                width: 140px;
                text-align: center;
                flex-shrink: 0;
            }
            .gauge-score {
                font-size: 26px;
                font-weight: 900;
                color: var(--text-primary);
                line-height: 1;
            }
            .gauge-label {
                font-size: 10px;
                font-weight: 700;
                color: var(--text-muted);
                text-transform: uppercase;
                margin-top: 4px;
            }
            .risk-badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 800;
                text-transform: uppercase;
                margin-top: 6px;
            }
            .risk-badge-low { background-color: #D1FAE5; color: #065F46; }
            .risk-badge-moderate { background-color: #FEF3C7; color: #92400E; }
            .risk-badge-high { background-color: #FEE2E2; color: #991B1B; }

            .risk-cards-grid {
                flex: 1;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
                gap: 10px;
            }
            .risk-mini-card {
                background-color: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 10px;
                padding: 12px;
                text-align: center;
            }
            .risk-mini-title {
                font-size: 10px;
                font-weight: 700;
                color: var(--text-muted);
                text-transform: uppercase;
            }
            .risk-mini-value {
                font-size: 14px;
                font-weight: 800;
                margin-top: 4px;
            }

            /* Flagged Warning Cards */
            .warning-card {
                background-color: #FFFBEB;
                border: 1px solid #FCD34D;
                border-left: 5px solid #D97706;
                border-radius: 10px;
                padding: 12px 16px;
                margin-bottom: 10px;
            }
            .warning-card.high {
                background-color: #FEF2F2;
                border-color: #FCA5A5;
                border-left-color: #DC2626;
            }
            body.dark-mode .warning-card { background-color: #2E1F0D; border-color: #78350F; }
            body.dark-mode .warning-card.high { background-color: #3B1219; border-color: #881337; }

            .warning-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 4px;
            }
            .warning-title {
                font-size: 13px;
                font-weight: 700;
                color: #92400E;
            }
            .warning-card.high .warning-title { color: #991B1B; }
            .warning-amount {
                font-size: 13px;
                font-weight: 800;
                color: var(--text-primary);
            }
            .warning-detail {
                font-size: 12px;
                color: var(--text-secondary);
            }

            /* Top Transactions List */
            .top-tx-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background-color: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 10px 14px;
                margin-bottom: 8px;
            }
            .top-tx-info {
                display: flex;
                flex-direction: column;
            }
            .top-tx-name {
                font-weight: 700;
                color: var(--text-primary);
                font-size: 13px;
            }
            .top-tx-date {
                font-size: 11px;
                color: var(--text-muted);
            }
            .top-tx-amt {
                font-weight: 800;
                font-size: 14px;
                color: var(--red-accent);
            }

            /* Full Report Action Buttons */
            .report-action-row {
                display: flex;
                justify-content: flex-end;
                gap: 12px;
                margin-top: 28px;
                padding-top: 16px;
                border-top: 1px solid var(--border-color);
            }
            .report-btn {
                padding: 10px 18px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                cursor: pointer;
                border: none;
                transition: transform 0.2s, opacity 0.2s;
            }
            .report-btn:hover { transform: translateY(-1px); }
            .btn-pdf { background: linear-gradient(135deg, #059669 0%, #047857 100%); color: #FFFFFF; }
            .btn-email { background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%); color: #FFFFFF; }
        </style>
        """

    @classmethod
    def _parse_tx_days(cls, transactions) -> int:
        """Calculates active statement day count based on date range in transactions."""
        dates = []
        for tx in transactions:
            d_str = str(tx.get("date", "")).strip()
            if not d_str:
                continue
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d-%b-%Y"):
                try:
                    dt = datetime.datetime.strptime(d_str, fmt)
                    dates.append(dt)
                    break
                except Exception:
                    pass
        if len(dates) >= 2:
            days = (max(dates) - min(dates)).days + 1
            return max(1, days)
        return 30

    # ====================================================
    # SINGLE SOURCE OF TRUTH: UNIFIED DATA ENGINE & VIEWS
    # ====================================================

    @classmethod
    def clean_html_response(cls, text: str) -> str:
        """Strips raw markdown code fences like ```html or ``` from response text."""
        if not text:
            return ""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) > 2 and lines[0].startswith("```"):
                end_idx = len(lines) - 1
                while end_idx > 0 and not lines[end_idx].strip() == "```":
                    end_idx -= 1
                if end_idx > 0:
                    text = "\n".join(lines[1:end_idx]).strip()
        text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^```\s*", "", text).strip()
        text = re.sub(r"\s*```$", "", text).strip()
        return text

    @classmethod
    def normalize_transactions(cls, transactions: list) -> list:
        """
        Normalizes any raw parser transaction list or dictionary into a clean numeric schema:
        {date, narration, debit, credit, balance, transaction_type, reference, category, source_statement_id}
        """
        if not transactions:
            return []

        normalized = []
        for raw in transactions:
            if not isinstance(raw, dict):
                continue

            date_val = str(raw.get("date") or raw.get("Date") or raw.get("txn_date") or "").strip()
            narr_val = str(
                raw.get("narration") or raw.get("description") or raw.get("particulars") or 
                raw.get("Narration") or raw.get("Description") or raw.get("Transaction Description / Narration") or ""
            ).strip()

            def parse_num(val):
                if val is None or val == "":
                    return 0.0
                try:
                    s = str(val).replace(",", "").replace("₹", "").replace("$", "").strip()
                    if s.endswith("-"):
                        s = "-" + s[:-1]
                    return float(s)
                except Exception:
                    return 0.0

            debit_val = parse_num(raw.get("debit") or raw.get("Debit") or raw.get("withdrawal") or raw.get("Debit Amount") or "")
            credit_val = parse_num(raw.get("credit") or raw.get("Credit") or raw.get("deposit") or raw.get("Credit Amount") or "")
            balance_val = parse_num(raw.get("balance") or raw.get("Balance") or raw.get("running_balance") or "")

            total_amt = parse_num(raw.get("amount") or raw.get("total_amount") or "")
            tx_type = str(raw.get("transaction_type") or raw.get("type") or "").lower()
            if total_amt > 0 and debit_val == 0.0 and credit_val == 0.0:
                if "credit" in tx_type or "deposit" in tx_type:
                    credit_val = total_amt
                else:
                    debit_val = total_amt

            narr_lower = narr_val.lower()
            if any(k in narr_lower for k in ["swiggy", "zomato", "restaurant", "cafe", "food", "dining", "starbucks", "blinkit", "instamart", "dominos", "pizza"]):
                cat = "Food & Dining"
            elif any(k in narr_lower for k in ["rent", "housing", "apartment", "society", "lease", "landlord"]):
                cat = "Rent & Housing"
            elif any(k in narr_lower for k in ["netflix", "spotify", "prime", "youtube", "hotstar", "subscription", "aws", "google", "microsoft", "adobe", "saas", "github", "zoom"]):
                cat = "Subscriptions"
            elif any(k in narr_lower for k in ["electricity", "water", "bill", "recharge", "airtel", "jio", "bsnl", "broadband", "bescom", "gas"]):
                cat = "Utilities & Bills"
            elif any(k in narr_lower for k in ["amazon", "flipkart", "myntra", "retail", "shopping", "store", "mall", "supermarket"]):
                cat = "Shopping"
            elif any(k in narr_lower for k in ["uber", "ola", "fuel", "petrol", "transport", "irctc", "metro", "rapido", "namma"]):
                cat = "Transport"
            elif any(k in narr_lower for k in ["upi", "gpay", "phonepe", "paytm", "transfer", "neft", "rtgs", "imps", "@"]):
                cat = "UPI & Direct Transfers"
            else:
                cat = "Other"

            ref_val = str(raw.get("reference") or raw.get("ref_no") or raw.get("ref no") or raw.get("cheque") or "").strip()
            stmt_id = str(raw.get("source_statement_id") or raw.get("statement_id") or "").strip()

            normalized.append({
                "date": date_val,
                "narration": narr_val,
                "debit": abs(debit_val),
                "credit": abs(credit_val),
                "balance": balance_val,
                "transaction_type": "Credit" if credit_val > 0 else "Debit",
                "reference": ref_val,
                "category": cat,
                "source_statement_id": stmt_id
            })

        # Balance Delta Fallback calculation for rows where Debit & Credit are 0.0 but Balance exists
        prev_b = None
        for item in normalized:
            d = item["debit"]
            c = item["credit"]
            b = item["balance"]

            if d == 0.0 and c == 0.0 and b > 0.0 and prev_b is not None and prev_b > 0.0:
                diff = round(b - prev_b, 2)
                if diff > 0:
                    item["credit"] = diff
                    item["transaction_type"] = "Credit"
                elif diff < 0:
                    item["debit"] = abs(diff)
                    item["transaction_type"] = "Debit"

            if b > 0.0:
                prev_b = b

        return normalized

    @classmethod
    def calculate_risk_analysis(cls, transactions: list) -> dict:
        """
        Centralized Risk Engine: Produces a deterministic risk_analysis dictionary.
        Returns exact score, rating, duplicate_risk, liquidity_risk, velocity_risk, and flagged_transactions.
        """
        normalized = cls.normalize_transactions(transactions)
        if not normalized:
            return {
                "score": 100,
                "rating": "LOW RISK",
                "duplicate_risk": "LOW",
                "liquidity_risk": "LOW",
                "velocity_risk": "LOW",
                "flagged_transactions": [],
                "risk_factors": ["No transaction data loaded."]
            }

        total_credit = sum(tx["credit"] for tx in normalized)
        total_debit = sum(tx["debit"] for tx in normalized)

        flagged = []
        penalties = 0

        # 1. Duplicate Detection
        seen = {}
        duplicates_found = 0
        for tx in normalized:
            if tx["debit"] > 0:
                key = (tx["date"], tx["narration"], tx["debit"])
                if key in seen:
                    duplicates_found += 1
                    flagged.append({
                        "title": "Duplicate Transaction Detected",
                        "amount": tx["debit"],
                        "narration": tx["narration"],
                        "date": tx["date"],
                        "reason": "Identical date, merchant narration, and debit amount detected."
                    })
                else:
                    seen[key] = True

        duplicate_risk = "HIGH" if duplicates_found >= 3 else ("MEDIUM" if duplicates_found > 0 else "LOW")
        penalties += duplicates_found * 8

        # 2. Liquidity Risk
        if total_credit > 0:
            outflow_ratio = total_debit / total_credit
        else:
            outflow_ratio = 1.5 if total_debit > 0 else 0.0

        if outflow_ratio > 1.1:
            liquidity_risk = "HIGH"
            penalties += 20
        elif outflow_ratio > 0.85:
            liquidity_risk = "MEDIUM"
            penalties += 10
        else:
            liquidity_risk = "LOW"

        # 3. High-Value Outflow & Velocity Anomalies
        large_outflows = 0
        for tx in normalized:
            if tx["debit"] >= 50000.0:
                large_outflows += 1
                flagged.append({
                    "title": "High-Value Single Outflow",
                    "amount": tx["debit"],
                    "narration": tx["narration"],
                    "date": tx["date"],
                    "reason": "Single transaction exceeding ₹50,000.00."
                })

        if len(normalized) > 50 or large_outflows >= 3:
            velocity_risk = "MEDIUM"
        else:
            velocity_risk = "LOW"

        penalties += large_outflows * 5

        # 4. Score & Rating
        raw_score = max(58, min(98, 100 - penalties))
        if raw_score >= 82:
            rating = "LOW RISK"
        elif raw_score >= 68:
            rating = "MEDIUM RISK"
        else:
            rating = "HIGH RISK"

        risk_factors = []
        if duplicates_found > 0:
            risk_factors.append(f"{duplicates_found} duplicate payment pattern(s) identified for verification.")
        else:
            risk_factors.append("Zero duplicate billing anomalies detected.")

        if liquidity_risk == "HIGH":
            risk_factors.append("Account outflow exceeds total credit income during the statement period.")
        elif liquidity_risk == "MEDIUM":
            risk_factors.append("Outflow absorption ratio is high (>85% of total inflow).")
        else:
            risk_factors.append("Liquidity status is stable with healthy net cash reserves.")

        if large_outflows > 0:
            risk_factors.append(f"{large_outflows} high-value transaction(s) exceeding ₹50,000 flagged for audit review.")
        else:
            risk_factors.append("No excessive single-transaction capital outflow detected.")

        score_reason_lines = []
        symbol_fmt = "₹" if normalized and True else "₹"
        score_reason_lines.append(f"Score of {raw_score}/100 ({rating}) evaluated across {len(normalized)} transactions totaling {symbol_fmt}{total_credit:,.2f} credits and {symbol_fmt}{total_debit:,.2f} debits.")

        if total_credit > 0 and total_debit > total_credit:
            score_reason_lines.append(f"Deducted points due to liquidity risk where total outflows exceed credit income by {((total_debit - total_credit)/total_credit*100):.1f}%.")
        elif total_credit > 0 and total_debit / total_credit > 0.85:
            score_reason_lines.append(f"Outflows absorb {(total_debit/total_credit*100):.1f}% of total credit income reserves.")
        else:
            sav_pct = ((total_credit - total_debit) / total_credit * 100) if total_credit > 0 else 0.0
            score_reason_lines.append(f"Maintains a stable balance sheet with a {sav_pct:.1f}% net savings position.")

        if duplicates_found > 0 or large_outflows > 0:
            items = []
            if duplicates_found > 0:
                items.append(f"{duplicates_found} duplicate entry set(s)")
            if large_outflows > 0:
                items.append(f"{large_outflows} high-value transfer(s) exceeding {symbol_fmt}50,000")
            score_reason_lines.append("Audit findings: " + " and ".join(items) + ".")
        else:
            score_reason_lines.append("Zero duplicate billing anomalies or suspicious large transfers detected.")

        score_reason_text = "<br>• ".join(score_reason_lines)

        return {
            "score": raw_score,
            "rating": rating,
            "duplicate_risk": duplicate_risk,
            "liquidity_risk": liquidity_risk,
            "velocity_risk": velocity_risk,
            "flagged_transactions": flagged,
            "risk_factors": risk_factors,
            "score_reason": score_reason_text
        }

    @classmethod
    def build_report_data(cls, transactions: list, bank_name: str, statement_period: str, account_holder="Unknown", account_number="Unknown", currency="INR", statement_id="") -> dict:
        """
        Creates the single source of truth report_data object powering all 4 views, PDF, and Email.
        """
        normalized = cls.normalize_transactions(transactions)
        total_credits = sum(tx["credit"] for tx in normalized)
        total_debits = sum(tx["debit"] for tx in normalized)
        net_savings = total_credits - total_debits
        savings_rate = (net_savings / total_credits * 100) if total_credits > 0 else 0.0
        days = cls._parse_tx_days(normalized)
        average_daily_burn = total_debits / max(1, days)

        cat_totals = {}
        for tx in normalized:
            if tx["debit"] > 0:
                cat = tx["category"]
                cat_totals[cat] = cat_totals.get(cat, 0.0) + tx["debit"]

        spending_categories = []
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (amt / total_debits * 100) if total_debits > 0 else 0.0
            spending_categories.append({
                "category": cat,
                "amount": amt,
                "percentage": pct
            })

        top_debits = sorted([tx for tx in normalized if tx["debit"] > 0], key=lambda x: x["debit"], reverse=True)[:10]
        risk_data = cls.calculate_risk_analysis(normalized)
        symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency + " ")

        highlights = []
        if net_savings >= 0:
            highlights.append(f"Positive net savings recorded at {symbol}{net_savings:,.2f} ({savings_rate:.1f}% savings rate).")
        else:
            highlights.append(f"Net cash deficit of {symbol}{abs(net_savings):,.2f} recorded during the statement period.")
        highlights.append(f"Total credit inflow of {symbol}{total_credits:,.2f} against {symbol}{total_debits:,.2f} total outflows.")
        highlights.append(f"Average daily burn rate stood at {symbol}{average_daily_burn:,.2f} per day across {days} active days.")
        highlights.append(f"Overall audit risk score is rated at {risk_data['score']}/100 ({risk_data['rating']}).")

        spending_insights = []
        if spending_categories:
            top_cat = spending_categories[0]
            spending_insights.append(f"'{top_cat['category']}' represents the largest expense share at {symbol}{top_cat['amount']:,.2f} ({top_cat['percentage']:.1f}%).")
        if len(spending_categories) > 1:
            sec_cat = spending_categories[1]
            spending_insights.append(f"'{sec_cat['category']}' is the second-largest category at {symbol}{sec_cat['amount']:,.2f} ({sec_cat['percentage']:.1f}%).")
        spending_insights.append(f"Top {len(top_debits)} transactions account for {symbol}{sum(t['debit'] for t in top_debits):,.2f} of total outflows.")

        recommendations = []
        if savings_rate < 15:
            recommendations.append("Increase monthly reserve accumulation by reducing discretionary category outflows.")
        else:
            recommendations.append("Maintain positive savings rate and route surplus liquidity toward high-yield reserves.")
        if risk_data["duplicate_risk"] != "LOW":
            recommendations.append("Review flagged duplicate transaction entries with merchant support for refund processing.")
        if average_daily_burn > 2000:
            recommendations.append("Establish daily spending threshold alerts to monitor recurring variable daily outflows.")
        recommendations.append("Implement automated category budget caps to control direct payment transfer volumes.")

        return {
            "statement_id": statement_id,
            "bank_name": bank_name,
            "statement_period": statement_period,
            "account_holder": account_holder,
            "account_number": account_number,
            "currency": currency,
            "transaction_count": len(normalized),
            "total_credits": total_credits,
            "total_debits": total_debits,
            "net_savings": net_savings,
            "savings_rate": savings_rate,
            "average_daily_burn": average_daily_burn,
            "spending_categories": spending_categories,
            "top_transactions": top_debits,
            "risk_analysis": risk_data,
            "ai_highlights": highlights,
            "ai_spending_insights": spending_insights,
            "ai_risk_assessment": risk_data["risk_factors"],
            "recommendations": recommendations
        }

    # ====================================================
    # 4 UI ANALYSIS VIEW RENDERERS (DETERMINISTIC)
    # ====================================================

    @classmethod
    def generate_financial_summary(cls, transactions, bank_name, statement_period, currency="INR") -> str:
        """Renders Output #1: Financial Summary KPI Dashboard."""
        report_data = cls.build_report_data(transactions, bank_name, statement_period, currency=currency)
        return cls._render_financial_summary_view(report_data)

    @classmethod
    def _render_financial_summary_view(cls, report_data: dict) -> str:
        if not report_data or report_data.get("transaction_count", 0) == 0:
            return "<div class='report-container'><p style='text-align:center; color:#64748B;'>No sufficient transaction data available.</p></div>"

        symbol = "₹" if report_data["currency"] == "INR" else ("$" if report_data["currency"] == "USD" else report_data["currency"] + " ")
        total_credits = report_data["total_credits"]
        total_debits = report_data["total_debits"]
        net_savings = report_data["net_savings"]
        savings_rate = report_data["savings_rate"]
        daily_burn = report_data["average_daily_burn"]

        savings_class = "text-green" if net_savings >= 0 else "text-red"
        savings_accent = "accent-green" if net_savings >= 0 else "accent-red"
        bullets_html = "".join([f"<li>{h}</li>" for h in report_data["ai_highlights"]])

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    {cls._get_report_styles()}
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <div>
                <h1 class="report-title">📋 Financial Summary</h1>
                <p class="report-subtitle">{report_data['bank_name']} • {report_data['statement_period']} • {report_data['transaction_count']} Transactions</p>
            </div>
            <span class="auditor-badge">KPI Dashboard</span>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card accent-green">
                <span class="kpi-label">TOTAL INFLOW</span>
                <span class="kpi-value text-green">{symbol}{total_credits:,.2f}</span>
            </div>
            <div class="kpi-card accent-red">
                <span class="kpi-label">TOTAL OUTFLOW</span>
                <span class="kpi-value text-red">{symbol}{total_debits:,.2f}</span>
            </div>
            <div class="kpi-card {savings_accent}">
                <span class="kpi-label">NET SAVINGS</span>
                <span class="kpi-value {savings_class}">{symbol}{net_savings:,.2f}</span>
            </div>
            <div class="kpi-card accent-purple">
                <span class="kpi-label">SAVINGS RATE</span>
                <span class="kpi-value text-purple">{savings_rate:.1f}%</span>
            </div>
            <div class="kpi-card accent-blue">
                <span class="kpi-label">AVG DAILY BURN</span>
                <span class="kpi-value text-blue">{symbol}{daily_burn:,.2f}</span>
            </div>
        </div>

        <h3 class="section-header">AI Highlights</h3>
        <div class="insights-box">
            <ul>
                {bullets_html}
            </ul>
        </div>
    </div>
</body>
</html>"""
        return cls.clean_html_response(html)

    @classmethod
    def analyze_monthly_spending(cls, transactions, currency="INR", **kwargs) -> str:
        """Renders Output #2: Spending Insights with Donut SVG & Top Transactions."""
        bank_name = kwargs.get("bank_name", "Unknown Bank")
        statement_period = kwargs.get("period", "Unknown Period")
        report_data = cls.build_report_data(transactions, bank_name, statement_period, currency=currency)
        return cls._render_spending_insights_view(report_data)

    @classmethod
    def _render_spending_insights_view(cls, report_data: dict) -> str:
        if not report_data or report_data.get("transaction_count", 0) == 0:
            return "<div class='report-container'><p style='text-align:center; color:#64748B;'>No valid transaction data found in the selected statement.</p></div>"

        symbol = "₹" if report_data["currency"] == "INR" else ("$" if report_data["currency"] == "USD" else report_data["currency"] + " ")
        total_debits = report_data["total_debits"]
        cats = report_data["spending_categories"]

        cat_colors = ["#2563EB", "#7C3AED", "#059669", "#D97706", "#EC4899", "#8B5CF6", "#64748B", "#0D9488", "#E11D48"]

        # Progress bar / table rows
        rows_html = ""
        for idx, cat_item in enumerate(cats):
            c_name = cat_item["category"]
            c_amt = cat_item["amount"]
            c_pct = cat_item["percentage"]
            color = cat_colors[idx % len(cat_colors)]

            rows_html += f"""
            <div class="progress-item" style="margin-bottom:10px;">
                <div class="progress-info" style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; margin-bottom:4px;">
                    <span class="progress-label" style="display:flex; align-items:center; gap:6px;">
                        <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background-color:{color};"></span>
                        {c_name}
                    </span>
                    <span class="progress-value" style="font-weight:700;">{symbol}{c_amt:,.2f} ({c_pct:.1f}%)</span>
                </div>
                <div class="progress-bar-bg" style="height:8px; background-color:var(--border-color); border-radius:4px; overflow:hidden;">
                    <div class="progress-bar-fill" style="width: {min(100, max(3, c_pct))}%; height:100%; background-color: {color}; border-radius:4px;"></div>
                </div>
            </div>
            """

        # SVG Donut Chart (if <= 6 categories) or Horizontal Bar Chart (if > 6 categories)
        if len(cats) <= 6:
            svg_arcs = ""
            accumulated_pct = 0.0
            for idx, cat_item in enumerate(cats):
                c_pct = cat_item["percentage"]
                color = cat_colors[idx % len(cat_colors)]
                dash_array = f"{c_pct * 2.827} {282.7 - (c_pct * 2.827)}"
                dash_offset = -accumulated_pct * 2.827
                svg_arcs += f'<circle cx="60" cy="60" r="45" fill="transparent" stroke="{color}" stroke-width="16" stroke-dasharray="{dash_array}" stroke-dashoffset="{dash_offset}" />'
                accumulated_pct += c_pct

            chart_html = f"""
            <div class="chart-container" style="display:flex; flex-wrap:wrap; gap:24px; align-items:center; background-color:var(--bg-main); border:1px solid var(--border-color); border-radius:12px; padding:20px; margin-bottom:24px;">
                <div class="donut-chart-wrapper" style="position:relative; width:140px; height:140px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                    <svg width="140" height="140" viewBox="0 0 120 120" style="transform: rotate(-90deg);">
                        {svg_arcs if svg_arcs else '<circle cx="60" cy="60" r="45" fill="transparent" stroke="#E2E8F0" stroke-width="16"/>'}
                    </svg>
                    <div class="donut-center-text" style="position:absolute; text-align:center;">
                        <span class="donut-label" style="display:block; font-size:9px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">TOTAL SPENDING</span>
                        <span class="donut-val" style="display:block; font-size:12px; font-weight:800; color:var(--text-primary);">{symbol}{total_debits:,.2f}</span>
                    </div>
                </div>
                <div class="progress-list" style="flex:1; min-width:240px;">
                    {rows_html}
                </div>
            </div>
            """
        else:
            chart_html = f"""
            <div class="bar-chart-container" style="background-color:var(--bg-main); border:1px solid var(--border-color); border-radius:12px; padding:20px; margin-bottom:24px;">
                <div style="font-size:11px; font-weight:700; color:var(--text-muted); margin-bottom:12px; text-transform:uppercase;">HORIZONTAL CATEGORY BREAKDOWN ({len(cats)} CATEGORIES)</div>
                {rows_html}
            </div>
            """

        insights_html = "".join([f"<li>{h}</li>" for h in report_data["ai_spending_insights"]])

        top_tx_html = ""
        for tx in report_data["top_transactions"]:
            top_tx_html += f"""
            <div class="top-tx-card" style="display:flex; justify-content:space-between; align-items:center; background-color:var(--card-bg); border:1px solid var(--border-color); border-radius:10px; padding:12px 16px; margin-bottom:8px;">
                <div>
                    <div class="top-tx-narr" style="font-weight:700; color:var(--text-primary); font-size:13px;">{tx['narration']}</div>
                    <div class="top-tx-sub" style="font-size:11px; color:var(--text-muted); margin-top:2px;">{tx['date']} • {tx['category']}</div>
                </div>
                <div class="top-tx-amount" style="font-size:14px; font-weight:800; color:var(--red-accent);">{symbol}{tx['debit']:,.2f}</div>
            </div>
            """

        if not top_tx_html:
            top_tx_html = "<p style='color:#64748B;'>No debit transactions recorded.</p>"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    {cls._get_report_styles()}
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <div>
                <h1 class="report-title">📊 Spending Insights</h1>
                <p class="report-subtitle">Where your money went • {report_data['bank_name']} • {report_data['statement_period']}</p>
            </div>
            <span class="auditor-badge" style="background-color:#7C3AED;">Category Audit</span>
        </div>

        <h3 class="section-header">SPENDING BY CATEGORY</h3>
        {chart_html}

        <h3 class="section-header">AI Spending Insights</h3>
        <div class="insights-box">
            <ul>
                {insights_html}
            </ul>
        </div>

        <h3 class="section-header">Top Transactions</h3>
        <div class="top-tx-grid">
            {top_tx_html}
        </div>
    </div>
</body>
</html>"""
        return cls.clean_html_response(html)

    @classmethod
    def analyze_risks(cls, transactions, currency="INR", **kwargs) -> str:
        """Renders Output #3: Risk Analysis Forensic Audit Dashboard."""
        bank_name = kwargs.get("bank_name", "Unknown Bank")
        statement_period = kwargs.get("period", "Unknown Period")
        report_data = cls.build_report_data(transactions, bank_name, statement_period, currency=currency)
        return cls._render_risk_analysis_view(report_data)

    @classmethod
    def _render_risk_analysis_view(cls, report_data: dict) -> str:
        if not report_data or report_data.get("transaction_count", 0) == 0:
            return "<div class='report-container'><p style='text-align:center; color:#64748B;'>No valid transaction data found in the selected statement.</p></div>"

        symbol = "₹" if report_data["currency"] == "INR" else ("$" if report_data["currency"] == "USD" else report_data["currency"] + " ")
        risk_info = report_data["risk_analysis"]
        score = risk_info["score"]
        rating = risk_info["rating"]

        rating_upper = rating.upper()
        if "CRITICAL" in rating_upper:
            risk_color = "#991B1B"
        elif "HIGH" in rating_upper:
            risk_color = "#DC2626"
        elif "MEDIUM" in rating_upper or "MODERATE" in rating_upper:
            risk_color = "#D97706"
        else:
            risk_color = "#059669"

        # Flagged transaction cards
        flagged_cards_html = ""
        for item in risk_info["flagged_transactions"]:
            flagged_cards_html += f"""
            <div class="warning-card high">
                <div class="warning-header">
                    <span class="warning-title">⚠️ {item['title']}</span>
                    <span class="warning-amount">{symbol}{item['amount']:,.2f}</span>
                </div>
                <div class="warning-detail">{item['date']} • {item['narration']} — {item['reason']}</div>
            </div>
            """

        if not flagged_cards_html:
            flagged_cards_html = """
            <div class="warning-card" style="background-color:#ECFDF5; border-color:#A7F3D0; border-left-color:#059669;">
                <div class="warning-header">
                    <span class="warning-title" style="color:#065F46;">✓ No Flagged Anomalies</span>
                </div>
                <div class="warning-detail" style="color:#047857;">No qualifying duplicate, unusual-time, high-value or suspicious transaction pattern was detected.</div>
            </div>
            """

        risk_bullets_html = "".join([f"<li>{h}</li>" for h in risk_info["risk_factors"]])

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    {cls._get_report_styles()}
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <div>
                <h1 class="report-title">🛡️ Risk Analysis</h1>
                <p class="report-subtitle">{report_data['bank_name']} • {report_data['statement_period']}</p>
            </div>
            <span class="auditor-badge" style="background-color:#EA580C;">FORENSIC AUDIT</span>
        </div>

        <div class="risk-score-wrapper">
            <div class="score-ring">
                <svg width="120" height="120" viewBox="0 0 100 100" style="transform: rotate(-90deg);">
                    <circle cx="50" cy="50" r="42" fill="transparent" stroke="#E2E8F0" stroke-width="8" />
                    <circle cx="50" cy="50" r="42" fill="transparent" stroke="{risk_color}" stroke-width="8" stroke-dasharray="{score * 2.639} 263.9" />
                </svg>
                <div class="score-center-text">
                    <span class="score-num" style="color:{risk_color};">{score}</span>
                    <span class="score-den">/100</span>
                </div>
            </div>
            <div class="score-meta" style="display:flex; flex-direction:column; justify-content:center;">
                <div style="font-size:16px; font-weight:800; color:{risk_color}; letter-spacing:0.5px; margin-bottom:4px; text-transform:uppercase;">{rating}</div>
                <div style="margin-top:4px; color:var(--text-secondary); font-size:12px; line-height:1.5;">
                    <strong>Score Rationale:</strong><br>• {risk_info.get('score_reason', 'Comprehensive deterministic forensic compliance assessment score.')}
                </div>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card accent-blue">
                <span class="kpi-label">DUPLICATE RISK</span>
                <span class="kpi-value text-blue">{risk_info['duplicate_risk']}</span>
            </div>
            <div class="kpi-card accent-purple">
                <span class="kpi-label">LIQUIDITY RISK</span>
                <span class="kpi-value text-purple">{risk_info['liquidity_risk']}</span>
            </div>
            <div class="kpi-card accent-orange">
                <span class="kpi-label">VELOCITY RISK</span>
                <span class="kpi-value text-orange">{risk_info['velocity_risk']}</span>
            </div>
        </div>

        <h3 class="section-header">⚠️ Flagged Transactions</h3>
        <div class="warning-grid">
            {flagged_cards_html}
        </div>

        <h3 class="section-header">AI Risk Assessment</h3>
        <div class="insights-box" style="border-left-color:#EA580C;">
            <ul>
                {risk_bullets_html}
            </ul>
        </div>
    </div>
</body>
</html>"""
        return cls.clean_html_response(html)

    @classmethod
    def generate_executive_report(cls, transactions, bank_name, account_holder, account_number, statement_period, currency="INR") -> str:
        """Renders Output #4: ✨ Generate Full AI Report (Executive Report)."""
        report_data = cls.build_report_data(
            transactions, 
            bank_name, 
            statement_period, 
            account_holder=account_holder, 
            account_number=account_number, 
            currency=currency
        )
        return cls._render_full_report_view(report_data)

    @classmethod
    def _render_full_report_view(cls, report_data: dict) -> str:
        if not report_data or report_data.get("transaction_count", 0) == 0:
            return "<div class='report-container'><p style='text-align:center; color:#64748B;'>No valid transaction data found in the selected statement.</p></div>"

        symbol = "₹" if report_data["currency"] == "INR" else ("$" if report_data["currency"] == "USD" else report_data["currency"] + " ")
        total_credits = report_data["total_credits"]
        total_debits = report_data["total_debits"]
        net_savings = report_data["net_savings"]
        savings_rate = report_data["savings_rate"]
        daily_burn = report_data["average_daily_burn"]

        savings_class = "text-green" if net_savings >= 0 else "text-red"
        savings_accent = "accent-green" if net_savings >= 0 else "accent-red"

        risk_info = report_data["risk_analysis"]
        score = risk_info["score"]
        rating = risk_info["rating"]

        top_cat_name = report_data["spending_categories"][0]["category"] if report_data["spending_categories"] else "N/A"

        recs_html = "".join([f"<li>{r}</li>" for r in report_data["recommendations"]])

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    {cls._get_report_styles()}
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <div>
                <h1 class="report-title">✨ AI FINANCIAL &amp; FORENSIC REPORT</h1>
                <p class="report-subtitle">{report_data['account_holder']} • {report_data['bank_name']} • Account #{report_data['account_number']} • {report_data['statement_period']}</p>
            </div>
            <span class="auditor-badge" style="background:linear-gradient(135deg, #059669 0%, #047857 100%);">Full AI Report</span>
        </div>

        <h3 class="section-header">1. Executive Overview</h3>
        <div class="insights-box" style="border-left-color:#059669;">
            <p style="margin:0; font-size:13px;">Statement ledger contains {report_data['transaction_count']} transactions. Total credit inflows of <strong>{symbol}{total_credits:,.2f}</strong> against total debit outflows of <strong>{symbol}{total_debits:,.2f}</strong> resulting in net savings of <strong>{symbol}{net_savings:,.2f}</strong> ({savings_rate:.1f}% savings rate).</p>
        </div>

        <h3 class="section-header">2. Financial Performance</h3>
        <div class="kpi-grid">
            <div class="kpi-card accent-green">
                <span class="kpi-label">Total Credits</span>
                <span class="kpi-value text-green">{symbol}{total_credits:,.2f}</span>
            </div>
            <div class="kpi-card accent-red">
                <span class="kpi-label">Total Debits</span>
                <span class="kpi-value text-red">{symbol}{total_debits:,.2f}</span>
            </div>
            <div class="kpi-card {savings_accent}">
                <span class="kpi-label">Net Savings</span>
                <span class="kpi-value {savings_class}">{symbol}{net_savings:,.2f}</span>
            </div>
            <div class="kpi-card accent-purple">
                <span class="kpi-label">Savings Rate</span>
                <span class="kpi-value text-purple">{savings_rate:.1f}%</span>
            </div>
            <div class="kpi-card accent-blue">
                <span class="kpi-label">Avg Daily Burn</span>
                <span class="kpi-value text-blue">{symbol}{daily_burn:,.2f}</span>
            </div>
        </div>

        <h3 class="section-header">3. Spending Assessment</h3>
        <div class="insights-box" style="border-left-color:#7C3AED;">
            <p style="margin:0 0 6px 0;">Total outflow across statement period was <strong>{symbol}{total_debits:,.2f}</strong> across {len(report_data['top_transactions'])} top debit entries.</p>
        </div>

        <h3 class="section-header">4. Risk Assessment</h3>
        <div class="insights-box" style="border-left-color:#EA580C;">
            <p style="margin:0 0 6px 0; font-size:14px;"><strong>Audit Risk Score: {score}/100 — {rating}</strong></p>
            <p style="margin:0;">Duplicate Risk: <strong>{risk_info['duplicate_risk']}</strong> • Liquidity Risk: <strong>{risk_info['liquidity_risk']}</strong> • Velocity Risk: <strong>{risk_info['velocity_risk']}</strong>.</p>
        </div>

        <h3 class="section-header">5. Key Recommendations</h3>
        <div class="insights-box" style="border-left-color:#2563EB;">
            <ol style="margin:0; padding-left:18px;">
                {recs_html}
            </ol>
        </div>

        <h3 class="section-header">6. Final Financial Snapshot</h3>
        <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));">
            <div class="kpi-card accent-green">
                <span class="kpi-label">INCOME</span>
                <span class="kpi-value text-green">{symbol}{total_credits:,.2f}</span>
            </div>
            <div class="kpi-card accent-red">
                <span class="kpi-label">EXPENSES</span>
                <span class="kpi-value text-red">{symbol}{total_debits:,.2f}</span>
            </div>
            <div class="kpi-card {savings_accent}">
                <span class="kpi-label">SAVINGS</span>
                <span class="kpi-value {savings_class}">{symbol}{net_savings:,.2f}</span>
            </div>
            <div class="kpi-card accent-purple">
                <span class="kpi-label">SAVINGS RATE</span>
                <span class="kpi-value text-purple">{savings_rate:.1f}%</span>
            </div>
            <div class="kpi-card accent-orange">
                <span class="kpi-label">RISK SCORE</span>
                <span class="kpi-value text-orange">{score}/100</span>
            </div>
            <div class="kpi-card accent-blue">
                <span class="kpi-label">TOP SPENDING</span>
                <span class="kpi-value text-blue" style="font-size:13px; font-weight:700;">{top_cat_name}</span>
            </div>
        </div>

        <div class="report-action-row">
            <button type="button" class="report-btn btn-pdf" onclick="triggerExportPdf()">📥 Export PDF</button>
            <button type="button" class="report-btn btn-email" onclick="triggerSendEmail()">✉️ Send via Email</button>
        </div>
    </div>
</body>
</html>"""
        return cls.clean_html_response(html)

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
            # Use stable active model
            response = client.models.generate_content(
                model="gemini-flash-latest",
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

    @classmethod
    def analyze_gst_transactions(cls, transactions, currency="INR") -> list:
        """
        Calls Gemini to perform tax auditing and classification on transaction data.
        Returns a list of dictionaries containing audited GST metadata.
        """
        if not transactions:
            return []
            
        tx_text = cls._format_transactions(transactions, currency)
        
        prompt = f"""
You are an expert corporate tax auditor. Analyze the following list of transactions from a bank statement:

{tx_text}

For each transaction, determine:
1. "category": Classify into one of these EXACT categories:
   - Bank Charges
   - Processing Fees
   - Service Charges
   - Courier Charges
   - Office Expenses
   - Utilities
   - Software Subscription
   - Vendor Payment
   - Fuel
   - Travel
   - Miscellaneous
   - Personal (if it represents non-business spending like swiggy, starbucks, netflix, personal dining, shopping, grocery, etc.)
2. "vendor": Detect/normalize the merchant or vendor name (e.g. "UBER", "AMAZON", "HDFC BANK").
3. "gstin": Predict 15-character GSTIN identifier if known for this enterprise (e.g., "27AAACH111221Z3") or return "Unassigned".
4. "is_business": Boolean (true if business-related, false if personal).
5. "gst_rate": The standard Indian GST rate that applies to this transaction category (0.18, 0.05, 0.12, 0.28, or 0.00). If the transaction is personal or GST doesn't apply, set to 0.00.
6. "itc_eligible": "Yes" if it's a business expense eligible for Input Tax Credit (ITC) under GST laws (blocked credits like Fuel or Personal expenses should be "No"), otherwise "No".
7. "confidence": Integer percentage (0-100) representing your confidence in this classification.
8. "is_duplicate": Boolean (true if there's another transaction on the same date with the identical description and amount, representing double-billing).
9. "is_missing_invoice": Boolean (true if this is a business expense where GST was paid/applicable but no invoice number, invoice reference, or bill ID is in the transaction narration).

Output format: A valid JSON array of objects, each containing:
- "date": (the date from the transaction)
- "narration": (the narration from the transaction)
- "category": (string)
- "vendor": (string)
- "gstin": (string)
- "is_business": (boolean)
- "gst_rate": (float)
- "itc_eligible": (string: "Yes" or "No")
- "confidence": (integer)
- "is_duplicate": (boolean)
- "is_missing_invoice": (boolean)

Ensure the output is ONLY a valid JSON list. Do not wrap in markdown or add explanations.
"""
        try:
            client = cls.get_client()
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt,
                config=config
            )
            
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "", 1)
            if response_text.endswith("```"):
                response_text = response_text.rsplit("```", 1)[0]
            response_text = response_text.strip()
            
            import json
            cleaned = json.loads(response_text)
            
            ledger = []
            tx_map = {}
            for tx in transactions:
                key = (tx.get("date", ""), tx.get("narration", ""))
                tx_map[key] = tx
                
            for item in cleaned:
                date = item.get("date", "")
                narration = item.get("narration", "")
                
                orig_tx = tx_map.get((date, narration)) or next((tx for tx in transactions if tx.get("narration") == narration), None)
                if not orig_tx:
                    continue
                    
                debit = orig_tx.get("debit", 0.0)
                credit = orig_tx.get("credit", 0.0)
                try:
                    debit_val = float(str(debit).replace(",", "").strip()) if debit else 0.0
                except:
                    debit_val = 0.0
                try:
                    credit_val = float(str(credit).replace(",", "").strip()) if credit else 0.0
                except:
                    credit_val = 0.0
                    
                if debit_val > 0:
                    amount = debit_val
                    tx_type = "Debit (ITC Claimable)"
                elif credit_val > 0:
                    amount = credit_val
                    tx_type = "Credit (GST Output)"
                else:
                    continue
                    
                rate = float(item.get("gst_rate", 0.18))
                base_value = amount / (1.0 + rate)
                total_gst = amount - base_value
                
                if "igst" in narration.lower() or "interstate" in narration.lower():
                    cgst, sgst, igst = 0.0, 0.0, total_gst
                else:
                    cgst, sgst, igst = total_gst / 2.0, total_gst / 2.0, 0.0
                    
                ledger.append({
                    "date": date,
                    "narration": narration,
                    "type": tx_type,
                    "category": item.get("category", "Miscellaneous"),
                    "vendor": item.get("vendor", "Unknown Vendor"),
                    "gstin": item.get("gstin", "Unassigned"),
                    "total_amount": amount,
                    "base_value": round(base_value, 2),
                    "gst_rate": rate,
                    "cgst": round(cgst, 2),
                    "sgst": round(sgst, 2),
                    "igst": round(igst, 2),
                    "total_gst": round(total_gst, 2),
                    "itc_eligible": item.get("itc_eligible", "No"),
                    "is_business": bool(item.get("is_business", True)),
                    "confidence": float(item.get("confidence", 80.0)),
                    "status": "Verified" if float(item.get("confidence", 80.0)) >= 85 else "Estimated",
                    "is_duplicate": bool(item.get("is_duplicate", False)),
                    "is_missing_invoice": bool(item.get("is_missing_invoice", False)),
                    "gstr2b_status": "Not Reconciled"
                })
            return ledger
        except Exception as e:
            print(f"GeminiService: GST transaction analysis failed: {e}")
            return []

    @classmethod
    def chat_with_statement(cls, transactions: list, chat_history: list, message: str, currency="INR", **kwargs) -> str:
        """
        AI Chatbot Engine: Answers financial questions using ONLY the actual selected statement transactions.
        1. Validates and normalizes statement transactions (Single Source of Truth).
        2. Evaluates query intent deterministically (Top Expenses, Duplicate UPIs, Subscriptions, Where I Spend Most, Totals/Stats).
        3. Formats response into clean HTML cards matching StatementForge UI aesthetics.
        4. Invokes Gemini as a natural language synthesizer strictly using the actual calculated facts (Never invents numbers).
        """
        if not transactions or len(transactions) == 0:
            return (
                "<div style='background:#FEF2F2; border:1px solid #FCA5A5; border-radius:8px; padding:12px; color:#991B1B; font-size:13px; font-weight:600;'>"
                "⚠️ No sufficient transaction data is available for this statement.<br>"
                "Please verify that the statement has been parsed successfully."
                "</div>"
            )

        normalized = cls.normalize_transactions(transactions)
        if not normalized:
            return (
                "<div style='background:#FEF2F2; border:1px solid #FCA5A5; border-radius:8px; padding:12px; color:#991B1B; font-size:13px; font-weight:600;'>"
                "⚠️ No sufficient transaction data is available for this statement."
                "</div>"
            )

        symbol = "₹" if currency == "INR" else ("$" if currency == "USD" else currency + " ")
        msg_lower = message.lower().strip()

        # Build Single Source of Truth Metrics
        total_credits = sum(tx["credit"] for tx in normalized)
        total_debits = sum(tx["debit"] for tx in normalized)
        net_savings = total_credits - total_debits
        savings_rate = (net_savings / total_credits * 100) if total_credits > 0 else 0.0

        # --- INTENT 1: TOP EXPENSES ---
        if any(w in msg_lower for w in ["top expense", "top expenses", "largest expense", "highest expense", "highest debit", "big expense", "most expensive"]):
            debit_txs = [tx for tx in normalized if tx["debit"] > 0]
            if not debit_txs:
                return "<p style='margin:4px 0; color:#64748B;'>No debit expenses were found in the selected statement.</p>"
            sorted_debits = sorted(debit_txs, key=lambda x: x["debit"], reverse=True)[:5]
            
            items_html = ""
            for idx, tx in enumerate(sorted_debits, 1):
                cat_badge = f"<span style='background:#EFF6FF; color:#1D4ED8; font-size:11px; padding:2px 8px; border-radius:12px; font-weight:600;'>{tx['category']}</span>" if tx.get("category") else ""
                items_html += f"""
                <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <div style='font-weight:700; color:#0F172A; font-size:13px;'>{idx}. {tx['narration']}</div>
                        <div style='color:#64748B; font-size:11px; margin-top:2px;'>{tx['date']} &nbsp; {cat_badge}</div>
                    </div>
                    <div style='font-weight:800; color:#DC2626; font-size:14px;'>{symbol}{tx['debit']:,.2f}</div>
                </div>
                """
            return f"""
            <div style='font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:#1E293B; font-size:14px; margin-bottom:10px; display:flex; align-items:center; gap:6px;'>
                    <span>📌</span> <span>TOP EXPENSES</span>
                </div>
                {items_html}
            </div>
            """

        # --- INTENT 1B: LOWEST EXPENSES & SMALL PURCHASES ---
        if any(w in msg_lower for w in ["low expense", "low expenses", "lowest expense", "lowest expenses", "small expense", "small expenses", "smallest expense", "cheapest", "minimum expense", "low spending", "lowest spending"]):
            debit_txs = [tx for tx in normalized if tx["debit"] > 0]
            if not debit_txs:
                return "<p style='margin:4px 0; color:#64748B;'>No debit expenses were found in the selected statement.</p>"
            sorted_debits = sorted(debit_txs, key=lambda x: x["debit"])[:5]
            
            items_html = ""
            for idx, tx in enumerate(sorted_debits, 1):
                cat_badge = f"<span style='background:#EFF6FF; color:#1D4ED8; font-size:11px; padding:2px 8px; border-radius:12px; font-weight:600;'>{tx['category']}</span>" if tx.get("category") else ""
                items_html += f"""
                <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <div style='font-weight:700; color:#0F172A; font-size:13px;'>{idx}. {tx['narration']}</div>
                        <div style='color:#64748B; font-size:11px; margin-top:2px;'>{tx['date']} &nbsp; {cat_badge}</div>
                    </div>
                    <div style='font-weight:800; color:#059669; font-size:14px;'>{symbol}{tx['debit']:,.2f}</div>
                </div>
                """
            return f"""
            <div style='font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:#1E293B; font-size:14px; margin-bottom:10px; display:flex; align-items:center; gap:6px;'>
                    <span>📉</span> <span>LOWEST EXPENSES & SMALL PURCHASES</span>
                </div>
                {items_html}
            </div>
            """

        # --- INTENT 2: DUPLICATE UPIS / DUPLICATE TRANSACTIONS ---
        if any(w in msg_lower for w in ["duplicate", "duplicate upi", "duplicate upis", "repeated payment"]):
            seen = {}
            duplicates = []
            for tx in normalized:
                if tx["debit"] > 0:
                    key = (tx["date"], tx["narration"].lower().strip(), tx["debit"])
                    if key in seen:
                        duplicates.append(tx)
                    else:
                        seen[key] = True
            
            if not duplicates:
                return (
                    "<div style='background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:12px; color:#065F46; font-size:13px; font-weight:600;'>"
                    "<strong>✓ DUPLICATE UPI TRANSACTIONS</strong><br>"
                    "No duplicate UPI transactions were detected in the selected statement."
                    "</div>"
                )
            
            dup_items_html = ""
            for tx in duplicates:
                dup_items_html += f"""
                <div style='background:#FEF2F2; border:1px solid #FCA5A5; border-radius:8px; padding:10px 14px; margin-bottom:8px;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <span style='font-weight:700; color:#991B1B; font-size:13px;'>⚠️ {tx['narration']}</span>
                        <span style='font-weight:800; color:#DC2626; font-size:13px;'>{symbol}{tx['debit']:,.2f}</span>
                    </div>
                    <div style='color:#B91C1C; font-size:11px; margin-top:2px;'>Date: {tx['date']} — Duplicate debit pattern detected</div>
                </div>
                """
            return f"""
            <div style='font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:#991B1B; font-size:14px; margin-bottom:10px;'>⚠️ DUPLICATE UPI TRANSACTIONS DETECTED ({len(duplicates)})</div>
                {dup_items_html}
            </div>
            """

        # --- INTENT 3: ACTIVE SUBSCRIPTIONS ---
        if any(w in msg_lower for w in ["subscription", "subscriptions", "recurring", "monthly bill"]):
            sub_keywords = ["netflix", "spotify", "prime", "amazon prime", "youtube", "adobe", "apple", "google", "jio", "airtel", "tatasky", "swiggy super", "zomato gold", "gym", "broadband", "hotstar", "zee5", "sony"]
            merchant_counts = {}
            for tx in normalized:
                if tx["debit"] > 0:
                    narr_lower = tx["narration"].lower()
                    for kw in sub_keywords:
                        if kw in narr_lower:
                            if kw not in merchant_counts:
                                merchant_counts[kw] = {"name": kw.title(), "count": 0, "total": 0.0, "dates": []}
                            merchant_counts[kw]["count"] += 1
                            merchant_counts[kw]["total"] += tx["debit"]
                            merchant_counts[kw]["dates"].append(tx["date"])
                            break

            if not merchant_counts:
                raw_merchant_counts = {}
                for tx in normalized:
                    if tx["debit"] > 0 and len(tx["narration"]) > 3:
                        m_name = tx["narration"].strip()
                        if m_name not in raw_merchant_counts:
                            raw_merchant_counts[m_name] = {"name": m_name, "count": 0, "total": 0.0, "dates": []}
                        raw_merchant_counts[m_name]["count"] += 1
                        raw_merchant_counts[m_name]["total"] += tx["debit"]
                        raw_merchant_counts[m_name]["dates"].append(tx["date"])
                for m_name, m_data in raw_merchant_counts.items():
                    if m_data["count"] >= 2 and any(k in m_name.lower() for k in ["sub", "bill", "pay", "fee", "auto", "club"]):
                        merchant_counts[m_name] = m_data

            if not merchant_counts:
                return (
                    "<div style='background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px; padding:12px; color:#1E40AF; font-size:13px; font-weight:600;'>"
                    "<strong>📱 ACTIVE SUBSCRIPTIONS & RECURRING PAYMENTS</strong><br>"
                    "No recurring subscription payments were identified in the selected statement."
                    "</div>"
                )

            sub_items_html = ""
            for kw, data in merchant_counts.items():
                avg_amt = data["total"] / max(1, data["count"])
                last_date = data["dates"][-1] if data["dates"] else "-"
                sub_items_html += f"""
                <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <div style='font-weight:700; color:#0F172A; font-size:13px;'>📱 {data['name']}</div>
                        <div style='color:#64748B; font-size:11px; margin-top:2px;'>{data['count']} occurrence(s) • Last paid: {last_date}</div>
                    </div>
                    <div style='font-weight:800; color:#2563EB; font-size:13px;'>~{symbol}{avg_amt:,.2f}</div>
                </div>
                """
            return f"""
            <div style='font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:#1E293B; font-size:14px; margin-bottom:10px;'>📱 ACTIVE SUBSCRIPTIONS & RECURRING PAYMENTS</div>
                {sub_items_html}
            </div>
            """

        # --- INTENT 4: WHERE I SPEND MOST / CATEGORY BREAKDOWN ---
        if any(w in msg_lower for w in ["where i spend", "where am i spending", "spend most", "spending category", "category", "breakdown", "spending distribution"]):
            cat_totals = {}
            cat_counts = {}
            for tx in normalized:
                if tx["debit"] > 0:
                    cat = tx.get("category", "Other")
                    cat_totals[cat] = cat_totals.get(cat, 0.0) + tx["debit"]
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1

            if not cat_totals:
                return "<p style='margin:4px 0; color:#64748B;'>No debit spending recorded in this statement.</p>"

            sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
            cat_items_html = ""
            for cat, amount in sorted_cats[:6]:
                pct = (amount / total_debits * 100) if total_debits > 0 else 0.0
                count = cat_counts.get(cat, 0)
                cat_items_html += f"""
                <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; margin-bottom:8px;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <span style='font-weight:700; color:#0F172A; font-size:13px;'>📊 {cat}</span>
                        <span style='font-weight:800; color:#0F172A; font-size:13px;'>{symbol}{amount:,.2f}</span>
                    </div>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-top:4px;'>
                        <div style='background:#E2E8F0; border-radius:4px; height:6px; flex:1; margin-right:10px; overflow:hidden;'>
                            <div style='background:#2563EB; height:100%; width:{min(100, pct):.1f}%;'></div>
                        </div>
                        <span style='color:#64748B; font-size:11px; font-weight:600;'>{pct:.1f}% ({count} tx)</span>
                    </div>
                </div>
                """
            return f"""
            <div style='font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:#1E293B; font-size:14px; margin-bottom:10px;'>📊 SPENDING BY CATEGORY</div>
                {cat_items_html}
            </div>
            """

        # --- INTENT 5: TOTAL INCOME / TOTAL CREDITS ---
        if any(w in msg_lower for w in ["total income", "total credit", "total credits", "how much income", "credit total", "money in", "inflow"]):
            credits_list = [tx for tx in normalized if tx["credit"] > 0]
            max_credit = max((tx["credit"] for tx in credits_list), default=0.0)
            return f"""
            <div style='background:#ECFDF5; border:1px solid #A7F3D0; border-radius:10px; padding:14px; font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:#065F46; font-size:14px; margin-bottom:6px;'>💰 TOTAL INCOME / CREDITS</div>
                <div style='font-size:22px; font-weight:900; color:#059669;'>{symbol}{total_credits:,.2f}</div>
                <div style='color:#047857; font-size:12px; margin-top:6px;'>
                    Total credit transactions: <b>{len(credits_list)}</b><br>
                    Largest credit inflow: <b>{symbol}{max_credit:,.2f}</b>
                </div>
            </div>
            """

        # --- INTENT 6: TOTAL OUTFLOW / TOTAL SPENDING ---
        if any(w in msg_lower for w in ["total spending", "total debit", "total debits", "total outflow", "how much spent", "debit total", "outflow"]):
            debits_list = [tx for tx in normalized if tx["debit"] > 0]
            max_debit = max((tx["debit"] for tx in debits_list), default=0.0)
            return f"""
            <div style='background:#FEF2F2; border:1px solid #FCA5A5; border-radius:10px; padding:14px; font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:#991B1B; font-size:14px; margin-bottom:6px;'>💸 TOTAL SPENDING / DEBITS</div>
                <div style='font-size:22px; font-weight:900; color:#DC2626;'>{symbol}{total_debits:,.2f}</div>
                <div style='color:#B91C1C; font-size:12px; margin-top:6px;'>
                    Total debit transactions: <b>{len(debits_list)}</b><br>
                    Largest debit outflow: <b>{symbol}{max_debit:,.2f}</b>
                </div>
            </div>
            """

        # --- INTENT 7: NET SAVINGS / SAVINGS RATE ---
        if any(w in msg_lower for w in ["savings", "net savings", "savings rate", "how much did i save", "saved"]):
            color = "#059669" if net_savings >= 0 else "#DC2626"
            bg = "#ECFDF5" if net_savings >= 0 else "#FEF2F2"
            border = "#A7F3D0" if net_savings >= 0 else "#FCA5A5"
            return f"""
            <div style='background:{bg}; border:1px solid {border}; border-radius:10px; padding:14px; font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:{color}; font-size:14px; margin-bottom:6px;'>🏦 NET SAVINGS & SAVINGS RATE</div>
                <div style='font-size:22px; font-weight:900; color:{color};'>{symbol}{net_savings:,.2f}</div>
                <div style='color:{color}; font-size:12px; margin-top:6px;'>
                    Savings Rate: <b>{savings_rate:.1f}%</b><br>
                    Income ({symbol}{total_credits:,.2f}) − Spending ({symbol}{total_debits:,.2f})
                </div>
            </div>
            """

        # --- INTENT 8: HIGHEST / LARGEST TRANSACTION ---
        if any(w in msg_lower for w in ["highest transaction", "largest transaction", "max transaction", "biggest transaction"]):
            all_txs = sorted(normalized, key=lambda x: max(x["debit"], x["credit"]), reverse=True)
            if not all_txs:
                return "<p style='margin:4px 0; color:#64748B;'>No transactions found.</p>"
            top = all_txs[0]
            is_debit = top["debit"] > 0
            amt_str = f"{symbol}{top['debit']:,.2f}" if is_debit else f"{symbol}{top['credit']:,.2f}"
            t_type = "Debit (Outflow)" if is_debit else "Credit (Inflow)"
            t_color = "#DC2626" if is_debit else "#059669"
            return f"""
            <div style='background:#F8FAFC; border:1px solid #CBD5E1; border-radius:10px; padding:14px; font-family:Inter, sans-serif;'>
                <div style='font-weight:800; color:#0F172A; font-size:14px; margin-bottom:6px;'>🏆 LARGEST TRANSACTION</div>
                <div style='font-size:20px; font-weight:900; color:{t_color};'>{amt_str}</div>
                <div style='color:#475569; font-size:12px; margin-top:6px;'>
                    <b>Narration:</b> {top['narration']}<br>
                    <b>Date:</b> {top['date']} &nbsp; • &nbsp; <b>Type:</b> {t_type}
                </div>
            </div>
            """

        # --- INTENT 8C: SEARCH BY MERCHANT OR NARRATION KEYWORD ---
        stop_words = ["what", "where", "show", "many", "much", "did", "spent", "paid", "from", "for", "with", "this", "that", "there", "have", "tell", "give", "list", "check", "the", "are", "any", "my"]
        query_words = [w for w in msg_lower.replace("?", "").replace(".", "").split() if len(w) >= 3 and w not in stop_words]
        if len(query_words) > 0:
            matching_txs = [t for t in normalized if any(w in t["narration"].lower() for w in query_words)]
            if len(matching_txs) > 0:
                items_html = ""
                for idx, t in enumerate(matching_txs[:5], 1):
                    amt_str = f"{symbol}{t['debit']:,.2f}" if t["debit"] > 0 else f"{symbol}{t['credit']:,.2f}"
                    color_str = "#DC2626" if t["debit"] > 0 else "#059669"
                    items_html += f"""
                    <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <div style='font-weight:700; color:#0F172A; font-size:13px;'>{idx}. {t['narration']}</div>
                            <div style='color:#64748B; font-size:11px; margin-top:2px;'>{t['date']}</div>
                        </div>
                        <div style='font-weight:800; color:{color_str}; font-size:14px;'>{amt_str}</div>
                    </div>
                    """
                kw_title = " / ".join(query_words[:2]).upper()
                return f"""
                <div style='font-family:Inter, sans-serif;'>
                    <div style='font-weight:800; color:#1E293B; font-size:14px; margin-bottom:10px;'>🔍 TRANSACTIONS MATCHING '{kw_title}' ({len(matching_txs)} items)</div>
                    {items_html}
                </div>
                """

        # --- INTENT 9: GENERAL STATEMENT SUMMARY / UNRECOGNIZED QUERY ---
        facts_summary = f"""
        Statement Data Context:
        - Bank: {kwargs.get('bank_name', 'Bank')}
        - Statement Period: {kwargs.get('period', 'Period')}
        - Total Transactions: {len(normalized)}
        - Total Income / Credits: {symbol}{total_credits:,.2f}
        - Total Outflow / Debits: {symbol}{total_debits:,.2f}
        - Net Savings: {symbol}{net_savings:,.2f} (Savings Rate: {savings_rate:.1f}%)
        - Top 3 Debits: {', '.join([f"{tx['narration']} ({symbol}{tx['debit']:,.2f} on {tx['date']})" for tx in sorted([t for t in normalized if t['debit']>0], key=lambda x:x['debit'], reverse=True)[:3]])}
        """

        try:
            client = cls.get_client()
            if client:
                prompt = (
                    f"You are StatementForge AI Financial Assistant.\n"
                    f"Answer the user's question concisely using ONLY the statement facts provided below.\n"
                    f"DO NOT invent or guess any numbers. If the data does not answer the question, state: 'No sufficient data was found in the selected statement for this question.'\n\n"
                    f"STATEMENT FACTS:\n{facts_summary}\n\n"
                    f"USER QUESTION: {message}"
                )
                gemini_res = cls._call_model_with_fallback(
                    client,
                    prompt=prompt,
                    system_instruction="You are StatementForge AI Assistant. Never invent numbers."
                )
                if gemini_res:
                    return cls.clean_html_response(gemini_res)
        except Exception:
            pass

        return f"""
        <div style='font-family:Inter, sans-serif;'>
            <div style='font-weight:700; color:#0F172A; font-size:13px; margin-bottom:8px;'>📊 Statement Summary ({len(normalized)} transactions)</div>
            <div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; font-size:12px; color:#334155; line-height:1.6;'>
                • <b>Total Income:</b> {symbol}{total_credits:,.2f}<br>
                • <b>Total Spending:</b> {symbol}{total_debits:,.2f}<br>
                • <b>Net Savings:</b> {symbol}{net_savings:,.2f} ({savings_rate:.1f}% savings rate)<br>
                • <b>Transaction Count:</b> {len(normalized)} items parsed.
            </div>
        </div>
        """

