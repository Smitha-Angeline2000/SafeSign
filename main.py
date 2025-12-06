# main.py
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from utils import extract_text_bytes
from risk_engine import detect_rules_and_keywords, combine_signals_to_score
from ai_service import ask_gpt_for_summary_and_risk

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/analyze")
async def analyze_api(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF or image.")

    # 1) Extract text (pdfplumber, fallback to OCR)
    try:
        content_bytes = await file.read()
        text = extract_text_bytes(content_bytes, filename=file.filename)
        if not text or not text.strip():
            raise ValueError("No text extracted")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction error: {str(e)}")

    # 2) Local detection (fast)
    local_signals = detect_rules_and_keywords(text)

    # 3) Ask GPT (if API key present) to summarize + give risk estimate + highlight legal keywords
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            gpt_result = ask_gpt_for_summary_and_risk(text, local_signals)
        except Exception as e:
            # If GPT call fails, continue with local fallback
            gpt_result = {
                "summary": text[:500] + ("..." if len(text) > 500 else ""),
                "explanation": "LLM call failed: " + str(e),
                "llm_risk_score": None
            }
    else:
        gpt_result = {
            "summary": text[:500] + ("..." if len(text) > 500 else ""),
            "explanation": "No OPENAI_API_KEY configured — using local rules only.",
            "llm_risk_score": None
        }

    # 4) Combine signals into final risk %
    combined = combine_signals_to_score(local_signals, gpt_result.get("llm_risk_score"))

    # 5) Return JSON (the frontend will display everything)
    response = {
        "filename": file.filename,
        "text": text,
        "local_signals": local_signals,
        "gpt_summary": gpt_result.get("summary"),
        "gpt_explanation": gpt_result.get("explanation"),
        "gpt_risk_score": gpt_result.get("llm_risk_score"),
        "final_risk_score": combined,
    }
    return JSONResponse(response)
