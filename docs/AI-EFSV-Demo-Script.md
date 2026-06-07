# AI-EFSV Demo Script
## 10–15 Minute Walkthrough — University Term Project

---

## Before You Start (Setup Checklist)

- [ ] Run `~/Downloads/SAD-main/PoC/start.sh` — wait for all 3 terminal windows to open
- [ ] Confirm the AI status badge shows **AI 4/4** (green) in the top right of the tool
- [ ] Have your sample `.csv` file ready (use the one in `PoC/backend/sample_data/`)
- [ ] Open `active-mustard-chemicals.ngrok-free.dev` in a browser tab — confirm it loads
- [ ] Open the slide deck `AI-EFSV-Demo.pptx` in presenter mode on a second screen

---

## Slide-by-Slide Script

---

### SLIDE 1 — Title (30 sec)

> "Our term project is called AI-EFSV — AI-Assisted ECU Software Verification. The core idea is to take one of the most painful, manual processes in automotive software development — verifying that ECU software meets its safety requirements — and automate as much of it as possible using AI."

---

### SLIDE 2 — The Problem (1 min)

> "To understand why this matters, here's what the process looks like today."

**S — Slow & Manual:**
> "An engineer gets a spreadsheet of hundreds of requirements and manually figures out which test cases cover each one. This takes days per release cycle."

**E — Error-Prone:**
> "It's easy to miss a low-confidence mapping, leave a traceability gap, or forget to flag something for review. Human review at this scale is inconsistent."

**C — Compliance Burden:**
> "And then at the end, someone has to write the ISO 26262 compliance report by hand. That standard is the safety bible for automotive software, and the paperwork alone takes significant time."

---

### SLIDE 3 — Our Solution (1 min)

> "AI-EFSV replaces that manual workflow with a 5-step AI-driven pipeline."

Walk through each step:
1. **Upload** — "The engineer uploads their requirements file — CSV or Excel."
2. **Extract** — "AI automatically parses the requirements, detects boundary clues like timing constraints or voltage thresholds, and generates candidate test cases."
3. **Review** — "The engineer reviews the AI's mappings and either approves or rejects them. The tool never moves forward without human sign-off."
4. **Simulate** — "Approved test cases run through a virtual ECU verification simulation."
5. **Report** — "The AI drafts the ISO 26262 compliance report based on the outcomes."

> "The key point: what used to take days can now be done in minutes, with a full audit trail."

---

### SLIDE 4 — 4 AI Models (1.5 min)

> "We use four specialized AI models, each matched to a specific task."

- **C1 — llama3.2 (3B):** "Requirement extraction and test case generation. It reads the requirements and produces candidate test cases with rationale."
- **C2 — gemma3:4b:** "Regression prioritization. When requirements change, this model scores which tests need to be re-run first."
- **C3a — Chronos-Bolt Small:** "This is a time-series forecasting model — normally used for stock prices or weather — but we repurposed it to detect anomalies in ECU signal data from simulated tests."
- **C3b — llama3.2 (3B):** "Drafts the final ISO 26262 compliance report in natural language."

> "All four run locally on this laptop using Ollama. No cloud, no API keys."

---

### SLIDE 5 — Tech Stack (30 sec)

> "On the technical side: React frontend, Python FastAPI backend, and the Chronos service runs as a separate microservice on port 9001. The whole thing is accessible publicly through ngrok — which means you can open it right now on your phone."

---

### SLIDE 6 — Live Demo (transition slide, ~8 min total)

> "Let's see it live."

Switch to the browser. Walk through in this order:

---

#### DEMO STEP 1 — Upload (1 min)

- Navigate to the **Upload** tab
- Drag and drop (or select) the sample requirements CSV
- Point out the progress bar and stage labels while analysis runs

> "The file is being parsed, requirements extracted, and all four AI models are running in parallel. You can see the estimated progress. This usually takes 60–90 seconds because the models are running on CPU."

---

#### DEMO STEP 2 — Parser Summary (30 sec)

- After analysis, the tool auto-navigates to **Parser Summary**

> "The tool tells us exactly what it found: how many requirements, which columns it used, which sheet, any warnings about the file format. Full transparency on what the AI saw."

---

#### DEMO STEP 3 — Dashboard (30 sec)

- Click **Dashboard**

> "The dashboard gives us a high-level KPI view — requirements count, ASIL distribution, how many mappings are ready vs. flagged for review, overall confidence score."

---

#### DEMO STEP 4 — Mapping Review (2 min)

- Click **Mapping Review**
- Click **Show workspace** to expand
- Show the **Mapping Review Required** filter tab

> "This is the main engineer workspace. C1 analyzed each requirement and flagged the ones it wasn't confident about. Each card shows the AI-generated candidate test case, its rationale, detected boundary clues, and recommended historical tests."

- Point to a card with a mapping review reason code

> "Here you can see WHY the AI flagged this one — in this case it found ambiguous coverage type."

- Click **Approve** on one item, point out the decision pill updating

> "Approve moves it forward. Now let's reject one."

- Click **Reject** on another item

> "Notice — clicking Reject automatically switches to the Rejected / Recovery tab. The item doesn't disappear; it moves to a recovery workflow where the engineer can select an alternative test, request a manual design, or mark the requirement untestable."

---

#### DEMO STEP 5 — Traceability (30 sec)

- Click **Traceability**

> "The traceability matrix links every requirement to its test case, ASIL level, confidence score, AI rationale, and review status. This is the document that typically takes days to build manually."

---

#### DEMO STEP 6 — Audit Log (30 sec)

- Click **Audit Log**

> "Every action is logged — system events, AI decisions, and live engineer actions like the approve/reject we just did. You can see the timestamp on each one. This becomes part of the compliance record."

---

#### DEMO STEP 7 — Simulation (1 min)

- Click **Simulation**
- Click **Run Verification Simulation**

> "This triggers the virtual test execution — the tool runs all approved test cases through a simulated ECU environment. Chronos-Bolt is running in the background analyzing the signal telemetry."

- Wait for simulation to complete, then click **Test Results**

> "Results come back with a PASS or REVIEW status for each test case. REVIEW cases have AI anomaly detection attached — Chronos identified something unusual in the signal pattern."

---

#### DEMO STEP 8 — Anomaly Review (1 min)

- Click **Anomaly Review** (auto-navigated after simulation)

> "REVIEW items land here. For each one, the AI gives us the anomaly type, confidence score, expected vs. observed behavior, and an explanation. The engineer reviews, uploads evidence if needed, and makes a final confirm/deny decision."

- Confirm one item

> "Only after all review items are resolved does the 'Draft Report' button unlock."

---

#### DEMO STEP 9 — Draft Report (30 sec)

- Click **Draft Report**
- Scroll through the generated report sections

> "And here's the ISO 26262 compliance report — automatically drafted by C3b based on everything that happened in this session. Engineer decisions, test outcomes, anomaly findings, traceability links. This is the deliverable that would normally take days."

---

### SLIDE 7 — What We Built (1 min)

> "To summarize what we shipped: 12-section end-to-end workflow, 4 AI models running live, one file upload triggers the whole pipeline, and the output is an ISO 26262-ready package."

Point out the feature cards:
> "We were also deliberate about design choices. Engineer-in-the-loop — no AI decision is final without human approval. Graceful fallback — if Ollama isn't running, the system switches to statistical algorithms and keeps working. Full traceability. Full audit log."

---

### SLIDE 8 — Challenges (1 min)

Pick 2–3 to mention:

> "A few technical challenges worth calling out:"

- **Python 3.14 + Rust:** "Chronos uses a Rust extension that only supports Python 3.13. We had to use a forward-compatibility environment variable to make it work on 3.14."
- **React TDZ bug:** "Moving to tab-based navigation caused silent crashes on every render. The bug was a hook referencing a variable that wasn't declared yet — a JavaScript temporal dead zone error. Took a while to track down."
- **Engineer-AI trust:** "We spent a lot of time thinking about how the tool presents AI output. It's not enough to show a result — you have to show the confidence, the reasoning, and make it easy to disagree."

---

### SLIDE 9 — Thank You / Q&A (remaining time)

> "That's AI-EFSV. The code is on GitHub if you want to explore it. Any questions?"

**Common questions to prepare for:**

- *"Does this work on real ECU data?"*
  > "The pipeline is real — the sample data is simplified for the demo. The Chronos model and the AI backends are the same ones used in research contexts. The main thing needed for production use is real historical test data for C1 to learn from."

- *"Why run everything locally?"*
  > "No cloud dependency, no data leaving the machine. For automotive software this matters — requirements documents are often proprietary."

- *"What's the accuracy of the AI matching?"*
  > "We don't have formal recall/precision numbers yet — that's a future work item. What we do know is that the fallback mode produces deterministic results, so you can always compare AI vs. rule-based output."

- *"Could this be used at a real company?"*
  > "With production-quality test data and a proper ASIL-certified validation process on top, yes. The architecture decisions — audit log, traceability, engineer gates — were specifically designed with that use case in mind."

---

## Timing Summary

| Section | Target Time |
|---|---|
| Slides 1–5 (context) | ~4 min |
| Live Demo | ~8 min |
| Slides 7–8 (results/learnings) | ~2 min |
| Q&A buffer | ~1–2 min |
| **Total** | **~15 min** |

---

## Emergency Fallback

If the AI models are slow or unavailable:
> "The system has a built-in fallback mode — when AI is unavailable it uses statistical algorithms instead. You'll notice the AI badge shows fewer active models. The workflow is identical; the outputs are rule-based rather than model-generated. This was a deliberate design choice."

If ngrok is down, run locally:
> Open `http://localhost:5173` instead. Tell the audience: "The public URL is for remote access — locally it runs on port 5173."
