# AI-EFSV Chronos-Bolt Anomaly Service

This isolated FastAPI service performs time-series anomaly decision support for
AI-EFSV. It defaults to `amazon/chronos-bolt-small`, which is the preferred
starting model for an RTX 4060 with 8 GB VRAM.

The service uses CUDA when available and otherwise uses CPU. If Chronos or the
model cannot be loaded, `/anomaly` returns a deterministic statistical fallback
with `metadata.ai_used=false` and a clear fallback reason.

It does not claim real ECU validation, HIL execution, ISO 26262 compliance, or
formal safety approval.

## Windows Setup

```cmd
cd "6th iteration/PoC/backend/chronos_service"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set CHRONOS_MODEL_NAME=amazon/chronos-bolt-small
uvicorn app:app --host 127.0.0.1 --port 9001
```

`amazon/chronos-bolt-small` is recommended for an RTX 4060 with 8 GB VRAM.
`amazon/chronos-bolt-base` may be tried if its memory usage and inference speed
are acceptable.

PowerShell environment override:

```powershell
$env:CHRONOS_MODEL_NAME="amazon/chronos-bolt-base"
```

If model loading or inference fails, the service returns an honest statistical
fallback with `metadata.ai_used=false`, `metadata.fallback_used=true`, and the
specific failure reason. It never reports Chronos usage unless real model
inference completed.

## Endpoint

`POST /anomaly` accepts a structured signal observation containing an expected
range, observed series, protocol log text, and linked requirement context.
Chronos forecasts the recent target window from the preceding context and the
service compares observations against forecast quantiles and the configured
expected range.
