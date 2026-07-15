import json
import os
from dotenv import load_dotenv , find_dotenv
from google import genai

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

SAMPLE_RESUME = """
Nitesh Giri
Data Scientist | AI/ML Engineer

Data Science (AI/ML) Intern, Virtuosway
- Built an LLM-powered HR conversational assistant using Google Gemini's
  function-calling API, translating natural-language queries into
  structured tool calls against a MongoDB backend.
- Built a RAG pipeline using FAISS vector search and Gemini embeddings
  to ground HR policy answers in a company handbook.

Projects
- AI-Powered Business Insights Dashboard: LLM-generated insights,
  Prophet + XGBoost forecasting, Random Forest churn model (85%+ precision).
- Weather Prediction Model: 28+ engineered features, TensorFlow neural
  network, 7 models benchmarked by RMSE.

Skills: Python, SQL, TensorFlow, XGBoost, FAISS, MongoDB, Flask, Plotly
"""

SAMPLE_JOB_DESCRIPTION = """
We are hiring an entry-level Data Scientist (AI/ML) with strong Python
skills and experience in machine learning. Experience with LLM-based
systems, RAG pipelines, and vector databases such as FAISS is a strong
plus. SQL and experience with cloud or database systems preferred.
Familiarity with model evaluation and deployment is a bonus.
"""

# ---------------------------------------------------------------
# Prompt: force structured JSON output instead of free-form text
# ---------------------------------------------------------------

PROMPT_TEMPLATE = """You are an expert technical recruiter and resume reviewer.
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
  resume and rewrite them to be stronger, more quantified, or better
  matched to the JD's language. Keep "original" short (quote or
  closely paraphrase the actual bullet).

RESUME:
{resume}

TARGET JOB DESCRIPTION:
{job_description}
"""


def review_resume(resume_text: str, job_description_text: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(resume=resume_text, job_description=job_description_text)

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
    print("Sending resume + job description to Gemini...")
    review = review_resume(SAMPLE_RESUME, SAMPLE_JOB_DESCRIPTION)
    print_review(review)

