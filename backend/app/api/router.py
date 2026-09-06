"""Aggregates the individual routers into one API router."""

from fastapi import APIRouter

from app.api import health, routes, shuttles, simulation, ws

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(routes.router)
api_router.include_router(shuttles.router)
api_router.include_router(simulation.router)
api_router.include_router(ws.router)
