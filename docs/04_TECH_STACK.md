# Healysis — Technology Stack

## Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS

## Backend
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL target
- SQLite acceptable locally

## Google AI — mandatory
Gemini is the primary AI layer for:
- grounded operational advisor
- structured risk explanations
- anomaly triage
- recommendation explanation
- controlled function calling

Flow:
```text
Question → Authorization → Trusted data retrieval → Tool call → Gemini → Structured JSON → UI
```

## Predictive modelling
Start with transparent, reproducible forecasting:
- rolling averages
- exponential smoothing where useful
- consumption velocity
- lead-time projection

Use Vertex AI only where it materially strengthens the prototype.

## Google Cloud
**Target deployment: Cloud Run**

## Data
- PostgreSQL for transactional prototype data
- BigQuery as the scale analytics layer if implemented
- public/open datasets where appropriate
- realistic synthetic data when live data is unavailable
- clearly label synthetic data

## Optional Google services
- Firebase Auth
- Google Maps Platform
- Cloud Translation API
- Speech-to-Text / Text-to-Speech
- Gemini multimodal

## Security
- backend authorization
- environment variables for secrets
- restrictive CORS
- validation
- rate limiting
- audit logging
- no patient PII in demo data
- least privilege
