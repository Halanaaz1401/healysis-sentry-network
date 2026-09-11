# 🏥 Healysis Sentry Network

<p align="center">
  <strong>AI-Powered Health Supply Chain Resilience for India's Primary Healthcare Network.</strong>
</p>

<p align="center">
  A production-ready healthcare operations platform for inventory visibility, demand forecasting, stockout early warning, cross-facility redistribution, and grounded Google Gemini assistance.
</p>

---

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js 16](https://img.shields.io/badge/Next.js%2015-black?style=for-the-badge&logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-8E75C2?style=for-the-badge&logo=googlebard&logoColor=white)
![Platform](https://img.shields.io/badge/Live%20Platform-healysis.ashlynxcyber.in-0ea5e9?style=for-the-badge&logo=googlechrome&logoColor=white)
![Status](https://img.shields.io/badge/Status-Completed-brightgreen?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

</p>

<p align="center">

![Cybersecurity](https://img.shields.io/badge/Cybersecurity-SHA--256%20Ledger-10b981?style=flat-square)
![Threat Detection](https://img.shields.io/badge/Threat-Ghost%20Drawdowns-darkred?style=flat-square)
![Incident Response](https://img.shields.io/badge/Forensic%20Triage-Gemini%20AI-blueviolet?style=flat-square)
![Supply Chain](https://img.shields.io/badge/Supply%20Chain-Two--Tier%20CDMO-teal?style=flat-square)
![Zero PII](https://img.shields.io/badge/Privacy-Zero--PII%20Tokens-blue?style=flat-square)
![Geo-Fencing](https://img.shields.io/badge/Geo--Fencing-Odisha%20%26%20WB-green?style=flat-square)

</p>

---

## Overview

Healthcare facilities can face medicine shortages even when useful stock exists elsewhere in the network. Current stock alone is not enough: administrators need visibility into demand, safety stock, days of cover, projected stockout dates, facility risk, and redistribution options.

**Healysis Sentry Network** provides a centralized operational intelligence layer for healthcare supply-chain resilience.

The platform combines:

- Real-time medicine inventory visibility
- Facility and district-level operational data
- EWMA-based demand forecasting
- Stockout-date estimation
- Risk severity and early-warning alerts
- Cross-facility redistribution recommendations
- Human-approved stock transfer workflows
- Firebase authentication and server-side RBAC
- Audit logging and operational traceability
- Google Gemini-powered AI assistance

> **Core principle: deterministic healthcare calculations establish the operational state; Gemini explains that state in natural language.**
## Repository Highlights

✔ Google Gemini-powered grounded AI Advisor  
✔ EWMA demand forecasting and stockout-risk prediction  
✔ Real-time facility and medicine inventory visibility  
✔ Cross-district redistribution recommendations  
✔ Human-in-the-loop approval workflow  
✔ Post-approval inventory, forecast, risk, and alert reconciliation  
✔ Firebase authentication with server-side RBAC  
✔ Audit logging for operational traceability  
✔ PostgreSQL production architecture with local SQLite fallback  
✔ Live production deployment


## Key Features

### 📊 Dashboard
Central operational view of facility status, inventory conditions, critical resources, forecasts, risk levels, alerts, and redistribution activity.

### 🏥 Facility Management
Facility-level visibility including facility name/type, district/state, address, assigned officer, inventory, and operational context.

### 📦 Inventory & Resources
Tracks SKU/item code, resource name, unit of measure, current stock, safety stock, daily demand, days of cover, projected stockout date, and risk severity.

### 📈 Forecasts & Risk
Healysis uses **Exponentially Weighted Moving Average (EWMA)** forecasting to estimate demand trends.

```text
Historical Demand
       ↓
EWMA Forecast
       ↓
Days of Cover
       ↓
Projected Stockout
       ↓
Risk Classification
```

### 🚨 Alerts
Surfaces inventory conditions requiring operational attention and reconciles alert state when inventory changes.

### 🔄 Redistribution
Generates potential stock-transfer recommendations between facilities.

```text
Recommendation
      ↓
Authorized Human Review
      ↓
Approve / Reject
      ↓
Inventory Update
      ↓
Forecast & Risk Recalculation
      ↓
Audit Record
```

AI does not independently execute physical stock transfers.

### 🤖 Google Gemini AI Advisor
Answers operational questions using verified Healysis data. The backend resolves the facility, retrieves authorized telemetry, and supplies deterministic operational values to Gemini for explanation.

### 🔐 Authentication & RBAC
Firebase authentication is combined with backend authorization. Roles include System Administrator, CDMO / Director, and Facility Officer. Facility-level access remains enforced server-side.


## Project Status

| Area | Status |
|---|---|
| Core product | ✅ Completed |
| End-to-end workflow | ✅ Completed |
| Google Gemini integration | ✅ Completed |
| Predictive forecasting | ✅ Completed |
| Stockout risk & alerts | ✅ Completed |
| Redistribution approval | ✅ Completed |
| Firebase authentication / RBAC | ✅ Completed |
| Security & regression QA | ✅ Completed |
| GitHub repository | ✅ Published |
| Live deployment | ✅ Live |
| Demo video | ⏳ Submission asset |
| Pitch deck | ⏳ Submission asset |
| Final submission | ⏳ Pending |

**Live Platform:** https://healysis.ashlynxcyber.in


## Why This Project?

Traditional healthcare supply chains rely on static, centralized databases or paper registers that can be trivially modified or backdated.

Healysis introduces **mathematical trust and decentralized forensic accountability**. By anchoring every telemetry event in an immutable SHA-256 chain and evaluating live drawdowns using Gemini AI, district health directors can prevent medicine theft in real time rather than discovering stockouts months later during post-mortem audits.

---

## Table of Contents

- [Overview](#overview)
- [Repository Highlights](#repository-highlights)
- [Key Features](#key-features)
- [Project Status](#project-status)
- [Why This Project?](#why-this-project)
- [Problem vs. Solution](#problem-vs-solution)
- [Project Architecture](#project-architecture)
- [System Workflow](#system-workflow)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Core Design Principles](#core-design-principles)
- [Security Hardening](#security-hardening)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Running the Complete System](#running-the-complete-system)
- [Configuration](#configuration)
- [Forensic AI Pipeline](#forensic-ai-pipeline)
- [Two-Tier Rebalancing Engine](#two-tier-rebalancing-engine)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)
- [License](#license)
- [Author](#author)
- [Acknowledgements](#acknowledgements)

---

## Problem vs. Solution

| Problem | Healysis Sentry Network Solution |
|---|---|
| Paper-based records with no audit trail | SHA-256 cryptographic ledger — every transaction is hashed and chained, retroactive edits mathematically break the chain |
| Zero real-time inventory visibility | Live geo-fenced dashboard across facilities, districts, and states |
| Medicine stockouts (ORS, Insulin, Paracetamol) | Real-time inventory math (`Base + Receive − Dispense − Spoilage`) with early-warning telemetry |
| Cold-chain vaccine spoilage in ILR units | Spoilage batch tracking built into the ledger and rule engine |
| Gray-market "ghost drawdowns" (high-volume draws vs. near-zero footfall) | `RULE_GHOST_DISPENSE` / `RULE_BULK_DEPLETION` anomaly rules + statistical footfall correlation |
| No accountability for cross-facility stock transfers | Two-tier CDMO requisition desk with atomic dual-block dispatch, zero double-spending |
| Manual, slow incident investigation | Gemini 2.5 Flash generates a structured 4-part forensic brief automatically on every flagged event |

---

## Project Architecture

The Healysis Sentry Network follows an asynchronous, event-driven architecture that separates raw telemetry ingestion, cryptographic block computation, rule sentry scoring, and neural forensic analysis.

```mermaid
flowchart LR

A[Frontline PHC Transaction] --> B[Security Sanitizer & Rate Limiter]
B --> C[SHA-256 Ledger Engine]
C --> D[Rule Sentry Evaluator]
D --> E{Integrity Violation?}
E -->|No| F[Commit Verified Block]
E -->|Yes| G[Flagged Incident Queue]
G --> H[Gemini 2.5 Forensic Engine]
G --> I[Deterministic Heuristic Fallback]
H --> J[4-Part Forensic Brief]
I --> J
J --> K[Two-Tier Requisition Desk]
K --> L[CDMO Director Authorization]
L --> M[Atomic Dispatch Ledger Blocks]
```

---

## System Workflow

```
Frontline Telemetry Input (Facility, Action, SKU, Qty, Footfall, Token)
        │
        ▼
Regex Sanitization & Sliding-Window Rate Limiter
        │
        ▼
SHA-256 Previous Hash Linking (Hn = SHA256(Hn-1 + Payload))
        │
        ▼
Rule Sentry Scoring Engine (Ghost Draw, Bulk Depletion, Spoilage)
        │
        ▼
────────────────────────────────────────────────────────────
Status: Verified (No Rules Triggered)
────────────────────────────────────────────────────────────
Appended to Ledger as VERIFIED Block

────────────────────────────────────────────────────────────
Status: Anomaly Flagged (Severity >= Medium)
────────────────────────────────────────────────────────────
        │
        ▼
Flagged Incident Queued in Cryptographic Ledger
        │
        ▼
Google Gemini 2.5 Flash / Deterministic Fallback
        │
        ▼
Structured 4-Part Forensic Audit Brief Generated
        │
        ▼
CDMO Operational Directives & Verification Mandate
        │
        ▼
One-Click Verifiable Audit PDF Exported
        │
        ▼
Two-Tier Inter-Facility Requisition & Atomic Dispatch
```

---

## Project Structure

```
healysis-sentry-network/
│
├── backend/
│   ├── data/
│   │   └── phc_stock_events.csv      # Persistent SHA-256 transaction ledger
│   ├── engine.py                     # Cryptographic hashing & rule evaluation
│   ├── main.py                       # FastAPI application & Gemini integration
│   ├── requirements.txt              # Python dependency definitions
│   └── .env.example                  # Environment configuration template
│
├── frontend/
│   ├── public/
│   │   └── logo.png                  # Platform branding assets
│   ├── src/
│   │   └── app/
│   │       ├── globals.css           # Tailwind CSS directives
│   │       ├── layout.tsx            # Root layout wrapper
│   │       └── page.tsx              # Complete clinical telemetry dashboard
│   ├── package.json                  # Next.js and frontend dependencies
│   ├── tailwind.config.ts            # Tailwind styling tokens
│   └── tsconfig.json                 # TypeScript compiler configuration
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## Technology Stack

### Frontend Layer

| Technology | Purpose |
|---|---|
| **Next.js 16 (App Router)** | Client interface & server-rendered routing |
| **React 19** | Component-driven UI architecture |
| **TypeScript** | Type-safe schema validation |
| **Tailwind CSS** | Clinical dashboard styling |
| **Tabler Icons React** | Vector iconography |

### Backend & Security

| Technology | Purpose |
|---|---|
| **Python 3.11+** | Backend engine execution |
| **FastAPI** | Asynchronous RESTful telemetry endpoints |
| **Pydantic V2** | Ingestion validation schemas |
| **hashlib (SHA-256)** | Cryptographic hash chaining |
| **Pandas** | Telemetry and historical data manipulation |
| **Uvicorn** | High-performance ASGI server |

### Artificial Intelligence & Telemetry

| Technology | Purpose |
|---|---|
| **Google GenAI SDK** | Gemini 2.5 Flash API interface |
| **Gemini 2.5 Flash** | Grounded healthcare operations assistant |
| **Custom Sentry Heuristics** | Deterministic audit generation fallback |

---

## Core Design Principles

### Cryptographic Non-Repudiation

Every transaction payload is hashed sequentially with the previous block's hash. Any retroactive modification breaks all subsequent hashes, immediately identifying tampering.

### Two-Tier Administrative Safeguards

Frontline nodes can never self-authorize inventory transfers. All rebalancing requires CDMO Director sign-off to prevent inventory double-spending.

### Zero-Downtime Deterministic Fallbacks

If external AI connectivity is unavailable, the internal heuristic baseline immediately generates a structured audit brief to avoid operational blind spots.

### Privacy by Design (Zero-PII)

Patient interactions are logged via tokenized encounter strings without storing Aadhaar numbers, phone numbers, or personal identifying data.

---

## Security Hardening

Healysis is built with a "hack-proof by design" posture across every layer of the stack:

| Layer | Protection |
|---|---|
| **Cryptographic Immutability** | SHA-256 block-chaining (`H_n = SHA256(H_{n-1} + Payload)`) anchored to `GENESIS_ROOT_HEALYSIS_000`. Retroactive database row modification mathematically invalidates the entire subsequent chain. |
| **SQLi & XSS Sanitization** | Deep regex filter inspecting all inbound payloads for classic attack patterns (`UNION SELECT`, `OR 1=1`, `<script>`, `onerror=`). |
| **LLM Jailbreak & Prompt Injection Defense** | Dedicated sanitization layer neutralizing system prompt overrides, ignore-instruction vectors, and adversarial tokens before invoking the AI model. |
| **Rate Limiting Sentinel** | Sliding-window memory rate limiter capping requests at 30 req/min per client IP to mitigate automated DDoS, scraping, and brute-force flooding. |
| **Zero-PII Tokenization** | Patient privacy by design — anonymizes all transactions with encounter hashes (e.g., `PAT-IN-8921`), never storing identity data (Aadhaar, contact, name) on-chain. |
| **Secret Boundary Isolation** | Environment variables and API keys strictly quarantined in isolated server environments, never compiled into client-side Next.js bundles or committed to git history. |

---

## 🏆 Hackathon Alignment

Healysis is built for the **Smart Health & Supply Chain Resilience** track.

| Hackathon Requirement | Healysis Implementation |
|---|---|
| Functioning end-to-end prototype | Inventory → forecast → risk → redistribution → audit |
| Mandatory Google AI | Google Gemini-powered AI Advisor |
| Real / realistic data | Realistic healthcare facility and resource data |
| Built for India | Multi-district, multi-state healthcare model |
| Deployed prototype | Live production deployment |
| Human-centered operation | Authorized human approval for redistribution |

## 🧠 Google AI Architecture

```text
User Question
     ↓
Intent / Facility Resolution
     ↓
Authorization Check
     ↓
Verified Backend Retrieval
     ↓
Deterministic Inventory & Forecast Data
     ↓
Google Gemini
     ↓
Grounded Natural-Language Response
```

### Grounding Rules

Gemini must not:

- Invent stock quantities
- Invent forecast values
- Invent facilities or resources
- Bypass authorization
- Approve redistribution
- Expose secrets or authentication data

## 🔄 End-to-End Operational Flow

```text
Facility
   ↓
Inventory & Demand
   ↓
Forecasting
   ↓
Stockout / Risk Detection
   ↓
Alert
   ↓
Redistribution Recommendation
   ↓
Human Approval
   ↓
Inventory Transfer
   ↓
Forecast Refresh
   ↓
Risk Refresh
   ↓
Audit
```

## 🇮🇳 India-Scale Design

```text
State
  ↓
District
  ↓
Facility
  ↓
Resource
  ↓
Demand / Inventory Telemetry
```

The prototype demonstrates facilities across Odisha and West Bengal while keeping the core model extensible to additional states, districts, PHCs, CHCs, UPHCs, resource catalogs, and demand datasets.

## 📸 Product Screenshots

Create `docs/screenshots/` and add the actual screenshots below.

### Dashboard

![Healysis Dashboard](docs/screenshots/dashboard.png)

### Facilities

![Healysis Facilities](docs/screenshots/facilities.png)

### Forecasts & Risk

![Healysis Forecasts and Risk](docs/screenshots/forecasts-risk.png)

### AI Advisor

![Healysis AI Advisor](docs/screenshots/ai-advisor.png)

### Redistribution & Audit

![Healysis Redistribution and Audit](docs/screenshots/redistribution-audit.png)

> Five strong screenshots are enough. Prioritize Dashboard, Facilities, Forecasts & Risk, AI Advisor, and Redistribution/Audit.

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │    Next.js Web UI   │
                    └──────────┬──────────┘
                               │
                    Firebase Authentication
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI Backend   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        Authorization     PostgreSQL       Gemini AI
              │                │                │
              ▼                ▼                ▼
          RBAC / Scope    Operational      Grounded
                           Telemetry       Explanation
                               │
                               ▼
                  Forecast / Risk / Alerts
                               │
                               ▼
                     Redistribution
                               │
                               ▼
                         Audit Trail
```

## 🧪 Quality Assurance

Healysis completed production-readiness and end-to-end QA.

### Backend

```text
168 / 168 tests passing
```

### Frontend

```text
Production build successful
13 / 13 application routes validated
```

Validation covered authentication, RBAC, authorization boundaries, redistribution approval, duplicate approval prevention, inventory consistency, forecast/risk refresh, alert reconciliation, AI grounding, input validation, and security regressions.

## 🧩 Design Principles

### AI Grounding
Numerical operational truth comes from backend data and deterministic calculations.

### Human-in-the-Loop
AI recommends; authorized healthcare personnel decide.

### Server-Side Authorization
Frontend visibility is never treated as a security boundary.

### Operational Consistency
Approved transfers update inventory, forecasts, risk, and alerts consistently.

### Production Separation
Development and production configuration are separated, and secrets remain outside source control.

## 🌍 Deployment

**Live prototype:** https://healysis.ashlynxcyber.in

The production architecture separates the frontend, backend API, database, authentication service, and Gemini integration so each layer can be scaled independently.

## Installation

### Prerequisites

| Requirement | Version |
|---|---|
| **Node.js** | v18.18+ or v20+ |
| **Python** | v3.10+ |
| **pip** | Latest |
| **Gemini API Key** | From [Google AI Studio](https://aistudio.google.com/) |

---

## Quick Start

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Halanaaz1401/healysis-sentry-network.git
cd healysis-sentry-network
```

### Step 2 — Configure & Run Backend

```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt

# Create environment file
echo GEMINI_API_KEY="your_actual_gemini_api_key_here" > .env

# Start FastAPI Engine (Port 8000)
uvicorn main:app --reload --port 8000
```

### Step 3 — Launch Frontend Dashboard

```bash
# Open a separate terminal window:
cd frontend
npm install
npm run dev
```

---

## Running the Complete System

| Service | Port | Local Endpoint |
|---|---|---|
| **FastAPI Backend** | 8000 | `http://127.0.0.1:8000` |
| **Next.js Dashboard** | 3000 | `http://localhost:3000` |
| **API Documentation** | 8000 | `http://127.0.0.1:8000/docs` |
| **Production Demo** | 443 | `https://healysis.ashlynxcyber.in` |

---

## Configuration

All backend secrets are isolated in a single environment file and never committed to git.

**`backend/.env`**

```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

- No quotes around the key value
- No trailing whitespace after the key
- `.env` is excluded via `.gitignore` — never commit real credentials
- Use `backend/.env.example` as the template for new environments

---

## Forensic AI Pipeline

When an anomaly is flagged, the system prompts **Gemini 2.5 Flash** with multi-variable parameters to produce an executive brief:

```
1. EXECUTIVE INCIDENT CLASSIFICATION
   - Severity Rating (CRITICAL / HIGH / MEDIUM)
   - Policy & Baseline Breaches

2. FORENSIC EVIDENCE & STATISTICAL CORRELATION
   - Quantity Drawdown vs. Registered Patient Footfall (>3σ deviation)
   - Encounter Token Verification

3. SUSPECTED ROOT CAUSE ANALYSIS
   - Parallel Gray-Market Stock Diversion
   - Unlogged Offline Emergency Dispensation
   - ILR Cold-Chain Batch Spoilage

4. CDMO OPERATIONAL DIRECTIVES
   - Transaction Block Quarantine
   - Block Medical Officer (BMO) Register Audit
   - Inter-District Stock Rebalance Action
```

If the Gemini API is unreachable or rate-limited, the **deterministic heuristic fallback engine** generates an equivalent structured brief with zero downtime, and the full docket can be exported as a signed, printable PDF for district magistrates and health directors.

---

## Two-Tier Rebalancing Engine

1. **Requisition Submission:** Remote clinic selects target item and submits an emergency request (`PENDING_APPROVAL`).
2. **Director Review:** Requisition appears in the CDMO Central Hub console.
3. **Atomic Execution:** On "Authorize & Dispatch", the backend commits two linked SHA-256 blocks:
   - `DISPENSE` at source facility
   - `RECEIVE` at target facility

This guarantees stock transfers are cryptographically balanced across nodes with zero inventory double-spending.

---

## Troubleshooting

### Backend fails to connect to Gemini

Ensure your `backend/.env` file contains `GEMINI_API_KEY=your_key` without quotes and has no trailing spaces.

### Ledger tampering alert appears

Click **"Verify Hash Chain"** in the header. If testing manual tampering, inspect `phc_stock_events.csv` to ensure hashes match sequential outputs.

### Port conflicts

If port 8000 or 3000 is in use:

```bash
uvicorn main:app --reload --port 8080
npm run dev -- -p 3001
```

---

## Future Enhancements

- **Hardware ILR Integration:** Direct IoT temperature sensor hooks for automated cold-chain excursion logging.
- **Offline Mesh Sync:** Bluetooth/Wi-Fi Direct peer-to-peer ledger sync for remote areas without internet.
- **Federated Zero-Knowledge Proofs (ZKPs):** Verifying multi-district quotas without disclosing clinic-specific patient counts.

---

## License

This project is licensed under the **MIT License** - see the `LICENSE` file for details.

---

## Author

**Hala Naaz**

Platform: [https://healysis.ashlynxcyber.in](https://healysis.ashlynxcyber.in)

GitHub: [https://github.com/Halanaaz1401](https://github.com/Halanaaz1401)

---

## Acknowledgements

- **Google AI Studio** for Gemini 2.5 Flash developer access.
- **FastAPI & Next.js Communities** for foundational open-source toolkits.
- **Public Health Administrations** of Odisha and West Bengal for inspirational clinical telemetry workflows.
