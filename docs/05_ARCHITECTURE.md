# Healysis — Architecture

## Target
```text
                    USERS
                      │
                      ▼
              Next.js Web App
                      │
                 HTTPS / JSON
                      │
                      ▼
              FastAPI Application
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
   PostgreSQL      Forecasting     Gemini
       │           / Analytics      │
       └──────────────┼─────────────┘
                      ▼
             Recommendation Engine
                      │
                Human Approval
                      │
                      ▼
             Redistribution Action
                      │
                      ▼
              Audit / Ledger Layer
```

## Domains
```text
facilities
inventory
beds
personnel
consumption
forecasts
alerts
recommendations
requisitions
users/roles
audit_events
```

## India-scale story
```text
State A ─┐
State B ─┼──> standardized ingestion
State C ─┤
State N ─┘
             ↓
       regional processing
             ↓
       shared analytics
             ↓
        national insights
```

The prototype does not need every state populated. It must demonstrate that the architecture can expand beyond one state.

## Security boundary
```text
Browser → Authentication → Authorization → API → Services → Database
```

Never trust client-side role flags.

## AI boundary
```text
Gemini
  ↓
Recommendation
  ↓
Human approval
  ↓
Backend transaction
  ↓
Audit event
```

## Reuse from existing Healysis
- SHA-256 event chaining
- anomaly rule concepts
- requisition workflow
- seed generation concepts
- FastAPI foundation
- Next.js foundation
- brand/logo

## Replace
- CSV primary storage
- in-memory requisitions
- monolithic page
- simulated client-side RBAC
- hardcoded production URL
