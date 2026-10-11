from fastapi import APIRouter

from app.api.agents import router as agents_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(agents_router)
