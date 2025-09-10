from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..database.models import ShoppingList, ShoppingListItem, AldiProduct
from ..models.schemas import ShoppingListCreate, ShoppingListUpdate

class ShoppingService:
    
    @staticmethod
    def get_shopping_lists(db: Session, status_filter: str = "active") -> List[ShoppingList]:
        """Get shopping lists with status filter"""
        query = db.query(ShoppingList)
        
        if status_filter != "all":
            query = query.filter(ShoppingList.status == status_filter)
        
        return query.order_by(ShoppingList.created_at.desc()).all()
    
    @staticmethod
    def get_shopping_list(db: Session, list_id: int) -> Optional[ShoppingList]:
        """Get shopping list by ID"""
        return db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
    
    @staticmethod
    def create_shopping_list(db: Session, shopping_list: ShoppingListCreate) -> ShoppingList:
        """Create new shopping list"""
        db_list = ShoppingList(
            name=shopping_list.name,
            list_type=shopping_list.list_type,
            status=shopping_list.status,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_list)
        db.commit()
        db.refresh(db_list)
        
        # Add items to the shopping list
        for item in shopping_list.items:
            db_item = ShoppingListItem(
                shopping_list_id=db_list.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit=item.unit,
                priority=item.priority,
                is_checked=item.is_checked,
                estimated_price=item.estimated_price,
                created_at=datetime.now()
            )
            db.add(db_item)
        
        db.commit()
        return db_list
    
    @staticmethod
    def update_shopping_list(db: Session, list_id: int, shopping_list: ShoppingListUpdate) -> ShoppingList:
        """Update shopping list"""
        db_list = db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
        if db_list:
            update_data = shopping_list.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_list, field, value)
            db_list.updated_at = datetime.now()
            db.commit()
            db.refresh(db_list)
        return db_list
    
    @staticmethod
    def add_items_to_list(db: Session, list_id: int, items: List[Dict[str, Any]]) -> bool:
        """Add items to existing shopping list"""
        shopping_list = ShoppingService.get_shopping_list(db, list_id)
        if not shopping_list:
            return False
        
        for item_data in items:
            db_item = ShoppingListItem(
                shopping_list_id=list_id,
                **item_data,
                created_at=datetime.now()
            )
            db.add(db_item)
        
        shopping_list.updated_at = datetime.now()
        db.commit()
        return True
    
    @staticmethod
    def check_item(db: Session, list_id: int, item_id: int, is_checked: bool = True) -> bool:
        """Mark item as checked/unchecked"""
        db_item = db.query(ShoppingListItem).filter(
            ShoppingListItem.shopping_list_id == list_id,
            ShoppingListItem.id == item_id
        ).first()
        
        if db_item:
            db_item.is_checked = is_checked
            
            # Update shopping list timestamp
            shopping_list = ShoppingService.get_shopping_list(db, list_id)
            if shopping_list:
                shopping_list.updated_at = datetime.now()
            
            db.commit()
            return True
        return False
    
    @staticmethod
    def generate_shopping_list_from_recipes(db: Session, recipe_ids: List[int]) -> Dict[str, Any]:
        """Generate shopping list based on selected recipes"""
        from .inventory_service import InventoryService
        from .recipe_service import RecipeService
        
        needed_ingredients = {}
        
        # Get all ingredients from selected recipes
        for recipe_id in recipe_ids:
            recipe = RecipeService.get_recipe_by_id(db, recipe_id)
            if recipe:
                for ingredient in recipe.ingredients:
                    product_id = ingredient.product_id
                    quantity = float(ingredient.quantity)
                    
                    if product_id in needed_ingredients:
                        needed_ingredients[product_id] += quantity
                    else:
                        needed_ingredients[product_id] = quantity
        
        # Check what's already in inventory
        inventory_items = InventoryService.get_inventory(db)
        inventory_map = {}
        
        for item in inventory_items:
            product_id = item.product_id
            quantity = float(item.quantity)
            
            if product_id in inventory_map:
                inventory_map[product_id] += quantity
            else:
                inventory_map[product_id] = quantity
        
        # Calculate what needs to be bought
        shopping_items = []
        
        for product_id, needed_qty in needed_ingredients.items():
            available_qty = inventory_map.get(product_id, 0)
            needed_qty_adjusted = needed_qty - available_qty
            
            if needed_qty_adjusted > 0:
                product = db.query(AldiProduct).filter(AldiProduct.id == product_id).first()
                if product:
                    shopping_items.append({
                        'product_id': product_id,
                        'product_name': product.name,
                        'quantity': needed_qty_adjusted,
                        'unit': product.unit_type or 'piece',
                        'estimated_price': float(product.price_per_unit) * needed_qty_adjusted if product.price_per_unit else None
                    })
        
        return {
            'items': shopping_items,
            'total_estimated_cost': sum(item['estimated_price'] for item in shopping_items if item['estimated_price']),
            'recipes_count': len(recipe_ids)
        }