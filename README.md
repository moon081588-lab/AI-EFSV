# AI-EFSV — AI Assisted ECU Verification Tool

A React + FastAPI proof-of-concept for AI-assisted automotive software verification.

## 🌐 Live Demo

**[https://active-mustard-chemicals.ngrok-free.dev](https://active-mustard-chemicals.ngrok-free.dev)**

Open the link above in any browser on any device — no installation required.

> Note: the demo runs on my personal local Mac and must be online for the link to work.

---

## 📄 The Problem

[ecu_verification_pain_demo.html](./ecu_verification_pain_demo.html) — A standalone visual showing the manual ECU verification pain points this tool addresses.

---

## 📁 Project Structure

```text
ecu_verification_pain_demo.html  ← Standalone problem-statement demo

PoC/
  backend/
    main.py
    requirements.txt
    ai_services/
  frontend/
    index.html
    package.json
    src/
      main.jsx
      styles.css
  start.sh        ← Mac launcher (starts everything with one command)
  start.bat       ← Windows launcher

sample_data/
  Requirements_correct.xlsx                   ← Standard test input
  Requirements_correct_5.xlsx                 ← 5-requirement minimal input
  Requirements_blank.xlsx                     ← Edge case: blank requirements
  Requirements_missing.xlsx                   ← Edge case: missing fields
  Requirements_wrong_format_parser_test.xlsx  ← Parser stress test
  requirements_100.csv                        ← Large CSV input (100 rows)
  draft_iso_26262_compliance_report.doc       ← Sample output report

docs/
  AI-EFSV-Demo.pptx        ← Presentation deck (9 slides)
  AI-EFSV-Demo-Script.md   ← 10–15 min demo talking points
```

---

## Running Locally

### Mac

**One-command launch:**
```bash
~/Downloads/SAD-main/PoC/start.sh
```

This opens the backend, frontend, and ngrok in separate Terminal windows automatically.

**Or manually:**

Terminal 1 — Backend:
```bash
cd ~/Downloads/SAD-main/PoC/backend
source .venv/bin/activate
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — Frontend:
```bash
cd ~/Downloads/SAD-main/PoC/frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173)

---

### Windows

Terminal 1 — Backend:
```cmd
cd "PoC\backend"
.venv\Scripts\activate
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — Frontend:
```cmd
cd "PoC\frontend"
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173)

Or use the included launcher:
```cmd
"PoC\start.bat"
```

---

## Prerequisites

| Tool | Mac | Windows |
|------|-----|---------|
| Python 3.12 | `brew install python@3.12` | [python.org](https://www.python.org/downloads/) |
| Node.js | `brew install node` | [nodejs.org](https://nodejs.org/) |
| Ollama (optional) | `brew install ollama` | [ollama.com](https://ollama.com/) |

---

## File Upload Format

Use a `.csv` or `.xlsx` Excel file containing software requirements.
Sample files are in the [`sample_data/`](./sample_data/) folder.
