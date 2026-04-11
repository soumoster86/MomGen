import streamlit as st
import json
import time as time_module  # FIX: avoid conflict
from ai_handler import generate_mom, analyze_notes
from doc_generator import create_doc
from utils import extract_text

st.set_page_config(page_title="AI MOM Generator", layout="wide")

HISTORY_FILE = "mom_history.json"


# ---------------- STORAGE ----------------
def load_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_history(data):
    history = load_history()
    history.append(data)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ---------------- SCORE ----------------
def calculate_score(feedback):
    score = 100

    if not feedback.get("is_complete", True):
        score -= 30

    issues = feedback.get("issues", [])
    score -= min(len(issues) * 10, 40)

    suggestions = feedback.get("suggestions", [])
    score += min(len(suggestions) * 2, 10)

    return max(0, min(score, 100))


# ---------------- SESSION INIT ----------------
if "mom" not in st.session_state:
    st.session_state.mom = None

if "last_notes" not in st.session_state:
    st.session_state.last_notes = ""

if "feedback" not in st.session_state:
    st.session_state.feedback = None


# ---------------- NAV ----------------
page = st.sidebar.radio("Navigation", ["MOM Generator", "Analytics"])


# ===============================
# PAGE 1: MOM GENERATOR
# ===============================
if page == "MOM Generator":

    st.title("📄 AI MOM Generator")
    st.caption("Generate structured Minutes of Meeting using AI")

    # -------- Meeting Type --------
    meeting_type = st.selectbox(
        "Meeting Type",
        ["Sprint Planning", "Client Meeting", "Internal", "Steering Committee"],
        help="Helps AI focus on relevant outputs like risks, decisions, or tasks"
    )

    # -------- Meeting Details --------
    st.subheader("📝 Meeting Details")
    col1, col2 = st.columns(2)

    with col1:
        title = st.text_input(
            "Meeting Title",
            placeholder="e.g., Sprint Planning - Project Phoenix",
            help="Provide a clear and descriptive meeting name"
        )
        date = st.date_input("Meeting Date")

    with col2:
        meeting_time = st.time_input("Meeting Time")  # FIXED
        participants = st.text_area(
            "Participants",
            placeholder="e.g., John Doe, Jane Smith",
            help="Comma-separated names for assigning action owners"
        )

    # -------- Upload Section --------
    st.subheader("📂 Upload or Enter Notes")

    uploaded_file = st.file_uploader(
        "Upload Notes (.txt / .docx)",
        type=["txt", "docx"],
        help="Upload raw meeting notes"
    )

    extracted_text = ""

    if uploaded_file:
        extracted_text = extract_text(uploaded_file)
        st.success("✅ File uploaded successfully")

        with st.expander("Preview Uploaded Notes"):
            st.write(extracted_text[:1500])

    # -------- Manual Notes --------
    manual_notes = st.text_area(
        "Or Enter Notes Manually",
        height=200,
        placeholder=(
            "- Decision: Launch by Friday\n"
            "- Action: John to update tracker\n"
            "- Risk: Delay in approval"
        ),
        help="Include decisions, actions, and risks clearly"
    )

    notes = extracted_text if extracted_text else manual_notes

    # -------- AI FEEDBACK --------
    st.subheader("🤖 AI Feedback & Quality Score")

    if notes and len(notes) > 30:

        if notes != st.session_state.last_notes:
            time_module.sleep(0.5)  # FIXED

            try:
                feedback = analyze_notes(notes)
                st.session_state.feedback = feedback
                st.session_state.last_notes = notes
            except:
                st.session_state.feedback = None

        feedback = st.session_state.feedback

        if feedback:
            score = calculate_score(feedback)

            col1, col2 = st.columns([1, 3])

            with col1:
                st.metric("Quality Score", f"{score}/100")

            with col2:
                st.progress(score / 100)

            if not feedback.get("is_complete", True):
                st.warning("⚠️ Notes may be incomplete")

            with st.expander("❌ Issues Detected"):
                for issue in feedback.get("issues", []):
                    st.write(f"- {issue}")

            with st.expander("💡 Suggestions"):
                for suggestion in feedback.get("suggestions", []):
                    st.write(f"- {suggestion}")

        else:
            st.info("Analyzing notes...")

    else:
        st.info("Start typing notes to get AI feedback")

    # -------- GENERATE MOM --------
    st.markdown("---")

    if st.button("🚀 Generate MOM"):

        if not title:
            st.error("Meeting Title is required")
            st.stop()

        if not participants:
            st.error("Participants are required")
            st.stop()

        if not notes:
            st.error("Meeting Notes are required")
            st.stop()

        mom = generate_mom(notes, participants, meeting_type)

        if not mom:
            st.error("Failed to generate MOM")
            st.stop()

        st.session_state.mom = mom
        st.success("✅ MOM Generated Successfully")

    # -------- EDIT MOM --------
    if st.session_state.mom:

        mom = st.session_state.mom

        st.subheader("✏️ Edit MOM")

        summary = st.text_area("Summary", value=mom.get("summary", ""), key="summary")

        decisions = st.text_area(
            "Decisions",
            value="\n".join(mom.get("decisions", [])),
            key="decisions"
        )

        risks = st.text_area(
            "Risks",
            value="\n".join(mom.get("risks", [])),
            key="risks"
        )

        st.write("### Action Items")

        actions = []
        for i, a in enumerate(mom.get("actions", [])):

            col1, col2, col3 = st.columns(3)

            task = col1.text_input(f"Task {i+1}", value=a.get("task", ""), key=f"task_{i}")
            owner = col2.text_input(f"Owner {i+1}", value=a.get("owner", ""), key=f"owner_{i}")
            deadline = col3.text_input(f"Deadline {i+1}", value=a.get("deadline", ""), key=f"deadline_{i}")

            actions.append({"task": task, "owner": owner, "deadline": deadline})

        final_mom = {
            "summary": summary,
            "decisions": [d.strip() for d in decisions.split("\n") if d.strip()],
            "risks": [r.strip() for r in risks.split("\n") if r.strip()],
            "actions": actions
        }

        datetime_str = f"{date} {meeting_time}"

        if st.button("💾 Save Changes"):
            st.session_state.mom = final_mom
            st.success("Changes saved!")

        buffer = create_doc(title, datetime_str, participants, final_mom)

        save_history({
            "title": title,
            "datetime": datetime_str,
            "mom": final_mom
        })

        st.download_button("📥 Download MOM", buffer, file_name="MOM.docx")


# ===============================
# PAGE 2: ANALYTICS
# ===============================
if page == "Analytics":

    st.title("📊 Analytics Dashboard")

    data = load_history()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Meetings", len(data))
    col2.metric("Total Actions", sum(len(m["mom"]["actions"]) for m in data))
    col3.metric("Total Risks", sum(len(m["mom"]["risks"]) for m in data))

    st.subheader("Recent Meetings")

    for m in reversed(data[-5:]):
        st.write(f"{m['title']} - {m['datetime']}")