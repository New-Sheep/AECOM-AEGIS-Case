# AEGIS Research & Plan — Whiteboard Digest (Part 1)

**Source:** AI tutor / Miro-style research session (screenshots 1–6)  
**Status:** Digested; more screenshots expected  
**Caveat:** Some panels have edge crops/cutoffs — incomplete lines noted as `[cut off]`.

---

## Locked Direction (Working Summary)

| Decision | Choice |
|----------|--------|
| Product name | **AEGIS** — AI-Enabled Grid & Infrastructure Shield |
| Client | Southeastern Grid & Water (SGW) |
| Primary MVP focus | **P1 — Asset Protection (“The Shield”)** |
| Roadmap framing | **P2 — Intelligent Restoration (“The Sword”)** |
| Target user (MVP) | Executive / Incident Commander |
| Core MVP features | Risk heatmap + asset health + **Auto-Brief** GenAI agent |
| Data for prototype | Mock GIS / SCADA / Weather (JSON + scripts) |
| Sprint framing | ~3–5 day MVP build |

**Strategy slogan:** *Shield & Sword* — protect unreplaceable assets first; restore equitably second.

---

## 1. Assignment Frame & Study Plan

### The Plan (4 steps)

1. **The Problem** — Why does AEGIS exist?
2. **The Tools** — Classical ML vs GenAI vs Agents
3. **The Strategy** — ROI & implementation
4. **Final PRD Pitch**

### Deliverables Reminder

| Deliverable | Role |
|-------------|------|
| PRD | Detailed technical blueprint |
| Exec Brief | Business ROI & strategy |
| Prototype | Working demo + code |

### SGW Pain Points (recurring)

- Extreme weather risk (hurricanes, flooding, heatwaves, wildfires)
- Service disruptions
- High insurance premiums
- Regulatory pressure
- Fragmented GIS / SCADA / weather / field ops data

---

## 2. Infrastructure Literacy (GIS + SCADA)

### GIS — “The Map Layer”

Tracks **where** assets are: substations, poles, lines, plants, pumps.

### SCADA — “The Nervous System”

Remote control & monitoring: sensors, switches, alarms.  
Not only power — also **water treatment & pumping** (RPM, pressure, chemical tanks).

### Data Flow Pipeline

```
Sensors → SCADA → GIS → AI
1. Collect    2. Monitor real-time    3. Spatial analysis    4. Analyze & predict
```

### Cascading Failure (“Domino Effect”)

Violent cycle:

```
Power Plant / Grid failure
  → Water treatment / pumps stop
  → Social impact (firefighting, hospitals, hygiene)
  → Grid instability / further stress
  → back to power failure
```

**Where AI breaks the chain:**

1. **Predictive Hardening** — De-energize transformer *before* failure → hours of outage vs months of replacement
2. **Smart Dispatch** — Prioritize power to survival assets (water plants) over non-critical loads

---

## 3. What Is the Data Platform?

**Single source of truth for the grid.**

| Input stream | Examples |
|--------------|----------|
| **IT Systems** | GIS, Customer Data, Asset Management |
| **OT Systems** | SCADA, Sensors, IoT |
| **External Data** | Weather, Satellite, Drones |

→ **Unified Data Platform** → serves GIS, SCADA, AI models

### Platform Jobs

1. **Ingest** — GIS maps + SCADA “heartbeats”
2. **Normalize** — Map a SCADA fault to a specific asset (e.g. Pole #1402)
3. **Expose** — Clean data to AI models

---

## 4. AI Toolbox — Classical vs GenAI vs Agents

| Type | Role | Example |
|------|------|---------|
| **Classical ML** (“Number Cruncher”) | Predict equipment failure (regression / classification) | “Will this transformer blow if wind hits 80 mph?” |
| **GenAI** (“Summarizer”) | Summarize storm reports, draft response plans | Briefing language from scores |
| **Agentic AI** (“Coordinator”) | Dispatch, cross-system coordination | “Write a briefing for the Governor about current outages” |

### Advanced Capabilities of Interest (beyond LLMs)

| Capability | Use |
|------------|-----|
| **Forecasting** | Time-series load prediction & storm surge modeling |
| **Anomaly Detection** | SCADA “ghost” signals before fire / failure |
| **Optimization** | Route repair crews to maximize lives saved per hour |
| **Computer Vision** | Damage assessment via satellite / drone |

**Optimization note:** LP / genetic algorithms — e.g. TSP-like problem for ~500 crews in a flooded city.

---

## 5. Mission-Critical Priorities (SGW)

| Priority | Theme | Pain | Business risk | Primary AI |
|----------|-------|------|---------------|------------|
| **P1** | Life & Infrastructure / Asset Destruction | Zero-spare transformers at risk | CapEx catastrophe; insurance | Predictive ML (“Shield”) |
| **P2** | Response Equity / Regulatory | Slow/uneven restoration of lifelines | Legal / brand / PUC | Linear programming / MILP (“Sword”) |
| **P3** | Data Blindness | Fragmented GIS/SCADA | Efficiency drain; overtime | Anomaly detection + unification |

### Money vs Mission

Venn: **Grid Infrastructure Protection** ∩ **Public Health / Equity** = **Systemic Resilience**

Gauge logic:

- Can’t restore a hospital if the hardware is ash → **P1 first**
- Restoring a golf course before a water pump → **brand death** → **P2 matters**

---

## 6. Option 1 — Proactive Asset Shielding (“The Shield”)

**Focus:** Predictive ML to save high-value **zero-spare** hardware.

### Tech Stack (Shield)

1. Time-series forecasting (surge loads, heat)
2. Anomaly detection (pumps / transformers)
3. Binary classification (de-energize decision)

### Critical Shield Data Points

1. **Weather** — Sustained wind vs design tolerance of poles
2. **SCADA** — Transformer oil temperature; current harmonics
3. **GIS** — Service history / last service; flood-zone status

### Shield Data Flow

```
Weather API + SCADA telemetry + GIS assets
        → Risk Scoring Engine / AI-ML models
        → Asset heatmap / predicted failures / criticality scores
        → De-energization vector map (advisory)
```

### Shield Objectives

1. **Zero Explosions** — Catastrophic loss → temporary interruption
2. **Predictive Maintenance** — Turn off now so it can turn on tomorrow
3. **CapEx Preservation** — Save millions in replacement cost

### With vs Without AEGIS (illustrative)

| | Traditional | With AEGIS Shield |
|--|-------------|-------------------|
| Outcome | Transformer fire / explosion | Status: De-energized (planned) |
| Cost | ~$250k+ repair; 18–24 month lead time | ~$0 repair; ~2 min remote restore |

### De-Risking False Alarms (trust ladder)

Increasing trust → increasing autonomy:

1. **Backtesting** — AI on ~10 years historical storm data
2. **Shadow Mode** — Real-time recommendations; no action
3. **Pilot Phase** — Full advisory/control on ~3 high-value non-spare assets

### Where’s the Training Data?

1. Historical SCADA (ground-truth failures)
2. Maintenance logs (unstructured text)
3. Synthetic data / digital twin (sparse real storms)

---

## 7. Option 2 — Intelligent Restoration (“The Sword”)

**Focus:** Optimization after impact to speed equitable restoration (~40% time reduction claimed in board framing).

### Optimizer Equation

- **Objective:** Minimize total restoration time **AND** public safety risk
- **Constraints:** Limited crews (e.g. 3–5 HV teams), blocked roads, topological dependencies

### Dispatch Flow

```
List of ~500 faults
  → Priority Scorer (Hospitals → Water → Seniors / SVI)
  → Resource Allocator (Trucks / Boats / Crew Shifts)
  → Constraint Engine (Road flooding / Crew fatigue)
  → Daily Dispatch Schedule
```

### Sword Tech Stack

1. **MILP** — Who goes where?
2. **Computer Vision** — Road passability from drone footage
3. **Reinforcement Learning** — Dynamic re-routing if roads flood mid-shift; policies from historical storms

### MVP Stance on Sword

Frame in PRD / roadmap; **do not build full optimizer first**. Prototype centers on **Shield** risk dashboard + briefing agent.

---

## 8. Forecasting & Anomaly Concepts (Teaching Layer)

### Time-Series Forecasting

Predict future values from past patterns.  
Use: peak load in heatwaves; water demand during fires.

### Three Pillars of Forecasting for SGW

1. **Trend** — e.g. ~2% annual load growth
2. **Seasonality** — AC in August vs heaters in January
3. **Exogenous Variables** — Cat-4 hurricane path, etc.

**Edge:** Multivariate series (loading + humidity + temp + wind) → asset temperature prediction.

### Anomaly Detection

Unsupervised “odd one out” — e.g. pump vibration pattern signaling pre-storm failure.

### Asset Health Scoring

- Survival analysis — time-to-next-failure
- Random Forests / XGBoost — brand, region, last service → risk
- Graph: health % declining toward failure threshold; “predicted failure in 30 days”

### Computer Vision (“The Eyes”)

- Thermal anomalies, mechanical damage, vegetation encroachment (drone / tower)
- Use cases: damage assessment; vegetation management (LiDAR + images); PPE compliance

---

## 9. Graph / GNN Angle (Interdependency)

**Pain:** Lack of integration between power, water, and weather → cascading failures.

**GNN framing:**

| Element | Meaning |
|---------|---------|
| **Nodes** | Transformers, pumps, hospitals, substations |
| **Edges** | Power lines, water pipes, dependencies |
| **Logic** | Stress/failure propagation (flooded substation → downstream outages) |

Complements classical risk scoring with **domino-effect** prediction.

---

## 10. AEGIS Command Center Concept

**“Unified Glass Pane”** — three views:

1. **Map (GIS)** — Where is the trouble?
2. **Logic (AI)** — What dominoes fall next?
3. **Action (Ops)** — Where do crews go?

Mock signals: hurricane path, alerts (e.g. Substation 402), “$2.4M Assets Protected.”

---

## 11. Architecture Layers (Prototype-Ready)

### Ingestion (MVP = Mock)

| Stream | Production | MVP mock |
|--------|------------|----------|
| SCADA | Real-time voltage / pressure | Scripted heartbeats |
| GIS | Asset location + connectivity | JSON: asset IDs + coordinates |
| Weather | NOAA / ECMWF / SLOSH | Static JSON hurricane path |

### AI Engine

- Classical ML — predictive risk / Markov-style models
- Graph analytics / GNN — cascading effects (roadmap depth)
- GenAI summarizer — “the Bridge”

### UI / Management

Executive dashboard (+ field apps later)

### GenAI / Agent Features

| Feature | Role | MVP priority |
|---------|------|--------------|
| **RAG for SOPs** | Query emergency manuals | Nice-to-have / later |
| **Agentic Dispatch** | Draft SMS to crews + parts | Roadmap |
| **Auto-Brief Agent** | Numbers → plain-English exec summary | **MVP core** |

Example Auto-Brief:

> “Transformer 402 is at 94% risk. Recommend safe shutdown in 15 mins to save $2M in assets.”

**Glue:** Normalize SCADA IDs ↔ GIS lat/long; GenAI calls **Risk API** for facts before writing.

---

## 12. Lean MVP Scope (Locked for Build)

### Problem / Users / AI / Metrics

| Dimension | MVP |
|-----------|-----|
| Problem | Data fragmentation → asset loss + response inequity |
| Users | Incident Commanders & Asset Managers |
| AI | Predictive risk scoring (classical ML) + situational summaries (GenAI) |
| Success | % reduction in zero-spare asset loss; speed of triage |

### Executive Requirements

1. Unified situational awareness — territory “Health Score” (8M residents)
2. Financial risk exposure — $ assets at risk in the storm
3. Regulatory compliance trail — logged decisions (e.g. shutdowns) for equity

### Locked Build Features

| Feature | Mechanism |
|---------|-----------|
| **Real-Time Risk Heatmap** | ML / rules: predicted storm surge (SLOSH) vs control-room elevation (GIS) |
| **Asset Health Monitor** | Time-series: transformer temp from load + ambient heat |
| **Executive Situation Agent** | GenAI briefing box: risk scores → one-sentence business recommendation |

### Architecture Sketch

```
SCADA Telemetry + Weather API + Asset GIS
              ↓
         AEGIS-1 Engine
              ↓
   Executive Health Score Dashboard
   (+ briefing box / gauges)
```

### Suggested Success Metrics

- Incident briefs in **&lt; 2 minutes**
- CapEx saved per storm
- Precision vs false-alarm rate
- Decision latency: hours → minutes
- Asset attrition (esp. long-lead assets)
- Brand / unplanned-outage impact

---

## 13. Domain Detail — Hurricane Substation Factors

(Ties to domain expert brainstorm in `02-…`)

| Factor | Check |
|--------|-------|
| Flood level | Transformers, batteries, switchgear above design flood level |
| Wind loading | Gantries, poles, roof sheets |
| Containment | Transformer oil containment & drainage |
| Backup power | DC / emergency batteries above flood |

### Plain-English Definitions (for execs)

- **DC System / Batteries** — Substation “brain”; keeps communication alive if AC power dies
- **Wind Loading** — Wind force a steel structure can take before failure
- **Oil Containment** — Pits catching cooling oil to avoid environmental contamination

---

## 14. Shield & Sword MVP Mapping to Deliverables

| Artifact | Focus |
|----------|-------|
| **PRD** | Asset loss = existential threat; inequity = regulatory threat; full stack described; MVP = Shield features |
| **Proposed AI** | Forecasting/ML for Shield; Optimization for Sword (roadmap) |
| **Prototype** | Risk dashboard: weather + SCADA → transformer failure prediction + Auto-Brief |
| **Exec Brief** | CapEx preservation, insurance, equity, phased trust ladder |

---

## Open / Incomplete from Crops

- Some optimization constraint bullets partially obscured by UI chrome (`[cut off]`)
- Exact numeric ROI claims in boards are illustrative — validate before putting in final exec brief
- Sprint length stated as both “3-day” and “5-day” across panels — treat as **short sprint**, pin exact days later

---

## Next

Await remaining whiteboard screenshots (prototype UX, PRD outline, video plan, stack choices, etc.) → Part 2 digest.
