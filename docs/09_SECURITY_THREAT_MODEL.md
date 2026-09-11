# Healysis — Security Threat Model & Risk Analysis

This document provides a comprehensive security threat model for the Healysis Core Telemetry & Cross-District Redistribution Network.

---

## Threat Matrix & Security Controls

| Threat | Impact | Likelihood | Existing Control | Required Mitigation | Verification Method | Status |
|---|---|---|---|---|---|---|
| **Unauthenticated API Access** | High | Medium | Firebase ID Token verification via FastAPI `verify_firebase_token` dependency. | Reject requests missing Bearer tokens or with invalid signatures. | Automated Pytest (`test_missing_auth_header`, `test_invalid_auth_header_format`). | **PASS** |
| **RBAC Authorization Bypass** | High | Low | Server-side role enforcement via `require_roles` dependency. | Gated role endpoints (`ADMIN`, `CDMO`, `FACILITY_OFFICER`). Never trust client-supplied roles. | Pytest (`test_admin_authorization_forbidden_for_officer`, `test_cdmo_authorization_forbidden_for_officer`). | **PASS** |
| **Cross-Facility IDOR / BOLA** | High | Medium | `verify_facility_access` dependency checks user `facility_id`. | Restrict `FACILITY_OFFICER` strictly to assigned facility. | Pytest (`test_facility_officer_access_unassigned_facility_forbidden`, `test_facility_officer_cross_facility_access_idor`). | **PASS** |
| **Prompt Injection Attack** | Medium | Medium | Sanitization & system prompt grounding in `run_grounded_ai_advisor`. | Refuse override attempts ("ignore previous instructions", "reveal system prompt"). | Pytest (`test_prompt_injection_defense`, `test_system_prompt_extraction_defense`). | **PASS** |
| **Autonomous Action / Transfer Approval by AI** | High | Low | Hardcoded safety contract `requires_human_approval = True`. | AI Advisor provides decision support only. All stock actions require human CDMO/Admin approval. | Pytest (`test_structured_response_validation_and_no_autonomous_approval`). | **PASS** |
| **Direct Database Manipulation by AI** | Critical | Low | Gemini has no direct database access. Gated by 6 function tools. | Access strictly via verified backend tools with server-side validation. | Code Audit & Pytest (`test_unknown_tool_rejection`). | **PASS** |
| **API Secret / Credential Leakage** | Critical | Low | Environment variable loading (`GEMINI_API_KEY`, `SECRET_KEY`). `.gitignore` rules. | Exclude secrets from responses, logs, stack traces, and git. | Pytest (`test_api_key_and_secret_leakage_protection`, `test_secret_scanning_environment_check`). | **PASS** |
| **API Denial of Service / Throttling Bypass** | Medium | Medium | Sliding window IP rate-limiting sentinel in FastAPI middleware. | Rate limit `/advisor/chat` (10 req/min) and heavy endpoints. Return HTTP 429 when exceeded. | Pytest (`test_rate_limit_exceeded_throttling`). | **PASS** |
| **Information / Stack Trace Leakage** | Medium | Low | Centralized exception handler in `main.py`. | Return clean JSON `{"error": "Internal server error", "request_id": "..."}` without stack traces. | Pytest (`test_error_response_no_stacktrace_leakage`). | **PASS** |
| **CORS Misconfiguration / Origin Hijacking** | Medium | Medium | Middleware configured via `settings.ALLOWED_ORIGINS`. | Restrict allowed origins to frontend domains (`localhost:3000`, `healysis.ashlynxcyber.in`). | Pytest (`test_cors_validation_and_headers`). | **PASS** |
| **SQL Injection Attack** | Critical | Low | SQLAlchemy 2.0 ORM parameterized query execution. | Zero raw SQL string concatenation. Parameterize all queries. | Pytest (`test_sql_injection_attempt_safety`). | **PASS** |
| **Oversized Input / Request Size Abuse** | Medium | Low | Pydantic V2 max-length field constraints (`message` max 1000 chars). | Reject oversized request payloads with HTTP 422. | Pytest (`test_oversized_advisor_prompt_rejection`). | **PASS** |
| **Mass Assignment Attack** | Medium | Low | Pydantic schemas explicitly define allowed fields. | Ignore/strip extra fields not in Pydantic schema. | Pytest (`test_mass_assignment_attempt`). | **PASS** |
| **OpenAPI / Docs Exposure in Production** | Low | Low | Conditional documentation loading (`ENABLE_DOCS` setting). | Disable `/docs`, `/redoc`, and `/openapi.json` in production when `ENABLE_DOCS=false`. | Pytest (`test_production_debug_docs_configuration`). | **PASS** |

---

## Verification Summary
- Total Security Threats Evaluated: **14 Threat Vectors**
- Total Mitigations Verified: **14 Passed (100%)**
