import os
import pathlib
import time
import uuid
import logging
from collections import defaultdict
from typing import Callable, Union, List

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.config import settings
from app.database import get_db
from app.routers import auth, forecasts, alerts, recommendations, advisor, facilities, resources, audit

BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

logger = logging.getLogger("healysis.api")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only seed database automatically in development/demo mode, never in production unless explicitly requested
    auto_seed = os.getenv("AUTO_SEED", "false" if settings.APP_ENV == "production" else "true").lower() == "true"
    if auto_seed:
        try:
            from seed_db import seed_database
            seed_database()
        except Exception as e:
            logger.warning(f"Startup database seeding note: {e}")
    yield

# Configure FastAPI application with conditional OpenAPI documentation
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Tamper-Evident Health Telemetry, Forecasting, Redistribution & AI Advisor API",
    version=settings.VERSION,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
    lifespan=lifespan
)

# Parsed Allowed Origins
allowed_origins_list: List[str] = (
    settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list)
    else [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
)

# Strict CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Rate Limiting Sentinel (Sliding Window per IP & Endpoint)
CALL_LOGS = defaultdict(list)

def check_rate_limit(client_ip: str, endpoint: str, max_calls: int = 15, window_secs: int = 60):
    """
    Server-side sliding window rate limiter.
    Returns HTTP 429 when max_calls limit per window_secs is exceeded.
    """
    now = time.time()
    key = f"{client_ip}:{endpoint}"
    # Relax limits during unit test execution
    effective_max = 500 if (settings.TESTING and endpoint != "test_rate_limit") else max_calls
    CALL_LOGS[key] = [t for t in CALL_LOGS[key] if now - t < window_secs]
    if len(CALL_LOGS[key]) >= effective_max:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Security Sentinel temporarily throttled requests."
        )
    CALL_LOGS[key].append(now)

# Security Headers & Correlation ID Middleware
@app.middleware("http")
async def add_security_headers_and_tracing(request: Request, call_next: Callable):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Enforce endpoint-specific rate limiting
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    try:
        if request.headers.get("x-test-rate-limit") == "true":
            check_rate_limit(client_ip, "test_rate_limit", max_calls=3, window_secs=60)
        elif "/advisor/chat" in path:
            check_rate_limit(client_ip, "advisor", max_calls=10, window_secs=60)
        elif "/forecasts/recalculate" in path or "/recommendations/generate" in path:
            check_rate_limit(client_ip, "heavy_op", max_calls=10, window_secs=60)
        elif path.startswith("/api/v1"):
            check_rate_limit(client_ip, "api_v1", max_calls=120, window_secs=60)
    except HTTPException as http_exc:
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"detail": http_exc.detail, "request_id": request_id}
        )


    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"Internal Error [REQ {request_id}]: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "request_id": request_id}
        )

    latency_ms = round((time.time() - start_time) * 1000, 2)

    # Attach HTTP Security Headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    
    logger.info(f"REQ {request_id} | {request.method} {path} | status={response.status_code} | latency={latency_ms}ms")
    return response

# Centralized Safe Exception Handling (Zero Info Leakage)
@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "request_id": request_id},
            headers=getattr(exc, "headers", None)
        )

    logger.error(f"Internal Error [REQ {request_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "request_id": request_id}
    )

# Mount APIRouters
app.include_router(auth.router)
app.include_router(facilities.router)
app.include_router(resources.router)
app.include_router(forecasts.router)
app.include_router(alerts.router)
app.include_router(recommendations.router)
app.include_router(advisor.router)
app.include_router(audit.router)

@app.get("/")
def health_check(request: Request):
    return {
        "service": settings.PROJECT_NAME,
        "status": "ONLINE",
        "version": settings.VERSION,
        "auth_provider": "FIREBASE_AUTHENTICATION_ENABLED",
        "ai_advisor": "GOOGLE_GENAI_SDK_GROUNDED_TOOLS_ENABLED",
        "redistribution_engine": "DETERMINISTIC_HAVERSINE_SCORING_ENABLED",
        "security_profile": "HARDENED_SERVER_SIDE_RBAC_AND_SECURITY_HEADERS"
    }