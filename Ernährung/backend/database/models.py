from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, DECIMAL, Date, ForeignKey, ARRAY, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from .connection import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    health_metrics = relationship("HealthMetrics", back_populates="user")
    meal_logs = relationship("MealLog", back_populates="user")
    recipe_ratings = relationship("RecipeRating", back_populates="user")

class UserSettings(Base):
    __tablename__ = "user_settings"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    daily_calorie_goal = Column(Integer, nullable=False)
    weight_goal = Column(DECIMAL(5,2))
    activity_level = Column(String(20), default="moderate")
    dietary_restrictions = Column(ARRAY(Text))
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="settings")

class AldiProduct(Base):
    __tablename__ = "aldi_products"
    
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String(50), unique=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    brand = Column(String(100))
    category = Column(String(100), index=True)
    price_per_unit = Column(DECIMAL(8,2))
    unit_type = Column(String(20))  # 'g', 'ml', 'piece'
    unit_size = Column(DECIMAL(10,2))
    availability = Column(String(20), default="regular")  # 'regular', 'seasonal', 'special'
    nutrition_per_100g = Column(JSON)  # Calories, protein, carbs, fat, etc.
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    inventory_items = relationship("Inventory", back_populates="product")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="product")
    shopping_list_items = relationship("ShoppingListItem", back_populates="product")

class Recipe(Base):
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    meal_type = Column(String(20), nullable=False, index=True)  # breakfast, lunch, dinner
    servings = Column(Integer, default=2)
    prep_time = Column(Integer)  # minutes
    cook_time = Column(Integer)  # minutes
    instructions = Column(Text)
    difficulty_level = Column(Integer, default=1)  # 1-5
    estimated_calories_per_serving = Column(Integer)
    tags = Column(ARRAY(Text))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    ingredients = relationship("RecipeIngredient", back_populates="recipe")
    meal_logs = relationship("MealLog", back_populates="recipe")
    ratings = relationship("RecipeRating", back_populates="recipe")

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    
    recipe_id = Column(Integer, ForeignKey("recipes.id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("aldi_products.id"), primary_key=True)
    quantity = Column(DECIMAL(10,2), nullable=False)
    unit = Column(String(20), nullable=False)
    is_essential = Column(Boolean, default=True)
    
    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    product = relationship("AldiProduct", back_populates="recipe_ingredients")

class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("aldi_products.id"), nullable=False)
    quantity = Column(DECIMAL(10,2), nullable=False)
    expiry_date = Column(Date)
    purchase_date = Column(Date, default=date.today)
    location = Column(String(100), default="Kühlschrank")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    product = relationship("AldiProduct", back_populates="inventory_items")

class HealthMetrics(Base):
    __tablename__ = "health_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    weight = Column(DECIMAL(5,2))
    blood_pressure_systolic = Column(Integer)
    blood_pressure_diastolic = Column(Integer)
    pulse = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="health_metrics")

class MealLog(Base):
    __tablename__ = "meal_log"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    meal_type = Column(String(20), nullable=False)
    date = Column(Date, nullable=False, index=True)
    servings_consumed = Column(DECIMAL(3,1), default=1.0)
    rating = Column(Integer)  # 1-5 stars
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="meal_logs")
    recipe = relationship("Recipe", back_populates="meal_logs")

class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    list_type = Column(String(20), default="weekly")  # daily, weekly
    status = Column(String(20), default="active")  # active, completed, archived
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    items = relationship("ShoppingListItem", back_populates="shopping_list")

class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"
    
    id = Column(Integer, primary_key=True, index=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_lists.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("aldi_products.id"), nullable=False)
    quantity = Column(DECIMAL(10,2), nullable=False)
    unit = Column(String(20), nullable=False)
    priority = Column(Integer, default=1)  # 1-3
    is_checked = Column(Boolean, default=False)
    estimated_price = Column(DECIMAL(8,2))
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    shopping_list = relationship("ShoppingList", back_populates="items")
    product = relationship("AldiProduct", back_populates="shopping_list_items")

class RecipeRating(Base):
    __tablename__ = "recipe_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    complexity_rating = Column(Integer)  # 1-5
    satisfaction_rating = Column(Integer)  # 1-5
    health_impact_rating = Column(Integer)  # 1-5
    would_cook_again = Column(Boolean)
    feedback_text = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="recipe_ratings")
    recipe = relationship("Recipe", back_populates="ratings")

class MLTrainingData(Base):
    __tablename__ = "ml_training_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    features = Column(JSON)  # Nutritional features, complexity, etc.
    target_score = Column(DECIMAL(3,2))  # Combined score from ratings
    weight = Column(DECIMAL(5,4), default=1.0)  # Weight for training
    created_at = Column(DateTime, default=func.now())

class ReceiptScan(Base):
    __tablename__ = "receipt_scans"
    
    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(500), nullable=False)
    scan_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    ocr_service = Column(String(50))  # openai, google_vision
    raw_ocr_result = Column(JSON)
    processed_items = Column(JSON)  # Array of recognized products
    confidence_score = Column(DECIMAL(3,2))
    manual_corrections = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)