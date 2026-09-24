"""API Routers Export
"""

from apps.api.routers.entities import router as entities_router
from apps.api.routers.graph import router as graph_router
from apps.api.routers.health import router as health_router
from apps.api.routers.projects import router as projects_router
from apps.api.routers.relations import router as relations_router

__all__ = [
    "health_router",
    "projects_router",
    "entities_router",
    "relations_router",
    "graph_router",
]
