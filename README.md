<div align="center">

# 🛡️ HEALYSIS SENTRY NETWORK
### Cryptographic Health Telemetry & Federated Forensic AI for Primary Health Centres

[![Live Demo](https://img.shields.io/badge/Live%20Demo-healysis.ashlynxcyber.in-0ea5e9?style=for-the-badge&logo=googlechrome&logoColor=white)](https://healysis.ashlynxcyber.in)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js 15](https://img.shields.io/badge/Next.js%2015-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Google Gemini 2.5](https://img.shields.io/badge/Google%20Gemini-8E75C2?style=for-the-badge&logo=googlebard&logoColor=white)](https://aistudio.google.com/)
[![SHA-256 Chained](https://img.shields.io/badge/Ledger-SHA--256%20Cryptographic-10b981?style=for-the-badge&logo=shield)](https://en.wikipedia.org/wiki/SHA-2)

<p align="center">
  <b>Securing every medicine vial, cold-chain excursion, and hospital bed across peripheral health centers.</b><br />
  Combines immutable hash chaining with two-tier CDMO director stock authorization and instant AI forensic briefs.
</p>

🔗 **Live Platform URL:** [https://healysis.ashlynxcyber.in](https://healysis.ashlynxcyber.in)

[Problem & Solution](#-problem--solution-match) • [Features Matrix](#-core-features-matrix) • [Architecture](#-neural-forensic-architecture) • [Personas](#-role-based-access-personas) • [Quickstart](#-quickstart-guide)

---

</div>

## 🌐 Problem & Solution Match

| The Real-World Crisis (Remote PHCs) | The Healysis Engineering Fix |
| :--- | :--- |
| **Silent Stockouts:** Remote health posts run out of ORS/Insulin without central alert triggers. | **Real-Time Dynamic Telemetry:** Live mathematical consumption modeling tracks balance in real time. |
| **Ghost Drawdowns (Theft):** Bulk medicine drawdowns logged against 0 or 1 OPD footfall. | **Deterministic Sentry Engine:** Instant anomaly scoring and encounter token cross-matching. |
| **Ledger Tampering:** Clerical alteration of manual register logs or local database rows. | **SHA-256 Block Chaining:** Immutable hash sequence ($H_n = \text{SHA256}(H_{n-1} + \text{Data})$). |
| **Uncoordinated Aid:** Stock rebalancing happens manually without director-level verification. | **Two-Tier CDMO Desk:** Frontline staff request stock; Central CDMO authorizes atomic dispatch. |

---

## ⚡ Core Features Matrix

### 🔐 1. Cryptographic SHA-256 Telemetry Ledger
* **Genesis-Anchored Immutability:** Every transaction is linked to the previous block hash starting from `GENESIS_ROOT_HEALYSIS_000`.
* **1-Click Ledger Audit:** Real-time hash recalculation engine that pinpoints the exact corrupted block index (`broken_at`) in $O(N)$ time if any row is tampered.
* **Zero-PII Tokenization:** Tracks patient interactions using anonymous encounter tokens (`PAT-IN-8921`) without storing personal identity data.

### 🧠 2. Google Gemini 2.5 Flash Forensic Triage Engine
* **4-Part Executive Brief:** Converts flagged transactions into structured audit dockets:
  1. *Executive Incident Classification*
  2. *Forensic Evidence & Statistical Correlation*
  3. *Suspected Root Cause Analysis*
  4. *CDMO Operational Directives*
* **Deterministic Fallback Engine:** Built-in heuristic audit generator ensures 100% operational uptime even during external API downtime.
* **Printable PDF Export:** Native one-click browser print pipeline that formats forensic incident case briefs with cryptographic block seals.

### 🏛️ 3. Two-Tier CDMO Requisition & Authorization Desk
* **Frontline Node Mode:** Health workers in remote facilities (Jatni, Cuttack, Pipili, Behala) can submit emergency requisitions (`PENDING_APPROVAL`).
* **CDMO Director Desk:** District authority reviews incoming emergency requests and signs cryptographic dispatch blocks directly into the network chain.

---

## 🏗️ Neural Forensic Architecture

```text
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