from docx import Document

def create_doc(title, datetime_str, participants, mom):

    doc = Document()

    doc.add_heading("Minutes of Meeting (MoM)", 0)

    # Meeting Details
    doc.add_heading("Meeting Details", 1)
    doc.add_paragraph(f"Title: {title}")
    doc.add_paragraph(f"Date & Time: {datetime_str}")

    doc.add_paragraph("Participants:")
    participants_list = [p.strip() for p in participants.split(",")]
    for p in participants_list:
        doc.add_paragraph(p, style="List Bullet")

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

    # Actions
    doc.add_heading("Action Items", 1)
    for a in mom.get("actions", []):
        doc.add_paragraph(
            f"{a.get('task')} | Owner: {a.get('owner')} | Deadline: {a.get('deadline')}"
        )

    file_path = "MOM_Output.docx"
    doc.save(file_path)

    return file_path