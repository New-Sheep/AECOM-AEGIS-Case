# AEGIS - AECOM AI Solution Engineer Case

**Status: PROTOTYPE LOCKED** for submission. No further feature work. Scrappy UI or small quirks are fine. Assess product thinking and the protect-first workflow.

**AEGIS** (AI-Enabled Grid and Infrastructure Shield) is an AI **decision-support** Command Center for fictional client **Southeastern Grid and Water (SGW)**.

- **Shield** = protect critical equipment before it is destroyed (this build).  
- **Sword** = restore power and water fairly after the storm (roadmap only, not in this build).

Repo: https://github.com/New-Sheep/AECOM-AEGIS-Case

---

## How this solution was developed

1. **Brainstorm:** Incomplete client brief; named gaps; domain expert input on floods, heat, and water plants.  
2. **Research:** Data silos, failure cascades, protect-then-restore priority.  
3. **Planning:** Locked stack and one operator workflow; what ships first vs later.  
4. **Implementation:** Working Command Center with hybrid sample data; human must approve actions.

Details: [`docs/18-PROTOTYPE-AND-PRD-HANDOVER.md`](docs/18-PROTOTYPE-AND-PRD-HANDOVER.md).

---

## Submission package (written + prototype)

| Deliverable | Location |
|-------------|----------|
| D1 - Product Requirements | [`docs/DELIVERABLE-1-PRD-AEGIS.md`](docs/DELIVERABLE-1-PRD-AEGIS.md) |
| D2 - Executive briefing | [`docs/DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`](docs/DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md) |
| D3 - This prototype | Code + this README |
| D3 - Video script | [`docs/DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md`](docs/DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md) |
| Assessor handover | [`docs/18-PROTOTYPE-AND-PRD-HANDOVER.md`](docs/18-PROTOTYPE-AND-PRD-HANDOVER.md) |
| Assignment brief | [`docs/01-technical-assessment-brief.md`](docs/01-technical-assessment-brief.md) |
| Data honesty | [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md) |
| Brief gap analysis | [`docs/19-GAP-ANALYSIS-BRIEF-VS-SUBMISSION.md`](docs/19-GAP-ANALYSIS-BRIEF-VS-SUBMISSION.md) |

---

## Architecture (snapshot)

```
Public maps + weather + sample sensor patterns
    → Seed and refresh (risk score · sensor check · impact graph · validation)
    → REST API
    → Command Center (map · summary · human approval · Ask AEGIS · Find site)
```

| Layer | Choice |
|-------|--------|
| API and database | Django + REST + SQLite |
| Risk | Tree model (XGBoost) with readable drivers |
| Odd sensors | Isolation Forest |
| Knock-on impact | NetworkX dependency graph |
| Plain-language briefs | Optional cloud language service, or offline demo mode |
| UI | Streamlit Command Center |
| Governance | Confirm + reason + auth token; audit log |

**Not in prototype:** live SGW control-room feeds, unsupervised switching, Sword crew optimizer, production critical-infrastructure security certification.

---

## Assumptions and limits

- Client context is incomplete by design. Working assumptions are explicit in the PRD.  
- The brief lists hurricane, flood, heatwave, and wildfire. This prototype is a **coastal flood/wind case study** first. Heat and wildfire share the same loop later; equipment oil temperature is not a full heatwave product.  
- Demo data is Hurricane Ian-themed: public Southwest Florida-style map sites, Open-Meteo wind, NOAA tide gauges for surge feel, and a public transformer time series as a **sensor proxy**. This is **not** live SGW operations data.  
- Dependency edges are inferred nearest lifelines, not true breaker topology.  
- `diversify_demo_map` spreads risk bands so the map tells a clear story.  
- Search may need a click outside the box (or another Find site control) before filters apply.  
- AI is **advisory only**. No write path into real switching. Demo auth token is not production cyber defense or CIP certification.  
- Phase 1 coordinates emergency **attention** (shared map, ranked sites, audit). It is not full field dispatch (Sword later).

---

## Setup

```powershell
cd c:\Users\ankit\Documents\AECOM-AEGIS-Case
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env` defaults to offline language mode (`FAKE_LLM=1`, no NVIDIA key). Optional live briefs: set `NVIDIA_API_KEY`, `FAKE_LLM=0`, and a model ID from [build.nvidia.com](https://build.nvidia.com).

### Seed demo (if database empty or after pull)

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_aegis --flush
.\.venv\Scripts\python.exe backend\manage.py diversify_demo_map
.\.venv\Scripts\python.exe backend\manage.py run_heartbeat
```

Optional rebuild of CSVs or models (only if regenerating data): see `docs/15-DATA-PROVENANCE.md` and scripts `build_realistic_demo_data.py`, `train_xgb.py`.

---

## Run (two terminals)

**API**

```powershell
cd c:\Users\ankit\Documents\AECOM-AEGIS-Case
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

**UI**

```powershell
cd c:\Users\ankit\Documents\AECOM-AEGIS-Case
$env:AEGIS_API_BASE="http://127.0.0.1:8000"
.\.venv\Scripts\streamlit.exe run frontend\dashboard.py
```

Open the URL Streamlit prints (typically http://localhost:8501). Use `?coach=done` to skip the coach overlay if present.

---

## Golden demo path (use for video)

1. Confirm header shows active emergency, high-risk count, decision-needed count.  
2. **Find site:** Show = **High risk** (or click a red map dot). Open a high-risk site (for example Blue Heron Solar or City of Sarasota WWTP).  
3. Read **Summary** (what is happening / why it matters / suggested next step) and skim **Why this score**.  
4. Under the map, **Reduce load** or **Shut down** with reason + token `AEGIS-EXEC-DEMO` (or quick buttons).  
5. Open **Ask AEGIS** → **Site priority list** → click **Open** on another listed site to jump the map.

Optional: search `tampa`, click a match, then **Clear**.

Auth token for forms: `AEGIS-EXEC-DEMO`.

---

## Quick API checks

- http://127.0.0.1:8000/api/v1/health/  
- Risk map / predict / impact / brief under `/api/v1/` (see handover and locked decisions docs)

```powershell
.\.venv\Scripts\python.exe backend\manage.py test api
```

---

## Layout

```
data/        assets, sensor samples, deps + raw provenance inputs
artifacts/   trained risk and sensor-check models
scripts/     data build, train, backtest, eval
backend/     Django + REST + services
frontend/    Streamlit Command Center
docs/        PRD, exec briefing, video script, research, provenance
```

---

## Supporting research (not submission)

North star, whiteboard digests, sprint plans: `docs/00`-`17`. Samples `03` and `04` are tone references only.
