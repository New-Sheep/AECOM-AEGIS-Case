# AEGIS Demo Data Provenance

**Scenario:** Hurricane **Ian** (AL092022, Sep 2022) · West / Southwest Florida coastal corridor  
**GIS / deps build:** `scripts/build_realistic_demo_data.py`  
**Telemetry refresh:** `scripts/refresh_telemetry_realistic.py` (Open-Meteo wind + CO-OPS surge + ETT oil/load proxy)  
**Approach:** Hybrid — real public GIS + **API weather** + **ETT SCADA proxy** (not SGW OT); nearest-lifeline dependencies.

---

## Why hybrid (not full OT)

| Layer | Publicly available? | AEGIS demo choice |
|-------|---------------------|-------------------|
| Plant / hospital / WWTP locations | Yes (EIA, HIFLD-style, EPA) | Real names + lat/lon from curated `data/raw/` |
| Hurricane track / intensity | Yes (NHC / IBTrACS) | Ian waypoints in `data/raw/ian_track.csv` |
| Coastal water levels | Yes (NOAA CO-OPS) | Gauge peaks + IDW blend to assets |
| Historical wind @ lat/lon | Yes (Open-Meteo archive) | Ian window 2022-09-28/29, cached per ~0.1° cell |
| Per-asset SCADA (load, oil_temp) | **No** (utility OT) | **ETT ETTh1 proxy** for power assets; light synthetic for hospitals/WWTP |
| Exact breaker topology | **No** | Nearest 3 power assets → each Hospital/WaterPlant/Pump |

Do **not** claim telemetry is live SGW SCADA. ETT is a public China transformer time-series used as a **labeled proxy** for oil_temp/load distributions only.

---

## Sources (cached under `data/raw/`)

| File | Content | Origin |
|------|---------|--------|
| `eia_plants_swfl.csv` | ~45 FL plants / battery / substation points | EIA Form 860–style public plant inventory (names, coords, MW, fuel/tech); clipped to SW/west-central FL |
| `hospitals_swfl.csv` | SW FL hospitals | HIFLD-style public hospital listings (name, city, beds, lat/lon) |
| `wwtp_swfl.csv` | WWTP / pump stations | EPA FRS–style public wastewater facility listings |
| `ian_track.csv` | Ian best-track waypoints + wind (kt) | Simplified from public NHC / IBTrACS best track |
| `coops_ian_peaks.json` | Tide-gauge peaks during Ian | **NOAA CO-OPS** API `water_level` MSL, stations 8725520 (Fort Myers), 8726724, 8726674 |
| `open_meteo_ian/*.json` | Hourly wind_speed_10m (mph) | **Open-Meteo** Historical Archive, Ian window, one file per ~0.1° grid |
| `ett/ETTh1.csv` | Hourly transformer OT + load channels | [ETT dataset](https://github.com/zhouhaoyi/ETDataset) (Zhou et al.) — **proxy**, not Florida |
| `weather_ian_by_asset.csv` | Per-asset wind/surge + source tags | Built by `build_weather_from_apis.py` |
| `ett_scada_by_asset.csv` | Per-asset oil_temp/load (+ synthetic V) | Built by `map_ett_to_telemetry.py` |

Refresh weather / ETT telemetry (needs network first time; then cache-only):

```powershell
python scripts/refresh_telemetry_realistic.py
python scripts/refresh_telemetry_realistic.py --weather-cache-only
python scripts/build_weather_from_apis.py --refresh-coops
```

---

## Generated outputs

| File | Role |
|------|------|
| `data/assets.csv` | Seeded assets (~50) — GIS; do not overwrite lightly |
| `data/telemetry.csv` | ETT proxy SCADA + Open-Meteo/CO-OPS weather |
| `data/dependencies.csv` | Inferred lifeline edges |
| `data/storm_ian_snapshot.csv` | Track copy for docs/backtest narrative |
| `data/asset_provenance.csv` | Per-asset source tag |
| `data/backtest_storm.csv` | Ian-themed recall / lead-time fixture |

---

## Field classification

| Field | Classification |
|-------|----------------|
| `name`, `lat`, `lon`, `type` (facility class) | **Real / public GIS** (or lightly edited for demo SUB-001) |
| `elevation` | **Estimated** coastal heuristic (west=lower, inland=higher); SUB-001 forced to 5.0 ft for ConflictFlag |
| `replacement_cost` | **Estimated** type bands (not utility book value) |
| `wind_speed` | **Open-Meteo** historical max (Ian window) @ asset lat/lon grid; Ian-track fallback if API/cache miss |
| `surge_level` | **NOAA CO-OPS** gauge peaks × inverse-distance blend × coastal/elev factor |
| `oil_temp`, `load` (Transformer/Battery/Switchgear) | **ETT ETTh1 proxy** (`OT` scaled → [55,105] °C; load channels → [0.2,1.1]; hash→row) |
| `load`, `oil_temp` (Hospital/WaterPlant/Pump) | **Light synthetic** (weather still real) |
| `voltage`, `battery_voltage` | **Synthetic** nominal (ETT has no voltage) |
| Dependency edges | **Inferred** (nearest neighbors) |

---

## Demo guarantees

- **SUB-001** = Fort Myers Beach corridor transformer with wind ≥ 115 mph and surge ≥ 12 ft vs elev 5 ft → Old Guard ConflictFlag after `run_heartbeat` (seed also reinforces weather).
- ≥3 hospitals and ≥2 water/pump facilities in the map.
- Legacy RNG generator remains at `scripts/generate_mock_data.py` (not default).

---

## ML preprocess + retrain gate

Training features (`load`, `oil_temp`, `wind_speed`, `surge_level`) pass through `api/services/preprocess.py`: coerce → median impute → clip to physical ranges. Artifacts: `preprocess.joblib`, `iforest_scaler.joblib`, `train_fingerprint.txt`.

`scripts/train_xgb.py` **skips** refitting when the fingerprint of the cleaned matrix is unchanged (unless `--force`). Inference (heartbeat / LangGraph) always applies the same transform; IF scores use the scaler, XGB does not.

This is separate from LangGraph’s `normalize_node` (payload merge only).

---

## GenAI brief validation

Action briefs are **JSON → Pydantic `ActionBrief` → Markdown**. Deterministic grounding checks (asset_id, risk tolerance, ConflictFlag → deenergize, cited sensors/weather must match facts) run before the brief is served; failures fall back to a FAKE structured brief. Optional LLM-as-judge: `scripts/eval_briefs.py` (use `--live` for NIM).

---

## Rebuild

```powershell
cd c:\Users\ankit\Documents\AECOM-AEGIS-Case
# GIS/deps (only when regenerating asset graph):
.\.venv\Scripts\python.exe scripts\build_realistic_demo_data.py
# Weather + ETT → telemetry.csv (does not auto-train):
.\.venv\Scripts\python.exe scripts\refresh_telemetry_realistic.py
.\.venv\Scripts\python.exe scripts\train_xgb.py   # retrains only if fingerprint changed
.\.venv\Scripts\python.exe backend\manage.py seed_aegis --flush
.\.venv\Scripts\python.exe backend\manage.py run_heartbeat
```

---

## Interview talking points

1. **Shield** needs GIS + weather + SCADA; real utility OT is CIP — we use **ETT as a transparent proxy** for oil_temp/load shapes, not as SGW SCADA.  
2. Open-Meteo + Fort Myers CO-OPS ground wind/surge in the **Ian** event for the ConflictFlag referee.  
3. Lifeline edges are a **NetworkX demo**, not a utility one-line diagram.  
4. Next realism step (roadmap): HIFLD substation layer + EAGLE-I county outages for eval labels — not required for this prototype.
