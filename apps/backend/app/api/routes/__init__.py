"""API routes."""

from api.routes.generations import router as generations_router
from api.routes.models import router as providers_router
from api.routes.packages import router as packages_router
from api.routes.payments import router as payments_router
from api.routes.storage import router as storage_router
from api.routes.users import router as users_router
from api.routes.webhook import router as webhook_router

__all__ = [
    "users_router",
    "providers_router",
    "generations_router",
    "packages_router",
    "payments_router",
    "storage_router",
    "webhook_router",
]
