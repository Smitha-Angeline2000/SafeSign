from fastapi import FastAPI, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import utils

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    text = await utils.extract_text(file)
    summary = utils.extract_main_points(text)
    clauses = utils.detect_clauses(text)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "text": text,
            "summary": summary,
            "clauses": clauses,
            "risk": risk
        }
    )