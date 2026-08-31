# AEGIS North Star

**AI-Enabled Grid & Infrastructure Shield**  
**Client:** Southeastern Grid & Water (SGW)  
**Role:** AECOM AI Solution Engineer Case  
**Document purpose:** Single source of truth for thinking, conclusions, and final deliverables (PRD · Executive Briefing · Prototype · Video · Live interview)

| | |
|--|--|
| **Status** | **Submission package ready for review** · Prototype **LOCKED** |
| **Strategy** | **Shield first, Sword second** |
| **MVP user** | Incident Commander / Executive |
| **Prototype stack** | Django/DRF + Streamlit · hybrid mocks · XGBoost · Isolation Forest · NetworkX · GenAI/FAKE |
| **Supporting digests** | `01`–`08` in this folder (sources; this file supersedes for decisions) |

### Submission package (Deliverables 1–3)

Written deliverables use **plain case-brief voice** (short sentences, limited jargon). This north star stays the internal thinking log.

| Deliverable | File |
|-------------|------|
| D1 PRD | [`DELIVERABLE-1-PRD-AEGIS.md`](DELIVERABLE-1-PRD-AEGIS.md) |
| D2 Exec briefing | [`DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`](DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md) |
| D3 Prototype + README | Repo root [`README.md`](../README.md) (locked) |
| D3 Video script | [`DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md`](DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md) |
| Assessor handover | [`18-PROTOTYPE-AND-PRD-HANDOVER.md`](18-PROTOTYPE-AND-PRD-HANDOVER.md) |
| Brief gap analysis | [`19-GAP-ANALYSIS-BRIEF-VS-SUBMISSION.md`](19-GAP-ANALYSIS-BRIEF-VS-SUBMISSION.md) (**gap-fill applied** into D1/D2) |
| Tech deep dive (XGBoost / IF / Old Guard / NetworkX) | [`20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md`](20-TECH-DEEP-DIVE-MODELS-RULES-GRAPH.md) |

---

## 0. How to Use This Document

| You need to… | Go to… |
|--------------|--------|
| Explain your brainstorming in interview | §1 Journey · §2 Problem · §3 Priorities |
| Write the **PRD** | §4–§10 · §12 Deliverable 1 checklist |
| Write the **Executive Briefing** | §2 · §3 · §11 ROI · §12 Deliverable 2 checklist |
| **Build the prototype** | §8–§10 · §12 Deliverable 3 checklist |
| Defend AI choices beyond LLMs | §5 Toolbox · §7 Roadmap depth |
| Show domain credibility | §2.3 Domain expert input |

---

## 1. Research Journey — How the Thinking Evolved

This is the story of the work, not just the conclusion.

### Phase A — Understand the assignment

**Inputs:** AECOM Technical Assessment Brief (`01`)

- Three pre-interview deliverables: **PRD**, **Exec Brief**, **Prototype + 5–10 min video**
- Live session: ~30 min presentation/demo + ~30 min Q&A
- Client context is **intentionally incomplete** → success = explicit assumptions, prioritization, clarity over polish
- Judging cares about: structured thinking, technical depth, communication, AI **beyond** LLMs

**Conclusion A:** Don’t boil the ocean. Ship one sharp workflow that proves solution engineering.

---

### Phase B — Ground in real infrastructure physics

**Inputs:** Electrical engineering HoD / VP brainstorm (`02`)

Framing: **Hazard → Vulnerability → Impact → Preparedness → Recovery**

Key realities absorbed:

- Hurricanes and heatwaves hit the **same assets differently** (flood/wind vs thermal overload/sag)
- Cascading failure mode that matters: **loss of power + loss of communication + loss of access + multi-asset failure**
- Zero-spare bulk transformers = CapEx catastrophe (long lead time, huge cost)
- Water/STP depends on power (pumps, MCC, SCADA) — equity and life safety are grid problems too
- Practical artifact: **Disaster Vulnerability Register** per critical asset

**Conclusion B:** Product must score **asset vulnerability under weather**, not just chat about outages.

---

### Phase C — Learn the utility stack & failure modes

**Inputs:** AI tutor whiteboards Parts 1–2 (`05`, `06`)

Literacy locked:

| Layer | Meaning |
|-------|---------|
| **GIS** | Map — where assets are |
| **SCADA** | Nervous system — live telemetry & control (power **and** water) |
| **Weather** | External shock — surge, wind, heat |
| **Unified platform** | Ingest → normalize (sensor ↔ asset) → expose to AI |

Cascading loop:

```
Grid fails → water/pumps stop → social/hospital/firefighting impact
  → more grid stress → deeper failure
```

AI breaks the chain by:

1. **Predictive hardening** (de-energize before destruction)  
2. **Smart prioritization** (survival assets before non-critical load)

**Conclusion C:** AEGIS is a **decision-support Shield**, not an autonomous grid controller.

---

### Phase D — Prioritize under ambiguity (the hard product call)

**Inputs:** Parts 1–2 priority matrices

| Priority | Theme | Business risk | AI family |
|----------|-------|---------------|-----------|
| **P1** | Zero-spare **asset destruction** | CapEx + insurance | Predictive ML / heuristics (**Shield**) |
| **P2** | **Inequitable / slow restoration** | PUC fines, brand, ESG | Optimization / MILP (**Sword**) |
| **P3** | **Data blindness** | Waste, overtime, lag | Unification + anomaly detection |

**Money vs Mission resolution:**  
You cannot restore a hospital if the transformer is ash → **P1 enables P2**.  
Restoring a golf course before a water plant → brand death → **P2 must be on the roadmap**.

**MVP asset focus — “Big Three”:**

| Asset | Metaphor | Why | Primary signal |
|-------|----------|-----|----------------|
| Bulk power transformers | Heart | Zero spare; ~12-month lead | SCADA oil temp & load |
| Control-room DC batteries | Nervous system | Station goes blind | GIS elevation vs flood |
| Switchgear | Joints | Re-route to hospitals | SCADA open/closed |

**Conclusion D (locked):** Prototype = **Shield**. Sword = PRD roadmap + interview depth.

---

### Phase E — Choose algorithms with honesty (vision vs build)

**Inputs:** Parts 3–4 (`07`, `08`)

Teaching depth explored (for PRD + interview):

- Time-series forecasting (trend / seasonality / exogenous shocks)
- XGBoost / gradient boosting for asset failure probability
- GNN / ST-GAT for cascade / neighbor effects
- CV (drone damage / vegetation) — later phase
- MILP for crew routing — Sword
- Isolation Forest / Kalman — sensor integrity

**Reality check — Power-Trio for what we actually ship:**

| Job | MVP choice | Why |
|-----|------------|-----|
| Asset prediction | Heuristics first; optional XGBoost | Explainable, CSV-friendly, Day-1 |
| Grid impact | NetworkX / lookup table | Domino story without GNN training |
| Intelligence | GenAI + tool calling | Numbers → CEO language, grounded |

**Conclusion E:** Show you *understand* GNN/MILP/CV; **build** the sweet spot that demos in days.

---

### Phase F — Design the product surface & governance

**Inputs:** Part 4 UI + defensive depth

Four UI pillars:

1. Global resilience header  
2. Predictive GIS map (glow, path trace, what-if)  
3. AI intelligence / Auto-Brief panel  
4. HITL action center (confirm / override + audit)

Governance ladder: **suggest → expert review → rule+ML agreement → executive-only de-energize**  
Plus: Old Guard heuristics, optional Referee LLM (“reasons not to shut down”), immutable audit log.

**Conclusion F:** Trust > cleverness. False alarms kill adoption; unsupervised switching is out of scope.

---

## 2. The Problem We Are Solving

### 2.1 Client context

SGW serves **8+ million** residents across coastal and inland regions exposed to hurricanes, flooding, heatwaves, and wildfires. Assets span substations, transmission, water treatment, and pumping.

Operational data is fragmented across **GIS, SCADA, weather feeds, maintenance / CMMS, and field dispatch**. During severe weather that causes:

- **Operational blindness** — no unified situational awareness  
- **Catastrophic asset loss** — especially zero-spare transformers  
- **Inequitable / slow restoration** — lifelines and vulnerable communities offline too long → fines, insurance, trust erosion  

### 2.2 Core problem statement (use in PRD)

> How might SGW break operational data silos to **predict infrastructure vulnerabilities hours before impact**, protect unreplaceable assets, and (over time) orchestrate **equitable restoration** under extreme uncertainty — with humans always in control of physical switching?

### 2.3 Domain constraints we respect

- Design for disaster **plus** lost power, lost comms, lost access, multi-asset failure  
- Flood / wind / heat / vegetation / backup power / spares / manpower all matter  
- SCADA may go dark or lie — need confidence scores, KNN proxies, anomaly fallout  
- Physical sensors override “sunny” weather APIs when they conflict  

### 2.4 Explicit assumptions (working)

| Assumption | If wrong |
|------------|----------|
| Major substations have usable SCADA (or we mock it) | Synthetic / neighbor proxies |
| GIS has location, elevation, connectivity (or mock) | Infer proximity graph |
| AI is **advisory only**; humans authorize switching | Non-negotiable for liability |
| Spares / crew rules imperfectly known | Mock constraints; expose config knobs |
| Storm backhaul degrades | Offline cache + confidence decay |

---

## 3. Strategic Thesis — Shield & Sword

```
         ┌─────────────────────────────────────┐
         │     SYSTEMIC RESILIENCE (goal)      │
         │  CapEx survival ∩ Public lifelines  │
         └─────────────────────────────────────┘
                         ▲
           ┌─────────────┴─────────────┐
           │                           │
    THE SHIELD (P1)              THE SWORD (P2)
    Protect assets               Restore equitably
    before destruction           after impact
           │                           │
    Predictive risk +            MILP / optimization
    HITL de-energize             crew + spares + equity
           │                           │
      ★ MVP / PROTOTYPE            ★ ROADMAP / PRD
```

**Slogan for execs:**  
*Don’t scramble in the dark — predict, protect, then restore fairly.*

---

## 4. Product Definition — AEGIS

**AEGIS** is an AI-enabled **decision-support** platform that unifies mock/live GIS + SCADA + weather, scores asset risk, shows dependency impact, and generates grounded executive briefings — with human confirmation for any control action.

### Target users (MVP)

| Persona | Need from AEGIS |
|---------|-----------------|
| Incident Commander / EOC | One pane: threat, money at risk, what to do next |
| Asset / Grid operator | Why this transformer is hot; what fails downstream |
| (Later) Resource coordinator / PIO | Dispatch plans; public/PUC narratives |

### Success metrics (targets for docs; validate in interview)

| Lens | Metric | Working target |
|------|--------|----------------|
| Financial | CapEx preserved per major event | **~$15–30M** avoided loss framing (see §11) |
| Operational | Alert → exec decision latency | **&lt; 15 min** (forecasted storms) |
| Technical | Prefer **high recall**; manage precision | ~**99%** recall aspiration; explain FP tradeoff |
| Safety / equity | Critical lifeline outage duration | Minimize hospitals / water / STP |
| Demo | Brief generation | **&lt; 2 min** from risk payload |

---

## 5. AI Toolbox — What We Use Where

### Classical ML / heuristics (Shield core)

| Technique | Question it answers |
|-----------|---------------------|
| Heuristic rules | Surge &gt; elevation? Temp &gt; 95°C? |
| XGBoost / time-series | Will *this* transformer fail in T+1…T+12h? |
| Isolation Forest | Is this sensor lying / drifting? |
| Kalman (roadmap) | Denoise SCADA |

### Graph methods

| Technique | Question | When |
|-----------|----------|------|
| NetworkX / lookup | If Sub A dies, who goes dark? | **MVP** |
| Centrality / Dijkstra | Criticality; crew path | MVP light / Sword |
| GNN / ST-GAT | Learned cascades & attention | **PRD Phase 2–3** |

### Optimization (Sword)

| Technique | Question |
|-----------|----------|
| MILP / heuristics | Which crew / spare goes where under constraints? |
| RL (stretch) | Dynamic re-route when roads flood mid-shift |

### GenAI / agents

| Technique | Question |
|-----------|----------|
| RAG + tool calling | What does risk mean for the CEO *right now*? |
| Referee agent (stretch) | Why should we *not* shut down? |
| Dispatch SMS agent | Later — not MVP |

### Beyond LLMs (say this in interview)

Forecasting · anomaly detection · graph/criticality · optimization · (later) CV · (later) ST-GNN

---

## 6. Functional Shape of the Solution

### Must-have capabilities (align PRD FRs)

| ID | Capability |
|----|------------|
| FR-01 | Live / mock asset health scores on map |
| FR-02 | Risk alert (e.g. predicted temp &gt; 95°C or flood vs elevation) |
| FR-03 | GenAI Auto-Brief every N minutes / on demand |
| FR-04 | Short-horizon forecast view (demo: hours–72h story) |
| FR-05 | Immutable decision / audit log |
| FR-06 | Dependency / “domino” impact (NetworkX or lookup) |

### Non-functionals (aspirational in PRD; mock in prototype)

- Latency: scoring fast enough for demo (&lt;&lt; 30s on small asset set)  
- Explainability: top drivers + data citations  
- Security narrative: NERC CIP / read-only SCADA / no unsupervised switching  
- Degraded mode: confidence drops when data stale  

### UI — four components (prototype spine)

1. **Global Resilience Header** — threat level, weather, impact tally  
2. **Predictive GIS Map** — glow, path trace, optional what-if surge slider  
3. **AI Intelligence Panel** — grounded briefing + why  
4. **HITL Action Center** — confirm / deny, reason, authorized-by  

### Graduated response (governance)

| Level | Action | Human role |
|-------|--------|------------|
| 1 | Load shed (~20%) | Suggest-only in MVP |
| 2 | Reroute (NetworkX) | Expert review |
| 3 | ML + Old Guard rules agree | Cross-check gate |
| 4 | Full de-energize | **Executive only** |

---

## 7. Architecture

### Prototype (build this)

```
Mock GIS / SCADA / Weather (JSON/CSV)
              │
              ▼
     Analytics Core (Python)
     · Heuristics / optional XGBoost
     · optional Isolation Forest
     · NetworkX impact
              │
              ▼
         FastAPI
     /health /predictive /impact /briefing /control
              │
              ▼
     Streamlit (+ map)
     Header · Map · Brief · Action + Audit
```

### Enterprise (describe in PRD)

```
GIS (PostGIS) + SCADA (read-only) + NOAA/ECMWF + CMMS
        → ingest / normalize / feature store
        → predictive ML + graph/GNN + optimizer
        → GenAI copilots + audit + HITL control plane
        → exec + field + public alert surfaces
```

Django/DRF/Celery = optional enterprise path (ORM, admin, audit). **Do not block MVP on Django.**

### Data for prototype (~5 substations)

Include Big Three signals: oil temp, load, battery/flood elevation, switchgear state, surge, wind, connectivity to hospital/water nodes.

---

## 8. Delivery Roadmap (locked for submissions)

| Phase | Timing | Focus | Ships |
|-------|--------|-------|-------|
| **1. PoC / MVP** | Weeks 1–6 | Situational awareness + Shield | Mock pipeline, heatmap, Auto-Brief, HITL audit |
| **2. Pilot** | Months 2–4 | Shadow mode | Live read-only SCADA/weather; predictive scoring advises only |
| **3. Enterprise** | Months 5–9 | Coordination | Restoration optimizer (Sword), alerts, scale, training |

Trust ladder: **Backtest → Shadow → Pilot on few high-value assets**

---

## 9. Prototype Build Spec (North Star for Code)

### In scope

- [ ] Mock dataset (≈5 substations + dependencies)  
- [ ] Risk scoring (heuristics; XGBoost optional)  
- [ ] Map or list view with risk scores + glow/priority  
- [ ] Impact/path for one node (hospital/water)  
- [ ] GenAI briefing grounded on Risk API JSON  
- [ ] Confirm/override modal with trade-off text + audit log  
- [ ] README: setup, architecture, assumptions, limits  
- [ ] 5–10 min video: end-to-end one workflow  

### Out of scope (mention as future)

- Live SCADA / real breaker control  
- Trained GNN / ST-GAT  
- Full MILP crew optimizer  
- Drone CV  
- Production NERC CIP deployment  

### Suggested API shapes

- `GET /api/v1/assets/health/`  
- `POST /api/v1/assets/predictive/` → risk_score, is_anomaly, drivers  
- `GET /api/v1/network/impact/?node_id=`  
- `POST /api/v1/ai/briefing/`  
- `POST /api/v1/control/shutdown/` (mock + audit only)  

### Example Auto-Brief tone

> Transformer Alpha-12 at 94% risk (surge vs elevation + oil temp). Downstream: Regional Hospital. Recommend executive-authorized safe shutdown within 15 minutes — estimated CapEx protected ~$3M; temporary Zone B outage ~4 hours.

---

## 10. Security, HITL & Trust

Non-negotiables for all three deliverables:

1. **Zero autonomous grid control** in MVP narrative (and prototype)  
2. **Dead man’s switch** — human authorizes Level 4  
3. **XAI** — top drivers on scores  
4. **Grounded GenAI** — cite telemetry/weather fields  
5. **Audit trail** — who, when, why, override  
6. **Hard physics overrides** — water at 4 ft beats “AI says fine”  
7. **SCADA &gt; weather API** on conflict  

---

## 11. Boardroom Math (Executive Briefing)

### Preferred loss model (use consistently)

| Step | Assumption | Result |
|------|------------|--------|
| Scale | ~500 substations · ~2 main transformers | ~1,000 transformers |
| Event | Major storm stresses ~20% of territory | High-risk subset |
| Loss | ~10 transformers destroyed / total-loss | Catastrophic cases |
| Unit cost | Replacement + labor + expedite ≈ **$3M** | |
| **Unmitigated** | | **~$30M per major event** |

### Value story

| Lever | Narrative |
|-------|-----------|
| CapEx shield | Prevent even a handful of bulk transformer losses |
| Insurance | Position AI as loss-mitigation control |
| Regulatory | Documented equitable / reasoned decisions |
| Speed | Hours → minutes for briefing & triage |
| Human impact | Illustrative: faster restoration → millions of “human-days” avoided |

**ROI line for exec deck:**  
*AEGIS targets tens of millions in avoided asset loss per major event, plus fine/insurance/brand downside — starting with a weeks-not-years MVP that proves situational awareness.*

Use sample briefing (`03`) for **tone**; use **this math** for **numbers**.

---

## 12. Final Deliverables — Authoring Checklists

### Deliverable 1 — PRD

Cover all nine required sections; write *your* voice from this north star (samples in `04` are reference only).

- [x] Problem & business context (§2) → `DELIVERABLE-1-PRD-AEGIS.md`  
- [x] Assumptions & unknowns (§2.4)  
- [x] Users & pain points (§4)  
- [x] FR / NFR (§6)  
- [x] AI capabilities — Shield Power-Trio + Sword/GNN/CV roadmap (§5)  
- [x] Architecture & integrations (§7)  
- [x] Data requirements (§7 + domain §2.3)  
- [x] Security / governance / HITL (§10)  
- [x] Success metrics, MVP scope, priorities (§4, §8, §9)  

**PRD emphasis:** structured product thinking for engineers; Big Three; Shield vs Sword; mock→live path.

---

### Deliverable 2 — Executive Management Briefing

- [x] Strategic value — blindness → Shield → resilience/equity (§2–3) → `DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`  
- [x] Financial / ROI — $30M model + levers (§11)  
- [x] Delivery roadmap — Phases 1–3 (§8)  
- [x] Governance & compliance — HITL, audit, NERC/PUC narrative (§10)  
- [x] Scalability — power→water, coastal hurricane→inland heat/fire (§2.3)  

**Exec emphasis:** outcomes, realism, governance — not model math.

---

### Deliverable 3 — Prototype + Video

- [x] Code + README + mocked data (§9) — prototype **LOCKED**  
- [x] One end-to-end workflow: storm → risk → impact → brief → HITL decision  
- [x] Video 5–10 min script: `DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md` (record separately)  

---

### Live interview

- [ ] Open with problem + Shield/Sword priority call  
- [ ] Demo prototype  
- [ ] Show domain register / cascade story  
- [ ] Defend beyond-LLM stack  
- [ ] Own assumptions and false-alarm trust ladder  

---

## 13. Decisions Log (Resolved Conflicts)

| Topic | Decision |
|-------|----------|
| MVP focus | **Shield** (asset protection) |
| Sword | Roadmap only for code |
| Loss math | **~$30M / major event** (10 × $3M) |
| Substation scale (story) | **~500** |
| Backend | **FastAPI** for prototype |
| Frontend | **Streamlit** (+ map) |
| Graph | **NetworkX / lookup**, not GNN in MVP |
| Control | **Suggest + audit**; no real switching |
| Phase timing | W1–6 · Mo2–4 · Mo5–9 |
| Samples `03`/`04` | Tone/structure reference, not copy-paste submission |

---

## 14. One-Page Pitch (Memorize)

**Problem:** SGW can’t see or act coherently when storms hit — fragmented GIS/SCADA/weather → destroyed zero-spare assets and unfair, slow restoration.

**Insight:** Protect the machine first (Shield), then restore the lifeline fairly (Sword). Cascades run through power→water→society.

**Solution:** AEGIS — advisory AI that scores Big Three asset risk, traces domino impact, and briefs executives in plain language.

**Why us / why this design:** Domain-grounded, beyond-LLM (forecast, anomaly, graph, later optimize), HITL-first, mockable in days, scalable to live OT.

**Ask:** Approve Phase-1 MVP to prove situational awareness and CapEx protection before automating anything that touches the grid.

---

## 15. Source Map

| File | Role |
|------|------|
| `01-technical-assessment-brief.md` | Official assignment |
| `02-domain-expert-brainstorm-electrical-stp.md` | Physics & ops reality |
| `03-sample-executive-briefing-aegis.md` | Sample exec tone (**not** submission) |
| `04-sample-prd-aegis.md` | Sample PRD structure (**not** submission) |
| `05`–`08` research-plan-whiteboard-part*.md` | Tutor board digests |
| `DELIVERABLE-1-PRD-AEGIS.md` | **Submission PRD** |
| `DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md` | **Submission exec briefing** |
| `DELIVERABLE-3-VIDEO-DEMO-SCRIPT.md` | **Video narration script** |
| `18-PROTOTYPE-AND-PRD-HANDOVER.md` | Assessor / interview handover |
| **`00-AEGIS-NORTH-STAR.md` (this file)** | **Governing plan** |

---

*North star locked as the thinking log. Submit the plain-language DELIVERABLE-* files and locked README; interview from §§1, 5, 14.*
