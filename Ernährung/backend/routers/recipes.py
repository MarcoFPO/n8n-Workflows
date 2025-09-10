from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from ..database.connection import get_database
from ..database.models import Recipe, RecipeRating
from ..models.schemas import (
    Recipe as RecipeSchema,
    RecipeCreate,
    RecipeUpdate,
    DailyRecipeSuggestions,
    RecipeRating as RecipeRatingSchema,
    RecipeRatingCreate,
    APIResponse
)
from ..services.recipe_service import RecipeService
from ..services.ml_service import MLService

router = APIRouter()

@router.get("/recipes", response_model=List[RecipeSchema])
async def get_recipes(
    meal_type: Optional[str] = None,
    difficulty_level: Optional[int] = None,
    max_prep_time: Optional[int] = None,
    tags: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_database)
):
    """Get recipes with filtering options"""
    try:
        filters = {}
        if meal_type:
            filters['meal_type'] = meal_type
        if difficulty_level:
            filters['difficulty_level'] = difficulty_level
        if max_prep_time:
            filters['max_prep_time'] = max_prep_time
        if tags:
            filters['tags'] = tags.split(',')
        
        recipes = RecipeService.get_recipes(db, filters=filters, skip=skip, limit=limit)
        return recipes
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching recipes: {str(e)}"
        )

@router.get("/recipes/{recipe_id}", response_model=RecipeSchema)
async def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_database)
):
    """Get recipe by ID"""
    try:
        recipe = RecipeService.get_recipe_by_id(db, recipe_id)
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found"
            )
        return recipe
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching recipe: {str(e)}"
        )

@router.post("/recipes", response_model=RecipeSchema)
async def create_recipe(
    recipe: RecipeCreate,
    db: Session = Depends(get_database)
):
    """Create new recipe"""
    try:
        new_recipe = RecipeService.create_recipe(db, recipe)
        return new_recipe
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating recipe: {str(e)}"
        )

@router.put("/recipes/{recipe_id}", response_model=RecipeSchema)
async def update_recipe(
    recipe_id: int,
    recipe: RecipeUpdate,
    db: Session = Depends(get_database)
):
    """Update recipe"""
    try:
        existing_recipe = RecipeService.get_recipe_by_id(db, recipe_id)
        if not existing_recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found"
            )
        
        updated_recipe = RecipeService.update_recipe(db, recipe_id, recipe)
        return updated_recipe
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating recipe: {str(e)}"
        )

@router.delete("/recipes/{recipe_id}", response_model=APIResponse)
async def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_database)
):
    """Delete recipe"""
    try:
        existing_recipe = RecipeService.get_recipe_by_id(db, recipe_id)
        if not existing_recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found"
            )
        
        RecipeService.delete_recipe(db, recipe_id)
        return APIResponse(
            success=True,
            message="Recipe deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting recipe: {str(e)}"
        )

@router.get("/recipes/suggestions/{user_id}", response_model=DailyRecipeSuggestions)
async def get_daily_suggestions(
    user_id: int,
    suggestion_date: Optional[str] = None,
    db: Session = Depends(get_database)
):
    """Get ML-based daily recipe suggestions for user"""
    try:
        target_date = date.fromisoformat(suggestion_date) if suggestion_date else date.today()
        
        # Check if user exists
        from ..services.user_service import UserService
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get ML suggestions
        ml_service = MLService(db)
        suggestions = ml_service.generate_daily_suggestions(user_id, target_date)
        
        return suggestions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recipe suggestions: {str(e)}"
        )

@router.post("/recipes/{recipe_id}/rate", response_model=RecipeRatingSchema)
async def rate_recipe(
    recipe_id: int,
    user_id: int,
    rating: RecipeRatingCreate,
    db: Session = Depends(get_database)
):
    """Rate a recipe"""
    try:
        # Check if recipe exists
        recipe = RecipeService.get_recipe_by_id(db, recipe_id)
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found"
            )
        
        # Check if user exists
        from ..services.user_service import UserService
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create or update rating
        new_rating = RecipeService.rate_recipe(db, user_id, recipe_id, rating)
        return new_rating
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rating recipe: {str(e)}"
        )

@router.get("/recipes/{recipe_id}/nutrition")
async def get_recipe_nutrition(
    recipe_id: int,
    servings: int = 1,
    db: Session = Depends(get_database)
):
    """Get detailed nutrition information for a recipe"""
    try:
        recipe = RecipeService.get_recipe_by_id(db, recipe_id)
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found"
            )
        
        nutrition = RecipeService.calculate_recipe_nutrition(db, recipe_id, servings)
        return nutrition
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating recipe nutrition: {str(e)}"
        )