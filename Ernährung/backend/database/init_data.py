from sqlalchemy.orm import Session
from models.database import User, UserSetting, AldiProduct, Recipe, RecipeIngredient
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)

def create_sample_data(db: Session):
    """Create sample data for the application."""
    try:
        # Check if data already exists
        if db.query(User).first():
            logger.info("Sample data already exists, skipping initialization")
            return
        
        # Create sample users
        user1 = User(name="Person 1")
        user2 = User(name="Person 2")
        db.add(user1)
        db.add(user2)
        db.commit()
        
        # Create user settings
        settings1 = UserSetting(
            user_id=user1.id,
            daily_calorie_goal=2000,
            weight_goal=Decimal("75.0"),
            activity_level="moderate",
            dietary_restrictions=[]
        )
        settings2 = UserSetting(
            user_id=user2.id,
            daily_calorie_goal=1800,
            weight_goal=Decimal("65.0"),
            activity_level="light",
            dietary_restrictions=["vegetarian"]
        )
        db.add(settings1)
        db.add(settings2)
        
        # Create sample Aldi products
        products = [
            AldiProduct(
                barcode="4088600212777",
                name="Bio Vollkornbrot",
                brand="Simply Nature",
                category="Backwaren",
                price_per_unit=Decimal("1.99"),
                unit_type="g",
                unit_size=Decimal("500"),
                availability="regular",
                nutrition_per_100g={
                    "calories": 245,
                    "protein": 8.5,
                    "carbs": 45.0,
                    "fat": 3.0,
                    "fiber": 7.0,
                    "sugar": 2.5,
                    "salt": 1.2
                }
            ),
            AldiProduct(
                barcode="4088600345678",
                name="Bio Eier Freiland",
                brand="Simply Nature",
                category="Milchprodukte",
                price_per_unit=Decimal("2.49"),
                unit_type="piece",
                unit_size=Decimal("6"),
                availability="regular",
                nutrition_per_100g={
                    "calories": 155,
                    "protein": 13.0,
                    "carbs": 1.0,
                    "fat": 11.0,
                    "fiber": 0.0,
                    "sugar": 1.0,
                    "salt": 0.3
                }
            ),
            AldiProduct(
                barcode="4088600456789",
                name="Bio Bananen",
                brand="Simply Nature",
                category="Obst",
                price_per_unit=Decimal("1.79"),
                unit_type="kg",
                unit_size=Decimal("1"),
                availability="regular",
                nutrition_per_100g={
                    "calories": 89,
                    "protein": 1.1,
                    "carbs": 23.0,
                    "fat": 0.3,
                    "fiber": 2.6,
                    "sugar": 12.0,
                    "salt": 0.001
                }
            ),
            AldiProduct(
                barcode="4088600567890",
                name="Bio Haferflocken",
                brand="Simply Nature",
                category="Müsli & Cerealien",
                price_per_unit=Decimal("0.89"),
                unit_type="g",
                unit_size=Decimal("500"),
                availability="regular",
                nutrition_per_100g={
                    "calories": 368,
                    "protein": 13.5,
                    "carbs": 58.7,
                    "fat": 7.0,
                    "fiber": 10.0,
                    "sugar": 0.7,
                    "salt": 0.02
                }
            ),
            AldiProduct(
                barcode="4088600678901",
                name="Bio Milch 3,5%",
                brand="Simply Nature",
                category="Milchprodukte",
                price_per_unit=Decimal("1.09"),
                unit_type="ml",
                unit_size=Decimal("1000"),
                availability="regular",
                nutrition_per_100g={
                    "calories": 64,
                    "protein": 3.4,
                    "carbs": 4.8,
                    "fat": 3.5,
                    "fiber": 0.0,
                    "sugar": 4.8,
                    "salt": 0.12
                }
            ),
            AldiProduct(
                barcode="4088600789012",
                name="Bio Hähnchenbrust",
                brand="Simply Nature",
                category="Fleisch",
                price_per_unit=Decimal("5.99"),
                unit_type="g",
                unit_size=Decimal("400"),
                availability="regular",
                nutrition_per_100g={
                    "calories": 165,
                    "protein": 31.0,
                    "carbs": 0.0,
                    "fat": 3.6,
                    "fiber": 0.0,
                    "sugar": 0.0,
                    "salt": 0.07
                }
            ),
            AldiProduct(
                barcode="4088600890123",
                name="Bio Brokkoli",
                brand="Simply Nature",
                category="Gemüse",
                price_per_unit=Decimal("1.49"),
                unit_type="g",
                unit_size=Decimal("500"),
                availability="regular",
                nutrition_per_100g={
                    "calories": 34,
                    "protein": 2.8,
                    "carbs": 6.6,
                    "fat": 0.4,
                    "fiber": 2.6,
                    "sugar": 1.5,
                    "salt": 0.03
                }
            )
        ]
        
        for product in products:
            db.add(product)
        
        db.commit()
        
        # Create sample recipes
        recipes = [
            Recipe(
                name="Gesundes Frühstück Porridge",
                meal_type="breakfast",
                servings=2,
                prep_time=5,
                cook_time=10,
                instructions="1. Haferflocken mit Milch aufkochen\n2. Bananen schneiden und untermischen\n3. Mit Honig süßen",
                difficulty_level=1,
                estimated_calories_per_serving=320,
                tags=["gesund", "schnell", "vegetarisch"]
            ),
            Recipe(
                name="Hähnchen mit Brokkoli",
                meal_type="dinner",
                servings=2,
                prep_time=15,
                cook_time=25,
                instructions="1. Hähnchenbrust würzen und anbraten\n2. Brokkoli dämpfen\n3. Zusammen servieren",
                difficulty_level=2,
                estimated_calories_per_serving=280,
                tags=["protein", "low-carb", "gesund"]
            ),
            Recipe(
                name="Vollkornbrot mit Ei",
                meal_type="breakfast",
                servings=1,
                prep_time=5,
                cook_time=8,
                instructions="1. Brot toasten\n2. Ei braten oder kochen\n3. Zusammen servieren",
                difficulty_level=1,
                estimated_calories_per_serving=380,
                tags=["schnell", "protein", "sättigend"]
            )
        ]
        
        for recipe in recipes:
            db.add(recipe)
        
        db.commit()
        
        # Create recipe ingredients
        # Porridge Recipe
        porridge = db.query(Recipe).filter(Recipe.name == "Gesundes Frühstück Porridge").first()
        haferflocken = db.query(AldiProduct).filter(AldiProduct.name == "Bio Haferflocken").first()
        milch = db.query(AldiProduct).filter(AldiProduct.name == "Bio Milch 3,5%").first()
        bananen = db.query(AldiProduct).filter(AldiProduct.name == "Bio Bananen").first()
        
        if porridge and haferflocken and milch and bananen:
            db.add(RecipeIngredient(recipe_id=porridge.id, product_id=haferflocken.id, quantity=Decimal("80"), unit="g"))
            db.add(RecipeIngredient(recipe_id=porridge.id, product_id=milch.id, quantity=Decimal("400"), unit="ml"))
            db.add(RecipeIngredient(recipe_id=porridge.id, product_id=bananen.id, quantity=Decimal("1"), unit="piece"))
        
        # Chicken with Broccoli Recipe
        chicken_recipe = db.query(Recipe).filter(Recipe.name == "Hähnchen mit Brokkoli").first()
        chicken = db.query(AldiProduct).filter(AldiProduct.name == "Bio Hähnchenbrust").first()
        broccoli = db.query(AldiProduct).filter(AldiProduct.name == "Bio Brokkoli").first()
        
        if chicken_recipe and chicken and broccoli:
            db.add(RecipeIngredient(recipe_id=chicken_recipe.id, product_id=chicken.id, quantity=Decimal("300"), unit="g"))
            db.add(RecipeIngredient(recipe_id=chicken_recipe.id, product_id=broccoli.id, quantity=Decimal("400"), unit="g"))
        
        # Bread with Egg Recipe
        bread_recipe = db.query(Recipe).filter(Recipe.name == "Vollkornbrot mit Ei").first()
        bread = db.query(AldiProduct).filter(AldiProduct.name == "Bio Vollkornbrot").first()
        eggs = db.query(AldiProduct).filter(AldiProduct.name == "Bio Eier Freiland").first()
        
        if bread_recipe and bread and eggs:
            db.add(RecipeIngredient(recipe_id=bread_recipe.id, product_id=bread.id, quantity=Decimal("100"), unit="g"))
            db.add(RecipeIngredient(recipe_id=bread_recipe.id, product_id=eggs.id, quantity=Decimal("1"), unit="piece"))
        
        db.commit()
        logger.info("Sample data created successfully")
        
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        db.rollback()
        raise