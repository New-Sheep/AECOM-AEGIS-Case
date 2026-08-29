# AEGIS — Final Locked Decisions (PRD · Stack · Algorithms)

**Status:** Accumulating final locks from AI tutor (more screenshots incoming)  
**Purpose:** Single file for **authoritative** PRD / prototype / Cursor build decisions. Supersedes conflicting notes in `00-AEGIS-NORTH-STAR.md` and whiteboard digests `05`–`08` when they disagree.  
**Product:** AEGIS — AI-Enabled Grid & Infrastructure Shield  
**Client:** Southeastern Grid & Water (SGW)

---

## How to use

| Audience | Use this file for |
|----------|-------------------|
| PRD drafting | Locked architecture, AI stack, MVP algorithm choices |
| Prototype / Cursor | Exact tech stack + system prompt constraints |
| Interview | Why XGBoost + NetworkX (not GNN) for MVP |

---

## Lock batch 1 — Cursor system alignment (tech stack & AI logic)

**Source:** Final whiteboard — “AEGIS: Cursor System Alignment”

### Core infrastructure (LOCKED)

| Layer | Choice | Notes |
|-------|--------|-------|
| **Backend** | **Django 4.2+** + **Django REST Framework (DRF)** | DRF = single source of truth for asset status |
| **Database** | **PostgreSQL + PostGIS** | GIS coordinate math |
| **Task queue** | **Celery + Redis** | Long-running AI inference without blocking UI |
| **UI (options)** | **Streamlit** (simple prototype) **or** Django Templates + **Chart.js** + **Leaflet.js** | Pick one for build; both approved |

### AI / ML stack — “The Brain” (LOCKED for MVP)

| Role | Choice | Input → Output / job |
|------|--------|----------------------|
| **Primary predictor** | **XGBoost** | CSV/Parquet SCADA → failure probability **0.0–1.0** |
| **Graph engine** | **NetworkX** | Adjacency (substations → hospitals); **Dijkstra** + **centrality** |
| **Sanity filter** | **scikit-learn Isolation Forest** | Unsupervised anomaly detection on sensor feeds |
| **GenAI layer** | **NVIDIA NIM** (OpenAI-compatible HTTP) | Summarize DRF JSON → executive briefs — see batch 7; **no OpenAI keys** |

### Cursor / codegen system prompt (LOCKED)

> Ignore all previous mentions of **GNNs** (Graph Neural Networks) or deep neural networks for the MVP. Implement a Python-based pipeline using **XGBoost** for tabular risk prediction and **NetworkX** for graph-based dependency mapping. Use **Django DRF** as the single source of truth for asset status.

### Implications (this batch)

- **MVP algorithms:** XGBoost + NetworkX + Isolation Forest + GenAI briefing — **not** GNN / ST-GAT / deep nets in code.
- **Backend lock:** **Django/DRF** (not FastAPI-first). Earlier FastAPI preference in digests/`00` is **overridden**.
- GNN / deep learning remain **PRD roadmap / interview depth only**, not MVP implementation.

---

## Lock batch 2 — Data schema, pipeline & InferenceService

**Source:** Final whiteboard — “2. Data Schema & Pipeline” + “The AEGIS Heartbeat”

### Unified data model — Django ORM (LOCKED for MVP)

| Model | Fields | Notes |
|-------|--------|-------|
| **Asset** | `id`, `name`, `type` (Transformer / Pump), `lat`, `lon`, `gis_id`, **`scada_link_id`**, `risk_score` | **`scada_link_id`** is the critical join key GIS ↔ SCADA. Persist XGBoost output on `risk_score`. |
| **Telemetry** | `asset` (FK), `timestamp`, `load`, `oil_temp`, `voltage`, `is_anomaly` | Live / mock SCADA heartbeats; anomaly flag from Isolation Forest |
| **WeatherContext** | `timestamp`, `wind_speed`, `flood_surge_level`, `storm_category` | External weather / surge context |
| **Dependency** | `parent_asset` (FK), `child_asset` (FK) | Builds the **NetworkX** graph (e.g. substation → hospital) |

### Cursor data strategy — `InferenceService` (LOCKED)

Create a Django service layer **`InferenceService`** that:

1. **Query** — latest `Telemetry` + `WeatherContext` for a given `Asset`
2. **Featurize** — vector `[load, oil_temp, wind_speed, surge_level]`
3. **Infer** — pass vector to loaded **XGBoost** model
4. **Persist** — write resulting `risk_score` onto the `Asset` row

### The AEGIS Heartbeat — continuous pipeline pulse (LOCKED)

```
1. INGEST      → Fetch CSV / API
2. NORMALIZE   → Map SCADA ID → Asset ID  (via scada_link_id)
3. FEATURIZE   → Merge weather + telemetry → vector
4. INFERENCE   → XGBoost .predict()
5. PERSIST     → Save risk_score to DB
```

This is the canonical MVP data loop (“continuous pipeline pulse”). Celery jobs should drive or wrap this heartbeat so inference does not block the UI.

### Implications (this batch)

- Normalize step is non-negotiable: **SCADA ID ↔ Asset ID** via `scada_link_id`
- Feature vector for MVP predictor is explicitly **four floats**: load, oil_temp, wind_speed, surge_level
- `Dependency` edges are the graph source of truth for NetworkX Dijkstra / centrality
- `is_anomaly` lives on Telemetry; `risk_score` lives on Asset

---

## Lock batch 3 — API contract, Streamlit UI & Shield interaction loop

**Source:** Final whiteboard — “3. API Contract & Frontend Logic” + “The Shield Interaction Loop”

### DRF API specifications (LOCKED)

| Endpoint | Method | Contract |
|----------|--------|----------|
| `/api/v1/assets/risk_map/` | **GET** | Serializer: `id`, `name`, `coords`, `current_risk`, `impact_count` |
| `/api/v1/assets/<id>/action_brief/` | **GET** | Triggers **NVIDIA NIM** briefing service: aggregate risk + dependencies → **Markdown** summary |
| `/api/v1/control/shutdown/` | **POST** | Payload: `asset_id`, `authorization_token`, `reason_text` |

### Cursor UI prompt — Streamlit dashboard (LOCKED)

Build a Streamlit dashboard that:

1. **GET** `/api/v1/assets/risk_map/` and render a map with color-coded markers:
   - **Green:** risk &lt; 0.3  
   - **Yellow:** 0.3–0.7  
   - **Red:** risk &gt; 0.7  
2. On marker click → show sidebar with Markdown from **`action_brief`** for that asset  
3. **Confirm Shutdown** button → **POST** `/api/v1/control/shutdown/` with **mandatory Reason** field  

### The Shield Interaction Loop (LOCKED UX flow)

```
1. Dash Load
2. Fetch JSON          ← risk_map
3. Render              ← Leaflet markers (color by risk)
4. On Click            ← fetch action_brief
5. Modal / sidebar     ← show Markdown brief
6. Shutdown            ← confirm + reason (then loop)
         └──────── Loop back to Dash Load ────────┘
```

### Implications (this batch)

- Frontend for MVP is **Streamlit** + map markers (Leaflet-style coloring)
- Primary user workflow = **risk map → brief → HITL shutdown with reason**
- `impact_count` on risk_map ties NetworkX dependency fan-out into the map payload
- Shutdown is **POST + auth token + reason** (audit-ready); not autonomous

---

## Lock batch 4 — Logic, safety, evaluation & confusion matrix

**Source:** Final whiteboard — “4. Logic, Safety & Evaluation” + “AEGIS Confusion Matrix”

### The Referee — heuristic override (LOCKED)

**Hard rule (runs alongside XGBoost):**

```
IF surge_level > asset_elevation AND wind_speed > 100mph
THEN risk = CRITICAL
```

| Condition | Behavior |
|-----------|----------|
| XGBoost says **Safe**, physics says **Flood** | Raise **Conflict Warning** → escalate to human |
| Low risk | Auto-shedding *(policy note: confirm vs suggest-only for MVP HITL)* |
| High risk | Human review |
| Critical | **Executive authorization** |

### Cursor safety & eval prompt (LOCKED)

> Implement a **`ValidationService`** that compares the XGBoost `risk_score` against a hardcoded **elevation-vs-surge** rule.  
> If the rule predicts **Failure** but XGBoost is **Safe**, the API response must include a **`ConflictFlag`**.  
> Also create a **Backtest** script that loads historical storm CSVs and calculates **Recall** and **Lead-Time** for predicted failures.

### Evaluation strategy — “The Proof” (LOCKED)

| Method | Detail |
|--------|--------|
| **Backtesting** | Run model vs historical hurricane data (e.g. **2012 Sandy** logs) |
| **Primary metrics** | **Recall** (do not miss failures) · **Lead-time** (hours of advance warning) |
| **Shadow mode** | Log AI *predicted* actions vs human *actual* actions; surface discrepancies |

### AEGIS Confusion Matrix (LOCKED priority)

|  | AI: Flood | AI: Safe |
|--|-----------|----------|
| **Actual: Flooded** | **True Positive** — Success | **False Negative** — ⚠ **CATASTROPHIC** |
| **Actual: Safe** | **False Positive** — Safe/false alarm | **True Negative** — No event |

**Goal: Minimize False Negatives at all costs** (optimize for recall / safety over precision comfort).

### Implications (this batch)

- Two-brain safety: **XGBoost + Old Guard / Referee heuristics** + `ConflictFlag` in API
- `ValidationService` is a first-class backend component (not optional polish)
- Prototype should include a **backtest script** (even on mock/historical CSVs)
- PRD eval section must state FN ≫ FP cost and recall/lead-time as headline metrics

---

## Lock batch 5 — Research gap closure (product · data · UI · governance)

**Source:** Cross-check of AI tutor digests `05`–`08` + domain expert `02` vs batches 1–4.  
**Purpose:** Pull major tutor/PRD misses into the locked baseline without undoing batches 1–4.

### 5.1 Product strategy (LOCKED for PRD + narrative)

| Pillar | Lock |
|--------|------|
| Strategy | **Shield first, Sword second** |
| P1 | Asset protection — zero-spare CapEx catastrophe |
| P2 | Equitable restoration — PUC / brand / lifelines (roadmap build) |
| P3 | Data unification + anomaly / confidence under storm degradation |
| Cascade story | Power failure → water/STP/pumps → hospitals/society → further grid stress |
| Trust ladder | **Backtest → Shadow mode → Pilot** on few high-value assets |
| Command center | **Map (GIS) · Logic (AI) · Action (Ops)** |

### 5.2 Big Three assets (LOCKED)

| Asset | Metaphor | Primary signals |
|-------|----------|-----------------|
| **Bulk power transformer** | Heart | `oil_temp`, `load` (+ heat-wave ambient context) |
| **Control-room DC batteries** | Nervous system | `battery_voltage`; **elevation vs flood/surge** |
| **Switchgear** | Joints | breaker/switch **status**; enables re-route to hospitals |

Asset `type` enum for MVP mock data must include at least:  
`Transformer`, `Battery`, `Switchgear`, `Pump`, `Hospital`, `WaterPlant` (dependency targets may be non-powered nodes).

### 5.3 Extended ORM (LOCKED — additive to batch 2)

| Model / field | Add |
|---------------|-----|
| **Asset** | `elevation`, `age`, `replacement_cost`, `flood_zone`, `last_service_date`, `confidence` (0–1) |
| **Telemetry** | `battery_voltage`, `switch_status` (optional), `load_rate_of_change` (optional temporal proxy) |
| **AuditLog** | `user_id`, `asset_id`, `action`, `reason_text`, `authorization_level`, `ai_recommendation`, `human_override` (bool), `timestamp`, `outcome` |
| **ShadowLog** *(eval)* | `asset_id`, `ai_predicted_action`, `human_actual_action`, `timestamp` |
| **StormScenario / fixture** | Historical CSV metadata for backtests (e.g. Sandy-style runs) |

`scada_link_id` and `risk_score` remain as in batch 2.

### 5.4 Feature vector & multi-hazard (LOCKED)

**Core inference vector (batch 2 — unchanged):**  
`[load, oil_temp, wind_speed, surge_level]`

**Additive context for rules / XAI / heat path (not all must enter XGB):**

| Hazard mode | Signals |
|-------------|---------|
| **Hurricane / flood** | surge vs `elevation`, wind, flood_zone |
| **Heat wave** | `oil_temp`, `load`, ambient heat (WeatherContext extension or mock), overload duration |
| **Explainability** | Return **top-3 drivers** (e.g. Surge, Age, Load) with every score |

**Temp alert (tutor FR-02):** if predicted/current transformer temp **> 95°C** → raise High/Critical alert path.

### 5.5 API contract — extended payloads (LOCKED — additive)

Keep batch 3 endpoints; **enrich serializers**:

**`GET /api/v1/assets/risk_map/`** each asset includes:

- Existing: `id`, `name`, `coords`, `current_risk`, `impact_count`
- **Add:** `asset_type`, `drivers` (top-3), `conflict_flag`, `confidence`, `replacement_cost` (for $ at risk rollup), `downstream_ids` (for path highlight)

**`GET /api/v1/assets/<id>/action_brief/`** Markdown must include:

- Risk + drivers + dependencies  
- **Trade-off line** (CapEx saved vs outage zone / duration)  
- **ConflictFlag** warning if present  
- Citations to SCADA/weather fields (grounding)

**`POST /api/v1/control/shutdown/`** (and optional mock actions):

- Existing: `asset_id`, `authorization_token`, `reason_text`
- **Add:** `action_level` ∈ {`load_shed`, `reroute`, `deenergize`}, write **AuditLog**

Optional MVP endpoints (mock OK):

- `GET /api/v1/dashboard/header/` → threat_level, weather, impact_tally, **dollars_at_risk**
- `GET /api/v1/assets/<id>/forecast/` → short-horizon health/temp series for chart

### 5.6 UI — four-component Command Center (LOCKED)

Streamlit (or Django+Leaflet) must implement **Map · Logic · Action**, not map-only:

| Component | Requirements |
|-----------|----------------|
| **1. Global Resilience Header** | Threat level · weather/storm category · impact tally (residents and/or **$ assets at risk**) |
| **2. Predictive GIS Map** | Green/yellow/red markers · **glow** on hot assets · **path highlight** to downstream (hospital/water) · filter hospital-linked · optional **what-if surge slider** |
| **3. Intelligence / Forecast panel** | `action_brief` Markdown · optional temp/health **trend chart** · show **raw sensors beside AI** · ConflictFlag banner · top-3 drivers |
| **4. HITL Action Center** | Graduated actions · **trade-off confirm modal** · mandatory reason · audit · override flag for retrain |

Risk colors remain: **&lt;0.3 green · 0.3–0.7 yellow · &gt;0.7 red**.

### 5.7 Graduated response (LOCKED)

| Level | Action | Human role | MVP implementation |
|-------|--------|------------|---------------------|
| **L1 Load shed** | Suggest ~20% load reduction | Suggest-only (no auto-execute in case demo) | Mock button + AuditLog |
| **L2 Reroute** | NetworkX alternate path | Expert review | Mock path suggestion |
| **L3 Cross-check** | XGBoost ∩ Old Guard rules | Gate | `ValidationService` |
| **L4 De-energize** | Full shutdown | **Executive auth only** | Existing shutdown POST |

### 5.8 Dual Referee naming (LOCKED clarification)

| Name | Mechanism | MVP? |
|------|-----------|------|
| **Old Guard / ValidationService** | Hardcoded physics (surge vs elevation, wind, temp&gt;95°C) + **ConflictFlag** | **Required** |
| **Devil’s Advocate LLM** | Second GenAI pass: reasons *not* to shut down (e.g. hospital backup impact) | **Stretch** — PRD + optional prototype |

Do not conflate these in PRD wording.

### 5.9 Data quality & degraded ops (LOCKED for PRD; mock-friendly in prototype)

| Failure | Mitigation |
|---------|------------|
| Sensor blackout | **KNN / neighbor proxy** risk (or mark unknown + low confidence) |
| Drift / impossible values | Isolation Forest → last-known-good |
| Stale / high latency | Drop **`confidence`**; UI warning |
| Weather vs SCADA conflict | **Physical SCADA overrides external weather API** for local state |
| Human ignores repeated alerts | Escalation note in PRD (optional EscalationAgent stretch) |

### 5.10 Water / STP interdependence (LOCKED narrative + data)

- Dependencies **must** include at least one path: `Transformer/Switchgear → Pump/WaterPlant` and `→ Hospital`
- Briefs and trade-offs call out **lifeline** impact explicitly
- Domain framing (PRD): Hazard → Vulnerability → Impact → Preparedness → Recovery; cascading failure includes **loss of power + comms + access**

### 5.11 GenAI / AI-engineering scope (LOCKED)

| In MVP | Out of MVP (PRD roadmap) |
|--------|---------------------------|
| NVIDIA NIM **action_brief** grounded on DRF JSON (`NVIDIA_API_KEY`) | Full **RAG** over SOP manuals |
| Optional tool-calling to Risk/Impact APIs | **MCP** tool mesh |
| Optional Devil’s Advocate LLM stretch | Multi-agent dispatch / SMS agents |
| | Autonomous grid control |

### 5.12 Eval & cold-start (LOCKED for PRD; scripts for prototype)

| Item | Lock |
|------|------|
| Confusion priority | **Minimize false negatives** |
| Metrics | **Recall**, **Lead-time**; precision managed for trust |
| Backtest | Historical storm CSVs (Sandy-style) |
| Shadow mode | Log AI vs human (`ShadowLog`) |
| Cold-start (PRD) | Digital twin / physics labels · transfer learning · expert Delphi rules |
| GenAI quality (PRD) | Grounding vs raw telemetry · optional judge LLM · red-team notes |

### 5.13 Roadmap algorithms (LOCKED — PRD / interview only, not MVP code)

MILP restoration (Sword) · GNN/ST-GAT · CV (drone) · Prophet/LSTM richer forecast · Kalman · Connected components (flood islands) · RL re-routing  

Cursor rule from batch 1 still stands: **no GNN/deep nets in MVP implementation.**

---

## Lock batch 6 — Prototype Day-1 build plan (48-hour pipeline)

**Source:** “AEGIS Prototype: Day 1 Build Plan — Django + Streamlit blueprint”

### 48-hour fast-build steps (LOCKED order)

| Step | Action | Expert shortcut |
|------|--------|-----------------|
| **1. Mock data** | Create `assets.csv` + `telemetry.csv` | ~50 fake substations with lat/lon — don’t wait for real SCADA |
| **2. Model training** | Train tiny XGBoost in a notebook | Save with **joblib** → Django loads `.model` instantly |
| **3. Backend API** | Django REST Framework endpoints | Start with risk endpoint that runs model on CSV/DB data |
| **4. Dashboard** | Streamlit UI | Use **`st_folium`** for fastest map markers |

### Fast-build architecture (LOCKED sketch)

```
data.csv (The Silo)
        ↓
predict.py (XGBoost)  ←→  app.py (Django API)
        ↓
dashboard.py (Streamlit)
```

### Alignment notes

- Day-1 path is the **thin vertical slice**; batches 1–5 (Heartbeat, ValidationService, action_brief, L1–L4, AuditLog, etc.) land as follow-on stories in the same epics.
- Prefer evolving Day-1 `/api/v1/risk/` into locked contracts (`risk_map`, `action_brief`, `control/shutdown`) rather than maintaining a parallel API forever.

---

## Lock batch 7 — GenAI provider: NVIDIA (not OpenAI)

**Source:** User direction + RedlineGuard (`hackathon/redlineguard`) LLM stack  
**Override:** All prior “OpenAI API / LangChain+OpenAI / GPT-4o” locks for the **prototype**.

### Locked env / endpoint (mirror RedlineGuard)

| Setting | Value |
|---------|--------|
| `LLM_PROVIDER` | `nvidia` |
| `NVIDIA_API_KEY` | from [build.nvidia.com](https://build.nvidia.com) — **never commit** |
| `NVIDIA_MODEL` | `meta/llama-3.1-8b-instruct` (default; overridable) |
| Base URL | `https://integrate.api.nvidia.com/v1` |
| Protocol | **OpenAI-compatible** chat completions HTTP |

### Implementation pattern (from RedlineGuard)

- Prefer a thin **OpenAI-compatible HTTP client** (see `redlineguard/apps/core/llm.py` + `llm_providers.py`) over requiring OpenAI SDK keys.
- If using LangChain, configure it with **NVIDIA base URL + `NVIDIA_API_KEY`** (ChatOpenAI-compatible host) — **do not** use `OPENAI_API_KEY`.
- Support `FAKE_LLM=1` canned briefs for offline / CI (same idea as RedlineGuard).
- Optional fallback later: Ollama (`LLM_PROVIDER=ollama`) — not required for AEGIS demo if NVIDIA key is available.

### Epic impact

- **E6 GenAI Action Brief** uses NVIDIA for `action_brief` Markdown.
- Devil’s Advocate stretch (if built) also uses the same NVIDIA client.

### Docs / PRD wording

- Say **“NVIDIA NIM / Llama instruct via integrate.api.nvidia.com”** in architecture sections.
- Samples that mention GPT-4o remain **tone references only**, not stack truth.

---

## Running conflict resolution

| Topic | Previous (digests / north star) | **Now locked** |
|-------|----------------------------------|----------------|
| Backend | FastAPI preferred for prototype | **Django 4.2+ / DRF** |
| DB | Implicit / SQLite-ish lean | **PostgreSQL + PostGIS** |
| Async jobs | Optional / omitted | **Celery + Redis** |
| Graph AI in MVP | NetworkX OK; GNN sometimes in FR wording | **NetworkX only; ignore GNN in MVP code** |
| Predictor | Heuristics first, XGBoost optional | **XGBoost primary** |
| GenAI | OpenAI / LangChain+OpenAI | **NVIDIA NIM** (`NVIDIA_API_KEY`); RedlineGuard-style client; RAG/MCP out of MVP |
| Feature vector | Ad hoc / many fields | **Core `[load, oil_temp, wind, surge]`** + heat/XAI context |
| Inference path | Generic “risk engine” | **`InferenceService` + Heartbeat 1–5** |
| Join key | Implied | **`Asset.scada_link_id`** |
| API shapes | Broader set | **`risk_map` · `action_brief` · `shutdown`** + enriched fields / optional header & forecast |
| UI | Map-only Streamlit | **Four-component Command Center** |
| Risk colors | Informal | **&lt;0.3 green · 0.3–0.7 yellow · &gt;0.7 red** |
| Safety gate | Generic Old Guard | **ValidationService + ConflictFlag**; LLM devil’s advocate = stretch |
| Governance | Shutdown only | **L1–L4 graduated response** (L1 suggest-only) |
| Eval focus | Precision vs recall open | **Minimize FN; Recall + Lead-time; shadow + backtest** |
| Product framing | Implicit | **Shield/Sword · Big Three · cascade · trust ladder** |
| Multi-hazard | Hurricane-skewed | **Hurricane + heat path** |
| Data quality | Underspecified | **Confidence · SCADA&gt;weather · KNN/blackout · AuditLog** |

---

## Changelog

| Date | Batch | What locked |
|------|-------|-------------|
| 2026-08-28 | 1 | Django/DRF, PostGIS, Celery/Redis, XGBoost, NetworkX, Isolation Forest, LangChain+OpenAI, Cursor anti-GNN MVP prompt |
| 2026-08-28 | 2 | ORM models (Asset/Telemetry/WeatherContext/Dependency), InferenceService, AEGIS Heartbeat ingest→persist |
| 2026-08-28 | 3 | API contract (risk_map / action_brief / shutdown), Streamlit UI prompt, Shield interaction loop |
| 2026-08-28 | 4 | Referee hard rule, ValidationService + ConflictFlag, backtest Recall/Lead-time, confusion matrix FN priority |
| 2026-08-28 | 5 | Gap closure: Shield/Sword, Big Three, ORM/API/UI extensions, L1–L4 governance, multi-hazard, data quality, GenAI scope, roadmap algos |
| 2026-08-29 | 6 | Day-1 48h build plan: CSV mocks → joblib XGB → Django risk API → Streamlit st_folium |
| 2026-08-29 | 7 | GenAI: **NVIDIA API** (not OpenAI); RedlineGuard-compatible NIM client pattern |
