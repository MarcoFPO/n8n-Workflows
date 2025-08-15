"""
Order History Module - Single Function Module
Verantwortlich ausschließlich für Order History Retrieval Logic
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import timedelta
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderStatus, OrderSide, OrderType


class HistoryFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    instrument_code: Optional[str] = None
    status: Optional[OrderStatus] = None
    side: Optional[OrderSide] = None
    limit: int = 100
    offset: int = 0
    include_fills: bool = False


class OrderHistoryEntry(BaseModel):
    order_id: str
    status: OrderStatus
    instrument_code: str
    side: OrderSide
    type: OrderType
    original_amount: str
    filled_amount: str
    average_price: Optional[str] = None
    total_fees: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    fills: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = {}


class HistoryResponse(BaseModel):
    orders: List[OrderHistoryEntry]
    total_count: int
    has_more: bool
    filter_applied: HistoryFilter
    retrieval_timestamp: datetime


class OrderHistoryModule(SingleFunctionModule):
    """
    Single Function Module: Order History Retrieval
    Verantwortlichkeit: Ausschließlich Order-History-Abfrage-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_history", event_bus)
        
        # History Cache für Performance (speichert letzte Abfragen)
        self.history_cache = {}
        self.cache_expiry_seconds = 300  # 5 Minuten Cache
        self.history_requests_count = 0
        
        # Default Filter Values
        self.default_history_days = 30
        self.max_history_days = 365
        self.max_limit_per_request = 1000
        
        # Performance Tracking
        self.large_history_threshold = 500  # Orders als "large" betrachten
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order History Retrieval
        
        Args:
            input_data: {
                'history_filter': HistoryFilter dict,
                'credentials': broker credentials,
                'use_cache': optional cache usage flag
            }
            
        Returns:
            Dict mit Order-History-Information
        """
        history_filter_data = input_data.get('history_filter', {})
        credentials = input_data.get('credentials', {})
        use_cache = input_data.get('use_cache', True)
        
        # HistoryFilter parsieren
        try:
            history_filter = HistoryFilter(**history_filter_data)
        except Exception as e:
            raise ValueError(f'Invalid history filter format: {str(e)}')
        
        # Filter validieren und normalisieren
        normalized_filter = await self._normalize_history_filter(history_filter)
        
        # History abrufen (mit Cache-Option)
        history_response = await self._get_order_history_from_broker(
            normalized_filter, credentials, use_cache
        )
        
        return {
            'orders': [self._serialize_order_entry(entry) for entry in history_response.orders],
            'total_count': history_response.total_count,
            'has_more': history_response.has_more,
            'filter_applied': history_response.filter_applied.dict(),
            'retrieval_timestamp': history_response.retrieval_timestamp.isoformat(),
            'performance_info': {
                'is_large_result': len(history_response.orders) > self.large_history_threshold,
                'cached_result': use_cache and self._is_history_cached(normalized_filter)
            }
        }
    
    async def _normalize_history_filter(self, history_filter: HistoryFilter) -> HistoryFilter:
        """Filter normalisieren und validieren"""
        
        # Default Date Range setzen falls nicht angegeben
        if not history_filter.start_date:
            history_filter.start_date = datetime.now() - timedelta(days=self.default_history_days)
        
        if not history_filter.end_date:
            history_filter.end_date = datetime.now()
        
        # Date Range validieren
        if history_filter.start_date > history_filter.end_date:
            raise ValueError("start_date must be before end_date")
        
        # Max History Range prüfen
        history_days = (history_filter.end_date - history_filter.start_date).days
        if history_days > self.max_history_days:
            raise ValueError(f"History range ({history_days} days) exceeds maximum allowed ({self.max_history_days} days)")
        
        # Limit validieren
        if history_filter.limit > self.max_limit_per_request:
            self.logger.warning(f"Limit {history_filter.limit} exceeds maximum, using {self.max_limit_per_request}")
            history_filter.limit = self.max_limit_per_request
        
        # Offset validieren
        if history_filter.offset < 0:
            history_filter.offset = 0
        
        return history_filter
    
    async def _get_order_history_from_broker(self, history_filter: HistoryFilter,
                                           credentials: Dict[str, Any],
                                           use_cache: bool) -> HistoryResponse:
        """
        Order History vom Broker abrufen (mit Cache-Support)
        """
        self.history_requests_count += 1
        
        # Cache Check
        cache_key = self._generate_cache_key(history_filter)
        if use_cache and self._is_history_cached(history_filter):
            self.logger.debug(f"Using cached history result for filter")
            return self.history_cache[cache_key]['history_response']
        
        # History vom Broker abrufen
        try:
            history_response = await self._fetch_history_from_broker_api(
                history_filter, credentials
            )
            
            # In Cache speichern (nur für kleinere Results)
            if use_cache and len(history_response.orders) <= self.large_history_threshold:
                self.history_cache[cache_key] = {
                    'history_response': history_response,
                    'cached_at': datetime.now()
                }
            
            self.logger.info(f"Order history retrieved successfully",
                           orders_count=len(history_response.orders),
                           total_count=history_response.total_count,
                           has_more=history_response.has_more)
            
            return history_response
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve order history", error=str(e))
            raise
    
    async def _fetch_history_from_broker_api(self, history_filter: HistoryFilter,
                                           credentials: Dict[str, Any]) -> HistoryResponse:
        """
        Order History von Broker API abrufen (Bitpanda API Simulation)
        """
        
        # Simulate API call delay (history queries can be slow)
        import asyncio
        api_delay = 0.1 + min(history_filter.limit / 100, 2.0)  # 100ms base + scaling
        await asyncio.sleep(api_delay)
        
        # Simulate broker history response
        broker_history_data = await self._simulate_broker_history_response(history_filter)
        
        # Convert to internal format
        history_entries = []
        for broker_order in broker_history_data['orders']:
            history_entry = await self._convert_broker_order_to_history_entry(
                broker_order, history_filter.include_fills
            )
            history_entries.append(history_entry)
        
        # Create response
        history_response = HistoryResponse(
            orders=history_entries,
            total_count=broker_history_data['total_count'],
            has_more=broker_history_data['has_more'],
            filter_applied=history_filter,
            retrieval_timestamp=datetime.now()
        )
        
        return history_response
    
    async def _simulate_broker_history_response(self, history_filter: HistoryFilter) -> Dict[str, Any]:
        """Simuliert Broker API History Response"""
        import random
        
        # Simulate total count (würde normalerweise von Broker kommen)
        total_count = random.randint(50, 2000)
        
        # Generate orders for requested page
        orders_to_generate = min(history_filter.limit, total_count - history_filter.offset)
        orders_to_generate = max(0, orders_to_generate)
        
        has_more = (history_filter.offset + orders_to_generate) < total_count
        
        orders = []
        for i in range(orders_to_generate):
            order = await self._generate_mock_historical_order(history_filter, i)
            orders.append(order)
        
        return {
            'orders': orders,
            'total_count': total_count,
            'has_more': has_more
        }
    
    async def _generate_mock_historical_order(self, history_filter: HistoryFilter, index: int) -> Dict[str, Any]:
        """Generiert realistische historische Order-Daten"""
        import random
        
        # Time Range für Order
        time_range = (history_filter.end_date - history_filter.start_date).total_seconds()
        random_offset = random.uniform(0, time_range)
        created_at = history_filter.start_date + timedelta(seconds=random_offset)
        
        # Order Parameters
        instruments = ['BTC_EUR', 'ETH_EUR', 'ADA_EUR', 'DOT_EUR']
        if history_filter.instrument_code:
            instruments = [history_filter.instrument_code]
        
        sides = ['BUY', 'SELL']
        if history_filter.side:
            sides = [history_filter.side.value]
        
        statuses = ['FILLED', 'CANCELLED', 'PARTIALLY_FILLED', 'REJECTED']
        status_weights = [0.7, 0.15, 0.1, 0.05]  # Meist FILLED
        if history_filter.status:
            statuses = [history_filter.status.value]
            status_weights = [1.0]
        
        status = random.choices(statuses, weights=status_weights)[0]
        instrument = random.choice(instruments)
        side = random.choice(sides)
        order_type = random.choice(['MARKET', 'LIMIT'])
        
        # Order Amounts
        original_amount = round(random.uniform(0.001, 50.0), 8)
        
        if status == 'FILLED':
            filled_amount = original_amount
            completed_at = created_at + timedelta(minutes=random.randint(1, 30))
        elif status == 'PARTIALLY_FILLED':
            filled_amount = round(original_amount * random.uniform(0.1, 0.9), 8)
            completed_at = created_at + timedelta(minutes=random.randint(5, 120))
        elif status == 'CANCELLED':
            filled_amount = round(original_amount * random.uniform(0.0, 0.3), 8)
            completed_at = created_at + timedelta(minutes=random.randint(1, 60))
        else:  # REJECTED
            filled_amount = 0.0
            completed_at = created_at + timedelta(seconds=random.randint(1, 30))
        
        # Prices and Fees
        base_price = random.uniform(1000, 50000)
        average_price = str(round(base_price, 2)) if filled_amount > 0 else None
        
        total_fees = round(filled_amount * base_price * 0.0015, 6) if filled_amount > 0 else 0.0
        
        return {
            'order_id': f"HIST-{int(created_at.timestamp())}-{index:06d}",
            'status': status,
            'symbol': instrument,
            'side': side,
            'order_type': order_type,
            'original_amount': str(original_amount),
            'executed_amount': str(filled_amount),
            'average_price': average_price,
            'total_fees': str(total_fees),
            'created_at': created_at.isoformat(),
            'completed_at': completed_at.isoformat() if completed_at else None,
            'fills': self._generate_mock_fills(filled_amount, base_price) if history_filter.include_fills and filled_amount > 0 else None
        }
    
    def _generate_mock_fills(self, total_filled: float, base_price: float) -> List[Dict[str, Any]]:
        """Generiert realistische Fill-Details"""
        import random
        
        if total_filled <= 0:
            return []
        
        fills = []
        remaining = total_filled
        fill_count = random.randint(1, min(5, max(1, int(total_filled * 10))))
        
        for i in range(fill_count):
            if i == fill_count - 1:
                fill_amount = remaining
            else:
                max_fill = remaining * 0.8
                fill_amount = round(random.uniform(0.001, max_fill), 8)
                remaining -= fill_amount
            
            if fill_amount <= 0:
                break
            
            # Price Variation für verschiedene Fills
            price_variation = random.uniform(0.95, 1.05)
            fill_price = round(base_price * price_variation, 2)
            
            fills.append({
                'fill_id': f"FILL-{int(datetime.now().timestamp())}-{i:03d}",
                'amount': str(fill_amount),
                'price': str(fill_price),
                'timestamp': (datetime.now() - timedelta(seconds=random.randint(30, 300))).isoformat(),
                'fee': str(round(fill_amount * fill_price * 0.0015, 6))
            })
        
        return fills
    
    async def _convert_broker_order_to_history_entry(self, broker_order: Dict[str, Any],
                                                   include_fills: bool) -> OrderHistoryEntry:
        """Konvertiert Broker Order zu OrderHistoryEntry"""
        
        return OrderHistoryEntry(
            order_id=broker_order['order_id'],
            status=OrderStatus(broker_order['status']),
            instrument_code=broker_order['symbol'],
            side=OrderSide(broker_order['side']),
            type=OrderType(broker_order['order_type']),
            original_amount=broker_order['original_amount'],
            filled_amount=broker_order['executed_amount'],
            average_price=broker_order.get('average_price'),
            total_fees=broker_order['total_fees'],
            created_at=datetime.fromisoformat(broker_order['created_at']),
            completed_at=datetime.fromisoformat(broker_order['completed_at']) if broker_order.get('completed_at') else None,
            fills=broker_order.get('fills') if include_fills else None,
            metadata={
                'original_broker_data': broker_order
            }
        )
    
    def _serialize_order_entry(self, entry: OrderHistoryEntry) -> Dict[str, Any]:
        """OrderHistoryEntry zu Dict serialisieren"""
        return {
            'order_id': entry.order_id,
            'status': entry.status.value,
            'instrument_code': entry.instrument_code,
            'side': entry.side.value,
            'type': entry.type.value,
            'original_amount': entry.original_amount,
            'filled_amount': entry.filled_amount,
            'average_price': entry.average_price,
            'total_fees': entry.total_fees,
            'created_at': entry.created_at.isoformat(),
            'completed_at': entry.completed_at.isoformat() if entry.completed_at else None,
            'fills': entry.fills,
            'metadata': entry.metadata
        }
    
    def _generate_cache_key(self, history_filter: HistoryFilter) -> str:
        """Cache Key für HistoryFilter generieren"""
        import hashlib
        
        filter_str = f"{history_filter.start_date}-{history_filter.end_date}-{history_filter.instrument_code}-{history_filter.status}-{history_filter.side}-{history_filter.limit}-{history_filter.offset}-{history_filter.include_fills}"
        return hashlib.md5(filter_str.encode()).hexdigest()
    
    def _is_history_cached(self, history_filter: HistoryFilter) -> bool:
        """Prüft ob History im Cache verfügbar und gültig ist"""
        cache_key = self._generate_cache_key(history_filter)
        
        if cache_key not in self.history_cache:
            return False
        
        cache_entry = self.history_cache[cache_key]
        cache_age = (datetime.now() - cache_entry['cached_at']).total_seconds()
        
        return cache_age < self.cache_expiry_seconds
    
    def clear_history_cache(self):
        """History Cache leeren"""
        self.history_cache.clear()
        self.logger.debug("Cleared entire history cache")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_history',
            'description': 'Retrieves historical trading order information with filtering',
            'responsibility': 'Order history retrieval logic only',
            'input_parameters': {
                'history_filter': 'HistoryFilter object with date range, instrument, status filters',
                'credentials': 'Broker authentication credentials',
                'use_cache': 'Optional flag to enable/disable history caching'
            },
            'output_format': {
                'orders': 'List of historical orders matching filter criteria',
                'total_count': 'Total number of orders matching filter (beyond current page)',
                'has_more': 'Boolean indicating if more results are available',
                'filter_applied': 'The actual filter that was applied (normalized)',
                'retrieval_timestamp': 'History retrieval timestamp',
                'performance_info': 'Performance and caching information'
            },
            'filtering_options': {
                'date_range': 'start_date and end_date for time filtering',
                'instrument_code': 'Filter by specific trading pair',
                'status': 'Filter by order status',
                'side': 'Filter by BUY/SELL side',
                'pagination': 'limit and offset for result paging',
                'include_fills': 'Include detailed fill information'
            },
            'limits': {
                'default_history_days': self.default_history_days,
                'max_history_days': self.max_history_days,
                'max_limit_per_request': self.max_limit_per_request,
                'large_history_threshold': self.large_history_threshold
            },
            'caching': {
                'cache_expiry_seconds': self.cache_expiry_seconds,
                'caches_small_results_only': True
            },
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_history_statistics(self) -> Dict[str, Any]:
        """History Retrieval Statistiken abrufen"""
        cache_size = len(self.history_cache)
        
        return {
            'total_history_requests': self.history_requests_count,
            'cache_size': cache_size,
            'cache_expiry_seconds': self.cache_expiry_seconds,
            'average_response_time': self.average_execution_time,
            'large_result_threshold': self.large_history_threshold,
            'max_history_days': self.max_history_days,
            'default_history_days': self.default_history_days

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