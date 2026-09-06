"""HTTP layer. Routers translate between services and Pydantic schemas only."""

from app.api.router import api_router

__all__ = ["api_router"]
