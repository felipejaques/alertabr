from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "alertabr-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
