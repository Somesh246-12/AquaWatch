# AquaWatch: System Architecture

AquaWatch is an intelligent digital water monitoring and leak detection system designed for college campuses, residential facilities, and community infrastructure.

## High-Level Architecture Flow

```
                      ┌──────────────────────────────────────┐
                      │           React Dashboard            │
                      │   (Frontend - Vite, Tailwind CSS,    │
                      │    Recharts, Live Polling & State)   │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │          FastAPI REST API            │
                      │   (/zones, /readings, /alerts,       │
                      │    /summary, /detection, /health)    │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │           Services Layer             │
                      │   - zone_service    - reading_service│
                      │   - alert_service   - summary_service│
                      │   - detection pipeline & evaluator   │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │      Database / Detection Engine     │
                      │   - SQLite Database (SQLAlchemy ORM) │
                      │   - Rule-based, Z-Score, IF Detectors│
                      │   - Ground Truth Anomaly Evaluator   │
                      └──────────────────────────────────────┘
```

---

## Database Architecture & Entity Relationships

The data layer uses SQLite managed through SQLAlchemy ORM with foreign-key constraints enabled via SQLite PRAGMA hooks.

```
       ┌────────────────────────┐
       │         zones          │
       ├────────────────────────┤
       │ id (PK)                │
       │ name (Unique)          │
       │ type                   │
       │ daily_budget_litres    │
       └───────────┬────────────┘
                   │
    ┌──────────────┼──────────────┐
    │ 1:N          │ 1:N          │ 1:N
    ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐
│   readings   │ │    alerts    │ │  injected_anomalies  │
├──────────────┤ ├──────────────┤ ├──────────────────────┤
│ id (PK)      │ │ id (PK)      │ │ id (PK)              │
│ zone_id (FK) │ │ zone_id (FK) │ │ zone_id (FK)         │
│ timestamp    │ │ timestamp    │ │ timestamp            │
│ litres       │ │ alert_type   │ │ anomaly_type         │
└──────────────┘ │ severity     │ └──────────────────────┘
                 │ message      │     (GROUND TRUTH)
                 │ resolved     │
                 └──────────────┘
```

### Table Specifications

1. **`zones`**
   - **Purpose**: Defines monitored functional areas and their daily water budgets in litres.
   - **Key Constraints**: Unique `name`, `daily_budget_litres > 0`.
   - **Default Records**:
     - *Household* (1,500 L/day)
     - *Hostel Block* (5,000 L/day)
     - *Garden* (2,500 L/day)
     - *Kitchen* (2,000 L/day)
     - *Community Tank* (8,000 L/day)

2. **`readings`**
   - **Purpose**: Records time-series water flow measurements per zone.
   - **Key Constraints**: `zone_id` foreign key with cascade delete, `litres >= 0`.
   - **Indexes**: `zone_id`, `timestamp`, composite index `(zone_id, timestamp)` for high-throughput temporal range queries.

3. **`alerts`**
   - **Purpose**: Tracks anomalies and leaks identified by the detection algorithms.
   - **Fields**: `alert_type` (`leak`, `spike`, `abnormal_usage`), `severity` (`low`, `medium`, `high`), `message`, and `resolved` boolean.
   - **Indexes**: `zone_id`, `timestamp`, `resolved`.

4. **`injected_anomalies` (GROUND TRUTH)**
   - **Purpose**: **Strictly Ground Truth** generated exclusively by the simulation pipeline.
   - **Role in Evaluation**: This table must never be queried by detection algorithms during inference. Instead, it serves as the benchmark against which detector predictions are scored to calculate **Precision**, **Recall**, and **F1-score**.
   - **Allowed Types**: `slow_leak`, `burst`, `wastage_day`.

---

## 🔍 Anomaly Detection Engine

The detection layer provides three distinct detection paradigms, each targeting complementary anomaly characteristics:

### 1. Rule-Based Night-Flow Detector
- **Purpose**: Pinpoints continuous, low-volume nighttime leaks (dripping fixtures, underground pipe cracks).
- **Rule Threshold**:
  - Monitors hours **01:00 to 04:00**.
  - Flow threshold: **> 3.0 Litres/hour**.
  - Minimum persistence: **$\ge$ 3 consecutive hours**.
- **Event Aggregation**: Consecutive hours (e.g. 01:00–04:00) are consolidated into a single logical `DetectionResult` with start/end timestamps, average flow, and peak flow.

### 2. Statistical Z-Score Detector
- **Purpose**: Flags sudden, extreme consumption surges and physical pipe bursts.
- **Statistical Formulation**:
  For each reading $x$ in a given zone and hour-of-day $h \in [0, 23]$:
  $$\mu_{z, h} = \text{historical mean consumption}$$
  $$\sigma_{z, h} = \text{historical standard deviation}$$
  $$z = \frac{x - \mu_{z, h}}{\sigma_{z, h}}$$
- **Threshold**: Readings with **$z > 3.0$** are flagged.
- **Robustness**: Safely guards against zero standard deviation ($\sigma = 0$) edge cases. Aggregates multi-hour spikes into unified burst events.

### 3. Machine-Learning Isolation Forest Detector
- **Purpose**: Captures multivariate and temporal behavioral outliers without requiring explicit thresholds.
- **Model**: `sklearn.ensemble.IsolationForest` trained independently per zone.
- **Features Used (5 Features)**:
  1. `hour_of_day`: Diurnal cycle indicator ($0$ to $23$).
  2. `day_of_week`: Weekly cycle indicator ($0$ to $6$).
  3. `litres`: Instantaneous hourly flow volume.
  4. `rolling_3_hour_mean`: Short-term trend moving average.
  5. `rolling_24_hour_mean`: 24-hour daily baseline moving average.
- **Configuration**:
  - `random_state = 42`: Ensures deterministic reproducibility across runs.
  - `contamination = 0.02`: Set to 2%, corresponding to the synthetic anomaly density (~20 anomalous hours out of 1,440 hours per zone).
  - Outlier score derived by inverting the model's `decision_function()`.

---

## 📊 Event-Level Benchmark Evaluation

Detectors produce continuous time-series events rather than isolated point predictions. AquaWatch implements **1-to-1 event-level bipartite matching** against ground truth:

### Evaluation Metrics
$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}$$
$$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
$$\text{F1-Score} = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

- **True Positive (TP)**: A detector event that temporally aligns with an unmapped ground-truth event in the same zone.
- **False Positive (FP)**: A detector event that does not correspond to any ground-truth event (or redundant multiple detections of the same event).
- **False Negative (FN)**: An injected ground-truth event missed by the detector.

---

---

## 🌐 Core REST API & Service Architecture

The AquaWatch REST API provides the interface between the data/detection engines and the dashboard frontend. All routers remain thin, delegating database access and calculations to modular services:

### 1. Layered Architecture
- **Routers (`backend/app/routers/`)**: Validate request query/body parameters, invoke services, handle HTTP status codes (200, 201, 400, 404, 422), and return typed Pydantic responses.
- **Service Modules (`backend/app/services/`)**:
  - `zone_service.py`: Zone listing and single-zone lookup.
  - `reading_service.py`: Querying, hourly/daily aggregations (`func.date`, `func.sum`), pagination, and live reading ingestion.
  - `alert_service.py`: Filtered alert queries, single-alert retrieval, and resolution updates.
  - `summary_service.py`: Dashboard KPIs, today/yesterday 24h comparisons, weekly volumes, top consuming zone identification, and zone budget tracking.
  - `detection/evaluator.py`: Anomaly detection orchestration, persistence, and benchmark scoring.

### 2. Alert Persistence Strategy
Detected events from all three algorithms are mapped to standard project alert types and persisted into the `alerts` database table:
- **Rule-Based Night-Flow Detector** $\to$ `alert_type = "leak"`
- **Statistical Z-Score Detector** $\to$ `alert_type = "spike"`
- **Machine-Learning Isolation Forest** $\to$ `alert_type = "abnormal_usage"`

Each alert record persists:
- `zone_id`: Monitored zone where anomaly occurred.
- `timestamp`: Event start timestamp.
- `alert_type`: Mapped category (`leak`, `spike`, `abnormal_usage`).
- `severity`: Diagnostic severity level (`low`, `medium`, `high`).
- `message`: Human-readable diagnostic description.
- `resolved`: Initialized to `False`.

### 4. Conservation Intelligence Services
The conservation service layer computes actionable conservation insights from live readings and detector outputs:
- **Water-Budget Tracking (`/conservation/budgets`)**:
  Evaluates actual consumption against configured daily zone budgets:
  - Consumed $< 80.0\%$: `normal`
  - $80.0\% \le \text{Consumed} < 100.0\%$: `warning`
  - $\text{Consumed} \ge 100.0\%$: `exceeded`
- **Targeted Recommendations (`/conservation/tips`)**:
  Extracts prioritized, deduplicated recommendations:
  1. Unresolved leak alerts (`leak_repair`, `critical`/`high` priority).
  2. Budget exceeded zones (`budget_exceeded`, `high` priority).
  3. Budget warning zones (`budget_warning`, `medium` priority).
  4. Primary consumer zone (`high_consumption`, `low` priority).
  5. Optimal efficiency tip (`general_tip`, `low` priority) when all zones operate under normal conditions with 0 active alerts.
- **Leak Savings Estimator (`/conservation/savings`)**:
  Calculates volumetric waste and monetary savings projections using configurable tariffs and leak persistence durations:
  $$\text{Daily Wasted Litres} = \text{Leak Flow (L/h)} \times \text{Assumed Leak Hours/day}$$
  $$\text{Monthly Wasted Litres} = \text{Daily Wasted Litres} \times 30$$
  $$\text{Monthly Monetary Savings} = \frac{\text{Monthly Wasted Litres}}{1,000} \times \text{Tariff per 1,000 Litres}$$
  - Unmeasured leaks return explicit `unavailable` status without guessing.
  - Results are explicitly marked as analytical projections, not guaranteed measurements.

### 5. Alert Statistics & Duplicate Prevention Analysis
The pipeline distinguishes three distinct metrics during detection execution:
- `candidate_detections`: Raw anomaly points flagged by the three algorithms (e.g. 52 candidates on 7,200 readings: 4 rule-based, 12 z-score, 36 Isolation Forest).
- `alerts_created`: New distinct alerts written to SQLite.
- `alerts_existing`: Candidate detections skipped due to duplicate suppression.

**Why the counts differed between runs (49 vs 52):**
1. **First Execution**: The database starts with 0 alerts. As the 52 candidate detections are processed, 3 Isolation Forest candidate points occurred within $\le 4$ hours of another candidate in the same zone. Because the first candidate creates an alert, the remaining 3 are suppressed as intra-batch duplicates. Thus, **49 alerts are created** and **3 candidates are skipped as duplicates** ($49 + 3 = 52$).
2. **Second Execution**: The database already contains all 49 unique alerts. When the same 52 candidates are evaluated, all 52 match either existing database records or intra-batch records within the $\pm 4$-hour window. Thus, **0 alerts are created** and **52 candidates are skipped as duplicates** ($0 + 52 = 52$).

---

## ⚠️ Important Limitations

1. **Synthetic Data vs. Real Sensors**: Current data is generated by a deterministic mathematical simulator with diurnal curves and Gaussian noise. Real sensor networks exhibit sensor dropouts, transmission jitter, and non-stationary consumption patterns.
2. **Threshold Sensitivity**: The rule-based threshold ($> 3$ L/h) and z-score threshold ($z > 3$) are calibrated for synthetic campus data and would require recalibration for different municipal or residential installations.
3. **Isolation Forest Contamination Prior**: Unsupervised Isolation Forest requires setting an expected contamination rate. Setting this too high introduces false alarms; setting it too low misses subtle anomalies.
4. **Temporal Tolerance Window**: Event-level matching depends on a temporal window ($\pm 2$ to $\pm 4$ hours). Wider windows increase recall while narrower windows demand tighter timing precision.
5. **Artificially Clean Ground Truth**: Injected anomalies have distinct start/end times and clear additives, making evaluation sharper than typical real-world ambiguous labels.
6. **Projected Savings**: Savings calculated from detected leaks are analytical projections based on assumed daily durations and municipal tariffs, not direct physically measured savings.

---

## Incremental Development Plan
- [x] **Task 1**: Project setup, directory structure, FastAPI backend foundation, SQLite engine, `/health` endpoint, pytest configuration.
- [x] **Task 2**: Complete database model layer (`zones`, `readings`, `alerts`, `injected_anomalies`), Pydantic validation schemas, idempotent database initialization, and comprehensive tests.
- [x] **Task 3**: Deterministic Water Consumption Simulator (60 days, 5 zones, 7,200 readings, diurnal curves, noise, 10 ground-truth injected anomalies: 4 slow leaks, 3 bursts, 3 wastage days, CSV export).
- [x] **Task 4**: Anomaly Detection Engine (Rule-based night flow, Z-Score, Isolation Forest), event-level evaluation against ground truth, and comparative benchmarking (63 passing tests).
- [x] **Task 6 (Completed)**: Conservation Intelligence (Water-budget tracking, data-driven recommendations, leak savings estimator, alert statistics decomposition, 116 passing tests).
- [x] **Task 7 (Completed)**: React + TypeScript + Vite frontend dashboard (Dark-first SaaS UI, centralized API client, Recharts graphs, Alert resolution, Budget progress & date picker, Conservation Intelligence simulator, Detection Engine workbench).
- [x] **Task 8 (Completed)**: Interactive Live Demo & Simulated Leak Injection (Simulated sandbox, 3-second live polling, Rule-Based & Z-Score detection verification, event timeline, alert resolution, safe rollback, 125 passing tests).

