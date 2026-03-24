from fastapi import APIRouter

from aces_backend.api.routes import health, matches

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(matches.router)
