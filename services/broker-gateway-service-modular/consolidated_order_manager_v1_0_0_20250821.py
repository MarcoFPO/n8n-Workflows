"""
Consolidated Order Manager v1.0.0
Clean Architecture - Konsolidiert 14 Over-Engineering Module in eine saubere Klasse
SOLID Principles: Single Responsibility mit klarer Interface-Trennung
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path
import sys

# Zentrale Konfiguration verwenden
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.central_config_v1_0_0_20250821 import config

class OrderStatus(Enum):
    """Order Status Enumeration"""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class OrderSide(Enum):
    """Order Side Enumeration"""
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    """Order Type Enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"

class Order:
    """Clean Order Data Model"""
    
    def __init__(self, symbol: str, side: OrderSide, order_type: OrderType, 
                 amount: Decimal, price: Optional[Decimal] = None):
        self.id = self._generate_order_id()
        self.symbol = symbol
        self.side = side
        self.type = order_type
        self.amount = amount
        self.price = price
        self.status = OrderStatus.PENDING
        self.created_at = datetime.now()
        self.filled_amount = Decimal('0')
        self.average_price = Decimal('0')
        self.fees = Decimal('0')
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        timestamp = int(datetime.now().timestamp() * 1000)
        return f"ORD_{timestamp}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.type.value,
            "amount": str(self.amount),
            "price": str(self.price) if self.price else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "filled_amount": str(self.filled_amount),
            "average_price": str(self.average_price),
            "fees": str(self.fees)
        }

class OrderValidator:
    """Order Validation Logic - Single Responsibility"""
    
    def __init__(self):
        self.config = config
        self.daily_limits = {}  # Track daily trading limits
    
    def validate_order(self, order: Order) -> Dict[str, Any]:
        """Comprehensive order validation"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Amount validation
        if order.amount <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("Order amount must be positive")
        
        # Size limits
        limits = self.config.TRADING_CONFIG["limits"]
        if order.amount > limits["max_order_size"]:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Order amount exceeds maximum: {limits['max_order_size']}")
        
        if order.amount < limits["min_order_size"]:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Order amount below minimum: {limits['min_order_size']}")
        
        # Daily limit check
        daily_total = self._get_daily_total(order.symbol)
        if daily_total + order.amount > limits["daily_limit"]:
            validation_result["valid"] = False
            validation_result["errors"].append("Daily trading limit exceeded")
        
        # Price validation for limit orders
        if order.type == OrderType.LIMIT and order.price is None:
            validation_result["valid"] = False
            validation_result["errors"].append("Limit orders require a price")
        
        return validation_result
    
    def _get_daily_total(self, symbol: str) -> Decimal:
        """Get today's trading total for symbol"""
        today = datetime.now().date()
        if symbol not in self.daily_limits:
            self.daily_limits[symbol] = {}
        if today not in self.daily_limits[symbol]:
            self.daily_limits[symbol][today] = Decimal('0')
        return self.daily_limits[symbol][today]

class OrderExecutor:
    """Order Execution Logic - Single Responsibility"""
    
    def __init__(self):
        self.config = config
        self.execution_counter = 0
    
    async def execute_order(self, order: Order) -> Dict[str, Any]:
        """Execute order with proper error handling"""
        try:
            # Simulate order execution
            execution_result = await self._simulate_execution(order)
            
            # Update order status
            if execution_result["success"]:
                order.status = OrderStatus.FILLED
                order.filled_amount = order.amount
                order.average_price = execution_result["execution_price"]
                order.fees = self._calculate_fees(order)
            else:
                order.status = OrderStatus.REJECTED
            
            return {
                "success": execution_result["success"],
                "order": order.to_dict(),
                "execution_details": execution_result
            }
        
        except Exception as e:
            order.status = OrderStatus.REJECTED
            return {
                "success": False,
                "order": order.to_dict(),
                "error": str(e)
            }
    
    async def _simulate_execution(self, order: Order) -> Dict[str, Any]:
        """Simulate broker execution"""
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Simulate 95% success rate
        import random
        success = random.random() > 0.05
        
        if success:
            # Simulate market price with small spread
            base_price = Decimal('100.00')  # Mock base price
            spread = Decimal('0.02')
            execution_price = base_price + (spread if order.side == OrderSide.BUY else -spread)
            
            return {
                "success": True,
                "execution_price": execution_price,
                "timestamp": datetime.now().isoformat(),
                "broker_order_id": f"BRK_{self.execution_counter}"
            }
        else:
            return {
                "success": False,
                "reason": "Insufficient liquidity",
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_fees(self, order: Order) -> Decimal:
        """Calculate trading fees"""
        fees_config = self.config.TRADING_CONFIG["fees"]
        fee_rate = Decimal(str(fees_config.get(f"{order.symbol}_EUR", fees_config["default"])))
        return order.amount * order.average_price * fee_rate

class ConsolidatedOrderManager:
    """
    Consolidated Order Manager - Clean Architecture
    Ersetzt 14 Over-Engineering Module mit sauberer Single-Class-Lösung
    SOLID Principles: Delegation an spezialisierte Komponenten
    """
    
    def __init__(self):
        self.validator = OrderValidator()
        self.executor = OrderExecutor()
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Place new order with full validation and execution"""
        try:
            # Create order object
            order = Order(
                symbol=symbol,
                side=OrderSide(side.lower()),
                order_type=OrderType(order_type.lower()),
                amount=Decimal(str(amount)),
                price=Decimal(str(price)) if price else None
            )
            
            # Validate order
            validation = self.validator.validate_order(order)
            if not validation["valid"]:
                return {
                    "success": False,
                    "errors": validation["errors"],
                    "order_id": None
                }
            
            # Add to active orders
            self.active_orders[order.id] = order
            
            # Execute order
            execution_result = await self.executor.execute_order(order)
            
            # Move to history if completed
            if order.status in [OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED]:
                self.order_history.append(order)
                if order.id in self.active_orders:
                    del self.active_orders[order.id]
            
            return {
                "success": execution_result["success"],
                "order_id": order.id,
                "order": order.to_dict(),
                "execution_details": execution_result.get("execution_details", {})
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Order placement failed: {str(e)}",
                "order_id": None
            }
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel active order"""
        if order_id not in self.active_orders:
            return {
                "success": False,
                "error": "Order not found or already completed"
            }
        
        order = self.active_orders[order_id]
        order.status = OrderStatus.CANCELLED
        
        # Move to history
        self.order_history.append(order)
        del self.active_orders[order_id]
        
        return {
            "success": True,
            "message": f"Order {order_id} cancelled successfully",
            "order": order.to_dict()
        }
    
    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get all active orders"""
        return [order.to_dict() for order in self.active_orders.values()]
    
    def get_order_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get order history with limit"""
        sorted_history = sorted(self.order_history, key=lambda x: x.created_at, reverse=True)
        return [order.to_dict() for order in sorted_history[:limit]]
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get specific order status"""
        # Check active orders first
        if order_id in self.active_orders:
            return self.active_orders[order_id].to_dict()
        
        # Check history
        for order in self.order_history:
            if order.id == order_id:
                return order.to_dict()
        
        return None

# Global instance for service use
order_manager = ConsolidatedOrderManager()