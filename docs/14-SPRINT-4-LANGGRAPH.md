# AEGIS Sprint 4a — LangGraph Controlled Autonomy

**Status:** ✅ DONE (2026-08-29)  
**Code home:** `c:\Users\ankit\Documents\AECOM-AEGIS-Case`  
**Epics:** E11 Agentic LangGraph (+ thin nervous-system APIs)

---

## Goal

```
weather refresh → LangGraph
  normalize → validate (Isolation Forest)
    → anomaly? interrupt Manual Audit → resume
    → predict (XGBoost) → impact (NetworkX) → briefing (NVIDIA/FAKE)
  → Streamlit updates from graph state
```

Heartbeat (`run_heartbeat`) remains the **batch** map scorer. LangGraph is the **per-asset agentic** path.

---

## Package

| Path | Role |
|------|------|
| `backend/api/agent/state.py` | `AegisGraphState` TypedDict |
| `backend/api/agent/nodes.py` | normalize / validate / human_review / predict / impact / briefing |
| `backend/api/agent/graph.py` | compile + MemorySaver + `run_agent` / `resume_agent` |

Checkpointer: in-process **MemorySaver** (demo). Production would use Redis/Postgres checkpointer + Celery — not in this sprint.

---

## APIs

| Method | Path |
|--------|------|
| POST | `/api/v1/predict/` |
| GET | `/api/v1/impact/<node_id>/` |
| POST | `/api/v1/brief/` |
| POST | `/api/v1/agent/run/` (`force_anomaly` for demo interrupt) |
| POST | `/api/v1/agent/resume/` (`decision`: approved\|rejected) |

---

## Streamlit

Sidebar: **Refresh agent (weather update)** + **Force Anomaly Shield**.  
Interrupted → Manual Audit Approve/Reject. Completed → Intelligence shows LangGraph `action_plan`.

---

## Out of scope

Devil’s Advocate LLM, Celery cron, PostGIS, video/PRD (Sprint 4b).

---

## Demo

```powershell
# API
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000

# UI — Force Anomaly Shield → Refresh agent → Approve
$env:AEGIS_API_BASE="http://127.0.0.1:8000"
.\.venv\Scripts\streamlit.exe run frontend\dashboard.py
```
