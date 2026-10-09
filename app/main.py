
import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from sqlalchemy import text

from app.database import Base, engine
from app import models
from app.devices import router as devices_router


# Load local configuration before reading environment variables.
load_dotenv()

API_KEY = os.getenv("API_KEY", "")

# Configure rate limiting through .env.
RATE_LIMIT_REQUESTS = max(
    1,
    int(os.getenv("RATE_LIMIT_REQUESTS", "10")),
)
RATE_LIMIT_WINDOW = max(
    1,
    int(os.getenv("RATE_LIMIT_WINDOW", "60")),
)

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def verify_api_key(api_key: str | None = Security(api_key_header)):
    """Reject requests without the configured API key."""

    if API_KEY in {
    "",
    "replace-this-with-your-own-local-key",
    "your-api-key-here",
}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    if api_key is None or not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return True


# Store request timestamps for each client IP.
# This in-memory limiter is suitable for our local demonstration.
request_timestamps: dict[str, deque[float]] = defaultdict(deque)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables when the application starts."""

    Base.metadata.create_all(bind=engine)

    yield

    engine.dispose()


app = FastAPI(
    title="Network Management API",
    description=(
        "A network-device inventory REST API with API-key "
        "authentication and request rate limiting."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def enforce_rate_limit(request: Request, call_next):
    """
    Limit requests to device endpoints by client IP.

    Requests older than the configured time window are removed.
    When the limit is reached, return HTTP 429 and Retry-After.
    """

    # Leave general pages and the health endpoint accessible.
    if request.url.path.startswith("/devices"):
        client_ip = (
            request.client.host
            if request.client is not None
            else "unknown"
        )

        now = time.monotonic()
        timestamps = request_timestamps[client_ip]

        # Keep only requests inside the active time window.
        while (
            timestamps
            and now - timestamps[0] >= RATE_LIMIT_WINDOW
        ):
            timestamps.popleft()

        if len(timestamps) >= RATE_LIMIT_REQUESTS:
            retry_after = max(
                1,
                int(RATE_LIMIT_WINDOW - (now - timestamps[0])),
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": (
                        "Rate limit exceeded. "
                        f"Try again in {retry_after} seconds."
                    )
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Count the request, including unauthenticated attempts.
        timestamps.append(now)

    return await call_next(request)


# Protect all device-management endpoints with API-key authentication.
app.include_router(
    devices_router,
    dependencies=[Depends(verify_api_key)],
)


@app.get("/", tags=["General"])
def root():
    """Provide basic API information."""

    return {
        "name": "Network Management API",
        "version": app.version,
        "documentation": "/docs",
        "health": "/health",
        "authentication": "X-API-Key required for device endpoints",
    }


@app.get("/health", tags=["General"])
def health_check():
    """Check whether the API can query the database."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "unavailable",
            },
        )

    return {
        "status": "healthy",
        "database": "connected",
    }