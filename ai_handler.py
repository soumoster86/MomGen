import json
import re
import os
import traceback
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APITimeoutError, InternalServerError, APIConnectionError
from utils import extract_entities

# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not found. Configure either:\n"
        "1. .env file (local)\n"
        "2. Streamlit Secrets (cloud)"
    )

client = OpenAI(api_key=api_key)

PRIMARY_MODEL = "gpt-4o-mini"

# Fallback model if primary fails for transient reasons
FALLBACK_MODEL = "gpt-4o"

# Only these errors are worth retrying on a different model.
# Auth errors, bad requests, quota issues, etc. would fail identically.
TRANSIENT_ERRORS = (
    RateLimitError,
    APITimeoutError,
    InternalServerError,
    APIConnectionError,
)


# ==========================================
# HELPERS
# ==========================================

def clean_json(text):
    """
    Extract valid JSON from model response
    """
    text = re.sub(r"```json|```", "", text)

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        return match.group(0)

    return text


def validate_mom(data):
    """
    Validate the full MOM structure, not just top-level keys.

    Required shape:
    {
      "summary":   str,
      "decisions": [str, ...],
      "risks":     [str, ...],
      "actions":   [{"task": str, "owner": str, "deadline": str}, ...]
    }
    """
    if not isinstance(data, dict):
        return False

    required_keys = ("summary", "decisions", "risks", "actions")
    if not all(key in data for key in required_keys):
        return False

    if not isinstance(data["summary"], str):
        return False

    for key in ("decisions", "risks"):
        if not isinstance(data[key], list):
            return False
        if not all(isinstance(item, str) for item in data[key]):
            return False

    if not isinstance(data["actions"], list):
        return False

    for action in data["actions"]:
        if not isinstance(action, dict):
            return False
        if "task" not in action:
            return False

    return True


def normalize_mom(data):
    """
    Coerce a validated MOM into a fully predictable shape so that
    downstream code (doc_generator, analytics) never hits a missing
    key or a None value.
    """
    normalized_actions = []
    for action in data.get("actions", []):
        normalized_actions.append({
            "task": str(action.get("task", "") or "").strip(),
            "owner": str(action.get("owner", "") or "TBD").strip() or "TBD",
            "deadline": str(action.get("deadline", "") or "TBD").strip() or "TBD",
        })

    return {
        "summary": str(data.get("summary", "")).strip(),
        "decisions": [str(d).strip() for d in data.get("decisions", []) if str(d).strip()],
        "risks": [str(r).strip() for r in data.get("risks", []) if str(r).strip()],
        "actions": normalized_actions,
    }


def call_model(model, prompt):
    """
    Generic OpenAI call
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert IT Project Manager. "
                    "Always return valid JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )

    return response.choices[0].message.content.strip()


# ==========================================
# MOM GENERATION
# ==========================================

def build_mom_prompt(
    notes,
    participants,
    names,
    dates,
    meeting_type,
    meeting_date
):
    return f"""
You are a Senior IT Project Manager.

Generate professional Minutes of Meeting.

Meeting Type:
{meeting_type}

Meeting Date (use this to resolve relative dates):
{meeting_date}

Participants:
{participants}

People Mentioned:
{names}

Dates Mentioned:
{dates}

Meeting Notes:
{notes}

Return ONLY valid JSON in this exact format:

{{
  "summary": "Meeting summary",
  "decisions": [
    "Decision 1"
  ],
  "risks": [
    "Risk 1"
  ],
  "actions": [
    {{
      "task": "Action item",
      "owner": "Owner Name",
      "deadline": "YYYY-MM-DD"
    }}
  ]
}}

Rules:
- Summary should be concise
- Extract decisions explicitly
- Identify risks and blockers
- Create action items with owner and deadline
- "decisions" and "risks" must be arrays of plain strings
- Each action must be an object with exactly the keys: task, owner, deadline
- ALL deadlines must be absolute dates in YYYY-MM-DD format
- Resolve relative deadlines using the Meeting Date above:
  * "today" -> the Meeting Date itself
  * "tomorrow" -> Meeting Date + 1 day
  * "next week" -> the Monday after the Meeting Date
  * "end of next week" -> the Friday of the week after the Meeting Date
  * "end of April" -> the last day of that month in the Meeting Date's year
- Never output vague deadlines like "today", "next week", or "soon"
- If owner is missing, use "TBD"
- If no deadline is stated or it cannot be resolved, use "TBD"
"""


def generate_mom(
    notes,
    participants,
    meeting_type,
    meeting_date=""
):
    try:

        names, dates = extract_entities(notes)

        prompt = build_mom_prompt(
            notes,
            participants,
            names,
            dates,
            meeting_type,
            meeting_date
        )

        # -------------------------------
        # PRIMARY ATTEMPT
        # -------------------------------
        # Fall back to the larger model only on transient errors.
        # Anything else (auth, quota, bad request) would fail the
        # same way and just waste a second round trip.

        try:
            content = call_model(
                PRIMARY_MODEL,
                prompt
            )
        except TRANSIENT_ERRORS:
            content = call_model(
                FALLBACK_MODEL,
                prompt
            )

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = json.loads(clean_json(content))

        if not validate_mom(data):
            return {
                "error": "AI returned invalid MOM structure",
                "response": content
            }

        return normalize_mom(data)

    except Exception as e:

        return {
            "error": str(e),
            "trace": traceback.format_exc()
        }


# ==========================================
# NOTES ANALYSIS
# ==========================================

def build_analysis_prompt(notes):
    return f"""
Evaluate the quality of these meeting notes against five criteria.

Notes:
{notes}

Return ONLY valid JSON in this exact format:

{{
    "criteria": {{
        "has_decisions": true,
        "has_actions": true,
        "has_owners": true,
        "has_deadlines": true,
        "has_risks": true
    }},
    "issues": [
        "Issue 1"
    ],
    "suggestions": [
        "Suggestion 1"
    ]
}}

Rules for the criteria flags — be strict:
- "has_decisions": true only if at least one explicit decision is stated
- "has_actions": true only if at least one concrete action item is stated
- "has_owners": true only if EVERY action item has a named owner
- "has_deadlines": true only if EVERY action item has a SPECIFIC deadline
  (a date or day). Vague phrases like "soon", "next week", or
  "middle of next week" count as false.
- "has_risks": true only if at least one risk or blocker is mentioned

For every criterion that is false, add a matching entry to "issues"
explaining what is missing. Use "suggestions" only for optional
improvements beyond the five criteria (e.g., adding context).
"""


def analyze_notes(notes):

    try:

        prompt = build_analysis_prompt(notes)

        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You evaluate meeting notes and "
                        "return only JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        content = response.choices[0].message.content

        data = json.loads(content)

        # Guarantee the criteria block exists with strict defaults
        criteria = data.get("criteria", {})
        data["criteria"] = {
            "has_decisions": bool(criteria.get("has_decisions", False)),
            "has_actions": bool(criteria.get("has_actions", False)),
            "has_owners": bool(criteria.get("has_owners", False)),
            "has_deadlines": bool(criteria.get("has_deadlines", False)),
            "has_risks": bool(criteria.get("has_risks", False)),
        }
        data.setdefault("issues", [])
        data.setdefault("suggestions", [])

        return data

    except Exception as e:

        return {
            "criteria": {
                "has_decisions": False,
                "has_actions": False,
                "has_owners": False,
                "has_deadlines": False,
                "has_risks": False,
            },
            "issues": [
                f"Analysis failed: {str(e)}"
            ],
            "suggestions": [
                "Check OpenAI API connectivity"
            ]
        }


# ==========================================
# CONNECTION TEST
# ==========================================

def test_openai_connection():
    """
    Useful for debugging
    """

    try:

        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with OK"
                }
            ]
        )

        return {
            "success": True,
            "message": response.choices[0].message.content
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
