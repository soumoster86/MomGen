import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

# ---------------- CONFIG ----------------
MODEL = "gpt-4o-mini"
MAX_RETRIES = 2

# ---------------- JSON CLEANER ----------------
def clean_json(text):
    text = re.sub(r"```json|```", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


# ---------------- VALIDATION ----------------
def validate_mom_structure(data):
    required_keys = ["summary", "decisions", "risks", "actions"]

    if not isinstance(data, dict):
        return False

    for key in required_keys:
        if key not in data:
            return False

    if not isinstance(data["actions"], list):
        return False

    return True


# ---------------- PROMPT ----------------
def build_prompt(notes):
    return f"""
You are a Senior IT Project Manager.

Your task is to convert meeting notes into a structured MOM.

STRICT RULES:
- Return ONLY valid JSON
- No explanation, no markdown
- Keep content concise and professional

QUALITY RULES:
- Summary should be crisp (3-5 lines)
- Decisions should be clear and final
- Risks should highlight potential blockers
- Actions must include:
    - task
    - owner (if missing → "TBD")
    - deadline (if missing → "TBD")

FORMAT:
{{
    "summary": "",
    "decisions": [],
    "risks": [],
    "actions": [
        {{"task": "", "owner": "", "deadline": ""}}
    ]
}}

MEETING NOTES:
{notes}
"""


# ---------------- MAIN FUNCTION ----------------
def generate_mom(notes):

    prompt = build_prompt(notes)

    for attempt in range(MAX_RETRIES):

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )

            content = response.choices[0].message.content.strip()

            # Try parsing
            try:
                data = json.loads(content)
            except:
                cleaned = clean_json(content)
                data = json.loads(cleaned)

            # Validate structure
            if validate_mom_structure(data):
                return data
            else:
                print(f"[WARN] Invalid structure on attempt {attempt+1}")

        except Exception as e:
            print(f"[ERROR] Attempt {attempt+1}: {e}")

    return None