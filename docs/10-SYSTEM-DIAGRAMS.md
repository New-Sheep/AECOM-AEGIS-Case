# AEGIS — System Understanding Diagrams

**Based on:** `09-FINAL-LOCKED-DECISIONS.md` (batches **1–5**)  
**Purpose:** Visual check of locked understanding — architecture, data, inference, UX, governance, hazards.

---

## 1. Product strategy — Shield & Sword

```mermaid
flowchart TB
  subgraph Goal["Systemic Resilience"]
    G[CapEx survival ∩ Public lifelines]
  end

  P1["P1 SHIELD — Asset protection<br/>XGBoost + Referee + HITL de-energize"]
  P2["P2 SWORD — Equitable restoration<br/>MILP / dispatch — ROADMAP"]
  P3["P3 Data blindness<br/>Unify GIS/SCADA/weather + confidence"]

  P1 --> G
  P2 --> G
  P3 --> P1
  P3 --> P2

  Trust["Trust ladder: Backtest → Shadow → Pilot"] --> P1
```

---

## 2. Cascading failure (why dependencies matter)

```mermaid
flowchart LR
  Grid[Grid / Transformer failure] --> Water[Water / STP / Pumps stop]
  Water --> Social[Hospitals · firefighting · hygiene]
  Social --> Stress[More grid / social stress]
  Stress --> Grid

  Shield["SHIELD: predict + protect asset"] -.->|breaks chain early| Grid
  Sword["SWORD: restore lifelines fairly"] -.->|recovers| Water
```

---

## 3. System context (who talks to what)

```mermaid
flowchart TB
  subgraph Actors
    IC[Incident Commander / Exec]
  end

  subgraph Frontend["Command Center UI"]
    ST[Streamlit or Django+Leaflet]
    HDR[Header]
    MAP[Map]
    LOGIC[Intelligence + Forecast]
    ACT[HITL Action Center]
  end

  subgraph Backend["Django 4.2 + DRF"]
    API[DRF API]
    INF[InferenceService]
    VAL[ValidationService / Old Guard]
    LC[NVIDIA NIM brief]
    DA[Devil's Advocate LLM — stretch]
    NX[NetworkX]
  end

  subgraph Data["PostgreSQL + PostGIS"]
    ORM[(Asset Telemetry Weather Dependency AuditLog ShadowLog)]
  end

  subgraph Async["Celery + Redis"]
    HB[Heartbeat pipeline]
  end

  subgraph Brain
    XGB[XGBoost]
    IF[Isolation Forest]
  end

  IC --> ST
  ST --- HDR
  ST --- MAP
  ST --- LOGIC
  ST --- ACT
  ST --> API
  API --> ORM
  API --> LC
  API --> DA
  API --> NX
  API --> VAL
  HB --> INF
  INF --> XGB
  INF --> IF
  INF --> ORM
  VAL --> ORM
```

---

## 4. Data model (extended ORM)

```mermaid
erDiagram
  Asset ||--o{ Telemetry : has
  Asset ||--o{ Dependency : parent_of
  Asset ||--o{ Dependency : child_of
  Asset ||--o{ AuditLog : decisions
  Asset ||--o{ ShadowLog : eval
  WeatherContext }o--|| Asset : "joined at inference"

  Asset {
    string type
    string scada_link_id
    float elevation
    float risk_score
    float confidence
    float replacement_cost
    string flood_zone
    int age
  }

  Telemetry {
    float load
    float oil_temp
    float voltage
    float battery_voltage
    string switch_status
    bool is_anomaly
    float load_rate_of_change
  }

  WeatherContext {
    float wind_speed
    float flood_surge_level
    string storm_category
    float ambient_temp
  }

  Dependency {
    uuid parent_asset
    uuid child_asset
  }

  AuditLog {
    string action
    string reason_text
    bool human_override
    string authorization_level
  }
```

**Big Three + lifelines:** `Transformer`, `Battery`, `Switchgear`, `Pump`, `Hospital`, `WaterPlant`

---

## 5. AEGIS Heartbeat (continuous pipeline)

```mermaid
flowchart LR
  A[1 INGEST<br/>CSV / API] --> B[2 NORMALIZE<br/>SCADA → Asset<br/>scada_link_id]
  B --> C[3 FEATURIZE<br/>telemetry + weather]
  C --> D[4 INFERENCE<br/>Isolation Forest<br/>+ XGBoost]
  D --> E[5 VALIDATE<br/>Old Guard rules]
  E --> F[6 PERSIST<br/>risk_score · drivers<br/>conflict_flag · confidence]
  F -.->|pulse| A
```

**Core XGB vector:** `[load, oil_temp, wind_speed, surge_level]`

---

## 6. Inference + Old Guard + optional Devil’s Advocate

```mermaid
flowchart TD
  Q[Latest Telemetry + Weather + Asset.elevation] --> F[Feature vector]
  F --> IF[Isolation Forest → is_anomaly]
  F --> X[XGBoost → risk_score + drivers]
  F --> R{Old Guard<br/>surge > elevation AND wind > 100?<br/>OR oil_temp > 95°C?}
  X --> V[ValidationService]
  R --> V
  IF --> V
  V --> C{Rule Fail AND XGB Safe?}
  C -->|Yes| CF[conflict_flag = true]
  C -->|No| OK[Return score + drivers + confidence]
  CF --> BRIEF
  OK --> BRIEF[action_brief via NVIDIA NIM]
  BRIEF --> DA{Devil's Advocate LLM?<br/>stretch}
  DA -->|Yes| WARN[Reasons NOT to shut down]
  DA -->|No| UI[UI]
  WARN --> UI
```

---

## 7. Graduated response L1–L4

```mermaid
flowchart LR
  S[Risk / Conflict] --> L1[L1 Load shed ~20%<br/>SUGGEST ONLY]
  L1 --> L2[L2 NetworkX reroute<br/>Expert review]
  L2 --> L3[L3 XGB ∩ Old Guard<br/>Cross-check gate]
  L3 --> L4[L4 Full de-energize<br/>Executive auth ONLY]
  L4 --> AUD[AuditLog]
```

---

## 8. Multi-hazard modes

```mermaid
flowchart TB
  H[Hazard mode] --> HU[Hurricane / Flood<br/>surge · wind · elevation · flood_zone]
  H --> HE[Heat wave<br/>oil_temp · load · ambient · overload]
  HU --> SCORE[Risk score + drivers]
  HE --> SCORE
  SCORE --> LIFE[Dependency impact<br/>Hospital / WaterPlant / Pump]
```

---

## 9. Shield user flow (full Command Center)

```mermaid
sequenceDiagram
  actor IC as Incident Commander
  participant UI as Command Center
  participant API as DRF
  participant NX as NetworkX
  participant VAL as ValidationService
  participant LC as NVIDIA NIM
  participant DB as Postgres

  IC->>UI: Open dashboard
  UI->>API: GET header + risk_map
  API->>DB: Assets + risk + confidence
  API->>NX: impact_count + downstream_ids
  API->>VAL: conflict_flag / drivers
  API-->>UI: markers + $ at risk + flags
  UI->>UI: Header + map colors + glow

  IC->>UI: Click asset / filter hospital-linked
  UI->>UI: Path highlight downstream
  UI->>API: GET action_brief (+ optional forecast)
  API->>LC: Grounded Markdown + trade-off
  API-->>UI: Brief + raw sensors + ConflictFlag
  IC->>UI: Choose L1–L4 action
  UI->>UI: Trade-off confirm modal
  IC->>UI: Reason + auth
  UI->>API: POST control (action_level, reason)
  API->>DB: AuditLog
  API-->>UI: Ack → refresh loop
```

---

## 10. UI layout — four components

```mermaid
flowchart TB
  subgraph CC["AEGIS Command Center"]
    HDR["1. Header<br/>Threat · Weather · Impact · $ at risk"]
    MAP["2. Map<br/>G/Y/R · glow · path · filter · what-if surge"]
    PANEL["3. Logic panel<br/>Brief · drivers · forecast chart<br/>raw sensors · ConflictFlag"]
    ACT["4. Action Center<br/>L1–L4 · trade-off modal · reason · audit"]
  end

  HDR --> MAP
  MAP -->|click| PANEL
  PANEL --> ACT
```

---

## 11. Data quality / degraded storm ops

```mermaid
flowchart TD
  SIG[Incoming telemetry] --> Q{Quality?}
  Q -->|Blackout| KNN[KNN / neighbor proxy<br/>or unknown + low confidence]
  Q -->|Impossible spike| IF2[Isolation Forest<br/>→ last known good]
  Q -->|Stale| CONF[Drop confidence<br/>UI warning]
  Q -->|OK| NOM[Normal Heartbeat]
  WX[Weather API] --> CONF2{Disagree with SCADA?}
  SCADA[Local SCADA] --> CONF2
  CONF2 -->|Yes| WIN[SCADA wins for local state]
  CONF2 -->|No| MERGE[Merge into features]
```

---

## 12. Eval & trust ladder

```mermaid
flowchart LR
  BT[Backtest storm CSVs<br/>Recall + Lead-time] --> SH[Shadow mode<br/>ShadowLog AI vs human]
  SH --> PI[Pilot on Big Three<br/>HITL only]
  PI --> PRD[PRD metrics / FN priority]
```

---

## 13. MVP vs roadmap algorithms

```mermaid
flowchart TB
  subgraph MVP["Build now"]
    XGB2[XGBoost]
    NX2[NetworkX Dijkstra/centrality]
    IF3[Isolation Forest]
    OG[Old Guard rules]
    LC2[NVIDIA NIM brief]
  end

  subgraph ROAD["PRD / interview only"]
    GNN[GNN / ST-GAT]
    MILP[MILP Sword]
    CV[Computer vision]
    RAG[RAG on SOPs]
    MCP[MCP / multi-agent]
    LSTM[Prophet / LSTM]
  end
```

---

## Check me (remaining soft choices)

1. L1 stays **suggest-only** in the demo (locked) — confirm if you ever want auto-shed later.  
2. Devil’s Advocate LLM = **stretch** — build only if time.  
3. What-if slider + forecast chart = **in locked UI**; drop only if timeboxed.
