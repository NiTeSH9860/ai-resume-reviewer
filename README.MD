# AI Resume Reviewer

An LLM-powered resume reviewer that scores and critiques a resume against a target job description using Google Gemini, with structured, actionable feedback — delivered through a Streamlit web app.

## What it does

Upload a resume (PDF or `.txt`) and paste a target job description, and Gemini returns a structured critique:

- **Overall fit score** (1-10) against the specific job description
- **Strengths** — concrete things the resume does well for this JD
- **Gaps** — specific missing skills, keywords, or unquantified claims
- **Rewrite suggestions** — 2-3 weak bullet points rewritten to be more concrete or quantified

## Progress and findings

### Day 1 — Core pipeline
Proved the pipeline end-to-end: a resume and JD sent to Gemini, with a prompt that forces structured JSON output instead of free-form text. Ran against hardcoded sample data first.

**Finding:** without explicit constraints, the model's "improved" rewrites tended to just add stronger adjectives ("robust," "comprehensively," "efficiently") without adding any real information — technically more impressive-sounding, but not more informative.

### Day 2 — Real file input, tightened prompt, and a date-awareness fix

**Real file input.** Resume and job description could be read from `.pdf` or `.txt` files (via `pypdf` for extraction) instead of hardcoded sample strings.

**Tightened rewrite prompt.** The model is explicitly instructed not to rely on vague intensifiers. Rewrites must either add a concrete number — clearly marked as an estimate for the candidate to verify — or get more specific about what was actually built. This produced noticeably better output: rewrites now name specific tools (e.g. "using scikit-learn pipelines") and include realistic placeholder metrics instead of just stronger adjectives.

**Finding: LLM temporal blind spot on recent dates.** Testing against a real resume, Gemini flagged legitimate 2025–2026 course completion dates as a "red flag" and likely typo. The model's training cutoff predates those dates, so anything recent looked impossible from its internal sense of "now" — a false positive, not an actual resume issue.

**Fix:** the prompt now explicitly passes today's real date and instructs the model to use it as ground truth rather than its own training cutoff, only flagging dates that are genuinely impossible (e.g. after today, or inconsistent with other dates on the resume).

### Day 3 — Streamlit web app

Wrapped the proven pipeline in a Streamlit app: file uploader for the resume, a text box to paste the target job description, and a "Review Resume" button that displays the structured critique (score, strengths, gaps, expandable rewrite suggestions) directly in the browser.

Shared logic (Gemini call, prompt, file/upload readers) was refactored into a standalone `reviewer.py` module so the app has a single source of truth. The project was then simplified to be app-only — the earlier CLI script and its sample data folder were dropped in favor of one clean entry point.

## How it works

1. Resume is uploaded through the app (PDF via `pypdf`, or `.txt`); job description is pasted directly
2. Both are sent to Gemini (`gemini-2.5-flash`) with a prompt that forces structured JSON output matching a fixed schema
3. The app parses and displays the critique — score, strengths, gaps, and expandable rewrite suggestions

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_key_here
```
Get a key from [Google AI Studio](https://aistudio.google.com/apikey).

## Run it

```bash
streamlit run app.py
```

Upload your resume, paste a job description, click "Review Resume."

## Tech stack

Python · Streamlit · Google Gemini API (`google-genai`) · pypdf