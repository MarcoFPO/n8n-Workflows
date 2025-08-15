"""
Active Orders Module - Single Function Module
Verantwortlich ausschließlich für Active Orders Retrieval Logic
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


class ActiveOrdersFilter(BaseModel):
    instrument_code: Optional[str] = None
    side: Optional[OrderSide] = None
    type: Optional[OrderType] = None
    min_amount: Optional[str] = None
    max_amount: Optional[str] = None
    limit: int = 50
    include_partially_filled: bool = True


class ActiveOrderInfo(BaseModel):
    order_id: str
    status: OrderStatus
    instrument_code: str
    side: OrderSide
    type: OrderType
    original_amount: str
    filled_amount: str
    remaining_amount: str
    price: Optional[str] = None
    stop_price: Optional[str] = None
    created_at: datetime
    last_update: datetime
    time_in_force: str
    priority_score: float  # For sorting/prioritization
    estimated_value: str  # EUR value estimation


class ActiveOrdersResponse(BaseModel):
    active_orders: List[ActiveOrderInfo]
    summary: Dict[str, Any]
    filter_applied: ActiveOrdersFilter
    retrieval_timestamp: datetime


class ActiveOrdersModule(SingleFunctionModule):
    """
    Single Function Module: Active Orders Retrieval
    Verantwortlichkeit: Ausschließlich Active-Orders-Abfrage-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("active_orders", event_bus)
        
        # Active Orders Cache für Performance
        self.active_orders_cache = None
        self.cache_expiry_seconds = 10  # 10 Sekunden Cache (aktive Orders ändern sich schnell)
        self.last_cache_update = None
        self.active_orders_requests_count = 0
        
        # Active Status Definition
        self.active_statuses = [
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.PENDING
        ]
        
        # Priority Scoring Weights
        self.priority_weights = {
            'age_weight': 0.3,        # Ältere Orders höhere Priorität
            'amount_weight': 0.4,     # Größere Orders höhere Priorität  
            'partial_fill_weight': 0.3  # Teilweise gefüllte Orders höhere Priorität
        }
        
        # Market Price Estimates (für Value Calculation)
        self.market_prices = {
            'BTC_EUR': Decimal('45000'),
            'ETH_EUR': Decimal('2500'),
            'ADA_EUR': Decimal('0.50'),
            'DOT_EUR': Decimal('25.00')
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Active Orders Retrieval
        
        Args:
            input_data: {
                'filter': ActiveOrdersFilter dict,
                'credentials': broker credentials,
                'use_cache': optional cache usage flag,
                'include_summary': optional summary calculation flag
            }
            
        Returns:
            Dict mit Active Orders Information
        """
        filter_data = input_data.get('filter', {})
        credentials = input_data.get('credentials', {})
        use_cache = input_data.get('use_cache', True)
        include_summary = input_data.get('include_summary', True)
        
        # Filter parsieren
        try:
            active_filter = ActiveOrdersFilter(**filter_data)
        except Exception as e:
            raise ValueError(f'Invalid active orders filter format: {str(e)}')
        
        # Active Orders abrufen (mit Cache-Option)
        active_orders_response = await self._get_active_orders_from_broker(
            active_filter, credentials, use_cache, include_summary
        )
        
        return {
            'active_orders': [self._serialize_active_order(order) for order in active_orders_response.active_orders],
            'summary': active_orders_response.summary,
            'filter_applied': active_orders_response.filter_applied.dict(),
            'retrieval_timestamp': active_orders_response.retrieval_timestamp.isoformat(),
            'cache_info': {
                'used_cache': use_cache and self._is_cache_valid(),
                'cache_age_seconds': self._get_cache_age_seconds()
            }
        }
    
    async def _get_active_orders_from_broker(self, active_filter: ActiveOrdersFilter,
                                           credentials: Dict[str, Any],
                                           use_cache: bool,
                                           include_summary: bool) -> ActiveOrdersResponse:
        """
        Active Orders vom Broker abrufen (mit Cache-Support)
        """
        self.active_orders_requests_count += 1
        
        # Cache Check
        if use_cache and self._is_cache_valid():
            self.logger.debug(f"Using cached active orders")
            cached_orders = self.active_orders_cache
            filtered_orders = self._apply_filter_to_cached_orders(cached_orders, active_filter)
        else:
            # Fresh Data vom Broker abrufen
            try:
                fresh_orders = await self._fetch_active_orders_from_broker_api(
                    active_filter, credentials
                )
                
                # Cache aktualisieren
                self.active_orders_cache = fresh_orders
                self.last_cache_update = datetime.now()
                
                filtered_orders = fresh_orders
                
            except Exception as e:
                self.logger.error(f"Failed to retrieve active orders", error=str(e))
                raise
        
        # Summary berechnen falls angefordert
        summary = {}
        if include_summary:
            summary = await self._calculate_active_orders_summary(filtered_orders)
        
        # Response erstellen
        active_orders_response = ActiveOrdersResponse(
            active_orders=filtered_orders,
            summary=summary,
            filter_applied=active_filter,
            retrieval_timestamp=datetime.now()
        )
        
        self.logger.info(f"Active orders retrieved successfully",
                       orders_count=len(filtered_orders),
                       used_cache=use_cache and self._is_cache_valid())
        
        return active_orders_response
    
    async def _fetch_active_orders_from_broker_api(self, active_filter: ActiveOrdersFilter,
                                                 credentials: Dict[str, Any]) -> List[ActiveOrderInfo]:
        """
        Active Orders von Broker API abrufen (Bitpanda API Simulation)
        """
        
        # Simulate API call delay
        import asyncio
        api_delay = 0.05 + (active_filter.limit / 100)  # Scaling mit Limit
        await asyncio.sleep(api_delay)
        
        # Simulate broker response
        broker_active_orders = await self._simulate_broker_active_orders(active_filter)
        
        # Convert to internal format
        active_orders = []
        for broker_order in broker_active_orders:
            active_order = await self._convert_broker_order_to_active_order(broker_order)
            active_orders.append(active_order)
        
        # Sort by priority (höchste Priorität zuerst)
        active_orders.sort(key=lambda x: x.priority_score, reverse=True)
        
        return active_orders
    
    async def _simulate_broker_active_orders(self, active_filter: ActiveOrdersFilter) -> List[Dict[str, Any]]:
        """Simuliert Broker API Active Orders Response"""
        import random
        
        # Simulate realistic number of active orders
        num_orders = random.randint(5, min(active_filter.limit, 30))
        
        orders = []
        for i in range(num_orders):
            order = await self._generate_mock_active_order(active_filter, i)
            orders.append(order)
        
        return orders
    
    async def _generate_mock_active_order(self, active_filter: ActiveOrdersFilter, index: int) -> Dict[str, Any]:
        """Generiert realistische aktive Order-Daten"""
        import random
        
        # Order Parameters (respektiert Filter)
        instruments = ['BTC_EUR', 'ETH_EUR', 'ADA_EUR', 'DOT_EUR']
        if active_filter.instrument_code:
            instruments = [active_filter.instrument_code]
        
        sides = ['BUY', 'SELL']
        if active_filter.side:
            sides = [active_filter.side.value]
        
        order_types = ['LIMIT', 'STOP', 'STOP_LIMIT']
        if active_filter.type:
            order_types = [active_filter.type.value]
        
        # Status (nur aktive)
        statuses = ['OPEN', 'PARTIALLY_FILLED', 'PENDING']
        if not active_filter.include_partially_filled:
            statuses = ['OPEN', 'PENDING']
        
        status = random.choice(statuses)
        instrument = random.choice(instruments)
        side = random.choice(sides)
        order_type = random.choice(order_types)
        
        # Order Amounts (respektiert min/max Filter)
        min_amount = float(active_filter.min_amount) if active_filter.min_amount else 0.001
        max_amount = float(active_filter.max_amount) if active_filter.max_amount else 50.0
        original_amount = round(random.uniform(min_amount, max_amount), 8)
        
        # Filled Amount basierend auf Status
        if status == 'PARTIALLY_FILLED':
            filled_amount = round(original_amount * random.uniform(0.1, 0.7), 8)
        else:
            filled_amount = 0.0
        
        remaining_amount = original_amount - filled_amount
        
        # Prices
        base_price = random.uniform(1000, 50000)
        price = str(round(base_price, 2)) if order_type in ['LIMIT', 'STOP_LIMIT'] else None
        stop_price = str(round(base_price * random.uniform(0.9, 1.1), 2)) if 'STOP' in order_type else None
        
        # Timestamps
        created_at = datetime.now() - datetime.timedelta(
            minutes=random.randint(1, 1440)  # 1 Minute bis 1 Tag alt
        )
        last_update = created_at + datetime.timedelta(
            minutes=random.randint(0, 60)  # Bis zu 1 Stunde nach Creation
        )
        
        return {
            'order_id': f"ACTIVE-{int(created_at.timestamp())}-{index:04d}",
            'status': status,
            'symbol': instrument,
            'side': side,
            'order_type': order_type,
            'original_amount': str(original_amount),
            'executed_amount': str(filled_amount),
            'remaining_amount': str(remaining_amount),
            'price': price,
            'stop_price': stop_price,
            'created_at': created_at.isoformat(),
            'last_update': last_update.isoformat(),
            'time_in_force': random.choice(['GTC', 'IOC', 'FOK'])
        }
    
    async def _convert_broker_order_to_active_order(self, broker_order: Dict[str, Any]) -> ActiveOrderInfo:
        """Konvertiert Broker Order zu ActiveOrderInfo"""
        
        # Priority Score berechnen
        priority_score = await self._calculate_priority_score(broker_order)
        
        # Estimated Value berechnen
        estimated_value = self._calculate_estimated_value(broker_order)
        
        return ActiveOrderInfo(
            order_id=broker_order['order_id'],
            status=OrderStatus(broker_order['status']),
            instrument_code=broker_order['symbol'],
            side=OrderSide(broker_order['side']),
            type=OrderType(broker_order['order_type']),
            original_amount=broker_order['original_amount'],
            filled_amount=broker_order['executed_amount'],
            remaining_amount=broker_order['remaining_amount'],
            price=broker_order.get('price'),
            stop_price=broker_order.get('stop_price'),
            created_at=datetime.fromisoformat(broker_order['created_at']),
            last_update=datetime.fromisoformat(broker_order['last_update']),
            time_in_force=broker_order['time_in_force'],
            priority_score=priority_score,
            estimated_value=estimated_value
        )
    
    async def _calculate_priority_score(self, broker_order: Dict[str, Any]) -> float:
        """Berechnet Priority Score für Order-Sortierung"""
        
        created_at = datetime.fromisoformat(broker_order['created_at'])
        age_hours = (datetime.now() - created_at).total_seconds() / 3600
        
        # Age Score (0-1, ältere Orders = höhere Score)
        age_score = min(age_hours / 24, 1.0)  # Max 1.0 nach 24h
        
        # Amount Score (0-1, größere Orders = höhere Score)
        amount = float(broker_order['remaining_amount'])
        amount_score = min(amount / 10.0, 1.0)  # Max 1.0 bei 10+ Units
        
        # Partial Fill Score (0-1, teilweise gefüllte = höhere Score)
        original = float(broker_order['original_amount'])
        executed = float(broker_order['executed_amount'])
        partial_fill_score = executed / original if original > 0 else 0
        
        # Weighted Score
        priority_score = (
            self.priority_weights['age_weight'] * age_score +
            self.priority_weights['amount_weight'] * amount_score +
            self.priority_weights['partial_fill_weight'] * partial_fill_score
        )
        
        return round(priority_score, 4)
    
    def _calculate_estimated_value(self, broker_order: Dict[str, Any]) -> str:
        """Berechnet geschätzten EUR-Wert der Order"""
        try:
            remaining_amount = Decimal(broker_order['remaining_amount'])
            instrument = broker_order['symbol']
            
            # Market Price schätzen
            market_price = self.market_prices.get(instrument, Decimal('1000'))
            
            # Order Price verwenden falls verfügbar und LIMIT order
            if broker_order.get('price') and broker_order['order_type'] in ['LIMIT', 'STOP_LIMIT']:
                order_price = Decimal(broker_order['price'])
                # Nehme den konservativeren Wert
                if broker_order['side'] == 'BUY':
                    estimated_price = min(order_price, market_price)
                else:  # SELL
                    estimated_price = max(order_price, market_price)
            else:
                estimated_price = market_price
            
            estimated_value = remaining_amount * estimated_price
            return str(round(estimated_value, 2))
            
        except Exception as e:
            self.logger.debug(f"Error calculating estimated value: {str(e)}")
            return "0.00"
    
    def _apply_filter_to_cached_orders(self, cached_orders: List[ActiveOrderInfo],
                                     active_filter: ActiveOrdersFilter) -> List[ActiveOrderInfo]:
        """Wendet Filter auf gecachte Orders an"""
        filtered = cached_orders
        
        # Instrument Filter
        if active_filter.instrument_code:
            filtered = [o for o in filtered if o.instrument_code == active_filter.instrument_code]
        
        # Side Filter
        if active_filter.side:
            filtered = [o for o in filtered if o.side == active_filter.side]
        
        # Type Filter
        if active_filter.type:
            filtered = [o for o in filtered if o.type == active_filter.type]
        
        # Amount Filter
        if active_filter.min_amount:
            min_decimal = Decimal(active_filter.min_amount)
            filtered = [o for o in filtered if Decimal(o.remaining_amount) >= min_decimal]
        
        if active_filter.max_amount:
            max_decimal = Decimal(active_filter.max_amount)
            filtered = [o for o in filtered if Decimal(o.remaining_amount) <= max_decimal]
        
        # Partially Filled Filter
        if not active_filter.include_partially_filled:
            filtered = [o for o in filtered if o.status != OrderStatus.PARTIALLY_FILLED]
        
        # Limit
        filtered = filtered[:active_filter.limit]
        
        return filtered
    
    async def _calculate_active_orders_summary(self, active_orders: List[ActiveOrderInfo]) -> Dict[str, Any]:
        """Berechnet Summary für Active Orders"""
        
        if not active_orders:
            return {
                'total_count': 0,
                'total_estimated_value_eur': '0.00',
                'by_status': {},
                'by_instrument': {},
                'by_side': {},
                'oldest_order_age_hours': 0,
                'highest_priority_score': 0.0
            }
        
        total_value = Decimal('0')
        status_counts = {}
        instrument_counts = {}
        side_counts = {}
        
        oldest_age = 0
        highest_priority = 0.0
        
        for order in active_orders:
            # Total Value
            total_value += Decimal(order.estimated_value)
            
            # Status Count
            status_key = order.status.value
            status_counts[status_key] = status_counts.get(status_key, 0) + 1
            
            # Instrument Count
            instrument_counts[order.instrument_code] = instrument_counts.get(order.instrument_code, 0) + 1
            
            # Side Count
            side_key = order.side.value
            side_counts[side_key] = side_counts.get(side_key, 0) + 1
            
            # Age
            age_hours = (datetime.now() - order.created_at).total_seconds() / 3600
            oldest_age = max(oldest_age, age_hours)
            
            # Priority
            highest_priority = max(highest_priority, order.priority_score)
        
        return {
            'total_count': len(active_orders),
            'total_estimated_value_eur': str(round(total_value, 2)),
            'by_status': status_counts,
            'by_instrument': instrument_counts,
            'by_side': side_counts,
            'oldest_order_age_hours': round(oldest_age, 1),
            'highest_priority_score': highest_priority
        }
    
    def _serialize_active_order(self, order: ActiveOrderInfo) -> Dict[str, Any]:
        """ActiveOrderInfo zu Dict serialisieren"""
        return {
            'order_id': order.order_id,
            'status': order.status.value,
            'instrument_code': order.instrument_code,
            'side': order.side.value,
            'type': order.type.value,
            'original_amount': order.original_amount,
            'filled_amount': order.filled_amount,
            'remaining_amount': order.remaining_amount,
            'price': order.price,
            'stop_price': order.stop_price,
            'created_at': order.created_at.isoformat(),
            'last_update': order.last_update.isoformat(),
            'time_in_force': order.time_in_force,
            'priority_score': order.priority_score,
            'estimated_value': order.estimated_value
        }
    
    def _is_cache_valid(self) -> bool:
        """Prüft ob Cache gültig ist"""
        if not self.active_orders_cache or not self.last_cache_update:
            return False
        
        cache_age = (datetime.now() - self.last_cache_update).total_seconds()
        return cache_age < self.cache_expiry_seconds
    
    def _get_cache_age_seconds(self) -> float:
        """Gibt Cache-Alter in Sekunden zurück"""
        if not self.last_cache_update:
            return 0.0
        
        return (datetime.now() - self.last_cache_update).total_seconds()
    
    def clear_active_orders_cache(self):
        """Active Orders Cache leeren"""
        self.active_orders_cache = None
        self.last_cache_update = None
        self.logger.debug("Cleared active orders cache")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'active_orders',
            'description': 'Retrieves currently active (open, partially filled) trading orders',
            'responsibility': 'Active orders retrieval and prioritization logic only',
            'input_parameters': {
                'filter': 'ActiveOrdersFilter object with filtering criteria',
                'credentials': 'Broker authentication credentials',
                'use_cache': 'Optional flag to enable/disable short-term caching',
                'include_summary': 'Optional flag to include summary statistics'
            },
            'output_format': {
                'active_orders': 'List of currently active orders sorted by priority',
                'summary': 'Summary statistics about active orders',
                'filter_applied': 'The filter that was applied',
                'retrieval_timestamp': 'Orders retrieval timestamp',
                'cache_info': 'Cache usage and age information'
            },
            'filtering_options': {
                'instrument_code': 'Filter by specific trading pair',
                'side': 'Filter by BUY/SELL side',
                'type': 'Filter by order type (LIMIT, STOP, etc.)',
                'amount_range': 'Filter by min/max order amounts',
                'include_partially_filled': 'Include partially filled orders'
            },
            'active_statuses': [status.value for status in self.active_statuses],
            'priority_scoring': {
                'factors': ['order_age', 'order_amount', 'partial_fill_percentage'],
                'weights': self.priority_weights
            },
            'caching': {
                'cache_expiry_seconds': self.cache_expiry_seconds,
                'cache_type': 'short_term_active_orders'
            },
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_active_orders_statistics(self) -> Dict[str, Any]:
        """Active Orders Statistiken abrufen"""
        cache_valid = self._is_cache_valid()
        cache_size = len(self.active_orders_cache) if self.active_orders_cache else 0
        
        return {
            'total_active_orders_requests': self.active_orders_requests_count,
            'cache_valid': cache_valid,
            'cache_size': cache_size,
            'cache_age_seconds': self._get_cache_age_seconds(),
            'cache_expiry_seconds': self.cache_expiry_seconds,
            'average_response_time': self.average_execution_time,
            'priority_weights': self.priority_weights

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