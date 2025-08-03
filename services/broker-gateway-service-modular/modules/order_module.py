"""
Order Module für Broker-Gateway-Service
Order Management und Trade Execution
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from backend_base_module import BackendBaseModule
from event_bus import EventType
import structlog


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderRequest(BaseModel):
    instrument_code: str = Field(..., description="Trading pair e.g. BTC_EUR")
    side: OrderSide = Field(..., description="BUY or SELL")
    type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    amount: str = Field(..., description="Amount to trade")
    price: Optional[str] = Field(None, description="Price for LIMIT orders")
    stop_price: Optional[str] = Field(None, description="Stop price for STOP orders")
    client_id: Optional[str] = Field(None, description="Client order ID")
    time_in_force: str = Field(default="GTC", description="GTC, IOC, FOK")


class OrderResponse(BaseModel):
    order_id: str
    client_id: Optional[str]
    status: OrderStatus
    instrument_code: str
    side: OrderSide
    type: OrderType
    amount: str
    filled_amount: str
    remaining_amount: str
    price: Optional[str]
    average_price: Optional[str]
    created_at: datetime
    updated_at: datetime


class OrderModule(BackendBaseModule):
    """Order Management und Trade Execution"""
    
    def __init__(self, event_bus):
        super().__init__("order", event_bus)
        self.active_orders = {}
        self.order_history = []
        self.order_book = {}
        self.execution_rules = {}
        self.max_order_size = {}
        
    async def _initialize_module(self) -> bool:
        """Initialize order module"""
        try:
            self.logger.info("Initializing Order Module")
            
            # Initialize execution rules
            self.execution_rules = {
                'max_slippage_percent': 2.0,  # Maximum 2% slippage
                'min_order_amount': 10.0,     # Minimum €10
                'max_order_amount': 100000.0, # Maximum €100k per order
                'daily_order_limit': 1000000.0, # €1M daily limit
                'risk_check_enabled': True,
                'position_size_limit': 0.1    # Max 10% of portfolio per position
            }
            
            # Initialize max order sizes per instrument
            self.max_order_size = {
                'BTC_EUR': 50000.0,
                'ETH_EUR': 30000.0,
                'ADA_EUR': 10000.0,
                'DOT_EUR': 10000.0,
                'AAPL': 20000.0,
                'TSLA': 15000.0,
                'MSFT': 25000.0,
                'GOOGL': 20000.0,
                'AMZN': 20000.0
            }
            
            # Test order creation
            test_request = OrderRequest(
                instrument_code="BTC_EUR",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                amount="100.00"
            )
            
            test_result = await self._validate_order_request(test_request)
            
            self.logger.info("Order module initialized successfully",
                           execution_rules=len(self.execution_rules),
                           max_sizes_configured=len(self.max_order_size),
                           test_validation=test_result.get('valid', False))
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize order module", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        await self.subscribe_to_event(
            EventType.INTELLIGENCE_TRIGGERED,
            self._handle_intelligence_event
        )
        await self.subscribe_to_event(
            EventType.DATA_SYNCHRONIZED,
            self._handle_market_data_event
        )
        await self.subscribe_to_event(
            EventType.SYSTEM_ALERT_RAISED,
            self._handle_system_alert_event
        )
        await self.subscribe_to_event(
            EventType.CONFIG_UPDATED,
            self._handle_config_event
        )
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main order processing logic"""
        try:
            request_type = data.get('type', 'place_order')
            
            if request_type == 'place_order':
                return await self._process_place_order(data)
            elif request_type == 'cancel_order':
                return await self._process_cancel_order(data)
            elif request_type == 'get_order_status':
                return await self._process_get_order_status(data)
            elif request_type == 'get_order_history':
                return await self._process_get_order_history(data)
            elif request_type == 'get_active_orders':
                return await self._get_active_orders()
            elif request_type == 'modify_order':
                return await self._process_modify_order(data)
            else:
                return {
                    'success': False,
                    'error': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            self.logger.error("Error in order processing", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_place_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process place order request"""
        try:
            order_request_data = data.get('order_request')
            broker_credentials = data.get('credentials')
            
            if not order_request_data:
                return {
                    'success': False,
                    'error': 'No order request provided'
                }
            
            # Create OrderRequest object
            try:
                order_request = OrderRequest(**order_request_data)
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Invalid order request format: {str(e)}'
                }
            
            # Validate order request
            validation_result = await self._validate_order_request(order_request)
            if not validation_result.get('valid', False):
                return {
                    'success': False,
                    'error': validation_result.get('error', 'Order validation failed'),
                    'validation_details': validation_result
                }
            
            # Execute order
            order_response = await self._execute_order(order_request, broker_credentials)
            
            if order_response:
                # Store order in active orders
                self.active_orders[order_response.order_id] = order_response
                
                # Add to order history
                self.order_history.append({
                    'order_id': order_response.order_id,
                    'action': 'created',
                    'timestamp': datetime.now(),
                    'order_data': order_response.dict()
                })
                
                # Publish trading event
                await self.publish_module_event(
                    EventType.TRADING_STATE_CHANGED,
                    {
                        'order_id': order_response.order_id,
                        'instrument': order_response.instrument_code,
                        'side': order_response.side.value,
                        'amount': order_response.amount,
                        'status': order_response.status.value,
                        'action': 'order_placed'
                    },
                    f"order-{order_response.order_id}"
                )
                
                self.logger.info("Order placed successfully",
                               order_id=order_response.order_id,
                               instrument=order_response.instrument_code,
                               side=order_response.side.value,
                               amount=order_response.amount)
                
                return {
                    'success': True,
                    'order': order_response.dict(),
                    'validation_details': validation_result
                }
            else:
                return {
                    'success': False,
                    'error': 'Order execution failed'
                }
                
        except Exception as e:
            self.logger.error("Error processing place order", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _validate_order_request(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Validate order request against business rules"""
        try:
            validation = {
                'valid': True,
                'warnings': [],
                'checks': {}
            }
            
            # Check instrument support
            max_size = self.max_order_size.get(order_request.instrument_code)
            if max_size is None:
                validation['valid'] = False
                validation['error'] = f'Instrument {order_request.instrument_code} not supported'
                return validation
            
            validation['checks']['instrument_supported'] = True
            
            # Check order amount
            try:
                amount = float(order_request.amount)
            except ValueError:
                validation['valid'] = False
                validation['error'] = 'Invalid order amount format'
                return validation
            
            # Minimum amount check
            if amount < self.execution_rules['min_order_amount']:
                validation['valid'] = False
                validation['error'] = f'Order amount below minimum {self.execution_rules["min_order_amount"]}'
                return validation
            
            validation['checks']['min_amount'] = True
            
            # Maximum amount check
            if amount > self.execution_rules['max_order_amount']:
                validation['valid'] = False
                validation['error'] = f'Order amount exceeds maximum {self.execution_rules["max_order_amount"]}'
                return validation
            
            validation['checks']['max_amount'] = True
            
            # Instrument-specific size check
            if amount > max_size:
                validation['valid'] = False
                validation['error'] = f'Order amount exceeds instrument limit {max_size}'
                return validation
            
            validation['checks']['instrument_limit'] = True
            
            # Price validation for limit orders
            if order_request.type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
                if not order_request.price:
                    validation['valid'] = False
                    validation['error'] = 'Price required for limit orders'
                    return validation
                
                try:
                    price = float(order_request.price)
                    if price <= 0:
                        validation['valid'] = False
                        validation['error'] = 'Price must be positive'
                        return validation
                except ValueError:
                    validation['valid'] = False
                    validation['error'] = 'Invalid price format'
                    return validation
            
            validation['checks']['price_validation'] = True
            
            # Stop price validation for stop orders
            if order_request.type in [OrderType.STOP, OrderType.STOP_LIMIT]:
                if not order_request.stop_price:
                    validation['valid'] = False
                    validation['error'] = 'Stop price required for stop orders'
                    return validation
                
                try:
                    stop_price = float(order_request.stop_price)
                    if stop_price <= 0:
                        validation['valid'] = False
                        validation['error'] = 'Stop price must be positive'
                        return validation
                except ValueError:
                    validation['valid'] = False
                    validation['error'] = 'Invalid stop price format'
                    return validation
            
            validation['checks']['stop_price_validation'] = True
            
            # Risk checks
            if self.execution_rules['risk_check_enabled']:
                # Daily order limit check (simplified)
                daily_total = self._calculate_daily_order_total()
                if daily_total + amount > self.execution_rules['daily_order_limit']:
                    validation['warnings'].append(f'Approaching daily order limit')
                
                # Large order warning
                if amount > max_size * 0.8:  # 80% of max size
                    validation['warnings'].append('Large order size detected')
            
            validation['checks']['risk_checks'] = True
            
            # Time in force validation
            valid_tif = ['GTC', 'IOC', 'FOK', 'DAY']
            if order_request.time_in_force not in valid_tif:
                validation['warnings'].append(f'Unusual time-in-force: {order_request.time_in_force}')
            
            validation['checks']['time_in_force'] = True
            
            return validation
            
        except Exception as e:
            self.logger.error("Error validating order request", error=str(e))
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }
    
    async def _execute_order(self, order_request: OrderRequest, credentials: Dict[str, Any]) -> Optional[OrderResponse]:
        """Execute order via broker API (mock implementation)"""
        try:
            # Generate order ID
            order_id = f"ORD_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # For demo purposes, simulate order execution
            # In production, integrate with real broker APIs (Bitpanda Pro, etc.)
            
            # Simulate order processing delay
            import asyncio
            await asyncio.sleep(0.1)  # 100ms processing time
            
            # Mock order execution
            amount = float(order_request.amount)
            
            # Simulate fill status based on order type
            if order_request.type == OrderType.MARKET:
                # Market orders fill immediately (in demo)
                status = OrderStatus.FILLED
                filled_amount = order_request.amount
                remaining_amount = "0.00"
                average_price = await self._get_estimated_execution_price(order_request)
            elif order_request.type == OrderType.LIMIT:
                # Limit orders start as open (in demo)
                status = OrderStatus.OPEN
                filled_amount = "0.00"
                remaining_amount = order_request.amount
                average_price = None
                
                # Sometimes partially fill limit orders for demo
                import random
                if random.random() < 0.3:  # 30% chance of partial fill
                    fill_percent = random.uniform(0.1, 0.8)
                    filled_amount = f"{amount * fill_percent:.2f}"
                    remaining_amount = f"{amount * (1 - fill_percent):.2f}"
                    status = OrderStatus.PARTIALLY_FILLED
                    average_price = order_request.price
            else:
                # Other order types start as open
                status = OrderStatus.OPEN
                filled_amount = "0.00"
                remaining_amount = order_request.amount
                average_price = None
            
            # Create order response
            order_response = OrderResponse(
                order_id=order_id,
                client_id=order_request.client_id,
                status=status,
                instrument_code=order_request.instrument_code,
                side=order_request.side,
                type=order_request.type,
                amount=order_request.amount,
                filled_amount=filled_amount,
                remaining_amount=remaining_amount,
                price=order_request.price,
                average_price=average_price,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Schedule order status updates for open orders
            if status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]:
                asyncio.create_task(self._simulate_order_updates(order_id))
            
            return order_response
            
        except Exception as e:
            self.logger.error("Error executing order", error=str(e))
            return None
    
    async def _get_estimated_execution_price(self, order_request: OrderRequest) -> Optional[str]:
        """Get estimated execution price for market orders"""
        try:
            # Mock price estimation (in production, get from order book)
            base_prices = {
                "BTC_EUR": 45000.0,
                "ETH_EUR": 2800.0,
                "ADA_EUR": 0.85,
                "DOT_EUR": 12.50,
                "AAPL": 180.0,
                "TSLA": 250.0,
                "MSFT": 380.0,
                "GOOGL": 140.0,
                "AMZN": 160.0
            }
            
            base_price = base_prices.get(order_request.instrument_code, 100.0)
            
            # Add realistic spread and slippage
            import random
            spread_percent = 0.001  # 0.1% spread
            slippage_percent = random.uniform(0.0, 0.005)  # 0-0.5% slippage
            
            if order_request.side == OrderSide.BUY:
                # Buy at ask + slippage
                execution_price = base_price * (1 + spread_percent/2 + slippage_percent)
            else:
                # Sell at bid - slippage
                execution_price = base_price * (1 - spread_percent/2 - slippage_percent)
            
            return f"{execution_price:.2f}"
            
        except Exception as e:
            self.logger.error("Error estimating execution price", error=str(e))
            return None
    
    async def _simulate_order_updates(self, order_id: str):
        """Simulate order status updates for open orders"""
        try:
            # Wait random time before updates
            import asyncio
            import random
            
            await asyncio.sleep(random.uniform(10, 60))  # 10-60 seconds
            
            if order_id not in self.active_orders:
                return
            
            order = self.active_orders[order_id]
            
            # Randomly update order status
            if order.status == OrderStatus.OPEN:
                # 70% chance to fill, 20% partial fill, 10% cancel
                rand = random.random()
                if rand < 0.7:
                    # Fill order
                    order.status = OrderStatus.FILLED
                    order.filled_amount = order.amount
                    order.remaining_amount = "0.00"
                    order.average_price = order.price or await self._get_estimated_execution_price(
                        OrderRequest(
                            instrument_code=order.instrument_code,
                            side=order.side,
                            type=order.type,
                            amount=order.amount
                        )
                    )
                elif rand < 0.9:
                    # Partial fill
                    amount = float(order.amount)
                    filled = float(order.filled_amount)
                    additional_fill = (amount - filled) * random.uniform(0.3, 0.8)
                    new_filled = filled + additional_fill
                    
                    order.filled_amount = f"{new_filled:.2f}"
                    order.remaining_amount = f"{amount - new_filled:.2f}"
                    order.average_price = order.price
                    
                    if new_filled >= amount * 0.99:  # 99% filled = complete
                        order.status = OrderStatus.FILLED
                        order.filled_amount = order.amount
                        order.remaining_amount = "0.00"
                    else:
                        order.status = OrderStatus.PARTIALLY_FILLED
                else:
                    # Cancel order
                    order.status = OrderStatus.CANCELLED
                
                order.updated_at = datetime.now()
                
                # Publish update event
                await self.publish_module_event(
                    EventType.TRADING_STATE_CHANGED,
                    {
                        'order_id': order_id,
                        'instrument': order.instrument_code,
                        'status': order.status.value,
                        'filled_amount': order.filled_amount,
                        'action': 'order_updated'
                    },
                    f"order-update-{order_id}"
                )
                
                self.logger.info("Order status updated",
                               order_id=order_id,
                               new_status=order.status.value,
                               filled_amount=order.filled_amount)
                
        except Exception as e:
            self.logger.error("Error simulating order updates", 
                            order_id=order_id, 
                            error=str(e))
    
    def _calculate_daily_order_total(self) -> float:
        """Calculate total order amount for today"""
        try:
            today = datetime.now().date()
            daily_total = 0.0
            
            for order_data in self.order_history:
                if order_data['timestamp'].date() == today:
                    order = order_data['order_data']
                    daily_total += float(order.get('amount', '0'))
            
            return daily_total
            
        except Exception as e:
            self.logger.error("Error calculating daily order total", error=str(e))
            return 0.0
    
    async def _process_cancel_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process cancel order request"""
        try:
            order_id = data.get('order_id')
            if not order_id:
                return {
                    'success': False,
                    'error': 'No order ID provided'
                }
            
            if order_id not in self.active_orders:
                return {
                    'success': False,
                    'error': f'Order {order_id} not found'
                }
            
            order = self.active_orders[order_id]
            
            # Check if order can be cancelled
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                return {
                    'success': False,
                    'error': f'Cannot cancel order in status {order.status.value}'
                }
            
            # Cancel order
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            
            # Add to history
            self.order_history.append({
                'order_id': order_id,
                'action': 'cancelled',
                'timestamp': datetime.now(),
                'order_data': order.dict()
            })
            
            # Publish event
            await self.publish_module_event(
                EventType.TRADING_STATE_CHANGED,
                {
                    'order_id': order_id,
                    'instrument': order.instrument_code,
                    'status': order.status.value,
                    'action': 'order_cancelled'
                },
                f"order-cancel-{order_id}"
            )
            
            return {
                'success': True,
                'order_id': order_id,
                'status': order.status.value,
                'cancelled_at': order.updated_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error cancelling order", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_get_order_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get order status"""
        try:
            order_id = data.get('order_id')
            if not order_id:
                return {
                    'success': False,
                    'error': 'No order ID provided'
                }
            
            if order_id not in self.active_orders:
                return {
                    'success': False,
                    'error': f'Order {order_id} not found'
                }
            
            order = self.active_orders[order_id]
            
            return {
                'success': True,
                'order': order.dict()
            }
            
        except Exception as e:
            self.logger.error("Error getting order status", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_get_order_history(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get order history"""
        try:
            limit = data.get('limit', 50)
            status_filter = data.get('status')
            instrument_filter = data.get('instrument')
            
            # Filter history
            filtered_history = []
            for entry in self.order_history[-limit:]:
                order_data = entry['order_data']
                
                # Apply filters
                if status_filter and order_data.get('status') != status_filter:
                    continue
                
                if instrument_filter and order_data.get('instrument_code') != instrument_filter:
                    continue
                
                filtered_history.append(entry)
            
            return {
                'success': True,
                'order_history': filtered_history,
                'total_orders': len(self.order_history),
                'filtered_count': len(filtered_history)
            }
            
        except Exception as e:
            self.logger.error("Error getting order history", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_active_orders(self) -> Dict[str, Any]:
        """Get active orders"""
        try:
            active_orders = [
                order.dict() for order in self.active_orders.values()
                if order.status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED, OrderStatus.PENDING]
            ]
            
            return {
                'success': True,
                'active_orders': active_orders,
                'count': len(active_orders)
            }
            
        except Exception as e:
            self.logger.error("Error getting active orders", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_intelligence_event(self, event):
        """Handle intelligence triggered events"""
        try:
            self.logger.debug("Received intelligence event")
            
            # Intelligence events could trigger automatic orders
            # For now, just log the event
            symbol = event.data.get('symbol')
            recommendation = event.data.get('recommendation')
            confidence = event.data.get('confidence', 0.0)
            
            if symbol and recommendation and confidence > 0.8:
                self.logger.info("High confidence intelligence signal received",
                               symbol=symbol,
                               recommendation=recommendation,
                               confidence=confidence)
                # Could trigger auto-trading logic here
                
        except Exception as e:
            self.logger.error("Error handling intelligence event", error=str(e))
    
    async def _handle_market_data_event(self, event):
        """Handle market data events"""
        try:
            self.logger.debug("Received market data event")
            # Market data updates could trigger stop orders, etc.
        except Exception as e:
            self.logger.error("Error handling market data event", error=str(e))
    
    async def _handle_system_alert_event(self, event):
        """Handle system alert events"""
        try:
            self.logger.info("Received system alert event")
            
            alert_type = event.data.get('alert_type')
            if alert_type == 'trading_halt':
                # Halt all trading
                self.logger.warning("Trading halt requested")
                # Could implement trading halt logic
                
        except Exception as e:
            self.logger.error("Error handling system alert event", error=str(e))
    
    async def _handle_config_event(self, event):
        """Handle configuration update events"""
        try:
            self.logger.info("Received config update event")
            
            config_data = event.data
            if 'execution_rules' in config_data:
                self.execution_rules.update(config_data['execution_rules'])
                self.logger.info("Execution rules updated")
            
            if 'max_order_size' in config_data:
                self.max_order_size.update(config_data['max_order_size'])
                self.logger.info("Max order sizes updated")
                
        except Exception as e:
            self.logger.error("Error handling config event", error=str(e))