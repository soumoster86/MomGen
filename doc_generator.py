from docx import Document
from io import BytesIO


def create_doc(title, datetime_str, participants, mom):
    doc = Document()

    doc.add_heading("Minutes of Meeting", 0)

    doc.add_heading("Meeting Details", 1)
    doc.add_paragraph(f"Title: {title}")
    doc.add_paragraph(f"Date & Time: {datetime_str}")

    doc.add_paragraph("Participants:")
    for p in participants.split(","):
        doc.add_paragraph(p.strip(), style="List Bullet")

    doc.add_heading("Summary", 1)
    doc.add_paragraph(mom["summary"])

    doc.add_heading("Key Decisions", 1)
    for d in mom["decisions"]:
        doc.add_paragraph(d, style="List Bullet")

    doc.add_heading("Risks", 1)
    for r in mom["risks"]:
        doc.add_paragraph(r, style="List Bullet")

    doc.add_heading("Action Items", 1)
    table = doc.add_table(rows=1, cols=3)
    table.rows[0].cells[0].text = "Task"
    table.rows[0].cells[1].text = "Owner"
    table.rows[0].cells[2].text = "Deadline"

    for a in mom["actions"]:
        row = table.add_row().cells
        row[0].text = a["task"]
        row[1].text = a["owner"]
        row[2].text = a["deadline"]

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer