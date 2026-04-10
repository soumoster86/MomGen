from docx import Document
from io import BytesIO

def create_doc(title, datetime_str, participants, mom):

    doc = Document()

    doc.add_heading("Minutes of Meeting (MoM)", 0)

    # Meeting Details
    doc.add_heading("Meeting Details", 1)
    doc.add_paragraph(f"Title: {title}")
    doc.add_paragraph(f"Date & Time: {datetime_str}")

    doc.add_paragraph("Participants:")
    for p in participants.split(","):
        doc.add_paragraph(p.strip(), style="List Bullet")

    # Summary
    doc.add_heading("Summary", 1)
    doc.add_paragraph(mom.get("summary", ""))

    # Decisions
    doc.add_heading("Key Decisions", 1)
    for d in mom.get("decisions", []):
        doc.add_paragraph(d, style="List Bullet")

    # Risks
    doc.add_heading("Risks & Issues", 1)
    for r in mom.get("risks", []):
        doc.add_paragraph(r, style="List Bullet")

    # Action Table
    doc.add_heading("Action Items", 1)

    table = doc.add_table(rows=1, cols=3)
    table.rows[0].cells[0].text = "Task"
    table.rows[0].cells[1].text = "Owner"
    table.rows[0].cells[2].text = "Deadline"

    for a in mom.get("actions", []):
        row = table.add_row().cells
        row[0].text = a.get("task", "")
        row[1].text = a.get("owner", "TBD")
        row[2].text = a.get("deadline", "TBD")

    # Save in memory
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return buffer