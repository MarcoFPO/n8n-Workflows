from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import date
from database import get_db
from models.database import (
    Recipe as RecipeModel, 
    RecipeIngredient as RecipeIngredientModel,
    RecipeRating as RecipeRatingModel,
    User as UserModel
)
from schemas.recipe import Recipe, RecipeCreate, RecipeUpdate, RecipeRating, RecipeRatingCreate
from services.ml_service import RecipeOptimizer
from services.nutrition_service import NutritionCalculator
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ML Service Instance
recipe_optimizer = RecipeOptimizer()
nutrition_calculator = NutritionCalculator()

@router.get("/suggestions/{user_id}", response_model=Dict[str, Any])
async def get_daily_suggestions(
    user_id: int,
    suggestion_date: date = Query(default_factory=date.today, description="Datum für Vorschläge"),
    db: Session = Depends(get_db)
):
    """Tagesvorschläge für Rezepte (ML-basiert)."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        suggestions = await recipe_optimizer.generate_daily_suggestions(
            user_id=user_id,
            date=suggestion_date.isoformat(),
            db=db
        )
        
        return suggestions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating suggestions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=List[Recipe])
async def get_recipes(
    skip: int = Query(0, ge=0, description="Anzahl zu überspringen"),
    limit: int = Query(50, ge=1, le=100, description="Maximale Anzahl"),
    meal_type: Optional[str] = Query(None, description="Mahlzeitentyp Filter"),
    category: Optional[str] = Query(None, description="Kategorie Filter"),
    db: Session = Depends(get_db)
):
    """Alle Rezepte abrufen."""
    try:
        query = db.query(RecipeModel).options(joinedload(RecipeModel.ingredients))
        
        if meal_type:
            query = query.filter(RecipeModel.meal_type == meal_type)
        
        if category:
            query = query.filter(RecipeModel.tags.contains([category]))
        
        recipes = query.offset(skip).limit(limit).all()
        return recipes
    except Exception as e:
        logger.error(f"Error getting recipes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Rezeptdetails abrufen."""
    try:
        recipe = db.query(RecipeModel).options(
            joinedload(RecipeModel.ingredients)
        ).filter(RecipeModel.id == recipe_id).first()
        
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        return recipe
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recipe {recipe_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", response_model=Recipe, status_code=status.HTTP_201_CREATED)
async def create_recipe(recipe: RecipeCreate, db: Session = Depends(get_db)):
    """Neues Rezept erstellen."""
    try:
        # Erstelle Rezept ohne Zutaten
        recipe_data = recipe.dict(exclude={'ingredients'})
        db_recipe = RecipeModel(**recipe_data)
        
        db.add(db_recipe)
        db.commit()
        db.refresh(db_recipe)
        
        # Füge Zutaten hinzu
        for ingredient in recipe.ingredients:
            ingredient_data = ingredient.dict()
            ingredient_data['recipe_id'] = db_recipe.id
            db_ingredient = RecipeIngredientModel(**ingredient_data)
            db.add(db_ingredient)
        
        db.commit()
        
        # Lade das komplette Rezept mit Zutaten
        db.refresh(db_recipe)
        return db_recipe
    except Exception as e:
        logger.error(f"Error creating recipe: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{recipe_id}", response_model=Recipe)
async def update_recipe(recipe_id: int, recipe: RecipeUpdate, db: Session = Depends(get_db)):
    """Rezept aktualisieren."""
    try:
        db_recipe = db.query(RecipeModel).filter(RecipeModel.id == recipe_id).first()
        if not db_recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        update_data = recipe.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_recipe, field, value)
        
        db.commit()
        db.refresh(db_recipe)
        return db_recipe
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating recipe {recipe_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{recipe_id}/rate", response_model=RecipeRating, status_code=status.HTTP_201_CREATED)
async def rate_recipe(
    recipe_id: int,
    user_id: int,
    rating: RecipeRatingCreate,
    db: Session = Depends(get_db)
):
    """Rezept bewerten."""
    try:
        # Prüfe ob Rezept und User existieren
        recipe = db.query(RecipeModel).filter(RecipeModel.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prüfe ob bereits eine Bewertung existiert
        existing_rating = db.query(RecipeRatingModel).filter(
            RecipeRatingModel.user_id == user_id,
            RecipeRatingModel.recipe_id == recipe_id
        ).first()
        
        if existing_rating:
            # Aktualisiere existierende Bewertung
            update_data = rating.dict(exclude={'recipe_id'})
            for field, value in update_data.items():
                setattr(existing_rating, field, value)
            db.commit()
            db.refresh(existing_rating)
            return existing_rating
        else:
            # Erstelle neue Bewertung
            rating_data = rating.dict()
            rating_data['user_id'] = user_id
            rating_data['recipe_id'] = recipe_id
            db_rating = RecipeRatingModel(**rating_data)
            
            db.add(db_rating)
            db.commit()
            db.refresh(db_rating)
            
            # Update ML training data asynchronously
            await recipe_optimizer.update_training_data(user_id, recipe_id, db_rating, db)
            
            return db_rating
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rating recipe {recipe_id} by user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{recipe_id}/ratings", response_model=List[RecipeRating])
async def get_recipe_ratings(recipe_id: int, db: Session = Depends(get_db)):
    """Bewertungen für ein Rezept abrufen."""
    try:
        recipe = db.query(RecipeModel).filter(RecipeModel.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        ratings = db.query(RecipeRatingModel).filter(
            RecipeRatingModel.recipe_id == recipe_id
        ).all()
        
        return ratings
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ratings for recipe {recipe_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{recipe_id}/nutrition", response_model=Dict[str, Any])
async def get_recipe_nutrition(recipe_id: int, servings: int = 1, db: Session = Depends(get_db)):
    """Nährwerte für ein Rezept berechnen."""
    try:
        recipe = db.query(RecipeModel).options(
            joinedload(RecipeModel.ingredients)
        ).filter(RecipeModel.id == recipe_id).first()
        
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        nutrition = await nutrition_calculator.calculate_recipe_nutrition(recipe, servings, db)
        return nutrition
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating nutrition for recipe {recipe_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Rezept löschen."""
    try:
        recipe = db.query(RecipeModel).filter(RecipeModel.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        # Lösche zuerst die Zutaten
        db.query(RecipeIngredientModel).filter(RecipeIngredientModel.recipe_id == recipe_id).delete()
        
        # Lösche das Rezept
        db.delete(recipe)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting recipe {recipe_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")