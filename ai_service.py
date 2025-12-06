# ai_service.py
import os
import openai
import json

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_KEY:
    openai.api_key = OPENAI_KEY


# -------------------------------
# New Strong Prompt
# -------------------------------
PROMPT_TEMPLATE = """
You are a legal assistant. A contract/document has the following extracted text:

\"\"\"{text_snippet}\"\"\"

Your tasks:

1) Produce a clear **summary in exactly 5 short paragraphs**, written in plain English so a non-legal reader can easily understand the obligations, responsibilities, risks, and overall intent of the document. 
   - Each paragraph must be 3–4 concise sentences.
   - DO NOT repeat the document verbatim.
   - DO NOT exceed 5 paragraphs.

2) Provide **3–6 bullet points** listing risky, unfair, unclear, or consumer-unfriendly clauses.

3) Assign a **numeric fraud/risk score (0–100)**. Output a single line as:
   RISK_SCORE: <number>

4) Give **1–2 sentences** explaining why that score was assigned.

Return your output ONLY as a JSON-like object with these keys:
{
  "summary": "...5 paragraphs...",
  "bullets": [...],
  "risk_score": <number>,
  "why": "..."
}
"""


# -------------------------------
# GPT Call Function
# -------------------------------
def ask_gpt_for_summary_and_risk(full_text: str, local_signals: dict):
    if not OPENAI_KEY:
        raise RuntimeError("OpenAI API key not configured")

    # send larger snippet safely
    snippet = full_text[:8000]

    # include triggered local rules
    rules = local_signals.get("rules", {})
    triggered = [k for k, v in rules.items() if v]
    if triggered:
        snippet += "\n\nLOCAL_RULES_TRIGGERED: " + ", ".join(triggered)

    prompt = PROMPT_TEMPLATE.format(text_snippet=snippet)

    # Choose model properly
    try:
        available_models = [m.id for m in openai.models.list().data]
        if "gpt-4o-mini" in available_models:
            model_name = "gpt-4o-mini"
        else:
            model_name = "gpt-4o" if "gpt-4o" in available_models else "gpt-3.5-turbo"
    except:
        model_name = "gpt-4o-mini"

    response = openai.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=900,
    )

    raw = response.choices[0].message.content.strip()

    # -------------------------------
    # Extract JSON-like structure
    # -------------------------------
    # Attempt to locate braces
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        json_part = raw[start:end + 1]
    else:
        json_part = raw  # fallback

    # Clean invalid JSON trailing commas
    json_part = json_part.replace("\n", " ").replace("\r", " ")

    # Try actual JSON decoding
    try:
        data = json.loads(json_part)
    except:
        # fallback manual parsing
        data = {
            "summary": "",
            "bullets": [],
            "risk_score": None,
            "why": ""
        }

        # extract RISK_SCORE
        for line in raw.splitlines():
            if line.upper().startswith("RISK_SCORE"):
                try:
                    data["risk_score"] = int(
                        "".join(ch for ch in line if ch.isdigit())
                    )
                except:
                    data["risk_score"] = None

        # bullets
        bullets = []
        for line in raw.splitlines():
            if line.strip().startswith(("-", "•", "*")):
                bullets.append(line.strip("-•* ").strip())
        data["bullets"] = bullets

        # summary fallback
        data["summary"] = raw

        # why fallback
        if bullets:
            data["why"] = bullets[0]

    # -------------------------------
    # Force summary into 5 paragraphs
    # -------------------------------
    summary = data.get("summary", "")

    # break on double newlines or periods
    parts = [p.strip() for p in summary.split("\n") if p.strip()]
    if len(parts) < 5:
        # try splitting by sentences
        sentences = summary.replace("\n", " ").split(".")
        sentences = [s.strip() for s in sentences if s.strip()]
        paragraphs = []
        chunk = []

        for s in sentences:
            chunk.append(s + ".")
            if len(chunk) == 3:  # 3 sentences per paragraph
                paragraphs.append(" ".join(chunk))
                chunk = []

        if chunk:
            paragraphs.append(" ".join(chunk))

        summary = "\n\n".join(paragraphs[:5])
    else:
        summary = "\n\n".join(parts[:5])

    # -------------------------------
    # Final Clean Return
    # -------------------------------
    return {
        "summary": summary,
        "bullets": data.get("bullets", []),
        "llm_risk_score": data.get("risk_score"),
        "explanation": data.get("why", "")
    }
