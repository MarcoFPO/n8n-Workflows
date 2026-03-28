from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from ..database.connection import get_database
from ..models.schemas import (
    Inventory as InventorySchema,
    InventoryCreate,
    InventoryUpdate,
    APIResponse
)
from ..services.inventory_service import InventoryService

router = APIRouter()

@router.get("/inventory", response_model=List[InventorySchema])
async def get_inventory(
    location: Optional[str] = None,
    expiring_days: Optional[int] = None,
    db: Session = Depends(get_database)
):
    """Get current inventory with optional filtering"""
    try:
        filters = {}
        if location:
            filters['location'] = location
        if expiring_days is not None:
            expiry_date = date.today() + timedelta(days=expiring_days)
            filters['expiring_before'] = expiry_date
        
        inventory = InventoryService.get_inventory(db, filters)
        return inventory
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching inventory: {str(e)}"
        )

@router.post("/inventory", response_model=InventorySchema)
async def add_inventory_item(
    item: InventoryCreate,
    db: Session = Depends(get_database)
):
    """Add item to inventory"""
    try:
        new_item = InventoryService.create_inventory_item(db, item)
        return new_item
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding inventory item: {str(e)}"
        )

@router.get("/inventory/expiring", response_model=List[InventorySchema])
async def get_expiring_products(
    days: int = 7,
    db: Session = Depends(get_database)
):
    """Get products expiring within specified days"""
    try:
        expiring_items = InventoryService.get_expiring_items(db, days)
        return expiring_items
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching expiring products: {str(e)}"
        )