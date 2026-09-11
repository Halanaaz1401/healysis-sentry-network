# Healysis — P0 Feature Specifications

## F1 — Command Center
Show:
- total facilities
- facilities at risk
- critical medicine stock-outs
- bed occupancy
- personnel coverage
- active redistribution recommendations
- forecast horizon
- recent audit events

Acceptance:
- values come from backend data
- risk cards link to evidence
- no fake hardcoded KPIs

## F2 — Medicine Inventory
Show:
- SKU, facility, available quantity
- safety stock
- consumption velocity
- days of cover
- batch/expiry
- incoming stock
- risk

Core calculation:
```text
days_of_cover = usable_stock / expected_daily_consumption
```

## F3 — Bed Availability
Track:
- General
- ICU
- Oxygen
- Isolation

Calculate:
- capacity
- occupied
- available
- occupancy %
- projected pressure

## F4 — Personnel Visibility
Track:
- doctors
- nurses
- pharmacists
- ASHA/support staff

Show:
- scheduled
- present
- absent
- coverage %
- staffing risk

## F5 — Demand Forecasting
Inputs:
- historical consumption
- recent velocity
- seasonality where available
- current stock
- incoming supply
- facility context

Outputs:
- predicted demand
- confidence/range where supported
- projected depletion
- stock-out risk
- safety buffer

Same input must produce reproducible results.

## F6 — Early Warning
Every alert includes:
- severity
- problem
- evidence
- projected impact
- time horizon
- recommended action

## F7 — Redistribution Recommendation
Consider:
- recipient demand
- recipient stock
- donor surplus
- donor safety stock
- distance
- urgency
- lead time

Output:
- donor
- recipient
- item
- quantity
- reason
- expected benefit
- confidence

Human approval required.

## F8 — Gemini AI Advisor
Grounded questions:
- Which facilities are at highest stock-out risk?
- Why is this medicine critical?
- Which facility should receive the next transfer?
- What changed in the last 24 hours?
- Explain this anomaly.

Use structured output:
```json
{
  "summary": "...",
  "risk_level": "HIGH",
  "evidence": [],
  "recommended_actions": [],
  "requires_human_approval": true
}
```

## F9 — Human Approval
```text
AI recommendation
      ↓
Evidence review
      ↓
Approve / Reject
      ↓
Action logged
      ↓
Ledger event
```

AI cannot approve its own recommendation.

## F10 — Trust & Audit
Retain the existing SHA-256 chained ledger concept.

Show:
- event ID
- previous hash
- current hash
- integrity status
- actor
- action
- timestamp

The ledger is **tamper-evident**, not a blockchain.
