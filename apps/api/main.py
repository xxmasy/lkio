"""FastAPI Application Main Entrypoint
"""

import sys
import uuid
from pathlib import Path

# Ensure workspace root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from apps.api.routers import (
    entities_router,
    graph_router,
    health_router,
    projects_router,
    relations_router,
)
from apps.api.schemas.common import error_response, success_response
from core.db.session import get_db
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from core.models.source import Source

app = FastAPI(
    title="Local Knowledge Intelligence OS (LKIO) API",
    description="Knowledge Core API for Local Knowledge Intelligence Operating System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for local frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# Standardized error handlers adhering to Section 12
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "validation_error",
        404: "not_found",
        409: "conflict",
        500: "internal_error",
    }
    error_code = code_map.get(exc.status_code, "http_error")
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            code=error_code,
            message=str(exc.detail),
            request_id=req_id,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response(
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
            request_id=req_id,
        ),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code="internal_error",
            message=str(exc),
            request_id=req_id,
        ),
    )


# System Overview API according to Section 13
@app.get("/api/v1/overview", tags=["Overview"])
def get_system_overview(db: Session = Depends(get_db)):
    """Summary metrics for the Overview dashboard."""
    project_count = db.scalar(select(func.count(Project.id))) or 0
    frontend_count = db.scalar(select(func.count(Project.id)).where(Project.kind == "frontend")) or 0
    backend_count = db.scalar(select(func.count(Project.id)).where(Project.kind == "backend")) or 0
    entity_count = db.scalar(select(func.count(Entity.id))) or 0
    relation_count = db.scalar(select(func.count(Relation.id))) or 0
    source_count = db.scalar(select(func.count(Source.id))) or 0

    return success_response({
        "project_count": project_count,
        "frontend_count": frontend_count,
        "backend_count": backend_count,
        "entity_count": entity_count,
        "relation_count": relation_count,
        "source_count": source_count,
    })


# Register v1 routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(entities_router, prefix="/api/v1")
app.include_router(relations_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
