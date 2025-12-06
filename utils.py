import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from io import BytesIO
import docx
import openai
import tempfile
from fastapi import UploadFile
import json

# Configure Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Set your OpenAI API key
openai.api_key = "YOUR_OPENAI_API_KEY"

# ------------------ Text Extraction ------------------
async def extract_text(uploaded_file: UploadFile):
    content = await uploaded_file.read()
    suffix = uploaded_file.filename.split('.')[-1].lower()

    # DOCX or TXT handling
    if suffix == "docx":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        return extract_docx_text(tmp_path)

    elif suffix == "txt":
        return content.decode("utf-8", errors="ignore")

    # PDF handling (with OCR fallback)
    elif suffix == "pdf":
        full_text = ""

        # 1️⃣ Try pdfplumber for selectable text
        try:
            pdf = pdfplumber.open(BytesIO(content))
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    full_text += page_text + "\n"
        except:
            pass

        # 2️⃣ If pdfplumber found nothing, fallback to OCR
        if not full_text.strip():
            images = convert_from_bytes(content)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img) + "\n"
            full_text = ocr_text

        return full_text

    else:
        return "Unsupported file type."

def extract_docx_text(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

# ------------------ GPT Summarization ------------------
def summarize_text(text: str) -> str:
    if not text.strip():
        return "No text found in document."

    prompt = f"""
    You are a legal assistant AI.
    Summarize the following legal document in **easy-to-understand language** for a non-legal person.
    Make it concise, structured, and highlight key points.

    Document:
    {text}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response['choices'][0]['message']['content']

# ------------------ Clause Detection + Risk Assessment ------------------
def detect_clauses_and_risk(text: str):
    """
    1. Detect common legal clauses using keywords.
    2. Ask GPT to provide a risk assessment percentage based on clauses.
    """

    # Step 1 — keyword-based detection
    text_lower = text.lower()
    clause_keywords = {
        "termination_clause": ["termination", "cancel", "end contract"],
        "confidentiality_clause": ["confidential", "non-disclosure", "nda"],
        "payment_terms": ["payment", "due date", "invoice", "fees"],
        "liability_clause": ["liability", "responsibility", "indemnity"],
        "dispute_resolution": ["dispute", "arbitration", "governing law"],
    }

    clauses = {}
    for clause, keywords in clause_keywords.items():
        clauses[clause] = any(word in text_lower for word in keywords)

    # Step 2 — GPT risk assessment
    prompt = f"""
    You are a legal AI assistant.
    Analyze the following legal document and its detected clauses:
    {text}

    Clauses detected:
    {clauses}

    Instructions:
    1. For each clause, provide a **risk explanation** in simple language.
    2. Calculate an **overall risk percentage** (0-100%) for this document.
    3. Return JSON with the following format:
       {{
           "risk_percentage": <int>,
           "clause_risks": {{
               "termination_clause": <string>,
               "confidentiality_clause": <string>,
               "payment_terms": <string>,
               "liability_clause": <string>,
               "dispute_resolution": <string>
           }}
       }}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        gpt_output = response['choices'][0]['message']['content']
        result = json.loads(gpt_output)
    except:
        # fallback if GPT does not return clean JSON
        result = {
            "risk_percentage": 50,
            "clause_risks": {k: "Risk analysis unavailable" for k in clauses}
        }

    # Merge detected clauses with GPT risk explanations
    final_clauses = {
        k: {"present": clauses[k], "risk": result["clause_risks"].get(k, "")} 
        for k in clauses
    }

    return final_clauses, result["risk_percentage"]
