"""ScopeGuard core logic: input validation, local-model call, JSON validation,
quote grounding (anti-hallucination) and deterministic risk scoring."""
import html
import json
import os
import re

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")  # Qwen3-4B, ~4.0B parameters
MIN_CHARS, MAX_CHARS = 30, 6000

CATEGORIES = ["vague_scope", "unlimited_revisions", "unpaid_extras",
              "tight_deadline", "unclear_budget", "unclear_ownership", "other"]
SEVERITIES = ["low", "medium", "high"]
POINTS = {"low": 8, "medium": 15, "high": 25}

SCHEMA = {
    "type": "object",
    "properties": {
        "project_summary": {"type": "string"},
        "deliverables": {"type": "array", "items": {"type": "string"}},
        "missing_info": {"type": "array", "items": {"type": "string"}},
        "risk_flags": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "quote": {"type": "string"},
                "category": {"type": "string", "enum": CATEGORIES},
                "severity": {"type": "string", "enum": SEVERITIES},
                "why": {"type": "string"},
            },
            "required": ["quote", "category", "severity", "why"]}},
        "clarifying_questions": {"type": "array", "items": {"type": "string"}},
        "draft_reply": {"type": "string"},
    },
    "required": ["project_summary", "deliverables", "missing_info",
                 "risk_flags", "clarifying_questions", "draft_reply"],
}

SYSTEM_PROMPT = """You are ScopeGuard, an assistant for freelancers. You read ONE client message describing a project and return a JSON analysis.
Rules:
- Use ONLY information in the client message. Never invent requirements, prices or dates.
- risk_flags: every flag must have a "quote" copied EXACTLY, word for word, from the client message (max 20 words). If you cannot quote it, do not flag it.
- category must be one of: vague_scope, unlimited_revisions, unpaid_extras, tight_deadline, unclear_budget, unclear_ownership, other.
- severity must be low, medium or high.
- deliverables: concrete things the client asked for.
- missing_info: facts a freelancer must know before quoting a price (pages, deadline, budget, tech stack, content, etc.) that the message does not give.
- clarifying_questions: 3 to 6 short, polite questions.
- draft_reply: a polite professional reply under 120 words that thanks the client, restates the scope in your own words, and asks the clarifying questions. Do not promise a price.
- Return JSON only."""


class ScopeGuardError(Exception):
    """Any user-facing error (bad input, model offline, invalid model output)."""


def validate_input(text):
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'") \
        .replace("\u201c", '"').replace("\u201d", '"').strip()
    if len(text) < MIN_CHARS:
        raise ScopeGuardError(f"Please paste a real client message (at least {MIN_CHARS} characters).")
    if len(text) > MAX_CHARS:
        raise ScopeGuardError(f"Message is too long ({len(text)} chars). Maximum is {MAX_CHARS}.")
    return text


def check_model():
    """Returns (ok, message). Used by the sidebar status."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
    except requests.RequestException:
        return False, "Ollama is not running. Start it (run `ollama serve`) and refresh."
    if not any(n == MODEL or n.startswith(MODEL + ":") for n in names):
        return False, f"Model '{MODEL}' not found. Run: ollama pull {MODEL}"
    return True, f"Ollama running, model '{MODEL}' ready."


def call_model(brief, timeout=240):
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": "CLIENT MESSAGE:\n" + brief}],
        "stream": False,
        "think": False,          # Qwen3: skip long reasoning, we need JSON fast
        "format": SCHEMA,        # Ollama structured output (JSON schema)
        "options": {"temperature": 0.2, "num_ctx": 6144},
    }
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
    except requests.ConnectionError:
        raise ScopeGuardError("Cannot reach Ollama. Start it with `ollama serve`.")
    except requests.Timeout:
        raise ScopeGuardError("The model took too long. Try a shorter message or a smaller model.")
    if r.status_code == 404:
        raise ScopeGuardError(f"Model '{MODEL}' not found. Run: ollama pull {MODEL}")
    if r.status_code != 200:
        raise ScopeGuardError(f"Ollama error {r.status_code}: {r.text[:200]}")
    return r.json().get("message", {}).get("content", "")


def extract_json(raw):
    raw = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL).strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e > s:
            try:
                return json.loads(raw[s:e + 1])
            except json.JSONDecodeError:
                pass
    raise ScopeGuardError("Model did not return valid JSON.")


def normalize(data):
    """Validate the shape of the model output. Raises if unusable."""
    if not isinstance(data, dict):
        raise ScopeGuardError("Model output is not a JSON object.")
    out = {"project_summary": str(data.get("project_summary", "")).strip(),
           "draft_reply": str(data.get("draft_reply", "")).strip()}
    for key in ("deliverables", "missing_info", "clarifying_questions"):
        v = data.get(key, [])
        if not isinstance(v, list):
            raise ScopeGuardError(f"Model output field '{key}' is not a list.")
        out[key] = [str(x).strip() for x in v if str(x).strip()]
    rf = data.get("risk_flags", [])
    if not isinstance(rf, list):
        raise ScopeGuardError("Model output field 'risk_flags' is not a list.")
    flags = []
    for f in rf:
        if not isinstance(f, dict):
            continue
        cat = f.get("category", "other")
        sev = f.get("severity", "medium")
        flags.append({"quote": str(f.get("quote", "")).strip(),
                      "category": cat if cat in CATEGORIES else "other",
                      "severity": sev if sev in SEVERITIES else "medium",
                      "why": str(f.get("why", "")).strip()})
    out["risk_flags"] = flags
    if not out["project_summary"] and not out["deliverables"]:
        raise ScopeGuardError("Model returned an empty analysis.")
    return out


def find_span(brief, quote):
    """Locate the quote inside the brief (whitespace/case tolerant). None if absent."""
    words = quote.strip(" \"'").split()
    if len(" ".join(words)) < 4:
        return None
    pattern = r"\s+".join(re.escape(w) for w in words)
    m = re.search(pattern, brief, re.IGNORECASE)
    return (m.start(), m.end()) if m else None


def ground_flags(brief, flags):
    """Keep only flags whose quote really exists in the client message."""
    kept, dropped = [], 0
    for f in flags:
        span = find_span(brief, f["quote"])
        if span:
            kept.append({**f, "span": span})
        else:
            dropped += 1
    return kept, dropped


def risk_score(flags, missing_info):
    total = sum(POINTS[f["severity"]] for f in flags) + 4 * len(missing_info)
    score = min(100, total)
    level = "Low" if score < 25 else "Medium" if score < 55 else "High"
    return score, level


def highlight_html(brief, flags):
    spans = sorted(f["span"] for f in flags)
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    out, pos = [], 0
    for s, e in merged:
        out.append(html.escape(brief[pos:s]))
        out.append("<mark>" + html.escape(brief[s:e]) + "</mark>")
        pos = e
    out.append(html.escape(brief[pos:]))
    return "".join(out).replace("\n", "<br>")


def analyze(text):
    brief = validate_input(text)
    last_err = None
    for _ in range(2):  # one retry if the model returns bad JSON
        try:
            data = normalize(extract_json(call_model(brief)))
            break
        except ScopeGuardError as e:
            last_err = e
            if "Ollama" in str(e) or "Model '" in str(e) or "too long" in str(e):
                raise
    else:
        raise last_err
    flags, dropped = ground_flags(brief, data["risk_flags"])
    score, level = risk_score(flags, data["missing_info"])
    return {**data, "brief": brief, "risk_flags": flags, "dropped_flags": dropped,
            "score": score, "level": level, "highlighted": highlight_html(brief, flags),
            "model": MODEL}
