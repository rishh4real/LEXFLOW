

## ⚖️ About LexFlow
**LexFlow** is an AI-powered court judgment intelligence system built for the **AI for Bharat Hackathon — Theme 11**. It automatically reads High Court judgment PDFs from CCMS, extracts critical directives, generates structured action plans, verifies them through a blind human-in-the-loop mechanism, and presents only trusted data to government officials on a clean dashboard.

### 🏆 Built By
**Team commitNpray** — We build fast, adapt instantly, and turn chaos into working solutions. We don't wait for perfection — we commit, iterate, and sometimes... pray. 🙏

---
👥 Team Members

Shaurya Sharma -- Teach lead + Team lead [ rishhhsharmaaa@gmail.com]

Aatifa Aftab -- Quality Assurance + Prototype Designer [atikaa@student.iul.ac.in]

Mayank choudhary -- Quality Assurance + Support Developer [mayanknst2028@gmail.com]

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

## 🌐 Live Demo

- **App:** https://lexflow-beta.vercel.app
- **Backend API:** https://lexflow-1-k5cc.onrender.com
- **Database health:** https://lexflow-1-k5cc.onrender.com/health/db

---

## 🗂️ Project Structure

```bash
lexflow/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── database/
│   │   ├── mongo.py             # MongoDB Atlas + GridFS connection
│   │   ├── local_store.py       # Local development fallback store
│   ├── routes/
│   │   ├── cases.py             # Upload PDF, list cases
│   │   ├── extraction.py        # Trigger AI extraction (Groq)
│   │   ├── quiz.py              # Quiz questions + scoring
│   │   ├── files.py             # Serve stored PDFs
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
| **Database** | MongoDB Atlas |
| **PDF Storage** | MongoDB GridFS |
| **AI Model** | Groq API (llama-3.3-70b-versatile) |
| **PDF Engine** | pdfplumber, pytesseract (OCR) |
| **Matching** | thefuzz (Fuzzy string matching) |
| **Frontend** | React + Vite, Tailwind CSS |
| **State** | Zustand |

---

## 🚀 Deployment

The frontend is deployed on **Vercel** and the backend is deployed on **Render**.

### Backend Environment Variables
Set these on the Render backend service:

```bash
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/<optional>?retryWrites=true&w=majority
MONGODB_DB_NAME=lexflow
GROQ_API_KEY=your-groq-key
JWT_SECRET=your-jwt-secret
ENVIRONMENT=production
```

### MongoDB Atlas Setup
1. Create a free Atlas cluster at `https://cloud.mongodb.com`
2. Create a DB user + password
3. Network Access: allow `0.0.0.0/0` (hackathon demo)
4. Copy the Python driver connection string and use it as `MONGODB_URI`
5. Confirm deployment health at `https://lexflow-1-k5cc.onrender.com/health/db`

### Frontend Environment
The frontend API base URL is controlled by `VITE_API_URL`.

For production, point it to:

```bash
VITE_API_URL=https://lexflow-1-k5cc.onrender.com
```

### Local Development
From the repository root:

```bash
chmod +x launch.sh
./launch.sh
```

This script will:
- create and activate the backend Python environment
- install backend and frontend dependencies if needed
- start the backend on `http://localhost:10000`
- start the frontend on `http://localhost:5173`

#### Notes
- PDFs are served from the backend via `GET /files/{file_id}`
- If MongoDB is unavailable locally, the backend can use a disk-backed fallback store for development.

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
