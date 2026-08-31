# AEGIS — AECOM AI Solution Engineer Case

**Prototype status: LOCKED** for submission. Assess product judgment and the protect-first workflow; small UI quirks are OK.

**Repo:** https://github.com/New-Sheep/AECOM-AEGIS-Case

**AEGIS** (AI-Enabled Grid and Infrastructure Shield) is an AI **decision-support** Command Center for fictional client **Southeastern Grid and Water (SGW)** (8M+ residents).

| Name | Meaning | In this build? |
|------|---------|----------------|
| **Shield** | Protect critical equipment before it is destroyed | **Yes** (core workflow) |
| **Sword** | Restore power and water fairly after the storm | **No** (roadmap only) |

AI **advises**. A person must approve reduce load / shut down / restore. Nothing writes into real grid switching.

---

## For assessors (Deliverable 3 checklist)

| Brief requirement | Where it lives |
|-------------------|----------------|
| All code to run the prototype | This repo (`backend/`, `frontend/`, `scripts/`) |
| README with setup and run | **This file** (Quick start below) |
| Architecture, assumptions, limitations | Sections below + linked docs |
| Sample / mocked data | `data/` (+ `data/raw/`); honesty in [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md) |
| Video (5–10 min) | Record using [`docs/DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md`](docs/DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md) |

**One core workflow to walk:** emergency Command Center → high-risk site → risk / impact / brief → human-approved protect action → Ask AEGIS priority jump.

---

## Quick start (clone → run)

**Needs:** Python 3.11+ recommended, Git. Works offline with default `.env` (`FAKE_LLM=1`). No cloud API key required for the demo.

### Windows (PowerShell)

```powershell
git clone https://github.com/New-Sheep/AECOM-AEGIS-Case.git
cd AECOM-AEGIS-Case

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_aegis --flush
.\.venv\Scripts\python.exe backend\manage.py diversify_demo_map
.\.venv\Scripts\python.exe backend\manage.py run_heartbeat
```

**Terminal 1 — API**

```powershell
cd AECOM-AEGIS-Case
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

**Terminal 2 — UI**

```powershell
cd AECOM-AEGIS-Case
$env:AEGIS_API_BASE="http://127.0.0.1:8000"
.\.venv\Scripts\streamlit.exe run frontend\dashboard.py
```

Open the URL Streamlit prints (usually http://localhost:8501). Add `?coach=done` to skip the coach overlay if shown.

### macOS / Linux

```bash
git clone https://github.com/New-Sheep/AECOM-AEGIS-Case.git
cd AECOM-AEGIS-Case

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python backend/manage.py migrate
python backend/manage.py seed_aegis --flush
python backend/manage.py diversify_demo_map
python backend/manage.py run_heartbeat
```

**Terminal 1 — API**

```bash
python backend/manage.py runserver 127.0.0.1:8000
```

**Terminal 2 — UI**

```bash
export AEGIS_API_BASE=http://127.0.0.1:8000
streamlit run frontend/dashboard.py
```

### Smoke checks

- API health: http://127.0.0.1:8000/api/v1/health/  
- Optional tests: `python backend/manage.py test api` (from repo root with venv active)

**HITL demo token:** `AEGIS-EXEC-DEMO` (not a real secret).

---

## Golden demo path (video / live session)

1. Header: active emergency, high-risk count, decision-needed count.  
2. **Find site** → Show = **High risk** (or click a red map dot). Open a high-risk site (e.g. Blue Heron Solar, City of Sarasota WWTP, or SUB-001 / Fort Myers Beach for ConflictFlag story).  
3. Read **Summary**, **Why this score**, downstream / impact story.  
4. **Reduce load** or **Shut down** with a reason + token `AEGIS-EXEC-DEMO`.  
5. **Ask AEGIS** → **Site priority list** → **Open** another site.

Optional: search `tampa` → click match → **Clear**.  
Full narration: [`docs/DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md`](docs/DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md).

---

## Architecture (how the prototype is built)

```text
Hybrid demo data (maps + weather + sensor proxy)
        │
        ▼
Heartbeat: Isolation Forest → XGBoost → Old Guard rules → save
        │
        ▼
Django REST API  (/api/v1/...)
        │
        ▼
Streamlit Command Center
  map · Find site · Summary · Why this score · HITL · Ask AEGIS
```

| Layer | Tech | Role |
|-------|------|------|
| API / DB | Django + DRF + SQLite | Assets, telemetry, audit, seed |
| Risk | **XGBoost** | Site risk score [0, 1] + feature drivers |
| Sensor integrity | **Isolation Forest** | Odd readings → lower confidence |
| Physics referee | **Old Guard** rules | ConflictFlag if physics says danger but model looks “safe” |
| Cascades | **NetworkX** | Who fails next (hospitals, water, pumps) |
| Language | Offline `FAKE_LLM=1` or optional NVIDIA NIM | Plain-English briefs only (not the risk engine) |
| UI | Streamlit | Operator Command Center |
| Control | HITL + audit log | Human must approve protect / restore |

**Beyond chatbots (brief interest):** forecasting-style risk scoring, anomaly detection, graph impact, grounded GenAI phrasing. Crew optimization (Sword) and computer vision are roadmap.

Deeper “why / math / code map”: [`docs/20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md`](docs/20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md).

---

## Sample and mocked data

| Path | What it is |
|------|------------|
| `data/assets.csv` | ~50 demo sites (names, coords, estimated `replacement_cost`) |
| `data/telemetry.csv` | Sensor-like channels (ETT transformer series used as **proxy**) |
| `data/dependencies.csv` | Inferred feed edges (not true breaker topology) |
| `data/raw/` | Public-style GIS / Ian track / weather cache inputs |
| `artifacts/xgb_risk.joblib` | Trained risk model |
| `artifacts/isolation_forest.joblib` | Trained anomaly model |

**Honesty:** This is a Hurricane Ian–themed **hybrid** demo (public Southwest Florida–style locations + Open-Meteo / NOAA-style weather feel + ETT as SCADA proxy). It is **not** live SGW control-room data. Full tags: [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md).

Optional rebuild (not required to demo): `scripts/build_realistic_demo_data.py`, `scripts/train_xgb.py`.

---

## Assumptions and limitations

| Topic | Working position |
|-------|------------------|
| Incomplete client brief | Explicit assumptions in the PRD; clarity over polish |
| Hazards | Brief lists hurricane, flood, heatwave, wildfire. **Prototype is coastal flood/wind first.** Heat/fire reuse the same loop later |
| “Temperature” in model | Mostly **equipment oil temp**, not a full heatwave product |
| Dependencies | Nearest-lifeline **inferred** edges |
| Risk labels | Physics-ish **synthetic** labels for learnable demo (see tech deep dive) |
| ConflictFlag demo | SUB-001 may be score-clamped so assessors always see Old Guard |
| Search UI | Streamlit may need blur / another click before Find filters apply |
| Emergency coordination | Phase 1 = shared map, ranked sites, audit. **Not** full dispatch (Sword later) |
| Security | Advisory + demo token. **Not** production CIP / hardened OT |
| Autonomy | **0%** unsupervised switching by design |

---

## Submission package (written + code)

| Deliverable | File |
|-------------|------|
| D1 — PRD | [`docs/DELIVERABLE-1-PRD-AEGIS.md`](docs/DELIVERABLE-1-PRD-AEGIS.md) |
| D2 — Executive briefing | [`docs/DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`](docs/DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md) |
| D3 — Prototype | This repo + README |
| D3 — Video script | [`docs/DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md`](docs/DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md) |
| Assessor / interview handover | [`docs/18-PROTOTYPE-AND-PRD-HANDOVER.md`](docs/18-PROTOTYPE-AND-PRD-HANDOVER.md) |
| Official brief (transcribed) | [`docs/01-technical-assessment-brief.md`](docs/01-technical-assessment-brief.md) |

---

## Document map (deeper reading)

| If you want… | Read |
|--------------|------|
| How we thought (brainstorm → build) | [`docs/18-PROTOTYPE-AND-PRD-HANDOVER.md`](docs/18-PROTOTYPE-AND-PRD-HANDOVER.md) |
| Product requirements (9 AECOM sections) | [`docs/DELIVERABLE-1-PRD-AEGIS.md`](docs/DELIVERABLE-1-PRD-AEGIS.md) |
| Business case, KPIs, FAQ | [`docs/DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`](docs/DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md) |
| XGBoost / IF / Old Guard / NetworkX explained | [`docs/20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md`](docs/20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md) |
| Data sources and proxies | [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md) |
| Brief vs package gaps (closed) | [`docs/19-GAP-ANALYSIS-BRIEF-VS-SUBMISSION.md`](docs/19-GAP-ANALYSIS-BRIEF-VS-SUBMISSION.md) |
| Internal thinking log | [`docs/00-AEGIS-NORTH-STAR.md`](docs/00-AEGIS-NORTH-STAR.md) |
| Domain brainstorm | [`docs/02-domain-expert-brainstorm-electrical-stp.md`](docs/02-domain-expert-brainstorm-electrical-stp.md) |
| Architecture diagrams (research) | [`docs/10-SYSTEM-DIAGRAMS.md`](docs/10-SYSTEM-DIAGRAMS.md) |
| Locked product decisions | [`docs/09-FINAL-LOCKED-DECISIONS.md`](docs/09-FINAL-LOCKED-DECISIONS.md) |

Samples `docs/03` and `docs/04` are **tone practice only**, not the submission.

Research digests `docs/05`–`08`, sprint notes `docs/12`–`17`: supporting context, not required reading to run the app.

---

## Repo layout

```text
README.md          ← you are here
.env.example       ← copy to .env (FAKE_LLM=1 by default)
requirements.txt
data/              ← demo CSVs + raw provenance inputs
artifacts/         ← trained XGBoost + Isolation Forest
scripts/           ← data build, train, eval (optional)
backend/           ← Django + DRF + ML/graph/HITL services
frontend/          ← Streamlit Command Center (dashboard.py)
docs/              ← PRD, exec brief, video script, handover, tech deep dive
```

---

## Optional: live language briefs

Default is offline demo mode (`FAKE_LLM=1` in `.env`). For optional live briefs: set `NVIDIA_API_KEY`, `FAKE_LLM=0`, and a model ID from [build.nvidia.com](https://build.nvidia.com). Not required to assess the Shield workflow.

---

## How this solution was developed

1. **Brainstorm** — Incomplete brief; named gaps; domain expert on floods, heat, water plants.  
2. **Research** — Data silos; power → water cascades; protect then restore.  
3. **Planning** — Locked one operator workflow; storm case study first.  
4. **Implementation** — Working Command Center; hybrid data; human must approve actions.

---

*Not legal or operational advice. First-pass decision support for a case assessment.*
