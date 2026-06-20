"""
MatEnergy-ML API v1 — root router.

Aggregates all domain routers under the /api/v1 prefix (set in main.py).
"""
from fastapi import APIRouter

from app.api.v1.auth_routes import router as auth_router
from app.api.v1.dashboard_routes import router as dashboard_router
from app.api.v1.dataset_routes import router as dataset_router
from app.api.v1.descriptor_routes import router as descriptor_router
from app.api.v1.material_routes import router as material_router
from app.api.v1.model_routes import router as model_router
from app.api.v1.prediction_routes import router as prediction_router
from app.api.v1.ranking_routes import router as ranking_router
from app.api.v1.user_routes import router as user_router
from app.api.v1.report_routes import router as report_router
from app.api.v1.explore_routes import router as explore_router
from app.api.v1.dft_routes import router as dft_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(user_router)
router.include_router(dataset_router)
router.include_router(material_router)
router.include_router(model_router)
router.include_router(prediction_router)
router.include_router(ranking_router)
router.include_router(dashboard_router)
router.include_router(descriptor_router)
router.include_router(report_router)
router.include_router(explore_router)
router.include_router(dft_router)

__all__ = ["router"]
