"""Route modules."""

from .instructions import router as instructions_router
from .internal import router as internal_router
from .jobs import router as jobs_router
from .projects import router as projects_router

__all__ = ["instructions_router", "internal_router", "jobs_router", "projects_router"]
