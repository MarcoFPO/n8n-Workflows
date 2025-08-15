"""
Trading Handler - Single Function Module
Verantwortlich ausschließlich für Trading Order Management Logic
"""

from typing import Dict, Any, List, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, timedelta, BaseModel, structlog
)
from modules.single_function_module_base import SingleFunctionModule
from shared.event_bus import Event, EventType


class TradingRequest(BaseModel):
    request_type: str  # 'create_order', 'cancel_order', 'get_orders', 'get_order_history', 'modify_order'
    order_data: Optional[Dict[str, Any]] = None
    order_id: Optional[str] = None
    status_filter: Optional[str] = None  # 'active', 'completed', 'cancelled', 'all'
    limit: Optional[int] = None


class TradingOrder(BaseModel):
    order_id: str
    symbol: str
    order_type: str  # 'market', 'limit', 'stop', 'stop_limit'
    side: str  # 'buy', 'sell'
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = 'GTC'  # 'GTC', 'IOC', 'FOK', 'DAY'
    status: str  # 'pending', 'active', 'partially_filled', 'filled', 'cancelled', 'rejected'
    filled_amount: float = 0.0
    remaining_amount: Optional[float] = None
    average_price: Optional[float] = None
    fees: Optional[float] = None
    created_timestamp: datetime
    updated_timestamp: Optional[datetime] = None
    executed_timestamp: Optional[datetime] = None
    source: str = "frontend"


class OrderExecutionResult(BaseModel):
    execution_successful: bool
    order_id: str
    execution_price: Optional[float] = None
    executed_amount: float
    remaining_amount: float
    fees_charged: float
    execution_timestamp: datetime
    execution_status: str  # 'partial', 'complete', 'failed'
    market_impact: Optional[float] = None


class TradingResult(BaseModel):
    trading_successful: bool
    active_orders: List[TradingOrder]
    order_history: List[TradingOrder]
    order_details: Optional[TradingOrder] = None
    execution_result: Optional[OrderExecutionResult] = None
    trading_statistics: Dict[str, Any]
    risk_warnings: List[str]
    trading_timestamp: datetime


class TradingHandler(SingleFunctionModule):
    """
    Single Function Module: Trading Order Management
    Verantwortlichkeit: Ausschließlich Trading-Order-Management-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("trading_handler", event_bus)
        
        # Active Orders Storage
        self.active_orders = {
            "order_001": TradingOrder(
                order_id="order_001",
                symbol="BTC",
                order_type="limit",
                side="buy",
                amount=0.1,
                price=42500.00,
                time_in_force="GTC",
                status="active",
                filled_amount=0.0,
                remaining_amount=0.1,
                created_timestamp=datetime.now() - timedelta(hours=2),
                source="frontend"
            ),
            "order_002": TradingOrder(
                order_id="order_002",
                symbol="ETH",
                order_type="limit",
                side="sell",
                amount=1.5,
                price=2450.00,
                time_in_force="GTC",
                status="partially_filled",
                filled_amount=0.8,
                remaining_amount=0.7,
                average_price=2448.50,
                fees=2.45,
                created_timestamp=datetime.now() - timedelta(hours=4),
                updated_timestamp=datetime.now() - timedelta(hours=1),
                source="frontend"
            ),
            "order_003": TradingOrder(
                order_id="order_003",
                symbol="AAPL",
                order_type="stop",
                side="sell",
                amount=10.0,
                stop_price=178.00,
                time_in_force="GTC",
                status="active",
                filled_amount=0.0,
                remaining_amount=10.0,
                created_timestamp=datetime.now() - timedelta(minutes=30),
                source="frontend"
            )
        }
        
        # Order History Storage
        self.order_history = [
            TradingOrder(
                order_id="order_h001",
                symbol="BTC",
                order_type="market",
                side="buy",
                amount=0.05,
                price=None,
                time_in_force="IOC",
                status="filled",
                filled_amount=0.05,
                remaining_amount=0.0,
                average_price=43125.50,
                fees=10.78,
                created_timestamp=datetime.now() - timedelta(days=1),
                executed_timestamp=datetime.now() - timedelta(days=1, seconds=15),
                source="frontend"
            ),
            TradingOrder(
                order_id="order_h002",
                symbol="ETH",
                order_type="limit",
                side="sell",
                amount=2.0,
                price=2400.00,
                time_in_force="GTC",
                status="filled",
                filled_amount=2.0,
                remaining_amount=0.0,
                average_price=2401.25,
                fees=9.61,
                created_timestamp=datetime.now() - timedelta(days=2),
                executed_timestamp=datetime.now() - timedelta(days=2, hours=3),
                source="frontend"
            ),
            TradingOrder(
                order_id="order_h003",
                symbol="TSLA",
                order_type="limit",
                side="buy",
                amount=5.0,
                price=245.00,
                time_in_force="DAY",
                status="cancelled",
                filled_amount=0.0,
                remaining_amount=5.0,
                created_timestamp=datetime.now() - timedelta(days=3),
                updated_timestamp=datetime.now() - timedelta(days=3, hours=6),
                source="frontend"
            )
        ]
        
        # Trading Configuration
        self.trading_config = {
            'max_active_orders': 50,
            'default_time_in_force': 'GTC',
            'enable_risk_checks': True,
            'max_order_amount_per_symbol': {
                'BTC': 5.0,
                'ETH': 50.0,
                'AAPL': 1000.0,
                'TSLA': 500.0
            },
            'min_order_amounts': {
                'BTC': 0.001,
                'ETH': 0.01,
                'AAPL': 1.0,
                'TSLA': 1.0
            },
            'supported_order_types': ['market', 'limit', 'stop', 'stop_limit'],
            'supported_time_in_force': ['GTC', 'IOC', 'FOK', 'DAY'],
            'fee_structure': {
                'maker_fee_percent': 0.1,
                'taker_fee_percent': 0.15,
                'minimum_fee': 0.01
            },
            'enable_paper_trading': True,
            'risk_management': {
                'max_portfolio_risk_percent': 10.0,
                'max_position_size_percent': 5.0,
                'require_confirmation_above': 10000.0
            }
        }
        
        # Trading Statistics
        self.trading_stats = {
            'orders_created_today': 3,
            'orders_executed_today': 1,
            'orders_cancelled_today': 0,
            'total_volume_today': 2150.75,
            'total_fees_today': 3.22,
            'successful_execution_rate': 85.5,
            'average_execution_time_seconds': 2.3,
            'active_symbols': ['BTC', 'ETH', 'AAPL'],
            'most_traded_symbol': 'BTC',
            'largest_order_today': 2150.75
        }
        
        # Trading Processing History
        self.trading_history = []
        self.trading_counter = 0
        
        # Order ID Counter
        self.order_id_counter = 4
        
        # Risk Assessment Cache
        self.risk_assessments = {}
        
        # Market Data Cache (for risk calculations)
        self.market_data_cache = {
            'BTC': {'price': 43250.00, 'volatility': 0.045, 'last_update': datetime.now()},
            'ETH': {'price': 2385.75, 'volatility': 0.055, 'last_update': datetime.now()},
            'AAPL': {'price': 182.50, 'volatility': 0.025, 'last_update': datetime.now()},
            'TSLA': {'price': 248.75, 'volatility': 0.065, 'last_update': datetime.now()}
        }
        
        # Order Execution Simulator
        self.execution_simulator = {
            'success_rate': 0.95,
            'average_slippage_percent': 0.05,
            'execution_delay_seconds': (1, 5),
            'partial_fill_probability': 0.15
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Trading Order Management
        
        Args:
            input_data: {
                'request_type': required string ('create_order', 'cancel_order', 'get_orders', 'get_order_history', 'modify_order'),
                'order_data': optional dict for order creation/modification,
                'order_id': optional string for order-specific operations,
                'status_filter': optional string for filtering orders,
                'limit': optional int for limiting results,
                'include_risk_analysis': optional bool (default: true),
                'simulate_execution': optional bool (default: true),
                'skip_validation': optional bool (default: false)
            }
            
        Returns:
            Dict mit Trading-Result
        """
        start_time = datetime.now()
        
        try:
            # Trading Request erstellen
            trading_request = TradingRequest(
                request_type=input_data.get('request_type'),
                order_data=input_data.get('order_data'),
                order_id=input_data.get('order_id'),
                status_filter=input_data.get('status_filter', 'all'),
                limit=input_data.get('limit')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid trading request: {str(e)}'
            }
        
        include_risk_analysis = input_data.get('include_risk_analysis', True)
        simulate_execution = input_data.get('simulate_execution', True)
        skip_validation = input_data.get('skip_validation', False)
        
        # Trading Processing
        trading_result = await self._process_trading_request(
            trading_request, include_risk_analysis, simulate_execution, skip_validation
        )
        
        # Statistics Update
        self.trading_counter += 1
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Trading History
        self.trading_history.append({
            'timestamp': datetime.now(),
            'request_type': trading_request.request_type,
            'order_id': trading_request.order_id,
            'trading_successful': trading_result.trading_successful,
            'active_orders_count': len(trading_result.active_orders),
            'warnings_count': len(trading_result.risk_warnings),
            'processing_time_ms': processing_time_ms,
            'trading_id': self.trading_counter
        })
        
        # Limit History
        if len(self.trading_history) > 500:
            self.trading_history.pop(0)
        
        # Event Publishing für Trading Events
        await self._publish_trading_event(trading_result, trading_request)
        
        self.logger.info(f"Trading request processed",
                       request_type=trading_request.request_type,
                       order_id=trading_request.order_id,
                       trading_successful=trading_result.trading_successful,
                       active_orders_count=len(trading_result.active_orders),
                       warnings_count=len(trading_result.risk_warnings),
                       processing_time_ms=round(processing_time_ms, 2),
                       trading_id=self.trading_counter)
        
        return {
            'success': True,
            'trading_successful': trading_result.trading_successful,
            'active_orders': [{
                'order_id': order.order_id,
                'symbol': order.symbol,
                'order_type': order.order_type,
                'side': order.side,
                'amount': order.amount,
                'price': order.price,
                'stop_price': order.stop_price,
                'time_in_force': order.time_in_force,
                'status': order.status,
                'filled_amount': order.filled_amount,
                'remaining_amount': order.remaining_amount,
                'average_price': order.average_price,
                'fees': order.fees,
                'created_timestamp': order.created_timestamp.isoformat(),
                'updated_timestamp': order.updated_timestamp.isoformat() if order.updated_timestamp else None,
                'executed_timestamp': order.executed_timestamp.isoformat() if order.executed_timestamp else None,
                'source': order.source
            } for order in trading_result.active_orders],
            'order_history': [{
                'order_id': order.order_id,
                'symbol': order.symbol,
                'order_type': order.order_type,
                'side': order.side,
                'amount': order.amount,
                'price': order.price,
                'status': order.status,
                'filled_amount': order.filled_amount,
                'average_price': order.average_price,
                'fees': order.fees,
                'created_timestamp': order.created_timestamp.isoformat(),
                'executed_timestamp': order.executed_timestamp.isoformat() if order.executed_timestamp else None
            } for order in trading_result.order_history[-10:]],  # Last 10 orders
            'order_details': {
                'order_id': trading_result.order_details.order_id,
                'symbol': trading_result.order_details.symbol,
                'order_type': trading_result.order_details.order_type,
                'side': trading_result.order_details.side,
                'amount': trading_result.order_details.amount,
                'price': trading_result.order_details.price,
                'status': trading_result.order_details.status,
                'created_timestamp': trading_result.order_details.created_timestamp.isoformat()
            } if trading_result.order_details else None,
            'execution_result': {
                'execution_successful': trading_result.execution_result.execution_successful,
                'order_id': trading_result.execution_result.order_id,
                'execution_price': trading_result.execution_result.execution_price,
                'executed_amount': trading_result.execution_result.executed_amount,
                'remaining_amount': trading_result.execution_result.remaining_amount,
                'fees_charged': trading_result.execution_result.fees_charged,
                'execution_timestamp': trading_result.execution_result.execution_timestamp.isoformat(),
                'execution_status': trading_result.execution_result.execution_status,
                'market_impact': trading_result.execution_result.market_impact
            } if trading_result.execution_result else None,
            'trading_statistics': trading_result.trading_statistics,
            'risk_warnings': trading_result.risk_warnings,
            'trading_timestamp': trading_result.trading_timestamp.isoformat()
        }
    
    async def _process_trading_request(self, request: TradingRequest,
                                     include_risk_analysis: bool,
                                     simulate_execution: bool,
                                     skip_validation: bool) -> TradingResult:
        """Verarbeitet Trading Request komplett"""
        
        risk_warnings = []
        execution_result = None
        order_details = None
        
        if request.request_type == 'create_order':
            # Neue Order erstellen
            if not request.order_data:
                risk_warnings.append('No order data provided for create_order')
                trading_successful = False
            else:
                order_details, execution_result = await self._create_order(
                    request.order_data, include_risk_analysis, simulate_execution, skip_validation
                )
                trading_successful = order_details is not None
                
        elif request.request_type == 'cancel_order':
            # Order stornieren
            if not request.order_id:
                risk_warnings.append('No order ID provided for cancel_order')
                trading_successful = False
            else:
                order_details = await self._cancel_order(request.order_id)
                trading_successful = order_details is not None
                if not trading_successful:
                    risk_warnings.append(f'Order {request.order_id} not found or cannot be cancelled')
                    
        elif request.request_type == 'modify_order':
            # Order modifizieren
            if not request.order_id or not request.order_data:
                risk_warnings.append('Order ID and order data required for modify_order')
                trading_successful = False
            else:
                order_details = await self._modify_order(request.order_id, request.order_data, skip_validation)
                trading_successful = order_details is not None
                if not trading_successful:
                    risk_warnings.append(f'Order {request.order_id} not found or cannot be modified')
                    
        elif request.request_type in ['get_orders', 'get_order_history']:
            # Orders abrufen (immer erfolgreich)
            trading_successful = True
            
        else:
            risk_warnings.append(f'Unknown request type: {request.request_type}')
            trading_successful = False
        
        # Active Orders abrufen (gefiltert)
        active_orders = await self._get_filtered_orders('active', request.status_filter, request.limit)
        
        # Order History abrufen (gefiltert)
        order_history = await self._get_filtered_orders('history', request.status_filter, request.limit)
        
        # Risk Warnings für Portfolio hinzufügen
        if include_risk_analysis:
            portfolio_warnings = await self._assess_portfolio_risk()
            risk_warnings.extend(portfolio_warnings)
        
        # Trading Statistics aktualisieren
        updated_stats = await self._update_trading_statistics()
        
        return TradingResult(
            trading_successful=trading_successful,
            active_orders=active_orders,
            order_history=order_history,
            order_details=order_details,
            execution_result=execution_result,
            trading_statistics=updated_stats,
            risk_warnings=risk_warnings,
            trading_timestamp=datetime.now()
        )
    
    async def _create_order(self, order_data: Dict[str, Any],
                          include_risk_analysis: bool,
                          simulate_execution: bool,
                          skip_validation: bool) -> tuple[Optional[TradingOrder], Optional[OrderExecutionResult]]:
        """Erstellt neue Trading Order"""
        
        # Order Validation
        if not skip_validation:
            validation_result = await self._validate_order(order_data)
            if not validation_result['valid']:
                self.logger.error(f"Order validation failed: {validation_result['errors']}")
                return None, None
        
        # Risk Assessment
        if include_risk_analysis:
            risk_result = await self._assess_order_risk(order_data)
            if risk_result['risk_level'] == 'high' and not skip_validation:
                self.logger.error(f"Order risk too high: {risk_result['warnings']}")
                return None, None
        
        # Order ID generieren
        self.order_id_counter += 1
        order_id = f"order_{self.order_id_counter:03d}"
        
        # Trading Order erstellen
        trading_order = TradingOrder(
            order_id=order_id,
            symbol=order_data['symbol'].upper(),
            order_type=order_data['order_type'],
            side=order_data['side'],
            amount=float(order_data['amount']),
            price=float(order_data['price']) if order_data.get('price') else None,
            stop_price=float(order_data['stop_price']) if order_data.get('stop_price') else None,
            time_in_force=order_data.get('time_in_force', self.trading_config['default_time_in_force']),
            status='pending',
            filled_amount=0.0,
            remaining_amount=float(order_data['amount']),
            created_timestamp=datetime.now(),
            source=order_data.get('source', 'frontend')
        )
        
        # Order zu Active Orders hinzufügen
        self.active_orders[order_id] = trading_order
        
        # Execution Simulation
        execution_result = None
        if simulate_execution and self.trading_config['enable_paper_trading']:
            execution_result = await self._simulate_order_execution(trading_order)
            if execution_result.execution_successful:
                # Update Order basierend auf Execution
                trading_order.status = 'filled' if execution_result.execution_status == 'complete' else 'partially_filled'
                trading_order.filled_amount = execution_result.executed_amount
                trading_order.remaining_amount = execution_result.remaining_amount
                trading_order.average_price = execution_result.execution_price
                trading_order.fees = execution_result.fees_charged
                trading_order.executed_timestamp = execution_result.execution_timestamp
                trading_order.updated_timestamp = execution_result.execution_timestamp
                
                # Move to history if completely filled
                if execution_result.execution_status == 'complete':
                    self.order_history.append(trading_order)
                    del self.active_orders[order_id]
            else:
                trading_order.status = 'rejected'
                trading_order.updated_timestamp = datetime.now()
        else:
            # Mark as active for real trading
            trading_order.status = 'active'
        
        # Statistics Update
        self.trading_stats['orders_created_today'] += 1
        if execution_result and execution_result.execution_successful:
            self.trading_stats['orders_executed_today'] += 1
            self.trading_stats['total_volume_today'] += execution_result.executed_amount * (execution_result.execution_price or 0)
            self.trading_stats['total_fees_today'] += execution_result.fees_charged
        
        return trading_order, execution_result
    
    async def _cancel_order(self, order_id: str) -> Optional[TradingOrder]:
        """Storniert Trading Order"""
        
        if order_id not in self.active_orders:
            return None
        
        order = self.active_orders[order_id]
        
        # Nur stornierbare Orders
        if order.status not in ['pending', 'active', 'partially_filled']:
            return None
        
        # Order stornieren
        order.status = 'cancelled'
        order.updated_timestamp = datetime.now()
        
        # Move to history
        self.order_history.append(order)
        del self.active_orders[order_id]
        
        # Statistics Update
        self.trading_stats['orders_cancelled_today'] += 1
        
        return order
    
    async def _modify_order(self, order_id: str, order_modifications: Dict[str, Any],
                          skip_validation: bool) -> Optional[TradingOrder]:
        """Modifiziert bestehende Trading Order"""
        
        if order_id not in self.active_orders:
            return None
        
        order = self.active_orders[order_id]
        
        # Nur modifizierbare Orders
        if order.status not in ['pending', 'active']:
            return None
        
        # Modifications anwenden
        if 'price' in order_modifications:
            order.price = float(order_modifications['price'])
        
        if 'amount' in order_modifications:
            new_amount = float(order_modifications['amount'])
            if new_amount >= order.filled_amount:  # Amount kann nicht unter filled_amount sein
                order.amount = new_amount
                order.remaining_amount = new_amount - order.filled_amount
        
        if 'time_in_force' in order_modifications:
            order.time_in_force = order_modifications['time_in_force']
        
        if 'stop_price' in order_modifications:
            order.stop_price = float(order_modifications['stop_price'])
        
        # Validation
        if not skip_validation:
            validation_result = await self._validate_order({
                'symbol': order.symbol,
                'order_type': order.order_type,
                'side': order.side,
                'amount': order.amount,
                'price': order.price,
                'stop_price': order.stop_price
            })
            if not validation_result['valid']:
                return None
        
        order.updated_timestamp = datetime.now()
        
        return order
    
    async def _get_filtered_orders(self, source: str, status_filter: str,
                                 limit: Optional[int]) -> List[TradingOrder]:
        """Holt gefilterte Orders"""
        
        if source == 'active':
            orders = list(self.active_orders.values())
        else:  # history
            orders = self.order_history.copy()
        
        # Status Filter
        if status_filter != 'all':
            if status_filter == 'active':
                orders = [o for o in orders if o.status in ['pending', 'active', 'partially_filled']]
            elif status_filter == 'completed':
                orders = [o for o in orders if o.status == 'filled']
            elif status_filter == 'cancelled':
                orders = [o for o in orders if o.status == 'cancelled']
            else:
                orders = [o for o in orders if o.status == status_filter]
        
        # Sort by timestamp (newest first)
        orders.sort(key=lambda x: x.created_timestamp, reverse=True)
        
        # Limit
        if limit:
            orders = orders[:limit]
        
        return orders
    
    async def _validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validiert Order Data"""
        
        errors = []
        warnings = []
        
        # Required Fields
        required_fields = ['symbol', 'order_type', 'side', 'amount']
        for field in required_fields:
            if field not in order_data or order_data[field] is None:
                errors.append(f'Missing required field: {field}')
        
        if errors:
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        symbol = order_data['symbol'].upper()
        order_type = order_data['order_type']
        side = order_data['side']
        amount = float(order_data['amount'])
        price = float(order_data['price']) if order_data.get('price') else None
        
        # Order Type Validation
        if order_type not in self.trading_config['supported_order_types']:
            errors.append(f'Unsupported order type: {order_type}')
        
        # Side Validation
        if side not in ['buy', 'sell']:
            errors.append(f'Invalid side: {side}')
        
        # Amount Validation
        min_amount = self.trading_config['min_order_amounts'].get(symbol, 0.001)
        if amount < min_amount:
            errors.append(f'Amount below minimum: {amount} < {min_amount}')
        
        max_amount = self.trading_config['max_order_amount_per_symbol'].get(symbol, float('inf'))
        if amount > max_amount:
            errors.append(f'Amount above maximum: {amount} > {max_amount}')
        
        # Price Validation für Limit/Stop Orders
        if order_type in ['limit', 'stop', 'stop_limit'] and price is None:
            errors.append(f'Price required for {order_type} orders')
        
        if price is not None and price <= 0:
            errors.append('Price must be positive')
        
        # Market Data Check
        if symbol in self.market_data_cache:
            market_price = self.market_data_cache[symbol]['price']
            
            if price and order_type == 'limit':
                price_deviation = abs(price - market_price) / market_price
                if price_deviation > 0.1:  # 10% deviation
                    warnings.append(f'Limit price deviates {price_deviation:.1%} from market price')
        else:
            warnings.append(f'No market data available for {symbol}')
        
        # Active Orders Check
        active_orders_count = len([o for o in self.active_orders.values() if o.symbol == symbol])
        if active_orders_count >= 10:
            warnings.append(f'Many active orders for {symbol}: {active_orders_count}')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    async def _assess_order_risk(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Bewertet Order Risk"""
        
        symbol = order_data['symbol'].upper()
        amount = float(order_data['amount'])
        side = order_data['side']
        
        risk_factors = []
        risk_score = 0.0
        
        # Market Data Risk
        if symbol in self.market_data_cache:
            volatility = self.market_data_cache[symbol]['volatility']
            if volatility > 0.05:  # 5% volatility
                risk_factors.append(f'High volatility: {volatility:.1%}')
                risk_score += volatility * 10
        
        # Position Size Risk
        current_price = self.market_data_cache.get(symbol, {}).get('price', 100)
        order_value = amount * current_price
        
        max_position_value = self.trading_config['risk_management']['require_confirmation_above']
        if order_value > max_position_value:
            risk_factors.append(f'Large order value: €{order_value:,.2f}')
            risk_score += (order_value / max_position_value) * 2
        
        # Portfolio Concentration Risk
        symbol_orders = [o for o in self.active_orders.values() if o.symbol == symbol]
        if len(symbol_orders) > 5:
            risk_factors.append(f'High concentration in {symbol}: {len(symbol_orders)} orders')
            risk_score += len(symbol_orders) * 0.2
        
        # Time-based Risk
        current_hour = datetime.now().hour
        if current_hour < 9 or current_hour > 17:  # Outside market hours
            risk_factors.append('Trading outside main market hours')
            risk_score += 1.0
        
        # Determine Risk Level
        if risk_score < 2:
            risk_level = 'low'
        elif risk_score < 5:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'warnings': risk_factors
        }
    
    async def _simulate_order_execution(self, order: TradingOrder) -> OrderExecutionResult:
        """Simuliert Order Execution"""
        
        import random
        
        # Execution Success Rate
        success_rate = self.execution_simulator['success_rate']
        if random.random() > success_rate:
            return OrderExecutionResult(
                execution_successful=False,
                order_id=order.order_id,
                executed_amount=0.0,
                remaining_amount=order.amount,
                fees_charged=0.0,
                execution_timestamp=datetime.now(),
                execution_status='failed'
            )
        
        # Market Price
        market_price = self.market_data_cache.get(order.symbol, {}).get('price', order.price or 100)
        
        # Execution Price (with slippage)
        slippage_percent = random.uniform(0, self.execution_simulator['average_slippage_percent'])
        if order.order_type == 'market':
            if order.side == 'buy':
                execution_price = market_price * (1 + slippage_percent)
            else:
                execution_price = market_price * (1 - slippage_percent)
        else:
            execution_price = order.price or market_price
        
        # Partial Fill Simulation
        if random.random() < self.execution_simulator['partial_fill_probability']:
            fill_percent = random.uniform(0.3, 0.8)  # 30-80% fill
            executed_amount = order.amount * fill_percent
            execution_status = 'partial'
        else:
            executed_amount = order.amount
            execution_status = 'complete'
        
        remaining_amount = order.amount - executed_amount
        
        # Fee Calculation
        order_value = executed_amount * execution_price
        fee_percent = self.trading_config['fee_structure']['taker_fee_percent'] / 100
        fees_charged = max(
            order_value * fee_percent,
            self.trading_config['fee_structure']['minimum_fee']
        )
        
        # Market Impact (simplified)
        market_impact = order_value / 10000000 * 0.01  # 0.01% impact per 10M volume
        
        return OrderExecutionResult(
            execution_successful=True,
            order_id=order.order_id,
            execution_price=round(execution_price, 2),
            executed_amount=executed_amount,
            remaining_amount=remaining_amount,
            fees_charged=round(fees_charged, 2),
            execution_timestamp=datetime.now(),
            execution_status=execution_status,
            market_impact=round(market_impact, 4) if market_impact > 0.0001 else None
        )
    
    async def _assess_portfolio_risk(self) -> List[str]:
        """Bewertet Portfolio Risk"""
        
        warnings = []
        
        # Active Orders Count
        active_count = len(self.active_orders)
        if active_count > self.trading_config['max_active_orders'] * 0.8:
            warnings.append(f'High number of active orders: {active_count}')
        
        # Concentration Risk
        symbol_counts = {}
        for order in self.active_orders.values():
            symbol_counts[order.symbol] = symbol_counts.get(order.symbol, 0) + 1
        
        for symbol, count in symbol_counts.items():
            if count > 5:
                warnings.append(f'High concentration in {symbol}: {count} orders')
        
        # Large Order Values
        large_orders = []
        confirmation_threshold = self.trading_config['risk_management']['require_confirmation_above']
        
        for order in self.active_orders.values():
            if order.price:
                order_value = order.amount * order.price
                if order_value > confirmation_threshold:
                    large_orders.append((order.symbol, order_value))
        
        if large_orders:
            warnings.append(f'Large orders pending: {len(large_orders)} orders > €{confirmation_threshold:,.0f}')
        
        return warnings
    
    async def _update_trading_statistics(self) -> Dict[str, Any]:
        """Aktualisiert Trading Statistics"""
        
        current_stats = self.trading_stats.copy()
        
        # Active Orders Stats
        current_stats['active_orders_count'] = len(self.active_orders)
        
        # Symbol Distribution
        active_symbols = list(set(order.symbol for order in self.active_orders.values()))
        current_stats['active_symbols'] = active_symbols
        current_stats['active_symbols_count'] = len(active_symbols)
        
        # Order Types Distribution
        order_types = {}
        for order in self.active_orders.values():
            order_types[order.order_type] = order_types.get(order.order_type, 0) + 1
        current_stats['order_types_distribution'] = order_types
        
        # Side Distribution
        buy_orders = sum(1 for o in self.active_orders.values() if o.side == 'buy')
        sell_orders = len(self.active_orders) - buy_orders
        current_stats['buy_orders_count'] = buy_orders
        current_stats['sell_orders_count'] = sell_orders
        
        # Execution Rate (based on history)
        total_historical = len(self.order_history)
        filled_orders = sum(1 for o in self.order_history if o.status == 'filled')
        if total_historical > 0:
            current_stats['historical_execution_rate'] = round((filled_orders / total_historical) * 100, 1)
        
        return current_stats
    
    async def _publish_trading_event(self, result: TradingResult,
                                   request: TradingRequest):
        """Published Trading Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        # Nur für Order-modifizierende Events publishen
        if request.request_type in ['create_order', 'cancel_order', 'modify_order']:
            from event_bus import Event
            
            event = Event(
                event_type="trading_order_processed",
                stream_id=f"trading-{self.trading_counter}",
                data={
                    'request_type': request.request_type,
                    'order_id': request.order_id or (result.order_details.order_id if result.order_details else None),
                    'trading_successful': result.trading_successful,
                    'active_orders_count': len(result.active_orders),
                    'execution_successful': result.execution_result.execution_successful if result.execution_result else None,
                    'risk_warnings_count': len(result.risk_warnings),
                    'trading_timestamp': result.trading_timestamp.isoformat()
                },
                source="trading_handler"
            )
            
            await self.event_bus.publish(event)
    
    async def _setup_event_subscriptions(self):
        """
        Setup Event-Bus subscriptions for trading updates
        Event-Bus Compliance: Subscribe to relevant events instead of direct calls
        """
        if not self.event_bus or not self.event_bus.connected:
            return
        
        try:
            # Subscribe to trading requests
            await self.event_bus.subscribe(
                EventType.TRADING_REQUEST.value,
                self._handle_trading_request,
                f"trading_request_{self.module_name}"
            )
            
            # Subscribe to order requests
            await self.event_bus.subscribe(
                EventType.ORDER_REQUEST.value,
                self._handle_order_request,
                f"order_request_{self.module_name}"
            )
            
            # Subscribe to system health requests
            await self.event_bus.subscribe(
                EventType.SYSTEM_HEALTH_REQUEST.value,
                self._handle_health_event,
                f"trading_health_{self.module_name}"
            )
            
            self.logger.info("Trading event subscriptions established")
            
        except Exception as e:
            self.logger.error(f"Failed to setup event subscriptions: {e}")
    
    async def _handle_trading_request(self, event: Event):
        """
        Handle trading request events
        Event-Bus Compliance: Process trading requests via events
        """
        try:
            request_data = event.data
            
            # Process trading request
            result = await self.execute_function(request_data)
            
            # Send response via event-bus
            response_event = Event(
                event_type=EventType.TRADING_RESPONSE.value,
                stream_id=event.stream_id,
                data=result,
                source=self.module_name,
                correlation_id=event.correlation_id
            )
            
            await self.event_bus.publish(response_event)
            self.logger.debug("Trading response sent via event")
            
        except Exception as e:
            self.logger.error(f"Failed to handle trading request: {e}")
    
    async def _handle_order_request(self, event: Event):
        """
        Handle order request events
        Event-Bus Compliance: Process order requests via events
        """
        try:
            request_data = event.data
            
            # Map order request to trading request format
            trading_request_data = {
                'request_type': request_data.get('request_type', 'create_order'),
                'order_data': request_data.get('order_data', {}),
                'order_id': request_data.get('order_id')
            }
            
            # Process order request
            result = await self.execute_function(trading_request_data)
            
            # Send response via event-bus
            response_event = Event(
                event_type=EventType.ORDER_RESPONSE.value,
                stream_id=event.stream_id,
                data=result,
                source=self.module_name,
                correlation_id=event.correlation_id
            )
            
            await self.event_bus.publish(response_event)
            self.logger.debug("Order response sent via event")
            
        except Exception as e:
            self.logger.error(f"Failed to handle order request: {e}")
    
    async def _handle_health_event(self, event: Event):
        """
        Handle system health request events
        Event-Bus Compliance: Respond to health checks via events
        """
        try:
            request_data = event.data
            
            if request_data.get('request_type') == 'trading_health':
                # Calculate trading health metrics
                trading_stats = await self._update_trading_statistics()
                portfolio_warnings = await self._assess_portfolio_risk()
                
                # Respond with trading health status
                health_response = Event(
                    event_type=EventType.SYSTEM_HEALTH_RESPONSE.value,
                    stream_id=f"trading-health-{event.stream_id}",
                    data={
                        'module': 'trading_handler',
                        'status': 'healthy' if len(portfolio_warnings) == 0 else 'warning',
                        'active_orders': len(self.active_orders),
                        'historical_orders': len(self.order_history),
                        'active_symbols': trading_stats.get('active_symbols_count', 0),
                        'portfolio_warnings': portfolio_warnings,
                        'execution_rate': trading_stats.get('historical_execution_rate', 0),
                        'last_order_timestamp': max([order.timestamp for order in self.active_orders.values()], default=datetime.now()).isoformat()
                    },
                    source=self.module_name,
                    correlation_id=event.correlation_id
                )
                
                await self.event_bus.publish(health_response)
                self.logger.debug("Trading health response sent via event")
            
        except Exception as e:
            self.logger.error(f"Failed to handle health event: {e}")
    
    async def process_event(self, event: Event):
        """
        Process incoming events - Event-Bus Compliance
        """
        try:
            if event.event_type == EventType.TRADING_REQUEST.value:
                await self._handle_trading_request(event)
            
            elif event.event_type == EventType.ORDER_REQUEST.value:
                await self._handle_order_request(event)
            
            elif event.event_type == EventType.SYSTEM_HEALTH_REQUEST.value:
                await self._handle_health_event(event)
            
            else:
                self.logger.debug(f"Unhandled event type: {event.event_type}")
        
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_type}: {e}")
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """Gibt Trading Summary zurück"""
        
        # Order Status Distribution
        status_distribution = {}
        for order in self.active_orders.values():
            status = order.status
            status_distribution[status] = status_distribution.get(status, 0) + 1
        
        # Average Order Age
        total_age = sum(
            (datetime.now() - order.created_timestamp).total_seconds() / 3600  # hours
            for order in self.active_orders.values()
        )
        avg_order_age = total_age / len(self.active_orders) if self.active_orders else 0
        
        # Portfolio Value (estimated)
        total_portfolio_value = 0
        for order in self.active_orders.values():
            if order.price and order.side == 'buy':
                total_portfolio_value += order.remaining_amount * order.price
        
        return {
            'active_orders_count': len(self.active_orders),
            'order_history_count': len(self.order_history),
            'status_distribution': status_distribution,
            'average_order_age_hours': round(avg_order_age, 1),
            'estimated_portfolio_value': round(total_portfolio_value, 2),
            'orders_created_today': self.trading_stats['orders_created_today'],
            'orders_executed_today': self.trading_stats['orders_executed_today'],
            'orders_cancelled_today': self.trading_stats['orders_cancelled_today'],
            'total_volume_today': round(self.trading_stats['total_volume_today'], 2),
            'total_fees_today': round(self.trading_stats['total_fees_today'], 2),
            'paper_trading_enabled': self.trading_config['enable_paper_trading'],
            'risk_checks_enabled': self.trading_config['enable_risk_checks'],
            'max_active_orders': self.trading_config['max_active_orders']
        }
    
    def configure_trading(self, config_updates: Dict[str, Any]):
        """Aktualisiert Trading Configuration"""
        
        for config_key, config_value in config_updates.items():
            if config_key in self.trading_config:
                self.trading_config[config_key] = config_value
                self.logger.info(f"Trading configuration updated",
                               config_key=config_key,
                               new_value=config_value)
    
    def reset_trading_stats(self):
        """Reset Trading Statistics (Administrative Function)"""
        
        self.trading_stats = {
            'orders_created_today': 0,
            'orders_executed_today': 0,
            'orders_cancelled_today': 0,
            'total_volume_today': 0.0,
            'total_fees_today': 0.0,
            'successful_execution_rate': 0.0,
            'average_execution_time_seconds': 0.0,
            'active_symbols': [],
            'most_traded_symbol': None,
            'largest_order_today': 0.0
        }
        
        self.logger.warning("Trading statistics reset")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'trading_handler',
            'description': 'Complete trading order management with risk assessment and execution simulation',
            'responsibility': 'Trading order management logic only',
            'input_parameters': {
                'request_type': 'Required request type (create_order, cancel_order, get_orders, get_order_history, modify_order)',
                'order_data': 'Optional order data for creation/modification',
                'order_id': 'Optional order ID for order-specific operations',
                'status_filter': 'Optional status filter for order retrieval',
                'limit': 'Optional limit for results',
                'include_risk_analysis': 'Whether to include risk analysis (default: true)',
                'simulate_execution': 'Whether to simulate order execution (default: true)',
                'skip_validation': 'Whether to skip order validation (default: false)'
            },
            'output_format': {
                'trading_successful': 'Whether trading operation was successful',
                'active_orders': 'List of active trading orders',
                'order_history': 'List of historical orders',
                'order_details': 'Details of specific order if applicable',
                'execution_result': 'Execution result if order was executed',
                'trading_statistics': 'Current trading statistics',
                'risk_warnings': 'List of risk warnings if any',
                'trading_timestamp': 'Timestamp of trading operation'
            },
            'supported_request_types': ['create_order', 'cancel_order', 'get_orders', 'get_order_history', 'modify_order'],
            'supported_order_types': self.trading_config['supported_order_types'],
            'supported_time_in_force': self.trading_config['supported_time_in_force'],
            'trading_configuration': self.trading_config,
            'risk_management': self.trading_config['risk_management'],
            'fee_structure': self.trading_config['fee_structure'],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_trading_statistics(self) -> Dict[str, Any]:
        """Trading Handler Module Statistiken"""
        total_requests = len(self.trading_history)
        
        if total_requests == 0:
            return {
                'total_requests': 0,
                'active_orders_count': len(self.active_orders),
                'order_history_count': len(self.order_history)
            }
        
        # Success Rate
        successful_requests = sum(1 for h in self.trading_history if h['trading_successful'])
        success_rate = round((successful_requests / total_requests) * 100, 1) if total_requests > 0 else 0
        
        # Request Type Distribution
        request_type_distribution = {}
        for request in self.trading_history:
            req_type = request['request_type']
            request_type_distribution[req_type] = request_type_distribution.get(req_type, 0) + 1
        
        # Order Processing Statistics
        orders_with_warnings = sum(1 for h in self.trading_history if h['warnings_count'] > 0)
        warning_rate = round((orders_with_warnings / total_requests) * 100, 1) if total_requests > 0 else 0
        
        # Historical Order Performance
        filled_orders = sum(1 for order in self.order_history if order.status == 'filled')
        cancelled_orders = sum(1 for order in self.order_history if order.status == 'cancelled')
        execution_rate = round((filled_orders / len(self.order_history)) * 100, 1) if self.order_history else 0
        
        # Recent Activity
        recent_requests = [
            h for h in self.trading_history
            if (datetime.now() - h['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate_percent': success_rate,
            'recent_requests_last_hour': len(recent_requests),
            'request_type_distribution': dict(sorted(
                request_type_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'orders_with_warnings': orders_with_warnings,
            'warning_rate_percent': warning_rate,
            'active_orders_count': len(self.active_orders),
            'order_history_count': len(self.order_history),
            'historical_execution_rate_percent': execution_rate,
            'filled_orders_count': filled_orders,
            'cancelled_orders_count': cancelled_orders,
            'supported_symbols': list(self.market_data_cache.keys()),
            'paper_trading_mode': self.trading_config['enable_paper_trading'],
            'average_processing_time': self.average_execution_time
        }