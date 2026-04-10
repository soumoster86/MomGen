import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from utils import extract_entities

load_dotenv()
client = OpenAI()

MODEL = "gpt-4o-mini"
MAX_RETRIES = 2


def clean_json(text):
    text = re.sub(r"```json|```", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def validate_mom(data):
    keys = ["summary", "decisions", "risks", "actions"]
    return isinstance(data, dict) and all(k in data for k in keys)


def build_prompt(notes, participants, names, dates):
    return f"""
You are a Senior IT Project Manager.

Participants: {participants}
Detected Names: {names}
Detected Dates: {dates}

TASK:
Convert notes into structured MOM.

RULES:
- Assign owners from names if possible
- Infer deadlines from dates
- Use "TBD" if missing
- Return ONLY JSON

FORMAT:
{{
 "summary": "",
 "decisions": [],
 "risks": [],
 "actions": [
   {{"task": "", "owner": "", "deadline": ""}}
 ]
}}

NOTES:
{notes}
"""


def generate_mom(notes, participants):

    names, dates = extract_entities(notes)
    prompt = build_prompt(notes, participants, names, dates)

    for _ in range(MAX_RETRIES):
        try:
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

            if validate_mom(data):
                return data

        except Exception as e:
            print("ERROR:", e)

    return None


# -------- AI FEEDBACK LOOP --------
def analyze_notes(notes):

    prompt = f"""
Evaluate meeting notes quality.

Return JSON:
{{
 "is_complete": true/false,
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