import json
import re
from openai import OpenAI
from utils import extract_entities
from dotenv import load_dotenv

import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set. Check your .env file")

from openai import OpenAI
client = OpenAI(api_key=api_key)

MODEL = "gpt-4o-mini"

def clean_json(text):
    text = re.sub(r"```json|```", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def validate_mom(data):
    return isinstance(data, dict) and all(k in data for k in ["summary", "decisions", "risks", "actions"])


def build_prompt(notes, participants, names, dates, meeting_type):
    return f"""
You are a Senior IT Project Manager.

Meeting Type: {meeting_type}
Participants: {participants}
Detected Names: {names}
Detected Dates: {dates}

Convert notes into structured MOM.
Return ONLY JSON.

FORMAT:
{{
 "summary": "",
 "decisions": [],
 "risks": [],
 "actions": [{{"task": "", "owner": "", "deadline": ""}}]
}}

Notes:
{notes}
"""


def generate_mom(notes, participants, meeting_type):
    names, dates = extract_entities(notes)
    prompt = build_prompt(notes, participants, names, dates, meeting_type)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()

    try:
        data = json.loads(content)
    except:
        data = json.loads(clean_json(content))

    return data if validate_mom(data) else None


def analyze_notes(notes):
    prompt = f"""
Evaluate meeting notes quality.

Return JSON:
{{
 "is_complete": true,
 "issues": [],
 "suggestions": []
}}

Notes:
{notes}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)