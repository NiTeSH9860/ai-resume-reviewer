"""
AI Resume Reviewer — Streamlit App (Day 5)
----------------------------------------------
Upload a resume, paste one or more target job descriptions, get a
structured Gemini-powered critique per job in the browser.

Day 5 addition:
  - Multiple job descriptions in one pass: add/remove JD boxes, review
    the same resume against each, results shown in separate tabs so you
    can compare fit across postings side by side.

Run:
    streamlit run app.py
"""

import hashlib

import streamlit as st

from reviewer import read_resume_upload, review_resume, run_consistency_check, build_pdf_report

# Cache by input: if the exact same resume text + JD text is reviewed again
# (e.g. accidental double-click, or re-running with no changes), reuse the
# cached result instead of burning another API call. Cache is keyed on the
# function's arguments automatically.
cached_review_resume = st.cache_data(show_spinner=False)(review_resume)
cached_run_consistency_check = st.cache_data(show_spinner=False)(run_consistency_check)

if "seen_input_hashes" not in st.session_state:
    st.session_state.seen_input_hashes = set()

if "jd_entries" not in st.session_state:
    # Each entry: {"id": int, "title": str, "text": str}
    st.session_state.jd_entries = [{"id": 0, "title": "", "text": ""}]
    st.session_state.next_jd_id = 1


def _input_hash(resume_text: str, jd_text: str) -> str:
    return hashlib.sha256((resume_text + "||" + jd_text).encode("utf-8")).hexdigest()


def _add_jd():
    st.session_state.jd_entries.append(
        {"id": st.session_state.next_jd_id, "title": "", "text": ""}
    )
    st.session_state.next_jd_id += 1


def _remove_jd(entry_id):
    st.session_state.jd_entries = [
        e for e in st.session_state.jd_entries if e["id"] != entry_id
    ]


st.set_page_config(page_title="AI Resume Reviewer", page_icon="📄", layout="centered")

with st.sidebar:
    st.caption("Identical resume + JD combinations are cached to avoid repeat API calls.")
    if st.button("Clear cache"):
        cached_review_resume.clear()
        cached_run_consistency_check.clear()
        st.session_state.seen_input_hashes = set()
        st.success("Cache cleared.")

st.title("📄 AI Resume Reviewer")
st.write(
    "Upload your resume and paste one or more target job descriptions. "
    "Gemini will score the match against each and suggest concrete improvements."
)

resume_file = st.file_uploader(
    "Resume (PDF or .txt)", type=["pdf", "txt"], accept_multiple_files=False
)

st.subheader("Job Descriptions")

for i, entry in enumerate(st.session_state.jd_entries):
    with st.container(border=True):
        header_col, remove_col = st.columns([5, 1])
        with header_col:
            entry["title"] = st.text_input(
                "Label (optional)", value=entry["title"],
                key=f"jd_title_{entry['id']}",
                placeholder=f"e.g. Company name or role — Job {i + 1}",
            )
        with remove_col:
            st.write("")  # vertical alignment spacer
            if len(st.session_state.jd_entries) > 1:
                st.button("✕ Remove", key=f"remove_{entry['id']}",
                          on_click=_remove_jd, args=(entry["id"],))

        entry["text"] = st.text_area(
            f"Job description {i + 1}", value=entry["text"], height=180,
            key=f"jd_text_{entry['id']}",
            placeholder="Paste the job description here...",
        )

st.button("+ Add another job description", on_click=_add_jd)

run_consistency = st.checkbox(
    "Also run a 3x consistency check per job (uses 3 extra API calls each, takes longer)",
    help="Runs each review 3 times on the identical input and reports how much "
         "the score varies — a sanity check on how stable the scoring is.",
)

review_clicked = st.button("Review Resume", type="primary", use_container_width=True)

if review_clicked:
    active_jds = [e for e in st.session_state.jd_entries if e["text"].strip()]

    if resume_file is None:
        st.warning("Please upload a resume first.")
    elif not active_jds:
        st.warning("Please paste at least one job description first.")
    else:
        try:
            with st.spinner("Reading resume..."):
                resume_text = read_resume_upload(resume_file)
        except ValueError as e:
            st.error(f"Couldn't process this resume: {e}")
        else:
            results = []  # list of (label, review, consistency_result, was_cached)

            for i, entry in enumerate(active_jds):
                jd_text = entry["text"]
                label = entry["title"].strip() or f"Job {i + 1}"

                try:
                    input_hash = _input_hash(resume_text, jd_text)
                    was_cached = input_hash in st.session_state.seen_input_hashes

                    with st.spinner(
                        f"[{label}] " + ("Loading cached result..." if was_cached
                                          else "Sending to Gemini for review...")
                    ):
                        review = cached_review_resume(resume_text, jd_text)

                    st.session_state.seen_input_hashes.add(input_hash)

                    consistency_result = None
                    if run_consistency:
                        with st.spinner(f"[{label}] Running consistency check (3 more calls)..."):
                            consistency_result = cached_run_consistency_check(
                                resume_text, jd_text, n_runs=3
                            )

                    results.append((label, review, consistency_result, was_cached))

                except Exception as e:
                    st.error(f"[{label}] Something went wrong: {e}")

            if results:
                st.success(f"Review complete for {len(results)} job description(s).")

                if len(results) == 1:
                    tab_containers = [st.container()]
                else:
                    tab_containers = st.tabs([label for label, *_ in results])

                for tab, (label, review, consistency_result, was_cached) in zip(tab_containers, results):
                    with tab:
                        if was_cached:
                            st.caption("Loaded from cache — no new API call made.")

                        score = review["overall_fit_score"]
                        st.metric("Overall Fit Score", f"{score} / 10")

                        pdf_bytes = build_pdf_report(review)
                        st.download_button(
                            "⬇ Download Report (PDF)",
                            data=pdf_bytes,
                            file_name=f"resume_review_{label.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            key=f"download_{label}",
                        )

                        if consistency_result:
                            st.subheader("🔁 Consistency Check (3 runs)")
                            scores = consistency_result["scores"]
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Mean Score", f"{consistency_result['mean']:.1f}")
                            c2.metric("Range", f"{consistency_result['range']}")
                            c3.metric("Std Dev", f"{consistency_result['stdev']:.2f}")
                            st.caption(f"Individual scores across 3 runs: {scores}")
                            if consistency_result["range"] <= 1:
                                st.caption("✅ Score is stable across repeated runs.")
                            else:
                                st.caption("⚠️ Score varies noticeably across repeated runs — "
                                           "treat any single score as approximate.")

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