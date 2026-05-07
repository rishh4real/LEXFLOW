"""
services/pdf_parser.py
Extract text from PDF using pdfplumber. Falls back to OCR for scanned PDFs.
"""
import os
import tempfile
import pdfplumber
from services.ocr_service import ocr_pdf

def parse_pdf(pdf_path: str) -> dict:
    """
    Parse a local PDF file path.
    """
    is_temp = False
    local_path = pdf_path
    
    if not os.path.exists(pdf_path):
        raise Exception("PDF file not found on disk.")

    sentences = []
    full_text = ""
    try:
        with pdfplumber.open(local_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                full_text += text + "\n"
                for line in text.split("\n"):
                    line = line.strip()
                    if len(line) > 10:
                        sentences.append({"text": line, "page": page_num, "position": None})
        
        # If text extraction failed, try OCR
        if len(full_text.strip()) < 50:
            result = ocr_pdf(local_path)
        else:
            result = {"full_text": full_text, "sentences": sentences}
            
    except Exception:
        result = ocr_pdf(local_path)
    finally:
        # Clean up temp file
        if is_temp and os.path.exists(local_path):
            os.remove(local_path)
            
    return result


def parse_pdf_bytes(pdf_bytes: bytes) -> dict:
    """
    Parse a PDF from in-memory bytes by writing to a temp file.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        temp_file.write(pdf_bytes)
        temp_file.flush()
        return parse_pdf(temp_file.name)
    finally:
        try:
            temp_file.close()
        except Exception:
            pass
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)
