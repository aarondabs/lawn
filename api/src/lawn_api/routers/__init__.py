from lawn_api.routers.admin import router as admin_router
from lawn_api.routers.cultural_practice import router as cultural_practice_router
from lawn_api.routers.equipment import router as equipment_router
from lawn_api.routers.irrigation_zone import router as irrigation_zone_router
from lawn_api.routers.lawn_profile import router as lawn_profile_router
from lawn_api.routers.product import router as product_router
from lawn_api.routers.rachio import router as rachio_router
from lawn_api.routers.soil_test import router as soil_test_router
from lawn_api.routers.treatment import router as treatment_router

__all__ = [
    "admin_router",
    "cultural_practice_router",
    "equipment_router",
    "irrigation_zone_router",
    "lawn_profile_router",
    "product_router",
    "rachio_router",
    "soil_test_router",
    "treatment_router",
]
