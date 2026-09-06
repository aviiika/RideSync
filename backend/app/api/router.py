"""Aggregates the individual routers into one API router."""

from fastapi import APIRouter

from app.api import health, routes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(routes.router)
