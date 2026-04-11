import json
import re
import streamlit as st
from openai import OpenAI
from utils import extract_entities

api_key = st.secrets.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY missing in Streamlit secrets")

client = OpenAI(api_key=api_key)

PRIMARY_MODEL = "gpt-4o-mini"
FALLBACK_MODEL = "gpt-4o"


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
        "You are a Senior IT Project Manager.\n"
        "Return ONLY valid JSON.\n"
        "{\n"
        '"summary": "",\n'
        '"decisions": [],\n'
        '"risks": [],\n'
        '"actions": [{"task": "", "owner": "", "deadline": ""}]\n'
        "}\n\n"
        f"Meeting Type: {meeting_type}\n"
        f"Participants: {participants}\n"
        f"Names: {names}\n"
        f"Dates: {dates}\n"
        f"Notes: {notes}"
    )


def call_model(model, prompt):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def generate_mom(notes, participants, meeting_type):
    try:
        names, dates = extract_entities(notes)
        prompt = build_prompt(notes, participants, names, dates, meeting_type)

        # -------- PRIMARY ATTEMPT --------
        content = call_model(PRIMARY_MODEL, prompt)

        try:
            data = json.loads(content)
        except:
            data = json.loads(clean_json(content))

        if validate_mom(data):
            return data

        # -------- FALLBACK --------
        content = call_model(FALLBACK_MODEL, prompt)
        data = json.loads(clean_json(content))

        if validate_mom(data):
            return data

        return {"error": "Invalid JSON structure from AI"}

    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "trace": traceback.format_exc()
        }


def analyze_notes(notes):
    try:
        prompt = (
            "Evaluate meeting notes.\n"
            "Return JSON with is_complete, issues, suggestions.\n"
            f"Notes: {notes}"
        )

        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        return {
            "is_complete": False,
            "issues": [str(e)],
            "suggestions": []
        }