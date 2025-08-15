"""
Order Daily Limit Module - Single Function Module
Verantwortlich ausschließlich für Daily Order Limit Calculation Logic
"""

import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule


class DailyOrderSummary(BaseModel):
    date: datetime
    total_order_amount: str
    total_order_value_eur: str
    order_count: int
    largest_order_amount: str
    smallest_order_amount: str
    order_distribution_by_instrument: Dict[str, int]
    average_order_size: str
    processed_orders: List[str]


class DailyLimitStatus(BaseModel):
    date: datetime
    current_total: str
    daily_limit: str
    remaining_limit: str
    limit_utilization_percent: float
    limit_exceeded: bool
    warning_threshold_reached: bool
    orders_contributing_to_total: int


class OrderDailyLimitModule(SingleFunctionModule):
    """
    Single Function Module: Order Daily Limit Calculator
    Verantwortlichkeit: Ausschließlich Daily-Order-Total-Calculation-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_daily_limit", event_bus)
        
        # Daily Calculation Cache
        self.daily_calculations = {}
        self.calculation_counter = 0
        
        # Daily Limits (konfigurierbar - hier Defaults)
        self.daily_limits = {
            'total_order_amount': 50.0,      # Max 50 BTC/ETH etc. per day
            'total_order_value_eur': 1000000.0,  # Max €1M per day
            'max_single_order_eur': 100000.0,    # Max €100k per single order
            'max_orders_per_day': 100             # Max 100 orders per day
        }
        
        # Warning Thresholds (Prozent der Limits)
        self.warning_thresholds = {
            'amount_warning': 0.8,    # 80% of amount limit
            'value_warning': 0.8,     # 80% of value limit
            'count_warning': 0.9      # 90% of count limit
        }
        
        # Instrument Pricing für Value Calculation (normalerweise aus Market Data)
        self.instrument_prices = {
            'BTC_EUR': 45000.0,
            'ETH_EUR': 2500.0,
            'ADA_EUR': 0.35,
            'DOT_EUR': 5.20,
            'AAPL': 150.0,
            'TSLA': 200.0,
            'MSFT': 300.0
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Daily Order Total Calculation
        
        Args:
            input_data: {
                'order_history': list of orders to calculate from,
                'target_date': optional date (default: today),
                'calculation_type': 'summary' oder 'limit_check',
                'proposed_order': optional new order to include in calculation
            }
            
        Returns:
            Dict mit Daily-Order-Calculation-Result
        """
        order_history = input_data.get('order_history', [])
        target_date_str = input_data.get('target_date')
        calculation_type = input_data.get('calculation_type', 'summary')
        proposed_order = input_data.get('proposed_order')
        
        # Target Date verarbeiten
        if target_date_str:
            target_date = datetime.fromisoformat(target_date_str).date()
        else:
            target_date = datetime.now().date()
        
        # Daily Order Calculation durchführen
        if calculation_type == 'summary':
            result = await self._calculate_daily_order_summary(order_history, target_date)
            
            return {
                'calculation_type': 'summary',
                'date': result.date.isoformat(),
                'total_order_amount': result.total_order_amount,
                'total_order_value_eur': result.total_order_value_eur,
                'order_count': result.order_count,
                'largest_order_amount': result.largest_order_amount,
                'smallest_order_amount': result.smallest_order_amount,
                'order_distribution_by_instrument': result.order_distribution_by_instrument,
                'average_order_size': result.average_order_size,
                'processed_orders': result.processed_orders
            }
        
        elif calculation_type == 'limit_check':
            result = await self._calculate_daily_limit_status(
                order_history, target_date, proposed_order
            )
            
            return {
                'calculation_type': 'limit_check',
                'date': result.date.isoformat(),
                'current_total': result.current_total,
                'daily_limit': result.daily_limit,
                'remaining_limit': result.remaining_limit,
                'limit_utilization_percent': result.limit_utilization_percent,
                'limit_exceeded': result.limit_exceeded,
                'warning_threshold_reached': result.warning_threshold_reached,
                'orders_contributing_to_total': result.orders_contributing_to_total
            }
        
        else:
            raise ValueError(f'Unknown calculation_type: {calculation_type}')
    
    async def _calculate_daily_order_summary(self, order_history: List[Dict], 
                                           target_date: datetime.date) -> DailyOrderSummary:
        """Berechnet Daily Order Summary"""
        self.calculation_counter += 1
        
        # Filter Orders für Target Date
        daily_orders = await self._filter_orders_by_date(order_history, target_date)
        
        if not daily_orders:
            return DailyOrderSummary(
                date=datetime.combine(target_date, datetime.min.time()),
                total_order_amount="0.0",
                total_order_value_eur="0.0",
                order_count=0,
                largest_order_amount="0.0",
                smallest_order_amount="0.0",
                order_distribution_by_instrument={},
                average_order_size="0.0",
                processed_orders=[]
            )
        
        # Calculations
        total_amount = Decimal('0')
        total_value_eur = Decimal('0')
        amounts = []
        instrument_distribution = {}
        processed_order_ids = []
        
        for order in daily_orders:
            order_data = order.get('order_data', {})
            order_id = order_data.get('order_id', 'UNKNOWN')
            instrument_code = order_data.get('instrument_code', 'UNKNOWN')
            amount = Decimal(str(order_data.get('amount', '0')))
            
            # Amount Accumulation
            total_amount += amount
            amounts.append(amount)
            
            # Value Calculation
            estimated_price = self.instrument_prices.get(instrument_code, 1000.0)
            order_value_eur = amount * Decimal(str(estimated_price))
            total_value_eur += order_value_eur
            
            # Distribution Tracking
            instrument_distribution[instrument_code] = instrument_distribution.get(instrument_code, 0) + 1
            processed_order_ids.append(order_id)
        
        # Summary Statistics
        largest_amount = max(amounts) if amounts else Decimal('0')
        smallest_amount = min(amounts) if amounts else Decimal('0')
        average_amount = total_amount / len(amounts) if amounts else Decimal('0')
        
        summary = DailyOrderSummary(
            date=datetime.combine(target_date, datetime.min.time()),
            total_order_amount=str(total_amount),
            total_order_value_eur=str(total_value_eur),
            order_count=len(daily_orders),
            largest_order_amount=str(largest_amount),
            smallest_order_amount=str(smallest_amount),
            order_distribution_by_instrument=instrument_distribution,
            average_order_size=str(average_amount),
            processed_orders=processed_order_ids
        )
        
        # Cache Result
        cache_key = f"{target_date.isoformat()}_{len(daily_orders)}"
        self.daily_calculations[cache_key] = summary
        
        self.logger.info(f"Daily order summary calculated",
                       date=target_date.isoformat(),
                       total_orders=len(daily_orders),
                       total_amount=str(total_amount),
                       total_value_eur=str(total_value_eur))
        
        return summary
    
    async def _calculate_daily_limit_status(self, order_history: List[Dict], 
                                          target_date: datetime.date,
                                          proposed_order: Optional[Dict] = None) -> DailyLimitStatus:
        """Berechnet Daily Limit Status mit optionalem proposed Order"""
        
        # Bestehende Orders für den Tag
        daily_orders = await self._filter_orders_by_date(order_history, target_date)
        
        # Current Totals berechnen
        current_amount = Decimal('0')
        current_value_eur = Decimal('0')
        current_count = len(daily_orders)
        
        for order in daily_orders:
            order_data = order.get('order_data', {})
            instrument_code = order_data.get('instrument_code', 'UNKNOWN')
            amount = Decimal(str(order_data.get('amount', '0')))
            
            current_amount += amount
            
            # Value Calculation
            estimated_price = self.instrument_prices.get(instrument_code, 1000.0)
            order_value_eur = amount * Decimal(str(estimated_price))
            current_value_eur += order_value_eur
        
        # Proposed Order hinzufügen falls vorhanden
        if proposed_order:
            proposed_instrument = proposed_order.get('instrument_code', 'UNKNOWN')
            proposed_amount = Decimal(str(proposed_order.get('amount', '0')))
            proposed_price = self.instrument_prices.get(proposed_instrument, 1000.0)
            
            current_amount += proposed_amount
            current_value_eur += proposed_amount * Decimal(str(proposed_price))
            current_count += 1
        
        # Limit Checks
        value_limit = Decimal(str(self.daily_limits['total_order_value_eur']))
        remaining_limit = max(Decimal('0'), value_limit - current_value_eur)
        
        # Utilization Percentage (basierend auf Value Limit)
        utilization_percent = float((current_value_eur / value_limit) * 100) if value_limit > 0 else 0.0
        
        # Limit Exceeded Check
        limit_exceeded = (
            current_value_eur > value_limit or
            current_count > self.daily_limits['max_orders_per_day']
        )
        
        # Warning Threshold Check
        warning_threshold_reached = (
            utilization_percent >= (self.warning_thresholds['value_warning'] * 100) or
            current_count >= (self.daily_limits['max_orders_per_day'] * self.warning_thresholds['count_warning'])
        )
        
        limit_status = DailyLimitStatus(
            date=datetime.combine(target_date, datetime.min.time()),
            current_total=str(current_value_eur),
            daily_limit=str(value_limit),
            remaining_limit=str(remaining_limit),
            limit_utilization_percent=round(utilization_percent, 2),
            limit_exceeded=limit_exceeded,
            warning_threshold_reached=warning_threshold_reached,
            orders_contributing_to_total=current_count
        )
        
        # Log Critical Status
        if limit_exceeded:
            self.logger.warning(f"Daily limit exceeded",
                              date=target_date.isoformat(),
                              current_value=str(current_value_eur),
                              limit=str(value_limit),
                              utilization=utilization_percent)
        elif warning_threshold_reached:
            self.logger.info(f"Daily limit warning threshold reached",
                           date=target_date.isoformat(),
                           utilization=utilization_percent)
        
        return limit_status
    
    async def _filter_orders_by_date(self, order_history: List[Dict], 
                                   target_date: datetime.date) -> List[Dict]:
        """Filtert Orders nach Target Date"""
        
        daily_orders = []
        
        for order in order_history:
            # Handle verschiedene Timestamp Formate
            order_timestamp = order.get('timestamp')
            
            if isinstance(order_timestamp, str):
                try:
                    order_date = datetime.fromisoformat(order_timestamp).date()
                except (ValueError, TypeError):
                    continue
            elif isinstance(order_timestamp, datetime):
                order_date = order_timestamp.date()
            else:
                # Fallback: Versuche aus order_data
                order_data = order.get('order_data', {})
                created_at = order_data.get('created_at')
                if created_at:
                    try:
                        order_date = datetime.fromisoformat(created_at).date()
                    except (ValueError, TypeError):
                        continue
                else:
                    continue
            
            # Date Match Check
            if order_date == target_date:
                daily_orders.append(order)
        
        return daily_orders
    
    def configure_daily_limits(self, limits: Dict[str, float]):
        """Konfiguriert Daily Limits"""
        for limit_key, limit_value in limits.items():
            if limit_key in self.daily_limits:
                self.daily_limits[limit_key] = float(limit_value)
                self.logger.info(f"Daily limit updated",
                               limit_type=limit_key,
                               new_value=limit_value)
    
    def configure_warning_thresholds(self, thresholds: Dict[str, float]):
        """Konfiguriert Warning Thresholds"""
        for threshold_key, threshold_value in thresholds.items():
            if threshold_key in self.warning_thresholds:
                if 0.0 <= threshold_value <= 1.0:
                    self.warning_thresholds[threshold_key] = float(threshold_value)
                    self.logger.info(f"Warning threshold updated",
                                   threshold_type=threshold_key,
                                   new_value=threshold_value)
                else:
                    self.logger.warning(f"Invalid warning threshold value",
                                      threshold_type=threshold_key,
                                      value=threshold_value)
    
    def update_instrument_prices(self, prices: Dict[str, float]):
        """Aktualisiert Instrument Prices für Value Calculation"""
        for instrument, price in prices.items():
            if price > 0:
                self.instrument_prices[instrument] = float(price)
                self.logger.debug(f"Instrument price updated",
                                instrument=instrument,
                                new_price=price)
    
    def get_current_daily_limits(self) -> Dict[str, Any]:
        """Gibt aktuelle Daily Limits zurück"""
        return {
            'daily_limits': self.daily_limits.copy(),
            'warning_thresholds': self.warning_thresholds.copy(),
            'instrument_prices': self.instrument_prices.copy()
        }
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_daily_limit',
            'description': 'Calculates daily order totals and limit status',
            'responsibility': 'Daily order total calculation logic only',
            'input_parameters': {
                'order_history': 'List of orders to calculate from',
                'target_date': 'Optional target date (default: today)',
                'calculation_type': 'Type of calculation: summary or limit_check',
                'proposed_order': 'Optional new order to include in limit calculation'
            },
            'output_format': {
                'summary': {
                    'total_order_amount': 'Sum of all order amounts',
                    'total_order_value_eur': 'Total EUR value of orders',
                    'order_count': 'Number of orders processed',
                    'order_distribution_by_instrument': 'Orders per instrument',
                    'average_order_size': 'Average order size'
                },
                'limit_check': {
                    'current_total': 'Current total EUR value',
                    'daily_limit': 'Configured daily limit',
                    'remaining_limit': 'Remaining available limit',
                    'limit_utilization_percent': 'Percentage of limit used',
                    'limit_exceeded': 'Whether limit is exceeded',
                    'warning_threshold_reached': 'Whether warning threshold reached'
                }
            },
            'calculation_types': ['summary', 'limit_check'],
            'daily_limits': self.daily_limits,
            'warning_thresholds': self.warning_thresholds,
            'supported_instruments': list(self.instrument_prices.keys()),
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_daily_calculation_statistics(self) -> Dict[str, Any]:
        """Daily Calculation Statistiken abrufen"""
        total_calculations = len(self.daily_calculations)
        
        if total_calculations == 0:
            return {
                'total_calculations': 0,
                'cached_calculations': 0,
                'average_processing_time': self.average_execution_time
            }
        
        # Calculation Distribution
        calculation_dates = []
        for calc in self.daily_calculations.values():
            calculation_dates.append(calc.date.date().isoformat())
        
        # Date Distribution
        date_counts = {}
        for date in calculation_dates:
            date_counts[date] = date_counts.get(date, 0) + 1
        
        return {
            'total_calculations': total_calculations,
            'cached_calculations': len(self.daily_calculations),
            'calculation_date_distribution': date_counts,
            'daily_limits_configured': self.daily_limits,
            'warning_thresholds_configured': self.warning_thresholds,
            'tracked_instruments': len(self.instrument_prices),
            'average_processing_time': self.average_execution_time

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