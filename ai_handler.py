import json
import re
import streamlit as st
from openai import OpenAI
from utils import extract_entities

# -------- API KEY (Cloud Safe) --------
api_key = st.secrets.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in Streamlit secrets")

client = OpenAI(api_key=api_key)
MODEL = "gpt-4o-mini"


def clean_json(text):
    text = re.sub(r"```json|```", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def validate_mom(data):
    return isinstance(data, dict) and all(
        k in data for k in ["summary", "decisions", "risks", "actions"]
    )


def build_prompt(notes, participants, names, dates, meeting_type):
    return (
        f"You are a Senior IT Project Manager.\n"
        f"Meeting Type: {meeting_type}\n"
        f"Participants: {participants}\n"
        f"Names: {names}\n"
        f"Dates: {dates}\n"
        f"Return MOM JSON with summary, decisions, risks, actions.\n"
        f"Notes: {notes}"
    )


# -------- GENERATE MOM --------
def generate_mom(notes, participants, meeting_type):
    try:
        names, dates = extract_entities(notes)
        prompt = build_prompt(notes, participants, names, dates, meeting_type)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()

        try:
            data = json.loads(content)
        except:
            data = json.loads(clean_json(content))

        return data if validate_mom(data) else None

    except Exception as e:
        return {"error": str(e)}


# -------- ANALYZE NOTES --------
def analyze_notes(notes):
    try:
        prompt = (
            "Evaluate meeting notes quality.\n"
            "Return JSON with is_complete, issues, suggestions.\n"
            f"Notes: {notes}"
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        return {"is_complete": False, "issues": [str(e)], "suggestions": []}