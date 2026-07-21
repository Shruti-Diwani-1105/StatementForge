import smtplib
import ssl
from PyQt6.QtCore import QThread, pyqtSignal
from services.email_service import EmailService

class EmailSendWorker(QThread):
    """
    Background worker thread to execute email transmission off the main GUI thread.
    Keeps the PyQt6 interface fully responsive.
    """
    progress = pyqtSignal(str) # Status message update
    finished = pyqtSignal(bool, str, dict) # (success, message, metadata)

    def __init__(self, sender_email, password, smtp_host, smtp_port, encryption_type, recipient, cc, bcc, subject, body, attachment_paths, report_type="General Report", user_id="guest", parent=None):
        super().__init__(parent)
        self.sender_email = sender_email
        self.password = password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.encryption_type = encryption_type
        self.recipient = recipient
        self.cc = cc
        self.bcc = bcc
        self.subject = subject
        self.body = body
        self.attachment_paths = attachment_paths
        self.report_type = report_type
        self.user_id = user_id

    def run(self):
        self.progress.emit("Connecting to SMTP server...")
        success, msg = EmailService.send_email_sync(
            sender_email=self.sender_email,
            password=self.password,
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            encryption_type=self.encryption_type,
            recipient=self.recipient,
            cc=self.cc,
            bcc=self.bcc,
            subject=self.subject,
            body=self.body,
            attachment_paths=self.attachment_paths,
            report_type=self.report_type,
            user_id=self.user_id
        )
        
        meta = {
            "recipient": self.recipient,
            "subject": self.subject,
            "report_type": self.report_type,
            "attachments": self.attachment_paths
        }
        self.finished.emit(success, msg, meta)


class EmailTestWorker(QThread):
    """
    Background worker thread to validate SMTP connection, authentication,
    and send a small test email without blocking the application.
    """
    finished = pyqtSignal(bool, str) # Emits (success, message)

    def __init__(self, sender_email, password, smtp_host, smtp_port, encryption_type, send_test_mail=False, test_recipient="", parent=None):
        super().__init__(parent)
        self.sender_email = sender_email
        self.password = password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.encryption_type = encryption_type
        self.send_test_mail = send_test_mail
        self.test_recipient = test_recipient

    def run(self):
        if not self.smtp_host or not self.smtp_host.strip():
            self.finished.emit(False, "✕ SMTP Server address is required.")
            return

        if not self.smtp_port:
            self.finished.emit(False, "✕ SMTP Port is required.")
            return

        try:
            port_val = int(str(self.smtp_port).strip())
        except ValueError:
            self.finished.emit(False, "✕ SMTP Port must be a number.")
            return

        if not self.sender_email or not self.sender_email.strip():
            self.finished.emit(False, "✕ Sender Email Address is required.")
            return

        try:
            context = ssl.create_default_context()
            enc_upper = str(self.encryption_type).upper()

            if enc_upper == "SSL/TLS" or port_val == 465:
                server = smtplib.SMTP_SSL(self.smtp_host.strip(), port_val, context=context, timeout=8.0)
            else:
                server = smtplib.SMTP(self.smtp_host.strip(), port_val, timeout=8.0)
                server.ehlo()
                if enc_upper != "NONE" and server.has_extn("STARTTLS"):
                    server.starttls(context=context)
                    server.ehlo()

            if self.sender_email and self.password:
                server.login(self.sender_email.strip(), self.password)

            if self.send_test_mail and self.test_recipient and self.test_recipient.strip():
                from email.message import EmailMessage
                msg = EmailMessage()
                msg["From"] = self.sender_email.strip()
                msg["To"] = self.test_recipient.strip()
                msg["Subject"] = "StatementForge - SMTP Configuration Test"
                msg.set_content(
                    "Hello,\n\n"
                    "This is a test email sent from StatementForge Desktop Application.\n"
                    "Your SMTP email configuration is working successfully!\n\n"
                    "Regards,\n"
                    "StatementForge Team"
                )
                server.send_message(msg)

            server.quit()
            self.finished.emit(True, "✓ Email configuration verified successfully!")

        except smtplib.SMTPAuthenticationError:
            self.finished.emit(False, "✕ Unable to authenticate with the email provider. Check credentials.")
        except smtplib.SMTPConnectError:
            self.finished.emit(False, "✕ SMTP Connection failed. Check server address and port.")
        except ssl.SSLError as e:
            self.finished.emit(False, f"✕ TLS/SSL Error: {e}")
        except Exception as e:
            self.finished.emit(False, f"✕ SMTP Connection Failed: {str(e)}")
