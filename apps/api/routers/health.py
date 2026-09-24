"""Health Check Router
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from apps.api.schemas.common import success_response
from core.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint verifying database and pgvector extension status."""
    db.execute(text("SELECT 1"))
    ext_version = db.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    ).scalar_one_or_none()

    return success_response({
        "status": "ok",
        "database": "connected",
        "pgvector_version": ext_version,
    })
