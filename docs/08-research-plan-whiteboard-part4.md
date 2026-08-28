# AEGIS Research & Plan — Whiteboard Digest (Part 4 — Final)

**Source:** AI tutor / Miro research session (screenshots 19–22, last batch)  
**Status:** Complete digest of shared boards  
**Prior:** `05-…part1.md`, `06-…part2.md`, `07-…part3.md`

---

## Build Lock (Authoritative for Prototype)

Prefer **lean Power-Trio + FastAPI/Streamlit** for the case deliverable. Treat **Django/DRF/Celery** as enterprise PRD option unless you specifically want Django.

| Layer | Lock for MVP |
|-------|----------------|
| Asset health | Heuristics first; optional **XGBoost** on CSV |
| Anomaly | Optional **Isolation Forest** (“double defense” before predict) |
| Grid impact | **NetworkX** / hardcoded lookup (not GNN) |
| Intelligence | **LLM + tool calling** to Risk/Impact APIs |
| Frontend | **Streamlit** (+ Leaflet if map needed) *or* Dash (board variant) |
| Backend | **FastAPI** (simplest) *or* Django/DRF (auth, admin, audit ORM) |
| Data | CSV/JSON mocks + Weather API mock |
| Governance | Graduated response + rule “Old Guard” + HITL audit; optional **Referee** LLM |

---

## 1. Why This Stack Wins

### Operational benefits (vision)

- **Zero operational blindness** — cascades ~2h ahead (enterprise claim)
- **Dynamic reflex** — sudden + slow-onset events
- **Explainable scores** — attention / top drivers / citations

### Development philosophy (MVP)

- Fastest to build, easiest to explain, works on a **CSV**
- Hardcoded lookups (`IF Sub-A fails → Hospital B at risk`) instead of GNN → **zero GNN dev time**

---

## 2. Sweet-Spot Stack (Middle Tech)

| Capability | Choice | Notes |
|------------|--------|-------|
| **Asset health** | XGBoost + Isolation Forest | IF flags weird sensors **before** XGB (“Double Defense”) |
| **Grid impact** | Graph search / **NetworkX** | Trace flow Sub → Hospital (not full GNN) |
| **Intelligence** | GenAI + **tool calling** | LLM calls Python functions for live/mock state |

### Non-DL suite (keep on roadmap / talk-track)

| Tool | Job | Why |
|------|-----|-----|
| **MILP** | Crew routing (e.g. 50 trucks → ~200 sites) | Guaranteed optimality; \(\min \sum c_{ij}x_{ij}\) s.t. capacity |
| **Isolation Forest** | Sensor integrity / drift | Fast, unsupervised, no labels |
| **Kalman filters** | SCADA noise / state estimation | Ultra-low latency, low memory |

### NetworkX algorithms

| Algorithm | Use |
|-----------|-----|
| **Dijkstra / shortest path** | Crew routes depot → fault |
| **Connected components** | Flood “islands” — isolated grid fragments |
| **PageRank / betweenness centrality** | “If this node fails, how many go dark?” |

### Development pyramid

```
MVP     → LLM + SCADA/CSV analytics
Phase 2 → Anomaly detection + cascading states
Phase 3 → 3D digital twins + dynamic DFM
```

Alternate roadmap wording on boards: Phase 1 Dashboard → Phase 2 CV → Phase 3 Global grid.

---

## 3. Definitive MVP Architecture (Variants)

### Lean variant (recommended)

```
CSV Data + Weather API mock
        ↓
Analytics Core (Python):
  Isolation Forest | NetworkX | LLM (tool calling)
        ↓
API Gateway (FastAPI)
        ↓
UI (Streamlit / Dash)
```

### Pipeline shorthand

`SQL/CSV → Pandas → NetworkX → FastAPI → UI`

### 5-tier blueprint (PRD)

1. **Data sources** — GIS, SCADA, Weather  
2. **Ingestion & cleaning** — upload / API → centralized data pond  
3. **Brain** — NetworkX + XGBoost + LLM  
4. **Deployment** — Exec dashboard + CRM/alerts  
5. *(Implied ops)* — audit / control plane  

### Django advantage (enterprise option)

| Reason | Benefit |
|--------|---------|
| ORM | Map GIS nodes ↔ SCADA IDs |
| Security | Ready-made protections |
| Admin panel | Staff update asset status in storm |
| Audit logs | Regulatory trail for shutdowns |

Stack if chosen: Django + DRF + Celery + Redis; frontend Streamlit/React/Django templates + **Leaflet.js**.

---

## 4. API Contract (Resilience Engine)

Boards specify DRF paths; keep same shapes on FastAPI.

| Endpoint | Method | Behavior |
|----------|--------|----------|
| `/api/v1/assets/health/` | GET | All assets + SCADA telemetry (temp, load, voltage) |
| `/api/v1/assets/predictive/` | POST | Storm params (category, surge) → `{asset_id → risk_score, is_anomaly}` |
| `/api/v1/network/impact/` | GET | `node_id`, `radius` → downstream deps + criticality |
| `/api/v1/ai/briefing/` | POST | Top risks → Markdown executive summary |
| `/api/v1/control/shutdown/` | POST | Secure mock control + audit (HITL only) |

### Sample impact payload (from board)

```json
{
  "impact_score": 82,
  "restoration_priority": "High",
  "affected_assets": ["substation_…", "hospital_…"]
}
```

---

## 5. UI/UX Blueprint — Four Components

### Component 1: Global Resilience Header

At-a-glance: Threat Level · Weather (e.g. Hurricane Watch) · Impact tally (e.g. 750k potential outages)

| Logic | Detail |
|-------|--------|
| Dynamic risk aggregator | Sum/rollup scores → global Threat Level |
| Weather overlay | Poll weather API every **2–5 min** (boards vary) |
| Impact tally | NetworkX → `total_affected_residents` / `network_restores` |

### Component 2: Predictive GIS Map

Infrastructure domino view (coastal assets, storm shade)

| Interaction | Behavior |
|-------------|----------|
| **Glow** | High-risk assets glow (“hot”) |
| **Path tracing** | Click sub → highlight downstream outage path |
| **What-if slider** | Heuristic overlay (e.g. 10 ft surge) |
| Hover | Health scorelines |
| Filter | e.g. hospital-linked assets at risk |

### Component 3: AI Intelligence Panel

| Logic | Detail |
|-------|--------|
| Contextual prompting | Backend sends top ~5 risks + dependency list to LLM |
| The “Why” | Plain English (surge + age, etc.) |
| Grounding | Cite SCADA / Weather fields — anti-hallucination |
| One-click brief | Generate executive email / Markdown |

### Component 4: HITL Action / Decision Center

Confirm / Deny-Override cards (e.g. load shed at Substation Alpha-12)

| Logic | Detail |
|-------|--------|
| Control API | `POST …/control/shutdown/` (mocked for prototype) |
| Audit log | User ID, timestamp, reason, authorized-by |
| Retraining loop | Overrides flagged for future model training |

---

## 6. Defensive Depth & Governance

### Graduated response (4 levels)

| Level | AI action | Human role |
|-------|-----------|------------|
| **1. Load shedding** | Reduce flow ~20% to cool asset | AI-suggested / auto-implementable (policy choice) |
| **2. Rerouting** | NetworkX alternate path | Expert review required |
| **3. Secondary AI check** | “Old Guard” rule-engine must agree with XGBoost | Cross-validation gate |
| **4. Full de-energize** | Complete shutdown | **Executive auth ONLY** |

### Triple filter before shutdown

```
XGBoost signal → Rule-based Old Guard → Referee LLM → HITL execute
```

### Referee (“Devil’s Advocate”) agent

LLM finds reasons **not** to shut down, e.g.:

> “Warning: Shutting down now will offline the hospital’s backup generators in 30 minutes.”

### Blueprint sections for Cursor/Claude Code

1. **Architecture** — Django/DRF *or* FastAPI; unified GIS↔SCADA asset model; Leaflet map  
2. **Brain** — XGBoost · Isolation Forest · NetworkX · GenAI briefings  
3. **Governance** — Graduated response · Referee · Audit trail  
4. **Data strategy** — Transfer learning + digital twin labels; SCADA **rate-of-change** features as temporal proxy  

---

## 7. Road Ahead / Money Framing (This Batch)

| Claim | Number |
|-------|--------|
| Problem / losses | Fragmented data → **~$50M** operational losses *(board)* |
| Savings potential | **~$125M** direct + indirect *(board)* |
| Roadmap | P1 Dashboard MVP → P2 CV → P3 Global grid |

> Prefer Part 3’s **$30M / $25M+** math with explicit assumptions over the $50M/$125M figures unless you re-derive them.

---

## Conflicts — Final Resolution Table

| Topic | Options seen | **Recommended lock** |
|-------|--------------|----------------------|
| Backend | FastAPI vs Django/DRF | **FastAPI** for prototype; Django in PRD “enterprise” |
| Frontend | Streamlit vs Dash vs React+Leaflet | **Streamlit + simple map** (or Leaflet in Streamlit) |
| Unmitigated $ | $30M / $50M / $100M+ | **$30M** with 500-sub / 10-xfmr / $3M unit math |
| Weather poll | 2 vs 5 min | **Mock timer** — pick 5 min in NFR |
| Auto load-shed L1 | Auto vs suggest-only | **Suggest-only** for case (safer HITL story) |
| GNN / ST-GAT | Deep theory boards | **PRD Phase 2–3 / interview**; not MVP code |

---

## End-to-End Deliverable Map

| Assignment deliverable | Source of truth in docs |
|------------------------|-------------------------|
| Case brief | `01-technical-assessment-brief.md` |
| Domain depth | `02-domain-expert-brainstorm-electrical-stp.md` |
| Sample exec / PRD | `03-…`, `04-…` (reference tone only) |
| Research Parts 1–4 | `05`–`08` (this file) |
| **Your PRD** | Write from Big Three + Power-Trio + FRs + governance |
| **Your Exec Brief** | $30M math + Shield/Sword + phased roadmap + HITL |
| **Prototype** | 4 UI components + APIs above + Auto-Brief + audit mock |
| **Video** | Header → map glow/path → briefing → confirm/deny + trade-off |

---

## Prototype Acceptance Checklist (Final)

- [ ] Mock ~5 substations (Big Three signals where possible)  
- [ ] Health feed API + dashboard scores  
- [ ] Predictive risk (heuristic and/or XGB) + optional anomaly flag  
- [ ] Network impact / path highlight (NetworkX or lookup)  
- [ ] What-if surge slider (nice-to-have)  
- [ ] GenAI briefing grounded on API payload  
- [ ] Confirm / override with reason + audit log  
- [ ] Referee warning optional stretch  
- [ ] README: setup, architecture, assumptions, limits  
- [ ] 5–10 min demo video  

---

## Doc Index (`aecom-case/docs/`)

| File | Content |
|------|---------|
| `01-technical-assessment-brief.md` | Official case assignment |
| `02-domain-expert-brainstorm-electrical-stp.md` | Electrical/STP HoD brainstorm |
| `03-sample-executive-briefing-aegis.md` | Sample Deliverable 2 |
| `04-sample-prd-aegis.md` | Sample Deliverable 1 |
| `05-research-plan-whiteboard-part1.md` | Shield/Sword, priorities, Auto-Brief |
| `06-research-plan-whiteboard-part2.md` | Big Three, FRs, eval, cold-start |
| `07-research-plan-whiteboard-part3.md` | $30M math, GNN theory, Power-Trio |
| `08-research-plan-whiteboard-part4.md` | **This file** — API, UI, governance, build lock |
