import os
import re
import ssl
import smtplib
import mimetypes
import datetime
from email.message import EmailMessage
from database.email_repository import EmailRepository
from services.credential_manager import CredentialManager

# Common SMTP Provider Presets
PROVIDER_PRESETS = {
    "Gmail": {
        "host": "smtp.gmail.com",
        "port": 587,
        "encryption": "STARTTLS",
        "auth_method": "App Password",
        "note": "Use an App Password instead of your normal Google account password."
    },
    "Outlook / Microsoft": {
        "host": "smtp.office365.com",
        "port": 587,
        "encryption": "STARTTLS",
        "auth_method": "Password",
        "note": "Use your Microsoft 365 or Outlook account credentials."
    },
    "Yahoo": {
        "host": "smtp.mail.yahoo.com",
        "port": 465,
        "encryption": "SSL/TLS",
        "auth_method": "App Password",
        "note": "Generate an App Password from Yahoo Account Security settings."
    },
    "Custom SMTP server": {
        "host": "",
        "port": 587,
        "encryption": "STARTTLS",
        "auth_method": "Password",
        "note": "Enter your custom corporate or personal SMTP server credentials."
    }
}

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

class EmailService:
    """
    Core Email Service for StatementForge.
    Handles email validation, template generation, SMTP connection, and attachment processing.
    """

    @staticmethod
    def validate_email_address(email_str: str) -> bool:
        """Validates standard email address syntax."""
        if not email_str:
            return False
        return bool(EMAIL_REGEX.match(email_str.strip()))

    @staticmethod
    def validate_inputs(recipient: str, sender_email: str, smtp_host: str, smtp_port, attachment_paths: list):
        """
        Validates email sending requirements. Returns (is_valid, error_message).
        """
        if not recipient or not recipient.strip():
            return False, "Recipient email address is required."
        
        # Check all recipient emails (comma or semicolon separated)
        recipients = [r.strip() for r in re.split(r"[,;]", recipient) if r.strip()]
        for r in recipients:
            if not EmailService.validate_email_address(r):
                return False, f"Invalid recipient email format: '{r}'"

        if not sender_email or not sender_email.strip():
            return False, "Sender email address is not configured."

        if not EmailService.validate_email_address(sender_email):
            return False, "Configured sender email address has an invalid format."

        if not smtp_host or not smtp_host.strip():
            return False, "SMTP server host address is missing in Email Configuration."

        try:
            port_num = int(str(smtp_port).strip())
            if port_num <= 0 or port_num > 65535:
                return False, "SMTP Port must be a valid port number between 1 and 65535."
        except ValueError:
            return False, "SMTP Port must be a valid integer."

        if attachment_paths:
            for path in attachment_paths:
                if not os.path.exists(path):
                    return False, f"Attachment file not found: {os.path.basename(path)}"
                if not os.access(path, os.R_OK):
                    return False, f"Attachment file is not readable: {os.path.basename(path)}"
                
                # Check allowed file extensions
                ext = os.path.splitext(path)[1].lower()
                if ext not in [".xlsx", ".xls", ".pdf", ".csv"]:
                    return False, f"Unsupported attachment file type: '{ext}'. Allowed: .xlsx, .xls, .pdf, .csv"

                # Check max size (25MB limit)
                file_size_mb = os.path.getsize(path) / (1024 * 1024)
                if file_size_mb > 25.0:
                    return False, f"Attachment file '{os.path.basename(path)}' exceeds the 25MB email limit."

        return True, "Validation passed."

    @staticmethod
    def generate_smart_template(report_type: str, period: str = "", bank_name: str = "", file_name: str = ""):
        """
        Generates reusable template subject and body text based on report type.
        """
        now_str = datetime.datetime.now().strftime("%d %B %Y")
        period_str = period or datetime.datetime.now().strftime("%B %Y")
        bank_str = f" ({bank_name})" if bank_name else ""

        if "GST" in report_type.upper():
            subject = f"StatementForge - GST Reconciliation Report - {period_str}"
            body = (
                f"Dear Sir/Madam,\n\n"
                f"Please find attached the requested GST Reconciliation & Analysis Report generated using StatementForge{bank_str}.\n\n"
                f"Report Type: GST Reconciliation & Analysis Report\n"
                f"Report Period: {period_str}\n"
                f"Generated Date: {now_str}\n\n"
                f"Please review the attached report and let us know if you have any questions.\n\n"
                f"Regards,\n"
                f"StatementForge Accounting Hub"
            )
        elif "AI" in report_type.upper() or "AUDIT" in report_type.upper():
            subject = f"StatementForge - Financial Analysis Report - {period_str}"
            body = (
                f"Dear Sir/Madam,\n\n"
                f"Please find attached the AI Financial Audit & Insight Report generated using StatementForge{bank_str}.\n\n"
                f"Report Type: AI Financial Analysis Report\n"
                f"Report Period: {period_str}\n"
                f"Generated Date: {now_str}\n\n"
                f"The attached document includes automated summary metrics, spending breakdown, and audit notes.\n\n"
                f"Regards,\n"
                f"StatementForge Intelligence Team"
            )
        elif "DUPLICATE" in report_type.upper():
            subject = f"StatementForge - Duplicate Transaction Report - {period_str}"
            body = (
                f"Dear Sir/Madam,\n\n"
                f"Please find attached the Duplicate Transaction & Audit Report generated using StatementForge{bank_str}.\n\n"
                f"Report Type: Duplicate Transaction Report\n"
                f"Report Period: {period_str}\n"
                f"Generated Date: {now_str}\n\n"
                f"Please inspect the identified duplicate entry clusters in the attached spreadsheet.\n\n"
                f"Regards,\n"
                f"StatementForge Audit Hub"
            )
        else:
            subject = f"StatementForge - {report_type} - {period_str}"
            body = (
                f"Dear Sir/Madam,\n\n"
                f"Please find attached the requested financial report generated using StatementForge{bank_str}.\n\n"
                f"Report Type: {report_type}\n"
                f"Report Period: {period_str}\n"
                f"Generated Date: {now_str}\n\n"
                f"Please review the attached file.\n\n"
                f"Regards,\n"
                f"StatementForge"
            )

        return subject, body

    @staticmethod
    def send_email_sync(sender_email, password, smtp_host, smtp_port, encryption_type, recipient, cc, bcc, subject, body, attachment_paths, report_type="General Report", user_id="guest"):
        """
        Executes SMTP email transmission synchronously.
        Saves result to EmailRepository.
        Returns (success: bool, message: str).
        """
        # Validate inputs
        val_ok, val_msg = EmailService.validate_inputs(recipient, sender_email, smtp_host, smtp_port, attachment_paths)
        if not val_ok:
            EmailRepository.save_email_log(
                user_id=user_id, recipient_email=recipient, cc=cc, bcc=bcc,
                subject=subject, report_type=report_type,
                attachment_name=", ".join([os.path.basename(p) for p in attachment_paths]) if attachment_paths else "",
                attachment_paths=attachment_paths, status="Failed", error_message=val_msg
            )
            return False, val_msg

        try:
            port_val = int(str(smtp_port).strip())
            
            # Construct Email Message
            msg = EmailMessage()
            msg["From"] = sender_email.strip()
            
            # Process multiple recipient addresses
            to_list = [r.strip() for r in re.split(r"[,;]", recipient) if r.strip()]
            msg["To"] = ", ".join(to_list)

            if cc and cc.strip():
                cc_list = [r.strip() for r in re.split(r"[,;]", cc) if r.strip()]
                msg["Cc"] = ", ".join(cc_list)

            if bcc and bcc.strip():
                bcc_list = [r.strip() for r in re.split(r"[,;]", bcc) if r.strip()]
                msg["Bcc"] = ", ".join(bcc_list)

            msg["Subject"] = subject.strip()
            msg.set_content(body)

            # Add Attachments
            att_names = []
            if attachment_paths:
                for path in attachment_paths:
                    if os.path.exists(path):
                        filename = os.path.basename(path)
                        att_names.append(filename)
                        
                        ctype, encoding = mimetypes.guess_type(path)
                        if ctype is None or encoding is not None:
                            ctype = 'application/octet-stream'
                        maintype, subtype = ctype.split('/', 1)

                        with open(path, 'rb') as fp:
                            file_data = fp.read()
                            msg.add_attachment(
                                file_data,
                                maintype=maintype,
                                subtype=subtype,
                                filename=filename
                            )

            # Context setup
            context = ssl.create_default_context()
            
            enc_upper = str(encryption_type).upper()
            
            # Perform SMTP connection and send
            if enc_upper == "SSL/TLS" or port_val == 465:
                with smtplib.SMTP_SSL(smtp_host.strip(), port_val, context=context, timeout=15.0) as server:
                    if password and password.strip():
                        server.login(sender_email.strip(), password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_host.strip(), port_val, timeout=15.0) as server:
                    server.ehlo()
                    if enc_upper != "NONE" and server.has_extn("STARTTLS"):
                        server.starttls(context=context)
                        server.ehlo()
                    if password and password.strip():
                        server.login(sender_email.strip(), password)
                    server.send_message(msg)

            # Log success
            EmailRepository.save_email_log(
                user_id=user_id, recipient_email=recipient, cc=cc, bcc=bcc,
                subject=subject, report_type=report_type,
                attachment_name=", ".join(att_names),
                attachment_paths=attachment_paths, status="Sent", error_message=""
            )
            return True, "✓ Report sent successfully."

        except smtplib.SMTPAuthenticationError:
            err = "Authentication failed. Please verify your sender email and App Password."
            EmailRepository.save_email_log(user_id=user_id, recipient_email=recipient, cc=cc, bcc=bcc, subject=subject, report_type=report_type, attachment_name="", attachment_paths=attachment_paths, status="Failed", error_message=err)
            return False, f"✕ {err}"
        except smtplib.SMTPConnectError:
            err = "SMTP Connection failed. Unable to reach host or port."
            EmailRepository.save_email_log(user_id=user_id, recipient_email=recipient, cc=cc, bcc=bcc, subject=subject, report_type=report_type, attachment_name="", attachment_paths=attachment_paths, status="Failed", error_message=err)
            return False, f"✕ {err}"
        except smtplib.SMTPServerDisconnected:
            err = "SMTP Server disconnected unexpectedly."
            EmailRepository.save_email_log(user_id=user_id, recipient_email=recipient, cc=cc, bcc=bcc, subject=subject, report_type=report_type, attachment_name="", attachment_paths=attachment_paths, status="Failed", error_message=err)
            return False, f"✕ {err}"
        except ssl.SSLError as e:
            err = f"SSL/TLS Encryption error: {e}"
            EmailRepository.save_email_log(user_id=user_id, recipient_email=recipient, cc=cc, bcc=bcc, subject=subject, report_type=report_type, attachment_name="", attachment_paths=attachment_paths, status="Failed", error_message=err)
            return False, f"✕ {err}"
        except Exception as e:
            err = str(e) or "An unknown SMTP network error occurred."
            EmailRepository.save_email_log(user_id=user_id, recipient_email=recipient, cc=cc, bcc=bcc, subject=subject, report_type=report_type, attachment_name="", attachment_paths=attachment_paths, status="Failed", error_message=err)
            return False, f"✕ {err}"
