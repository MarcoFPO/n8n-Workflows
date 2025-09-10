from sqlalchemy.orm import Session
from typing import Dict, List, Any
from datetime import date, datetime
import random
from decimal import Decimal

from ..database.models import Recipe, User, RecipeRating, MealLog
from ..models.schemas import DailyRecipeSuggestions, RecipeSuggestion
from ..core.config import settings

class MLService:
    """Machine Learning service for recipe recommendations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.model = None  # Placeholder for ML model
        
    def generate_daily_suggestions(self, user_id: int, target_date: date) -> DailyRecipeSuggestions:
        """
        Generate daily recipe suggestions for a user
        For now, this is a simplified implementation that will be enhanced with ML
        """
        
        # Get user preferences and history
        user_preferences = self._get_user_preferences(user_id)
        
        # Generate suggestions for each meal type
        breakfast_suggestions = self._get_meal_suggestions("breakfast", user_id)
        lunch_suggestions = self._get_meal_suggestions("lunch", user_id) 
        dinner_suggestions = self._get_meal_suggestions("dinner", user_id)
        
        return DailyRecipeSuggestions(
            breakfast=breakfast_suggestions,
            lunch=lunch_suggestions,
            dinner=dinner_suggestions,
            date=target_date,
            user_id=user_id
        )
    
    def _get_meal_suggestions(self, meal_type: str, user_id: int) -> RecipeSuggestion:
        """Get suggestions for a specific meal type"""
        
        # Get all recipes for this meal type
        all_recipes = self.db.query(Recipe).filter(Recipe.meal_type == meal_type).all()
        
        if len(all_recipes) < 3:
            # If not enough recipes, return what we have
            shared = all_recipes[0] if all_recipes else None
            individual = all_recipes[1:3] if len(all_recipes) > 1 else []
        else:
            # Simple random selection for now
            # In production, this would use ML scoring
            selected = random.sample(all_recipes, min(3, len(all_recipes)))
            shared = selected[0]
            individual = selected[1:3]
        
        return RecipeSuggestion(
            shared=shared,
            individual=individual
        )
    
    def _get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user preferences based on ratings and meal logs"""
        
        # Get user's recipe ratings
        ratings = self.db.query(RecipeRating).filter(
            RecipeRating.user_id == user_id
        ).all()
        
        # Get user's meal history
        meal_logs = self.db.query(MealLog).filter(
            MealLog.user_id == user_id
        ).limit(50).all()
        
        # Analyze preferences (simplified)
        preferences = {
            'avg_rating': 0,
            'preferred_difficulty': 3,
            'preferred_prep_time': 30,
            'liked_tags': [],
            'disliked_tags': []
        }
        
        if ratings:
            preferences['avg_rating'] = sum(r.rating for r in ratings) / len(ratings)
        
        return preferences
    
    def calculate_recipe_score(self, recipe: Recipe, user_id: int) -> float:
        """
        Calculate ML-based score for a recipe for specific user
        This is a simplified implementation
        """
        
        base_score = 0.5  # Base score
        
        # Get user preferences
        preferences = self._get_user_preferences(user_id)
        
        # Score based on difficulty preference
        difficulty_diff = abs(recipe.difficulty_level - preferences['preferred_difficulty'])
        difficulty_score = max(0, 1.0 - (difficulty_diff * 0.2))
        
        # Score based on prep time preference  
        if recipe.prep_time:
            time_diff = abs(recipe.prep_time - preferences['preferred_prep_time'])
            time_score = max(0, 1.0 - (time_diff * 0.01))
        else:
            time_score = 0.5
        
        # Combine scores
        final_score = (base_score + difficulty_score + time_score) / 3
        
        return min(1.0, max(0.0, final_score))
    
    def update_model_with_new_ratings(self):
        """Update ML model with new rating data"""
        if not settings.ENABLE_ML:
            return False
            
        # Get recent ratings for model training
        recent_ratings = self.db.query(RecipeRating).filter(
            RecipeRating.created_at >= datetime.now().replace(day=1)  # This month
        ).all()
        
        if len(recent_ratings) < settings.ML_MIN_TRAINING_DATA:
            return False
            
        # Placeholder for actual ML model training
        # In production, this would:
        # 1. Extract features from recipes and user preferences
        # 2. Prepare training data
        # 3. Train/update the ML model
        # 4. Save model to disk
        
        return True
    
    def get_similar_recipes(self, recipe_id: int, limit: int = 5) -> List[Recipe]:
        """Get recipes similar to the given recipe"""
        
        base_recipe = self.db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not base_recipe:
            return []
        
        # Simple similarity based on meal type and difficulty
        similar_recipes = self.db.query(Recipe).filter(
            Recipe.meal_type == base_recipe.meal_type,
            Recipe.difficulty_level.between(
                base_recipe.difficulty_level - 1,
                base_recipe.difficulty_level + 1
            ),
            Recipe.id != recipe_id
        ).limit(limit).all()
        
        return similar_recipes