from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..database.models import Recipe, RecipeIngredient, RecipeRating, AldiProduct
from ..models.schemas import RecipeCreate, RecipeUpdate, RecipeRatingCreate

class RecipeService:
    
    @staticmethod
    def get_recipes(db: Session, filters: Dict[str, Any] = None, skip: int = 0, limit: int = 100) -> List[Recipe]:
        """Get recipes with optional filtering"""
        query = db.query(Recipe)
        
        if filters:
            if 'meal_type' in filters:
                query = query.filter(Recipe.meal_type == filters['meal_type'])
            if 'difficulty_level' in filters:
                query = query.filter(Recipe.difficulty_level == filters['difficulty_level'])
            if 'max_prep_time' in filters:
                query = query.filter(Recipe.prep_time <= filters['max_prep_time'])
                
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_recipe_by_id(db: Session, recipe_id: int) -> Optional[Recipe]:
        """Get recipe by ID"""
        return db.query(Recipe).filter(Recipe.id == recipe_id).first()
    
    @staticmethod
    def create_recipe(db: Session, recipe: RecipeCreate) -> Recipe:
        """Create new recipe"""
        db_recipe = Recipe(
            name=recipe.name,
            meal_type=recipe.meal_type,
            servings=recipe.servings,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            instructions=recipe.instructions,
            difficulty_level=recipe.difficulty_level,
            estimated_calories_per_serving=recipe.estimated_calories_per_serving,
            tags=recipe.tags,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_recipe)
        db.commit()
        db.refresh(db_recipe)
        
        # Add ingredients
        for ingredient in recipe.ingredients:
            db_ingredient = RecipeIngredient(
                recipe_id=db_recipe.id,
                product_id=ingredient.product_id,
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                is_essential=ingredient.is_essential
            )
            db.add(db_ingredient)
        
        db.commit()
        return db_recipe
    
    @staticmethod
    def update_recipe(db: Session, recipe_id: int, recipe: RecipeUpdate) -> Recipe:
        """Update recipe"""
        db_recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if db_recipe:
            update_data = recipe.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_recipe, field, value)
            db_recipe.updated_at = datetime.now()
            db.commit()
            db.refresh(db_recipe)
        return db_recipe
    
    @staticmethod
    def delete_recipe(db: Session, recipe_id: int) -> bool:
        """Delete recipe"""
        db_recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if db_recipe:
            db.delete(db_recipe)
            db.commit()
            return True
        return False
    
    @staticmethod
    def rate_recipe(db: Session, user_id: int, recipe_id: int, rating: RecipeRatingCreate) -> RecipeRating:
        """Rate a recipe"""
        # Check if user already rated this recipe today
        existing_rating = db.query(RecipeRating).filter(
            RecipeRating.user_id == user_id,
            RecipeRating.recipe_id == recipe_id
        ).first()
        
        if existing_rating:
            # Update existing rating
            for field, value in rating.dict(exclude_unset=True).items():
                setattr(existing_rating, field, value)
            db.commit()
            db.refresh(existing_rating)
            return existing_rating
        else:
            # Create new rating
            db_rating = RecipeRating(
                user_id=user_id,
                recipe_id=recipe_id,
                rating=rating.rating,
                complexity_rating=rating.complexity_rating,
                satisfaction_rating=rating.satisfaction_rating,
                health_impact_rating=rating.health_impact_rating,
                would_cook_again=rating.would_cook_again,
                feedback_text=rating.feedback_text,
                created_at=datetime.now()
            )
            db.add(db_rating)
            db.commit()
            db.refresh(db_rating)
            return db_rating
    
    @staticmethod
    def calculate_recipe_nutrition(db: Session, recipe_id: int, servings: int = 1) -> Dict[str, Any]:
        """Calculate nutrition information for a recipe"""
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            return {}
        
        # Get ingredients with product nutrition data
        ingredients = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()
        
        total_nutrition = {
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0,
            'fiber': 0
        }
        
        for ingredient in ingredients:
            product = db.query(AldiProduct).filter(
                AldiProduct.id == ingredient.product_id
            ).first()
            
            if product and product.nutrition_per_100g:
                # Calculate nutrition based on ingredient quantity
                quantity_factor = float(ingredient.quantity) / 100.0  # Per 100g
                nutrition = product.nutrition_per_100g
                
                total_nutrition['calories'] += nutrition.get('calories', 0) * quantity_factor
                total_nutrition['protein'] += nutrition.get('protein', 0) * quantity_factor
                total_nutrition['carbs'] += nutrition.get('carbs', 0) * quantity_factor
                total_nutrition['fat'] += nutrition.get('fat', 0) * quantity_factor
                total_nutrition['fiber'] += nutrition.get('fiber', 0) * quantity_factor
        
        # Adjust for servings
        serving_factor = servings / recipe.servings if recipe.servings > 0 else 1
        for key in total_nutrition:
            total_nutrition[key] = round(total_nutrition[key] * serving_factor, 2)
        
        return {
            'recipe_id': recipe_id,
            'servings': servings,
            'nutrition': total_nutrition,
            'calories_per_serving': round(total_nutrition['calories'] / servings, 2) if servings > 0 else 0
        }