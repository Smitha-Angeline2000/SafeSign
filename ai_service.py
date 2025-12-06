# ai_service.py
import os
import openai
import textwrap

OPENAI_KEY = os.getenv("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")
if OPENAI_KEY:
    openai.api_key = OPENAI_KEY

PROMPT_TEMPLATE = """
You are a legal-assistant. A contract or document has the following extracted text:

\"\"\"{text_snippet}\"\"\"

1) In plain, simple English (2-4 short paragraphs), summarize the main obligations and any clauses a regular non-legal person should worry about.
2) Provide a short, explicit list (3-6 bullet points) of clauses that are risky or consumer-unfriendly.
3) Provide a single numeric estimate (0-100) representing the *risk of fraud or consumer harm* present in the document based on the content above. Only output a single number on a line prefixed by "RISK_SCORE:".
4) Explain briefly (1-2 sentences) why you assigned that number.

Output JSON-like structure clearly labeled: "summary", "bullets", "risk_score", "why".
Be concise.
"""

def ask_gpt_for_summary_and_risk(full_text: str, local_signals: dict):
    """
    Sends the most relevant chunk(s) to GPT (avoid huge prompts). Returns a dict:
    {"summary": str, "explanation": str, "llm_risk_score": int or None}
    """
    if not OPENAI_KEY:
        raise RuntimeError("OpenAI API key not configured")

    # keep prompt size reasonable: take first 4000 chars + any local signals context
    snippet = full_text[:4000]
    local_info_lines = []
    rules = local_signals.get("rules", {})
    if rules:
        triggered = [k for k, v in rules.items() if v]
        if triggered:
            local_info_lines.append("Local rules triggered: " + ", ".join(triggered))
    if local_info_lines:
        snippet = "\n\n".join([snippet, "LOCAL_RULES: " + "; ".join(local_info_lines)])

    prompt = PROMPT_TEMPLATE.format(text_snippet=snippet)

    # call OpenAI ChatCompletion (gpt-3.5-turbo or gpt-4 if available)
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini" if "gpt-4o-mini" in openai.Model.list() else "gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=700,
    )

    out = resp.choices[0].message.content.strip()

    # parse for RISK_SCORE line
    risk_score = None
    explanation = ""
    summary_lines = []
    bullets = []

    for line in out.splitlines():
        line = line.strip()
        if line.upper().startswith("RISK_SCORE:"):
            try:
                risk_score = int(''.join(ch for ch in line.split(":",1)[1] if ch.isdigit()))
            except Exception:
                risk_score = None
        elif line.startswith("-") or line.startswith("•"):
            bullets.append(line.lstrip("-• ").strip())
        else:
            summary_lines.append(line)

    summary_text = "\n".join(summary_lines).strip()
    explanation = " ".join(bullets[:2]) if bullets else ""

    return {"summary": summary_text, "explanation": explanation, "llm_risk_score": risk_score}
