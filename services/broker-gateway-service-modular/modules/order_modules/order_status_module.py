"""
Order Status Module - Single Function Module
Verantwortlich ausschließlich für Order Status Retrieval Logic
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderStatus, OrderSide, OrderType


class OrderStatusInfo(BaseModel):
    order_id: str
    status: OrderStatus
    instrument_code: str
    side: OrderSide
    type: OrderType
    original_amount: str
    filled_amount: str
    remaining_amount: str
    average_price: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    broker_status: Dict[str, Any]


class StatusRequest(BaseModel):
    order_id: str
    include_fills: bool = False
    include_broker_details: bool = True


class OrderStatusModule(SingleFunctionModule):
    """
    Single Function Module: Order Status Retrieval
    Verantwortlichkeit: Ausschließlich Order-Status-Abfrage-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_status", event_bus)
        
        # Status Cache für Performance
        self.status_cache = {}
        self.cache_expiry_seconds = 30  # Cache 30 Sekunden gültig
        self.status_requests_count = 0
        
        # Broker Status Mapping
        self.broker_status_mapping = {
            'NEW': OrderStatus.OPEN,
            'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
            'FILLED': OrderStatus.FILLED,
            'CANCELED': OrderStatus.CANCELLED,
            'REJECTED': OrderStatus.REJECTED,
            'EXPIRED': OrderStatus.EXPIRED,
            'PENDING_CANCEL': OrderStatus.PENDING
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order Status Retrieval
        
        Args:
            input_data: {
                'status_request': StatusRequest dict,
                'credentials': broker credentials,
                'use_cache': optional cache usage flag
            }
            
        Returns:
            Dict mit Order-Status-Information
        """
        status_request_data = input_data.get('status_request')
        credentials = input_data.get('credentials', {})
        use_cache = input_data.get('use_cache', True)
        
        if not status_request_data:
            raise ValueError('No status request provided')
        
        # StatusRequest parsieren
        try:
            status_request = StatusRequest(**status_request_data)
        except Exception as e:
            raise ValueError(f'Invalid status request format: {str(e)}')
        
        # Status abrufen (mit Cache-Option)
        order_status_info = await self._get_order_status_from_broker(
            status_request, credentials, use_cache
        )
        
        return {
            'order_id': order_status_info.order_id,
            'status': order_status_info.status.value,
            'instrument_code': order_status_info.instrument_code,
            'side': order_status_info.side.value,
            'type': order_status_info.type.value,
            'original_amount': order_status_info.original_amount,
            'filled_amount': order_status_info.filled_amount,
            'remaining_amount': order_status_info.remaining_amount,
            'average_price': order_status_info.average_price,
            'created_at': order_status_info.created_at.isoformat(),
            'updated_at': order_status_info.updated_at.isoformat(),
            'broker_status': order_status_info.broker_status,
            'retrieval_timestamp': datetime.now().isoformat()
        }
    
    async def _get_order_status_from_broker(self, status_request: StatusRequest,
                                          credentials: Dict[str, Any],
                                          use_cache: bool) -> OrderStatusInfo:
        """
        Order Status vom Broker abrufen (mit Cache-Support)
        """
        self.status_requests_count += 1
        order_id = status_request.order_id
        
        # Cache Check
        if use_cache and self._is_status_cached(order_id):
            self.logger.debug(f"Using cached status for order {order_id}")
            return self.status_cache[order_id]['status_info']
        
        # Status vom Broker abrufen
        try:
            order_status_info = await self._fetch_status_from_broker_api(
                status_request, credentials
            )
            
            # In Cache speichern
            if use_cache:
                self.status_cache[order_id] = {
                    'status_info': order_status_info,
                    'cached_at': datetime.now()
                }
            
            self.logger.info(f"Order status retrieved successfully",
                           order_id=order_id,
                           status=order_status_info.status.value,
                           filled_amount=order_status_info.filled_amount)
            
            return order_status_info
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve order status",
                            order_id=order_id,
                            error=str(e))
            raise
    
    async def _fetch_status_from_broker_api(self, status_request: StatusRequest,
                                          credentials: Dict[str, Any]) -> OrderStatusInfo:
        """
        Order Status von Broker API abrufen (Bitpanda API Simulation)
        """
        
        # Simulate API call delay
        import asyncio
        api_delay = 0.05 + (hash(status_request.order_id) % 50) / 1000  # 50-100ms
        await asyncio.sleep(api_delay)
        
        order_id = status_request.order_id
        
        # Simulate broker response (in Produktion: echter API Call)
        broker_status_info = await self._simulate_broker_status_response(
            order_id, status_request.include_fills, status_request.include_broker_details
        )
        
        # Broker Status zu internem Status mappen
        internal_status = self._map_broker_status(broker_status_info['status'])
        
        # OrderStatusInfo erstellen
        order_status_info = OrderStatusInfo(
            order_id=order_id,
            status=internal_status,
            instrument_code=broker_status_info['symbol'],
            side=OrderSide(broker_status_info['side']),
            type=OrderType(broker_status_info['order_type']),
            original_amount=broker_status_info['original_amount'],
            filled_amount=broker_status_info['executed_amount'],
            remaining_amount=self._calculate_remaining_amount(
                broker_status_info['original_amount'],
                broker_status_info['executed_amount']
            ),
            average_price=broker_status_info.get('average_price'),
            created_at=datetime.fromisoformat(broker_status_info['created_at']),
            updated_at=datetime.fromisoformat(broker_status_info['updated_at']),
            broker_status=broker_status_info
        )
        
        return order_status_info
    
    async def _simulate_broker_status_response(self, order_id: str, include_fills: bool,
                                             include_broker_details: bool) -> Dict[str, Any]:
        """Simuliert Broker API Status Response"""
        import random
        
        # Realistische Order Status Simulation
        status_options = ['NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED']
        status_weights = [0.4, 0.2, 0.3, 0.1]
        broker_status = random.choices(status_options, weights=status_weights)[0]
        
        # Realistische Order Daten
        instruments = ['BTC_EUR', 'ETH_EUR', 'ADA_EUR', 'DOT_EUR']
        sides = ['BUY', 'SELL']
        order_types = ['MARKET', 'LIMIT']
        
        original_amount = round(random.uniform(0.1, 10.0), 8)
        
        # Executed Amount basierend auf Status
        if broker_status == 'NEW':
            executed_amount = 0.0
        elif broker_status == 'PARTIALLY_FILLED':
            executed_amount = round(original_amount * random.uniform(0.1, 0.8), 8)
        elif broker_status == 'FILLED':
            executed_amount = original_amount
        else:  # CANCELED
            executed_amount = round(original_amount * random.uniform(0.0, 0.3), 8)
        
        # Base Response
        response = {
            'order_id': order_id,
            'status': broker_status,
            'symbol': random.choice(instruments),
            'side': random.choice(sides),
            'order_type': random.choice(order_types),
            'original_amount': str(original_amount),
            'executed_amount': str(executed_amount),
            'average_price': str(round(random.uniform(1000, 50000), 2)) if executed_amount > 0 else None,
            'created_at': (datetime.now() - datetime.timedelta(minutes=random.randint(1, 120))).isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Fill Details
        if include_fills and executed_amount > 0:
            response['fills'] = self._simulate_order_fills(executed_amount)
        
        # Broker Details
        if include_broker_details:
            response['broker_details'] = {
                'exchange': 'bitpanda_pro',
                'order_book': 'primary',
                'fees': {
                    'trading_fee': str(round(executed_amount * 0.0015, 6)),
                    'settlement_fee': '0.0'
                },
                'market_data': {
                    'last_price': str(round(random.uniform(1000, 50000), 2)),
                    'bid': str(round(random.uniform(1000, 49000), 2)),
                    'ask': str(round(random.uniform(1001, 51000), 2))
                }
            }
        
        return response
    
    def _simulate_order_fills(self, total_executed: float) -> List[Dict[str, Any]]:
        """Simuliert Fill-Details für executed Orders"""
        import random
        
        fills = []
        remaining = total_executed
        fill_count = random.randint(1, min(5, int(total_executed * 10)))  # Max 5 Fills
        
        for i in range(fill_count):
            if i == fill_count - 1:
                # Letzter Fill: Rest
                fill_amount = remaining
            else:
                # Zufällige Fill-Größe
                max_fill = remaining * 0.8
                fill_amount = round(random.uniform(0.01, max_fill), 8)
                remaining -= fill_amount
            
            if fill_amount <= 0:
                break
            
            fills.append({
                'fill_id': f"FILL-{int(datetime.now().timestamp())}-{i:03d}",
                'amount': str(fill_amount),
                'price': str(round(random.uniform(1000, 50000), 2)),
                'timestamp': (datetime.now() - datetime.timedelta(seconds=random.randint(1, 300))).isoformat(),
                'fee': str(round(fill_amount * 0.0015, 6))
            })
        
        return fills
    
    def _map_broker_status(self, broker_status: str) -> OrderStatus:
        """Broker Status zu internem Status mappen"""
        return self.broker_status_mapping.get(broker_status, OrderStatus.PENDING)
    
    def _calculate_remaining_amount(self, original_amount: str, executed_amount: str) -> str:
        """Verbleibende Order-Menge berechnen"""
        try:
            original = Decimal(original_amount)
            executed = Decimal(executed_amount)
            remaining = original - executed
            return str(max(remaining, Decimal('0')))
        except Exception:
            return "0"
    
    def _is_status_cached(self, order_id: str) -> bool:
        """Prüft ob Status im Cache verfügbar und gültig ist"""
        if order_id not in self.status_cache:
            return False
        
        cache_entry = self.status_cache[order_id]
        cache_age = (datetime.now() - cache_entry['cached_at']).total_seconds()
        
        return cache_age < self.cache_expiry_seconds
    
    def clear_status_cache(self, order_id: Optional[str] = None):
        """Cache leeren (für spezifische Order oder komplett)"""
        if order_id:
            self.status_cache.pop(order_id, None)
            self.logger.debug(f"Cleared status cache for order {order_id}")
        else:
            self.status_cache.clear()
            self.logger.debug("Cleared entire status cache")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_status',
            'description': 'Retrieves current status information for trading orders',
            'responsibility': 'Order status retrieval logic only',
            'input_parameters': {
                'status_request': 'StatusRequest object with order ID and options',
                'credentials': 'Broker authentication credentials',
                'use_cache': 'Optional flag to enable/disable status caching'
            },
            'output_format': {
                'order_id': 'Order identifier',
                'status': 'Current order status',
                'instrument_code': 'Trading pair',
                'side': 'BUY/SELL',
                'type': 'Order type (MARKET, LIMIT, etc.)',
                'original_amount': 'Original order amount',
                'filled_amount': 'Amount already filled',
                'remaining_amount': 'Amount still open',
                'average_price': 'Average execution price (if filled)',
                'created_at': 'Order creation timestamp',
                'updated_at': 'Last update timestamp',
                'broker_status': 'Detailed broker status information',
                'retrieval_timestamp': 'Status retrieval timestamp'
            },
            'caching': {
                'cache_expiry_seconds': self.cache_expiry_seconds,
                'supports_cache_control': True
            },
            'broker_status_mapping': {k: v.value for k, v in self.broker_status_mapping.items()},
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_status_statistics(self) -> Dict[str, Any]:
        """Status Retrieval Statistiken abrufen"""
        cache_size = len(self.status_cache)
        cache_hit_rate = 0.0
        
        # Cache Hit Rate berechnen (vereinfacht)
        if self.status_requests_count > 0:
            # Schätzung basierend auf Cache-Größe
            estimated_cache_hits = min(cache_size, self.status_requests_count)
            cache_hit_rate = estimated_cache_hits / self.status_requests_count
        
        return {
            'total_status_requests': self.status_requests_count,
            'cache_size': cache_size,
            'cache_hit_rate': cache_hit_rate,
            'cache_expiry_seconds': self.cache_expiry_seconds,
            'average_response_time': self.average_execution_time,
            'supported_broker_statuses': list(self.broker_status_mapping.keys())

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
        }