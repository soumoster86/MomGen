import streamlit as st
from utils import extract_text
from ai_handler import generate_mom, analyze_notes
from doc_generator import create_doc

st.set_page_config(page_title="MOM Generator", layout="wide")

st.title("📄 AI-Powered MOM Generator")
st.caption("Convert raw meeting notes into structured Minutes of Meeting (MoM) using AI")

# ---------------- SIDEBAR ----------------
st.sidebar.header("📊 Completion Status")
progress = 0

# ---------------- MEETING DETAILS ----------------
st.subheader("📝 Meeting Details")

st.markdown("Provide basic meeting information to generate a complete MOM.")

col1, col2 = st.columns(2)

with col1:
    meeting_title = st.text_input(
        "Meeting Title",
        help="Enter a clear and descriptive name (e.g., Sprint Planning, Client Review)"
    )

    meeting_date = st.date_input(
        "Meeting Date",
        help="Select the date when the meeting occurred"
    )

with col2:
    meeting_time = st.time_input(
        "Meeting Time",
        help="Select the start time of the meeting"
    )

    participants = st.text_area(
        "Participants",
        placeholder="e.g., John Doe, Jane Smith, Client A",
        help="Enter participant names separated by commas"
    )

# ---------------- FILE UPLOAD ----------------
st.subheader("📂 Upload Meeting Notes")

st.markdown("Upload your raw meeting notes or paste them manually below.")

uploaded_file = st.file_uploader(
    "Upload Notes (.txt or .docx)",
    type=["txt", "docx"],
    help="Supported formats: .txt and .docx"
)

extracted_text = ""

if uploaded_file:
    extracted_text = extract_text(uploaded_file)
    st.success("✅ File uploaded and processed successfully")

    with st.expander("📄 Preview Extracted Notes"):
        st.write(extracted_text[:1500])

# ---------------- MANUAL INPUT ----------------
manual_notes = st.text_area(
    "✍️ Or Enter Notes Manually",
    height=200,
    placeholder="""
Example:
- Discussed delays in delivery timeline
- Client requested additional features
- Decision: Phase 1 delivery by next Friday
- Action: John to update project plan
""",
    help="Provide structured notes including decisions, risks, and actions for best results"
)

notes = extracted_text if extracted_text else manual_notes

# ---------------- PROGRESS ----------------
if meeting_title:
    progress += 25
if participants:
    progress += 25
if notes:
    progress += 50

st.sidebar.progress(progress / 100)
st.sidebar.write(f"{progress}% Complete")

# ---------------- AI FEEDBACK ----------------
if notes:
    try:
        feedback = analyze_notes(notes)

        if not feedback.get("is_complete", True):
            st.warning("⚠️ Your notes may be incomplete")

            with st.expander("💡 Suggestions to Improve Input"):
                for issue in feedback.get("issues", []):
                    st.write(f"❌ {issue}")
                for suggestion in feedback.get("suggestions", []):
                    st.write(f"💡 {suggestion}")
    except:
        pass

# ---------------- GENERATE ----------------
st.markdown("---")

st.info("💡 Tip: Better structured notes → More accurate MOM output")

if st.button(
    "🚀 Generate MOM",
    help="Click to generate a structured MOM document using AI"
):

    if not meeting_title:
        st.error("Meeting Title is required")
        st.stop()

    if not participants:
        st.error("Participants are required")
        st.stop()

    if not notes:
        st.error("Please provide meeting notes")
        st.stop()

    meeting_datetime = f"{meeting_date} {meeting_time}"

    with st.spinner("Generating MOM..."):
        mom = generate_mom(notes, participants)

    if not mom:
        st.error("AI failed to generate MOM. Try improving your notes.")
        st.stop()

    st.success("✅ MOM Generated Successfully")

    # ---------------- PREVIEW ----------------
    st.subheader("📊 MOM Preview")

    st.write("### 📌 Meeting Details")
    st.write(f"**Title:** {meeting_title}")
    st.write(f"**Date & Time:** {meeting_datetime}")
    st.write(f"**Participants:** {participants}")

    st.write("---")

    st.write("### Summary")
    st.write(mom.get("summary"))

    st.write("### Key Decisions")
    for d in mom.get("decisions", []):
        st.write(f"- {d}")

    st.write("### Risks & Issues")
    for r in mom.get("risks", []):
        st.write(f"- {r}")

    st.write("### Action Items")
    for a in mom.get("actions", []):
        st.write(
            f"- {a.get('task')} (Owner: {a.get('owner')}, Deadline: {a.get('deadline')})"
        )

    # ---------------- DOWNLOAD ----------------
    buffer = create_doc(
        meeting_title,
        meeting_datetime,
        participants,
        mom
    )

    st.download_button(
        "📥 Download MOM (Word)",
        buffer,
        file_name="MOM.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        help="Download the generated MOM as a Word document"
    )