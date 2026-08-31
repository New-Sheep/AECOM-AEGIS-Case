# Gap Analysis — AECOM Brief vs Submission Package

**Purpose:** Preserve context from the assessor-style review of AEGIS deliverables against the official case brief.  
**Date:** 2026-08-31  
**Brief source:** `AECOM-AI-Solution Eng Case.pdf` (transcribed in [`01-technical-assessment-brief.md`](01-technical-assessment-brief.md))  
**Reviewed files:** `DELIVERABLE-1-PRD-AEGIS.md`, `DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`, README, handover, related research (`10`, `15`)  
**Prototype:** LOCKED (no feature work implied by this note)

**Status (2026-08-31):** Gap-fill **applied** into `DELIVERABLE-1-PRD-AEGIS.md`, `DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`, handover, README, and video script. Prototype still locked. This file remains the historical checklist.

**Original verdict (pre-fill):** The package hit every **named PRD/exec heading**, but several **themes the PDF calls out in the client story** were only one-liners or honest-but-thin. The biggest gaps were: multi-hazard honesty, insurance/legal/regulatory ROI, emergency-response coordination story, architecture diagrams + “why this AI,” US/UK compliance naming, production data path, and cyber/adversarial misuse.

---

## PDF checklist (every point → status)

### Client story (SGW)

| Brief point | In PRD / exec today | Honest gap |
|-------------|---------------------|------------|
| 8M residents, coastal + inland | Covered | — |
| Hurricanes, flooding, **heatwaves**, **wildfires** | Listed in §1; exec says “same loop later for heat/fire” | Prototype + safety rules + demo narrative are **coastal flood/wind**. Oil temp is **equipment**, not heatwave ambient or wildfire weather. Need an explicit **case-study bias** paragraph. |
| Substations, transmission, water, pumps | Covered | Transmission depth is light in prototype |
| Rising opex, disruptions | Light | Fine |
| **Growing insurance premiums** | One phrase (“insurance pressure / conversation”) | No sketch of premium / liability / self-insurance logic at 8M scale |
| **Regulatory pressure** (climate + emergency prep) | Vague “regulators / fines / brand” | No US (PUC, FERC/NERC, EPA water) or UK (Ofgem, UK GDPR, AI assurance) naming |
| GIS / maintenance / weather / field tools silos | Covered | Field-ops **integration** is thin |
| Proactive risk assessment | Strong (Shield) | — |
| **Coordinate emergency response** | Mentioned; Phase 3 Sword | Under-explained what Phase 1 *does* for EOC coordination vs what is not built |
| Real-time situational awareness | Strong | — |
| Incomplete context → assumptions | Strong (§2) | — |

### Deliverable 1 – 9 required sections

| # | Section | Coverage | Quality for assessors |
|---|---------|----------|------------------------|
| 1 | Problem & business context | Present | Thin on insurance / lawsuits / multi-hazard depth |
| 2 | Assumptions & unknowns | Present | Hazard assumption is there but underplayed vs prototype bias |
| 3 | Users & pain points | Present | Resource coordinator / public liaison = later; OK if labeled |
| 4 | Functional & NFR | Present | Security NFR = HITL only; cyber depth missing |
| 5 | AI capabilities | Present | “What” good; “why this technique” still short |
| 6 | Architecture & integrations | **Weakest D1 section** | ASCII only; no diagrams; GIS/weather/field/maintenance plug-in shallow |
| 7 | Data requirements | Present but thin | Provenance mostly lives in `15-DATA-PROVENANCE.md`, not in submission voice; quality, production transition, scaling under-done |
| 8 | Security, governance, HITL | Present for HITL | Almost no compliance frameworks, cyber stack, adversarial misuse |
| 9 | Metrics, MVP, priorities | Present | OK |

### Deliverable 2 – 5 topics

| Topic | Status |
|-------|--------|
| Strategic value | OK; emergency coordination under-sold |
| Financial / ROI | **Equipment loss only**; insurance / legal / regulatory / opex coordination under-sold for 8M scale |
| Roadmap | OK |
| Governance & compliance | HITL story only; **named compliance landscape missing** |
| Scalability | Hazard/domain/geo listed; **reuse + plug-into existing systems** thin |

### Deliverable 3 / interview cues

| Expectation | Status |
|-------------|--------|
| One core workflow | Strong |
| Architecture, assumptions, limits in README | Partial |
| Beyond-LLM AI | Strong in product; explain “why” more in video/PRD |
| Visuals / architecture diagrams | Research has `10-SYSTEM-DIAGRAMS.md`; **submission PRD/exec don’t carry diagrams** |
| Resilience, preparedness, **emergency response** | Preparedness/Shield strong; ER coordination story weak |
| Adoption / org | Light |

---

## Specific concerns (scored)

### 1. Flood/hurricane bias vs heat/fire

**Correct observation.** Vision says multi-hazard; prototype is Ian-style coastal (surge, wind, elevation, flood overrides). Temperature in the model is mostly **transformer oil / load**, not heatwave ambient or wildfire indices.

**Honest answer to write:**

> We treated coastal flood/wind as the **first case study** because assets, public weather, and cascade-to-water are easiest to demo honestly. Heat and wildfire share the same loop (score → impact → human approve), but need different features (ambient load stress, fire weather, PSPS-style protect). Prototype is **biased to the storm case**; heat/fire are roadmap feature packs, not equal in this build.

### 2. Insurance, regulatory pressure, lawsuits (indirect ROI)

**Thin.** Brief names insurance + regulatory pressure explicitly; package mostly monetizes ~$30M transformer losses.

Worth adding (illustrative, not fake accounting), for ~8M customers:

| Indirect lever | Plain story | Prototype? |
|----------------|-------------|------------|
| Insurance premiums / liability | Documented early protect + audit trail supports **prudence** narratives with insurers/regulators; wildfire/storm markets are tightening | Not modeled |
| Fines / disallowance | Written “who/why prioritized” reduces “arbitrary restore” risk | Partial (audit) |
| Lawsuits / brand | Fairness + lifeline priority (Sword later) | Not built |
| Emergency overtime / handoffs | One common operating picture cuts coordination waste | Partial (map + counts) |

### 3. Coordinating emergency response

**Under-explained.** Phase 1 *does* help: shared map, ranked sites, impact to hospitals/water, brief, decision log for handoffs. Phase 1 *does not*: multi-agency dispatch, crew routing, public alerts, mutual aid (Sword / later).

Say both clearly so it does not look like the brief bullet was ignored.

### 4. Architecture & integrations + why AI

**Gap.** PRD §6 is a text pipeline. Richer material exists in [`10-SYSTEM-DIAGRAMS.md`](10-SYSTEM-DIAGRAMS.md) but is not in submission voice.

Add (briefly):

- Context diagram: GIS / weather / sensors / maintenance / identity → AEGIS API → Command Center; control systems stay outside (read-only mirror).
- Why XGBoost: tabular, explainable drivers, works with sparse PoC features.
- Why Isolation Forest: separate “sensor lying” from weather risk.
- Why NetworkX: explicit “who fails next” without pretending breaker-true GNN data.
- Why GenAI: phrase grounded briefs only; not the risk engine.
- Why not MILP/CV yet: needs inventory/topology/imagery we do not have.

### 5. Compliance US / UK (research snapshot)

Client is **US-based**; AECOM is global, so a short dual landscape is smart. Current docs barely name frameworks.

**United States (primary for SGW)**

- **NERC CIP** (FERC-backed): cyber/physical controls for bulk electric system cyber assets (categorization, access, perimeters, incident response, supply chain, etc.). Design posture: **advisory IT analytics**, **read-only** copies of operational data, **no unsupervised switching**, production CIP certification **out of scope for PoC**.
- **State PUCs**: climate resilience / emergency preparedness / wildfire mitigation prudence and cost recovery (insurance and liability pressure is real in industry). Audit trails help “reasonable action” stories.
- **Water side**: EPA / state drinking-water and emergency response planning expectations; cascade power→water is the domain link.
- **Privacy**: operational telemetry is mostly not consumer GDPR, but customer outage / vulnerable-customer lists later = privacy + equity care.

**United Kingdom (AECOM / reuse story, not SGW law)**

- **UK GDPR + Data Protection Act 2018**: lawful basis, DPIA when personal data + AI; transparency.
- **UK AI assurance** (DSIT-style): principles-based assurance, evidence of claims, existing regulators.
- **Ofgem** ethical AI / energy guidance: accountability, misuse, safety context for CNI-like systems.
- **Equality Act** if fairness scoring touches protected groups / vulnerable customers (Sword).

**Honest prototype gaps to state:** no CIP program evidence, no DPIA, no red-team, no SOC integration, no supply-chain attestations, no production IAM/MFA story beyond a demo token.

### 6. Data requirements → production

§7 exists; still missing a crisp production ladder:

| Topic | Today | Say in PRD |
|-------|-------|------------|
| Sources | Public GIS-style, Open-Meteo/NOAA, ETT proxy | Already partly there; pull honesty from `15` |
| Quality | Estimates, inferred deps, demo diversify | Label confidence / stale flags |
| Join key | Asset ID map | Critical dependency |
| Scale | ~50-site demo | Territory partitions, streaming ingest, model registry |
| Transition | Phase 2 read-only | Adapter pattern, shadow mode, no write to control plane |

### 7. Cybersecurity & adversarial misuse

**Largest missing narrative** relative to critical infrastructure.

Threats worth naming (without attack recipes):

- Compromised accounts approving false shut-downs / restores
- Poisoned or spoofed sensor/weather inputs to drive bad advice
- Prompt injection / tool abuse on Ask if GenAI is live
- Map/API exposure leaking critical-asset locations and vulnerability
- Insider misuse of “recommended protect” as cover

Mitigations as **design intent** (many not implemented): read-only OT mirror, human approval + dual control for high impact, least privilege, audit, model/input validation, network isolation from control systems, no autonomous breaker path. **Prototype limitation:** demo auth token, local SQLite, no hardened perimeter.

### 8. Scalability / reusability / plug-in

Exec §5 is high-level. Missing: **adapter / API contract** to existing GIS, historian/SCADA mirror, CMMS, weather, IdP; multi-tenant region packs; hazard feature packs (storm / heat / fire) reusing the same Command Center.

---

## Priority edits (when revising docs)

1. **PRD §1 + §2 + §9:** Explicit multi-hazard case-study bias (storm first; heat/fire later).
2. **Exec §2:** Indirect costs (insurance, regulatory, lawsuits, coordination) at 8M scale, labeled illustrative.
3. **PRD §3 / strategic value:** Emergency coordination = common picture + ranked decisions + audit; dispatch/Sword later.
4. **PRD §5–§6:** Short “why this AI” + real architecture/integration diagram (mermaid from `10`).
5. **PRD §7:** Data quality, provenance pointer, production transition assumptions.
6. **PRD §8 + Exec §4:** US (NERC CIP, PUC) + UK (UK GDPR, AI assurance, Ofgem) mapping: followed in design vs planned vs missing.
7. **PRD §8 / NFR:** Cyber + adversarial misuse + fullstack/AI limits.
8. **Exec §5:** Plug-in and reuse pattern.

---

## Bottom line for the assessor story

We **did not miss required section titles**. We **did undersell** several **problem-statement themes** the PDF puts in the client overview (insurance, regulation, multi-hazard, emergency coordination) and we **under-specified** architecture, compliance naming, production data, and cyber/adversarial risk—exactly the areas that show “solution engineer who has worked near regulated infrastructure.”

**Next step:** Done (gap-fill rewrite applied). Re-read D1/D2 before interview; prototype stays locked.

---

## Related files

| File | Role |
|------|------|
| [`01-technical-assessment-brief.md`](01-technical-assessment-brief.md) | Official assignment transcription |
| [`DELIVERABLE-1-PRD-AEGIS.md`](DELIVERABLE-1-PRD-AEGIS.md) | Submission PRD |
| [`DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md`](DELIVERABLE-2-EXECUTIVE-BRIEFING-AEGIS.md) | Submission exec briefing |
| [`10-SYSTEM-DIAGRAMS.md`](10-SYSTEM-DIAGRAMS.md) | Architecture diagrams (research; pull into PRD) |
| [`15-DATA-PROVENANCE.md`](15-DATA-PROVENANCE.md) | Data honesty |
| [`18-PROTOTYPE-AND-PRD-HANDOVER.md`](18-PROTOTYPE-AND-PRD-HANDOVER.md) | Assessor handover |
