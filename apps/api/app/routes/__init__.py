"""Route modules."""

from .internal import router as internal_router
from .jobs import router as jobs_router
from .projects import router as projects_router

__all__ = ["internal_router", "jobs_router", "projects_router"]
