# AquaWatch 💧
**Water Conservation through Digital Monitoring**

AquaWatch is an intelligent digital water monitoring and leak detection system designed for campuses and residential communities. It monitors simulated water consumption across multiple zones, identifies abnormal consumption patterns and leaks using three distinct detection algorithms, and visualizes real-time metrics through a modern interactive dashboard.

---

## 🏗️ System Architecture

```
                    ┌────────────────────────────┐
                    │      Data Simulator        │
                    │ (60 days, 5 zones, seed 42)│
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │      SQLite Database       │
                    │  (zones, readings, alerts) │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │      FastAPI Backend       │
                    │ (Modular REST API/Schemas) │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │      Detection Engine      │
                    │ 1. Rule-based Night Flow   │
                    │ 2. Z-Score (Statistical)   │
                    │ 3. Isolation Forest (ML)   │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │      React Dashboard       │
                    │ (Vite, Tailwind, Recharts) │
                    └────────────────────────────┘
```

---

## 🗄️ Database Architecture (SQLite + SQLAlchemy ORM)

AquaWatch uses SQLite with SQLAlchemy ORM and active foreign-key enforcement (`PRAGMA foreign_keys = ON`).

### Entity Relationship Diagram

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

| Table | Purpose | Constraints & Indexes |
| :--- | :--- | :--- |
| **`zones`** | Stores monitored water areas and daily allowances. | Unique `name`, `daily_budget_litres > 0`. |
| **`readings`** | Hourly water meter consumption readings in litres. | Indexed `zone_id`, `timestamp`, composite `(zone_id, timestamp)`, `litres >= 0`. |
| **`alerts`** | Detected anomalies, leak flags, severity, and status. | Indexed `zone_id`, `timestamp`, `resolved`. Types: `leak`, `spike`, `abnormal_usage`. Severities: `low`, `medium`, `high`. |
| **`injected_anomalies`** | **GROUND TRUTH** anomalies injected by the simulator. | Indexed `zone_id`, `timestamp`. Types: `slow_leak`, `burst`, `wastage_day`. |

> [!IMPORTANT]
> **Ground Truth Table**: `injected_anomalies` represents the ground truth created during synthetic dataset generation. Detection algorithms **never** query this table. It exists solely to compute objective evaluation metrics (**Precision**, **Recall**, and **F1-score**) against algorithm predictions.

---

## 🗂️ Monitored Zones & Default Daily Budgets

AquaWatch initializes with five core zones configured with realistic consumption allowances:

| Zone ID | Zone Name | Type | Configured Daily Budget |
| :---: | :--- | :--- | :---: |
| 1 | **Household** | residential | **1,500 L/day** |
| 2 | **Hostel Block** | residential_bulk | **5,000 L/day** |
| 3 | **Garden** | irrigation | **2,500 L/day** |
| 4 | **Kitchen** | commercial_facility | **2,000 L/day** |
| 5 | **Community Tank** | storage_distribution | **8,000 L/day** |

*Budgets are defined in `app/config.py` and can be adjusted dynamically.*

---

## 📂 Project Structure

```
AquaWatch/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App package initialization
│   │   ├── config.py            # Pydantic Settings & default zone configuration
│   │   ├── database.py          # SQLAlchemy SQLite engine & session management
│   │   ├── main.py              # FastAPI entrypoint, lifespan seeding & CORS
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── zone.py          # Zone entity model
│   │   │   ├── reading.py       # Reading entity model
│   │   │   ├── alert.py         # Alert entity model
│   │   │   └── anomaly.py       # InjectedAnomaly (Ground Truth) model
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── health.py        # GET /health endpoint
│   │   ├── schemas/             # Pydantic validation and serialization models
│   │   │   ├── __init__.py
│   │   │   ├── alert.py
│   │   │   ├── anomaly.py
│   │   │   ├── health.py
│   │   │   ├── reading.py
│   │   │   └── zone.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── init_db.py       # Idempotent database & zone seeding service
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Pytest fixtures & isolated in-memory test DB
│   │   ├── test_config.py       # Configuration tests
│   │   ├── test_database.py     # Engine connection tests
│   │   ├── test_database_models.py # Models, relationships, constraints & seeding tests
│   │   ├── test_health.py       # /health and root route tests
│   │   └── test_schemas.py      # Pydantic input validation tests
│   ├── .env.example             # Example environment configuration
│   ├── init_db.py               # CLI tool to initialize database manually
│   ├── pytest.ini               # Pytest configuration
│   └── requirements.txt         # Backend Python dependencies
├── data/                        # SQLite storage & datasets (aquawatch.db)
├── docs/                        # Project architecture & documentation
│   └── ARCHITECTURE.md
├── frontend/                    # React + Vite dashboard (upcoming tasks)
├── .gitignore                   # Git ignore rules for Python & Node
└── README.md                    # Project documentation & setup instructions
```

---

## 🚀 Quickstart Guide (Backend)

### 1. Prerequisites
- **Python 3.11+** installed (verified compatible with 3.11 and 3.12)
- PowerShell, Command Prompt, or Bash

### 2. Set Up Virtual Environment

From the project root directory:

**Windows (PowerShell):**
```powershell
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv backend\.venv
backend\.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Initialize Database & Seed Default Zones
Initialize the SQLite tables and insert default zones idempotently:

```powershell
backend\.venv\Scripts\python.exe backend\init_db.py
```

### 5. Run the Deterministic Water Consumption Simulator
Generate 60 days of hourly water readings (7,200 total), inject 10 ground-truth anomalies (4 slow leaks, 3 bursts, 3 wastage days), and optionally export to CSV:

```powershell
backend\.venv\Scripts\python.exe backend\simulate.py --days 60 --seed 42 --reset --export-csv
```

### 6. Run the Anomaly Detection & Evaluation Engine
Execute all three detectors (Rule-Based, Z-Score, Isolation Forest) and benchmark their performance against the ground truth:

```powershell
backend\.venv\Scripts\python.exe backend\run_detection.py
```

### 7. Run the Backend API
Start the FastAPI development server with automatic reload (the app also auto-initializes the database on startup):

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```
*(Or if your virtual environment is activated: `uvicorn app.main:app --app-dir backend --reload --port 8000`)*

The server will be available at:
- **API Base:** `http://127.0.0.1:8000`
- **Health Endpoint:** `http://127.0.0.1:8000/health`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`

### 8. Run Backend Tests
Run the complete test suite using `pytest`:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend
```
*(Or if activated: `pytest backend`)*

---

## 🌐 REST API Endpoints & Reference

FastAPI exposes interactive OpenAPI documentation at `/docs` (Swagger UI) and `/redoc`.

### Summary of Endpoints

| Method | Endpoint | Tag | Description | Query / Body Parameters |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Health | Health check & DB connectivity status | None |
| `GET` | `/zones` | Zones | Monitored zones list (ordered by ID asc) | None |
| `GET` | `/zones/{zone_id}` | Zones | Retrieve individual zone by ID | Path: `zone_id` |
| `GET` | `/readings` | Readings | Query time-series or aggregated readings | `zone_id`, `start`, `end`, `aggregation` (`hourly`/`daily`), `limit`, `offset` |
| `GET` | `/readings/{reading_id}` | Readings | Retrieve single reading record | Path: `reading_id` |
| `POST` | `/readings` | Readings | Ingest live sensor reading (201 Created) | JSON: `{zone_id, timestamp, litres}` |
| `GET` | `/summary` | Summary | Dashboard KPI summary & zone budget statuses | None |
| `GET` | `/alerts` | Alerts | Query alerts (ordered newest first) | `zone_id`, `severity`, `resolved`, `alert_type`, `limit`, `offset` |
| `GET` | `/alerts/{alert_id}` | Alerts | Retrieve single alert | Path: `alert_id` |
| `PATCH` | `/alerts/{alert_id}/resolve` | Alerts | Mark alert as resolved (`resolved = True`) | Path: `alert_id` |
| `POST` | `/detection/run` | Detection | Run 3 detectors, persist non-duplicate alerts, return benchmarks | `contamination` (float, default 0.02) |
| `GET` | `/conservation/budgets` | Conservation | Zone water budgets & status (normal/warning/exceeded) | `date` (YYYY-MM-DD, optional) |
| `GET` | `/conservation/tips` | Conservation | Prioritized, data-driven water conservation recommendations | `date` (YYYY-MM-DD, optional) |
| `GET` | `/conservation/savings` | Conservation | Volumetric and financial savings estimates for detected leaks | `tariff_per_kl`, `hours_per_day`, `zone_id` |

### Example API Requests & Responses

#### 1. Retrieve Zones (`GET /zones`)
```bash
curl http://127.0.0.1:8000/zones
```
```json
[
  {
    "id": 1,
    "name": "Household",
    "type": "residential",
    "daily_budget_litres": 1500.0
  },
  {
    "id": 2,
    "name": "Hostel Block",
    "type": "residential_bulk",
    "daily_budget_litres": 5000.0
  }
]
```

#### 2. Query Aggregated Daily Readings (`GET /readings?aggregation=daily&limit=2`)
```bash
curl "http://127.0.0.1:8000/readings?aggregation=daily&limit=2"
```
```json
[
  {
    "date": "2026-08-10",
    "zone_id": 1,
    "zone_name": "Household",
    "litres": 1392.79
  },
  {
    "date": "2026-08-10",
    "zone_id": 2,
    "zone_name": "Hostel Block",
    "litres": 5298.26
  }
]
```

#### 3. Ingest Live Reading (`POST /readings`)
```bash
curl -X POST http://127.0.0.1:8000/readings \
  -H "Content-Type: application/json" \
  -d '{"zone_id": 1, "timestamp": "2026-10-09T08:00:00", "litres": 45.2}'
```
```json
{
  "id": 7201,
  "zone_id": 1,
  "timestamp": "2026-10-09T08:00:00",
  "litres": 45.2
}
```

#### 4. Dashboard Summary KPIs (`GET /summary`)
```bash
curl http://127.0.0.1:8000/summary
```
```json
{
  "today_usage_litres": 19661.92,
  "yesterday_usage_litres": 19560.98,
  "change_percent": 0.52,
  "weekly_usage_litres": 154539.78,
  "top_zone": {
    "id": 5,
    "name": "Community Tank",
    "litres": 8571.31
  },
  "active_alerts": 48,
  "zones": [
    {
      "id": 1,
      "name": "Household",
      "type": "residential",
      "daily_budget_litres": 1500.0,
      "today_usage_litres": 1412.35,
      "budget_used_percent": 94.2
    }
  ]
}
```

#### 5. Execute Detection & Persist Alerts (`POST /detection/run`)
```bash
curl -X POST http://127.0.0.1:8000/detection/run
```
```json
{
  "status": "completed",
  "candidate_detections": 52,
  "alerts_created": 49,
  "alerts_existing": 3,
  "detectors": {
    "rule_based": {"events_detected": 4, "zones_affected": [1, 2, 4], "mapped_alert_type": "leak"},
    "z_score": {"events_detected": 12, "zones_affected": [1, 2, 3, 5], "mapped_alert_type": "spike"},
    "isolation_forest": {"events_detected": 36, "zones_affected": [1, 2, 3, 4, 5], "mapped_alert_type": "abnormal_usage"}
  },
  "evaluation": {
    "rule_based": {"precision": 1.0, "recall": 0.4, "f1_score": 0.5714, "true_positives": 4, "false_positives": 0, "false_negatives": 6},
    "z_score": {"precision": 0.8333, "recall": 1.0, "f1_score": 0.9091, "true_positives": 10, "false_positives": 2, "false_negatives": 0},
    "isolation_forest": {"precision": 0.1667, "recall": 0.6, "f1_score": 0.2609, "true_positives": 6, "false_positives": 30, "false_negatives": 4}
  }
}
```

#### 6. Water Budget Evaluation (`GET /conservation/budgets`)
```bash
curl "http://127.0.0.1:8000/conservation/budgets?date=2026-08-15"
```
```json
{
  "date": "2026-08-15",
  "total_budget_litres": 19000.0,
  "total_actual_litres": 18200.5,
  "total_remaining_litres": 799.5,
  "overall_consumed_percent": 95.79,
  "overall_status": "warning",
  "zones": [
    {
      "zone_id": 1,
      "zone_name": "Household",
      "zone_type": "residential",
      "daily_budget_litres": 1500.0,
      "actual_consumption_litres": 1180.2,
      "remaining_budget_litres": 319.8,
      "consumed_percent": 78.68,
      "is_exceeded": false,
      "status": "normal"
    },
    {
      "zone_id": 2,
      "zone_name": "Hostel Block",
      "zone_type": "residential_bulk",
      "daily_budget_litres": 5000.0,
      "actual_consumption_litres": 5120.4,
      "remaining_budget_litres": -120.4,
      "consumed_percent": 102.41,
      "is_exceeded": true,
      "status": "exceeded"
    }
  ]
}
```

#### 7. Conservation Tips & Recommendations (`GET /conservation/tips`)
```bash
curl http://127.0.0.1:8000/conservation/tips
```
```json
{
  "date": "2026-10-08",
  "total_recommendations": 3,
  "recommendations": [
    {
      "id": "leak-repair-zone-1",
      "category": "leak_repair",
      "title": "Inspect and Repair Active Leak in Household",
      "description": "Active unresolved leak detected in Household (Alert #1). Investigate shut-off valves, pipe fittings, and fixtures immediately to halt water loss.",
      "priority": "critical",
      "zone_id": 1,
      "zone_name": "Household",
      "supporting_data": {"alert_id": 1, "severity": "high"}
    },
    {
      "id": "budget-exceeded-zone-2",
      "category": "budget_exceeded",
      "title": "Budget Exceeded in Hostel Block",
      "description": "Hostel Block has used 103.9% of its daily budget (5194.9 L vs 5000.0 L allowance), exceeding limits by 194.9 L. Implement immediate consumption curtailment.",
      "priority": "high",
      "zone_id": 2,
      "zone_name": "Hostel Block"
    }
  ]
}
```

#### 8. Leak Savings Estimator (`GET /conservation/savings`)
```bash
curl "http://127.0.0.1:8000/conservation/savings?tariff_per_kl=2.50&hours_per_day=24.0"
```
```json
{
  "tariff_per_kl": 2.5,
  "currency": "USD",
  "assumed_hours_per_day": 24.0,
  "total_leaks_evaluated": 4,
  "actionable_leaks_count": 4,
  "total_daily_wasted_litres": 1151.76,
  "total_monthly_wasted_litres": 34552.8,
  "total_monthly_savings": 86.37,
  "leak_estimates": [
    {
      "alert_id": 1,
      "zone_id": 1,
      "zone_name": "Household",
      "leak_flow_lph": 11.43,
      "assumed_hours_per_day": 24.0,
      "daily_wasted_litres": 274.32,
      "monthly_wasted_litres": 8229.6,
      "monthly_savings": 20.57,
      "status": "estimated",
      "message": "Leak flow rate of 11.43 L/h extracted from detector telemetry.",
      "is_estimate": true
    }
  ],
  "disclaimer": "Estimated savings are projections based on assumed daily leak duration and configured tariffs. They are not guaranteed or measured savings."
}
```

#### 9. Resolve Alert (`PATCH /alerts/{alert_id}/resolve`)
```bash
curl -X PATCH http://127.0.0.1:8000/alerts/1/resolve
```
```json
{
  "id": 1,
  "zone_id": 1,
  "timestamp": "2026-08-15T02:00:00",
  "alert_type": "leak",
  "severity": "high",
  "message": "Continuous night flow detected: 4.80 L/h between 01:00 and 04:00.",
  "resolved": true
}
```

---

## 🔍 Anomaly Detection Engine & Benchmark Results

AquaWatch benchmarks three distinct anomaly detection methods against the ground truth (`injected_anomalies`):

| Detection Method | Target Anomaly Category | Key Features / Rule Specification |
| :--- | :--- | :--- |
| **Rule-Based Night Flow** | Continuous Slow Leaks | Hours **01:00 to 04:00**, flow **> 3.0 L/h**, minimum **$\ge$ 3 consecutive hours**. |
| **Statistical Z-Score** | Sudden Bursts & Spikes | Grouped by `(zone_id, hour_of_day)`. Standardized $z = (x - \mu) / \sigma$. Flagged when **$z > 3.0$**. |
| **Isolation Forest (ML)** | General Multivariate Anomalies | `sklearn.ensemble.IsolationForest` (`random_state=42`, `contamination=0.02`). 5 features: `hour_of_day`, `day_of_week`, `litres`, `rolling_3_hour_mean`, `rolling_24_hour_mean`. |

### Actual Evaluator Results on 7,200 Readings (10 Ground-Truth Events):

```
1. Rule-Based Night-Flow Detector
   TP: 4 | FP: 0 | FN: 6 | Precision: 100.0% | Recall: 40.0% | F1: 0.5714
   -> Slow Leaks detected: 4/4 (100.0% Recall) with ZERO false alarms.

2. Statistical Z-Score Detector
   TP: 10 | FP: 2 | FN: 0 | Precision: 83.3% | Recall: 100.0% | F1: 0.9091
   -> Bursts detected: 3/3 (100.0% Recall).

3. Machine-Learning Isolation Forest Detector
   TP: 6 | FP: 30 | FN: 4 | Precision: 16.7% | Recall: 60.0% | F1: 0.2609
   -> Captures bursts (3/3) and wastage days (3/3).
```

> [!NOTE]
> **Limitations Notice**: This evaluation is conducted on synthetic data generated by the deterministic simulator. In real-world physical installations:
> 1. Noise distributions and baseline water consumption may deviate from idealized mathematical models.
> 2. Rule thresholds and statistical cutoff multipliers may require empirical recalibration.
> 3. Unsupervised ML models like Isolation Forest require adaptive tuning of the contamination hyperparameter.

---

## 🗺️ Incremental Development Roadmap

- [x] **Task 1: Initial Project Structure & Backend Foundation**
  - Project directory layout (`backend/`, `data/`, `docs/`, `frontend/`)
  - Virtual environment and requirements setup
  - FastAPI application structure & CORS middleware
  - SQLite database engine and session dependency
  - `GET /health` endpoint & Pydantic response models
  - Pytest test suite setup & validation
- [x] **Task 2: Database Models & Schemas**
  - SQLAlchemy ORM models: `zones`, `readings`, `alerts`, `injected_anomalies`
  - Active foreign key enforcement (`PRAGMA foreign_keys = ON`)
  - Pydantic schemas with strict validation rules
  - Idempotent `init_db()` seeding service and CLI script
  - 21 passing automated tests covering models, constraints, and relationships
- [x] **Task 3: Deterministic Water Consumption Simulator**
  - 60-day hourly synthetic dataset generator with random seed `42` (7,200 readings total)
  - Diurnal curves (morning/evening peaks, near-zero night flow, weekend factor)
  - 10 ground-truth anomalies injected (4 slow leaks, 3 bursts, 3 wastage days)
  - Safe reset and re-simulation mechanics
  - CSV export capability (`data/readings.csv`)
  - 39 automated tests covering simulator statistics and reproducibility
- [x] **Task 4: Anomaly Detection Engine**
  - 1. Rule-based night-flow detector (01:00-04:00, > 3 L/h, $\ge$ 3 consecutive hours)
  - 2. Statistical Z-Score detector ($z > 3.0$ grouped by zone and hour-of-day)
  - 3. Unsupervised Isolation Forest model (5 specified features, `random_state=42`)
  - Event-level 1-to-1 bipartite matching against ground truth
  - Precision, Recall, and F1 score benchmark evaluation per method and anomaly type
  - 63 passing automated unit and integration tests
- [x] **Task 5: REST API Services & Endpoints**
  - Modular routers for `/health`, `/zones`, `/readings`, `/summary`, `/alerts`, `/detection/run`
  - Clean service layer decoupling database queries and business logic
  - Hourly and daily reading aggregation (`aggregation=hourly|daily`)
  - Alert persistence and $\pm 4$-hour duplicate suppression strategy
  - 95 passing automated tests (all 63 regressions + 32 new API tests)
- [x] **Task 6: Conservation Intelligence**
  - Water-budget tracking service and `/conservation/budgets` endpoint (<80% normal, 80-100% warning, >=100% exceeded)
  - Data-driven conservation recommendations and `/conservation/tips` endpoint (leak repair, budget overruns, efficiency tips)
  - Configurable water-savings estimator and `/conservation/savings` endpoint (daily/monthly volumetric waste and monetary savings)
  - Alert count decomposition (`candidate_detections`, `alerts_created`, `alerts_existing`) explaining intra-batch duplicates
  - 116 passing automated tests (all 95 regressions + 21 new conservation tests)
- [x] **Task 7: Premium React Dashboard & Frontend**
  - Modern, dark-first environmental intelligence UI with cyan/aqua/turquoise accents
  - Centralized API client connecting to FastAPI with type-safe schemas
  - 5 feature-rich pages: Overview, Water Zones, Alerts & Anomalies, Conservation Intelligence, and Detection Engine
  - Recharts telemetry area chart & zone comparison bar chart
  - Date-picker driven zone budget tracking and drill-down
  - Alert management with severity indicators, search/filter, detail modals, and resolution workflow
  - Interactive conservation simulator with tariff and leak-duration sensitivity controls
  - Multi-detector benchmark matrix comparison against ground-truth events
- [x] **Task 8: Interactive Live Demo & Simulated Leak Injection**
  - Dedicated Live Demo sandbox interface with live 3-second data polling
  - Safe, backend-controlled simulated leak injection for all 5 zones
  - Algorithmic anomaly detection verification (Rule-Based night-flow and Statistical Z-Score detectors)
  - Clear `[SIMULATED DEMO: ...]` event isolation and duplicate prevention
  - Interactive milestone timeline and real-time telemetry trace Recharts chart
  - One-click operational alert resolution workflow
  - Safe session rollback and cleanup preserving all 7,200 baseline readings and 10 ground-truth anomalies
  - 125 passing automated backend tests (116 regressions + 9 new demo tests)

---

## 💻 Frontend Dashboard (React + TypeScript + Vite)

AquaWatch features a presentation-ready web application built for environmental intelligence and conservation operations.

### ✨ Visual Design & Tech Stack
- **Framework**: React 19 + TypeScript + Vite
- **Design Philosophy**: Climate-tech SaaS dark theme (`#060b17` base, `#00f2fe` / `#4facfe` cyan accents, `#22c55e` emerald success, `#ef4444` alerts)
- **Styling**: Vanilla CSS design tokens with responsive layout, subtle borders, and glassmorphic card overlays
- **Icons**: Lucide React
- **Data Visualizations**: Recharts (`AreaChart`, `BarChart`, custom glassmorphic tooltips)

### 📄 Available Pages & Capabilities

1. **Overview Dashboard (`/`)**
   - Live KPI cards: Today's Consumption, Daily Budget Utilization, Active Alerts, and Potential Monthly Leak Savings.
   - Real-time telemetry area chart with toggleable view (24-Hour Profile vs. 14-Day Trend).
   - Zone-by-zone volumetric consumption bar chart.
   - Live zone budget health list with progress bars and color-coded status pills.
   - Recent unresolved alerts widget with one-click resolution.
   - Conservation recommendations preview.

2. **Water Zones (`/zones`)**
   - Grid cards for all 5 monitored zones: **Household**, **Hostel Block**, **Garden**, **Kitchen**, and **Community Tank**.
   - Consumption metrics, configured daily budgets, and utilization percentages (<80% Normal, 80–100% Warning, $\ge$100% Exceeded).
   - Date picker to inspect historical budget compliance for any recorded day.
   - Interactive zone deep-dive drawer: Click any zone card to inspect its 24-hour hourly flow profile and active alerts.

3. **Alerts & Anomalies (`/alerts`)**
   - Severity counters (High, Medium, Low) and total unresolved counts.
   - Multi-parameter filter bar: Zone, Severity, Resolution Status (Unresolved vs. Resolved), Alert Type (Leak, Spike, Abnormal Usage), and text query search.
   - Interactive alerts table displaying timestamps, detection method, and diagnostic telemetry.
   - **Alert Detail Modal**: Inspect anomaly outlier scores, baseline z-scores, and root-cause summaries.
   - **One-Click Resolve**: Functional `PATCH /alerts/{id}/resolve` interaction that dynamically updates badges and recalculates KPIs.
   - Anomaly detection pipeline trigger button with live progress indicator.

4. **Conservation Intelligence (`/conservation`)**
   - Water budget progress metrics across all zones.
   - Zone-by-zone compliance status table.
   - **Interactive Leak Savings Estimator**: Dynamic controls for water tariff (`$/kL`) and leak runtime (`hours/day`) to project potential financial and resource savings in real time.
   - Per-leak volumetric loss breakdown (Daily Wasted Litres, Monthly Wasted Litres, Estimated Monthly Recovery).
   - Prioritized, actionable water-saving recommendations generated directly by backend heuristics.

5. **Detection Engine Workbench (`/detection`)**
   - Architectural breakdown of all three detection algorithms: Rule-Based Night Flow, Statistical Z-Score, and Isolation Forest ML.
   - **Ground-Truth Benchmark Matrix**: Event-level bipartite matching scores against the 10 ground-truth synthetic events (Precision, Recall, F1-Score).
   - Intra-batch and temporal duplicate suppression mechanics explained.
   - Triggerable detection pipeline with instant benchmark recalculation.

6. **Interactive Live Demo Sandbox (`/demo`)**
   - Dedicated demonstration environment designed for classroom and evaluator presentations.
   - **Simulated Leak Injector**: Choose target zone, flow profile (Continuous Night Leak vs. Sudden Burst), and severity (Low, Medium, High).
   - **Real Detection Verification**: Executes genuine Rule-Based or Z-Score algorithms against injected readings; only dispatches alerts when detection criteria are mathematically fulfilled.
   - **Demonstration Milestone Timeline**: Tracks sequence from baseline initialization through telemetry ingestion, detector trigger, alert dispatch, and operator resolution.
   - **Telemetry Trace Chart**: Dual-series area chart highlighting anomalous consumption points against normal diurnal baselines.
   - **Safe Rollback (`POST /demo/reset`)**: Safely removes all session-injected readings and demo alerts, leaving all 7,200 baseline readings and 10 ground-truth anomalies intact.
   - **Live 3-Second Polling**: Real-time polling with request deduplication and pause controls.

---

### 🚀 Running the Full Stack (Windows PowerShell)

#### Prerequisites
- Python 3.11+ (with virtual environment in `backend/.venv`)
- Node.js 18+ and npm

#### 1. Configure the Frontend Environment
Create or verify `frontend/.env`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```
*(A template is also provided in `frontend/.env.example`)*

#### 2. Start the Backend API
In a PowerShell window:
```powershell
cd c:\Users\somes\OneDrive\Desktop\AquaWatch
.\backend\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --app-dir backend --port 8000 --reload
```
*Backend runs at:* `http://127.0.0.1:8000`  
*Interactive Swagger docs at:* `http://127.0.0.1:8000/docs`

#### 3. Start the React Frontend
In a second PowerShell window:
```powershell
cd c:\Users\somes\OneDrive\Desktop\AquaWatch\frontend
npm install
npm run dev
```
*Frontend opens at:* `http://127.0.0.1:5173`

#### 4. Run Frontend Production Build & Type-Check
```powershell
cd c:\Users\somes\OneDrive\Desktop\AquaWatch\frontend
npm run build
```

#### 5. Run Automated Test Suite (125 Tests)
```powershell
cd c:\Users\somes\OneDrive\Desktop\AquaWatch
.\backend\.venv\Scripts\python.exe -m pytest backend
```

---

## 🌐 Production Cloud Deployment Guide

AquaWatch is prepared for zero-friction cloud deployment using **Render** for the FastAPI backend and **Vercel** for the React + Vite frontend.

```
┌─────────────────────────────────┐       HTTPS REST API       ┌─────────────────────────────────┐
│         Vercel (Frontend)       │ ─────────────────────────> │         Render (Backend)        │
│    https://<app>.vercel.app     │ <───────────────────────── │  https://<service>.onrender.com │
│   React 18 + Vite + Tailwind    │         CORS Allowed       │    FastAPI + SQLite + Uvicorn   │
└─────────────────────────────────┘                            └─────────────────────────────────┘
```

### 1. Backend Deployment (Render Web Service)

#### Option A: One-Click Render Blueprint (Recommended)
AquaWatch includes a pre-configured `render.yaml` at the root of the repository.
1. Push your repository to **GitHub** or **GitLab**.
2. In the Render Dashboard, click **New +** → **Blueprint**.
3. Connect your repository. Render will automatically parse `render.yaml` and configure the service.

#### Option B: Manual Web Service Setup
In the Render Dashboard, click **New +** → **Web Service** and connect your repository:

| Setting Field | Exact Value to Enter | Notes |
| :--- | :--- | :--- |
| **Name** | `aquawatch-backend` | Or any unique name |
| **Region** | `Oregon (US West)` | Or closest to your users |
| **Branch** | `main` | Production branch |
| **Root Directory** | `backend` | **Crucial:** Sets context to backend |
| **Runtime** | `Python` | Python 3.11.9 (pinned via `.python-version`) |
| **Build Command** | `pip install -r requirements.txt` | Installs FastAPI, Pandas, Scikit-learn, etc. |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Uses Render's dynamic `$PORT` |
| **Health Check Path**| `/health` | Validates database connectivity before routing |
| **Plan Type** | `Free` | Ephemeral container |

#### Backend Environment Variables (Render Dashboard → "Environment")

| Variable Name | Value | Purpose |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Enforces exact Python runtime |
| `ENVIRONMENT` | `production` | Production mode |
| `DEBUG` | `false` | Disables debug logs |
| `CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` | Securely permits all Vercel preview & production subdomains |
| `CORS_ORIGINS` | `http://localhost:5173` | Optional comma-separated list of additional origins |

> [!NOTE]
> Once Render finishes deploying, copy your backend service URL (e.g., `https://aquawatch-backend.onrender.com`). You will need this for the Vercel frontend setup.

---

### 2. Frontend Deployment (Vercel)

1. Go to the [Vercel Dashboard](https://vercel.com/dashboard) and click **Add New...** → **Project**.
2. Import your AquaWatch repository.
3. Configure the project settings:

| Setting Field | Exact Value to Enter | Notes |
| :--- | :--- | :--- |
| **Framework Preset** | `Vite` | Auto-detects Vite configuration |
| **Root Directory** | `frontend` | Click "Edit" and choose the `frontend` folder |
| **Build Command** | `npm run build` | Runs `tsc -b && vite build` |
| **Output Directory** | `dist` | Default Vite build output |
| **Install Command** | `npm install` | Installs React, Lucide, Recharts |

#### Frontend Environment Variables (Vercel Project Settings → "Environment Variables")

| Variable Name | Exact Value | Notes |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://<your-render-backend-url>` | **Never `localhost` in production.** Example: `https://aquawatch-backend.onrender.com`. Do not include a trailing slash. |

4. Click **Deploy**. Vercel will build and deploy the React frontend with SPA routing rewrites pre-configured in `frontend/vercel.json`.

---

### 3. Ephemeral SQLite Storage Limitations

> [!WARNING]
> **Ephemeral Storage Notice on Free-Tier Hosting**:
> - Free-tier hosting containers on platforms like Render do not include persistent block storage. When the service idles after 15 minutes of inactivity or restarts during a new deployment, the local container disk is reset.
> - **Self-Healing Baseline Architecture**: AquaWatch handles this gracefully on startup. When the backend initializes via `init_db(auto_seed_data=True)`, it automatically checks whether the database is empty. If so, it creates all four tables, inserts the 5 monitoring zones, regenerates the 60-day baseline dataset (7,200 readings + 10 ground truth events), and executes the detection engine to generate 49 initial alerts.
> - **Live Demo Persistence**: Any simulated leaks injected during the live demo, resolved alerts, or reset operations persist continuously for the duration of the active container session. When the container sleeps or redeploys, it safely restarts back to the pristine baseline.
> - **Production Scale**: For permanent multi-instance persistent data storage, configure `DATABASE_URL` to point to a managed PostgreSQL instance (e.g. Supabase, Neon, or Render PostgreSQL).

---

### 4. Post-Deployment Smoke-Test Checklist

Run these quick checks after deployment to verify end-to-end functionality:

- [ ] **1. Backend Health Check**:
  Navigate to `https://<your-backend>.onrender.com/health` in your browser.
  **Expected response:** `{"status": "ok", "database": "connected"}` (HTTP 200).
- [ ] **2. Swagger Documentation**:
  Navigate to `https://<your-backend>.onrender.com/docs`.
  **Expected response:** Interactive FastAPI Swagger UI loads cleanly.
- [ ] **3. Zones API Endpoint**:
  Navigate to `https://<your-backend>.onrender.com/zones`.
  **Expected response:** Array of 5 monitored zones with daily budgets.
- [ ] **4. Frontend Dashboard Load**:
  Open your deployed Vercel URL `https://<your-app>.vercel.app`.
  **Expected response:**
  - Overview KPI cards load (Total Consumption, Total Cost, Active Alerts, System Status).
  - Daily Consumption chart renders data without loading errors.
  - Browser developer console has **zero CORS errors**.
- [ ] **5. Client-Side Routing**:
  Directly refresh the page while on `https://<your-app>.vercel.app/alerts` and `https://<your-app>.vercel.app/demo`.
  **Expected response:** Page reloads cleanly without 404 Not Found (handled by `vercel.json` rewrites).
- [ ] **6. Live Demo Leak Injection**:
  Navigate to `/demo`.
  - Select zone: **Household**, leak type: **Continuous Night Leak**, severity: **High**.
  - Click **Inject Simulated Leak**.
  - **Expected response:** Status badge changes to **Leak Active**, the telemetry trace chart highlights anomalous values, and an alert is recorded.
- [ ] **7. Alert Resolution**:
  Navigate to `/alerts`.
  - Locate an active alert and click **Resolve**.
  - **Expected response:** Alert badge updates to **Resolved** and active count decrements dynamically.
- [ ] **8. Safe Demo Reset**:
  Return to `/demo` and click **Reset Demo**.
  - **Expected response:** Status returns to **Normal**, session injections are removed, and baseline readings (7,200) remain intact.




