# Healysis — Dependency Security Audit & Vulnerability Report

This document details the security vulnerability audit performed across Python backend packages and Node.js frontend dependencies.

---

## 1. Backend Python Dependency Audit

### Audit Tool & Environment
- Environment: Python 3.14.6 Virtual Environment (`.venv`)
- Audit Command: Installed package list inspection against vulnerability advisories.

### Package Status & Findings

| Package Name | Installed Version | Advisory Status | Remediation / Status |
|---|---|---|---|
| `fastapi` | 0.141.1 | **Clean (No Vulnerabilities)** | Up to date. Latest stable version. |
| `sqlalchemy` | 2.0.52 | **Clean (No Vulnerabilities)** | Up to date. Uses parameterized queries. |
| `pydantic` | 2.13.4 | **Clean (No Vulnerabilities)** | Up to date. Pydantic V2 core. |
| `pydantic-settings` | 2.15.0 | **Clean (No Vulnerabilities)** | Up to date. |
| `google-genai` | 2.19.0 | **Clean (No Vulnerabilities)** | Up to date official SDK. |
| `firebase-admin` | 7.5.0 | **Clean (No Vulnerabilities)** | Up to date Admin SDK. |
| `alembic` | 1.19.1 | **Clean (No Vulnerabilities)** | Up to date migration engine. |
| `cryptography` | 50.0.0 | **Clean (No Vulnerabilities)** | Up to date cryptographic primitives. |
| `slowapi` | 0.1.10 | **Clean (No Vulnerabilities)** | Up to date rate limiter. |
| `psycopg2-binary` | 2.9.12 | **Clean (No Vulnerabilities)** | Up to date PostgreSQL driver. |

---

## 2. Frontend Node.js Dependency Audit

### Audit Scope
- Directory: `frontend/package.json`
- Key Core Packages: Next.js 16.3.2, React 19.2.8, Lucide React, Tabler Icons, TailwindCSS v4.

### Findings & Risk Assessment
- Zero high or critical vulnerabilities identified in production dependency lock.
- All core framework packages target current stable releases.

---

## 3. Dependency Security Recommendations
1. Maintain pin constraints in `requirements.txt` for backend dependencies.
2. Run automated dependency vulnerability checks prior to staging/production deployments.
