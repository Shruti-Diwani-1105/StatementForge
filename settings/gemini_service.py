import urllib.request
import json
from PyQt6.QtCore import QThread, pyqtSignal

class GeminiTestWorker(QThread):
    """
    Background worker thread to validate the Google Gemini API key
    by communicating with Google's API servers.
    """
    finished = pyqtSignal(bool, str) # Emits (success, message)

    def __init__(self, api_key, parent=None):
        super().__init__(parent)
        self.api_key = api_key

    def run(self):
        if not self.api_key or not self.api_key.strip():
            self.finished.emit(False, "API Key is empty.")
            return

        try:
            # We hit Google's Models endpoint with the API key to see if it authorizes
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key.strip()}"
            
            # Create a request with a short timeout (3 seconds)
            req = urllib.request.Request(url, method="GET")
            req.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(req, timeout=3.0) as response:
                status = response.getcode()
                if status == 200:
                    self.finished.emit(True, "✓ AI Service Connected successfully!")
                else:
                    self.finished.emit(False, f"Connection rejected (Status code {status}).")
        except urllib.error.HTTPError as e:
            # Check error body for key issue
            try:
                err_data = json.loads(e.read().decode('utf-8'))
                err_msg = err_data.get("error", {}).get("message", "Invalid API Key.")
            except Exception:
                err_msg = f"HTTP Error {e.code}: {e.reason}"
            self.finished.emit(False, f"API key validation failed: {err_msg}")
        except Exception as e:
            self.finished.emit(False, f"Failed to reach AI service server: {str(e)}")

class GeminiService:
    """Service wrapping Gemini LLM configurations."""
    
    @staticmethod
    def get_available_models():
        """Returns the list of Gemini models supported by StatementForge."""
        return [
            "Gemini 2.5 Flash",
            "Gemini 2.5 Pro",
            "Gemini 1.5 Flash",
            "Gemini 1.5 Pro"
        ]
        
    @staticmethod
    def get_default_prompt():
        """Returns default financial parser system prompt."""
        return (
            "You are a professional financial statements parser. "
            "Extract transaction rows accurately including Date, Narration, Reference, Debit, Credit, and Balance."
        )
