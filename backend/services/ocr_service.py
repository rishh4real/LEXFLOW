"""
services/ocr_service.py
OCR fallback for scanned PDFs using pytesseract.
"""
import pytesseract
from pdf2image import convert_from_path

def ocr_pdf(pdf_path: str) -> dict:
    sentences = []
    full_text = ""
    try:
        images = convert_from_path(pdf_path, dpi=200)
        for page_num, img in enumerate(images, start=1):
            text = pytesseract.image_to_string(img)
            full_text += text + "\n"
            for line in text.split("\n"):
                line = line.strip()
                if len(line) > 10:
                    sentences.append({"text": line, "page": page_num, "position": None})
    except Exception as e:
        print(f"OCR failed: {e}")
    return {"full_text": full_text, "sentences": sentences}
