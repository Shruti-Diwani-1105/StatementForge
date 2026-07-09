import os
import urllib.request
import urllib.parse
import urllib.error
import json
import webbrowser
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from PyQt6.QtCore import QThread, pyqtSignal
from dotenv import load_dotenv

load_dotenv()

class CallbackHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler to capture Google's redirect containing the authorization code.
    """
    def log_message(self, format, *args):
        # Suppress logging to stdout/stderr to keep terminal clean
        pass

    def do_GET(self):
        # Parse query parameters from the path
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Save the authorization code on the server object
        code = query_params.get("code")
        error = query_params.get("error")
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        
        if code:
            self.server.auth_code = code[0]
            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {
                        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                        background-color: #F8FAFC;
                        color: #0F172A;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .card {
                        background-color: #FFFFFF;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                        text-align: center;
                        max-width: 400px;
                        border: 1px solid #E2E8F0;
                    }
                    .icon {
                        font-size: 48px;
                        color: #10B981;
                        margin-bottom: 20px;
                    }
                    h1 {
                        font-size: 22px;
                        margin: 0 0 10px 0;
                        font-weight: 700;
                    }
                    p {
                        font-size: 14px;
                        color: #64748B;
                        line-height: 1.5;
                        margin: 0 0 24px 0;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="icon">✓</div>
                    <h1>Sign-in Successful!</h1>
                    <p>Google authentication was successful. You can safely close this window and return to StatementForge.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode("utf-8"))
        else:
            err_msg = error[0] if error else "Unknown error occurred."
            self.server.auth_error = err_msg
            failure_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Failed</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                        background-color: #F8FAFC;
                        color: #0F172A;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }}
                    .card {{
                        background-color: #FFFFFF;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                        text-align: center;
                        max-width: 400px;
                        border: 1px solid #E2E8F0;
                    }}
                    .icon {{
                        font-size: 48px;
                        color: #EF4444;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        font-size: 22px;
                        margin: 0 0 10px 0;
                        font-weight: 700;
                    }}
                    p {{
                        font-size: 14px;
                        color: #64748B;
                        line-height: 1.5;
                        margin: 0 0 24px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="icon">❌</div>
                    <h1>Authentication Failed</h1>
                    <p>{err_msg}</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(failure_html.encode("utf-8"))


class GoogleAuthWorker(QThread):
    """
    QThread worker that spins up a local server, opens Google Consent screen in system browser,
    receives redirect code, exchanges it for an Access Token, and fetches user details.
    """
    finished = pyqtSignal(bool, dict)  # (success, user_data_dict or {"error": "..."})

    def __init__(self):
        super().__init__()
        self.server = None
        self.is_cancelled = False

    def run(self):
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or "your_google_client" in client_id:
            self.finished.emit(
                False, 
                {"error": "Google OAuth Client ID is not configured in your .env file.\nPlease add GOOGLE_CLIENT_ID."}
            )
            return

        # 1. Bind to a free local port
        port = self._find_free_port()
        redirect_uri = f"http://127.0.0.1:{port}"
        
        # 2. Spin up local HTTP server
        try:
            self.server = HTTPServer(("127.0.0.1", port), CallbackHandler)
            # Set a 60 seconds socket timeout to prevent blocking indefinitely if tab is closed
            self.server.timeout = 60.0
            self.server.auth_code = None
            self.server.auth_error = None
        except Exception as e:
            if not self.is_cancelled:
                self.finished.emit(False, {"error": f"Failed to start local callback server: {str(e)}"})
            return

        # 3. Construct Google Authorization URL
        auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account"
        }
        auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
        
        if self.is_cancelled:
            try:
                self.server.server_close()
            except Exception:
                pass
            return

        webbrowser.open(auth_url)
        
        # 4. Wait for redirect request
        try:
            self.server.handle_request()
        except Exception as e:
            # Handle socket closing exception during cancellation gracefully
            if self.is_cancelled:
                return
            else:
                self.finished.emit(False, {"error": f"Callback server error: {str(e)}"})
                return
        
        # Shut down the server immediately
        try:
            self.server.server_close()
        except Exception:
            pass

        if self.is_cancelled:
            return

        # Check if auth code was received or if we timed out
        if not self.server.auth_code and not self.server.auth_error:
            self.finished.emit(False, {"error": "Google Sign-In timed out (no response within 60s)."})
            return

        if self.server.auth_error:
            self.finished.emit(False, {"error": f"Google Authentication Error: {self.server.auth_error}"})
            return

        # 5. Exchange auth code for access token
        token_endpoint = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": self.server.auth_code,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        if client_secret and "your_google_client_secret" not in client_secret.strip() and client_secret.strip():
            token_data["client_secret"] = client_secret.strip()
        
        print(f"[Google OAuth] Token exchange request data keys: {list(token_data.keys())}")
        
        try:
            req_data = urllib.parse.urlencode(token_data).encode("utf-8")
            req = urllib.request.Request(
                token_endpoint,
                data=req_data,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                tokens = json.loads(response.read().decode("utf-8"))
                
            access_token = tokens.get("access_token")
            if not access_token:
                self.finished.emit(False, {"error": "Failed to retrieve access token from Google."})
                return
                
            # 6. Fetch user profile from userinfo endpoint
            userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
            req_profile = urllib.request.Request(userinfo_endpoint)
            req_profile.add_header("Authorization", f"Bearer {access_token}")
            
            with urllib.request.urlopen(req_profile, timeout=5) as response:
                user_info = json.loads(response.read().decode("utf-8"))
                
            # Emit success
            if not self.is_cancelled:
                self.finished.emit(True, user_info)
            
        except urllib.error.HTTPError as e:
            if not self.is_cancelled:
                try:
                    error_body = e.read().decode("utf-8")
                    err_json = json.loads(error_body)
                    msg = err_json.get("error_description", e.reason)
                except Exception:
                    msg = e.reason
                self.finished.emit(False, {"error": f"HTTP Error during token exchange: {msg}"})
        except Exception as e:
            if not self.is_cancelled:
                self.finished.emit(False, {"error": f"Failed to retrieve user profile: {str(e)}"})

    def cancel(self):
        """
        Force-stops the local server and flags the worker as cancelled.
        """
        self.is_cancelled = True
        if self.server:
            try:
                # This closes the socket and breaks handle_request()
                self.server.server_close()
            except Exception:
                pass

    def _find_free_port(self) -> int:
        """
        Queries the OS to find an available local port.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port
