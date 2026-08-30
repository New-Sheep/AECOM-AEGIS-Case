# AEGIS — AECOM AI Solution Engineer Case

**AEGIS** (AI-Enabled Grid & Infrastructure Shield) for fictional client **Southeastern Grid & Water (SGW)**.

**UI:** Streamlit Command Center for executives and operators. Plain English on the main screen. Fast standard summaries by default; **Advanced** for live AI. Click map dots to select a site; **Reduce load** / **Shut down** under the map. **Ask AEGIS** is a bottom-right widget with tool chips; write actions need **Confirm**.

**Product scope:** Multi-hazard Shield for unforeseen severe weather (any forecasted emergency). **Demo data** currently uses a coastal hurricane case study (Hurricane Ian + SW Florida GIS + Open-Meteo wind + NOAA CO-OPS surge + ETT ETTh1 oil_temp/load proxy — not SGW SCADA). See [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md).

## Docs

- [`docs/09-FINAL-LOCKED-DECISIONS.md`](docs/09-FINAL-LOCKED-DECISIONS.md)
- [`docs/11-EPIC-BACKLOG.md`](docs/11-EPIC-BACKLOG.md)
- [`docs/13-SPRINT-3-PLAN.md`](docs/13-SPRINT-3-PLAN.md)
- [`docs/14-SPRINT-4-LANGGRAPH.md`](docs/14-SPRINT-4-LANGGRAPH.md)
- [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md)
- [`docs/16-OPERATOR-UX-DYNAMIC-SIM.md`](docs/16-OPERATOR-UX-DYNAMIC-SIM.md) — chrome, idempotent controls, restore, living scenario + alarms
- [`docs/17-CRISIS-STRATEGIST-EXPLAINABILITY.md`](docs/17-CRISIS-STRATEGIST-EXPLAINABILITY.md) — site/region strategist, customers, finance transparency, grounded tools

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
# Spread Low / Watch / High / Needs attention for map demos
.\.venv\Scripts\python.exe backend\manage.py diversify_demo_map
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

The Command Center is written for first-time operators: short site names, no engineer jargon on the main screen, map click + quick actions, human approval records, and **Ask AEGIS** as a corner widget (tools + chat). Stack details stay under **Advanced** / docs.

**Operator notes**

- **Reduce load** cuts that site's load ~20% and clears that site's attention flag so the top banner count drops (demo simulation).
- **Shut down** sets load to 0 and clears that site's attention flag.
- Banner goes **2 → 1 → 0** as you handle each flagged site (acting on one site does not clear others).
- **Ask AEGIS** (sidebar expander): open the widget, use tool chips or chat. **Confirm** is required before Reduce load / Shut down from the assistant.
- Re-run `seed_aegis --flush` + `run_heartbeat` after pulling so site names (e.g. **Fort Myers Beach**) and storm label refresh.

### Demo paths

**A — Attention warning → action (Fort Myers Beach)**

1. Select **Fort Myers Beach** (or click its red map dot).
2. Read **Summary** + **Readings**. Optional: open **Ask AEGIS** → "Explain this warning" or "What should I do?" then **Confirm**.
3. Or use **Site actions** under the map / Approve form with token `AEGIS-EXEC-DEMO`.

**B — Unusual sensors check**

1. Sidebar **Advanced**: enable **Demo: fake unusual sensors**.
2. Click **Refresh this site's analysis**.
3. Banner: Approve / Reject, then open **Status**.

### API checks

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/api/v1/health/
- `POST /api/v1/predict/` `{ "asset_id": "SUB-001" }`
- `GET /api/v1/impact/SUB-001/`
- `POST /api/v1/brief/` `{ "asset_id": "SUB-001" }`
- `POST /api/v1/assistant/chat/` `{ "asset_id": "SUB-001", "message": "What should I do?", "mode": "fake" }`
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
frontend/       Streamlit Command Center (theme, map, intel, Ask AEGIS sidebar, HITL)
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
