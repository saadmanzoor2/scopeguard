# ScopeGuard: Hacktoberfest Lahore 2026 Guide

## 1. Selected idea and why
**ScopeGuard** reads a freelancer's incoming client message and finds scope-creep risks before they quote a price.
Why it wins on the rubric: the model does ALL the language understanding (25%); the engineering is real, not a wrapper: schema-constrained output, JSON validation, retry, **quote-grounding check**, code-computed score (30%); the freelancer-privacy angle is distinct from generic summarizers (20%); freelancing is a real income path in Pakistan (15%); small repo, easy to demo (10%).
Originality note: contract/brief analyzers exist. What is distinctive here is the verified-quote workflow and fully local privacy. Do not claim "nobody has done this".

## 2. Requirement checklist
| Manual requirement | How ScopeGuard meets it |
|---|---|
| Model <= 8B | Qwen3-4B, ~4B params |
| Open-weight AI is central | Model produces every analysis field |
| Disclose model/size/runtime/integration | README "AI component" table |
| Original work | Own pipeline, grounding, scoring, UI |
| Public GitHub + license | MIT, steps in section 11 |
| Setup/test/diagrams/limits/team/acks | In README |
| No secrets | No API key at all |
| MLH fields | Section 12 |

**IMPORTANT findings:**
- The manual says build window is **2h 30m** (you said ~60 min). Plan below is 60 min, so you have spare buffer. Confirm the final deadline with organizers.
- Groq's `llama-3.1-8b-instant` (the manual's example) was **shut down on 16 Aug 2026**. Groq's remaining production models, GPT-OSS 20B/120B, are **above 8B**, so they are not eligible. That is why this project uses **local Ollama + Qwen3-4B** (the manual's other example). If organizers give you credits for an eligible hosted model, tell me and I will switch `call_model`.
- I could not run the model in my environment. The offline tests pass (8/8); the real-model tests are marked PENDING for you to run. Verify the model tag with `ollama show qwen3:4b` (should show about 4.0B parameters).

## 3. Workflow and scope
MUST: paste message, Analyze, see score + highlighted phrases + deliverables + missing info + flags + questions + draft reply.
SHOULD (only if done early): JSON download (already included), try `qwen3:1.7b` fallback.
FUTURE (not built): Roman Urdu support, multiple messages, history/database, PDF briefs, email integration, calibrated scoring.

## 4. Stack
Python, Streamlit, Requests, Ollama, Qwen3-4B. No database, no API key.

## 5. Architecture
Diagrams are in README.md (architecture, data flow, sequence). They match the code exactly: no database exists.

## 6. Folder structure
```
scopeguard/
├── app.py            # Streamlit UI
├── scopeguard.py     # core logic + model call
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── samples/ vague_brief.txt, clear_brief.txt
└── tests/ test_core.py, live_check.py
```
Full source is in the project files.

## 8-9. Run commands and 60-minute plan
**Min 0-5 (START DOWNLOAD FIRST).** Install Ollama (ollama.com, Windows installer is per-user). Then:
```
ollama pull qwen3:4b
```
Success: "success". Fail (no internet/blocked): ask organizers for Wi-Fi/mirror or a pre-downloaded model; try `ollama pull qwen3:1.7b`. (Roman Urdu: pehle download shuru karo, baqi kaam saath saath hota rahe ga.)
**Min 5-15.** Copy project folder, then:
```
cd scopeguard
python -m venv .venv
.venv\Scripts\activate        (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest -q
```
Success: `8 passed`. Fail: `pip install` error means check internet, or `python --version` must be 3.10+.
**Min 15-25.** `python tests/live_check.py`. Success: prints flags and two CHECK lines. If model is slow/odd, rerun once; if JSON errors repeat, update Ollama (needed for `think:false` and schema output).
**Min 25-35.** `streamlit run app.py`, open the browser link, click **Load vague brief** then **Analyze brief**. Success: sidebar green, report appears in 10-60 s.
**Min 35-45.** Edit README: fill test table with REAL results, team names. Take 2 screenshots, put in `docs/` and link in README (optional).
**Min 45-55.** Git push (section 11), verify public.
**Min 55-60.** Rehearse demo twice. If time runs short: skip screenshots, skip fallback model; never skip the live test or the push.

## 10. Troubleshooting
- "Cannot reach Ollama": run `ollama serve` in another terminal.
- "Model not found": `ollama pull qwen3:4b`.
- Very slow (CPU only): use shorter message; or `qwen3:1.7b` via env var.
- "Model did not return valid JSON": click Analyze again; update Ollama.
- Zero verified flags: the model paraphrased quotes and code removed them (this is the safety feature working); try again or use the vague sample.

## 11. GitHub commands
Create an EMPTY public repo on github.com named `scopeguard` (no README/license, they exist already), copy its URL.
```
git init
git add .
git status            # confirm no .env or .venv listed
git commit -m "ScopeGuard: local AI scope-creep analyzer"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/scopeguard.git
git push -u origin main
```
Verify: open the repo URL in a private/incognito window (should open without login), README diagrams render, LICENSE shows, and search the repo for "key", "token", "password" (there should be none).

## 12. MLH submission (edit)
- **Title:** ScopeGuard
- **Description:** ScopeGuard helps freelancers spot scope-creep risks in vague client messages before quoting a price. A local open-weight model (Qwen3-4B, about 4B parameters, via Ollama) extracts deliverables, missing information, risky phrases and a draft clarifying reply. Code verifies that every risk quote exists in the client's message and computes the risk score, so unsupported model claims are removed. Runs fully offline.
- **GitHub link:** https://github.com/YOUR_USERNAME/scopeguard
- Use the submission URL and deadline shared by the organizers.

## 13. Demo and judges
**60-second demo:** "Freelancers often get messages like this one (show vague brief). I paste it into ScopeGuard, which runs Qwen3-4B locally via Ollama, so client data never leaves my laptop. (Click Analyze.) It gives a risk score, highlights exact risky phrases such as 'small changes whenever I want', lists what's missing before I can quote, and drafts a reply. Code checks each quote is really in the message and removes invented ones. (Load clear brief, analyze: lower score.) Model: Qwen3-4B, 4B parameters, Ollama."

**2-minute technical explanation:** The UI is Streamlit. `analyze()` validates input, sends a fixed system prompt plus the message to Ollama with a JSON schema so output is structured, and `think:false` for speed. The reply is parsed (handling fences/think tags), shape-validated, retried once if invalid. Then `ground_flags` regex-matches each quoted phrase against the original text; unmatched flags are dropped and counted. The score is computed by code from severity points and missing info. No database, no API key.

**Judge Q&A**
1. *Why this model?* 4B fits the 8B limit, runs on a laptop, follows JSON schema well enough, Apache-2.0. We did not benchmark other models.
2. *How do you handle hallucination?* Quote grounding removes invented evidence. It does not guarantee the explanation is correct; that is a limitation.
3. *Why not an API like Groq?* The manual's example Llama 8B was retired on 16 Aug 2026 and the remaining Groq models exceed 8B; local also gives privacy.
4. *What did you build vs reuse?* Reused: Qwen3, Ollama, Streamlit. Built: prompt/schema design, validation, grounding, scoring, highlighting, UI, tests, docs. (Say honestly what each teammate did and that AI coding help was used.)
5. *How tested?* 8 offline unit tests plus live checks on two samples; report actual results from README table. Not statistically evaluated.

**Simple architecture:** UI, then Python checks, then local AI, then Python checks again, then result. The AI reads; Python verifies.
**Originality:** workflow combination of local privacy + verified evidence quotes + code-owned score for a specific user group.
**Limitations and future:** small model misses risks (try larger eligible model / few-shot examples); English only (add Roman Urdu tests); score weights uncalibrated (label real briefs and tune).
**Three test cases:** vague brief (many flags, Medium/High), clear brief (lower score), Ollama stopped (clear error). Also try 5-character input.
