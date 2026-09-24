# Healysis — Final Authoritative Technology Stack & Verification Matrix

> **Source of Truth Document**  
> **Status:** FINAL AUDIT COMPLETE  
> **Date:** September 2026  
> **Project:** Healysis — Autonomous Healthcare Resource Sentry & Redistribution Network  

---

## 1. Google Technologies ACTUALLY USED

| Google Technology | Implementation Status | Executable Evidence in Repository | Runtime Role & Architecture |
|---|---|---|---|
| **Google GenAI SDK (`google-genai`)** | **IMPLEMENTED** | `backend/requirements.txt`, `backend/app/advisor_service.py` | Official Google GenAI SDK used to initialize Gemini client (`Client(api_key=...)`) with deterministic tool grounding. |
| **Gemini 2.5 Flash (`gemini-2.5-flash`)** | **IMPLEMENTED** | `backend/app/advisor_service.py`, `backend/app/config.py` | Core LLM reasoning engine for conversational operational intelligence, natural language intake, and risk assessment. |
| **Gemini Multimodal / Vision** | **IMPLEMENTED** | `backend/app/advisor_service.py` (`analyze_inventory_image`), `backend/app/routers/advisor.py` (`/analyze-image`), `frontend/src/app/advisor/page.tsx` | Frontline medicine packaging and delivery challan image inspection. Extracts SKU, quantity, batch, and expiry with NLEM cross-verification. |
| **Firebase Admin SDK (`firebase-admin`)** | **IMPLEMENTED** | `backend/requirements.txt`, `backend/app/security.py`, `backend/app/config.py` | Production token verification bridge (`auth.verify_id_token`). Validates Firebase Auth JWTs on all protected endpoints. |
| **BigQuery (Data Architecture & Export)** | **IMPLEMENTED** | `backend/app/routers/network_intelligence.py` (`/bigquery-schema`, `/bigquery-export`) | Authoritative BigQuery TableSchema definitions and streaming JSON export endpoints for `facilities_spatial_telemetry`, `inventory_burn_rate_snapshots`, and `cryptographic_audit_ledger`. |
| **Google Maps Platform (GIS & Routing)** | **IMPLEMENTED** | `frontend/src/components/GoogleMapsRouteViewer.tsx`, `frontend/src/app/recommendations/page.tsx`, `backend/app/algorithms.py` | Facility geospatial coordinate mapping, route corridor visualization, Haversine logistics calculation with road detour factor, and Google Maps JS API script integration. |
| **Google AI Studio** | **DEVELOPMENT ONLY** | Development environment | Model prototyping, parameter tuning (temperature=0.1), and prompt structure verification. Not claimed as runtime package. |

---

## 2. Non-Google Technologies ACTUALLY USED

| Technology | Layer | Version / Package | Concrete Evidence |
|---|---|---|---|
| **Next.js** | Frontend Framework | Next.js 16.3.2 (App Router, Turbopack) | `frontend/package.json`, `frontend/src/app/` |
| **React** | UI Library | React 19.2.3 | `frontend/package.json` |
| **TypeScript** | Static Typing | TypeScript 5.8.3 | `frontend/tsconfig.json` (0 compiler errors) |
| **Tailwind CSS** | Styling System | Tailwind v4 (`@tailwindcss/postcss`) | `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx` |
| **Tabler Icons** | UI Iconography | `@tabler/icons-react` 3.36.1 | `frontend/src/components/`, `frontend/src/app/` |
| **FastAPI** | Backend Framework | FastAPI 0.135.3 | `backend/main.py`, `backend/app/routers/` |
| **Python** | Backend Language | Python 3.14 / 3.12+ | `backend/app/` |
| **Uvicorn** | ASGI Web Server | Uvicorn 0.43.0 | `backend/requirements.txt`, systemd/supervisord |
| **SQLAlchemy** | Database ORM | SQLAlchemy 2.0.48 | `backend/app/models.py`, `backend/app/database.py` |
| **SQLite (Dev) / PostgreSQL (Prod)** | Relational DB | SQLite 3 via SQLAlchemy engine | `backend/app/database.py`, `backend/healysis.db` |
| **Pydantic** | Schema Validation | Pydantic v2.12.5 | `backend/app/schemas.py` |
| **Pytest** | Test Framework | Pytest 9.1.1 + AnyIO | `backend/tests/` (367 passing automated tests) |
| **Web Speech API** | Voice Input / Output | Browser Native (`webkitSpeechRecognition`, `speechSynthesis`) | `frontend/src/app/advisor/page.tsx` |
| **PyJWT & Passlib** | Local JWT & Hashing | `pyjwt` 2.11.0, `passlib[bcrypt]` 1.7.4 | `backend/app/security.py` |

---

## 3. AI Architecture & Grounding Strategy

```
                          ┌──────────────────────────────────────┐
                          │     Frontline Health Worker / CDMO   │
                          └──────────────────┬───────────────────┘
                                             │ User Prompt / Voice / Image
                                             ▼
                          ┌──────────────────────────────────────┐
                          │   Healysis AI Advisor API Gateway    │
                          │   (RBAC + Facility Scope Enforced)   │
                          └──────────────────┬───────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
         ┌───────────────────────────┐               ┌───────────────────────────┐
         │ Structured DB Retrieval   │               │ Gemini Multimodal Vision  │
         │ - Facility Stock Levels   │               │ - Image File Header Check │
         │ - Forecast Days of Cover  │               │ - Medicine Packaging OCR  │
         │ - Pending Alerts          │               │ - NLEM 2022 Matcher       │
         │ - Network Redistribution  │               │ - 5MB Strict Size Filter  │
         └─────────────┬─────────────┘               └─────────────┬─────────────┘
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             │ Grounded Prompt Context
                                             ▼
                          ┌──────────────────────────────────────┐
                          │  Google GenAI SDK (Gemini 2.5 Flash) │
                          │  Temperature = 0.1 (Strict Grounded) │
                          └──────────────────┬───────────────────┘
                                             │
                                             ▼
                          ┌──────────────────────────────────────┐
                          │ Security Guardrail & Injection Filter│
                          │ - Rejects System Prompt Extraction   │
                          │ - Blocks Secret / Key Exfiltration   │
                          │ - Neutralizes SQL / Instruction Bias │
                          └──────────────────┬───────────────────┘
                                             │
                                             ▼
                          ┌──────────────────────────────────────┐
                          │ Advisory Result + Human Confirmation │
                          │  (ZERO autonomous DB write mutation) │
                          └──────────────────────────────────────┘
```

---

## 4. Backend Architecture

- **Modular Routers:**
  - `auth.py`: Token verification, role identification, local demo exchange.
  - `facilities.py`: Facility discovery, ward bed occupancy, personnel attendance.
  - `inventory.py`: Facility-isolated stock queries, SKU catalogs.
  - `forecasts.py`: 7-day demand forecasting, stockout countdowns.
  - `alerts.py`: Early warning engine, acknowledgment & escalation lifecycle.
  - `recommendations.py`: Deterministic inter-facility transfer recommendations, What-If simulation.
  - `network_intelligence.py`: Network-wide aggregated dashboards, BigQuery schema & telemetry exports.
  - `audit.py`: Cryptographic SHA-256 audit ledger inspection.
  - `advisor.py`: AI Advisor chat, multimodal vision analysis, stock confirmation.
  - `voice.py`: Speech token and configuration verification.

---

## 5. Frontend Architecture

- **App Router (`src/app/`):** 14 fully statically pre-rendered & dynamic routes:
  - `/` (Redirect to Dashboard)
  - `/login` (Role-based authentication & session selector)
  - `/dashboard` (Executive KPI overview, critical alerts, stockout horizons)
  - `/facilities` & `/facilities/[id]` (Facility directory and unit details)
  - `/resources` (Inventory management and NLEM essential medicines)
  - `/forecasts` (Demand prediction curves and burn-rate calculations)
  - `/alerts` (Alert notification, acknowledgement, escalation)
  - `/recommendations` (Inter-facility resource redistribution, What-If simulator, Geospatial Route Viewer)
  - `/network` (Network-wide intelligence, district rollups, BigQuery export)
  - `/audit` (Cryptographically verified SHA-256 event ledger)
  - `/advisor` (Grounded Gemini Advisor, Voice STT/TTS, Multimodal camera inspection)

---

## 6. Database & Relational Foundation

- **Relational Integrity:** Foreign keys across State &rarr; District &rarr; Facility &rarr; Inventory / Forecast / Alerts.
- **Unique Constraints:** `uix_facility_medicine_batch` prevents duplicate inventory records.
- **Cryptographic Audit Log:** Every approved transfer or verified frontline stock update generates an immutable `AuditEvent` with `previous_hash` and `current_hash` (SHA-256 hash chaining).

---

## 7. Authentication

- **Dual-Mode Production Architecture:**
  1. **Firebase Admin SDK:** Validates Google Firebase ID tokens via official Google cryptographic public keys.
  2. **Local Cryptographic HS256 JWT Fallback:** Fully operational for offline demonstration, emergency disconnected clinic scenarios, and automated CI/CD test runners.

---

## 8. Role-Based Access Control (RBAC)

| Role | Scope | Permitted Actions | Restricted Actions |
|---|---|---|---|
| **ADMIN** | System-Wide | All network operations, user management, audit review, BigQuery export. | None. |
| **CDMO** | District / Network | Network intelligence, approve/reject redistribution, alert escalation, BigQuery telemetry. | Restricted from mutating unassigned facility stock without audit. |
| **FACILITY_OFFICER** | Single Facility | View own facility stock, draft frontline telemetry updates, acknowledge facility alerts. | **FORBIDDEN** from viewing other facilities, viewing network telemetry, approving transfers, exporting BigQuery data. |

---

## 9. Predictive Modeling & Demand Forecasting

- **Implementation:** Deterministic hybrid statistical engine combining:
  - Empirical baseline consumption logs (7-day and 30-day moving averages).
  - Bed occupancy weighting factor (General beds, ICU, Oxygen beds).
  - Outbreak seasonal surge multipliers (monsoon diarrheal surge for ORS, vector-borne for antimalarials).
- **Safety Stock Threshold:** Dynamically calculated based on replenishment lead times (default: 30-40 units / 5 days).
- **Vertex AI Evaluation:** Vertex AI was evaluated for custom AutoML time-series forecasting. Because deterministic local execution guarantees offline resilience in remote rural PHCs and 100% demo uptime without cloud bill dependencies, local deterministic forecasting was retained as primary and Vertex AI is documented as evaluated rather than claimed as runtime dependency.

---

## 10. Voice & Multilingual Integration

- **Languages Supported:**
  - English (`en-IN`)
  - Hindi (`hi-IN` — हिंदी)
  - Hinglish (Conversational mixed healthcare phrasing: *"Aaj ORS ka stock 180 hai"*)
- **Speech-to-Text (STT):** Browser-native Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) with zero credential overhead, instant frontline dictation, and real-time interim drafts.
- **Text-to-Speech (TTS):** Browser-native Speech Synthesis (`speechSynthesisUtterance`) with automatic Devanagari script detection and accent matching.
- **Gemini Multilingual Grounding:** Prompts instruct Gemini 2.5 Flash to understand mixed Hindi-English medical terms and reply fluently in the user's preferred language.

---

## 11. Geospatial & Google Maps Integration

- **Odisha Public Health Coordinates:** Real GPS coordinates for verified health facilities across Khordha, Puri, Cuttack, and Ganjam districts.
- **Google Maps Platform Integration:** `<GoogleMapsRouteViewer>` loads the official Google Maps JavaScript API when `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` is present, rendering native interactive maps with markers and route polylines.
- **Resilient Fallback Mode:** When running offline or without external credentials, an interactive SVG GIS vector map visualizes the exact coordinates, donor &rarr; recipient trajectory, Haversine logistics distance, and cold-chain turnaround parameters.

---

## 12. Multimodal Vision Integration

- **Engine:** Gemini 2.5 Flash Multimodal via Google GenAI SDK.
- **Endpoint:** `POST /api/v1/advisor/analyze-image`
- **Security Guardrails:**
  - 5MB maximum file size limit.
  - Image MIME validation (`image/jpeg`, `image/png`, `image/webp`).
  - Binary header magic byte inspection (rejects disguised executables/scripts).
  - Base64 payload sanitization.
  - Advisory disclaimer enforced: requires human physical verification before inventory update.

---

## 13. Data Sources

- **National Health Mission (NHM) Odisha:** District and facility classifications (DHH, SDH, CHC, PHC).
- **National List of Essential Medicines (NLEM 2022):** Standardized drug codes, categories, units, and safety buffers.
- **Realistic Seeded Telemetry:** Calibrated historical consumption logs and burn-rate curves for Khordha and Puri health facilities.

---

## 14. Deployment Architecture

- **Frontend:** Next.js deployed on Vercel or Cloud Run (Node.js 20+ runtime).
- **Backend:** FastAPI ASGI server run with Uvicorn, ready for Google Cloud Run containerized deployment via `Dockerfile`.
- **Database:** SQLite for local zero-config evaluation, seamless migration to Cloud SQL (PostgreSQL) via SQLAlchemy connection URI.

---

## 15. Security Controls & Threat Mitigations

- **Secret Handling:** All API keys (`GEMINI_API_KEY`, Firebase credentials) stored exclusively in backend `.env` and never leaked to the client.
- **Prompt Injection Defense:** Strict delimitation of user input, negative prompt rules against revealing system instructions or credentials, and read-only AI role enforcement.
- **Security Headers:** HSTS, X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy, and CORS whitelisting on every HTTP response.
- **Zero Autonomous Write Mutation:** The AI Advisor can only generate a cryptographic preview token; database state changes require an explicit human confirmation POST request.

---

## 16. Technologies Evaluated but NOT Implemented

| Technology | Evaluation Outcome | Rationale |
|---|---|---|
| **Vertex AI AutoML / Custom Training** | Evaluated, **NOT CLAIMED** | Deterministic statistical forecasting guarantees instant, explainable, and zero-cost operation for remote Indian healthcare facilities without cloud downtime risk. |
| **Google Dialogflow** | Evaluated, **NOT CLAIMED** | Gemini 2.5 Flash with grounded tool execution provides superior multi-turn comprehension, Hinglish flexibility, and operational extraction compared to static intent trees. |
| **Google Earth Engine** | Evaluated, **NOT CLAIMED** | Healysis focuses on supply-chain medicine inventory and inter-facility logistics; satellite remote sensing does not provide direct inventory telemetry. |
| **Firebase Firestore / Realtime DB** | Evaluated, **NOT CLAIMED** | Relational SQLAlchemy database with foreign key cascades and cryptographic audit ledger provides the ACID compliance necessary for medical supply chains. |
