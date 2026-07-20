"""
reviewer.py — Shared core logic for the AI Resume Reviewer.

Both resume_reviewer.py (CLI) and app.py (Streamlit) import from this
module, so the review logic, prompt, and file-reading code live in one
place instead of being duplicated.
"""

import json
import os
import statistics
from datetime import date
from io import BytesIO

from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY not found. Create a .env file with GEMINI_API_KEY=your_key_here"
    )

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"


# ---------------------------------------------------------------
# File reading
# ---------------------------------------------------------------

def _extract_pdf_text(pdf_source) -> str:
    """pdf_source can be a file path (str/Path) or a file-like object
    (e.g. Streamlit's UploadedFile), since PdfReader accepts both."""
    reader = PdfReader(pdf_source)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_resume_upload(uploaded_file) -> str:
    """For Streamlit's st.file_uploader result (a file-like object with
    .name and bytes content)."""
    name = getattr(uploaded_file, "name", "")
    if name.lower().endswith(".pdf"):
        text = _extract_pdf_text(BytesIO(uploaded_file.getvalue()))
    else:
        text = uploaded_file.getvalue().decode("utf-8")

    text = text.strip()
    if not text:
        raise ValueError(
            "No extractable text found in the uploaded resume. "
            "If this is a scanned/image-based PDF, text extraction won't work."
        )
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


# ---------------------------------------------------------------
# Consistency check: does the score stay stable across repeated
# runs on the identical resume + JD?
# ---------------------------------------------------------------

def run_consistency_check(resume_text: str, job_description_text: str, n_runs: int = 3) -> dict:
    """Runs review_resume n_runs times on the exact same input and
    reports how much the overall_fit_score varies. A well-behaved,
    grounded critique should stay fairly stable across runs — large
    swings would suggest the score is more noise than signal."""
    scores = []
    reviews = []
    for _ in range(n_runs):
        review = review_resume(resume_text, job_description_text)
        scores.append(review["overall_fit_score"])
        reviews.append(review)

    return {
        "scores": scores,
        "mean": statistics.mean(scores),
        "min": min(scores),
        "max": max(scores),
        "range": max(scores) - min(scores),
        "stdev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
        "reviews": reviews,
    }


# ---------------------------------------------------------------
# Downloadable PDF report
# ---------------------------------------------------------------

def build_pdf_report(review: dict) -> bytes:
    """Renders a review dict into a formatted PDF report, returned as
    bytes so it can be handed directly to st.download_button."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle", parent=styles["Title"], fontSize=18,
        textColor=colors.HexColor("#1F3864"), spaceAfter=4,
    )
    score_style = ParagraphStyle(
        "ScoreStyle", parent=styles["Normal"], fontSize=14,
        textColor=colors.HexColor("#1F3864"), spaceAfter=16,
    )
    heading_style = ParagraphStyle(
        "HeadingStyle", parent=styles["Heading2"], fontSize=13,
        spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1F3864"),
    )
    body_style = ParagraphStyle("BodyStyle", parent=styles["Normal"], fontSize=10.5, leading=15)

    story = [
        Paragraph("AI Resume Reviewer — Report", title_style),
        Paragraph(f"Overall Fit Score: {review['overall_fit_score']} / 10", score_style),
        Paragraph("Strengths", heading_style),
        ListFlowable(
            [ListItem(Paragraph(s, body_style), leftIndent=10) for s in review["strengths"]],
            bulletType="bullet", start="•", leftIndent=14,
        ),
        Paragraph("Gaps", heading_style),
        ListFlowable(
            [ListItem(Paragraph(g, body_style), leftIndent=10) for g in review["gaps"]],
            bulletType="bullet", start="•", leftIndent=14,
        ),
        Paragraph("Rewrite Suggestions", heading_style),
    ]

    for i, r in enumerate(review["rewrite_suggestions"], start=1):
        story.append(Paragraph(f"{i}. Original", ParagraphStyle(
            "SubHead", parent=styles["Heading3"], fontSize=11, spaceBefore=10, spaceAfter=2,
        )))
        story.append(Paragraph(r["original"], body_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Improved:", ParagraphStyle(
            "SubHeadBold", parent=styles["Normal"], fontSize=10.5, spaceAfter=2,
        )))
        story.append(Paragraph(r["improved"], body_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<i>Why: {r['why']}</i>", body_style))
        story.append(Spacer(1, 10))

    doc.build(story)
    return buffer.getvalue()