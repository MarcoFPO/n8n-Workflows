from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class InventoryBase(BaseModel):
    product_id: int = Field(..., description="Produkt ID")
    quantity: Decimal = Field(..., gt=0, description="Menge")
    expiry_date: Optional[date] = Field(None, description="Ablaufdatum")
    purchase_date: Optional[date] = Field(None, description="Kaufdatum")
    location: str = Field("Kühlschrank", description="Lagerort")

class InventoryCreate(InventoryBase):
    pass

class InventoryUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(None, gt=0)
    expiry_date: Optional[date] = None
    purchase_date: Optional[date] = None
    location: Optional[str] = None

class Inventory(InventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ExpiringItem(BaseModel):
    inventory_id: int
    product_name: str
    quantity: Decimal
    unit_type: str
    expiry_date: date
    days_until_expiry: int
    location: str
    
    class Config:
        from_attributes = True