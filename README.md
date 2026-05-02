<div align="center">
  <img src="./lexflow_logo.png" alt="LexFlow Logo" width="300"/>
  <h1>⚖️ LexFlow</h1>
  <p><strong>From Judgment to Action</strong></p>
  <p><em>Ensuring No Court Order Goes Unnoticed, Unverified, or Unacted Upon.</em></p>
</div>

---

## ⚖️ About LexFlow
**LexFlow** is an AI-powered court judgment intelligence system built for the **AI for Bharat Hackathon — Theme 11**. It automatically reads High Court judgment PDFs from CCMS, extracts critical directives, generates structured action plans, verifies them through a blind human-in-the-loop mechanism, and presents only trusted data to government officials on a clean dashboard.

### 🏆 Built By
**Team commitNpray** — We build fast, adapt instantly, and turn chaos into working solutions. We don't wait for perfection — we commit, iterate, and sometimes... pray. 🙏

---

## 🚨 The Problem
Every day, High Courts across India dispose of cases involving government departments. Each judgment contains critical directives — compliance orders, appeal deadlines, departmental responsibilities — requiring immediate administrative action.

Today these arrive as lengthy, complex PDFs in CCMS. Officials must manually read every document to find what needs to be done and by when. The result:
- ❌ **Delayed compliance**
- ❌ **Missed appeal windows** (limitation period lapses)
- ❌ **Court orders going unacted upon**
- ❌ **No intelligent prioritization or tracking**

---

## ✅ Our Solution
LexFlow solves this through a 5-stage intelligent pipeline:

1. **Court Judgment PDF (CCMS API)**
2. **PDF Parsing + OCR** (pdfplumber + Tesseract)
3. **RAG + LLM Extraction** (Groq LLaMA 3.3 70B)
4. **Blind Human Verification** (Law Students)
5. **Verified Government Dashboard**

### 🔑 Core USP — Blind Cross-Verification
Most systems ask a human to approve/reject AI output while showing them the AI's answer — which means they are influenced by it, not independently checking it. LexFlow's verification is **genuinely blind**:

- Law students see only the original PDF + 5 factual questions.
- AI answers are **completely hidden** until after submission.
- System cross-checks student answers vs AI extraction.
- **Match** → high confidence → auto-approved ✅
- **Mismatch** → AI hallucinated → flagged for admin review ⚑

---

## 🗂️ Project Structure

```bash
lexflow/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── database/
│   │   ├── db.py                # SQLite connection & schemas
│   ├── routes/
│   │   ├── cases.py             # Upload PDF, list cases
│   │   ├── extraction.py        # Trigger AI extraction (Groq)
│   │   ├── quiz.py              # Quiz questions + scoring
│   ├── services/
│   │   ├── pdf_parser.py        # pdfplumber + OCR fallback
│   │   ├── llm_service.py       # Groq LLaMA 3.3 API logic
│   │   └── confidence.py        # Fuzzy match scoring logic
│   └── auth/                    # JWT & Role-based Access
├── frontend/
│   ├── src/
│   │   ├── pages/               # GovDashboard, StudentPortal, AdminPanel
│   │   ├── components/          # PDFViewer, QuizPanel, UrgencyBadge
│   │   └── store/               # Zustand state management
└── README.md
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python, FastAPI |
| **Database** | SQLite |
| **AI Model** | Groq API (llama-3.3-70b-versatile) |
| **PDF Engine** | pdfplumber, pytesseract (OCR) |
| **Matching** | thefuzz (Fuzzy string matching) |
| **Frontend** | React + Vite, Vanilla CSS |
| **State** | Zustand |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Create a `.env` file in `backend/`:
```env
GROQ_API_KEY=your_key_here
JWT_SECRET=your_secret_here
```
Run: `uvicorn main:app --reload`

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 👤 Test Accounts
| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@lexflow.com | admin123 |
| **Student** | student@lexflow.com | student123 |
| **Official** | official@lexflow.com | official123 |

---

## 📝 License
Built for AI for Bharat Hackathon 2026. All rights reserved by **Team commitNpray**.

<div align="center">
  <strong>⚖️ LexFlow</strong> — From Judgment to Action<br/>
  <em>Team commitNpray 🙏</em>
</div>
