# AI Resume Reviewer

An LLM-powered resume reviewer that scores and critiques a resume against a target job description using Google Gemini, with structured, actionable feedback.

## What it does

Given a resume (PDF or text) and a target job description (PDF or text), the tool sends both to Gemini and returns a structured critique:

- **Overall fit score** (1-10) against the specific job description
- **Strengths** — concrete things the resume does well for this JD
- **Gaps** — specific missing skills, keywords, or unquantified claims
- **Rewrite suggestions** — 2-3 weak bullet points rewritten to be more concrete or quantified

## Progress and findings

### Day 1 — Core pipeline
Proved the pipeline end-to-end: a resume and JD sent to Gemini, with a prompt that forces structured JSON output instead of free-form text. Ran against hardcoded sample data first.

**Finding:** without explicit constraints, the model's "improved" rewrites tended to just add stronger adjectives ("robust," "comprehensively," "efficiently") without adding any real information — technically more impressive-sounding, but not more informative.

### Day 2 — Real file input, tightened prompt, and a date-awareness fix

**Real file input.** Both `--resume` and `--jd` now accept `.pdf` or `.txt` files (via `pypdf` for extraction) instead of hardcoded sample strings.

**Tightened rewrite prompt.** The model is now explicitly instructed not to rely on vague intensifiers. Rewrites must either add a concrete number — clearly marked as an estimate for the candidate to verify — or get more specific about what was actually built. This produced noticeably better output: rewrites now name specific tools (e.g. "using scikit-learn pipelines") and include realistic placeholder metrics instead of just stronger adjectives.

**Finding: LLM temporal blind spot on recent dates.** Testing against a real resume, Gemini flagged legitimate 2025–2026 course completion dates as a "red flag" and likely typo. The model's training cutoff predates those dates, so anything recent looked impossible from its internal sense of "now" — a false positive, not an actual resume issue.

**Fix:** the prompt now explicitly passes today's real date and instructs the model to use it as ground truth rather than its own training cutoff, only flagging dates that are genuinely impossible (e.g. after today, or inconsistent with other dates on the resume). This is a good example of an LLM failure mode that's easy to miss if you only spot-check output rather than testing against real, current data.

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
python resume_reviewer.py --resume path/to/resume.pdf --jd path/to/job_description.pdf
```

Both `--resume` and `--jd` accept `.pdf` or `.txt`. Defaults point to `data/cv_of_nitesh.pdf` and `data/data_scientist_job_description.pdf` if run with no arguments.

## Tech stack

Python · Google Gemini API (`google-genai`) · pypdf