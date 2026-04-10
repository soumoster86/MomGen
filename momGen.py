import streamlit as st
from utils import extract_text
from ai_handler import generate_mom
from doc_generator import create_doc

st.set_page_config(page_title="MOM Generator", layout="wide")

st.title("📄 Smart MOM Generator")

# ---------------- Sidebar Progress ----------------
st.sidebar.header("📊 Progress Tracker")

progress = 0

# ---------------- Inputs ----------------
st.subheader("📝 Meeting Details")

with st.expander("ℹ️ What should I enter here?"):
    st.markdown("""
    - **Meeting Title**: Name of meeting  
    - **Participants**: Comma-separated names  
    - **Date & Time**: When meeting occurred  
    """)

col1, col2 = st.columns(2)

with col1:
    meeting_title = st.text_input("Meeting Title", help="Enter clear meeting name")
    meeting_date = st.date_input("Meeting Date")

with col2:
    meeting_time = st.time_input("Meeting Time")
    participants = st.text_area(
        "Participants",
        placeholder="John, Jane, Client A",
        help="Comma-separated participants"
    )

# ---------------- File Upload ----------------
st.subheader("📂 Upload Meeting Notes")

with st.expander("💡 Tips for better results"):
    st.markdown("""
    - Provide structured notes  
    - Include decisions, risks, actions  
    - Avoid random text dumps  
    """)

uploaded_file = st.file_uploader(
    "Upload .txt or .docx",
    type=["txt", "docx"]
)

extracted_text = ""

if uploaded_file:
    extracted_text = extract_text(uploaded_file)
    st.success("File processed successfully")

    with st.expander("Preview Extracted Text"):
        st.write(extracted_text[:1500])

# ---------------- Manual Input ----------------
manual_notes = st.text_area(
    "✍️ Or Enter Notes Manually",
    height=200,
    placeholder="""
- Discussed timeline delays
- Client requested new features
- Action: John to send update
"""
)

notes = extracted_text if extracted_text else manual_notes

# ---------------- Progress ----------------
if meeting_title:
    progress += 25
if participants:
    progress += 25
if notes:
    progress += 50

st.sidebar.progress(progress / 100)
st.sidebar.write(f"Completion: {progress}%")

# ---------------- Validation ----------------
def validate():
    if not meeting_title:
        return "Enter meeting title"
    if not participants:
        return "Enter participants"
    if not notes:
        return "Provide meeting notes"
    return None

# ---------------- Generate ----------------
st.markdown("---")

st.info("💡 Better notes = better MOM output")

if st.button("🚀 Generate MOM"):

    error = validate()

    if error:
        st.error(error)
        st.stop()

    meeting_datetime = f"{meeting_date} {meeting_time}"

    with st.spinner("Generating MOM..."):
        mom = generate_mom(notes)

    if not mom:
        st.error("AI failed to generate MOM")
        st.stop()

    st.success("MOM Generated Successfully!")

    # ---------------- Preview ----------------
    st.subheader("📊 MOM Preview")

    st.write("### 📌 Meeting Details")
    st.write(f"**Title:** {meeting_title}")
    st.write(f"**Date & Time:** {meeting_datetime}")
    st.write(f"**Participants:** {participants}")

    st.write("---")

    st.write("### Summary")
    st.write(mom.get("summary"))

    st.write("### Decisions")
    for d in mom.get("decisions", []):
        st.write(f"- {d}")

    st.write("### Risks")
    for r in mom.get("risks", []):
        st.write(f"- {r}")

    st.write("### Actions")
    for a in mom.get("actions", []):
        st.write(
            f"- {a.get('task')} (Owner: {a.get('owner')}, Deadline: {a.get('deadline')})"
        )

    # ---------------- Download ----------------
    file_path = create_doc(
        meeting_title,
        meeting_datetime,
        participants,
        mom
    )

    with open(file_path, "rb") as file:
        st.download_button(
            "📥 Download MOM",
            file,
            file_name="MOM.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )