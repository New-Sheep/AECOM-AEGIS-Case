# Product Requirements Document (Sample)

**Product:** AEGIS (AI-Enabled Grid & Infrastructure Shield)  
**Author:** AI Solution Engineering Team  
**Client:** Southeastern Grid & Water (SGW)  
**Version:** 1.0-MVP  
**Status:** In Review  

> **Note:** This is a sample / rough example of Deliverable 1 (PRD). Use as a reference for structure and depth — not as the final submission.

---

## 1. Problem Definition & Business Context

### 1.1 Executive Summary

Southeastern Grid & Water (SGW) manages critical power and water assets serving **8+ million residents** across coastal and inland territories subject to extreme weather (hurricanes, flooding, heatwaves, wildfires). Operational data is fragmented across legacy GIS platforms, SCADA telemetry, weather services, work-management software, and field dispatch systems.

During severe weather, this fragmentation creates:

- **Operational Blindness:** Incident commanders lack unified situational awareness, leading to delayed triage and uncoordinated emergency response.
- **Catastrophic Asset Loss:** High-value, long-lead-time assets (such as transmission substations and bulk power transformers with zero spare availability) are destroyed because operators lack predictive warning to de-energize or protect them safely.
- **Human & Economic Inequity:** Unoptimized restoration workflows leave vulnerable communities and critical public lifelines (hospitals, water pumping stations, telecom) offline for extended periods, generating regulatory penalties, skyrocketing insurance premiums, and eroding public trust.

### 1.2 The Core Problem Statement

> How might SGW break operational data silos to predict infrastructure vulnerabilities hours before a storm hits, optimize crew and spare-asset dispatch, and orchestrate equitable, resilient restoration under extreme uncertainty?

---

## 2. Key Assumptions & Unknowns

| Type | Item | Working Assumption | Risk / Impact if Invalid |
|------|------|--------------------|--------------------------|
| Assumption | Telemetry Coverage | SCADA and IoT sensor feeds exist at major substations and pump stations. | AI damage forecasting will require synthetic proxy data for unmonitored assets. |
| Assumption | Spatial Data | GIS network topology (connectivity models) is mapped. | Topological connectivity must be inferred via geospatial proximity models. |
| Assumption | Human-in-the-Loop | AI will act strictly as an advisory system; field dispatch requires human sign-off. | Eliminates liability of autonomous grid switching errors and false-alarm shutdowns. |
| Unknown | Sensor Latency | Cellular/SCADA backhaul during storms may suffer packet loss. | System must support asynchronous offline sync and degraded-state caching. |
| Unknown | Spares Inventory | ERP/CMMS (SAP/Maximo) real-time availability is unknown. | MVP will mock inventory constraints and lead-time matrices. |
| Unknown | Union Work-Rules | Overtime and multi-shift rules governing emergency deployments. | Optimization engine must expose configurable constraint parameters. |

---

## 3. Target Users & Operational Pain Points

| User Persona | Core Responsibilities | Primary Pain Points |
|--------------|----------------------|---------------------|
| **1. Incident Commander (EOC Director)** | Overall storm response, emergency coordination, executive briefings. | 12-hour lag in cross-silo situational awareness; political/regulatory scrutiny on restoration. |
| **2. Grid & Water Operator** | Real-time SCADA monitoring, line switching, load shedding. | False alarms trigger unnecessary shutdowns; lack of proactive pre-trip warnings. |
| **3. Resource Coordinator** | Staging crews, tracking replacement parts, contractor allocation. | Critical transformer spares depleted with no lead-time visibility; blind routing into floods. |
| **4. Public Info Officer (PIO)** | Customer alerts, utility commission (PUC) disclosures. | Inaccurate restoration estimates; perceived inequity in marginalized service zones. |

---

## 4. Functional & Non-Functional Requirements

### 4.1 Functional Requirements (FR)

| ID | Requirement |
|----|-------------|
| **FR-01** Data Ingestion | Ingest and normalize GIS shapefiles, NOAA/ECMWF weather telemetry, SCADA alarm streams, and work-order data via standard REST/streaming endpoints. |
| **FR-02** Predictive Scoring | Predict asset-level failure probabilities (0.0 to 1.0) 6 to 24 hours prior to storm landfall using storm vectoring, asset age, and topological stress. |
| **FR-03** Dependency Graph | Map power-grid dependencies against municipal water pumping stations, hospitals, and emergency services to evaluate cascading failure risks. |
| **FR-04** Restoration Optimizer | Generate ranked staging plans balancing: (1) Life safety / critical uptime, (2) Socio-economic equity (Social Vulnerability Index weighting), and (3) Asset replacement availability. |
| **FR-05** Incident Copilot | Enable natural language interrogation of real-time operational status (e.g., “Show un-energized substations within 5 miles of flood zones impacting dialysis centers”). |
| **FR-06** Alert Generation | Auto-generate PUC compliance reports, executive summaries, and localized public emergency broadcast notifications. |

### 4.2 Non-Functional Requirements (NFR)

| ID | Requirement |
|----|-------------|
| **NFR-01** Latency | Risk scoring inference time ≤ 30 seconds across 10,000+ asset nodes upon receipt of updated weather forecast runs. |
| **NFR-02** Availability | 99.99% system uptime during defined emergency weather declarations, with automated failover. |
| **NFR-03** Security | Full compliance with NERC CIP (critical infrastructure protection) and SOC2 Type II standards. |
| **NFR-04** Explainability | All optimization recommendations and AI risk scores must provide clear, human-readable attribution factors (e.g., SHAP values). |

---

## 5. Proposed AI Capabilities

### AEGIS AI Intelligence Stack

1. **Predictive Damage & Vulnerability Models (Gradient Boosting / GNNs)**  
   Correlates wind gust vectors, precipitation, soil saturation, and surge predictions against asset characteristics (transformer age, elevation, vegetation exposure) to forecast equipment failure probability before impact.

2. **Operational Optimization Engine (Mixed-Integer LP / Heuristics)**  
   Solves the constrained resource allocation problem: assigns limited repair crews and high-value spares to maximize restored capacity, critical lifelines, and social equity while minimizing transit delays through hazard zones.

3. **GenAI Situational Copilot (RAG + Function Calling)**  
   Uses an LLM with domain-specific Retrieval-Augmented Generation (indexed on SGW operating procedures, GIS metadata, and live incident logs) to answer operator questions and produce stakeholder reports in seconds.

---

## 6. High-Level Architecture & Integrations

### Core System Interfaces

| Connector | Role |
|-----------|------|
| **GIS Connector** | Ingests geospatial vector layers representing substations, feed lines, treatment plants, and pump stations (ArcGIS / PostGIS). |
| **SCADA Bridge** | Consumes real-time operational status (voltage spikes, temperature, breaker trips) using read-only gateways (DNP3 / OPC-UA). |
| **Weather Service Connector** | Consumes live meteorological radar, track forecasting, and flood inundation boundaries (NOAA, ECMWF). |
| **Workforce & Inventory API** | Queries available personnel certifications, active work orders, and yard stock for high-value components (SAP/Maximo). |

---

## 7. Data Requirements & Dependencies

| Dataset | Source | Critical Fields | Quality / Risk Factor |
|---------|--------|-----------------|----------------------|
| Asset Inventory & GIS | Enterprise GIS (Esri) | Asset_ID, GeoJSON, Age, Replacement_Cost | Outdated equipment replacement logs |
| Real-time Telemetry | SCADA Historian / MQTT | Bus Voltage, Frequency, Temp, Breaker Status | Intermittent sensor packet loss |
| Meteorological Feeds | NOAA API / GFS | Wind Vector, Surge Depth, Rain Accumulation | Spatial resolution granularity (1–3 km) |
| Critical Dependencies | State Homeland Security | Hospital Beds, Water Intake, Telecom Nodes | Missing facility backup generator data |
| Social Vulnerability | CDC SVI Index | Tract_ID, Poverty Rate, Medical Fragility Index | Updated every 2 yrs; needs interpolation |
| Spares & Workforce | SAP / Maximo DB | Crew_Skill, Spare_Count, Depot_Location | Static snapshots; manual stock updates |

---

## 8. Security, Governance & Human-in-the-Loop

- **Zero Autonomous Grid Control:** AEGIS is strictly a decision-support copilot. The platform cannot trigger automated breaker operations or de-energization without authenticated two-operator confirmation in SCADA.
- **Network Segmentation:** Read-only data replication from SCADA control networks into the cloud-hosted AEGIS analytics plane ensures air-gap readiness.
- **Algorithmic Equity Safeguards:** The restoration optimization engine enforces minimum service allocation constraints across historically disadvantaged census tracts to prevent purely capital-driven recovery patterns.

---

## 9. Success Metrics, MVP Scope & Delivery Priorities

### 9.1 Target Business & Operational Metrics

- ≥ **25%** reduction in Critical Facility Outage Duration (CAIDI) across hospitals and water treatment assets
- ≥ **40%** reduction in High-Value Asset Losses through proactive pre-storm de-energization
- ≤ **5 minutes** from Weather Track Update to Full Operational Briefing Generation
- **Zero** disproportionate recovery discrepancy across vulnerable socio-economic cohorts

### 9.2 Scope Matrix & Delivery Priorities

| Capability / Feature | Phase 1 (MVP) | Phase 2 (Beta) | Phase 3 (Full) |
|----------------------|---------------|----------------|----------------|
| Multi-Layer Geospatial Dashboard (Assets + Weather) | MUST | — | — |
| Predictive Asset Vulnerability Scoring (Mock Model) | MUST | — | — |
| Critical Infrastructure Dependency Overlay | MUST | — | — |
| Priority Restoration Optimization Algorithm | MUST | — | — |
| LLM Incident Copilot for Situational Awareness | MUST | — | — |
| Real-time SCADA Live Telemetry Connector | COULD | MUST | — |
| Computer Vision Satellite / Drone Damage Assessment | WON’T | COULD | MUST |

---

## Mapping to Assignment Brief

Covers all 9 required PRD sections from `01-technical-assessment-brief.md`:

| Required section | Covered in |
|------------------|------------|
| Problem Definition & Business Context | §1 |
| Key Assumptions & Unknowns | §2 |
| Target Users & Pain Points | §3 |
| Functional & Non-Functional Requirements | §4 |
| Proposed AI Capabilities | §5 |
| High-Level Architecture & Integrations | §6 |
| Data Requirements & Dependencies | §7 |
| Security, Governance & Human-in-the-Loop | §8 |
| Success Metrics, MVP Scope & Delivery Priorities | §9 |

---

## Source

Sample PRD text provided for the AECOM AI Solution Engineer case (AEGIS / SGW).
