import streamlit as st
import json
import uuid
import pandas as pd
from ai_handler import generate_mom, analyze_notes
from doc_generator import create_doc
from utils import extract_text

st.set_page_config(
    page_title="AI MOM Generator",
    page_icon="📄",
    layout="wide",
)

HISTORY_FILE = "mom_history.json"

SAMPLE_NOTES = (
    "Discussed Q3 rollout plan. Decision: launch moves to July 15. "
    "Decision: we will use the existing vendor for hosting. "
    "Risk: vendor contract not yet signed, could delay infrastructure setup. "
    "Action: Anna to finalize the vendor contract by Friday. "
    "Action: Mark to prepare the comms plan, deadline July 1. "
    "Action: Priya to update the JIRA board with new milestones."
)


# ==========================================
# STORAGE
# ==========================================
def load_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def save_new_record(record):
    """Append a brand new record. Called exactly once, at generation time."""
    history = load_history()
    history.append(record)
    write_history(history)


def update_record(record_id, updates):
    """Update an existing record in place (matched by id)."""
    history = load_history()
    for entry in history:
        if entry.get("id") == record_id:
            entry.update(updates)
            break
    write_history(history)


# ==========================================
# SCORE
# ==========================================
def calculate_score(feedback):
    score = 100

    if not feedback.get("is_complete", True):
        score -= 30

    issues = feedback.get("issues", [])
    score -= min(len(issues) * 10, 40)

    return max(0, min(score, 100))


def analysis_failed(feedback):
    """Detect the error-fallback dict returned when the API is unreachable."""
    return any(
        str(i).startswith("Analysis failed")
        for i in feedback.get("issues", [])
    )


# ==========================================
# SESSION
# ==========================================
defaults = {
    "mom": None,
    "mom_id": None,
    "feedback": None,
    "saved_title": "",
    "saved_participants": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_mom():
    """Start a fresh MOM: clear generated data and editor widget state."""
    st.session_state.mom = None
    st.session_state.mom_id = None
    st.session_state.feedback = None
    for k in list(st.session_state.keys()):
        if k.startswith(("editor_", "summary_", "decisions_", "risks_")):
            del st.session_state[k]


# ==========================================
# NAV
# ==========================================
page = st.sidebar.radio("Navigation", ["MOM Generator", "Analytics"])

if st.session_state.mom:
    st.sidebar.divider()
    if st.sidebar.button("🆕 New MOM", use_container_width=True):
        reset_mom()
        st.rerun()


# ===============================
# PAGE: MOM GENERATOR
# ===============================
if page == "MOM Generator":

    st.title("📄 AI MOM Generator")
    st.caption("Turn raw meeting notes into structured Minutes of Meeting using AI")

    # -------- File upload (kept OUTSIDE the form so preview is instant) ----
    uploaded_file = st.file_uploader(
        "Upload Notes (.txt / .docx) — optional",
        type=["txt", "docx"],
        help="If a file is uploaded, it takes priority over manually typed notes",
    )

    extracted_text = ""
    if uploaded_file:
        extracted_text = extract_text(uploaded_file)
        st.success("✅ File uploaded — its content will be used as the meeting notes")
        with st.expander("📄 Preview Uploaded Notes"):
            st.write(extracted_text[:1500])

    # -------- Sample notes (must run BEFORE the notes widget is created) ---
    if not extracted_text:
        if st.button("✨ Try with sample notes"):
            st.session_state.notes_input = SAMPLE_NOTES
            st.toast("Sample notes loaded")

    # -------- Input form: reruns only on submit, not on every keystroke ----
    with st.form("mom_input"):

        meeting_type = st.selectbox(
            "Meeting Type",
            ["Sprint Planning", "Client Meeting", "Internal", "Steering Committee"],
            help="Different meeting types influence AI output (e.g., sprint → tasks, steering → risks)",
        )

        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input(
                "Meeting Title *",
                placeholder="e.g., Sprint Planning - Project Phoenix",
            )
            date = st.date_input("Meeting Date")

        with col2:
            meeting_time = st.time_input("Meeting Time")
            participants = st.text_area(
                "Participants *",
                placeholder="e.g., John Doe, Jane Smith",
                help="Comma-separated names. Helps assign action items",
            )

        manual_notes = st.text_area(
            "Meeting Notes" + (" (ignored — file uploaded)" if extracted_text else " *"),
            height=200,
            key="notes_input",
            placeholder=(
                "- Decision: Launch by Friday\n"
                "- Action: John to update tracker\n"
                "- Risk: Delay in approval"
            ),
            help="Include keywords like Decision, Action, Risk for better AI results",
        )

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            analyze_clicked = st.form_submit_button(
                "🔍 Analyze Notes Quality", use_container_width=True
            )
        with btn_col2:
            generate_clicked = st.form_submit_button(
                "🚀 Generate MOM", type="primary", use_container_width=True
            )

    notes = extracted_text if extracted_text else manual_notes

    # -------- AI FEEDBACK (explicit, on demand) --------
    if analyze_clicked:
        if not notes or len(notes.strip()) < 30:
            st.warning("Add more detailed notes (at least 30 characters) before analyzing.")
        else:
            with st.status("Analyzing notes...", expanded=False) as status:
                st.session_state.feedback = analyze_notes(notes)
                status.update(label="Analysis complete", state="complete")

    feedback = st.session_state.feedback

    if feedback:
        if analysis_failed(feedback):
            st.error(
                "⚠️ Could not analyze notes — OpenAI API unreachable. "
                "Check your network connection. You can still generate the MOM "
                "once connectivity is restored."
            )
        else:
            score = calculate_score(feedback)

            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Quality Score", f"{score}/100")
            with col2:
                st.progress(score / 100)

            if score >= 75:
                st.success(f"Quality Score {score}/100 — good to generate")
            elif score >= 50:
                st.warning(f"Quality Score {score}/100 — consider adding owners/deadlines")
            else:
                st.error(f"Quality Score {score}/100 — notes are too thin for a good MOM")

            issues = feedback.get("issues", [])
            suggestions = feedback.get("suggestions", [])

            if issues:
                with st.expander(f"❌ Issues Detected ({len(issues)})"):
                    for issue in issues:
                        st.write(f"- {issue}")

            if suggestions:
                with st.expander(f"💡 Suggestions to Improve ({len(suggestions)})"):
                    for suggestion in suggestions:
                        st.write(f"- {suggestion}")

    # -------- GENERATE --------
    if generate_clicked:

        if not title:
            st.error("Meeting Title is required")
            st.stop()

        if not participants:
            st.error("Participants are required")
            st.stop()

        if not notes or len(notes.strip()) < 20:
            st.error("Please provide detailed meeting notes")
            st.stop()

        with st.spinner("Generating MOM..."):
            mom = generate_mom(
                notes,
                participants,
                meeting_type,
                meeting_date=str(date),
            )

        if not mom or "error" in mom:
            st.error("AI failed to generate MOM")
            st.code(mom)
            st.stop()

        # Save EXACTLY ONCE, here, inside the submit handler.
        record_id = str(uuid.uuid4())
        datetime_str = f"{date} {meeting_time}"

        save_new_record({
            "id": record_id,
            "title": title,
            "datetime": datetime_str,
            "participants": participants,
            "mom": mom,
        })

        st.session_state.mom = mom
        st.session_state.mom_id = record_id
        st.session_state.saved_title = title
        st.session_state.saved_participants = participants
        st.toast("✅ MOM generated & saved")

    # -------- EDIT + PREVIEW --------
    if st.session_state.mom:

        mom = st.session_state.mom
        mom_id = st.session_state.mom_id
        title = title or st.session_state.saved_title
        participants = participants or st.session_state.saved_participants
        datetime_str = f"{date} {meeting_time}"

        st.divider()
        st.subheader("✏️ Review MOM Before Download")

        tab_edit, tab_preview = st.tabs(["✏️ Edit", "👁️ Preview"])

        # ---------- EDIT TAB ----------
        with tab_edit:
            summary = st.text_area(
                "Summary",
                value=mom.get("summary", ""),
                key=f"summary_{mom_id}",
                help="High-level overview of meeting",
            )

            decisions = st.text_area(
                "Decisions",
                value="\n".join(mom.get("decisions", [])),
                key=f"decisions_{mom_id}",
                help="One decision per line",
            )

            risks = st.text_area(
                "Risks",
                value="\n".join(mom.get("risks", [])),
                key=f"risks_{mom_id}",
                help="One risk per line",
            )

            st.write("**Action Items** — edit cells directly, use ＋ to add rows, "
                     "select a row and press Delete to remove it")

            actions_source = mom.get("actions", [])
            if not actions_source:
                actions_source = [{"task": "", "owner": "TBD", "deadline": "TBD"}]

            edited = st.data_editor(
                pd.DataFrame(actions_source),
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_{mom_id}",
                column_config={
                    "task": st.column_config.TextColumn(
                        "Task", required=True, width="large"
                    ),
                    "owner": st.column_config.TextColumn("Owner"),
                    "deadline": st.column_config.TextColumn("Deadline (YYYY-MM-DD)"),
                },
            )

        # ---------- Build final MOM from editor state ----------
        def _cell(value, default=""):
            """data_editor returns empty cells as NaN (which is truthy!) —
            normalize NaN/None/blank to the given default."""
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return default
            text = str(value).strip()
            return text if text else default

        actions = []
        for row in edited.to_dict("records"):
            task = _cell(row.get("task"))
            if not task:
                continue  # skip empty rows the user added but didn't fill
            actions.append({
                "task": task,
                "owner": _cell(row.get("owner"), "TBD"),
                "deadline": _cell(row.get("deadline"), "TBD"),
            })

        final_mom = {
            "summary": summary,
            "decisions": [d.strip() for d in decisions.split("\n") if d.strip()],
            "risks": [r.strip() for r in risks.split("\n") if r.strip()],
            "actions": actions,
        }

        # ---------- PREVIEW TAB ----------
        with tab_preview:
            st.markdown(f"## {title}")
            st.caption(f"🕐 {datetime_str}  ·  👥 {participants}")

            st.markdown("**Summary**")
            st.write(final_mom["summary"] or "_No summary_")

            st.markdown("**Decisions**")
            if final_mom["decisions"]:
                for d in final_mom["decisions"]:
                    st.markdown(f"- {d}")
            else:
                st.write("_No decisions recorded_")

            st.markdown("**Risks**")
            if final_mom["risks"]:
                for r in final_mom["risks"]:
                    st.markdown(f"- {r}")
            else:
                st.write("_No risks recorded_")

            st.markdown("**Action Items**")
            if final_mom["actions"]:
                st.table(pd.DataFrame(final_mom["actions"]))
            else:
                st.write("_No action items_")

        # ---------- SAVE + DOWNLOAD ----------
        action_col1, action_col2 = st.columns([1, 1])

        with action_col1:
            # Updates the EXISTING record (matched by id) — never appends.
            if st.button("💾 Save Changes", use_container_width=True):
                st.session_state.mom = final_mom
                update_record(mom_id, {
                    "title": title,
                    "datetime": datetime_str,
                    "participants": participants,
                    "mom": final_mom,
                })
                st.toast("💾 Changes saved")

        # Building the docx + download has NO storage side effects.
        buffer = create_doc(title, datetime_str, participants, final_mom)

        safe_title = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).strip().replace(" ", "_")[:40] or "MOM"

        with action_col2:
            st.download_button(
                "📥 Download MOM",
                buffer,
                file_name=f"MOM_{safe_title}_{date}.docx",
                use_container_width=True,
            )


# ===============================
# PAGE: ANALYTICS
# ===============================
if page == "Analytics":

    from collections import Counter
    from datetime import date as date_cls

    try:
        import altair as alt
        ALTAIR = True
    except ImportError:
        ALTAIR = False

    st.title("📊 Advanced Analytics Dashboard")
    st.caption("Insights across meetings, actions, risks, and team productivity")

    data = load_history()

    if not data:
        st.warning("No data available yet. Generate some MOMs first.")
        st.stop()

    # Legacy dedup: protects against duplicates created before the
    # save-flow fix. New records have unique ids and won't collide.
    seen = set()
    unique_data = []
    for m in data:
        key = m.get("id") or (
            m.get("title"),
            m.get("datetime"),
            json.dumps(m.get("mom", {}), sort_keys=True),
        )
        if key not in seen:
            seen.add(key)
            unique_data.append(m)
    data = unique_data

    # ---------------- TOP METRICS ----------------
    total_meetings = len(data)
    total_actions = sum(len(m["mom"].get("actions", [])) for m in data)
    total_risks = sum(len(m["mom"].get("risks", [])) for m in data)

    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Total Meetings", total_meetings)
    col2.metric("✅ Total Actions", total_actions)
    col3.metric("⚠️ Total Risks", total_risks)

    st.divider()

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
        for a in m["mom"].get("actions", []):
            owner = str(a.get("owner") or "").strip()
            if owner and owner.upper() != "TBD":
                owners.append(owner)

    if owners:
        owner_count = Counter(owners)
        owner_df = pd.DataFrame(owner_count.items(), columns=["Owner", "Tasks"])
        owner_df = owner_df.sort_values(by="Tasks", ascending=False)

        if ALTAIR:
            chart = (
                alt.Chart(owner_df)
                .mark_bar()
                .encode(
                    x=alt.X("Tasks:Q", title="Tasks"),
                    y=alt.Y("Owner:N", sort="-x", title=None),
                    tooltip=["Owner", "Tasks"],
                )
                .properties(height=max(120, 35 * len(owner_df)))
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.bar_chart(owner_df.set_index("Owner"))
    else:
        st.info("No owner data available")

    # ---------------- DEADLINE INSIGHTS ----------------
    st.subheader("⏱️ Deadline Insights")
    st.caption(
        "Based on absolute YYYY-MM-DD deadlines. "
        "Older free-text deadlines are counted as 'Unparseable'."
    )

    today = date_cls.today()
    overdue = upcoming = no_deadline = unparseable = 0

    for m in data:
        for a in m["mom"].get("actions", []):
            d = str(a.get("deadline", "")).strip()

            if not d or d.upper() == "TBD":
                no_deadline += 1
                continue

            parsed = pd.to_datetime(d, errors="coerce")
            if pd.isna(parsed):
                unparseable += 1
            elif parsed.date() < today:
                overdue += 1
            else:
                upcoming += 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Overdue", overdue)
    c2.metric("🟡 Upcoming", upcoming)
    c3.metric("⚪ No Deadline", no_deadline)
    c4.metric("❓ Unparseable", unparseable)

    # ---------------- RISK ANALYSIS ----------------
    st.subheader("⚠️ Risk Distribution per Meeting")

    risk_df = pd.DataFrame({
        "Meeting": [m.get("title", "Untitled") for m in data],
        "Risks": [len(m["mom"].get("risks", [])) for m in data],
    })
    st.bar_chart(risk_df.set_index("Meeting"))

    # ---------------- ACTION TABLE ----------------
    st.subheader("📋 Action Tracker")

    rows = []
    for m in data:
        for a in m["mom"].get("actions", []):
            rows.append({
                "Meeting": m.get("title"),
                "Owner": a.get("owner"),
                "Task": a.get("task"),
                "Deadline": a.get("deadline"),
            })

    action_df = pd.DataFrame(rows)

    if not action_df.empty:
        st.dataframe(action_df, use_container_width=True)
    else:
        st.info("No actions available")

    st.divider()

    # ---------------- HISTORY BROWSER ----------------
    st.subheader("🗂️ Meeting History")

    search = st.text_input("🔍 Filter by meeting title", placeholder="Type to filter...")

    visible = [
        m for m in reversed(data)
        if not search or search.lower() in m.get("title", "").lower()
    ]

    if not visible:
        st.warning("No matching meetings found")

    for idx, m in enumerate(visible):
        label = f"📌 {m.get('title', 'Untitled')} — {m.get('datetime', 'N/A')}"
        with st.expander(label):
            mom = m.get("mom", {})

            st.write(mom.get("summary", "_No summary_"))

            if mom.get("decisions"):
                st.markdown("**Decisions**")
                for d in mom["decisions"]:
                    st.markdown(f"- {d}")

            if mom.get("risks"):
                st.markdown("**Risks**")
                for r in mom["risks"]:
                    st.markdown(f"- {r}")

            if mom.get("actions"):
                st.markdown("**Action Items**")
                st.table(pd.DataFrame(mom["actions"]))

            buffer = create_doc(
                m.get("title", "MOM"),
                m.get("datetime", ""),
                m.get("participants", ""),
                mom,
            )
            safe = "".join(
                c for c in m.get("title", "MOM")
                if c.isalnum() or c in (" ", "-", "_")
            ).strip().replace(" ", "_")[:40] or "MOM"

            st.download_button(
                "📥 Re-download",
                buffer,
                file_name=f"MOM_{safe}.docx",
                key=f"dl_{m.get('id', idx)}",
            )
