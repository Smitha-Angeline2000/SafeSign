# risk_engine.py
import re
from collections import defaultdict

# Local rules and keywords (extend this list)
RULE_PATTERNS = {
    "auto_renewal": r"auto[- ]?renew|automatic\s+renewal",
    "penalty_fee": r"(penalt(y|ies)|late fee|early termination fee|termination fee)",
    "lock_in_period": r"lock[- ]?in|minim(um)?\s+(term|period)",
    "refund_restriction": r"non[- ]?refundable|no\s+refund",
    "unilateral_change": r"we\s+reserve\s+the\s+right|we\s+may\s+change|subject to change",
    "arbitration": r"arbitration|dispute\s+resolution",
    "data_sharing": r"(share your data|third[- ]party|data\s+sharing)",
    "short_notice": r"(notice\s+period\s+of\s+less\s+than\s+\d+\s+days|no\s+prior\s+notice)"
}

# Legal keywords to surface (not exhaustive)
LEGAL_KEYWORDS = [
    "penalty", "termination", "notice period", "lock-in", "auto-renewal",
    "arbitration", "indemnify", "liability", "governing law", "data sharing"
]


def detect_rules_and_keywords(text: str):
    """
    Returns a dict of matched rules (bool) and keyword counts.
    """
    found = {}
    for name, pattern in RULE_PATTERNS.items():
        found[name] = bool(re.search(pattern, text, re.IGNORECASE))

    # keyword counts (simple)
    keyword_counts = defaultdict(int)
    low = text.lower()
    for kw in LEGAL_KEYWORDS:
        if kw.lower() in low:
            keyword_counts[kw] += low.count(kw.lower())

    return {"rules": found, "keyword_counts": dict(keyword_counts)}


def combine_signals_to_score(local_signals: dict, llm_score):
    """
    Combine local rules (simple weighted sum) and LLM score (if present) into final 0-100 percentage.
    local_signals: {"rules": {...}, "keyword_counts": {...}}
    llm_score: float between 0-100 or None
    """
    rules = local_signals.get("rules", {})
    keyword_counts = local_signals.get("keyword_counts", {})

    # rule weights (tune as needed)
    weights = {
        "auto_renewal": 8,
        "penalty_fee": 12,
        "lock_in_period": 10,
        "refund_restriction": 10,
        "unilateral_change": 15,
        "arbitration": 6,
        "data_sharing": 8,
        "short_notice": 10
    }

    score = 0
    max_possible = sum(weights.values())

    for name, triggered in rules.items():
        if triggered:
            score += weights.get(name, 5)

    # keyword bump (each keyword occurrence adds a small amount)
    score += sum(min(5, cnt) for cnt in keyword_counts.values())

    # normalize to 0-100
    local_pct = int((score / (max_possible + 20)) * 100)  # +20 reserve
    local_pct = max(0, min(local_pct, 95))

    if llm_score is None:
        return local_pct

    # combine LLM estimate (50% weight on llm, 50% on local)
    combined = int((0.5 * local_pct) + (0.5 * llm_score))
    return max(0, min(combined, 100))
