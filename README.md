# AEGIS — AECOM AI Solution Engineer Case

**AEGIS** (AI-Enabled Grid & Infrastructure Shield) for fictional client **Southeastern Grid & Water (SGW)**.

**UI:** Redesigned Streamlit Command Center (SOC theme) — scenario strip, structured brief chips (recommendation / provider / grounding), sensor provenance (Open-Meteo · CO-OPS · ETT), LangGraph Manual Audit, L1–L4 HITL.

**Demo data:** Hybrid **Hurricane Ian + SW Florida** GIS + **Open-Meteo** wind + **NOAA CO-OPS** surge + **ETT ETTh1** oil_temp/load proxy (not SGW SCADA). See [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md).

## Docs

- [`docs/09-FINAL-LOCKED-DECISIONS.md`](docs/09-FINAL-LOCKED-DECISIONS.md)
- [`docs/11-EPIC-BACKLOG.md`](docs/11-EPIC-BACKLOG.md)
- [`docs/13-SPRINT-3-PLAN.md`](docs/13-SPRINT-3-PLAN.md)
- [`docs/14-SPRINT-4-LANGGRAPH.md`](docs/14-SPRINT-4-LANGGRAPH.md)
- [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md)

## Setup

```powershell
cd c:\Users\ankit\Documents\AECOM-AEGIS-Case
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env` defaults to `FAKE_LLM=1` (no NVIDIA key needed). For live briefs: set `NVIDIA_API_KEY` from [build.nvidia.com](https://build.nvidia.com), `FAKE_LLM=0`, and `NVIDIA_MODEL=nvidia/nemotron-3-nano-30b-a3b` (or another live catalog ID).

**Briefs:** NIM returns JSON validated by Pydantic (`ActionBrief`); Markdown is rendered for the UI. Grounding checks reject invented sensors. QA: `python scripts/eval_briefs.py` (deterministic + LLM-as-judge; FAKE by default, `--live` for NIM).

### Demo data (default) + train / seed

```powershell
.\.venv\Scripts\python.exe scripts\build_realistic_demo_data.py
.\.venv\Scripts\python.exe scripts\refresh_telemetry_realistic.py
# Open-Meteo + CO-OPS + ETT → telemetry.csv (validates; does not auto-train)
.\.venv\Scripts\python.exe scripts\train_xgb.py
# re-run train_xgb.py → skips if feature fingerprint unchanged; use --force to refit
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_aegis --flush
.\.venv\Scripts\python.exe backend\manage.py run_heartbeat
```

Offline weather rebuild after first fetch: `refresh_telemetry_realistic.py --weather-cache-only`.  
Legacy pure-RNG CSVs: `scripts\generate_mock_data.py` (not recommended for the assessor demo).

**Preprocess:** features are validated / median-imputed / range-clipped before train and inference. Isolation Forest uses a fitted `StandardScaler`; XGBoost uses cleaned raw features. Retrain is gated by `artifacts/train_fingerprint.txt` (see `docs/15-DATA-PROVENANCE.md`). LangGraph `normalize_node` only merges GIS+SCADA+weather — it is not this statistical preprocess.

## Run demo (two terminals)

**API**

```powershell
cd c:\Users\ankit\Documents\AECOM-AEGIS-Case
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

**UI (Command Center)**

```powershell
cd c:\Users\ankit\Documents\AECOM-AEGIS-Case
$env:AEGIS_API_BASE="http://127.0.0.1:8000"
.\.venv\Scripts\streamlit.exe run frontend\dashboard.py
```

The Command Center surfaces Ian scenario provenance, Pydantic brief grounding status, and LangGraph agent state (not just raw Markdown).

### Demo paths

**A — ConflictFlag → L4 (Ian / Fort Myers Beach)**

1. Select **SUB-001** (*Fort Myers Beach Tap*).
2. Read brief + raw sensors (surge vs elevation ConflictFlag).
3. L4 De-energize, token `AEGIS-EXEC-DEMO`, reason, confirm → AuditLog.

**B — LangGraph Anomaly Shield**

1. Sidebar: enable **Force Anomaly Shield**.
2. Click **Refresh agent (weather update)**.
3. Banner: Manual Audit → Approve (continues predict→impact→brief) or Reject (halt).
4. Intelligence panel shows LangGraph `action_plan` + trail.

### API checks

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/api/v1/health/
- `POST /api/v1/predict/` `{ "asset_id": "SUB-001" }`
- `GET /api/v1/impact/SUB-001/`
- `POST /api/v1/brief/` `{ "asset_id": "SUB-001" }`
- `POST /api/v1/agent/run/` `{ "asset_id": "SUB-001", "force_anomaly": true }`
- `POST /api/v1/agent/resume/` `{ "thread_id": "...", "decision": "approved", "reason_text": "..." }`

### Backtest + tests

```powershell
.\.venv\Scripts\python.exe scripts\backtest_storm.py
.\.venv\Scripts\python.exe scripts\eval_risk_model.py
.\.venv\Scripts\python.exe scripts\eval_briefs.py
.\.venv\Scripts\python.exe backend\manage.py test api
```

## Layout

```
data/           assets/telemetry/deps + raw/ (Ian GIS, open_meteo_ian, ett)
artifacts/      xgb_risk.joblib, isolation_forest.joblib
scripts/        build_realistic_demo_data, refresh_telemetry_realistic, train_xgb, backtest_storm
backend/api/agent/   LangGraph state machine
frontend/       Streamlit Command Center (theme, map, intel, HITL panels)
docs/           research + sprint plans + DATA-PROVENANCE
```

## Stack

| Layer | Choice |
|-------|--------|
| API / DB | Django + DRF + SQLite ORM |
| ML | XGBoost + Isolation Forest |
| Safety | ValidationService ConflictFlag + Anomaly Shield interrupt |
| Graph | NetworkX |
| Orchestration | **LangGraph** (MemorySaver checkpointer) |
| GenAI | NVIDIA NIM or `FAKE_LLM=1` |
| UI | Streamlit Command Center |
| Governance | L1–L4 HITL + AuditLog / ShadowLog |

## Next (Sprint 4b)

Demo hardening, video checklist, PRD + executive briefing (E9 / E10).
