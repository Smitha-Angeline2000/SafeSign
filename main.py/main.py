from fastapi import FastAPI, UploadFile, File, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import pdfplumber
from utils import detect_risks, summarize_text

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    pdf_bytes = await file.read()

    text = ""
    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

    risks = detect_risks(text)
    summary = summarize_text(text)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "summary": summary,
            "risks": risks,
            "full_text": text
        }
    )
