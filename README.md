# AEGIS — AECOM AI Solution Engineer Case

**Prototype status: LOCKED** for submission.

**Repo:** https://github.com/New-Sheep/AECOM-AEGIS-Case

**AEGIS** (AI-Enabled Grid and Infrastructure Shield) is an AI **decision-support** Command Center for fictional client **Southeastern Grid and Water (SGW)** (8M+ residents).

| Name | Meaning | In this build? |
|------|---------|----------------|
| **Shield** | Protect critical equipment before it is destroyed | **Yes** |
| **Sword** | Restore power and water fairly after the storm | **No** (roadmap) |

AI **advises**. A person must approve reduce load / shut down / restore. No write path into real grid switching.

---

## Quick start (clone → run)

**Needs:** Python 3.11+, Git. Offline demo works with default `.env` (`FAKE_LLM=1`). No API key required.

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

Open the URL Streamlit prints (usually http://localhost:8501). Optional: add `?coach=done` to skip the coach overlay.

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

**Terminal 1:** `python backend/manage.py runserver 127.0.0.1:8000`  
**Terminal 2:**

```bash
export AEGIS_API_BASE=http://127.0.0.1:8000
streamlit run frontend/dashboard.py
```

### Smoke checks

- http://127.0.0.1:8000/api/v1/health/  
- Optional: `python backend/manage.py test api`  
- HITL demo token: `AEGIS-EXEC-DEMO`

---

## Golden demo path

1. Header: active emergency, high-risk count, decision-needed count.  
2. **Find site** → Show = **High risk** (or click a red map dot). Try Blue Heron Solar, City of Sarasota WWTP, or SUB-001 / Fort Myers Beach (ConflictFlag story).  
3. Read **Summary**, **Why this score**, downstream impact.  
4. **Reduce load** or **Shut down** with a reason + token `AEGIS-EXEC-DEMO`.  
5. **Ask AEGIS** → **Site priority list** → **Open** another site.

Optional: search `tampa` → click match → **Clear**.

---

## Architecture (as built)

```text
Hybrid demo data (maps + weather + sensor proxy)
    → Heartbeat: Isolation Forest → XGBoost → Old Guard rules → save
    → Django REST API (/api/v1/...)
    → Streamlit Command Center (map · Find site · Summary · HITL · Ask AEGIS)
```

| Layer | Tech | Role |
|-------|------|------|
| API / DB | Django + DRF + **SQLite** | Assets, telemetry, audit, seed |
| Risk | XGBoost | Site risk [0, 1] + drivers |
| Sensor integrity | Isolation Forest | Odd readings → lower confidence |
| Physics referee | Old Guard rules | ConflictFlag on false-negative risk |
| Cascades | NetworkX | Who fails next (hospitals, water, pumps) |
| Language | `FAKE_LLM=1` or optional NVIDIA NIM (`nvidia/nemotron-3-nano-30b-a3b`) | Briefs / Ask only — not the risk engine |
| Control | HITL + audit log | Human must approve protect / restore |

**Not in this prototype:** PostgreSQL/PostGIS, Celery/Redis, live SGW SCADA, unsupervised switching, Sword optimizer, production CIP certification.

Deeper tech notes: [`docs/21-APPENDIX-TECH-DEEP-DIVE-PROTOTYPE-ACCURATE.md`](docs/21-APPENDIX-TECH-DEEP-DIVE-PROTOTYPE-ACCURATE.md) and [`docs/20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md`](docs/20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md).

---

## Sample / mocked data

| Path | What |
|------|------|
| `data/assets.csv` | ~50 demo sites + estimated replacement costs |
| `data/telemetry.csv` | Sensor proxy channels |
| `data/dependencies.csv` | Inferred feed edges |
| `data/raw/` | Provenance inputs |
| `artifacts/*.joblib` | Trained XGBoost + Isolation Forest |

Honesty: Hurricane Ian–themed hybrid demo — **not** live SGW OT. Details: [`docs/15-DATA-PROVENANCE.md`](docs/15-DATA-PROVENANCE.md).

---

## Assumptions and limits (short)

- Coastal **flood/wind** case study first; heat/fire are later feature packs.  
- Dependencies are **inferred**, not breaker-true.  
- Risk training labels are **synthetic** physics-style for the demo.  
- SUB-001 may be score-clamped so ConflictFlag is visible.  
- Find-site search may need blur / another click (Streamlit).  
- Demo auth token is not production identity / CIP.

---

## Written deliverables (also submitted as PDF)

| Deliverable | In-repo markdown |
|-------------|------------------|
| D1 — PRD | [`docs/DELIVERABLE-1-PRD-AEGIS.md`](docs/DELIVERABLE-1-PRD-AEGIS.md) |
| D2 — Executive briefing | [`docs/DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`](docs/DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md) |
| Tech appendix (prototype-accurate) | [`docs/21-APPENDIX-TECH-DEEP-DIVE-PROTOTYPE-ACCURATE.md`](docs/21-APPENDIX-TECH-DEEP-DIVE-PROTOTYPE-ACCURATE.md) |
| Assessor handover | [`docs/18-PROTOTYPE-AND-PRD-HANDOVER.md`](docs/18-PROTOTYPE-AND-PRD-HANDOVER.md) |
| Assignment brief (transcribed) | [`docs/01-technical-assessment-brief.md`](docs/01-technical-assessment-brief.md) |

Further reading if needed: `docs/00` (north star), `docs/02` (domain), `docs/09` (locked decisions), `docs/15` (data provenance). Samples `03`/`04` are tone practice only.

---

## Optional: live NVIDIA briefs

Default: offline (`FAKE_LLM=1`).  
Optional live: set `NVIDIA_API_KEY`, `FAKE_LLM=0`, and keep:

```text
NVIDIA_MODEL=nvidia/nemotron-3-nano-30b-a3b
```

(from [build.nvidia.com](https://build.nvidia.com)). Not required to assess the Shield workflow.

---

## Repo layout

```text
README.md
.env.example
requirements.txt
data/          demo CSVs + raw inputs
artifacts/     trained models
scripts/       optional rebuild/train
backend/       Django + DRF + services
frontend/      Streamlit Command Center
docs/          PRD, exec briefing, tech appendix, research notes
```

---

*Not legal or operational advice. Case assessment prototype.*
