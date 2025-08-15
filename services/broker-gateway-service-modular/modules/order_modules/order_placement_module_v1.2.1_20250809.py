"""
Order Placement Module - Single Function Module
Verantwortlich ausschließlich für Order Placement Logic
"""

import time
import uuid
from typing import Dict, Any, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, Field, structlog
)
from ..single_function_module_base import SingleFunctionModule

# Order Models Import
from enum import Enum

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
    order_id: str = Field(..., description="Unique order ID")
    status: OrderStatus = Field(..., description="Order status")
    instrument_code: str = Field(..., description="Trading pair")
    side: OrderSide = Field(..., description="BUY or SELL")
    type: OrderType = Field(..., description="Order type")
    amount: str = Field(..., description="Order amount")
    price: Optional[str] = Field(None, description="Order price")
    filled_amount: str = Field(default="0", description="Filled amount")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class OrderPlacementModule(SingleFunctionModule):
    """
    Single Function Module: Order Placement
    Verantwortlichkeit: Ausschließlich Order-Placement-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_placement", event_bus)
        self.placed_orders = {}  # Order Cache für Simulation
        self.order_counter = 0
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order Placement
        
        Args:
            input_data: {
                'order_request': OrderRequest dict,
                'credentials': broker credentials
            }
            
        Returns:
            Dict mit Order-Placement-Result
        """
        order_request_data = input_data.get('order_request')
        broker_credentials = input_data.get('credentials')
        
        if not order_request_data:
            raise ValueError('No order request provided')
        
        # OrderRequest validieren
        try:
            order_request = OrderRequest(**order_request_data)
        except Exception as e:
            raise ValueError(f'Invalid order request format: {str(e)}')
        
        # Order platzieren
        order_response = await self._place_order_with_broker(order_request, broker_credentials)
        
        # Order in lokalem Cache speichern
        self.placed_orders[order_response.order_id] = order_response
        
        return {
            'order_id': order_response.order_id,
            'status': order_response.status.value,
            'instrument_code': order_response.instrument_code,
            'side': order_response.side.value,
            'amount': order_response.amount,
            'price': order_response.price,
            'created_at': order_response.created_at.isoformat()
        }
    
    async def _place_order_with_broker(self, order_request: OrderRequest, credentials: Dict[str, Any]) -> OrderResponse:
        """
        Order bei Broker platzieren (Simulation für Demo)
        In Produktion: Bitpanda API Call
        """
        self.order_counter += 1
        order_id = f"ORD-{int(time.time())}-{self.order_counter:04d}"
        
        # Simulate order processing delay
        await self._simulate_broker_processing()
        
        # Create order response
        order_response = OrderResponse(
            order_id=order_id,
            status=OrderStatus.OPEN,
            instrument_code=order_request.instrument_code,
            side=order_request.side,
            type=order_request.type,
            amount=order_request.amount,
            price=order_request.price,
            filled_amount="0",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.logger.info(f"Order placed successfully",
                        order_id=order_id,
                        instrument=order_request.instrument_code,
                        side=order_request.side.value,
                        amount=order_request.amount)
        
        return order_response
    
    async def _simulate_broker_processing(self):
        """Simuliert Broker-API Processing-Zeit"""
        import asyncio
        # Simuliere 100-300ms API-Latenz
        processing_time = 0.1 + (hash(str(datetime.now())) % 200) / 1000
        await asyncio.sleep(processing_time)
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_placement',
            'description': 'Places trading orders with broker',
            'responsibility': 'Order placement logic only',
            'input_parameters': {
                'order_request': 'OrderRequest object with trading details',
                'credentials': 'Broker authentication credentials'
            },
            'output_format': {
                'order_id': 'Unique order identifier',
                'status': 'Order status (OPEN, FILLED, etc.)',
                'instrument_code': 'Trading pair',
                'side': 'BUY/SELL',
                'amount': 'Order amount',
                'price': 'Order price (if applicable)',
                'created_at': 'Order creation timestamp'
            },
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_placed_orders_count(self) -> int:
        """Anzahl platzierter Orders"""
        return len(self.placed_orders)
    
    def get_recent_orders(self, limit: int = 10) -> list:
        """Letzte platzierte Orders abrufen"""
        orders = list(self.placed_orders.values())
        orders.sort(key=lambda x: x.created_at, reverse=True)

    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions for Order Module"""
        try:
            # Subscribe to system health requests
            await self.event_bus.subscribe('system.health.request', self.process_event)
            
            # Subscribe to module-specific order events
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('order.status.request', self.process_event)
            await self.event_bus.subscribe('order.update', self.process_event)
            
            self.logger.info("Event subscriptions setup completed",
                           module=self.module_name)
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions",
                            error=str(e), module=self.module_name)

    async def process_event(self, event):
        """Process incoming events"""
        try:
            event_type = event.get('event_type', '')
            
            if event_type == 'system.health.request':
                # Health check response
                health_response = {
                    'event_type': 'system.health.response',
                    'stream_id': 'health-check',
                    'data': {
                        'module_name': self.module_name,
                        'status': 'healthy',
                        'execution_count': len(self.execution_history),
                        'average_execution_time_ms': self.average_execution_time,
                        'orders_processed': getattr(self, 'orders_processed', 0),
                        'health_check_timestamp': datetime.now().isoformat()
                    },
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(health_response)
                
            elif event_type == f'{self.module_name}.request':
                # Module-specific request
                event_data = event.get('data', {})
                result = await self.execute_function(event_data)
                
                response_event = {
                    'event_type': f'{self.module_name}.response',
                    'stream_id': event.get('stream_id', f'{self.module_name}-request'),
                    'data': result,
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(response_event)
            
            elif event_type == 'order.status.request':
                # Order status request
                order_id = event.get('data', {}).get('order_id')
                if order_id and hasattr(self, 'get_order_status'):
                    status = self.get_order_status(order_id)
                    status_response = {
                        'event_type': 'order.status.response',
                        'stream_id': event.get('stream_id', 'order-status'),
                        'data': {
                            'order_id': order_id,
                            'status': status,
                            'module': self.module_name
                        },
                        'source': self.module_name,
                        'correlation_id': event.get('correlation_id')
                    }
                    await self.event_bus.publish(status_response)
            
            else:
                self.logger.debug("Unhandled event type",
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)

    async def publish_order_event(self, event_type: str, order_data: dict):
        """Publish order-related events"""
        if not self.event_bus:
            return
            
        try:
            order_event = {
                'event_type': event_type,
                'stream_id': f'order-{order_data.get("order_id", "unknown")}',
                'data': {
                    **order_data,
                    'timestamp': datetime.now().isoformat(),
                    'processing_module': self.module_name
                },
                'source': self.module_name
            }
            await self.event_bus.publish(order_event)
            
        except Exception as e:
            self.logger.error("Failed to publish order event",
                            error=str(e), event_type=event_type)
        return orders[:limit]