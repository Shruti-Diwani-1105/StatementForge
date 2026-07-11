import smtplib
from PyQt6.QtCore import QThread, pyqtSignal

class EmailTestWorker(QThread):
    """
    Background worker thread to test SMTP server connections and credentials
    without blocking the user interface.
    """
    finished = pyqtSignal(bool, str) # Emits (success, message)

    def __init__(self, host, port, username, password, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def run(self):
        if not self.host or not self.host.strip():
            self.finished.emit(False, "SMTP Server address is empty.")
            return
            
        if not self.port:
            self.finished.emit(False, "SMTP Port is empty.")
            return

        try:
            port_val = int(str(self.port).strip())
        except ValueError:
            self.finished.emit(False, "SMTP Port must be a number.")
            return

        try:
            # Connect based on common secure ports
            if port_val == 465:
                # SSL connection
                server = smtplib.SMTP_SSL(self.host, port_val, timeout=4.0)
            else:
                # Standard TCP connection, optional upgrade to TLS later
                server = smtplib.SMTP(self.host, port_val, timeout=4.0)
                server.ehlo()
                if server.has_extn("STARTTLS"):
                    server.starttls()
                    server.ehlo()

            # Attempt Authentication if credentials are provided
            if self.username and self.username.strip():
                server.login(self.username.strip(), self.password)

            server.quit()
            self.finished.emit(True, "✓ Email SMTP Connection and Credentials verified successfully!")
        except Exception as e:
            self.finished.emit(False, f"SMTP Connection Failed: {str(e)}")

class EmailService:
    """Service wrapping email logs and SMTP details."""
    
    @staticmethod
    def get_recent_email_logs():
        """Returns mock recent mail dispatches for Logs panel display."""
        return [
            {"date": "2026-07-08 14:22", "recipient": "finance@enterprise.com", "subject": "Statement Report Wells Fargo", "status": "Delivered"},
            {"date": "2026-07-09 09:15", "recipient": "audit@enterprise.com", "subject": "GST Tax File Jun 2026", "status": "Delivered"},
            {"date": "2026-07-10 17:40", "recipient": "cfo@company.com", "subject": "Weekly Summary Audit Sheet", "status": "Failed (Timeout)"}
        ]
