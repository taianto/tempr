from fastapi import APIRouter

from app.api.agents import router as agents_router
from app.api.classifications import router as classifications_router
from app.api.evaluations import router as evaluations_router
from app.api.test_suites import router as test_suites_router
from app.api.traces import router as traces_router
from app.api.versions import router as versions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(agents_router)
api_router.include_router(versions_router)
api_router.include_router(classifications_router)
api_router.include_router(test_suites_router)
api_router.include_router(traces_router)
api_router.include_router(evaluations_router)
