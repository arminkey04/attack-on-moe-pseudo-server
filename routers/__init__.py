# Routers package
from routers.users import router as users_router
from routers.login import router as login_router
from routers.classes import router as classes_router
from routers.functions import router as functions_router
from routers.batch import router as batch_router
from routers.coupon import router as coupon_router
from routers.config import router as config_router

__all__ = [
    "users_router",
    "login_router",
    "classes_router",
    "functions_router",
    "batch_router",
    "coupon_router",
    "config_router",
]
