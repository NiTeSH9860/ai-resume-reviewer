"""
AI Resume Reviewer — Streamlit App (Day 3)
----------------------------------------------
Upload a resume, paste a target job description, get a structured
Gemini-powered critique in the browser.

Run:
    streamlit run app.py
"""

import streamlit as st

from reviewer import read_resume_upload, review_resume

st.set_page_config(page_title="AI Resume Reviewer", page_icon="📄", layout="centered")

st.title("📄 AI Resume Reviewer")
st.write(
    "Upload your resume and paste a target job description. "
    "Gemini will score the match and suggest concrete improvements."
)

col1, col2 = st.columns(2)

with col1:
    resume_file = st.file_uploader(
        "Resume (PDF or .txt)", type=["pdf", "txt"], accept_multiple_files=False
    )

with col2:
    job_description_text = st.text_area(
        "Target job description", height=220,
        placeholder="Paste the job description here...",
    )

review_clicked = st.button("Review Resume", type="primary", use_container_width=True)

if review_clicked:
    if resume_file is None:
        st.warning("Please upload a resume first.")
    elif not job_description_text.strip():
        st.warning("Please paste a job description first.")
    else:
        try:
            with st.spinner("Reading resume..."):
                resume_text = read_resume_upload(resume_file)

            with st.spinner("Sending to Gemini for review..."):
                review = review_resume(resume_text, job_description_text)

        except ValueError as e:
            st.error(f"Couldn't process this resume: {e}")
        except Exception as e:
            st.error(
                "Something went wrong contacting Gemini. This is often a quota, "
                "network, or API key issue rather than a problem with your files."
            )
            st.caption(f"Details: {e}")
        else:
            st.success("Review complete.")

            score = review["overall_fit_score"]
            st.metric("Overall Fit Score", f"{score} / 10")

            st.subheader("✅ Strengths")
            for s in review["strengths"]:
                st.markdown(f"- {s}")

            st.subheader("⚠️ Gaps")
            for g in review["gaps"]:
                st.markdown(f"- {g}")

            st.subheader("✍️ Rewrite Suggestions")
            for i, r in enumerate(review["rewrite_suggestions"], start=1):
                with st.expander(f"Suggestion {i}"):
                    st.markdown(f"**Original:** {r['original']}")
                    st.markdown(f"**Improved:** {r['improved']}")
                    st.markdown(f"**Why:** {r['why']}")