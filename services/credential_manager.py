import keyring
import logging

logger = logging.getLogger("StatementForge.CredentialManager")

SERVICE_NAME = "StatementForge_SMTP"

class CredentialManager:
    """
    Secure credential manager using system keyring (Windows Credential Manager / macOS Keychain).
    Ensures SMTP passwords are never stored in plain text configuration files, SQLite, JSON,
    or source code files.
    """

    @staticmethod
    def set_password(email: str, password: str) -> bool:
        """
        Stores the SMTP password securely in the OS keychain for the given email address.
        """
        if not email or not email.strip():
            return False
        try:
            clean_email = email.strip()
            keyring.set_password(SERVICE_NAME, clean_email, password)
            logger.info(f"Successfully saved credentials in system keychain for {clean_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to store credential in system keychain: {type(e).__name__}")
            return False

    @staticmethod
    def get_password(email: str) -> str:
        """
        Retrieves the SMTP password securely from the OS keychain for the given email address.
        """
        if not email or not email.strip():
            return ""
        try:
            clean_email = email.strip()
            password = keyring.get_password(SERVICE_NAME, clean_email)
            return password or ""
        except Exception as e:
            logger.error(f"Failed to retrieve credential from system keychain: {type(e).__name__}")
            return ""

    @staticmethod
    def delete_password(email: str) -> bool:
        """
        Removes stored credentials from system keychain.
        """
        if not email or not email.strip():
            return False
        try:
            clean_email = email.strip()
            keyring.delete_password(SERVICE_NAME, clean_email)
            logger.info(f"Successfully deleted credentials from system keychain for {clean_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete credential from system keychain: {type(e).__name__}")
            return False
