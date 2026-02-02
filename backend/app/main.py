"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from collections import defaultdict
from time import time

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import init_db, close_db

settings = get_settings()
logger = get_logger(__name__)


# =============================================================================
# Rate Limiter (Token Bucket Algorithm)
# =============================================================================
class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int = 100, per: int = 60):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum requests allowed
            per: Time window in seconds
        """
        self.rate = rate
        self.per = per
        self._tokens: dict[str, float] = defaultdict(float)
        self._last_update: dict[str, float] = defaultdict(float)

    def _get_token_count(self, key: str) -> float:
        """Get current token count for a key."""
        now = time()
        elapsed = now - self._last_update[key]

        # Refill tokens based on elapsed time
        self._tokens[key] = min(
            self.rate,
            self._tokens[key] + elapsed * (self.rate / self.per)
        )
        self._last_update[key] = now

        return self._tokens[key]

    def _consume_token(self, key: str, tokens: float = 1.0) -> bool:
        """
        Consume tokens from the bucket.

        Args:
            key: API key or identifier
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if rate limited
        """
        if self._get_token_count(key) >= tokens:
            self._tokens[key] -= tokens
            return True
        return False

    def is_allowed(self, key: str, tokens: float = 1.0) -> bool:
        """Check if request is allowed."""
        return self._consume_token(key, tokens)

    def get_retry_after(self, key: str) -> float:
        """Get seconds until next token is available."""
        current = self._get_token_count(key)
        if current >= 1.0:
            return 0.0
        # Calculate time to refill 1 token
        return (1.0 - current) * (self.per / self.rate)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(rate=100, per=60)
    return _rate_limiter


# =============================================================================
# Security Middleware
# =============================================================================
async def api_key_middleware(request: Request, call_next):
    """
    API Key authentication middleware.

    Validates X-API-Key header for POST/PUT/DELETE requests.
    """
    # Skip auth for GET, OPTIONS, HEAD requests
    if request.method in ["GET", "OPTIONS", "HEAD"]:
        return await call_next(request)

    # Skip auth for health check and docs
    if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    # Check API key header
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        logger.warning("api_key_missing", path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "API key is required", "detail": "X-API-Key header is missing"},
        )

    # TODO: Validate against stored keys with SHA-256 hashing
    # For now, accept any non-empty key (development mode)
    if not api_key or len(api_key) < 10:
        logger.warning("api_key_invalid", path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid API key", "detail": "API key must be at least 10 characters"},
        )

    return await call_next(request)


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.

    Enforces rate limit of 100 requests per minute per API key.
    """
    # Get API key or use IP address as fallback
    api_key = request.headers.get("X-API-Key", request.client.host if request.client else "anonymous")

    rate_limiter = get_rate_limiter()

    if not rate_limiter.is_allowed(api_key):
        retry_after = rate_limiter.get_retry_after(api_key)
        logger.warning(
            "rate_limit_exceeded",
            api_key=api_key[:8] + "...",
            path=request.url.path,
            retry_after=retry_after,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "detail": f"Rate limit exceeded. Retry after {retry_after:.1f} seconds",
            },
            headers={"Retry-After": str(int(retry_after))},
        )

    return await call_next(request)


# =============================================================================
# Application Lifespan
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("application_startup", version=settings.app_version)

    # Initialize database
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))

    # Create data directories
    for dir_path in ["./data", "./data/uploads", "./data/chromadb"]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    logger.info("application_shutdown")
    await close_db()


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware (order matters - these must be before route handlers)
app.middleware("http")(api_key_middleware)
app.middleware("http")(rate_limit_middleware)

# Include v1 API router
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
