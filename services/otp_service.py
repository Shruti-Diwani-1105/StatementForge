import os
import time
import random
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyQt6.QtCore import QThread, pyqtSignal
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class SendOTPWorker(QThread):
    """
    Background worker thread to send the OTP email via SMTP.
    This prevents blocking the PyQt UI thread during the network request.
    """
    finished = pyqtSignal(bool, str)  # (success, message)

    def __init__(self, email: str, otp: str, action_type: str = "reset"):
        super().__init__()
        self.email = email.strip().lower()
        self.otp = otp
        self.action_type = action_type

    def run(self):
        sender_email = os.getenv("SMTP_SENDER_EMAIL")
        sender_password = os.getenv("SMTP_SENDER_PASSWORD")

        if not sender_email or not sender_password:
            self.finished.emit(False, "SMTP credentials are missing from the configuration.")
            return

        smtp_server = "smtp.gmail.com"
        port = 465  # SSL port

        if self.action_type == "login":
            subject = f"StatementForge - Login Verification Code: {self.otp}"
            text_content = (
                f"Your StatementForge login verification code is: {self.otp}\n\n"
                f"Please enter code {self.otp} in the application to complete your first-time login.\n"
                f"This code is valid for 5 minutes."
            )
            action_title = "First-Time Login Verification"
            action_desc = f"To complete your first-time login for <b>{self.email}</b>, use the 6-digit verification code below:"
        else:
            subject = f"StatementForge - Verification Code: {self.otp}"
            text_content = (
                f"Your StatementForge password reset verification code is: {self.otp}\n\n"
                f"Please enter code {self.otp} in the application to reset your password.\n"
                f"This code is valid for 5 minutes."
            )
            action_title = "Your Verification Code"
            action_desc = f"You requested a password reset for <b>{self.email}</b>. Use the 6-digit verification code below:"

        # Create message container
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"StatementForge Support <{sender_email}>"
        msg["To"] = self.email

        html_content = f"""
        <html>
          <body style="font-family: 'Times New Roman', Times, Georgia, serif; background-color: #F8FAFC; color: #1E293B; padding: 40px 20px; margin: 0;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
              <!-- Header -->
              <div style="background-color: #0037b0; padding: 24px; text-align: center; color: #FFFFFF;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">StatementForge</h1>
              </div>
              <!-- Body -->
              <div style="padding: 32px 24px;">
                <h2 style="margin-top: 0; font-size: 18px; font-weight: 600; color: #0F172A;">{action_title}</h2>
                <p style="font-size: 14px; line-height: 1.6; color: #64748B;">
                  {action_desc}
                </p>
                <div style="background-color: #EFF6FF; border: 2px dashed #0037b0; border-radius: 8px; padding: 20px; margin: 24px 0; text-align: center;">
                  <span style="font-size: 36px; font-weight: 900; letter-spacing: 8px; color: #0037b0; font-family: monospace;">{self.otp}</span>
                </div>
                <p style="font-size: 13px; color: #64748B; text-align: center; margin-bottom: 0;">
                  This code is valid for <b>5 minutes</b>.
                </p>
              </div>
              <!-- Footer -->
              <div style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px; text-align: center; font-size: 11px; color: #94A3B8;">
                &copy; 2026 StatementForge Inc. All rights reserved.
              </div>
            </div>
          </body>
        </html>
        """

        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        msg.attach(part1)
        msg.attach(part2)

        try:
            # Try to build a secure SSL context; fallback to unverified context if macOS certificates are missing
            try:
                context = ssl.create_default_context()
            except Exception:
                context = ssl._create_unverified_context()

            success = False
            smtp_err = ""

            # Try Port 465 SSL first
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=8) as server:
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, self.email, msg.as_string())
                success = True
            except Exception as e:
                smtp_err = str(e)
                print(f"SMTP Port 465 failed: {e}. Trying Port 587 STARTTLS...")

            # Fallback to Port 587 STARTTLS if SSL fails (common when ISPs block Port 465)
            if not success:
                try:
                    with smtplib.SMTP("smtp.gmail.com", 587, timeout=8) as server:
                        server.starttls(context=context)
                        server.login(sender_email, sender_password)
                        server.sendmail(sender_email, self.email, msg.as_string())
                    success = True
                except Exception as e:
                    smtp_err = f"Port 465 SSL failed ({smtp_err}); Port 587 STARTTLS failed ({str(e)})"

            if success:
                self.finished.emit(True, "OTP email sent successfully.")
            else:
                self.finished.emit(False, f"SMTP Error: {smtp_err}")
        except Exception as e:
            self.finished.emit(False, f"SMTP Worker General Error: {str(e)}")


class OTPService:
    # Class-level dictionary storing active OTPs
    # Format: { email.lower(): { "otp": str, "expires_at": float } }
    _active_otps = {}
    
    # OTP validity duration (e.g. 5 minutes)
    OTP_EXPIRY_SECONDS = 300

    @classmethod
    def generate_otp(cls, email: str) -> str:
        """
        Generates a 6-digit random OTP and stores it with an expiry timestamp.
        """
        email_clean = email.strip().lower()
        otp = f"{random.randint(100000, 999999):06d}"
        
        expires_at = time.time() + cls.OTP_EXPIRY_SECONDS
        cls._active_otps[email_clean] = {
            "otp": otp,
            "expires_at": expires_at
        }
        
        # Log to console for debugging and testing purposes
        print(f"[OTP Service] Generated OTP for {email_clean}: {otp} (Expires at {time.strftime('%H:%M:%S', time.localtime(expires_at))})")
        return otp

    @classmethod
    def verify_otp(cls, email: str, code: str) -> tuple[bool, str]:
        """
        Verifies the provided OTP for the given email.
        Returns (success_bool, message_str).
        """
        email_clean = email.strip().lower()
        code_clean = code.strip()
        
        if not email_clean:
            return False, "Email address is required."
        if not code_clean:
            return False, "OTP code is required."
            
        record = cls._active_otps.get(email_clean)
        if not record:
            return False, "No OTP requested or OTP has expired. Please send a new code."
            
        # Check expiry
        if time.time() > record["expires_at"]:
            # Clean up expired OTP
            cls._active_otps.pop(email_clean, None)
            return False, "The verification code has expired. Please request a new one."
            
        if record["otp"] != code_clean:
            return False, "Incorrect verification code. Please check and try again."
            
        # Success - consume the OTP so it can't be reused
        cls._active_otps.pop(email_clean, None)
        return True, "Verification successful!"
