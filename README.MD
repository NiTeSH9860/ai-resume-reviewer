# AI Resume Reviewer

An LLM-powered resume reviewer that scores and critiques a resume against a target job description using Google Gemini, with structured, actionable feedback — delivered through a Streamlit web app.

## What it does

Upload a resume (PDF or `.txt`) and paste a target job description, and Gemini returns a structured critique:

- **Overall fit score** (1-10) against the specific job description
- **Strengths** — concrete things the resume does well for this JD
- **Gaps** — specific missing skills, keywords, or unquantified claims
- **Rewrite suggestions** — 2-3 weak bullet points rewritten to be more concrete or quantified

Reviews can be downloaded as a formatted PDF report, and an optional consistency check runs the same review 3 times to check how stable the score is.

## Progress and findings

### Day 1 — Core pipeline
Proved the pipeline end-to-end: a resume and JD sent to Gemini, with a prompt that forces structured JSON output instead of free-form text.

**Finding:** without explicit constraints, the model's "improved" rewrites tended to just add stronger adjectives ("robust," "comprehensively," "efficiently") without adding any real information.

### Day 2 — Real file input, tightened prompt, and a date-awareness fix

**Real file input** — resume and JD read from `.pdf` or `.txt` files via `pypdf`.

**Tightened rewrite prompt** — rewrites must now add a concrete number (marked as an estimate to verify) or get more specific about what was actually built, instead of relying on vague intensifiers.

**Finding: LLM temporal blind spot on recent dates.** Gemini flagged legitimate 2025–2026 course dates on a real resume as a likely typo, since its training cutoff predates those dates. **Fix:** the prompt now explicitly passes today's real date and instructs the model to use it as ground truth rather than its own training cutoff.

### Day 3 — Streamlit web app

Wrapped the pipeline in a Streamlit app: file uploader for the resume, a text box for the target job description, and a "Review Resume" button that displays the critique directly in the browser. Shared logic was refactored into a standalone `reviewer.py` module, and the project was simplified to be app-only — the earlier CLI script and its sample data folder were dropped in favor of one clean entry point.

### Day 4 — Downloadable reports, consistency check, and caching

**PDF report export** — every review can be downloaded as a formatted PDF (score, strengths, gaps, rewrite suggestions), giving users a real artifact instead of just on-screen text.

**Consistency check (optional)** — a checkbox runs the same review 3 times on identical input and reports the mean score, range, and standard deviation, with a plain verdict on whether the score is stable — a sanity check on how much noise vs. signal is in a single score.

**Caching** — identical resume + JD combinations are cached (via `st.cache_data`), so accidental re-runs on the same input don't burn extra API calls. This was added directly in response to hitting a real Gemini free-tier quota limit during development.

## How it works

1. Resume is uploaded through the app (PDF via `pypdf`, or `.txt`); job description is pasted directly
2. Both are sent to Gemini (`gemini-2.5-flash`) with a prompt that forces structured JSON output matching a fixed schema and grounds the model in the actual current date
3. The app parses and displays the critique — score, strengths, gaps, and expandable rewrite suggestions
4. Results can be downloaded as a PDF, and optionally cross-checked for consistency across repeated runs

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

Python · Streamlit · Google Gemini API (`google-genai`) · pypdf · reportlab