from fastapi import APIRouter

from app.api.agents import router as agents_router
from app.api.classifications import router as classifications_router
from app.api.versions import router as versions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(agents_router)
api_router.include_router(versions_router)
api_router.include_router(classifications_router)
