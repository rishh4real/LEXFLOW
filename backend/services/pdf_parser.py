"""
services/pdf_parser.py
Extract text from PDF using pdfplumber. Falls back to OCR for scanned PDFs.
"""
import pdfplumber
from services.ocr_service import ocr_pdf

def parse_pdf(pdf_path: str) -> dict:
    sentences = []
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                full_text += text + "\n"
                for line in text.split("\n"):
                    line = line.strip()
                    if len(line) > 10:
                        sentences.append({"text": line, "page": page_num, "position": None})
        if len(full_text.strip()) < 50:
            return ocr_pdf(pdf_path)
    except Exception:
        return ocr_pdf(pdf_path)
    return {"full_text": full_text, "sentences": sentences}
