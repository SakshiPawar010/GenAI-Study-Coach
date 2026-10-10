# 🎓 GenAI Study Coach

A complete GenAI-powered Personal Study Assistant built with Python Flask and Google Gemini. This application uses an agentic AI approach with a **three-phase human-in-the-loop study session** powered by LangGraph, helping students study smarter and more effectively.

---

## ✨ Features

- **📝 Smart Summarization** — Concise topic-wise summaries from uploaded PDFs, DOCX, or plain text. Supports multiple documents at once.
- **❓ Quiz Generation** — Auto-generated MCQ quizzes with difficulty levels (easy / medium / hard)
- **🃏 Flashcards** — 8 targeted flashcards generated from your study notes
- **🗺️ Study Roadmap** — Personalized N-day study plan based on your content and weak areas
- **💬 AI Chat Tutor** — Context-aware chat assistant that answers questions about your uploaded notes
- **📊 Document Comparison** — Side-by-side comparison of two documents with key differences and study recommendations
- **🔍 Topic Detection** — Automatically detects the subject, topic, and subtopic from your notes
- **📈 Progress Tracking** — Tracks quiz history, scores, and weak areas per session
- **📄 PDF Export** — Export summaries, quizzes, flashcards, and roadmaps as PDF
- **⚡ Streaming Responses** — Real-time streaming for summaries and chat via Server-Sent Events
- **🧠 Agentic Study Session** — Three-phase human-in-the-loop study workflow powered by LangGraph

---

## 🧠 Agentic Study Session (LangGraph)

The core feature is a **three-phase agentic study session** that adapts to your performance:

```
PHASE 1:   Detect Topic → Summarize → Diagnostic Quiz
                          ⬇ (user answers quiz)
PHASE 2a:  Evaluate Quiz → [Score < 60%?]
                YES → Generate Flashcards → Targeted Quiz
                NO  → Skip remediation
                          ⬇ (user answers targeted quiz)
PHASE 2b:  Evaluate Targeted Quiz → Build Roadmap → Compile Report
```

- If you score **≥ 60%** on the diagnostic quiz → skips remediation, goes straight to roadmap
- If you score **< 60%** → generates flashcards + a harder targeted quiz on your weak areas
- Final report includes scores, weak topics, flashcards, roadmap, and full session log

---

## 🏗️ Architecture

```
User Interface (HTML/JS)
        │
        ▼
Flask Backend (app.py)
        │
   ┌────┴─────────────────────────────────┐
   │              Agents                  │
   │  SummarizerAgent   QuizAgent         │
   │  FlashcardAgent    RoadmapAgent      │
   │  ChatAgent         ComparisonAgent   │
   │  TopicDetector     StudyOrchestrator │
   └────┬─────────────────────────────────┘
        │
        ▼
  LangChain + LangGraph
        │
        ▼
   Google Gemini API
   (gemini-2.0-flash-lite)
```

---

## 📁 Project Structure

```
GenAI-Study-Coach/
├── backend/
│   ├── agents/
│   │   ├── summarizer_agent.py
│   │   ├── quiz_agent.py
│   │   ├── roadmap_agent.py
│   │   ├── flashcard_agent.py
│   │   ├── chat_agent.py
│   │   ├── comparison_agent.py
│   │   ├── topic_detector.py
│   │   └── study_orchestrator.py
│   ├── service/
│   │   ├── bedrock_client.py      # Gemini API wrapper
│   │   ├── config.py
│   │   ├── langchain_client.py
│   │   ├── document_processor.py
│   │   ├── vector_store.py
│   │   ├── doc_cache.py
│   │   ├── progress_store.py
│   │   ├── srs_store.py
│   │   ├── task_queue.py
│   │   └── pdf_exporter.py
│   ├── templates/
│   │   ├── index.html
│   │   ├── summarize.html
│   │   ├── quiz.html
│   │   ├── flashcards.html
│   │   ├── roadmap.html
│   │   └── chat.html
│   ├── static/
│   │   ├── script.js
│   │   └── style.css
│   └── app.py
├── k8s/                           # Kubernetes manifests
├── terraform/                     # AWS infrastructure (EKS, ECR, VPC)
├── Dockerfile
├── Jenkinsfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google Gemini API Key → [Get it here](https://aistudio.google.com/app/apikey)

### Local Setup

**1. Clone the repository**
```bash
git clone https://github.com/SakshiPawar010/GenAI-Study-Coach.git
cd GenAI-Study-Coach
```

**2. Create virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment**
```bash
cp .env.example .env
```
Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=<your-gemini-api-key>
MODEL_ID=gemini-2.0-flash-lite
```

**5. Run the application**
```bash
python backend/app.py
```

**6. Open in browser**
```
http://localhost:5000
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/summarize` | POST | Summarize uploaded notes/files |
| `/summarize/stream` | POST | Streaming summarization (SSE) |
| `/quiz` | POST | Generate MCQ quiz |
| `/roadmap` | POST | Generate study roadmap |
| `/flashcards` | POST | Generate flashcards |
| `/chat` | POST | Chat with AI about your notes |
| `/chat/stream` | POST | Streaming chat (SSE) |
| `/compare` | POST | Compare two documents |
| `/detect-topic` | POST | Auto-detect topic from notes |
| `/study-session/phase1` | POST | Start agentic study session |
| `/study-session/phase2a` | POST | Submit diagnostic quiz answers |
| `/study-session/phase2b` | POST | Submit targeted quiz answers |
| `/progress` | GET | Get quiz history |
| `/progress/record` | POST | Record quiz result |
| `/progress/weak-areas` | GET | Get weak areas |
| `/export/summary` | GET | Export summary as PDF |
| `/export/quiz` | GET | Export quiz as PDF |
| `/export/roadmap` | GET | Export roadmap as PDF |
| `/export/flashcards` | GET | Export flashcards as PDF |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| AI Model | Google Gemini (gemini-2.0-flash-lite) |
| Agentic Framework | LangGraph, LangChain |
| Vector Store | FAISS |
| Frontend | Vanilla JavaScript, HTML5, CSS3 |
| PDF Export | ReportLab |
| Database | SQLite |
| Containerization | Docker |
| Orchestration | Kubernetes (EKS) |
| Infrastructure | Terraform (AWS — EKS, ECR, VPC) |
| CI/CD | Jenkins |

---

## ☁️ AWS Deployment

Infrastructure is fully defined in `terraform/`:
- **ECR** — Container registry for Docker images
- **EKS** — Kubernetes cluster for running the app
- **VPC** — Networking with public/private subnets
- **IAM** — Roles and policies
- **Secrets Manager** — Secure storage for API keys

Kubernetes manifests are in `k8s/`:
- `deployment.yaml` — App deployment
- `service.yaml` — Load balancer service
- `pvc.yaml` — Persistent volume for data
- `secret.yaml` — Kubernetes secrets
- `serviceaccount.yaml` — IAM service account

---

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API Key | Required |
| `MODEL_ID` | Gemini model to use | `gemini-2.0-flash-lite` |
| `SECRET_KEY` | Flask session secret | Auto-generated |

---

## 📝 License

MIT License — Feel free to use this project for learning and development.
