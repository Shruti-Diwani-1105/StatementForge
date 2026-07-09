import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

def main():
    api_key = sys.argv[1] if len(sys.argv) > 1 else os.getenv("GEMINI_API_KEY")
    print(f"Testing key: {api_key}")
    if not api_key:
        print("Error: API key is not set.")
        return
        
    try:
        genai.configure(api_key=api_key)
        models_to_test = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        for model_name in models_to_test:
            print(f"Testing model: {model_name}...")
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Say hello.")
                print(f"Success with {model_name}! Response: {response.text}")
                return
            except Exception as e:
                print(f"Failed with {model_name}: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"Config error: {e}")

if __name__ == "__main__":
    main()
