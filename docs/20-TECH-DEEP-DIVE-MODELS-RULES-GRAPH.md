# AEGIS Tech Deep Dive - Models, Rules, and Graph

**Audience:** Candidate prep / interview / assessors who want “why this stack”  
**Scope:** Prototype tech only (Shield). Sword optimization is roadmap, not in this code.  
**Related code:** `backend/api/services/`, `scripts/train_xgb.py`, `run_heartbeat`  
**Related docs:** PRD §5–§6, handover, `15-DATA-PROVENANCE.md`

**Number honesty:** Demo labels and some ConflictFlag paths are scaffolding. Architecture is the point.

---

## Big picture: four different questions

AEGIS does **not** use one model for everything. Each layer answers a different question.

| Layer | Question | Output | Code |
|-------|----------|--------|------|
| Isolation Forest | Are these readings weird vs normal? | `is_anomaly`, lower confidence | `services/anomaly.py` |
| XGBoost | How high is site failure / storm risk? | `risk_score` in [0, 1], drivers | `services/predict.py`, `inference.py` |
| Old Guard (rules) | Does hard physics disagree with a “safe” score? | `conflict_flag`, confidence | `services/validation.py` |
| NetworkX | Who else is hurt if this site goes? | Downstream / lifeline list | `services/graph.py` |

```text
sensors / weather
        │
        ▼
┌───────────────────┐
│ Isolation Forest  │  sensor trust
└─────────┬─────────┘
          │ is_anomaly → confidence ↓
          ▼
┌───────────────────┐
│ XGBoost           │  hazard / failure risk
└─────────┬─────────┘
          │ risk_score
          ▼
┌───────────────────┐
│ Old Guard rules   │  physics vs calm model (false-negative catch)
└─────────┬─────────┘
          │ conflict_flag
          ▼
┌───────────────────┐
│ NetworkX graph    │  cascade / who fails next
└─────────┬─────────┘
          │ downstream_ids
          ▼
   Brief + map + human approval (HITL)
```

Heartbeat order (by design): **anomaly → XGBoost → validation → persist** (`run_heartbeat`).

Agent path (simplified): validate / anomaly → predict → **impact** → briefing → HITL.

---

## 1. XGBoost (risk scoring)

### What it is

A **gradient-boosted tree regressor** (`XGBRegressor`) that maps four tabular features to a continuous risk in [0, 1].

**Features** (`FEATURE_COLS`):

```text
load, oil_temp, wind_speed, surge_level
```

**Artifact:** `artifacts/xgb_risk.joblib`  
**Train:** `scripts/train_xgb.py`  
**Score:** `api/services/predict.py`, `inference.py`

### Why this choice

| Criterion | Why XGBoost fits |
|-----------|------------------|
| Data shape | Tabular sensors + weather per site |
| Speed | Scores ~50 sites in milliseconds |
| Explainability | Tree `feature_importances_` → operator drivers |
| Sample size | Works on small CSV demos |
| Ops familiarity | Common for risk / tabular ML |

**Why not (yet):** deep sequence models (need long history), GNN (need breaker-true topology), LLM as risk engine (hallucination; GenAI is for briefs only).

### How it works (math, interview-level)

Build many shallow trees. Each new tree fits residual error of the current model:

\[
F_m(x) = F_{m-1}(x) + \eta \, f_m(x)
\]

- \(\eta\) = learning rate (`0.15`)  
- \(M\) = number of trees (`n_estimators=40`)  
- Tree depth capped (`max_depth=3`)  
- Loss: squared error (`reg:squarederror`)  
- Final score clipped to [0, 1]

### Critical honesty: labels

Training labels are **synthetic / physics-ish**, not years of SGW failure history:

```text
risk ≈ 0.35*flood + 0.25*wind + 0.25*thermal + 0.15*load
  (each term a clipped normalized excess over a threshold)
```

See `synthetic_risk_label` in `predict.py`.

**Interview line:** “XGBoost is the right model class; prototype labels are transparent so the demo is learnable. A pilot would retrain on real near-miss and failure outcomes.”

### Drivers (“Why this score”)

`top_drivers` ranks `|feature_importance × feature_value|`. This is **global importance × current value**, not full SHAP. Good enough for PoC; SHAP is a later upgrade.

### Key snippets

Training (`train_xgb.py`):

```python
model = XGBRegressor(
    n_estimators=40,
    max_depth=3,
    learning_rate=0.15,
    objective="reg:squarederror",
    random_state=42,
)
model.fit(X_clean[FEATURE_COLS], y)
joblib.dump(model, MODEL_PATH)
```

Scoring (`predict.py`): preprocess feature dict → `model.predict` → clip to [0, 1].

---

## 2. Isolation Forest (anomaly detection)

### What it is

**Unsupervised** outlier detection on the **same four features**, after **StandardScaler**. Flags “this vector looks weird vs the usual cloud,” not “this storm will destroy the transformer.”

**Artifact:** `artifacts/isolation_forest.joblib` (+ `iforest_scaler.joblib`)  
**Code:** `api/services/anomaly.py`  
**Params:** `n_estimators=100`, `contamination=0.08` (~8% expected outliers)

### Why this choice

| Reason | Fit |
|--------|-----|
| Unsupervised | Few labeled “bad sensor” examples |
| Built for outliers | Isolates rare points with few random splits |
| Separates trust problems | Weather risk ≠ sensor integrity |
| Light | Four features; sklearn-standard |

**Why not first:** supervised fault classifier (needs labels), autoencoder (overkill), per-channel z-score only (misses joint weirdness), XGB alone (high risk can be a *real* storm).

### How it works (math, interview-level)

Random trees split feature space. Points that become isolated after **few** splits are anomalous; dense “normal” points need many splits.

Sklearn: `predict` → `-1` anomaly / `+1` normal; `decision_function` for a continuous score (AEGIS negates so higher = more anomalous).

### Policy with the rest of the stack

- Heartbeat: still runs XGBoost; anomaly **lowers confidence** (does not blank features).  
- Old Guard: `confidence = 0.45` if anomaly.  
- Agent path: can pause for **Manual Audit** on anomaly (HITL for data quality).

### Interview line

> “Isolation Forest asks ‘do I trust this reading?’ XGBoost asks ‘how risky is the site?’ They are complementary.”

---

## 3. Old Guard (physics / rules referee)

### What it is

**Not ML.** Deterministic checks in `api/services/validation.py` (`evaluate_physics`). Nickname: the experienced engineer / SOP that refuses a calm model when the world looks dangerous.

### Rules (demo defaults)

| Rule | Condition |
|------|-----------|
| Physics failure (flood/wind) | `surge > elevation` **and** `wind > 100 mph` |
| Thermal critical | `oil_temp > 95°C` |
| Model “safe” | `risk_score < 0.3` |
| **ConflictFlag** | (physics failure **or** thermal) **and** model safe |

Goal in code: catch **false negatives** (model says safe, physics says fail).

### Why it exists / does it make sense?

**Yes.** Industry guidance for grid / critical AI stresses:

- AI as **advisory**, not closed-loop trips  
- **Deterministic** protection / EMS remain systems of record  
- **Rule-based safety overrides** and failover when ML is wrong or low-confidence  
- Hybrid physics / expert rules + data-driven models  
- Extra care on **false negatives** for rare extremes  

Old Guard is a **lightweight simulation of that hybrid safety pattern**, not a simulation of protective relays.

### Demo honesty

For asset **SUB-001**, heartbeat may **clamp** the XGB score low (unless `--no-demo-conflict`) so ConflictFlag always appears for assessors. Say that if asked; do not claim it proves live model failure.

Elevation is used in **labels** and **Old Guard**, but **not** in XGB `FEATURE_COLS`. That is intentional: flood-over-pad geometry lives in the referee.

### Interview line

> “We’re not replacing relays. We’re showing ML risk plus a deterministic physics disagreement flag plus human authorization—the advisory stack pattern.”

---

## 4. NetworkX (dependency / cascade graph)

### What it is

A **directed graph** of assets: edge `parent → child` means parent feeds / supports child. **Not ML.** Graph reachability answers “who fails next?”

**Code:** `api/services/graph.py`  
**Core call:** `nx.descendants(g, asset_id)` → all downstream nodes  
**Consumers:** impact API, map traces, briefs, agent `impact_node` (prefer Hospital / WaterPlant / Pump lifelines)

### Why this choice

| Reason | Fit |
|--------|-----|
| Structure ≠ tabular risk | Cascades are relationships |
| Explainable | Point at edges on the map |
| Small graph | ~50 nodes; NetworkX is enough |
| Honest PoC | Avoid claiming full power-flow / GNN without true topology |

**Why not GNN / DigSILENT yet:** need breaker-true models and history; harder to explain; weeks-scale PoC prioritization.

### “Math”

Directed graph \(G=(V,E)\). Descendants of \(u\) = nodes reachable by directed paths from \(u\). Implemented as search (BFS/DFS) along outgoing edges.

### Honesty

Edges are largely **inferred nearest-lifeline** demo dependencies, not true switching topology. Still valuable: risk without impact is incomplete for an incident commander.

### Interview line

> “NetworkX turns a 0–1 score into a cascade story. Edges are inferred for the demo; a pilot would ingest real GIS/connectivity. We skipped GNN on purpose.”

---

## 5. How they work together (scenarios)

| Scenario | IF | XGB | Old Guard | NetworkX |
|----------|----|-----|-----------|----------|
| Real storm, sensors OK | Normal | High | Often quiet (score already high) | Shows hospital / water downstream |
| Spoofed / stuck sensors | Anomaly | Anything | Confidence down | Still shows structural impact |
| Flood over pad + extreme wind, model calm | Maybe normal | Low (FN) | **ConflictFlag** | Still lists who depends on site |
| Hot oil > 95°C, model calm | Maybe | Low | **ConflictFlag** | Same |

**Commander narrative:**

1. Trust the vector? (IF)  
2. How urgent? (XGB + Old Guard)  
3. Why does it matter? (NetworkX lifelines)  
4. Authorize protect action? (HITL + audit)

GenAI (optional / FAKE) only **phrases** grounded facts from these layers. It is **not** the risk engine.

---

## 6. What is deliberately *not* in the prototype

| Capability | Status |
|------------|--------|
| Live SGW control-room feeds | Hybrid public GIS/weather + sensor **proxy** |
| Unsupervised switching | Forbidden by design |
| Sword crew / spare optimization | Roadmap Phase 3 |
| GNN / full power-flow | Later if topology exists |
| Production NERC CIP certification | Design posture only |
| Heatwave / wildfire feature parity | Storm case study first |
| SHAP per-prediction attribution | Global importance × value for now |

---

## 7. Cheat sheet: 20-second pitches

**Stack**  
> Tabular risk (XGBoost), sensor integrity (Isolation Forest), physics veto (Old Guard), cascade impact (NetworkX), human approval. GenAI briefs only.

**XGBoost**  
> Gradient-boosted trees on load, oil temp, wind, surge. Right model class for tabular risk; synthetic labels for the demo; retrain on real outcomes in pilot.

**Isolation Forest**  
> Unsupervised outliers on the same features. Separates “weird sensors” from “dangerous weather.”

**Old Guard**  
> Deterministic flood/wind/thermal rules vs calm model score. Catches false negatives. Pattern matches hybrid safety guidance; thresholds are PoC-simple.

**NetworkX**  
> Directed feed graph; descendants = who fails next. Explainable; inferred edges for demo; not a GNN or EMS contingency engine.

---

## 8. File map

| Path | Role |
|------|------|
| `scripts/train_xgb.py` | Fit XGB + IF + preprocess/scaler |
| `backend/api/services/predict.py` | Synthetic labels, load model, score |
| `backend/api/services/inference.py` | Batch score, top drivers |
| `backend/api/services/anomaly.py` | Isolation Forest train/predict |
| `backend/api/services/validation.py` | Old Guard / ConflictFlag |
| `backend/api/services/graph.py` | NetworkX build + descendants |
| `backend/api/management/commands/run_heartbeat.py` | Full pipeline + SUB-001 demo clamp |
| `backend/api/agent/nodes.py` | Agent nodes: anomaly, predict, impact, brief |
| `artifacts/xgb_risk.joblib` | Trained risk model |
| `artifacts/isolation_forest.joblib` | Trained anomaly model |

---

*Prep note: Prefer sounding precise and bounded over sounding fully production-ready. Assessors reward prioritization and honesty.*
