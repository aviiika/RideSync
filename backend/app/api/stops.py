"""Stop endpoints, including the departure board."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_route_service, get_shuttle_service
from app.models import Coordinate, InvalidCoordinateError
from app.schemas import StopResponse
from app.schemas.shuttle import ShuttleSnapshotResponse
from app.services import RouteNotFoundError, RouteService, StopNotFoundError
from app.services.shuttle_service import ShuttleService

router = APIRouter(tags=["stops"])

HTTP_422_UNPROCESSABLE = 422


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


@router.get("/stops/{stop_id}/arrivals", response_model=list[ShuttleSnapshotResponse])
def arrivals(
    stop_id: str,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    service: ShuttleService = Depends(get_shuttle_service),
) -> list[ShuttleSnapshotResponse]:
    """What is due at this stop, soonest first.

    Only shuttles whose route calls here can arrive, however near anything
    else happens to be.
    """
    user: Coordinate | None = None
    if latitude is not None and longitude is not None:
        try:
            user = Coordinate(latitude=latitude, longitude=longitude)
        except InvalidCoordinateError as exc:
            raise HTTPException(HTTP_422_UNPROCESSABLE, detail=str(exc)) from exc

    try:
        snapshots = service.arrivals_at(stop_id, user)
    except StopNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [ShuttleSnapshotResponse.from_domain(snapshot) for snapshot in snapshots]
