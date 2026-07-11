import re
import os

class ValidationService:
    """
    Validation logic for individual settings fields.
    Returns (is_valid, error_message).
    """
    
    @staticmethod
    def validate_email(email):
        """Validates standard email format."""
        if not email or not email.strip():
            return False, "Email address is required."
        email_clean = email.strip()
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, email_clean):
            return False, "Invalid Email address format."
        return True, ""

    @staticmethod
    def validate_gemini_api(api_key, ai_enabled):
        """Validates Gemini API Key constraint based on toggle state."""
        if ai_enabled:
            if not api_key or not api_key.strip():
                return False, "Empty API Key. Please provide a key when Google Gemini is enabled."
        return True, ""

    @staticmethod
    def validate_mongodb_uri(uri):
        """Validates MongoDB Atlas URI prefix format."""
        if not uri or not uri.strip():
            return False, "MongoDB URI cannot be empty."
        uri_clean = uri.strip()
        if not (uri_clean.startswith("mongodb://") or uri_clean.startswith("mongodb+srv://")):
            return False, "Invalid MongoDB URI (must start with mongodb:// or mongodb+srv://)."
        return True, ""

    @staticmethod
    def validate_save_folder(folder):
        """Validates that a save folder path is non-empty."""
        if not folder or not folder.strip():
            return False, "Missing Save Folder location."
        # Note: We do not check os.path.exists() strictly to allow creating folders on the fly during saves,
        # but we could verify format.
        return True, ""

    @staticmethod
    def validate_smtp_port(port):
        """Validates SMTP Port numbers."""
        if not port:
            return False, "Invalid SMTP Port."
        port_str = str(port).strip()
        if not port_str.isdigit():
            return False, "Invalid SMTP Port (must be numeric)."
        val = int(port_str)
        if val < 1 or val > 65535:
            return False, "Invalid SMTP Port (must be between 1 and 65535)."
        return True, ""

    @staticmethod
    def validate_smtp_server(server):
        """Validates SMTP Server host name."""
        if not server or not server.strip():
            return False, "SMTP Server is required."
        return True, ""

    @staticmethod
    def validate_application_name(name):
        """Validates application name."""
        if not name or not name.strip():
            return False, "Application name cannot be empty."
        return True, ""
        
    @staticmethod
    def validate_name(name):
        """Validates account full name."""
        if not name or not name.strip():
            return False, "Name is required."
        if len(name.strip()) < 3:
            return False, "Name must be at least 3 characters."
        return True, ""
        
    @staticmethod
    def validate_phone(phone):
        """Validates account phone format (Indian 10-digit format)."""
        if not phone or not phone.strip():
            return False, "Phone number is required."
        phone_clean = phone.strip()
        if not phone_clean.isdigit():
            return False, "Phone number must contain digits only."
        if len(phone_clean) != 10:
            return False, "Phone number must contain exactly 10 digits."
        return True, ""
