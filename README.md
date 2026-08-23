<div align="center">

# 🛡️ HEALYSIS SENTRY NETWORK
### Cryptographic Health Telemetry & Federated Forensic AI for Primary Health Centres

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js 15](https://img.shields.io/badge/Next.js%2015-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Google Gemini 2.5](https://img.shields.io/badge/Google%20Gemini-8E75C2?style=for-the-badge&logo=googlebard&logoColor=white)](https://aistudio.google.com/)
[![SHA-256 Chained](https://img.shields.io/badge/Ledger-SHA--256%20Cryptographic-0ea5e9?style=for-the-badge&logo=shield)](https://en.wikipedia.org/wiki/SHA-2)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald?style=for-the-badge)](https://opensource.org/licenses/MIT)

<p align="center">
  <b>Securing every medicine vial, cold-chain excursion, and hospital bed across peripheral health centers.</b><br />
  Combines immutable hash chaining with two-tier CDMO director stock authorization and instant AI forensic briefs.
</p>

[Explore Key Features](#-core-features-matrix) • [Architecture](#-neural-forensic-architecture) • [Live Personas](#-role-based-access-personas) • [Quickstart](#-quickstart-guide)

---

</div>

## 🌐 The Problem & Solution Match

| The Real-World Crisis (Remote PHCs) | The Healysis Engineering Fix |
| :--- | :--- |
| **Silent Stockouts:** Remote health posts run out of ORS/Insulin without central alert triggers. | **Real-Time Dynamic Telemetry:** Live mathematical consumption modeling tracks balance in real time. |
| **Ghost Drawdowns (Theft):** Bulk medicine drawdowns logged against 0 or 1 OPD footfall. | **Deterministic Sentry Engine:** Instant anomaly scoring and encounter token cross-matching. |
| **Ledger Tampering:** Clerical alteration of manual register logs or local database rows. | **SHA-256 Block Chaining:** Immutable hash sequence ( = \text{SHA256}(H_{n-1} + \text{Data})$). |
| **Uncoordinated Aid:** Stock rebalancing happens manually without director-level verification. | **Two-Tier CDMO Desk:** Frontline staff request stock; Central CDMO authorizes atomic dispatch. |

---

## ⚡ Core Features Matrix

### 🔐 1. Cryptographic SHA-256 Telemetry Ledger
* **Genesis-Anchored Immutability:** Every transaction is linked to the previous block hash starting from GENESIS_ROOT_HEALYSIS_000.
* **1-Click Ledger Audit:** Real-time hash recalculation engine that pinpoints the exact corrupted block index (roken_at) in (N)$ time if any row is tampered.
* **Zero-PII Tokenization:** Tracks patient interactions using anonymous encounter tokens (PAT-IN-8921) without storing personal identity data.

### 🧠 2. Google Gemini 2.5 Flash Forensic Triage Engine
* **4-Part Executive Brief:** Converts flagged transactions into structured audit dockets:
  1. *Executive Incident Classification*
  2. *Forensic Evidence & Statistical Correlation*
  3. *Suspected Root Cause Analysis*
  4. *CDMO Operational Directives*
* **Deterministic Fallback Engine:** Built-in heuristic audit generator ensures 100% operational uptime even during external API downtime.
* **Printable PDF Export:** Native one-click browser print pipeline that formats forensic incident case briefs with cryptographic block seals.

### 🏛️ 3. Two-Tier CDMO Requisition & Authorization Desk
* **Frontline Node Mode:** Health workers in remote facilities (Jatni, Cuttack, Pipili, Behala) can submit emergency requisitions (PENDING_APPROVAL).
* **CDMO Director Desk:** District authority reviews incoming emergency requests and signs cryptographic dispatch blocks directly into the network chain.

---

## 🏗️ Neural Forensic Architecture

\\\
  +-------------------------------------------------------------------------------+
  |                          HEALYSIS TELEMETRY PIPELINE                          |
  +-------------------------------------------------------------------------------+
                                          |
   [Frontline PHC Telemetry Stream]       |-----> [Cryptographic Ledger Block]
   (Qty, Footfall, Bed, Token, SKU)       |       (SHA-256 Chained to Genesis)
                                          |
                                          v
                              [Deterministic Rule Sentry]
                              (GHOST_DRAW, BULK_DEPLETION)
                                          |
                   +----------------------+----------------------+
                   | (Passed Integrity)                          | (Anomaly Flagged)
                   v                                             v
          [✅ Ledger Verified]                        [🚨 Forensic Triage Queue]
                                                                 |
                                              +------------------+------------------+
                                              |                                     |
                                              v                                     v
                                   [Google Gemini 2.5 Flash]              [Deterministic Engine]
                                   (Neural Forensic Model)                (Statistical Baseline)
                                              |                                     |
                                              +------------------+------------------+
                                                                 |
                                                                 v
                                                 [4-Part Forensic Audit Brief]
                                                 - Incident Classification
                                                 - Correlation Matrix
                                                 - Suspected Root Cause
                                                 - CDMO Directives
                                                                 |
                                                                 v
                                                    [📥 Export Verifiable PDF]
\\\

---

## 🧑‍⚕️ Role-Based Access Personas

The dashboard features **5 distinct authenticated roles** across two states to simulate district-wide operations:

| Persona | Location / Node | State | Role Scope |
| :--- | :--- | :---: | :--- |
| **Dr. A. Nayak (MO)** | Jatni CHC (Khordha) | OD | Frontline reporting & local stock audit |
| **S. Patra (Pharmacist)** | UPHC MS Das (Kafla Bazar) | OD | Urban dispensary stock dispensation |
| **R. Mohanty (Inventory)** | Pipili PHC (Puri) | OD | Rural health buffer monitoring |
| **T. Banerjee (Nurse Admin)** | Behala Urban PHC (Kolkata) | WB | Metro clinic triage & emergency request |
| **CDMO District Director** | Central Directorate Hub | HQ | Multi-District Requisition Authorization |

---

## 💻 Tech Stack & Engineering Decisions

<table align="center">
  <tr>
    <td align="center" width="96">
      <img src="https://skillicons.dev/icons?i=nextjs" width="48" height="48" alt="Next.js" />
      <br>Next.js 15
    </td>
    <td align="center" width="96">
      <img src="https://skillicons.dev/icons?i=react" width="48" height="48" alt="React" />
      <br>React 19
    </td>
    <td align="center" width="96">
      <img src="https://skillicons.dev/icons?i=tailwind" width="48" height="48" alt="Tailwind" />
      <br>Tailwind CSS
    </td>
    <td align="center" width="96">
      <img src="https://skillicons.dev/icons?i=ts" width="48" height="48" alt="TypeScript" />
      <br>TypeScript
    </td>
    <td align="center" width="96">
      <img src="https://skillicons.dev/icons?i=fastapi" width="48" height="48" alt="FastAPI" />
      <br>FastAPI
    </td>
    <td align="center" width="96">
      <img src="https://skillicons.dev/icons?i=py" width="48" height="48" alt="Python" />
      <br>Python 3.11+
    </td>
  </tr>
</table>

* **Frontend:** Next.js 15 App Router with Tabler Icons and localized English/Hindi translation layers.
* **Backend:** FastAPI with asynchronous request routing, Pydantic V2 schema validation, and sliding-window rate limiting.
* **Security Layer:** Regex sanitization protecting against SQLi, XSS, and LLM Prompt Injection attacks.
* **AI/LLM:** Google GenAI SDK powered by Gemini 2.5 Flash for high-speed clinical reasoning.

---

## 🚀 Quickstart Guide

### 1. Clone the Repository
\\\ash
git clone https://github.com/Halanaaz1401/healysis-sentry-network.git
cd healysis-sentry-network
\\\

### 2. Configure Backend
\\\ash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Create environment file
echo GEMINI_API_KEY="your_gemini_api_key_here" > .env

# Start FastAPI Engine
uvicorn main:app --reload --port 8000
\\\

### 3. Launch Frontend Dashboard
\\\ash
# Open a second terminal:
cd frontend
npm install
npm run dev
\\\

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🏆 The Solo Dev Factor: Engineering Challenges Solved

<details>
<summary><b>1. Cryptographic Tamper Pinpointing in (N)$</b></summary>
<br />
Implemented a continuous validation function that walks the chain forward from the genesis block, recomputing SHA-256 hashes against stored states and immediately surfacing the exact index and event ID where record corruption occurred.
</details>

<details>
<summary><b>2. State-Aware Geo-Fenced Telemetry Intelligence</b></summary>
<br />
Built a dynamic natural language query engine that detects administrative boundaries (Odisha vs. West Bengal clusters) and filters medicine stock metrics, preventing cross-jurisdiction confusion during emergency shortages.
</details>

<details>
<summary><b>3. Two-Tier Atomic Stock Redistribution</b></summary>
<br />
Designed paired transaction blocks (simultaneous source DISPENSE and target RECEIVE) linked to CDMO digital authorizations, preventing double-spending and unverified inventory inflation.
</details>

---

<div align="center">
  <sub>Built for resilient, tamper-evident public health administration.</sub>
</div>
