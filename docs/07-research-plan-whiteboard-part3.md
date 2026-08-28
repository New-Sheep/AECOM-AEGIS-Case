# AEGIS Research & Plan — Whiteboard Digest (Part 3)

**Source:** AI tutor / Miro research session (screenshots 13–18)  
**Status:** Digested; more may follow  
**Prior:** `05-…part1.md`, `06-…part2.md`  
**Caveat:** Boards mix **aspirational enterprise architecture** with a **lean 2-day MVP**. Prefer the Reality Check / Power-Trio for what to build; use deep GNN/ST-GAT content for PRD depth + interview talk-track.

---

## Locked / Reinforced (This Batch)

| Decision | Choice |
|----------|--------|
| Boardroom loss math (working) | ~**$30M** unmitigated per major event (10 × ~$3M transformers) |
| ROI narrative | ~**$25M+** annual value framing (assets + fines); refine with assumptions |
| Lean prototype | **Heuristics + GenAI + small mock dataset** (not full GNN Day 1) |
| MVP “Power-Trio” | **XGBoost** (asset) + **heuristic dependency lookup** (grid impact) + **GPT-4o** (brief) |
| Suggested hackathon stack | Streamlit + FastAPI + Pandas + NetworkX + OpenAI/Anthropic |
| Home-stretch status (from board) | Problem ✓ · AI caps ✓ · Architecture ✓ · **Roadmap ⚠ then filled** |

---

## 1. Boardroom Math — $30M Value Creation (Harmonized)

### Loss estimate (deconstructed)

| Step | Assumption | Result |
|------|------------|--------|
| Asset base | ~**500** substations × **2** main transformers | **~1,000** transformers |
| Scale check | 8M residents ≈ 2.5M meters; ~1 substation / 5k residents | ~500 substations |
| Storm exposure | Major storm hits ~**20%** of territory | ~100 substations at high risk |
| Destruction rate | ~**1%** of transformers destroyed *or* ~**10%** of flooded assets total-loss (boards use both framings) | **~10** transformers lost |
| Unit cost | Replacement + labor + emergency shipping ≈ **$3M** / unit | **~$30M** total damage |

### Supporting narrative

- Cumulative value creation over years (chart on board)
- Unmitigated ~$30M vs mitigated residual (~$5M illustrated)
- Side benefits cited: **1 day faster restoration**; ~**$4.5M** human/catering cost avoided (illustrative)

### Master review one-liner

| | |
|--|--|
| **Why** | Fragmented data → operational blindness → **$30M+** losses |
| **How** | AEGIS AI decision engine / Shield |
| **ROI** | Save ~5 transformers + avoid fines ≈ **$25M+** annual value (board claim) |

> Earlier boards used ~100 substations / ~$400k–$1M unit costs. **Prefer one story for the exec brief** — the $30M / 500-substation / $3M-unit path is the most fully spelled out here.

---

## 2. “2-Day” Prototype Strategy (Build Bible)

**Principle:** Logic + UI over algorithm complexity.

| Component | Do this | Not this (Day 1) |
|-----------|---------|------------------|
| **Data** | CSV/JSON for **~5 substations** with realistic fake sensors | Live SCADA |
| **AI logic** | Simple heuristics: `IF WaterLevel > Elevation THEN Risk = High` | Trained GNN / full XGBoost pipeline (optional later) |
| **GenAI** | Python + OpenAI/Claude: risk JSON → “Summarize for a CEO” | Full LangChain agent mesh |
| **UI** | Risk gauge + historical trend + Briefing text area | Full enterprise command center |

### Logic stack (3 tiers)

```
Narrative Layer   → GenAI briefing (non-technical users)
Risk Engine       → Scoring heuristics (gauge > threshold → risk)
Live / Mock Data  → Weather + assets
```

---

## 3. Delivery Roadmap (Updated This Batch)

| Phase | Timing | Focus | Key work |
|-------|--------|-------|----------|
| **1. PoC & MVP** | Weeks **1–4** | Situational awareness | GIS + historical weather; LLM copilot on simulated data |
| **2. Pilot Ops** | Months **2–4** | Shadow mode | Live SCADA + weather; predictive scoring |
| **3. Enterprise** | Months **5–7** | Full coordination | Restoration optimizer, public alerts, scaled cloud |

> Still conflicts with Part 2 (Weeks 1–6 / Mo 2–9 / Mo 9–18) and sample briefing. **Recommend locking Phase 1 = Weeks 1–4/6, Phase 2 = Mo 2–4, Phase 3 = Mo 5–9** for final docs unless AECOM sample requires otherwise.

### Home-stretch checklist (board)

1. Problem statement — Complete  
2. AI capabilities — Complete  
3. Technical architecture — Complete  
4. Delivery roadmap — Was “Not Started”; this batch fills it  

Closing note on board: *Mission Briefing COMPLETE — vision, tech, math, roadmap.*

---

## 4. Enterprise Architecture (PRD Depth — Not All MVP)

### Production-oriented pipeline (aspirational)

```
GIS (PostGIS) + SCADA live + Weather API
        → Stream processing (Spark / Flink) + Vector DB (Milvus / Pinecone)
        → LLM orchestrator (LangChain)
        → Executive briefing + spatial outputs
```

### Backend stack list (enterprise talk-track)

1. PostgreSQL + PostGIS  
2. FastAPI  
3. Celery or Airflow (weather refresh)  
4. Pandas (munging)  

### UX outputs

Executive briefing · Field ops dashboard · Public alerts

---

## 5. Three-Layer AI Brain (Theory → Product Map)

### Layer 1 — Predictive ML (foundation)

- Models: Prophet, XGBoost, LSTM  
- Input features \(X_i\): temperature, humidity, wind, surge, age, maintenance history  
- Output: risk score per asset for **T+1 … T+12 hours**  
- Mechanics: ensemble / sum of trees → final risk score  

**Decision-tree teaching example:**

```
Is Surge > 5ft?
  → High risk branch vs Low risk
  → further splits: Asset Age > 20yr, Pop. density, …
```

**Boosting loop (interview-ready):** Tree1 guesses → misses Substation 7 → Tree2 focuses on residual error → model improves.

| Classic tree (ID3/CART) | Gradient boosting (XGBoost) |
|-------------------------|-----------------------------|
| Entropy / Gini; full tree | Objective gradients; trees fix prior errors |

### Layer 2 — Relationship logic (GNN)

**Why GNN for SGW:**

1. Cascade prediction — blackouts before they travel  
2. Criticality ranking — which substation is the “heart”  
3. Soft failure detection — anomalies only visible vs neighbors  

**How a GNN thinks:** Look around → share status → update own risk.

**Message-passing intuition:** “I’m overloaded” / “Substation 4 is down.”

**GNN vs Graph Search (“GPS vs Brain”):**

| | Graph search | GNN |
|--|--------------|-----|
| Logic | Binary connected? | Weighted (e.g. 80% overloaded) |
| Prediction | Static map | If A fails, B overheats in 20 min |
| Patterns | Structural only | Learns historical cascade physics |

**GNN vs MLP:** MLP is point-wise; GNN aggregates neighbors \(N(i)\).

**Feature factory (supervised):**

- X = grid state ~2h before event; Y = failed/survived  
- Loss: binary cross-entropy  
- Aggregate neighbor features → multiply by W → hidden state → risk %  

**Attention (GAT):** Avoid “average trap” — focus on dangerous neighbors.  
**ST-GAT / ST-GNN:** Spatial GNN + temporal LSTM/GRU — “ultimate engine” for cascades over time.

**Cold-start for GNN:** Transfer learning (FL/TX utilities) + synthetic digital twin; ST-GNN puts RNN/LSTM per node before neighbor share.

### Layer 3 — GenAI voice

GPT-4o / Claude (+ LangChain in enterprise view) consumes Layer 1 scores + Layer 2 impact → exec summary + recommendations.

### Algorithm-to-problem map (“Which brain solves which pain?”)

| Problem | Question | Best algorithm |
|---------|----------|----------------|
| **Asset health** | Will *this* transformer blow in 3 hours? | XGBoost / time-series (single asset) |
| **Grid resilience** | If I turn off Sub A, what happens to the hospital? | GNN or graph search (connections) |

### Asset-view → Node-view

Single asset icon → feature map / network layout → GNN node graph (system view).

### Why “deep” matters for the Shield

1. Non-linearity — physics IF-THEN misses  
2. Embeddings — substation as high-dim vector  
3. Training — learn shutdown timing from many simulated storms  

Deep stack beyond surface:

| Area | Implementation | SGW use |
|------|----------------|---------|
| Graph DL | GNN | Cascading outages across ~500 nodes |
| CV | YOLO / ResNet | Drone: sag, vegetation, fire risk |
| Recurrent | LSTM / GRU | Non-linear energy spikes XGBoost may miss |

---

## 6. Simplicity Ladder (MVP Argument)

| Alternative | How | Why better *for now* |
|-------------|-----|----------------------|
| **Heuristic rules** | `IF Surge > 5ft AND Age > 20 THEN Risk = 90%` | 100% explainable; Day 1 |
| **Simple regression** | Trend sensor upward | Fast; tiny compute |
| **Lookup tables** | Sub-4 → Hospital-1 | Humans trust readable lists |

| Approach | Generalization | Scalability |
|----------|----------------|-------------|
| Hard rules | Poor / rigid | Low (rule per asset) |
| Fuzzy logic | Degrees of truth | Medium (manual tune) |
| ML (XGBoost) | Learns patterns | High (one model ≈ 500 substations) |
| Deep / GNN | Auto thresholds | High — learns “physics” of fleet |

Fuzzy membership example: Cool / Healthy / Hot on core temp; alarm if temp membership Hot (e.g. >75°C framing).

---

## 7. Non-DL Powerhouse Suite (Sword / Ops)

| Tool | Job | SGW example |
|------|-----|-------------|
| **MILP** | Crew routing | 20–50 trucks → 200 sites; \(\min \sum c_{ij}x_{ij}\) s.t. capacity |
| **Isolation Forest** | Sensor integrity | Impossible voltage spikes |
| **LOF** | Local density outliers | Substation “quiet” while neighbors busy |
| **Kalman filters** | State estimation | Denoise SCADA |
| **Autoencoders** | Reconstruction error | “Weird state” if can’t reconstruct |
| **Dijkstra** | Fastest repair route | Crew pathing |
| **Connected components** | Flood “islands” | Grid fragments cut off |

---

## 8. Reality Check — Narrow MVP Scope (AUTHORITATIVE FOR BUILD)

**Power-Trio for a defensible MVP:**

| Capability | Choice | Reason |
|------------|--------|--------|
| **1. Asset prediction** | **XGBoost** *(or heuristics first if timeboxed)* | Fast, explainable, works on CSV |
| **2. Grid impact** | **Heuristic rules / lookup** (Phase 1) | `IF Sub-A fails → Hospital B at risk` — zero GNN dev time |
| **3. Intelligence layer** | **GenAI (GPT-4o)** | Briefing via simple API calls |

### Hackathon / prototype tech stack (board)

1. **Frontend:** Streamlit  
2. **Backend API:** FastAPI  
3. **Data processing:** Pandas + NetworkX  
4. **Model storage:** Pickle / Joblib  
5. **Intelligence:** OpenAI / Anthropic API  

### System architecture (4-tier)

```
Sources (GIS, Weather, SCADA mocks)
  → Processing engine
  → Intelligence layer (GenAI)
  → Front-end dashboard
```

### Road ahead

- AEGIS Vault (GitHub repo)  
- Field feedback loop → enterprise features (GNN, CV, optimizer)

---

## 9. ST-GAT Value Props (Interview Depth — Not MVP Scope)

1. Zero operational blindness — cascades ~2h early  
2. Dynamic reflex — sudden weather/load shifts  
3. Explainable scores — attention weights (“worried about Sub-A because Sub-B is melting”)

Formula framing from board:  
\(h^{(t)} = GRU(Attn(History, i, j), m_{i,j}^{(t)})\)

---

## Conflicts Update (Carry Forward)

| Topic | New signal this batch | Recommendation |
|-------|----------------------|----------------|
| Unmitigated loss | **$30M** spelled out | Use in exec brief with assumptions footnote |
| Annual ROI | **$25M+** | Pair with $30M loss math |
| Substation count | **~500** (vs earlier ~100) | Lock **500** for boardroom math |
| Phase 1 length | Weeks **1–4** | Align PRD roadmap |
| Phase 3 end | Months **5–7** | Shorter than Part 2’s 18-mo plan — pick “demo realism” vs “enterprise realism” |
| Build vs PRD | Full GNN/ST-GAT vs Power-Trio | **PRD:** full vision · **Prototype:** Power-Trio |
| Streamlit vs richer UI | Streamlit named | Fine for case; React OK if faster for you |

---

## Prototype Checklist (Updated)

- [ ] Mock **5 substations** JSON/CSV (Big Three signals where possible)  
- [ ] Heuristic risk: surge vs elevation; temp threshold  
- [ ] Dependency **lookup table** (sub → hospital / water) — NetworkX optional  
- [ ] Optional XGBoost on CSV if time  
- [ ] FastAPI Risk API  
- [ ] Streamlit (or equivalent) dashboard: gauge + trend + briefing  
- [ ] GenAI: risk payload → CEO one-liner + trade-off  
- [ ] Decision log  
- [ ] README + architecture/assumptions/limits  
- [ ] 5–10 min video walkthrough  

---

## Next

Send remaining screenshots (PRD draft structure, video outline, final UX, etc.) → Part 4 / consolidation doc.
