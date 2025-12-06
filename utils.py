# utils.py
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from io import BytesIO
from PIL import Image

# If Windows and Tesseract installed in Program Files, uncomment and set path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_bytes(file_bytes: bytes, filename: str = "file"):
    """
    Try pdfplumber for text (for selectable PDFs). If no text, fallback to OCR via pdf2image+pytesseract.
    Returns the concatenated text of all pages.
    """
    text = ""

    lower = filename.lower()
    try:
        if lower.endswith(".pdf"):
            # Use pdfplumber on bytes
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        pages_text.append(extracted)
                text = "\n\n".join(pages_text).strip()
        else:
            # images: direct OCR
            image = Image.open(BytesIO(file_bytes))
            text = pytesseract.image_to_string(image).strip()
    except Exception:
        # fallback to OCR if pdfplumber failed or returned empty
        text = ""

    # If no text found using pdfplumber, use OCR fallback (for scanned PDFs)
    if not text:
        try:
            images = convert_from_bytes(file_bytes)
            ocr_pages = []
            for img in images:
                ocr_pages.append(pytesseract.image_to_string(img))
            text = "\n\n".join(ocr_pages).strip()
        except Exception as e:
            # re-raise after failing both
            raise RuntimeError(f"OCR fallback failed: {e}")

    return text
