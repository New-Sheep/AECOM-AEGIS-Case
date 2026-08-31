# Appendix: Technical Deep Dive and Architecture (Prototype-Accurate)

**Product:** AEGIS (AI-Enabled Grid and Infrastructure Shield)  
**Audience:** AI Solution Engineering assessors and technical reviewers  
**Repo:** https://github.com/New-Sheep/AECOM-AEGIS-Case  
**Purpose:** Algorithms, data model, inference loop, graph analytics, and GenAI/agent workflows **as built in the locked prototype**.

**Scope:** This appendix is technical only. Business case → Executive Briefing. Product strategy → PRD.  
**Honesty rule:** Anything not implemented is labeled **Roadmap / not in prototype**. Do not treat roadmap ideas as shipped features.

This file corrects an earlier Gamma/PDF appendix that mixed **target architecture** with **what the code actually runs**.

---

## Claim audit (PDF vs code)

| Earlier PDF claim | Prototype reality |
|-------------------|-------------------|
| PostgreSQL + PostGIS | **SQLite** via Django ORM (`backend/config/settings.py`) |
| Celery / Redis continuous heartbeat | **`manage.py run_heartbeat`** (batch management command) |
| Live SCADA payloads in milliseconds | **Hybrid CSV / seeded DB**; not live SGW OT |
| Last-Known-Good (LKG) clamp | **Median impute + physical clip** in preprocess |
| FastAPI | **Django REST Framework only** |
| Devil’s Advocate multi-agent L4 critique | **Not built** (stretch / roadmap) |
| GPT-4o as primary LLM | Optional **NVIDIA NIM** or **`FAKE_LLM=1`** offline briefs |
| API paths like `/assets/health/`, `/network/impact/`, `/ai/briefing/` | **Different paths** (see §5) |
| UUID primary keys everywhere | Django auto IDs + **`external_id`** / **`scada_link_id`** strings |
| Feature names `load_pct`, `oil_temp_c` | Code uses **`load`**, **`oil_temp`**, **`wind_speed`**, **`surge_level`** |
| Old Guard = only surge > elev and risk < 0.3 | Also requires **wind > 100 mph** for flood rule; **oil > 95°C** alone can conflict |

---

## Contents

1. Data architecture and ORM (as built)  
2. Inference heartbeat (as built)  
3. Classical ML and graph analytics  
4. Generative and agentic AI (as built vs roadmap)  
5. API contract reference (actual DRF routes)  
6. File map  

---

## 1. Data architecture and ORM (as built)

**Database:** SQLite file `backend/db.sqlite3` (Django `django.db.backends.sqlite3`).  
**Not in prototype:** PostgreSQL, PostGIS spatial SQL.

**Join principle (true):** `Asset` is the anchor. Telemetry and weather attach through the ORM; CSV seed joins sensors via **`scada_link_id`**.

### Logical schema (simplified to real fields)

```text
Asset
  external_id (unique), name, asset_type
  lat, lon, elevation, flood_zone, age
  scada_link_id (unique)
  replacement_cost
  risk_score, confidence, conflict_flag, drivers_json
  operational_state (normal | load_reduced | deenergized)

Telemetry (1:N from Asset)
  timestamp, load, oil_temp, voltage, battery_voltage, is_anomaly

WeatherContext (1:N from Asset, or global)
  timestamp, wind_speed, flood_surge_level, storm_category, ambient_temp

Dependency (directed edge)
  parent_id → child_id   # "feeds / supports"

AuditLog (HITL)
  user_id, asset_id, action, reason_text
  authorization_level, ai_recommendation, human_override, timestamp

ShadowLog, ScenarioClock  # demo / eval helpers
```

**Demo data:** `data/assets.csv`, `data/telemetry.csv`, `data/dependencies.csv`, plus `data/raw/` provenance inputs. See `docs/15-DATA-PROVENANCE.md`.

**Dependency honesty:** Edges are largely **inferred nearest lifelines**, not breaker-true topology.

---

## 2. Inference heartbeat (the core loop, as built)

**Command:** `python backend/manage.py run_heartbeat`  
**Not:** Celery workers or Redis queues in this prototype.

```text
Load assets + latest telemetry/weather
    → Isolation Forest  → is_anomaly
    → XGBoost           → risk_score (+ drivers)
    → Old Guard rules   → conflict_flag, confidence
    → Persist on Asset / Telemetry
```

**When it runs:** On demand after seed (and whenever an operator/assessor re-runs the command). It is a **batch refresh** for the demo map, not a continuous OT ingest loop.

### Data quality (as built)

Preprocess (`api/services/preprocess.py`):

1. Coerce numerics  
2. **Median impute** missing cells (from training bundle)  
3. **Clip** to configured physical ranges  
4. Isolation Forest may set `is_anomaly`  
5. Confidence often **1.0**, or **~0.45** if anomaly; further reduced if ConflictFlag  

This is **not** a Last-Known-Good store of the previous good sample. Saying “LKG” overstates the implementation.

**Demo hook:** Unless `--no-demo-conflict`, asset **SUB-001** may have its risk clamped low so ConflictFlag is visible for assessors.

---

## 3. Classical ML and graph analytics

Generative AI does **not** compute risk. Risk and integrity are classical ML + rules + graph.

### 3.1 Risk engine: XGBoost

**Objective:** Score imminent site risk as a continuous value in [0, 1].

**Features `FEATURE_COLS`:**

```text
load, oil_temp, wind_speed, surge_level
```

**Model:** `XGBRegressor`  
**Hyperparameters (train script):** `n_estimators=40`, `max_depth=3`, `learning_rate=0.15`, `objective=reg:squarederror`  
**Artifact:** `artifacts/xgb_risk.joblib`  
**Train:** `scripts/train_xgb.py`

**Why:** Tabular, fast, readable `feature_importances_`. Better MVP fit than LSTM/GNN without long history or true topology.

**Label honesty:** Training targets are a **synthetic physics-style formula** (`synthetic_risk_label` in `predict.py`), not multi-year SGW failure labels. Pilot would retrain on real outcomes.

**Explainability:** `top_drivers` ranks `|feature_importance × feature_value|` (global importance × current value). Not full SHAP.

### 3.2 Sensor integrity: Isolation Forest

**Objective:** Flag odd sensor vectors vs the normal cloud (integrity), separate from weather-driven risk.

**Config:** `n_estimators=100`, `contamination=0.08`, features **StandardScaled**  
**Artifact:** `artifacts/isolation_forest.joblib`  
**Code:** `api/services/anomaly.py`

**Behavior:** XGBoost still runs. Anomaly lowers confidence and can trigger **Manual Audit** on the LangGraph agent path. Heartbeat policy: keep features, degrade trust.

### 3.3 Old Guard (deterministic referee)

**Code:** `api/services/validation.py` → `evaluate_physics`

**As implemented:**

| Check | Condition |
|-------|-----------|
| Flood/wind physics failure | `surge > elevation` **and** `wind_speed > 100` mph |
| Thermal critical | `oil_temp > 95` °C |
| Model “safe” | `risk_score < 0.3` |
| **ConflictFlag** | (physics failure **or** thermal critical) **and** model safe |

**Why it makes sense:** Hybrid pattern used in safety-minded AI: ML for patterns, hard rules for false-negative catch, humans for action. This is **not** a protective relay or EMS.

**PDF correction:** The earlier appendix omitted the **wind** conjunct on the flood rule and the **thermal** path.

### 3.4 Cascade mapping: NetworkX

**Code:** `api/services/graph.py`  
**Graph:** `nx.DiGraph` of `Dependency` edges (parent → child).  
**Core call:** `nx.descendants(asset_id)` → downstream impact list.  
**UI / agent:** Prefer lifeline types (Hospital, WaterPlant, Pump) when present.

**Why:** Explainable “who fails next” without claiming power-flow physics.  
**Roadmap (not built):** ST-GAT / learned cascades, true breaker topology.

---

## 4. Generative and agentic AI (as built vs roadmap)

### 4.1 Grounded briefs and Ask AEGIS (built)

**Briefs:** Structured facts from ORM + risk + downstream (`build_asset_facts`) → grounded brief via:

- Offline **`FAKE_LLM=1`** (default, reliable demo), or  
- Optional **NVIDIA NIM** with `NVIDIA_MODEL=nvidia/nemotron-3-nano-30b-a3b` when configured  


Schema / grounding checks live in `brief_schema.py` / briefing services. The language model **phrases** structured state; it must not invent sensors.

**Ask AEGIS (assistant):** Multi-turn chat with **tool-style calls** over explain endpoints (priority list, customers, finance methodology, dependencies, region situation). Implemented in `AssistantChatView` + frontend `assistant_panel.py`. This is the main “tool calling” surface in the prototype.

### 4.2 LangGraph controlled autonomy (built; limited)

**Package:** `backend/api/agent/`  
**APIs:** `POST /api/v1/agent/run/`, `POST /api/v1/agent/resume/`  
**Nodes:** normalize / validate (IF) → predict (XGB) → impact (NetworkX) → briefing → HITL interrupts (e.g. anomaly manual audit).  
**Checkpointer:** in-process MemorySaver (demo), not Redis.

This is **agentic orchestration of existing services**, not a free-roaming multi-agent debate.

### 4.3 Devil’s Advocate L4 critique (NOT built)

The earlier PDF described Agent 1 (recommender) vs Agent 2 (public-safety Devil’s Advocate) before de-energize.

**Status: not in the prototype.** Sprint plans list it as stretch / out of scope.  
**What exists instead:** HITL form with reason + auth token `AEGIS-EXEC-DEMO`, AuditLog, and briefs that already surface downstream lifelines so humans see the trade-off.

### 4.4 Roadmap only (not in prototype)

| Idea | Status |
|------|--------|
| RAG over SOPs (Milvus / Pinecone / NERC manuals) | Not built |
| SMS / turn-by-turn crew dispatch agent | Not built |
| Sword MILP crew–spare optimizer | Not built |
| Celery weather cron + Redis checkpointer | Not built |
| Live read-only SCADA mirror | Phase 2 story, not this code |

---

## 5. API contract reference (actual Django REST routes)

Base: `http://127.0.0.1:8000/api/v1/`  
Defined in `backend/api/urls.py`.

| Endpoint | Method | Behavior (prototype) |
|----------|--------|----------------------|
| `/health/` | GET | Health check |
| `/assets/risk_map/` | GET | Map payload: scores, flags, positions |
| `/dashboard/header/` | GET | Territory / emergency header chips |
| `/assets/<asset_id>/action_brief/` | GET | Grounded action brief for a site |
| `/predict/` | POST | Per-asset / nervous-system predict path |
| `/impact/<node_id>/` | GET | NetworkX descendants / impact |
| `/brief/` | POST | Brief generation helper |
| `/control/shutdown/` | POST | HITL control (reason + token) → AuditLog |
| `/assistant/chat/` | POST | Ask AEGIS (tools / grounded replies) |
| `/explain/site/<asset_id>/` | GET | Site explanation payload |
| `/explain/region/` | GET | Region situation |
| `/explain/customers/` | GET | Customer impact helpers |
| `/explain/finance/` | GET | Finance methodology breakdown |
| `/explain/dependencies/<asset_id>/` | GET | Dependency cascade |
| `/agent/run/` | POST | LangGraph run |
| `/agent/resume/` | POST | LangGraph resume after interrupt |
| `/scenario/tick/` `/reset/` `/pause/` | POST | Demo storm clock helpers |
| `/assets/<asset_id>/forecast/` | GET | Forecast helper (demo) |

**PDF correction:** Paths such as `/api/v1/assets/health/`, `/api/v1/network/impact/`, `/api/v1/ai/briefing/` are **not** the live contract.

---

## 6. How the four technical layers work together

| Layer | Question | Built? |
|-------|----------|--------|
| Isolation Forest | Do these readings look weird? | Yes |
| XGBoost | How high is site risk? | Yes |
| Old Guard | Does physics disagree with “safe”? | Yes |
| NetworkX | Who is hurt downstream? | Yes |
| Grounded brief / Ask tools | How do we say it in plain English? | Yes |
| LangGraph orchestration | Can we run a controlled per-asset agent path? | Yes (demo checkpointer) |
| Devil’s Advocate dual LLM | Force L4 counter-argument agent | **No** |
| Celery / PostGIS / live SCADA | Enterprise OT scale | **No** |

```text
Hybrid data → Heartbeat (IF → XGB → Old Guard)
                    ↓
              Django REST + SQLite
                    ↓
         Streamlit Command Center + HITL
                    ↓
    Optional LangGraph path / Ask AEGIS tools
```

---

## 7. File map

| Path | Role |
|------|------|
| `backend/config/settings.py` | SQLite settings |
| `backend/api/models.py` | ORM |
| `backend/api/urls.py` | Real API routes |
| `backend/api/management/commands/run_heartbeat.py` | Batch inference loop |
| `backend/api/services/predict.py` | XGB score + synthetic labels |
| `backend/api/services/anomaly.py` | Isolation Forest |
| `backend/api/services/validation.py` | Old Guard |
| `backend/api/services/graph.py` | NetworkX |
| `backend/api/services/preprocess.py` | Impute / clip |
| `backend/api/agent/` | LangGraph controlled autonomy |
| `scripts/train_xgb.py` | Train XGB + IF |
| `docs/20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md` | Interview math / justification companion |
| `docs/15-DATA-PROVENANCE.md` | Data honesty |

---

## 8. Suggested assessor reading order

1. This appendix (what is actually built)  
2. `docs/20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md` (why / math)  
3. Repo `README.md` (clone → run)  
4. Live golden demo path in the README  

**One-line summary for assessors:** AEGIS ships a **Django/DRF + SQLite** Command Center with **XGBoost, Isolation Forest, Old Guard rules, NetworkX cascades, grounded briefs, Ask tools, HITL audit, and a LangGraph orchestration path**. It does **not** ship PostGIS, Celery, Devil’s Advocate dual agents, RAG, or live SCADA.

---

*Replace the prior Gamma PDF appendix with an export of this file (or attach this markdown / regenerated PDF) so written claims match the GitHub prototype.*
