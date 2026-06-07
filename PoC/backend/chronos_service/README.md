# AI-EFSV Chronos-Bolt Anomaly Service

Isolated FastAPI service (port 9001) that runs `amazon/chronos-bolt-small` for
time-series anomaly decision support. Falls back to a deterministic statistical
method if the model fails to load. Does not claim real ECU validation, HIL
execution, ISO 26262 compliance, or formal safety approval.

---

## Mac Setup

```bash
cd ~/Downloads/SAD-main/PoC/backend/chronos_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # installs PyTorch (CPU) + chronos
```

Start the service (keep this terminal open):
```bash
uvicorn app:app --host 127.0.0.1 --port 9001
```

On first request the model (~200 MB) downloads from Hugging Face automatically.
Pre-load before running an analysis:
```
GET http://127.0.0.1:9001/health?load_model=true
```

Then in `backend/.env` set `CHRONOS_ENABLED=true` and restart the main backend.

---

## Windows Setup

```cmd
cd SAD-main\PoC\backend\chronos_service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 9001
```

---

## Endpoint

`POST /anomaly` — accepts a structured signal observation (expected range,
observed series, protocol logs, linked requirements). Chronos forecasts the
recent target window from the context series and compares observations against
forecast quantiles and the expected range.

`GET /health` — returns model load status, device, and any load error.
`GET /health?load_model=true` — triggers model pre-load.
