from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class ShoppingListItemBase(BaseModel):
    product_id: int = Field(..., description="Produkt ID")
    quantity: Decimal = Field(..., gt=0, description="Menge")
    unit: str = Field(..., min_length=1, max_length=20, description="Einheit")
    priority: int = Field(1, ge=1, le=3, description="Priorität 1-3")
    is_checked: bool = Field(False, description="Ist abgehakt?")
    estimated_price: Optional[Decimal] = Field(None, gt=0, description="Geschätzter Preis")

class ShoppingListItemCreate(ShoppingListItemBase):
    pass

class ShoppingListItemUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    priority: Optional[int] = Field(None, ge=1, le=3)
    is_checked: Optional[bool] = None
    estimated_price: Optional[Decimal] = Field(None, gt=0)

class ShoppingListItem(ShoppingListItemBase):
    id: int
    shopping_list_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ShoppingListBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name der Einkaufsliste")
    list_type: str = Field("weekly", description="Listentyp (daily, weekly)")
    status: str = Field("active", description="Status (active, completed, archived)")

class ShoppingListCreate(ShoppingListBase):
    items: List[ShoppingListItemCreate] = Field(default_factory=list, description="Artikel")

class ShoppingListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    list_type: Optional[str] = None
    status: Optional[str] = None

class ShoppingList(ShoppingListBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[ShoppingListItem] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class ShoppingListSummary(BaseModel):
    total_items: int
    checked_items: int
    estimated_total_price: Optional[Decimal]
    completion_percentage: float
    
    class Config:
        from_attributes = True