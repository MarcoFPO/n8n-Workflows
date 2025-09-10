from fastapi import APIRouter
from .endpoints import users, health, recipes, inventory, shopping, analytics, receipts

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(shopping.router, prefix="/shopping-lists", tags=["shopping"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["receipts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

__all__ = ["api_router"]