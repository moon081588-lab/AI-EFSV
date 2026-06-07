# AI-EFSV — AI Assisted ECU Verification Tool

A React + FastAPI proof-of-concept for AI-assisted automotive software verification.

## 🌐 Live Demo

**[https://active-mustard-chemicals.ngrok-free.dev](https://active-mustard-chemicals.ngrok-free.dev)**

Open the link above in any browser on any device — no installation required.

> Note: the demo runs on a local Mac and must be online for the link to work.

---

## Project Structure

```text
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
  ecu_verification_pain_demo.html

start.sh        ← Mac launcher (starts everything with one command)
start.bat       ← Windows launcher
```

---

## Running Locally

### Mac

**One-command launch:**
```bash
~/Downloads/SAD-main/"6th iteration"/PoC/start.sh
```

This opens the backend, frontend, and ngrok in separate Terminal windows automatically.

**Or manually:**

Terminal 1 — Backend:
```bash
cd ~/Downloads/SAD-main/"6th iteration"/PoC/backend
source .venv/bin/activate
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — Frontend:
```bash
cd ~/Downloads/SAD-main/"6th iteration"/PoC/frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173)

---

### Windows

Terminal 1 — Backend:
```cmd
cd "6th iteration\PoC\backend"
.venv\Scripts\activate
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — Frontend:
```cmd
cd "6th iteration\PoC\frontend"
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173)

Or use the included launcher:
```cmd
"6th iteration\PoC\start.bat"
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
