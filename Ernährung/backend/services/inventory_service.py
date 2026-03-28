from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from ..database.models import Inventory, AldiProduct
from ..models.schemas import InventoryCreate, InventoryUpdate

class InventoryService:
    
    @staticmethod
    def get_inventory(db: Session, filters: Dict[str, Any] = None) -> List[Inventory]:
        """Get inventory items with optional filtering"""
        query = db.query(Inventory).join(AldiProduct)
        
        if filters:
            if 'location' in filters:
                query = query.filter(Inventory.location == filters['location'])
            if 'expiring_before' in filters:
                query = query.filter(Inventory.expiry_date <= filters['expiring_before'])
            if 'category' in filters:
                query = query.filter(AldiProduct.category == filters['category'])
        
        return query.order_by(Inventory.expiry_date.asc()).all()
    
    @staticmethod
    def get_inventory_item(db: Session, item_id: int) -> Optional[Inventory]:
        """Get inventory item by ID"""
        return db.query(Inventory).filter(Inventory.id == item_id).first()
    
    @staticmethod
    def create_inventory_item(db: Session, item: InventoryCreate) -> Inventory:
        """Add item to inventory"""
        db_item = Inventory(
            product_id=item.product_id,
            quantity=item.quantity,
            expiry_date=item.expiry_date,
            purchase_date=item.purchase_date,
            location=item.location,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    
    @staticmethod
    def update_inventory_item(db: Session, item_id: int, item: InventoryUpdate) -> Inventory:
        """Update inventory item"""
        db_item = db.query(Inventory).filter(Inventory.id == item_id).first()
        if db_item:
            update_data = item.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_item, field, value)
            db_item.updated_at = datetime.now()
            db.commit()
            db.refresh(db_item)
        return db_item
    
    @staticmethod
    def delete_inventory_item(db: Session, item_id: int) -> bool:
        """Remove item from inventory"""
        db_item = db.query(Inventory).filter(Inventory.id == item_id).first()
        if db_item:
            db.delete(db_item)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_expiring_items(db: Session, days: int = 7) -> List[Inventory]:
        """Get items expiring within specified days"""
        expiry_threshold = date.today() + timedelta(days=days)
        
        return db.query(Inventory).filter(
            Inventory.expiry_date <= expiry_threshold,
            Inventory.expiry_date >= date.today()
        ).join(AldiProduct).order_by(Inventory.expiry_date.asc()).all()
    
    @staticmethod
    def get_low_stock_items(db: Session, threshold: float = 10.0) -> List[Inventory]:
        """Get items with low stock"""
        return db.query(Inventory).filter(
            Inventory.quantity <= threshold
        ).join(AldiProduct).all()
    
    @staticmethod
    def update_inventory_from_usage(db: Session, product_id: int, quantity_used: float):
        """Update inventory when products are used in recipes"""
        # Find the oldest inventory item for this product
        inventory_item = db.query(Inventory).filter(
            Inventory.product_id == product_id,
            Inventory.quantity > 0
        ).order_by(Inventory.purchase_date.asc()).first()
        
        if inventory_item:
            new_quantity = float(inventory_item.quantity) - quantity_used
            
            if new_quantity <= 0:
                # Remove item if quantity becomes 0 or negative
                db.delete(inventory_item)
            else:
                # Update quantity
                inventory_item.quantity = new_quantity
                inventory_item.updated_at = datetime.now()
            
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_inventory_value(db: Session) -> Dict[str, Any]:
        """Calculate total inventory value"""
        inventory_items = db.query(Inventory).join(AldiProduct).all()
        
        total_value = 0.0
        total_items = len(inventory_items)
        categories = {}
        
        for item in inventory_items:
            if item.product.price_per_unit:
                item_value = float(item.quantity) * float(item.product.price_per_unit)
                total_value += item_value
                
                # Group by category
                category = item.product.category or 'Unknown'
                if category not in categories:
                    categories[category] = {'value': 0.0, 'items': 0}
                
                categories[category]['value'] += item_value
                categories[category]['items'] += 1
        
        return {
            'total_value': round(total_value, 2),
            'total_items': total_items,
            'categories': categories,
            'average_item_value': round(total_value / total_items, 2) if total_items > 0 else 0
        }