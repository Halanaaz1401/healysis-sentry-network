# Healysis — AI, Forecasting & Data Contract

## AI philosophy
**Deterministic systems calculate. Gemini explains and assists. Humans authorize consequential actions.**

## Architecture Diagram (Google GenAI Integration)
```text
User / Frontend
      ↓
Healysis API (FastAPI + Firebase Auth + RBAC)
      ↓
Gemini AI Advisor (Google GenAI SDK 2.x - google-genai)
      ↓
Healysis Grounded Tools (Function Calling)
  ├── get_facility_overview
  ├── get_resource_status
  ├── get_active_alerts
  ├── get_forecasts
  ├── get_redistribution_recommendations
  └── get_facility_comparison
      ↓
Verified Database Records & Deterministic Engines
      ↓
Gemini Grounded Operational Response
```

## Pipeline
```text
Raw / synthetic data
        ↓
Validation
        ↓
Normalization
        ↓
Database
        ↓
Analytics
        ↓
Forecasts + alerts
        ↓
Gemini grounding
        ↓
Recommendation explanation
```

## Forecast input
- facility_id
- item_id
- historical daily consumption
- current stock
- incoming quantity
- lead time
- safety stock

## Forecast output
- expected daily demand
- days of cover
- projected depletion
- risk
- recommended reorder quantity

## Alert contract
```json
{
  "alert_id": "ALT-001",
  "facility_id": "PHC-001",
  "resource_id": "MED-001",
  "severity": "CRITICAL",
  "title": "Projected stock-out",
  "evidence": [],
  "projected_date": "...",
  "recommended_action": "..."
}
```

## Gemini rules
Gemini receives:
- user question
- authorized scope
- retrieved data
- computed metrics
- relevant alerts
- approved tools

Gemini must NOT:
- invent inventory
- invent facilities
- fabricate statistics
- approve transfers
- diagnose patients
- prescribe treatment

## Tool/function examples
```text
get_facility_overview(facility_id)
get_resource_status(facility_id, resource_id)
get_active_alerts(facility_id, severity)
get_forecasts(facility_id, resource_id)
get_redistribution_recommendations(facility_id, status)
get_facility_comparison(facility_ids)
```

Every tool enforces authorization.

## Evidence
Every AI recommendation should trace to:
- records
- calculated metrics
- forecast outputs
- business rules

## Data realism
Document:
- source
- generation method
- date range
- assumptions
- limitations
