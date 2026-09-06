"""Liveness endpoint."""

from fastapi import APIRouter, Depends

from app.api.deps import get_route_service
from app.config import get_settings
from app.schemas import HealthResponse
from app.services import RouteService

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(service: RouteService = Depends(get_route_service)) -> HealthResponse:
    """Report that the API is up and that seed data loaded."""
    return HealthResponse(
        status="ok",
        version=get_settings().api_version,
        routes_loaded=len(service.list_routes()),
    )
