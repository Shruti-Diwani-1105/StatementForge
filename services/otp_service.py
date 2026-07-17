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

    def __init__(self, email: str, otp: str):
        super().__init__()
        self.email = email
        self.otp = otp

    def run(self):
        sender_email = os.getenv("SMTP_SENDER_EMAIL")
        sender_password = os.getenv("SMTP_SENDER_PASSWORD")

        if not sender_email or not sender_password:
            self.finished.emit(False, "SMTP credentials are missing from the configuration.")
            return

        smtp_server = "smtp.gmail.com"
        port = 465  # SSL port

        # Create message container
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "StatementForge - Password Reset Verification Code"
        msg["From"] = f"StatementForge Support <{sender_email}>"
        msg["To"] = self.email

        # Create standard text and beautiful HTML message bodies
        text_content = f"Your StatementForge password reset verification code is: {self.otp}\nThis code is valid for 5 minutes."
        
        html_content = f"""
        <html>
          <body style="font-family: 'Times New Roman', Times, Georgia, serif; background-color: #F8FAFC; color: #1E293B; padding: 40px 20px; margin: 0;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); overflow: hidden;">
              <!-- Header -->
              <div style="background-color: #2563EB; padding: 24px; text-align: center; color: #FFFFFF;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">StatementForge</h1>
              </div>
              <!-- Body -->
              <div style="padding: 32px 24px;">
                <h2 style="margin-top: 0; font-size: 18px; font-weight: 600; color: #0F172A;">Reset Your Password</h2>
                <p style="font-size: 14px; line-height: 1.6; color: #64748B;">
                  You requested a password reset for your StatementForge account. Use the verification code below to proceed:
                </p>
                <div style="background-color: #F1F5F9; border-radius: 8px; padding: 16px; margin: 24px 0; text-align: center;">
                  <span style="font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #2563EB; font-family: monospace;">{self.otp}</span>
                </div>
                <p style="font-size: 12px; color: #94A3B8; text-align: center; margin-bottom: 0;">
                  This code is valid for <b>5 minutes</b>. If you did not request this reset, you can safely ignore this email.
                </p>
              </div>
              <!-- Footer -->
              <div style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px; text-align: center; font-size: 11px; color: #94A3B8;">
                &copy; 2026 StatementForge. All rights reserved.
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
            # Create a secure SSL context and connect
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, port, context=context, timeout=8) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, self.email, msg.as_string())
                
            self.finished.emit(True, "OTP email sent successfully via SMTP.")
        except smtplib.SMTPAuthenticationError:
            self.finished.emit(False, "SMTP Authentication failed. Please verify your email and app passkey.")
        except Exception as e:
            self.finished.emit(False, f"SMTP Error: {str(e)}")


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
