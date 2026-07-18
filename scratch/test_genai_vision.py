import sys
sys.path.append('.')
import io
from PIL import Image
from services.gemini_service import GeminiService
from parser.ocr_parser import OCRParser
from google.genai import types

try:
    pdf_path = "D:/Kotak Mahindra Somaiya.pdf"
    print("Rendering page 1...")
    pil_image = OCRParser.render_pdf_page_to_pil(pdf_path, 0)
    
    # Convert PPM image to standard PNG bytes
    print("Converting PPM image to PNG bytes...")
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()
    
    print("Calling GeminiService.get_client()...")
    client = GeminiService.get_client()
    prompt = GeminiService._get_prompt()
    
    print("Calling generate_content with Part.from_bytes...")
    img_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1
    )
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, img_part],
        config=config
    )
    print("Success with Part.from_bytes! Response text:")
    print(response.text[:200])
    
    print("\n--- Trying standard PngImageFile ---")
    buffer.seek(0)
    png_image = Image.open(buffer)
    response2 = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, png_image],
        config=config
    )
    print("Success with standard PngImageFile! Response text:")
    print(response2.text[:200])
    
except Exception as e:
    import traceback
    traceback.print_exc()
