# Implementation Plan — Rebuilding Healysis for Smart Health & Supply Chain Resilience

This implementation plan outlines the architecture, data models, algorithms, security controls, and UI structure to rebuild **Healysis** into a enterprise-grade, audit-secure health supply-chain resilience platform.

---

## Technical Stack & Architecture Decisions

1. **Database:** PostgreSQL (SQLAlchemy 2 + Alembic migrations). Docker PostgreSQL locally.
2. **Authentication & RBAC:** Firebase Authentication verified via `firebase-admin` on FastAPI. Roles: `ADMIN`, `CDMO`, `FACILITY_OFFICER`.
3. **Geographic Distance:** Haversine distance formula for P0 redistribution scoring.
4. **Google AI Integration:** Google GenAI Python SDK (`google-genai`) with Gemini 2.0 Flash. Enforces **Pydantic Structured Outputs** and **Function/Tool Calling**. Operates strictly on retrieved database records (read-only); never directly mutates database state.
5. **Predictive Analytics:** Deterministic, reproducible daily demand forecasting, days-of-cover math, and projected stock-out date calculations.
6. **Storage Migration:** Complete removal of flat CSV files and in-memory Python array state.
7. **UI Architecture:** 7 modular routes in Next.js App Router using Obsidian Command Center aesthetic (`#020617`, `#0f172a`, `#06b6d4`).

---

## 1. Database Schema

The database will be implemented using **SQLAlchemy 2.0** declarative models in PostgreSQL.

```mermaid
erDiagram
    USERS ||--o{ REQUISITIONS : reviews
    FACILITIES ||--o{ INVENTORY : holds
    FACILITIES ||--o{ BEDS : tracks
    FACILITIES ||--o{ PERSONNEL : employs
    FACILITIES ||--o{ CONSUMPTION : logs
    FACILITIES ||--o{ FORECASTS : projects
    FACILITIES ||--o{ ALERTS : triggers
    FACILITIES ||--o{ REQUISITIONS : requests_or_supplies
    INVENTORY ||--o{ CONSUMPTION : records
    INVENTORY ||--o{ FORECASTS : targets
    INVENTORY ||--o{ REQUISITIONS : transfers
    AUDIT_EVENTS ||--o{ USERS : performed_by
```

### Table Definitions

#### `users`
- `id` (UUID, Primary Key)
- `firebase_uid` (String, Unique, Indexed)
- `email` (String, Unique)
- `full_name` (String)
- `role` (Enum: `ADMIN`, `CDMO`, `FACILITY_OFFICER`)
- `facility_id` (UUID, Foreign Key to `facilities.id`, Nullable for CDMO/Admin)
- `created_at` (DateTime)

#### `facilities`
- `id` (UUID, Primary Key)
- `facility_code` (String, Unique, Indexed, e.g. `CHC-OD-KHU-001`)
- `name` (String)
- `facility_type` (Enum: `PHC`, `UPHC`, `CHC`, `DISTRICT_HOSPITAL`)
- `state` (String, e.g. `OD`, `WB`)
- `district` (String, e.g. `Khordha`, `Puri`, `Kolkata`)
- `latitude` (Float)
- `longitude` (Float)
- `created_at` (DateTime)

#### `inventory`
- `id` (UUID, Primary Key)
- `facility_id` (UUID, Foreign Key to `facilities.id`, Indexed)
- `item_code` (String, Indexed, e.g. `MED-ORS-SACHET`, `MED-INSULIN-100IU`)
- `item_name` (String)
- `category` (Enum: `ESSENTIAL_MEDICINE`, `VACCINE`, `MEDICAL_SUPPLY`)
- `current_stock` (Integer)
- `safety_stock` (Integer)
- `reorder_threshold` (Integer)
- `batch_number` (String, Nullable)
- `expiry_date` (Date, Nullable)
- `unit_of_measure` (String, e.g. `sachets`, `vials`, `tablets`)
- `updated_at` (DateTime)

#### `beds`
- `id` (UUID, Primary Key)
- `facility_id` (UUID, Foreign Key to `facilities.id`, Unique)
- `general_capacity` (Integer)
- `general_occupied` (Integer)
- `icu_capacity` (Integer)
- `icu_occupied` (Integer)
- `oxygen_capacity` (Integer)
- `oxygen_occupied` (Integer)
- `isolation_capacity` (Integer)
- `isolation_occupied` (Integer)
- `updated_at` (DateTime)

#### `personnel`
- `id` (UUID, Primary Key)
- `facility_id` (UUID, Foreign Key to `facilities.id`, Unique)
- `doctors_scheduled` (Integer)
- `doctors_present` (Integer)
- `nurses_scheduled` (Integer)
- `nurses_present` (Integer)
- `pharmacists_scheduled` (Integer)
- `pharmacists_present` (Integer)
- `asha_scheduled` (Integer)
- `asha_present` (Integer)
- `updated_at` (DateTime)

#### `consumption_logs`
- `id` (UUID, Primary Key)
- `facility_id` (UUID, Foreign Key to `facilities.id`, Indexed)
- `item_code` (String, Indexed)
- `date` (Date, Indexed)
- `quantity_dispensed` (Integer)
- `patient_footfall` (Integer)
- `encounter_token` (String, Nullable)
- `action_type` (Enum: `DISPENSE`, `RECEIVE`, `SPOILAGE`)
- `created_at` (DateTime)

#### `forecasts`
- `id` (UUID, Primary Key)
- `facility_id` (UUID, Foreign Key to `facilities.id`, Indexed)
- `item_code` (String, Indexed)
- `forecast_date` (Date, Indexed)
- `expected_daily_demand` (Float)
- `days_of_cover` (Float)
- `projected_stockout_date` (Date, Nullable)
- `confidence_score` (Float)
- `calculated_at` (DateTime)

#### `alerts`
- `id` (UUID, Primary Key)
- `alert_code` (String, Unique, e.g. `ALT-2026-0801`)
- `facility_id` (UUID, Foreign Key to `facilities.id`, Indexed)
- `resource_id` (String, Nullable, e.g. `MED-INSULIN-100IU`)
- `severity` (Enum: `LOW`, `WARNING`, `CRITICAL`)
- `alert_type` (Enum: `STOCKOUT_PROJECTED`, `GHOST_DRAWDOWN`, `SPOILAGE_SPIKE`, `BED_PRESSURE`, `STAFFING_DEFICIT`)
- `title` (String)
- `evidence_json` (JSONB)
- `projected_impact_date` (Date, Nullable)
- `status` (Enum: `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`)
- `created_at` (DateTime)

#### `recommendations`
- `id` (UUID, Primary Key)
- `recommendation_code` (String, Unique, e.g. `REC-2026-0091`)
- `donor_facility_id` (UUID, Foreign Key to `facilities.id`)
- `recipient_facility_id` (UUID, Foreign Key to `facilities.id`)
- `item_code` (String)
- `recommended_quantity` (Integer)
- `urgency_level` (Enum: `ROUTINE`, `URGENT`, `CRITICAL`)
- `haversine_distance_km` (Float)
- `expected_days_cover_gained` (Float)
- `confidence_score` (Float)
- `reason` (Text)
- `status` (Enum: `PENDING_HUMAN_APPROVAL`, `APPROVED`, `REJECTED`, `DISPATCHED`)
- `reviewed_by_user_id` (UUID, Foreign Key to `users.id`, Nullable)
- `reviewed_at` (DateTime, Nullable)
- `created_at` (DateTime)

#### `audit_events`
- `id` (UUID, Primary Key)
- `event_id` (String, Unique, Indexed, e.g. `EVT-10001`)
- `timestamp` (DateTime, Indexed)
- `actor_user_id` (UUID, Foreign Key to `users.id`, Nullable)
- `action` (String, e.g. `DISPENSE`, `RECEIVE`, `APPROVE_RECOMMENDATION`, `QUARANTINE_BLOCK`)
- `facility_id` (UUID, Foreign Key to `facilities.id`, Nullable)
- `payload_json` (JSONB)
- `prev_hash` (String, Indexed)
- `current_hash` (String, Indexed)
- `is_tampered` (Boolean, Default False)

---

## 2. Migration Plan

1. **Alembic Initialization:** Configure `alembic` in `backend/alembic/` pointing to `postgresql://healysis_user:healysis_pass@localhost:5432/healysis_db`.
2. **Initial Schema Migration:** Create migration `001_initial_schema.py` creating all 10 tables, indexes, and ENUM types.
3. **Seed Data Migration:** Create `backend/seed_data.py` populating:
   - 10 Health Facilities (Odisha & West Bengal clusters with real GPS coordinates).
   - 15 Essential Medicines & Supplies.
   - 30-day historical consumption & footfall data.
   - Initial bed capacities and personnel rosters.
   - Pre-computed genesis block for `audit_events` (`GENESIS_ROOT_HEALYSIS_000`).

---

## 3. API Route Plan

Organized into clean FastAPI router modules under `backend/app/routers/`:

```
backend/app/
├── routers/
│   ├── auth.py             # User profile & session validation
│   ├── facilities.py       # Facilities list, details & regional aggregates
│   ├── resources.py        # Medicine inventory, beds & personnel
│   ├── forecasts.py        # Demand forecasting & days-of-cover predictions
│   ├── alerts.py           # Early warning alerts & evidence
│   ├── recommendations.py # Cross-district redistribution & human approval
│   ├── advisor.py          # Grounded Gemini Q&A with tool calling
│   └── audit.py            # SHA-256 chain verification & incident dockets
```

### Route Summary & RBAC Matrix

| Router | Method | Endpoint | Allowed Roles | Function / Description |
|---|---|---|---|---|
| **Auth** | `GET` | `/api/v1/auth/me` | `ADMIN`, `CDMO`, `FACILITY_OFFICER` | Validates Firebase token and returns user profile + DB role. |
| **Facilities**| `GET` | `/api/v1/facilities` | All Roles | Lists facilities with optional state/district filters. |
| | `GET` | `/api/v1/facilities/{id}` | All Roles | Returns single facility breakdown (inventory, beds, staff). |
| **Resources** | `GET` | `/api/v1/resources/inventory` | All Roles | Lists inventory across facilities with stockout risk flags. |
| | `POST` | `/api/v1/resources/inventory/log` | `FACILITY_OFFICER`, `ADMIN` | Ingests stock movement (DISPENSE, RECEIVE, SPOILAGE). |
| | `GET` | `/api/v1/resources/beds` | All Roles | Returns bed capacity & occupancy % (General, ICU, O2, Iso). |
| | `GET` | `/api/v1/resources/personnel` | All Roles | Returns personnel attendance & staffing risk metrics. |
| **Forecasts** | `GET` | `/api/v1/forecasts` | All Roles | Returns demand forecasts & projected stockout depletion dates. |
| | `POST`| `/api/v1/forecasts/recalculate`| `CDMO`, `ADMIN` | Triggers deterministic forecast engine recalculation. |
| **Alerts** | `GET` | `/api/v1/alerts` | All Roles | Lists active early warning alerts with evidence JSON. |
| | `POST`| `/api/v1/alerts/{id}/acknowledge`| `CDMO`, `ADMIN` | Acknowledges an active warning alert. |
| **Recommendations**| `GET` | `/api/v1/recommendations` | All Roles | Lists cross-district stock redistribution recommendations. |
| | `POST`| `/api/v1/recommendations/{id}/approve` | `CDMO`, `ADMIN` | **Human Approval:** Approves redistribution & commits dual SHA-256 ledger blocks. |
| | `POST`| `/api/v1/recommendations/{id}/reject` | `CDMO`, `ADMIN` | Rejects a redistribution recommendation. |
| **Advisor** | `POST`| `/api/v1/advisor/query` | All Roles | Grounded Gemini Advisor with backend function/tool calling. |
| **Audit** | `GET` | `/api/v1/audit/ledger` | All Roles | Returns cryptographic event ledger history. |
| | `GET` | `/api/v1/audit/verify` | All Roles | Performs $O(N)$ SHA-256 hash sequence verification. |
| | `POST`| `/api/v1/audit/docket/{evt_id}`| All Roles | Generates Gemini 4-part legal forensic audit docket. |

---

## 4. Authentication Flow & Security Architecture

```mermaid
sequenceDiagram
    participant User as Browser (Next.js)
    participant FB as Firebase Auth
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB

    User->>FB: Authenticate with Email/Password or SS0
    FB-->>User: Return Firebase JWT ID Token
    User->>API: HTTP Request with Header `Authorization: Bearer <ID_TOKEN>`
    API->>FB: Verify Token via `firebase_admin.auth.verify_id_token()`
    FB-->>API: Token Claims (UID, email)
    API->>DB: Query `users` table by `firebase_uid`
    DB-->>API: User Record (id, role, facility_id)
    API->>API: Enforce Role Permissions (RBAC Check)
    API->>DB: Execute Authorized Transaction
    API-->>User: Return HTTP JSON Response
```

- **Token Verification:** FastAPI dependency `get_current_user` extracts Bearer Token and verifies signature/expiration via `firebase_admin.auth.verify_id_token()`.
- **Role Binding:** Database maps `firebase_uid` to explicit domain role (`ADMIN`, `CDMO`, `FACILITY_OFFICER`). Client-side claims are ignored; role is enforced by backend middleware.

---

## 5. Algorithms & Mathematical Specifications

### A. Demand Forecasting Algorithm

Deterministic, reproducible demand forecasting using Exponentially Weighted Moving Average (EWMA) combined with 7-day consumption velocity:

$$\text{Daily Consumption Velocity } (V_d) = \frac{\sum_{i=1}^{7} C_{t-i}}{7}$$

$$\text{EWMA Forecast } (\hat{D}_{t+1}) = \alpha \cdot C_t + (1 - \alpha) \cdot \hat{D}_t \quad (\text{where } \alpha = 0.3)$$

$$\text{Days of Cover } (DoC) = \frac{\text{Current Usable Stock}}{\max(\hat{D}_{t+1}, 0.1)}$$

$$\text{Projected Depletion Date} = \text{Current Date} + \lfloor DoC \rfloor \text{ days}$$

### B. Early Warning Alert Criteria

- **CRITICAL Alert:** Triggered if $DoC < 3.0$ days OR ICU Bed Occupancy $> 90\%$ OR Staff Coverage $< 60\%$.
- **WARNING Alert:** Triggered if $3.0 \le DoC < 7.0$ days OR General Bed Occupancy $> 80\%$ OR Unverified Dispense (Ghost Draw).
- **SAFE:** $DoC \ge 7.0$ days.

### C. Cross-District Redistribution Scoring Formula

Calculates a priority score $S_{d,r}$ for transferring medicine from Donor $d$ to Recipient $r$:

$$\text{Haversine Distance } D_{d,r} = 2 R \cdot \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_d)\cos(\phi_r)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$

$$\text{Need Score } N_r = \max\left(0, \frac{\text{Safety Stock}_r - \text{Current Stock}_r}{\text{Safety Stock}_r}\right)$$

$$\text{Surplus Score } P_d = \max\left(0, \frac{\text{Current Stock}_d - 1.5 \times \text{Safety Stock}_d}{\text{Safety Stock}_d}\right)$$

$$\text{Distance Penalty } W_{dist} = \frac{1}{1 + \frac{D_{d,r}}{50}}$$

$$\text{Final Redistribution Score } S_{d,r} = N_r \times P_d \times W_{dist} \times 100$$

A recommendation is generated only if $S_{d,r} > 25.0$ and Donor stock remains $\ge 120\%$ of safety stock after transfer.

---

## 6. Gemini 2.0 Flash Integration Specification

### Backend Function / Tool Definitions

The Gemini client will be provided with read-only tool functions defined via `google-genai`:

1. `get_facility_status(facility_code: str)`: Fetches current inventory, bed occupancy, and staff presence for a facility.
2. `get_inventory_risk(state: str, category: str)`: Returns list of items running below safety stock in a given region.
3. `get_forecast(facility_code: str, item_code: str)`: Returns expected daily demand, days of cover, and depletion date.
4. `get_stockout_alerts(severity: str)`: Returns active critical or warning alerts with evidence.
5. `find_redistribution_candidates(item_code: str)`: Computes top candidate donor/recipient pairs with Haversine scores.
6. `get_audit_event(event_id: str)`: Fetches SHA-256 block details and tamper verification status.

### Structured Output Pydantic Schemas

Gemini Advisor responses will be validated against strict Pydantic schemas:

```python
class ActionRecommendation(BaseModel):
    action_type: str  # e.g., "TRANSFER_STOCK", "INSPECT_REFRIGERATOR"
    donor_facility: Optional[str]
    recipient_facility: Optional[str]
    item_code: Optional[str]
    suggested_quantity: Optional[int]
    reasoning: str

class GeminiAdvisorResponse(BaseModel):
    summary: str
    risk_level: Literal["SAFE", "WARNING", "CRITICAL"]
    evidence_records: List[str]
    recommended_actions: List[ActionRecommendation]
    requires_human_approval: bool
```

---

## 7. Seven-Route UI Architecture

Built with Next.js 16 App Router using the **Obsidian Command Center** palette (`#020617` background, `#0f172a` surface, `#06b6d4` cyan accents):

```
frontend/src/app/
├── layout.tsx                  # Root layout with Sidebar Shell & Auth Provider
├── (auth)/
│   └── login/page.tsx          # Firebase authentication login page
├── dashboard/page.tsx          # 1. Executive Command Center
├── facilities/page.tsx         # 2. State & Facility Intelligence
├── resources/page.tsx          # 3. Inventory, Beds & Personnel Telemetry
├── forecasts/page.tsx          # 4. Predictive Demand & Stockout Horizon
├── recommendations/page.tsx    # 5. Redistribution Desk & Human Approvals
├── advisor/page.tsx            # 6. Grounded Gemini AI Advisor Terminal
└── audit/page.tsx              # 7. SHA-256 Cryptographic Audit Ledger
```

---

## 8. Test Strategy & Verification Plan

### Automated Test Suites (`pytest` in backend)

1. **Unit Tests (`tests/unit/`):**
   - Test SHA-256 block hash computation and tamper detection.
   - Test Haversine distance formula against known GPS pairs.
   - Test EWMA forecasting math and days-of-cover logic.
   - Test Redistribution scoring formula.
2. **Integration Tests (`tests/integration/`):**
   - Test Firebase token auth dependency.
   - Test RBAC permission checks (confirm `FACILITY_OFFICER` cannot approve recommendations).
   - Test Human Approval workflow: verify approving a recommendation commits dual SHA-256 ledger blocks (`DISPENSE` + `RECEIVE`) to `audit_events`.
   - Test Gemini Tool Calling execution and fallback handling.
3. **Frontend Smoke Tests (`frontend/`):**
   - Verify all 7 routes render correctly with navigation shell.

---

## 9. Deployment Architecture

- **Local Development:** PostgreSQL via Docker Compose (`docker-compose.yml` running Postgres on port 5432). FastAPI running via Uvicorn. Next.js running via `npm run dev`.
- **Target Cloud Deployment:** Google Cloud Run (Containerized FastAPI backend and Next.js frontend). Managed Cloud SQL (PostgreSQL) instance.
