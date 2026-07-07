import os
import cv2
import numpy as np
import pytesseract
import pypdfium2 as pdfium

# Automatically search standard Windows installation paths for Tesseract
if os.name == 'nt':
    standard_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")
    ]
    for path in standard_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break

class OCRService:
    """Performs advanced OpenCV image preprocessing and Tesseract OCR on scanned PDFs."""

    @classmethod
    def is_tesseract_installed(cls):
        """Returns True if Tesseract OCR is installed and available in PATH."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @classmethod
    def deskew_image(cls, cv_gray):
        """
        Calculates rotation skew angle of text pixels and rotates the image to align it horizontally.
        """
        # Threshold the image to find text regions (invert so text is white on black background)
        thresh = cv2.threshold(cv_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        
        # Grab all coordinates of white pixels (the text)
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) == 0:
            return cv_gray
            
        # Get the minimum area bounding box enclosing the text points
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        
        # The angle is returned in the range [-90, 0] or similar depending on OpenCV version
        # Normalize the angle for deskewing
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        # If rotation is significant, warp the image
        if abs(angle) > 0.5:
            (h, w) = cv_gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                cv_gray, M, (w, h), 
                flags=cv2.INTER_CUBIC, 
                borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
            
        return cv_gray

    @classmethod
    def preprocess_image(cls, image_np):
        """
        Applies OpenCV image preprocessing pipeline:
        Grayscale -> Noise Removal -> Deskew -> Otsu Thresholding.
        """
        # 1. Convert to Grayscale
        if len(image_np.shape) == 3:
            if image_np.shape[2] == 4:
                gray = cv2.cvtColor(image_np, cv2.COLOR_RGBA2GRAY)
            else:
                gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np.copy()

        # 2. Noise Removal (using Median Blur with kernel size 3)
        denoised = cv2.medianBlur(gray, 3)

        # 3. Deskewing
        deskewed = cls.deskew_image(denoised)

        # 4. Otsu Thresholding
        thresh = cv2.threshold(deskewed, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        return thresh

    @classmethod
    def extract_text_from_scanned(cls, pdf_path, progress_callback=None):
        """
        Renders PDF pages as images, pre-processes with OpenCV, and runs Tesseract OCR.
        Calls progress_callback(current_page, total_pages) if provided.
        Returns the combined text extracted from all pages.
        """
        if not cls.is_tesseract_installed():
            raise RuntimeError(
                "Tesseract OCR is not installed or not in the system PATH.\n\n"
                "To process scanned PDF statements, please install Tesseract:\n"
                "• Windows: Download installer from UB Mannheim\n"
                "• macOS: Run 'brew install tesseract'"
            )

        extracted_text = []
        try:
            # Load PDF document using pypdfium2
            doc = pdfium.PdfDocument(pdf_path)
            total_pages = len(doc)
            
            for idx, page in enumerate(doc):
                # Render page at 2x scale (high resolution for OCR accuracy)
                bitmap = page.render(scale=2)
                pil_img = bitmap.to_pil()
                
                # Convert PIL image to numpy array for OpenCV
                img_np = np.array(pil_img)
                
                # Apply OpenCV preprocessing pipeline
                preprocessed = cls.preprocess_image(img_np)
                
                # Run Tesseract OCR on preprocessed image
                page_text = pytesseract.image_to_string(preprocessed)
                extracted_text.append(page_text)
                
                if progress_callback:
                    progress_callback(idx + 1, total_pages)
                    
        except Exception as e:
            if "tesseract" in str(e).lower() or "tesseractnotfounderror" in type(e).__name__.lower():
                raise RuntimeError(
                    "Tesseract OCR executable could not be run. "
                    "Please verify that the installation is complete and added to your PATH."
                )
            raise RuntimeError(f"OCR failure during text extraction: {e}")

        return "\n".join(extracted_text)
