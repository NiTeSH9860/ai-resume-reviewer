import argparse
import json
import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv , find_dotenv
from google import genai
from pypdf import PdfReader

load_dotenv(find_dotenv('.env'))

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY not found. Create a .env file with GEMINI_API_KEY=your_key_here"
    )

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"

 
# ---------------------------------------------------------------
# Sample data — replace with real resume/JD text once this works
# ---------------------------------------------------------------
 
def read_resume_file(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {file_path}")
 
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = path.read_text(encoding="utf-8")
 
    text = text.strip()
    if not text:
        raise ValueError(
            f"No extractable text found in {file_path}. "
            f"If this is a scanned/image-based PDF, text extraction won't work."
        )
    return text
 
 
def read_job_description_file(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Job description file not found: {file_path}")
 
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = path.read_text(encoding="utf-8")
 
    text = text.strip()
    if not text:
        raise ValueError(f"No extractable text found in {file_path}.")
    return text
 
# ---------------------------------------------------------------
# Prompt: force structured JSON output instead of free-form text
# ---------------------------------------------------------------
 
PROMPT_TEMPLATE = """You are an expert technical recruiter and resume reviewer.
Today's date is {today}. Use this as ground truth for what counts as
past, present, or future — your own training data may be outdated, so do
NOT assume a date is a typo or "in the future" just because it looks
recent or unfamiliar to you. Only flag a date as suspicious if it is
genuinely impossible relative to {today} (e.g. clearly after today, or
internally inconsistent with other dates on the resume).
 
Evaluate the RESUME below against the TARGET JOB DESCRIPTION.
 
Respond with ONLY valid JSON (no markdown code fences, no extra text),
matching exactly this schema:
 
{{
  "overall_fit_score": <integer 1-10>,
  "strengths": [<string>, ...],
  "gaps": [<string>, ...],
  "rewrite_suggestions": [
    {{"original": <string>, "improved": <string>, "why": <string>}}
  ]
}}
 
Guidelines:
- overall_fit_score: how well the resume matches the JD's requirements
- strengths: 2-4 concrete things the resume does well for this specific JD
- gaps: 2-4 specific missing skills, keywords, or unquantified claims
- rewrite_suggestions: pick 2-3 weak or vague bullet points from the
  resume and rewrite them. Keep "original" short (quote or closely
  paraphrase the actual bullet).
 
  CRITICAL rule for rewrites: do NOT just add stronger adjectives or
  intensifiers ("robust", "efficiently", "comprehensively", "significantly")
  without real data behind them — that makes a bullet sound more
  impressive without actually being more informative, which is a common
  and unhelpful pattern to avoid. Instead:
  - If the original already implies a measurable quantity (a count,
    percentage, time saved, scale, frequency) that isn't stated, add a
    concrete number, and mark it clearly as an ESTIMATE the candidate
    must verify, e.g. "(replace with your actual number)".
  - If no reasonable quantification is possible from the given context,
    improve the bullet by being more specific about WHAT was built/done
    and its concrete outcome, rather than reaching for vaguer, grander
    language.
  - Every "why" must name the specific concrete change made (e.g. "added
    a request-volume estimate" or "specified the exact tool used"), not
    a vague claim like "sounds more impressive."
 
RESUME:
{resume}
 
TARGET JOB DESCRIPTION:
{job_description}
"""
 
 
def review_resume(resume_text: str, job_description_text: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        resume=resume_text,
        job_description=job_description_text,
        today=date.today().isoformat(),
    )
 
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    raw_text = response.text.strip()
 
    # Defensive: strip markdown code fences if the model adds them anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[len("json"):].strip()
 
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Model did not return valid JSON. Raw response:\n{raw_text}"
        ) from e
 
 
def print_review(review: dict) -> None:
    print(f"\n=== Overall Fit Score: {review['overall_fit_score']}/10 ===\n")
 
    print("Strengths:")
    for s in review["strengths"]:
        print(f"  + {s}")
 
    print("\nGaps:")
    for g in review["gaps"]:
        print(f"  - {g}")
 
    print("\nRewrite Suggestions:")
    for i, r in enumerate(review["rewrite_suggestions"], start=1):
        print(f"\n  {i}. Original: {r['original']}")
        print(f"     Improved: {r['improved']}")
        print(f"     Why:      {r['why']}")
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Resume Reviewer")
    parser.add_argument(
        "--resume", default="data/cv_of_nitesh.pdf",
        help="Path to resume file (.pdf or .txt)"
    )
    parser.add_argument(
        "--jd", default="data/data_scientist_job_description.pdf",
        help="Path to job description file (.pdf or .txt)"
    )
    args = parser.parse_args()
 
    resume_text = read_resume_file(args.resume)
    job_description_text = read_job_description_file(args.jd)
 
    print(f"Loaded resume ({len(resume_text.split())} words) and "
          f"job description ({len(job_description_text.split())} words).")
    print("Sending to Gemini...")
 
    review = review_resume(resume_text, job_description_text)
    print_review(review)
 