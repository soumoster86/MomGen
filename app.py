import streamlit as st
import json
import time as time_module
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


# ---------------- SESSION ----------------
if "mom" not in st.session_state:
    st.session_state.mom = None

if "last_notes" not in st.session_state:
    st.session_state.last_notes = ""

if "feedback" not in st.session_state:
    st.session_state.feedback = None


# ---------------- NAV ----------------
page = st.sidebar.radio("Navigation", ["MOM Generator", "Analytics"])


# ===============================
# PAGE: MOM GENERATOR
# ===============================
if page == "MOM Generator":

    st.title("📄 AI MOM Generator")
    st.caption("Turn raw meeting notes into structured Minutes of Meeting using AI")

    # -------- Meeting Type --------
    meeting_type = st.selectbox(
        "Meeting Type",
        ["Sprint Planning", "Client Meeting", "Internal", "Steering Committee"],
        help="Different meeting types influence AI output (e.g., sprint → tasks, steering → risks)"
    )

    # -------- Details --------
    st.subheader("📝 Meeting Details")
    st.caption("Provide basic meeting information for context")

    col1, col2 = st.columns(2)

    with col1:
        title = st.text_input(
            "Meeting Title",
            placeholder="e.g., Sprint Planning - Project Phoenix",
            help="Use a clear and descriptive title"
        )

        date = st.date_input(
            "Meeting Date",
            help="Date when the meeting occurred"
        )

    with col2:
        meeting_time = st.time_input(
            "Meeting Time",
            help="Start time of meeting"
        )

        participants = st.text_area(
            "Participants",
            placeholder="e.g., John Doe, Jane Smith",
            help="Comma-separated names. Helps assign action items"
        )

    # -------- Notes --------
    st.subheader("📂 Upload or Enter Notes")
    st.caption("Better structured notes = better MOM")

    uploaded_file = st.file_uploader(
        "Upload Notes (.txt / .docx)",
        type=["txt", "docx"],
        help="Upload meeting notes file"
    )

    extracted_text = ""

    if uploaded_file:
        extracted_text = extract_text(uploaded_file)
        st.success("✅ File uploaded successfully")

        with st.expander("📄 Preview Uploaded Notes"):
            st.write(extracted_text[:1500])

    manual_notes = st.text_area(
        "Or Enter Notes Manually",
        height=200,
        placeholder=(
            "- Decision: Launch by Friday\n"
            "- Action: John to update tracker\n"
            "- Risk: Delay in approval"
        ),
        help="Include keywords like Decision, Action, Risk for better AI results"
    )

    notes = extracted_text if extracted_text else manual_notes

    # -------- AI FEEDBACK --------
    st.subheader("🤖 AI Feedback & Quality Score")

    if notes and len(notes) > 30:

        if notes != st.session_state.last_notes:
            time_module.sleep(0.5)

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
                st.warning("⚠️ Notes may be incomplete (missing decisions/actions)")

            with st.expander("❌ Issues Detected"):
                for issue in feedback.get("issues", []):
                    st.write(f"- {issue}")

            with st.expander("💡 Suggestions to Improve"):
                for suggestion in feedback.get("suggestions", []):
                    st.write(f"- {suggestion}")

        else:
            st.info("Analyzing notes...")

    else:
        st.info("Start typing detailed notes to activate AI feedback")

    # -------- GENERATE --------
    st.markdown("---")

    if st.button("🚀 Generate MOM", help="Generate structured Minutes of Meeting"):

        if not title:
            st.error("Meeting Title is required")
            st.stop()

        if not participants:
            st.error("Participants are required")
            st.stop()

        if not notes or len(notes.strip()) < 20:
            st.error("Please provide detailed meeting notes")
            st.stop()

        mom = generate_mom(notes, participants, meeting_type)

        if not mom or "error" in mom:
            st.error("AI failed to generate MOM")
            st.code(mom)
            st.stop()

        st.session_state.mom = mom
        st.success("✅ MOM Generated Successfully")

    # -------- EDIT --------
    if st.session_state.mom:

        mom = st.session_state.mom

        st.subheader("✏️ Edit MOM Before Download")

        summary = st.text_area(
            "Summary",
            value=mom.get("summary", ""),
            help="High-level overview of meeting"
        )

        decisions = st.text_area(
            "Decisions",
            value="\n".join(mom.get("decisions", [])),
            help="One decision per line"
        )

        risks = st.text_area(
            "Risks",
            value="\n".join(mom.get("risks", [])),
            help="List key risks/issues"
        )

        st.write("### Action Items")

        actions = []
        for i, a in enumerate(mom.get("actions", [])):
            col1, col2, col3 = st.columns(3)

            task = col1.text_input(f"Task {i+1}", a.get("task", ""), key=f"t{i}")
            owner = col2.text_input(f"Owner {i+1}", a.get("owner", ""), key=f"o{i}")
            deadline = col3.text_input(f"Deadline {i+1}", a.get("deadline", ""), key=f"d{i}")

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

        st.download_button(
            "📥 Download MOM",
            buffer,
            file_name="MOM.docx",
            help="Download the final MOM document"
        )


# ===============================
# ANALYTICS DASHBOARD (UPGRADED)
# ===============================
if page == "Analytics":

    import pandas as pd
    from collections import Counter
    from datetime import datetime

    st.title("📊 Advanced Analytics Dashboard")
    st.caption("Insights across meetings, actions, risks, and team productivity")

    data = load_history()

    if not data:
        st.warning("No data available yet. Generate some MOMs first.")
        st.stop()

    # ---------------- CLEAN DATA ----------------
    seen = set()
    unique_data = []

    for m in data:
        key = (m.get("title"), m.get("datetime"))
        if key not in seen:
            seen.add(key)
            unique_data.append(m)

    data = unique_data

    # ---------------- TOP METRICS ----------------
    total_meetings = len(data)
    total_actions = sum(len(m["mom"]["actions"]) for m in data)
    total_risks = sum(len(m["mom"]["risks"]) for m in data)

    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Total Meetings", total_meetings)
    col2.metric("✅ Total Actions", total_actions)
    col3.metric("⚠️ Total Risks", total_risks)

    st.markdown("---")

    # ---------------- TREND ----------------
    st.subheader("📈 Meetings Trend Over Time")

    df = pd.DataFrame(data)

    if "datetime" in df.columns:
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        trend = df.groupby(df["date"].dt.date).size()

        st.line_chart(trend)
    else:
        st.info("No date data available")

    # ---------------- OWNER ANALYSIS ----------------
    st.subheader("👤 Actions by Owner")

    owners = []
    for m in data:
        for a in m["mom"]["actions"]:
            if a.get("owner"):
                owners.append(a["owner"])

    if owners:
        owner_count = Counter(owners)
        owner_df = pd.DataFrame(owner_count.items(), columns=["Owner", "Tasks"])
        owner_df = owner_df.sort_values(by="Tasks", ascending=False)

        st.bar_chart(owner_df.set_index("Owner"))
    else:
        st.info("No owner data available")

    # ---------------- DEADLINE INSIGHTS ----------------
    st.subheader("⏱️ Deadline Insights")

    overdue = 0
    upcoming = 0
    no_deadline = 0

    for m in data:
        for a in m["mom"]["actions"]:
            d = str(a.get("deadline", "")).lower()

            if not d.strip():
                no_deadline += 1
            elif "today" in d:
                overdue += 1
            elif "next" in d or "week" in d:
                upcoming += 1

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 Overdue", overdue)
    c2.metric("🟡 Upcoming", upcoming)
    c3.metric("⚪ No Deadline", no_deadline)

    # ---------------- RISK ANALYSIS ----------------
    st.subheader("⚠️ Risk Distribution per Meeting")

    risk_counts = []
    titles = []

    for m in data:
        risk_counts.append(len(m["mom"]["risks"]))
        titles.append(m["title"])

    risk_df = pd.DataFrame({
        "Meeting": titles,
        "Risks": risk_counts
    })

    st.bar_chart(risk_df.set_index("Meeting"))

    # ---------------- ACTION TABLE ----------------
    st.subheader("📋 Action Tracker")

    rows = []

    for m in data:
        for a in m["mom"]["actions"]:
            rows.append({
                "Meeting": m.get("title"),
                "Owner": a.get("owner"),
                "Task": a.get("task"),
                "Deadline": a.get("deadline")
            })

    action_df = pd.DataFrame(rows)

    if not action_df.empty:
        st.dataframe(action_df, use_container_width=True)
    else:
        st.info("No actions available")

    # ---------------- SEARCH ----------------
    st.subheader("🔍 Search Meetings")

    search = st.text_input("Search by Meeting Title")

    if search:
        filtered = [m for m in data if search.lower() in m["title"].lower()]

        if filtered:
            for m in filtered:
                st.write(f"📌 {m['title']} - {m.get('datetime', 'N/A')}")
        else:
            st.warning("No matching meetings found")

    st.markdown("---")

    # ---------------- RECENT ----------------
    st.subheader("🕒 Recent Meetings")

    for m in reversed(data[-5:]):
        st.write(f"📌 {m['title']} - {m.get('datetime', 'N/A')}")
