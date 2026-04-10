# 📄 AI-Powered MOM Generator

An intelligent **Minutes of Meeting (MOM) Generator** built using **Streamlit + Python + OpenAI**, designed to help Project Managers automatically convert raw meeting notes into structured, professional MOM documents.

---

## 🚀 Features

* 📂 Upload meeting notes (`.txt`, `.docx`)
* ✍️ Manual input support
* 🤖 AI-powered MOM generation
* 📊 Structured preview (Summary, Decisions, Risks, Actions)
* 📄 Export to Word document (`.docx`)
* 🧠 Smart formatting with professional output
* 🎯 User-friendly UI with tooltips and guidance
* 📈 Progress tracking for input completeness

---

## 🧱 Tech Stack

* **Frontend/UI**: Streamlit
* **Backend**: Python
* **AI Engine**: OpenAI GPT (gpt-4o-mini)
* **Document Generation**: python-docx

---

## 📁 Project Structure

```
MomGen/
│
├── app.py                # Main Streamlit UI
├── ai_handler.py         # AI prompt + response handling
├── utils.py              # File extraction utilities
├── doc_generator.py      # Word document creation
├── requirements.txt      # Dependencies
└── .env                  # API Key (local only)
```

---

## ⚙️ Installation

### 1. Clone the repository

```
git clone https://github.com/your-username/mom-generator.git
cd mom-generator
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Add OpenAI API Key

Create a `.env` file:

```
OPENAI_API_KEY=your_api_key_here
```

---

## ▶️ Run the App

```
streamlit run app.py
```

---

## ☁️ Deployment (Streamlit Cloud)

1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Deploy your repository
4. Add API key in **Secrets**:

```
OPENAI_API_KEY = "your_api_key_here"
```

---

## 🧠 How It Works

1. User uploads or enters meeting notes
2. AI processes notes and extracts:

   * Summary
   * Key Decisions
   * Risks & Issues
   * Action Items
3. Output is displayed in UI
4. User downloads formatted Word document

---

## 💡 Best Practices for Input

For best results:

* Use structured notes
* Include decisions and action items
* Avoid random or unformatted text

---

## ⚠️ Limitations

* AI output depends on input quality
* Requires OpenAI API key (paid usage)
* No persistent storage (yet)

---

## 🚀 Future Enhancements

* 🔐 User authentication
* 📊 Dashboard & analytics
* 🧠 Auto-detection of owners & deadlines
* 📁 MOM history storage
* 🎯 Multiple MOM templates

---


## ⭐ Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

## 📜 License

This project is licensed under the MIT License.
