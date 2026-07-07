import sys
import os
import google.generativeai as genai
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("API Key not found in .env")
    sys.exit(1)

genai.configure(api_key=api_key)

try:
    print("Listing models available for this API Key:")
    for model in genai.list_models():
        print(f"Model: {model.name} | Supported methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
