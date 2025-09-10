from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class RecipeIngredientBase(BaseModel):
    product_id: int = Field(..., description="Produkt ID")
    quantity: Decimal = Field(..., gt=0, description="Menge")
    unit: str = Field(..., min_length=1, max_length=20, description="Einheit")
    is_essential: bool = Field(True, description="Ist die Zutat essentiell?")

class RecipeIngredientCreate(RecipeIngredientBase):
    pass

class RecipeIngredient(RecipeIngredientBase):
    recipe_id: int
    
    class Config:
        from_attributes = True

class RecipeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Name des Rezepts")
    meal_type: str = Field(..., description="Mahlzeitentyp (breakfast, lunch, dinner)")
    servings: int = Field(2, gt=0, le=20, description="Anzahl Portionen")
    prep_time: Optional[int] = Field(None, ge=0, le=300, description="Vorbereitungszeit in Minuten")
    cook_time: Optional[int] = Field(None, ge=0, le=600, description="Kochzeit in Minuten")
    instructions: Optional[str] = Field(None, description="Kochanweisungen")
    difficulty_level: int = Field(1, ge=1, le=5, description="Schwierigkeitsgrad 1-5")
    estimated_calories_per_serving: Optional[int] = Field(None, ge=0, le=2000, description="Geschätzte Kalorien pro Portion")
    tags: List[str] = Field(default_factory=list, description="Tags für das Rezept")

class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientCreate] = Field(default_factory=list, description="Zutaten")

class RecipeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    meal_type: Optional[str] = None
    servings: Optional[int] = Field(None, gt=0, le=20)
    prep_time: Optional[int] = Field(None, ge=0, le=300)
    cook_time: Optional[int] = Field(None, ge=0, le=600)
    instructions: Optional[str] = None
    difficulty_level: Optional[int] = Field(None, ge=1, le=5)
    estimated_calories_per_serving: Optional[int] = Field(None, ge=0, le=2000)
    tags: Optional[List[str]] = None

class Recipe(RecipeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    ingredients: List[RecipeIngredient] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class RecipeRatingBase(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Bewertung 1-5")
    complexity_rating: Optional[int] = Field(None, ge=1, le=5, description="Komplexitätsbewertung 1-5")
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5, description="Zufriedenheitsbewertung 1-5")
    health_impact_rating: Optional[int] = Field(None, ge=1, le=5, description="Gesundheitsbewertung 1-5")
    would_cook_again: Optional[bool] = Field(None, description="Würde es wieder kochen?")
    feedback_text: Optional[str] = Field(None, description="Feedback Text")

class RecipeRatingCreate(RecipeRatingBase):
    recipe_id: int = Field(..., description="Rezept ID")

class RecipeRating(RecipeRatingBase):
    id: int
    user_id: int
    recipe_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class RecipeSuggestion(BaseModel):
    breakfast: Dict[str, Any] = Field(..., description="Frühstücksvorschläge")
    lunch: Dict[str, Any] = Field(..., description="Mittagsvorschläge")
    dinner: Dict[str, Any] = Field(..., description="Abendvorschläge")
    
    class Config:
        from_attributes = True