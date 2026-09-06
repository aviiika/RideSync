"""Shuttle, nearby and ETA endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_shuttle_service
from app.models import Coordinate, InvalidCoordinateError
from app.schemas.shuttle import ShuttleResponse, ShuttleSnapshotResponse
from app.services import RouteNotFoundError
from app.services.shuttle_service import ShuttleService

# Spelled as a literal: Starlette renamed the constant, and the number is
# stable across versions while the name is not.
HTTP_422_UNPROCESSABLE = 422

router = APIRouter(tags=["shuttles"])

LATITUDE = Query(ge=-90, le=90, description="Rider latitude.")
LONGITUDE = Query(ge=-180, le=180, description="Rider longitude.")


def _coordinate(latitude: float, longitude: float) -> Coordinate:
    try:
        return Coordinate(latitude=latitude, longitude=longitude)
    except InvalidCoordinateError as exc:
        raise HTTPException(HTTP_422_UNPROCESSABLE, detail=str(exc)) from exc


@router.get("/shuttles", response_model=list[ShuttleResponse])
def list_shuttles(
    route_id: str | None = Query(default=None, description="Filter to one route."),
    service: ShuttleService = Depends(get_shuttle_service),
) -> list[ShuttleResponse]:
    """Every simulated shuttle currently in service."""
    try:
        shuttles = service.list_shuttles(route_id)
    except RouteNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    responses = []
    for shuttle in shuttles:
        geometry = service.geometry_for(shuttle.route_id)
        if geometry is not None:
            responses.append(ShuttleResponse.from_shuttle(shuttle, geometry.route))
    return responses


@router.get("/shuttles/nearby", response_model=list[ShuttleSnapshotResponse])
def nearby_shuttles(
    latitude: float = LATITUDE,
    longitude: float = LONGITUDE,
    route_id: str | None = Query(default=None, description="Filter to one route."),
    service: ShuttleService = Depends(get_shuttle_service),
) -> list[ShuttleSnapshotResponse]:
    """Shuttles ranked by when they reach the rider, soonest first.

    Ranked by ETA rather than by straight-line distance: the nearest shuttle
    on the map is not always the one that reaches you first.
    """
    user = _coordinate(latitude, longitude)
    try:
        snapshots = service.snapshots(user, route_id)
    except RouteNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [ShuttleSnapshotResponse.from_domain(snapshot) for snapshot in snapshots]


@router.get("/shuttles/nearest", response_model=ShuttleSnapshotResponse)
def nearest_shuttle(
    latitude: float = LATITUDE,
    longitude: float = LONGITUDE,
    route_id: str | None = Query(default=None, description="Filter to one route."),
    service: ShuttleService = Depends(get_shuttle_service),
) -> ShuttleSnapshotResponse:
    """The one shuttle a rider should wait for."""
    user = _coordinate(latitude, longitude)
    try:
        snapshot = service.nearest(user, route_id)
    except RouteNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if snapshot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no shuttles are in service")
    return ShuttleSnapshotResponse.from_domain(snapshot)


@router.get("/shuttles/{shuttle_id}", response_model=ShuttleSnapshotResponse)
def get_shuttle(
    shuttle_id: str,
    latitude: float = LATITUDE,
    longitude: float = LONGITUDE,
    service: ShuttleService = Depends(get_shuttle_service),
) -> ShuttleSnapshotResponse:
    """One shuttle, described relative to the rider."""
    shuttle = service.get_shuttle(shuttle_id)
    if shuttle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"unknown shuttle: {shuttle_id}")

    user = _coordinate(latitude, longitude)
    stop = service.nearest_stop(user, shuttle.route_id)
    return ShuttleSnapshotResponse.from_domain(service.snapshot(shuttle, user, stop))
