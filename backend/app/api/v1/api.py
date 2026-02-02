"""API v1 router aggregation."""
from fastapi import APIRouter
from app.api.v1.endpoints import topics, validation, proposals, references

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(topics.router, prefix="/topics", tags=["topics"])
api_router.include_router(validation.router, prefix="/validate", tags=["validation"])
api_router.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
api_router.include_router(references.router, prefix="/references", tags=["references"])


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
