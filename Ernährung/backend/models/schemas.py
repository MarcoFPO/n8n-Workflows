from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal

# User Schemas
class UserBase(BaseModel):
    name: str = Field(..., max_length=100)
    email: Optional[EmailStr] = None

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    name: Optional[str] = None

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# User Settings Schemas
class UserSettingsBase(BaseModel):
    daily_calorie_goal: int = Field(..., gt=0)
    weight_goal: Optional[Decimal] = Field(None, gt=0)
    activity_level: str = Field(default="moderate")
    dietary_restrictions: Optional[List[str]] = []

class UserSettingsCreate(UserSettingsBase):
    pass

class UserSettingsUpdate(UserSettingsBase):
    daily_calorie_goal: Optional[int] = None

class UserSettings(UserSettingsBase):
    user_id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Aldi Product Schemas
class AldiProductBase(BaseModel):
    barcode: Optional[str] = None
    name: str = Field(..., max_length=200)
    brand: Optional[str] = None
    category: Optional[str] = None
    price_per_unit: Optional[Decimal] = None
    unit_type: Optional[str] = None
    unit_size: Optional[Decimal] = None
    availability: str = Field(default="regular")
    nutrition_per_100g: Optional[Dict[str, Any]] = None

class AldiProductCreate(AldiProductBase):
    pass

class AldiProductUpdate(AldiProductBase):
    name: Optional[str] = None

class AldiProduct(AldiProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Recipe Schemas
class RecipeIngredientBase(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0)
    unit: str
    is_essential: bool = True

class RecipeIngredientCreate(RecipeIngredientBase):
    pass

class RecipeIngredient(RecipeIngredientBase):
    product: AldiProduct
    
    class Config:
        from_attributes = True

class RecipeBase(BaseModel):
    name: str = Field(..., max_length=200)
    meal_type: str = Field(..., regex="^(breakfast|lunch|dinner)$")
    servings: int = Field(default=2, gt=0)
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    instructions: Optional[str] = None
    difficulty_level: int = Field(default=1, ge=1, le=5)
    estimated_calories_per_serving: Optional[int] = None
    tags: Optional[List[str]] = []

class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientCreate] = []

class RecipeUpdate(RecipeBase):
    name: Optional[str] = None
    meal_type: Optional[str] = None

class Recipe(RecipeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    ingredients: List[RecipeIngredient] = []
    
    class Config:
        from_attributes = True

# Health Metrics Schemas
class HealthMetricsBase(BaseModel):
    date: date
    weight: Optional[Decimal] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    pulse: Optional[int] = None
    notes: Optional[str] = None

class HealthMetricsCreate(HealthMetricsBase):
    pass

class HealthMetricsUpdate(HealthMetricsBase):
    date: Optional[date] = None

class HealthMetrics(HealthMetricsBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Meal Log Schemas
class MealLogBase(BaseModel):
    recipe_id: int
    meal_type: str = Field(..., regex="^(breakfast|lunch|dinner)$")
    date: date
    servings_consumed: Decimal = Field(default=1.0, gt=0)
    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None

class MealLogCreate(MealLogBase):
    pass

class MealLogUpdate(MealLogBase):
    recipe_id: Optional[int] = None
    meal_type: Optional[str] = None
    date: Optional[date] = None

class MealLog(MealLogBase):
    id: int
    user_id: int
    created_at: datetime
    recipe: Recipe
    
    class Config:
        from_attributes = True

# Inventory Schemas
class InventoryBase(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0)
    expiry_date: Optional[date] = None
    purchase_date: date = Field(default_factory=date.today)
    location: str = Field(default="Kühlschrank")

class InventoryCreate(InventoryBase):
    pass

class InventoryUpdate(InventoryBase):
    product_id: Optional[int] = None
    quantity: Optional[Decimal] = None

class Inventory(InventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    product: AldiProduct
    
    class Config:
        from_attributes = True

# Shopping List Schemas
class ShoppingListItemBase(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0)
    unit: str
    priority: int = Field(default=1, ge=1, le=3)
    is_checked: bool = False
    estimated_price: Optional[Decimal] = None

class ShoppingListItemCreate(ShoppingListItemBase):
    pass

class ShoppingListItemUpdate(ShoppingListItemBase):
    product_id: Optional[int] = None
    quantity: Optional[Decimal] = None

class ShoppingListItem(ShoppingListItemBase):
    id: int
    shopping_list_id: int
    created_at: datetime
    product: AldiProduct
    
    class Config:
        from_attributes = True

class ShoppingListBase(BaseModel):
    name: str = Field(..., max_length=100)
    list_type: str = Field(default="weekly")
    status: str = Field(default="active")

class ShoppingListCreate(ShoppingListBase):
    items: List[ShoppingListItemCreate] = []

class ShoppingListUpdate(ShoppingListBase):
    name: Optional[str] = None

class ShoppingList(ShoppingListBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[ShoppingListItem] = []
    
    class Config:
        from_attributes = True

# Recipe Rating Schemas
class RecipeRatingBase(BaseModel):
    recipe_id: int
    rating: int = Field(..., ge=1, le=5)
    complexity_rating: Optional[int] = Field(None, ge=1, le=5)
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    health_impact_rating: Optional[int] = Field(None, ge=1, le=5)
    would_cook_again: Optional[bool] = None
    feedback_text: Optional[str] = None

class RecipeRatingCreate(RecipeRatingBase):
    pass

class RecipeRatingUpdate(RecipeRatingBase):
    recipe_id: Optional[int] = None
    rating: Optional[int] = None

class RecipeRating(RecipeRatingBase):
    id: int
    user_id: int
    created_at: datetime
    recipe: Recipe
    
    class Config:
        from_attributes = True

# Receipt Scan Schemas
class ReceiptScanBase(BaseModel):
    image_path: str
    scan_status: str = Field(default="pending")
    ocr_service: Optional[str] = None
    raw_ocr_result: Optional[Dict[str, Any]] = None
    processed_items: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[Decimal] = None
    manual_corrections: Optional[Dict[str, Any]] = None

class ReceiptScanCreate(ReceiptScanBase):
    pass

class ReceiptScanUpdate(ReceiptScanBase):
    image_path: Optional[str] = None

class ReceiptScan(ReceiptScanBase):
    id: int
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ML & Analytics Schemas
class RecipeSuggestion(BaseModel):
    shared: Recipe
    individual: List[Recipe]

class DailyRecipeSuggestions(BaseModel):
    breakfast: RecipeSuggestion
    lunch: RecipeSuggestion
    dinner: RecipeSuggestion
    date: date
    user_id: int

class HealthTrend(BaseModel):
    date: date
    weight: Optional[float]
    calories_consumed: Optional[int]
    avg_rating: Optional[float]

class NutritionAnalysis(BaseModel):
    total_calories: int
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    fiber_grams: float
    date_range: str
    daily_average: Dict[str, float]

class CostAnalysis(BaseModel):
    total_cost: Decimal
    cost_per_meal: Decimal
    cost_per_day: Decimal
    date_range: str
    top_expenses: List[Dict[str, Any]]

# API Response Schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class PaginationInfo(BaseModel):
    page: int
    size: int
    total: int
    pages: int

class PaginatedResponse(BaseModel):
    items: List[Any]
    pagination: PaginationInfo