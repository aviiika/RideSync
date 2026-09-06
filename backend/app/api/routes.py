"""Route and stop endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_route_service
from app.schemas import RouteResponse, StopResponse
from app.services import RouteNotFoundError, RouteService

router = APIRouter(tags=["network"])


@router.get("/routes", response_model=list[RouteResponse])
def list_routes(service: RouteService = Depends(get_route_service)) -> list[RouteResponse]:
    """Every route, including geometry and stops."""
    return [RouteResponse.from_domain(route) for route in service.list_routes()]


@router.get("/routes/{route_id}", response_model=RouteResponse)
def get_route(
    route_id: str,
    service: RouteService = Depends(get_route_service),
) -> RouteResponse:
    """One route by id."""
    try:
        return RouteResponse.from_domain(service.get_route(route_id))
    except RouteNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/stops", response_model=list[StopResponse])
def list_stops(
    route_id: str | None = Query(default=None, description="Filter to one route."),
    service: RouteService = Depends(get_route_service),
) -> list[StopResponse]:
    """Every stop, optionally filtered to a single route."""
    try:
        stops = service.list_stops(route_id)
    except RouteNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [StopResponse.from_domain(stop) for stop in stops]
