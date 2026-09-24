# Healysis P0 Frontend Implementation & Live Integration Guide

## 1. Overview
The Healysis P0 frontend is a Next.js App Router productized healthcare resource intelligence platform. It provides decision support for multi-state healthcare facilities across Odisha (OD) and West Bengal (WB) with strict server-side RBAC enforcement, deterministic EWMA forecasting, Haversine redistribution recommendations, and a grounded Gemini AI Advisor interface.

---

## 2. 10 Primary Healthcare Intelligence Screens & Routes

| Screen # | Screen Title | Route Path | Primary Capabilities & Features |
|---|---|---|---|
| **Screen 1** | **Authentication** | `/login` | Secure session entry, Firebase identity mapping, RBAC role selection (`ADMIN`, `CDMO`, `FACILITY_OFFICER`), facility assignment scoping, loading/error states, secure redirect to `/dashboard`. |
| **Screen 2** | **Executive Dashboard** | `/dashboard` | System overview, 4 KPI cards (Total Facilities, Active Alerts, Critical Shortages, Pending Rebalances), regional status indicators, active alert stream, and redistribution overview. |
| **Screen 3** | **Facility / Regional Overview** | `/facilities` | Interactive facility catalog across Odisha (Jatni CHC, UPHC MS Das Cuttack, Pipili PHC) and West Bengal (Behala UPHC Kolkata, Diamond Harbour PHC). Role-scoped filtering for `FACILITY_OFFICER`. |
| **Screen 4** | **Resource / Inventory Status** | `/resources` | Medicine inventory SKU table (ORS, Paracetamol, Insulin, Amoxicillin, Cetirizine), safety stock levels, daily demand, Days of Cover ($\text{DoC}$), projected stockout dates, and risk severity (`CRITICAL`, `WARNING`, `SAFE`). |
| **Screen 5** | **Forecast + Risk Engine** | `/forecasts` | Predictive intelligence based on deterministic EWMA ($\alpha=0.3$) demand projection, 7-day velocity, historical depletion dates, and clear callouts distinguishing verified math from AI text. |
| **Screen 6** | **Redistribution Recommendations** | `/recommendations` | Inter-facility stock transfer routes generated via Haversine distance scoring. Non-autonomous design strictly requiring human approval from authorized CDMO/ADMIN users. Includes What-if simulation and Before/After verification. |
| **Screen 7** | **Early Warning Alerts** | `/alerts` | Operational risk alerts with Notify → Acknowledge → Escalate SLA workflows, deterministic escalation timeout badges, and facility-scoped views. |
| **Screen 8** | **District / Network Intelligence** | `/network` | Aggregated network-level health, district breakdowns, resource-level network telemetry, intervention priorities, and donor/recipient signals. Restricted to `CDMO`/`ADMIN`. |
| **Screen 9** | **Gemini AI Advisor** | `/advisor` | Grounded decision support chat communicating with `POST /api/v1/advisor/chat`. Displays answer, risk severity, tool evidence payload inspector, data sources, and mandatory human approval disclaimer. |
| **Screen 10** | **Audit Ledger** | `/audit` | Cryptographically chained SHA-256 tamper-evident audit ledger displaying all inventory updates, redistribution approvals, and system state transitions. |

---

## 3. Architecture & Security Preservations
- **Zero Frontend Secret Exposure:** Browser client bundle contains zero Gemini API keys, Firebase Admin credentials, or database secrets.
- **Server-Side RBAC Enforcement:** UI routing displays role-aware badges (`ADMIN`, `CDMO`, `FACILITY_OFFICER`), but actual authorization is strictly validated by backend FastAPI endpoints.
- **Human Operational Approval:** Neither Gemini nor deterministic algorithms can autonomously dispatch stock transfers. Physical rebalancing requires human CDMO/ADMIN action.
- **Design System Tokens:** Reused existing brand assets, typography (Geist Sans & Geist Mono), color palette (`#0C2B4E` Deep Navy, `#1D546C` Teal Accent, `#F4F4F4` surface), and `/public/logo.png`. Documented in [`frontend/src/design-tokens.md`](file:///c:/Users/Hala/Downloads/Healysis/frontend/src/design-tokens.md).

---

## 4. Live Local Preview Instructions

1. **Start FastAPI Backend (Port 8000):**
   ```bash
   cd backend
   .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```
2. **Start Next.js Frontend (Port 3000):**
   ```bash
   cd frontend
   npm run dev -- -p 3000
   ```
3. **Open Browser Live Preview:**
   - **URL:** `http://localhost:3000`
