# SkyGaurd AI
### AI-Powered Automatic Weather Station Monitoring
*A Streamlit prototype for the Smart India Hackathon problem statement:
"AI/ML Based Intelligent Anomaly Detector for Automatic Weather Stations"*

---

## 1. Problem Statement

India's Automatic Weather Station (AWS) network streams temperature, pressure,
humidity, wind, rainfall, solar radiation and battery telemetry continuously.
Sensors silently degrade — spikes, drift, stuck values, impossible readings,
power instability, and communication faults all corrupt the data feeding
downstream forecasting and warning systems. Manual monitoring across
hundreds of stations doesn't scale. SkyGaurd AI automatically detects,
explains, corrects, and triages these faults in real time.

## 2. Why Sensor Anomalies Matter

A single frozen or spiking AWS sensor can silently poison a regional weather
model or trigger a false severe-weather alert. Early, explainable detection
protects both forecast accuracy and public trust — and flags failing
hardware before it fails completely.

## 3. Proposed Solution

An end-to-end pipeline that: detects anomalies with an unsupervised
Isolation Forest plus five supporting statistical/physical detectors,
fuses them into one 0–100 anomaly score, classifies severity and probable
root cause, generates a plain-language explanation, reconstructs the
expected sensor value, tracks sensor health over time, and recommends a
concrete maintenance action — all exposed through a live monitoring
dashboard.

## 4. System Architecture

```
AWS Sensor Data
      ↓
Data Preprocessing (imputation, sorting)
      ↓
Feature Engineering (deltas, rolling stats, baseline deviation)
      ↓
ML Anomaly Detection (Isolation Forest, trained on TRAIN split only)
      ↓
Anomaly Score (fused: ML + statistical + physical + temporal)
      ↓
Confidence + Severity
      ↓
Root Cause Classification
      ↓
Explainable AI (Detection Factors)
      ↓
Sensor Value Correction
      ↓
Sensor Health / Predictive Maintenance
```

## 5. Folder Structure

```
weather_anomaly_detector/
│
├── app.py                      # Streamlit entry point — wiring only, no business logic
├── config.py                   # Every threshold/weight/constant used anywhere
├── requirements.txt
├── README.md
│
├── data/
│   ├── stations.csv             # (optional cache — generated in-memory by default)
│   ├── sensor_data.csv          # (optional cache — generated in-memory by default)
│   └── generated/                # simulator scratch space
│
├── models/
│   ├── anomaly_detector.py      # ML score + 6 supporting detectors + score fusion + detect_anomaly()
│   ├── root_cause.py            # Root cause classification from detector outputs
│   ├── value_correction.py      # Sensor value reconstruction ensemble
│   ├── predictive_maintenance.py# Sensor health decay/recovery + recommendations
│   └── trained/                 # isolation_forest.joblib, preprocessor.joblib, metadata.joblib
│
├── services/
│   ├── data_generator.py        # 20-station AWS network + realistic historical simulator
│   ├── preprocessing.py         # Feature engineering + leak-safe imputation/scaling pipeline
│   ├── training.py              # Chronological split, train_anomaly_model(), evaluate_model()
│   ├── monitoring.py            # Network health aggregation
│   └── simulation.py            # Live simulation engine (framework-agnostic)
│
├── utils/
│   ├── explanations.py          # Dynamic "Detection Factors" / AI explanation log text
│   ├── metrics.py               # Precision/recall/F1/confusion-matrix from real predictions
│   └── helpers.py                # Formatting helpers (units, trend arrows, % change)
│
├── components/
│   ├── sidebar.py                # Dark-navy sidebar: nav, station list, simulation toggle
│   ├── cards.py                  # All dashboard info cards
│   ├── charts.py                 # Plotly chart builders
│   ├── map.py                    # Folium station map
│   ├── styles.py                 # Custom CSS + badge/status color helpers
│   └── injection_panel.py        # "Inject Anomaly" controls + "SIH Demo Mode" button
│
└── pages/
    ├── dashboard.py               # Network Overview (main dashboard)
    ├── analytics.py                # Model performance + live session analytics
    ├── station_details.py          # Per-station sensor detail view
    └── settings.py                  # Sensitivity / feature toggles / simulation settings
```

## 6. Synthetic Data — How It's Generated

Everything runs **fully offline**. `services/data_generator.py` simulates
**20 AWS stations** across major Indian cities (Raipur, Delhi, Mumbai,
Kolkata, Chennai, Bengaluru, Hyderabad, Jaipur, Lucknow, Ahmedabad, Bhopal,
Patna, Guwahati, Bhubaneswar, Chandigarh, Dehradun, Shimla, Kochi, Nagpur,
Indore), each with `station_id, station_name, city, state, latitude,
longitude, status`.

**Historical dataset** (`config.HISTORY_DAYS = 90`, hourly readings ≈43,200
rows total across the network):

Each sensor is generated with realistic temporal structure, not
independent random draws:
- **Temperature** = latitude-based baseline + slow ~monthly seasonal wobble
  + diurnal cycle (peaks mid-afternoon) + small random-walk continuity.
- **Pressure** = station baseline + slow random walk (no sudden jumps).
- **Humidity** = inversely related to temperature, boosted during rain.
- **Rainfall** = sparse exponential bursts; feeds back into humidity.
- **Wind speed** = AR(1)-style autocorrelated walk (never teleports).
- **Solar radiation** = strictly diurnal (zero at night), dimmed by rain.
- **Battery voltage** = charges with solar input, drains overnight.

**Anomaly injection** (`config.ANOMALY_INJECTION_RATE = 4.5%` of rows):
`spike`, `drift`, `stuck` (frozen for several consecutive readings),
`impossible_value`, `multivariate` (temperature/pressure/humidity all
shift together), `communication_error` (value becomes NaN). Every injected
row is tagged with ground truth:

```json
{ "actual_anomaly": 1, "anomaly_type": "temperature_spike" }
```

**`actual_anomaly` and `anomaly_type` are simulator-only evaluation labels.
They are never passed to the model as input features** — verify this in
`services/preprocessing.py::ALL_FEATURE_COLUMNS`, which lists only the raw
sensors + engineered features, and in `services/training.py`, which fits
on `preprocessor.transform(df[ALL_FEATURE_COLUMNS])`.

Because the injection rate is small (~4.5%), the chronological training
window is naturally **predominantly normal** — this is a documented
simulator design choice (see spec section 13/47); no post-hoc filtering of
the training set using ground-truth labels is performed, and — critically —
**no filtering ever touches the 20% test period.**

## 7. Machine Learning Methodology

### Why Isolation Forest
Sensor faults are rare, varied, and unlabeled in production — exactly the
setting Isolation Forest is built for: it isolates anomalies by random
recursive partitioning without needing anomaly labels to train on, handles
mixed-scale numeric features well after scaling, and scores each point by
how few splits it took to isolate (short path = anomalous).

### Features (`services/preprocessing.py`)
Raw: `temperature, pressure, humidity, wind_speed, rainfall,
solar_radiation, battery_voltage`

Engineered (all strictly backward-looking, computed per-station):
`temperature_delta, pressure_delta, humidity_delta, wind_speed_delta,
temperature_rolling_mean/std, pressure_rolling_mean/std,
humidity_rolling_mean/std, temperature_deviation_from_baseline
(expanding mean), humidity_temperature_ratio`

### Why a Chronological 80:20 Split
Weather telemetry is a time series. A random shuffle would let the model
"see the future" during training (a reading 5 minutes after a test point
would leak into the training set), producing unrealistically good offline
metrics that collapse in production. Sorting by timestamp and cutting at
80% simulates genuinely deploying the model and evaluating it only on
data it could not have seen — the last chronological 20%.

```python
df_sorted = df.sort_values("timestamp")
split = int(len(df_sorted) * 0.8)
train_df, test_df = df_sorted.iloc[:split], df_sorted.iloc[split:]
```

### Data Leakage Prevention — checklist implemented
- ✅ No `shuffle=True` / `train_test_split` random split anywhere.
- ✅ `RobustScaler` + `SimpleImputer` are `.fit()` **only** on `train_df`
  (`services/preprocessing.py::fit_preprocessor`).
- ✅ `evaluate_model()` (`services/training.py`) never calls `.fit()` on
  anything — it only `.transform()`s the test set with the already-fitted
  preprocessor and `.predict()`s with the already-fitted model.
- ✅ Rolling/expanding features use only past+current rows
  (`.rolling(window).mean()`, `.expanding().mean()` — never centered).
- ✅ `actual_anomaly` / `anomaly_type` are excluded from
  `ALL_FEATURE_COLUMNS` and never reach `model.fit()`.
- ✅ Isolation Forest hyperparameters are fixed in `config.py`, not tuned
  against test-set performance.

### Model Persistence
`train_anomaly_model()` saves `isolation_forest.joblib`,
`preprocessor.joblib`, and `metadata.joblib` to `models/trained/`. On
startup, `app.py` loads them via `@st.cache_resource` if present; if
missing, it trains automatically. The dataset generator is seeded
(`RANDOM_SEED = 42`), so re-training on a fresh run reproduces the same
data and comparable metrics.

## 8. How Anomaly Detection Works (Inference)

`models/anomaly_detector.py::detect_anomaly()` is the single entry point
(already returns a plain JSON-serializable dict for an easy future FastAPI
wrapper):

1. **ML score** — Isolation Forest's `decision_function()` on the live
   observation's engineered features, squashed to 0–100.
2. **Supporting detectors** run per sensor against that station's recent
   buffer: robust (median/MAD) z-score, rolling-median deviation,
   rate-of-change, physical range validation, stuck-sensor check, missing
   value check.
3. The sensor with the strongest supporting signal is selected as the
   **affected sensor**.
4. **Score fusion** (weights configurable in `config.SCORE_WEIGHTS`,
   default ML 50% / statistical 20% / physical 20% / temporal 10%)
   produces the final 0–100 **anomaly score**.
5. **Confidence** = agreement across the independent detectors (more
   detectors agreeing → higher confidence).
6. **Severity** = score bucketed via `config.SEVERITY_THRESHOLDS`
   (NORMAL/WARNING/HIGH/CRITICAL).

Nothing here is hardcoded — every number is computed from the actual
observation and its station's history at call time.

## 9. How Anomaly Correction Works

`models/value_correction.py::correct_sensor_value()` reconstructs the
expected value as a weighted ensemble of:
- rolling median of the last `ROLLING_WINDOW` readings (45%)
- local temporal interpolation — mean of the last 3 readings (35%)
- station historical baseline — mean of the full buffered history (20%)

Correction confidence is derived from how tightly these three estimates
agree with each other (low spread → high confidence), and the result is
clipped to the sensor's physical range.

## 10. How Predictive Maintenance Works

`models/predictive_maintenance.py` tracks a health score per
(station, sensor), starting at 100%. Each detection reading nudges it:

| Severity | Health change |
|---|---|
| NORMAL | +0.15 (slow recovery) |
| WARNING | −1.5 |
| HIGH | −3.5 |
| CRITICAL | −6.0 |

Health is mapped to a status (`HEALTHY ≥90`, `MONITORING ≥75`,
`DEGRADING ≥50`, `CRITICAL <50`), and `generate_recommendation()` maps the
*actual* classified root cause to a specific action (never one generic
message for every anomaly — see the mapping table in that file).

## 11. Root Cause Classification

`models/root_cause.py::classify_root_cause()` is a decision procedure over
the real detector outputs for the affected sensor — communication faults →
data-quality issue, battery rate-of-change → power instability, several
sensors flagged together (with other stations also unstable) → possible
environmental event vs. (all stable) → multivariate sensor fault, a frozen
value → stuck sensor fault, an out-of-range or high-z-score jump → sensor
spike/fault, a moderate sustained z-score → sensor drift. Nothing is
chosen randomly.

## 12. Evaluation Metrics

`services/training.py::evaluate_model()` computes Accuracy, Precision,
Recall, F1, False Positive Rate, False Negative Rate, and a full confusion
matrix (`utils/metrics.py`) directly from `model.predict()` on the unseen
test set vs. `actual_anomaly`. Per-anomaly-type detection rates are also
reported. All of this is visible on the **Analytics** page, along with an
expandable "Model Information" panel documenting the leakage-prevention
checklist for technical judges.

Because Isolation Forest is unsupervised and several anomaly types
(stuck sensors, silent communication faults) are intentionally *subtle in
magnitude*, its standalone precision/recall are realistically modest —
this is expected and honest, which is exactly why the supporting
detectors (§8) are fused into the score actually shown on the dashboard.

## 13. Technology Stack

Python 3.10+, Streamlit, pandas, numpy, scikit-learn, scipy, Plotly,
Folium + streamlit-folium, joblib. No API keys, no cloud services, no
external weather APIs — everything runs locally.

## 14. Installation

```bash
cd weather_anomaly_detector
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 15. How to Run

```bash
streamlit run app.py
```

First launch generates the historical dataset and trains the model
(a few seconds); both are cached (`@st.cache_data` / `@st.cache_resource`
in-memory, plus `models/trained/*.joblib` on disk) so subsequent reruns
and interactions don't retrain.

## 16. How to Demonstrate to SIH Judges

1. Open the **Dashboard** — 20 AWS stations shown, sidebar mostly green.
2. Select **AWS-001** — show its normal live readings.
3. Click **🚀 SIH Demo Mode**.
4. The injected ~55°C temperature reading passes through the *real*
   pipeline: watch the anomaly score, confidence, and severity populate
   dynamically, the AI Explanation Log generate specific reasons, the
   Sensor Data Correction card reconstruct an expected value, the Root
   Cause card name "Temperature Sensor Spike / Sensor Fault", and the
   Sensor Condition / Health Timeline degrade.
5. Open the **🧪 Anomaly Injection Control Panel** to demonstrate other
   anomaly types (drift, stuck, impossible value, multivariate) on any
   station/sensor combination on demand.
6. Switch to **Analytics** to show the chronological 80:20 split, real
   precision/recall/F1/confusion matrix, and per-anomaly-type detection
   rates — proof the numbers are computed, not staged.
7. Toggle **Live Simulation** in the sidebar to show the network updating
   continuously without any injected anomaly.

Total demo time: ~1–2 minutes.

## 17. Future React / FastAPI Migration

Every ML/business function already returns plain dicts (JSON-serializable)
and has zero Streamlit imports (`models/`, `services/`, `utils/`). The
planned migration:

```
Automatic Weather Stations
      ↓
IoT / MQTT ingestion
      ↓
FastAPI  (wraps train_model(), detect_anomaly(), evaluate_model(),
          classify_root_cause(), correct_sensor_value(),
          calculate_sensor_health(), get_network_health() as endpoints)
      ↓
ML Service (this same models/ + services/ package, unchanged)
      ↓
Database (persist readings + detection results instead of in-memory buffers)
      ↓
React.js Dashboard (replaces components/ + pages/, consumes the same JSON)
```

`services/simulation.py::SimulationState` was deliberately written with no
Streamlit dependency so the same engine can back a FastAPI
polling/WebSocket endpoint without modification.

## 18. Known Prototype Limitations

- The live "buffer" per station holds the most recent 60 readings in
  memory (not persisted to disk) — restarting the app resets live session
  state (the trained model and historical dataset persist/regenerate
  identically via the fixed seed).
- Injecting several different anomalies back-to-back on the *same* station
  without normal readings in between can leave residual influence in that
  station's short rolling window — this is realistic system behavior
  (a real station's rolling statistics would behave the same way) rather
  than a scripted result.
- The interactive map uses Folium's default OpenStreetMap/CartoDB tiles,
  which require internet access to render tile imagery (station markers
  and all detection logic are fully offline; only the map's background
  tiles are fetched from the web).
