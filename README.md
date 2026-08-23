# 🛡️ Healysis Sentry Network
**Tamper-Evident Health Telemetry & Federated Forensic AI for Primary Health Centres (PHCs)**

---

## 1. The Header & Hook
**Healysis Sentry Network** is a cryptographically secured public health supply-chain telemetry platform that tracks live medicine inventory, prevents ghost drawdowns, and orchestrates two-tier emergency stock rebalancing across Primary and Community Health Centres (PHCs/CHCs) using **SHA-256 block-chaining** and **Google Gemini 2.5/2.0 Flash**.

---

## 2. The Problem & Solution Match

### The Crisis: Vulnerable Health Supply Chains in Developing Regions
* **Zero Real-Time Visibility:** Peripheral PHCs operate on fragmented, manual paper records, causing unlogged stockouts for critical medicines (ORS, Insulin, Antibiotics).
* **Undocumented Parallel Diversion (Ghost Drawdowns):** High medicine drawdowns are frequently recorded against near-zero registered patient footfall, masking gray-market leakage.
* **Cold-Chain & Spoilage Failures:** Temperature-sensitive vaccines and biologics spoil in ILR units without real-time audit flags.

### The Healysis Solution
* **Cryptographic Block Verification:** Every dispense, receive, and spoilage event is linked in a sequential SHA-256 hash chain anchored to a genesis root.
* **Two-Tier CDMO Authorization:** Frontline staff log emergency requisitions, but physical and cryptographic transfer blocks are dispatched only upon Chief District Medical Officer (CDMO) authorization.
* **Automated Forensic AI Triage:** Google Gemini correlates clinical encounter tokens, footfall, and bed occupancy to generate 4-part legal audit dockets with one-click official PDF exports.

---

## 3. Core Features Breakdown

### Backend Engineering Engines
* **SHA-256 Cryptographic Ledger:** Computes event block hashes ( = \text{SHA256}(H_{n-1} + \text{Payload})$) ensuring immediate (1)$ tamper detection with exact index tracking (roken_at).
* **Two-Tier Requisition & Dispatch Engine:** Implements atomic dual-block execution (paired DISPENSE at source and RECEIVE at target) only upon director signature.
* **Multi-Layer Threat Filtering:** Regex sanitization layer guarding endpoints against SQLi (UNION SELECT), XSS (<script>), and LLM Jailbreak/Prompt Injections.
* **Sliding-Window Rate Limiter:** Hardened sentinel restricting bursts to 30 requests/minute per client IP.

### Frontend Operations & Clinical UX
* **5 Contextual RBAC Personas:** Seamlessly switch between frontline MOs, Pharmacists, Nurse Admins across Odisha & Bengal clusters, and the Central CDMO Director Hub.
* **One-Click Anomaly Simulation:** Immediate injection of high-severity ghost drawdowns for interactive evaluation and stress testing.
* **Official Forensic PDF Export:** Native print-engine pipeline converting AI forensic audits into signed district health briefs.
* **Dual Language Localization:** Real-time interface translation supporting both **English** and **हिंदी**.

---

## 4. The AI Architecture (Deep Dive)

\\\
+-----------------------------------------------------------------------------------+
|                        HEALYSIS NEURAL TELEMETRY PIPELINE                         |
+-----------------------------------------------------------------------------------+
                                          |
   [Raw PHC Telemetry Stream]             |-----> [Rule Sentry Evaluator]
   (Qty, Footfall, Token, SKU)            |       (RULE_GHOST_DISPENSE, BULK_DRAW)
                                          |
                                          v
                              [Anomaly Flagged (>=Medium)]
                                          |
                                          +---------------------------------+
                                          |                                 |
                                          v                                 v
                             [Primary AI Pipeline]             [Deterministic Engine]
                             (Gemini 2.5/2.0 Flash)            (Statistical Baseline)
                                          |                                 |
                                          +----------------+----------------+
                                                           |
                                                           v
                                            [4-Part Forensic Audit Docket]
                                            1. Incident Classification
                                            2. Evidence Correlation
                                            3. Root Cause Analysis
                                            4. CDMO Directives
                                                           |
                                                           v
                                            [Export Signed Audit PDF]
\\\

* **Structured Forensic Docket Generation:** Gemini correlates multi-variable parameters (e.g., 85 units of ORS dispensed against 1 patient with NULL token) into clinical audit findings.
* **Deterministic Fallback Engine:** If external API latency exceeds threshold or connectivity drops, an internal rule-based heuristic generates a complete clinical audit brief ensuring zero downtime.
* **State-Aware Geo-Fenced Advisor:** Live inventory math evaluation ($\text{Inventory} = \text{Base} + \text{Receive} - \text{Dispense} - \text{Spoilage}$) strictly bounded by district borders (Odisha vs. West Bengal).

---

## 5. Technical Stack & Engineering Choices

| Layer | Technologies / Tools | Technical Decision Justification |
| :--- | :--- | :--- |
| **Frontend UI/UX** | Next.js 15 (App Router), React 19, TypeScript | Server-rendered structural scaffolding and sub-second client transitions. |
| **Styling & Icons** | Tailwind CSS, @tabler/icons-react | Clean, high-density clinical dashboard aesthetics. |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn | Asynchronous endpoint execution with sub-millisecond telemetry routing. |
| **Data Validation** | Pydantic V2 | Strict data-type enforcement and input sanitization before ledger compute. |
| **Cryptography** | Python \hashlib\ (SHA-256) | Zero-dependency cryptographic hashing for verifiable audit chaining. |
| **Generative AI** | Google GenAI SDK (Gemini 2.5 / 2.0 Flash) | High token throughput with clinical forensic reasoning and structured output. |

---

## 6. Engineering Triumphs (The Solo Dev Factor)

* **Cryptographic Tamper Pinpointing:** Built a bidirectional hash verification algorithm that traverses the chain from GENESIS_ROOT_HEALYSIS_000 to the latest block, pinpointing the exact compromised block ID and array index in (N)$ time.
* **Low-Bandwidth Resilient Schema:** Stripped heavy blockchain consensus overhead (Proof-of-Work/Stake) down to lean, deterministic SHA-256 state hashing suitable for low-connectivity rural health outposts.
* **Zero Secret Leakage Architecture:** Designed isolated environment boundary masking ensuring API keys and administrative credentials are never exposed in client bundles or public commits.

---

## 7. Setup & Run Instructions

### Prerequisites
* **Node.js**: v18.18+ or v20+
* **Python**: v3.10+
* **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)

### 1. Clone & Configure
\\\ash
git clone https://github.com/Halanaaz1401/healysis-sentry-network.git
cd healysis-sentry-network
\\\

### 2. Backend Setup
\\\ash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt

# Create .env file
echo GEMINI_API_KEY=your_actual_gemini_api_key_here > .env

# Run FastAPI Server (Port 8000)
uvicorn main:app --reload --port 8000
\\\

### 3. Frontend Setup
\\\ash
# In a new terminal window:
cd frontend
npm install
npm run dev
\\\

Open **http://localhost:3000** in your browser to access the live dashboard.
