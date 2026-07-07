import os
import pdfplumber

class PDFReader:
    """Utility class to read text, count pages, detect password protection, and determine PDF type."""

    @classmethod
    def get_page_count(cls, pdf_path):
        """Returns the number of pages in the PDF file."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0

    @classmethod
    def is_password_protected(cls, pdf_path):
        """
        Checks if the PDF is password-protected/encrypted.
        Returns a boolean.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if pdf.metadata and pdf.metadata.get("Encrypted") is True:
                    return True
                # Access pages to trigger decryption check if metadata doesn't show it
                _ = len(pdf.pages)
                return False
        except Exception as e:
            err_str = str(e).lower()
            if "password" in err_str or "encrypted" in err_str or "authenticate" in err_str:
                return True
            return False

    @classmethod
    def is_digital_pdf(cls, pdf_path):
        """
        Detects if the PDF is digital or scanned.
        Returns True if Digital, False if Scanned.
        Uses text density check on the first page as a heuristic.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return False
                first_page_text = pdf.pages[0].extract_text()
                if first_page_text and len(first_page_text.strip()) > 50:
                    return True
        except Exception:
            pass
        return False

    @classmethod
    def extract_text(cls, pdf_path):
        """
        Extracts all raw text from a digital PDF file page by page.
        """
        text_content = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
        except Exception as e:
            raise RuntimeError(f"Error reading PDF text: {e}")
            
        return "\n".join(text_content)
