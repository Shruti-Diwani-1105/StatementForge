import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class GeminiService:
    """Communicates with the Google Gemini API or OpenAI API to analyze bank statement texts."""
    
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
        Sends the statement text to Gemini or OpenAI API and gets structured JSON.
        Returns a dictionary containing statement details and transaction rows.
        """
        # Reload environment dynamically
        load_dotenv(override=True)
        
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = cls.get_api_key()

        # If OPENAI_API_KEY is configured and not empty, use OpenAI
        if openai_key and openai_key.strip():
            print("GeminiService: OPENAI_API_KEY detected. Parsing with OpenAI GPT-4o-mini...")
            return cls._parse_with_openai(text, openai_key.strip())

        # Otherwise fallback/default to Gemini
        if not gemini_key or not gemini_key.strip():
            raise ValueError(
                "API Key is missing.\n\n"
                "Please configure either GEMINI_API_KEY or OPENAI_API_KEY in the .env file."
            )

        print("GeminiService: Parsing with Google Gemini...")
        return cls._parse_with_gemini(text, gemini_key.strip())

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
                raise RuntimeError("Google Gemini API quota exceeded. Please check your billing status or retry later.")
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
