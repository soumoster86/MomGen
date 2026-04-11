import streamlit as st
import time as time_module
from ai_handler import generate_mom, analyze_notes
from doc_generator import create_doc
from utils import extract_text

st.set_page_config(page_title="AI MOM Generator", layout="wide")

if "mom" not in st.session_state:
    st.session_state.mom = None

if "last_notes" not in st.session_state:
    st.session_state.last_notes = ""

if "feedback" not in st.session_state:
    st.session_state.feedback = None


def calculate_score(f):
    score = 100
    if not f.get("is_complete", True):
        score -= 30
    score -= len(f.get("issues", [])) * 10
    return max(0, score)


st.title("📄 AI MOM Generator")

meeting_type = st.selectbox(
    "Meeting Type",
    ["Sprint", "Client", "Internal"]
)

title = st.text_input("Meeting Title")
date = st.date_input("Date")
meeting_time = st.time_input("Time")
participants = st.text_area("Participants")

uploaded_file = st.file_uploader("Upload Notes", type=["txt", "docx"])

notes = extract_text(uploaded_file) if uploaded_file else st.text_area("Enter Notes")

# -------- FEEDBACK --------
if notes and len(notes) > 30:
    if notes != st.session_state.last_notes:
        time_module.sleep(0.5)
        st.session_state.feedback = analyze_notes(notes)
        st.session_state.last_notes = notes

    f = st.session_state.feedback
    if f:
        st.metric("Quality Score", calculate_score(f))

# -------- GENERATE --------
if st.button("Generate MOM"):

    if len(notes.strip()) < 20:
        st.error("Please provide more detailed notes")
        st.stop()

    mom = generate_mom(notes, participants, meeting_type)

    if not mom or "error" in mom:
        st.error("AI Failed")
        st.code(mom)
        st.stop()

    st.session_state.mom = mom

# -------- EDIT --------
if st.session_state.mom:

    mom = st.session_state.mom

    summary = st.text_area("Summary", mom["summary"])
    decisions = st.text_area("Decisions", "\n".join(mom["decisions"]))
    risks = st.text_area("Risks", "\n".join(mom["risks"]))

    final_mom = {
        "summary": summary,
        "decisions": decisions.split("\n"),
        "risks": risks.split("\n"),
        "actions": mom["actions"]
    }

    buffer = create_doc(title, f"{date} {meeting_time}", participants, final_mom)

    st.download_button("Download MOM", buffer)