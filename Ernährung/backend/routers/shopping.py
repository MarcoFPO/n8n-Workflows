from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database.connection import get_database
from ..models.schemas import (
    ShoppingList as ShoppingListSchema,
    ShoppingListCreate,
    ShoppingListUpdate,
    APIResponse
)
from ..services.shopping_service import ShoppingService

router = APIRouter()

@router.get("/shopping-lists", response_model=List[ShoppingListSchema])
async def get_shopping_lists(
    status_filter: str = "active",
    db: Session = Depends(get_database)
):
    """Get all shopping lists"""
    try:
        lists = ShoppingService.get_shopping_lists(db, status_filter)
        return lists
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching shopping lists: {str(e)}"
        )

@router.post("/shopping-lists", response_model=ShoppingListSchema)
async def create_shopping_list(
    shopping_list: ShoppingListCreate,
    db: Session = Depends(get_database)
):
    """Create new shopping list"""
    try:
        new_list = ShoppingService.create_shopping_list(db, shopping_list)
        return new_list
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating shopping list: {str(e)}"
        )