# 17 — Crisis Strategist Explainability

**Status:** Research + product decisions (implementation deferred except map diversify command)  
**Code home:** AEGIS Command Center (`frontend/`, `backend/api/`)  
**Related:** [`00-AEGIS-NORTH-STAR.md`](00-AEGIS-NORTH-STAR.md) · [`15-DATA-PROVENANCE.md`](15-DATA-PROVENANCE.md) · [`16-OPERATOR-UX-DYNAMIC-SIM.md`](16-OPERATOR-UX-DYNAMIC-SIM.md)

This note covers **transparent, grounded GenAI** for operators and execs: site-level and region-level strategy, **customer impact**, **finance formulas**, multi-turn tool calling, and how that pairs with a **living storm**. Control idempotency, restore, chrome, and alarm HF live in doc **16** — do not duplicate here.

---

## 1. Problem statement

| Gap | Today | Why it hurts the demo |
|-----|--------|------------------------|
| Shallow GenAI | Briefs and Ask AEGIS mostly restate wind/surge/load | Feels like a calculator with adjectives, not a **crisis strategist** |
| No consumers | North star / PRD cite SGW **8M+** residents; APIs ignore customers | Execs ask “who is affected?” and get asset jargon |
| Opaque `$ at risk` | Header sums `replacement_cost` for high-risk / conflict assets only | No VoLL, no outage-hours, no methodology string |
| Thin tools | Keyword-routed assistant tools | Follow-ups and clarifications do not systematically fetch new facts |
| Static map after clear | Conflict queue can go empty and stay empty | Hard to film a living incident; hard to QA all map colors |

**Dev unblock (this pass):** `manage.py diversify_demo_map` spreads Low / Watch / High / Needs attention so every legend color is testable.

---

## 2. Research anchors

### 2.1 Grounded crisis decision support

Patterns from tool-first / evidence-bound assistants (e.g. CrisisLens-style local command briefing; grounded-reasoning “verify before assert”):

- Separate **planning** (which tools to call) from **saying numbers** (only from tool JSON).
- Prefer “I don’t know yet — let me look that up” over fluent hallucination.
- Human remains in control of physical actions (Confirm / HITL).

### 2.2 Customer interruption cost and VoLL

Industry practice (LBNL **ICE Calculator**, customer interruption cost / **VoLL**, Fixed + Flow + Stock damage framing):

- CapEx / asset replacement ≠ customer economic loss.
- Outage cost ≈ *customers affected × duration × value-per-customer-time* (class-dependent in real studies).
- AEGIS demo must expose **illustrative** constants and a `methodology` string so assessors see the math — never claim ICE-certified precision.

### 2.3 Living conditions

Doc 16 scenario clock + tick. This doc adds: diversify as the **starting color mix**; ticks should **re-roll a subset** of sites so the map does not collapse to all-green after one clear cycle.

---

## 3. Two-level crisis strategist

| Mode | Audience question | Grounding |
|------|-------------------|-----------|
| **Site strategist** | “What exactly is going on at this site?” | Site tools only: sensors, weather, risk, conflict, downstream, customers on this node, asset $ |
| **Region strategist** | “How is the territory doing?” | Region tools: threat, phase, attention queue, risk histogram, customer rollups, finance breakdown, lifelines |

Natural language should **interpret** (priorities, trade-offs, who to call next) using only tool-backed facts — not invent conditions.

---

## 4. Read APIs / LLM tools (never invent numbers)

| Tool / API | Returns (demo) |
|------------|----------------|
| `get_site_explain` | sensors, weather, risk, drivers, conflict, operational state, downstream IDs/names, `customers_served`, `replacement_cost` |
| `get_region_situation` | threat level, sim phase, conflict list, risk band histogram, regional customer totals |
| `get_customer_impact` | by site and region; critical (hospital/water) vs residential estimates |
| `get_finance_breakdown` | CapEx at risk; illustrative outage cost; **formula + constants** in `methodology` |
| `get_dependency_impact` | downstream cascade + summed customers downstream |
| `list_attention_sites` | existing conflict queue (keep) |
| `say_unknown` | explicit when no tool covers the question |

### 4.1 Demo constants (transparent, editable)

Publish in API payloads (example — tune later):

| Constant | Example | Label |
|----------|---------|--------|
| `territory_customers` | `8_000_000` | SGW illustrative service population |
| `voll_per_customer_hour_usd` | e.g. `3.50` | Illustrative residential VoLL proxy — **not** ICE survey output |
| `hours_at_risk_heuristic` | from threat / phase | Short illustrative horizon (e.g. 6–24 h) |

Every finance response includes:

```text
methodology: "Illustrative. CapEx_at_risk = sum(replacement_cost) for flagged high-risk/conflict sites.
Illustrative_outage_cost = customers_at_risk * hours_at_risk * voll_per_customer_hour_usd.
Not an ICE Calculator run; not regulatory VoLL."
```

### 4.2 Customer attribution (demo)

Until richer GIS exists:

- Allocate territory customers across assets by type weights (hospitals/water higher criticality; transformers feed more residential meters).
- Persist or compute `customers_served` per asset so site and region tools agree.
- Critical customers (hospital, water plant) called out separately for equity / lifeline narrative.

---

## 5. Grounding and multi-turn rules

1. LLM may **only** cite values present in the latest tool JSON (or prior turn snapshots still in context).
2. If missing → say **I don’t know yet**, call a tool, or ask the user to select a site.
3. **Multi-turn:** `conversation_id` + retained tool snapshots; keep answering follow-ups and clarifications until the operator is satisfied.
4. **Writes** (reduce load / shut down / restore) stay Confirm-only; strategist never silently trips breakers.
5. Fake mode implements the same tools with deterministic prose so demos work without NVIDIA.

---

## 6. Living storm (pointer)

See doc **16** § scenario clock / `tick_scenario` / Live monitoring refresh (15–30s).

Additions for explainability demos:

- After `diversify_demo_map`, the map shows all four legend colors.
- Each tick: nudge weather/telemetry; optionally move a few sites between bands or reflag attention so the queue can refill.
- Region strategist should mention **sim phase / tick** when tools expose them.

---

## 7. Dev: diversify map (shipped this pass)

Map colors ([`frontend/map_panel.py`](../frontend/map_panel.py) `risk_color`):

| Legend | Rule |
|--------|------|
| Needs attention | `conflict_flag` |
| Low | `risk < 0.3` |
| Watch | `0.3 ≤ risk ≤ 0.7` |
| High | `risk > 0.7` |

```powershell
cd c:\Users\ankit\Documents\AECOM-AEGIS-Case
.\.venv\Scripts\python.exe backend\manage.py diversify_demo_map
# optional: --seed 42
```

Requires seeded assets (`seed_aegis`). Re-run anytime to reshuffle demo colors. Does not replace continuous tick (doc 16 / P2).

---

## 8. Phased backlog

| Phase | Work | Status |
|-------|------|--------|
| **Now** | `diversify_demo_map` + this doc | Done |
| **P0** | `customers_served` + finance breakdown APIs + methodology strings in UI KPIs | Done |
| **P1** | Multi-turn tool-calling strategist (fake + NIM); site + region modes | Done |
| **P2** | Auto tick + refresh preserving color diversity (doc 16) | See doc 16 |

---

## 9. Acceptance

- [x] Ask AEGIS answers “who is affected?” with customer counts from tools, not invented millions.
- [x] Ask AEGIS answers “how is $ calculated?” with CapEx vs illustrative outage formula from `get_finance_breakdown`.
- [x] Site and region briefs feel like strategy (priorities, trade-offs), still number-grounded.
- [x] Follow-up questions trigger tools when facts are missing; model admits unknowns.
- [x] Map can show Low, Watch, High, and Needs attention in one frame after diversify (and after ticks).

---

## 10. Decision summary

1. GenAI is a **two-level crisis strategist**, not a number parrot.  
2. **Customers and finance** become first-class tool-backed facts with explicit methodology.  
3. **No invented numbers** — tool call or “I don’t know.”  
4. **Multi-turn** until the human is satisfied; writes stay confirmed.  
5. **Diversify** unlocks demo/QA of all map colors now; living storm remains the follow-on from doc 16.

*End of doc — P0+P1 implemented (`impact_economy`, `/api/v1/explain/*`, grounded Ask AEGIS tools + conversation snapshots).*
