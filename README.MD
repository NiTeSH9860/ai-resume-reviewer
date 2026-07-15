# AI Resume Reviewer

An LLM-powered resume reviewer that scores and critiques a resume against a target job description using Google Gemini, with structured, actionable feedback.

## Status: Day 1 — Core pipeline

Sends a resume and a target job description to Gemini and returns a structured critique:

- **Overall fit score** (1-10) against the specific job description
- **Strengths** — concrete things the resume does well for this JD
- **Gaps** — specific missing skills, keywords, or unquantified claims
- **Rewrite suggestions** — 2-3 weak bullet points rewritten to be stronger or better matched to the JD

This version runs against hardcoded sample resume/JD text (a real resume and a sample job posting) to prove the core pipeline works end-to-end before adding file input, UI, or further prompt refinement.

## How it works

1. Send a hardcoded resume and job description to Gemini (`gemini-2.5-flash`)
2. Prompt forces structured JSON output matching a fixed schema (no markdown, no free text)
3. Parse and print the critique — score, strengths, gaps, and rewrite suggestions

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
python resume_reviewer.py
```

## Tech stack

Python · Google Gemini API (`google-genai`)