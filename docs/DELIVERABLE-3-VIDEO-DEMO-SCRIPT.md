# Video Demo Script - AEGIS (5-10 minutes)

**Deliverable 3 companion.** Record separately. Prototype is **locked**.  
**Author:** Ankit  
**Golden path:** also in [`../README.md`](../README.md)  
**Goal:** Cover AECOM video bullets: end-to-end workflow, architecture choices, AI capabilities, assumptions, limits, and future.

**Prep before record**

1. Seed + diversify + heartbeat (see README).  
2. API on `:8000`, Command Center on `:8501` (`?coach=done`).  
3. Keep offline language mode on for reliable narration. Mention a live language service as optional.  
4. Practice once without camera.

**Target runtime:** about 7-8 minutes (OK band 5-10).

---

## 0:00-1:00 - How we got here (~60s)

**On screen:** Title slide or Command Center header only.

**Say:**

> The assignment left client details incomplete on purpose. We worked in four steps.  
>  
> First, brainstorm: we named the gaps and spoke with a domain expert about floods, heat, substations, and water plants.  
> Second, research: map systems, sensor feeds, weather, and field tools do not connect. Power loss cascades into water and hospitals.  
> Third, planning: protect first, restore fairly later. One operator workflow for a first release.  
> Fourth, implementation: this Command Center. Sample data. A person must approve every protect action.  
>  
> Shield means protect critical equipment before it is destroyed. Sword means restore power and water fairly after the storm. Sword is on the roadmap. It is not in this prototype.

---

## 1:00-1:45 - Problem in one breath (~45s)

**On screen:** Same header or map at a glance.

**Say:**

> SGW serves more than eight million residents. The brief covers hurricanes, floods, heatwaves, and wildfires. Leaders cannot see which sites are about to fail, what fails next, or what action is justified. That blindness destroys hard-to-replace equipment, raises insurance and regulatory pressure, and slows fair recovery. AEGIS is advisory decision support. It does not run the grid by itself.  
>  
> Honest bias: this demo is a coastal flood and wind case study. Heat and fire reuse the same loop later. Phase 1 coordinates emergency attention with one map and an audit trail. It is not full crew dispatch.

---

## 1:45-3:00 - Architecture and beyond chatbots (~75s)

**On screen:** Optional simple architecture from the handover, or stay on the UI Advanced strip showing the API URL.

**Say:**

> The stack is a Django REST API as the source of truth, a Streamlit Command Center, a tree model for tabular risk with readable drivers, a separate check for odd sensor readings, a simple dependency graph for who fails next, and a language model only to phrase grounded briefs.  
>  
> We did not put a deep network model in the first release. We lack true breaker topology, and we need drivers people can read. The language model is not the risk engine. Control is never automatic: reason plus authorization, then an audit log.  
>  
> Demo data is honest hybrid: public Southwest Florida-style maps, Open-Meteo and NOAA gauges for Ian-era weather feel, and a public transformer time series as a sensor proxy. Not live SGW control-room feeds.

---

## 3:00-7:00 - Live end-to-end workflow (~3-4 min)

**On screen:** Command Center. Narrate while clicking.

| Time | Click / show | Say |
|------|--------------|-----|
| +0:00 | Header chips | Active emergency; high-risk and decision-needed counts. One pane for the incident commander. |
| +0:20 | Find site → Show **High risk** | Filter to sites that need attention. |
| +0:40 | Open **Blue Heron Solar** or top high-risk site | Map and Summary update. |
| +1:00 | Summary tabs | What is happening, why it matters, suggested next step, cost trade-off. Plain English. |
| +1:30 | Why this score / Readings | Beyond chat: model drivers and a sensor story. |
| +2:00 | Reduce load or Shut down + reason + `AEGIS-EXEC-DEMO` | Human approval. The demo simulates protection. We are not tripping a real grid. |
| +2:40 | Ask AEGIS → **Site priority list** | Helper over tools: High → Decision needed → Watch. |
| +3:20 | Open jump to **City of Sarasota WWTP** (or similar) | Same workflow, different site. Water and power cascade story. |

**If time:** quick `tampa` search → click match → Clear.

**Avoid:** long Advanced toggles, deep framework digressions, fixing the UI mid-take.

---

## 7:00-8:30 - Limits, Sword, close (~60-90s)

**On screen:** Map or Ask panel idle.

**Say:**

> Limits: sample sensor patterns, inferred dependencies, demo UI chrome, storm-first case study, no production security stamp for critical infrastructure. Design posture is advisory analytics on a read-only mirror with human approval. That is intentional for a weeks-scale proof of concept.  
>  
> Next: Phase 2 shadow advice on live read-only feeds and heat/fire feature design. Phase 3 Sword: crew and spare plans that put hospitals, water, and vulnerable communities first, with a written fairness story.  
>  
> Ask for leadership: approve Phase 1 situational awareness, then a sponsored pilot. Predict, protect, then restore fairly.

**End screen:** Repo URL + “Questions welcome in the live session.”

---

## Checklist vs AECOM video requirements

| Requirement | Covered in |
|-------------|------------|
| Working solution end-to-end | Live workflow section |
| One user workflow walkthrough | Shield loop above |
| Key technical decisions / architecture | Architecture section |
| AI capabilities highlighted | Risk model, sensor check, impact graph, grounded language, human approval |
| Assumptions, limits, future | Limits + Sword |

---

## Do not say

- “This is live SGW control-room data.”  
- “The AI trips breakers by itself.”  
- “Sword is fully implemented in the demo.”  
- “We fully cover heatwaves and wildfires in this build.”  
- “This prototype is CIP certified / production secure.”
