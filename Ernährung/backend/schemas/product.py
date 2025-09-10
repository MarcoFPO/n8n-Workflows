from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

class AldiProductBase(BaseModel):
    barcode: Optional[str] = Field(None, max_length=50, description="Barcode des Produkts")
    name: str = Field(..., min_length=1, max_length=200, description="Produktname")
    brand: Optional[str] = Field(None, max_length=100, description="Marke")
    category: Optional[str] = Field(None, max_length=100, description="Kategorie")
    price_per_unit: Optional[Decimal] = Field(None, gt=0, description="Preis pro Einheit")
    unit_type: Optional[str] = Field(None, max_length=20, description="Einheitstyp (g, ml, piece)")
    unit_size: Optional[Decimal] = Field(None, gt=0, description="Einheitsgröße")
    availability: str = Field("regular", description="Verfügbarkeit")
    nutrition_per_100g: Optional[Dict[str, Any]] = Field(None, description="Nährwerte pro 100g")

class AldiProductCreate(AldiProductBase):
    pass

class AldiProductUpdate(BaseModel):
    barcode: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    price_per_unit: Optional[Decimal] = Field(None, gt=0)
    unit_type: Optional[str] = Field(None, max_length=20)
    unit_size: Optional[Decimal] = Field(None, gt=0)
    availability: Optional[str] = None
    nutrition_per_100g: Optional[Dict[str, Any]] = None

class AldiProduct(AldiProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True