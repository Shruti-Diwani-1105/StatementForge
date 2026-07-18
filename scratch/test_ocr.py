import sys
sys.path.append('.')
import cv2
import numpy as np
from PIL import Image
from parser.ocr_parser import OCRParser
import easyocr

pdf_path = "D:/Kotak Mahindra Somaiya.pdf"
print("Rendering page 0...")
pil_img = OCRParser.render_pdf_page_to_pil(pdf_path, 0)

print("Running OCR on raw image...")
reader = easyocr.Reader(['en'], gpu=False)
raw_np = np.array(pil_img)
raw_result = reader.readtext(raw_np)
print(f"Raw image word count: {len(raw_result)}")
if raw_result:
    print("Sample raw text words:")
    for box, text, conf in raw_result[:20]:
        print(f"  {text} (conf: {conf:.2f})")

print("\nPreprocessing image...")
preprocessed = OCRParser.preprocess_image(pil_img)

print("Running OCR on preprocessed image...")
prep_result = reader.readtext(preprocessed)
print(f"Preprocessed image word count: {len(prep_result)}")
if prep_result:
    print("Sample preprocessed text words:")
    for box, text, conf in prep_result[:20]:
        print(f"  {text} (conf: {conf:.2f})")
