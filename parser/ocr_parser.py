import os
import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image

HAS_PADDLE = False
HAS_EASYOCR = False
HAS_TESSERACT = False

try:
    from paddleocr import PaddleOCR
    HAS_PADDLE = True
except ImportError:
    pass

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    pass

try:
    import pytesseract
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
    pytesseract.get_tesseract_version()
    HAS_TESSERACT = True
except Exception:
    pass


class OCRParser:
    """Performs advanced OpenCV image preprocessing and handles multi-engine OCR fallback (PaddleOCR -> EasyOCR -> Tesseract)."""

    _easyocr_reader = None
    _paddleocr_engine = None

    @classmethod
    def get_paddle_engine(cls):
        if cls._paddleocr_engine is None and HAS_PADDLE:
            try:
                cls._paddleocr_engine = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)
            except Exception as e:
                print(f"PaddleOCR init failed: {e}")
        return cls._paddleocr_engine

    @classmethod
    def get_easyocr_reader(cls):
        if cls._easyocr_reader is None and HAS_EASYOCR:
            try:
                cls._easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            except Exception as e:
                print(f"EasyOCR init failed: {e}")
        return cls._easyocr_reader

    @classmethod
    def deskew_image(cls, cv_gray):
        """Rotates skewed text horizontally."""
        thresh = cv2.threshold(cv_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) == 0:
            return cv_gray
            
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
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
    def preprocess_image(cls, pil_img):
        """
        Applies OpenCV image preprocessing pipeline:
        Grayscale -> Median Denoise -> Deskew -> CLAHE Contrast Enhancement -> Adaptive Thresholding.
        """
        img_np = np.array(pil_img)
        
        # 1. Grayscale
        if len(img_np.shape) == 3:
            if img_np.shape[2] == 4:
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
            else:
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np.copy()

        # 2. Denoise
        denoised = cv2.medianBlur(gray, 3)

        # 3. Deskew
        deskewed = cls.deskew_image(denoised)

        # 4. Contrast Enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(deskewed)

        # 5. Adaptive Thresholding
        thresh = cv2.adaptiveThreshold(
            contrast_enhanced, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        return thresh

    @classmethod
    def render_pdf_page_to_pil(cls, pdf_path, page_num):
        """Renders page_num (0-indexed) of pdf_path as a PIL Image."""
        doc = pdfium.PdfDocument(pdf_path)
        if page_num < 0 or page_num >= len(doc):
            raise IndexError("Page index out of range")
        page = doc[page_num]
        bitmap = page.render(scale=2.5)
        return bitmap.to_pil()

    @classmethod
    def extract_text_blocks(cls, pdf_path, page_num, logger=None):
        """
        Runs OCR on preprocessed page image and returns a list of dictionaries with text and coordinate boxes.
        Format: [{"text": str, "x0": float, "y0": float, "x1": float, "y1": float}]
        """
        pil_img = cls.render_pdf_page_to_pil(pdf_path, page_num)
        preprocessed = cls.preprocess_image(pil_img)
        
        # 1. PaddleOCR
        paddle_eng = cls.get_paddle_engine()
        if paddle_eng:
            if logger:
                logger.log(f"OCR: Running PaddleOCR for page {page_num + 1}...")
            try:
                result = paddle_eng.ocr(preprocessed, cls=True)
                blocks = []
                if result and result[0]:
                    for line in result[0]:
                        box = line[0]
                        text, conf = line[1]
                        x0 = min(pt[0] for pt in box)
                        y0 = min(pt[1] for pt in box)
                        x1 = max(pt[0] for pt in box)
                        y1 = max(pt[1] for pt in box)
                        blocks.append({"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1})
                return blocks
            except Exception as e:
                if logger:
                    logger.log(f"PaddleOCR failure: {e}. Trying fallback EasyOCR...")

        # 2. EasyOCR
        easy_reader = cls.get_easyocr_reader()
        if easy_reader:
            if logger:
                logger.log(f"OCR: Running EasyOCR fallback for page {page_num + 1}...")
            try:
                result = easy_reader.readtext(preprocessed)
                blocks = []
                for box, text, conf in result:
                    x0 = min(pt[0] for pt in box)
                    y0 = min(pt[1] for pt in box)
                    x1 = max(pt[0] for pt in box)
                    y1 = max(pt[1] for pt in box)
                    blocks.append({"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1})
                return blocks
            except Exception as e:
                if logger:
                    logger.log(f"EasyOCR failure: {e}. Trying fallback Tesseract...")

        # 3. Tesseract OCR
        if HAS_TESSERACT:
            if logger:
                logger.log(f"OCR: Running Tesseract fallback for page {page_num + 1}...")
            try:
                data = pytesseract.image_to_data(preprocessed, output_type=pytesseract.Output.DICT)
                blocks = []
                n_boxes = len(data['text'])
                for i in range(n_boxes):
                    text = data['text'][i].strip()
                    if text:
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        blocks.append({"text": text, "x0": float(x), "y0": float(y), "x1": float(x+w), "y1": float(y+h)})
                return blocks
            except Exception as e:
                if logger:
                    logger.log(f"Tesseract failure: {e}")
                
        raise RuntimeError("No OCR Engine available or all OCR engines failed.")

    @classmethod
    def extract_raw_text(cls, pdf_path, page_num, logger=None):
        """Extracts text string from preprocessed page image."""
        blocks = cls.extract_text_blocks(pdf_path, page_num, logger)
        if not blocks:
            return ""
            
        blocks_sorted = sorted(blocks, key=lambda b: (b['y0'], b['x0']))
        lines = []
        current_line = []
        current_y = -999.0
        
        for b in blocks_sorted:
            if current_y == -999.0:
                current_y = b['y0']
                current_line.append(b)
            elif abs(b['y0'] - current_y) < 15:
                current_line.append(b)
            else:
                current_line_sorted = sorted(current_line, key=lambda x: x['x0'])
                lines.append(" ".join(x['text'] for x in current_line_sorted))
                current_line = [b]
                current_y = b['y0']
                
        if current_line:
            current_line_sorted = sorted(current_line, key=lambda x: x['x0'])
            lines.append(" ".join(x['text'] for x in current_line_sorted))
            
        return "\n".join(lines)
