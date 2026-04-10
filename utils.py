from docx import Document

# Optional spaCy (graceful fallback)
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except:
    SPACY_AVAILABLE = False


def extract_text(uploaded_file):
    text = ""

    if uploaded_file.name.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")

    elif uploaded_file.name.endswith(".docx"):
        doc = Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"

    return " ".join(text.split())


def extract_entities(text):
    if not SPACY_AVAILABLE:
        return [], []

    doc = nlp(text)

    names = []
    dates = []

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            names.append(ent.text)
        elif ent.label_ == "DATE":
            dates.append(ent.text)

    return list(set(names)), list(set(dates))