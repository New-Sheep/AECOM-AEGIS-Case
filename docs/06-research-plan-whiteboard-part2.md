# AEGIS Research & Plan — Whiteboard Digest (Part 2)

**Source:** AI tutor / Miro research session (screenshots 7–12)  
**Status:** Digested; more screenshots expected  
**Prior:** See `05-research-plan-whiteboard-part1.md`  
**Caveat:** Some boards repeat topics with **different numbers** — conflicts called out below.

---

## Locked / Reinforced Decisions

| Decision | Detail |
|----------|--------|
| MVP assets (“Big Three”) | **Bulk transformers**, **Control-room DC batteries**, **Switchgear** |
| Tech pyramid | Data (Python/FastAPI mocks) → Classical ML → Heuristic risk → GenAI |
| Prototype style | **2-day lean:** JSON/CSV mocks + heuristics first + GenAI briefing |
| HITL | AI recommends; human executes (“Dead Man’s Switch”) |
| XAI | Top-3 drivers on every risk score |
| UI spine | Predictive heatmap + Intelligence panel + Forecast/health monitor |

---

## 1. MVP Focus — The “Critical Few” (Big Three)

| Asset | Metaphor | Why critical | Primary AI / data signal |
|-------|----------|--------------|--------------------------|
| **Bulk Power Transformers** | Heart | Zero spares; ~12-month replacement | SCADA — oil temp & load |
| **Control Room Batteries (DC)** | Nervous system | Station “goes blind”; can’t remote-reset | GIS — elevation vs flood level |
| **Switchgear** | Joints | Re-route power to hospitals / lifelines | SCADA — status open/closed |

**Master plan pillars (eagle-eye):**

| Pillar | Business (“Why”) | Tech (“How”) |
|--------|------------------|--------------|
| 1. Problem | Operational blindness = $ millions (boards also cite ~$400M / $100M+ framing) | Fragmented GIS/SCADA silos |
| 2. Solution | AEGIS “Shield” dashboard | Predictive risk engine (ML) + executive briefing (GenAI) |
| 3. MVP Scope | Save the Big Three | Mocked Python pipeline + decision dashboard |

**Strategy v1.0 success triangle:** Asset Survival ($) ∩ Rapid Delivery (mocked prototype) ∩ Strategic Clarity (exec dashboard)

**Delivery steps:**

1. **Normalize** — GIS structures, NOAA API, SCADA mocks  
2. **Prioritize** — Risk scores for transformers (then Big Three)  
3. **Interface** — GenAI report + health heatmap  

---

## 2. Technical Foundation — Stack Pyramid

| Layer | Role | MVP tech |
|-------|------|----------|
| **1. Data Ingestion** | Mock GIS / SCADA / NOAA | Python / FastAPI + JSON |
| **2. Classical ML** | Temp / time-series forecasting | XGBoost or Prophet |
| **3. Risk Engine** | Surge height vs asset elevation | Custom heuristic (Python) |
| **4. GenAI** | Briefings / tool calling | GPT-4o or Claude 3.5 Sonnet (+ LangChain tool calling in boards) |

**AI/ML engine (“The How”) — summary:**

1. Time-series forecasting — Prophet/XGBoost; ~12-hour window (temp / flood)  
2. Anomaly detection — impossible sensor jumps  
3. GenAI (GPT-4o + RAG) — numbers → NL executive summaries  
4. Graph logic — Substation → Hospital dependency for shutdown impact  

**Architecture pyramid (ops view):**

```
Top:    Dashboards, Copilot, Optimization
Middle: ML Forecasting, NLP Engine, Graph Logic
Bottom: GIS, SCADA, Weather, Work Orders
```

---

## 3. Functional Requirements (Prototype-Aligned)

| ID | Requirement | Benefit / UI hook |
|----|-------------|-------------------|
| **FR-01** | Live asset health scores (0–100) on GIS map | Immediate high-risk zone awareness → Heatmap |
| **FR-02** | Risk alert if predicted transformer temp **> 95°C** | Proactive failure prevention |
| **FR-03** | GenAI briefing agent: one-sentence NL summary ~every **10 min** | Zero-effort exec updates → Intelligence Panel |
| **FR-04** | **72-hour** look-ahead asset-health forecast from weather | Forecast Monitor |
| **FR-05** | Immutable decision log for user control actions | Action Center / audit |
| **FR-06** | GNN-based dependency mapping for 2nd-order impacts (e.g. water plants) | Predictive Heatmap / Domino tooltip |

---

## 4. UI Component Map

### Predictive Heatmap

- Coastal / territory map with asset icons + risk overlays  
- **Domino tooltip:** Hover red substation → dotted GNN-style link to hospital it powers  
- **Confirm Action popup:** Trade-off before shutdown, e.g.  
  > “You will save $14M in equipment, but Zone B will be without power for 4 hours.”

### Intelligence Panel

- GenAI + RAG for decision clarity (briefings grounded in Risk API / docs)

### Forecast & Health Monitor

- Predictive maintenance view (non-storm + storm)  
- Chart: current transformer temp vs ML predicted trend crossing critical threshold  

---

## 5. Data Requirements & Dependencies

| Dataset | Critical fields | Source |
|---------|-----------------|--------|
| Asset geospatial | Lat/lon, elevation, age, connectivity | Legacy GIS |
| Operational telemetry | Transformer temp, oil, load, battery voltage | SCADA stream |
| Environmental | Wind, storm surge height, precipitation | NOAA / weather APIs |
| Historical truth | Failure dates, maintenance logs, damage reports | Work management system |

Flow: GIS + SCADA + NOAA → **Unified Brain** → Risk/Impact Heatmap + Data Readiness Engine

---

## 6. Dark Sensors, Corrupt Data & Edge Cases

### Data-quality mitigations

| Failure mode | Mitigation |
|--------------|------------|
| **Sensor blackout** (no signal) | KNN — proxy risk from neighboring substations |
| **Drift / noise** (impossible values, e.g. 500°C) | Anomaly detection → fall back to last known good |
| **Latency / stale data** | Drop **confidence score**; visual warning on dashboard |

### SGW “Black Swan” edge cases

| Scenario | Response |
|----------|----------|
| **Comms failure** (dashboard cut) | Edge intelligence — lean local model; autonomous local shutdown path |
| **Conflicting data** (Weather “sunny” vs SCADA “flooded”) | Heuristic weighting: **physical SCADA overrides external APIs** |
| **Human echo chamber** (exec ignores ~3 alerts) | Escalation agent pings next command level after ~10 min |

### Cyber-physical resilience (roadmap depth)

| Threat | Detect | Respond |
|--------|--------|---------|
| Physical attack | Multi-node voltage drops | Agentic isolation / air-gap zone |
| Control hack | Rapid impossible sensor changes | Substation reflex (autonomous shutdown) |
| Cyber-cloud attack | SCADA commands violating physics | Integrity blocks in math layer |

---

## 7. Evaluation — ML Brain + GenAI Narrative

### Predictive model KPIs

| Metric | Intent | Targets (boards vary — see Conflicts) |
|--------|--------|----------------------------------------|
| **Recall (Safety)** | Must not miss failures (FN = explosion risk) | ~99%–99.9% |
| **Precision (Trust)** | Limit false alarms / CEO fatigue | ~50%–70%+ (boards disagree) |
| **Prediction lead time** | Time to safe load ramp-down | ~2–4 hours |

### GenAI evaluations

| Check | Method |
|-------|--------|
| Grounding / faithfulness | RAG triangulation + evaluator LLM vs raw SCADA numbers |
| Answer relevance | Expert grade 1–5 |
| Safety / toxicity | Red teaming in mock crises |

Loop: Document/input → LLM → Peer-judge evaluate → Pass / refine

### Who guards the guardian?

1. **Hardcoded heuristics** — Physical limits override AI (e.g. water at 4 ft)  
2. **Confidence thresholding** — Low confidence → indeterminate / human review  
3. **HITL** — Always show raw sensors beside AI summary  

---

## 8. Cold-Start QA (No Disaster History)

| Method | How without history | QA validation |
|--------|---------------------|---------------|
| **Physics / digital twins** | Manufacturer specs (e.g. melts at 110°C) → synthetic failures | Stress test until AI flags |
| **Transfer learning** | Train on peer utility (e.g. FPL); fine-tune for SGW | Cross-region validation |
| **Expert-in-the-loop (Delphi)** | Encode senior engineer rules (“at what water level do you pull the plug?”) | “Turing test for ops” — AI vs peer recommendations |

Boards show illustrative validation curve: AI risk vs actual failure history (~94% match claim — treat as aspirational demo number).

Flow: Simulation (digital twins) → QA filter → Reality (live grid)

---

## 9. Security, Governance & HITL

| Control | Rule |
|---------|------|
| **XAI** | Every risk score shows top-3 drivers (e.g. Wind, Age, Load) |
| **Dead Man’s Switch** | AI recommends shutdown; only authorized human executes |
| **Authority level** | Boards say both “Level 5” and “Level 1” — **pick one for final PRD** |
| **FERC / NERC logging** | Tamper-proof audit of AI recommendations + human overrides |
| **Hard limits** | Physics scripts override “AI says fine” when sensors disagree |

### Control logic by scenario

| Scenario | Target latency | Control logic |
|----------|----------------|---------------|
| Forecasted (hurricane) | &lt; 5–15 min (boards vary) | Human review of AI summary |
| Sudden (fire / attack) | &lt; 1 second | Autonomous edge reflex + manual override |

---

## 10. Success Metrics & Boardroom Math

### Impact metrics (consolidate carefully — see Conflicts)

| Lens | Theme | Example targets from boards |
|------|-------|-----------------------------|
| Financial | CapEx preservation | &gt;$5M / &gt;$10M / $15M+ per major event |
| Operational | Decision latency | &lt;10 min / &lt;15 min alert → response |
| Technical | Accuracy | 70%+ precision / 99%+ recall |
| Public safety | Critical uptime | Minimize hospital / water outages |

### “Braveheart” / boardroom human math (narrative)

1. SGW base: **8M** people  
2. Outage risk: **~4M** (50%)  
3. AEGIS gain: **~1 day** faster restoration  
4. Result: **~4M human-days** of suffering avoided  

### Big Money ROI table (illustrative)

| Cost driver | Unmitigated risk (order of magnitude) | AEGIS angle |
|-------------|--------------------------------------|-------------|
| Asset destruction (CapEx) | ~$15M–$50M transformers | Prevent catastrophic loss; ~$15M+ save framing |
| Regulatory fines | ~$5M–$20M inefficient / unfair restoration | Audit logs; fair response proof; ~$5M+ |
| Insurance premiums | Rising | Position AI as loss-mitigation → ~10–15% premium reduction thesis |
| Reputation | Trust collapse | “Tech leader in resilience” |

**Indirect ROI:** avoid 2-day delay for ~10% assets (~$2M–$10M); lawsuit avoidance via equitable restoration data (~$2M+).

**Deconstructing spend math (illustrative):** ~100 substations × ~3 main transformers; major hurricane destroys ~1%; ~$400k–$1M per unit → waterfall from high unmitigated spend toward mitigated target.

---

## 11. Delivery Roadmap (Exec-Aligned)

| Phase | Timing | Focus |
|-------|--------|-------|
| **1. POC & MVP** | Weeks 1–6 | Situational awareness: GIS + historical weather + AI copilot |
| **2. Pilot Ops** | Months 2–9 *(board text)* | Shadow mode; live SCADA + weather; predictive scoring |
| **3. Full Scale** | Months 9–18 | Restoration optimizer, public alerts, scaled cloud |

> Note: Sample exec brief (`03-…`) used Months 2–4 / 5–9 — **harmonize phases** in final submission.

---

## 12. “2-Day” Lean Prototype Strategy

| Layer | Lean approach |
|-------|----------------|
| **Data** | Fake telemetry CSV/JSON — don’t wait for live SCADA |
| **AI logic** | Heuristics first: `IF WaterLevel > Elevation THEN Risk = High` |
| **GenAI** | Thin Python + OpenAI/Claude API: risk JSON → briefing prompt |

Build order stays: **Normalize → Prioritize → Interface**.

---

## Conflicts to Resolve Before Final Docs

| Topic | Variants seen | Action |
|-------|---------------|--------|
| CapEx save target | &gt;$5M vs &gt;$10M vs $15M+ | Pick one conservative range for exec brief |
| Decision latency | &lt;5 / &lt;10 / &lt;15 min | Split by scenario (forecasted vs sudden) |
| Precision target | 50% vs 70%+ | Explain intentional FN/FP tradeoff; don’t leave both unexplained |
| HITL authority | Level 1 vs Level 5 | Single definition in PRD |
| Problem $ framing | $400M vs $100M+ vs millions | One consistent board-level number + footnote assumptions |
| Roadmap months | Part 1 Phase 2 = Mo 2–4; Part 2 = Mo 2–9 | Align with sample briefing or update both |
| LangChain | Mentioned in stack | Optional for hackathon MVP — thin SDK may be enough |

---

## Prototype Build Checklist (from Parts 1–2)

- [ ] Mock GIS JSON (Big Three + lat/lon/elevation/connectivity)  
- [ ] Mock SCADA heartbeats (temp, oil, load, battery V, switchgear state)  
- [ ] Mock weather / surge JSON  
- [ ] Heuristic risk engine (surge vs elevation; temp threshold 95°C)  
- [ ] Optional: Prophet/XGBoost forecast curve for demo  
- [ ] Map heatmap UI (health 0–100)  
- [ ] Domino / dependency tooltip (even if rule-based, not full GNN)  
- [ ] Confirm-action trade-off modal  
- [ ] GenAI Auto-Brief (grounded on Risk API)  
- [ ] Immutable decision log  
- [ ] Confidence score when data stale  

---

## Next

Await remaining screenshots (PRD outline, video storyboard, final prototype UX, etc.) → Part 3.
