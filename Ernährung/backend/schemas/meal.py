from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class MealLogBase(BaseModel):
    recipe_id: int = Field(..., description="Rezept ID")
    meal_type: str = Field(..., description="Mahlzeitentyp (breakfast, lunch, dinner)")
    date: date = Field(..., description="Datum der Mahlzeit")
    servings_consumed: Decimal = Field(1.0, gt=0, le=10, description="Konsumierte Portionen")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Bewertung 1-5")
    notes: Optional[str] = Field(None, description="Notizen")

class MealLogCreate(MealLogBase):
    pass

class MealLogUpdate(BaseModel):
    servings_consumed: Optional[Decimal] = Field(None, gt=0, le=10)
    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None

class MealLog(MealLogBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class DailyNutrition(BaseModel):
    date: date
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    meals: List[MealLog]
    
    class Config:
        from_attributes = True