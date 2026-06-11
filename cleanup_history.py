"""
One-time cleanup for mom_history.json.

Removes the duplicate records created by the old rerun-save bug and
adds a unique "id" to every surviving record so the new update-by-id
save flow works on legacy data too.

Run once from your project folder:  python cleanup_history.py
A backup is written to mom_history.backup.json first.
"""
import json
import uuid
import shutil

HISTORY_FILE = "mom_history.json"
BACKUP_FILE = "mom_history.backup.json"

with open(HISTORY_FILE, "r") as f:
    data = json.load(f)

shutil.copy(HISTORY_FILE, BACKUP_FILE)

seen = set()
cleaned = []

for record in data:
    # Duplicate = same title + datetime + identical MOM content
    key = (
        record.get("title"),
        record.get("datetime"),
        json.dumps(record.get("mom", {}), sort_keys=True),
    )
    if key in seen:
        continue
    seen.add(key)

    if "id" not in record:
        record["id"] = str(uuid.uuid4())

    cleaned.append(record)

with open(HISTORY_FILE, "w") as f:
    json.dump(cleaned, f, indent=2)

print(f"Before: {len(data)} records")
print(f"After:  {len(cleaned)} records")
print(f"Backup saved to {BACKUP_FILE}")
