"""
Order Execution Module - Single Function Module
Verantwortlich ausschließlich für Order Execution Logic
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, Any, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from datetime import timedelta
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderRequest, OrderResponse, OrderStatus, OrderSide


class ExecutionResult(BaseModel):
    execution_id: str
    order_id: str
    status: OrderStatus
    filled_amount: str
    average_price: str
    execution_time: datetime
    broker_response: Dict[str, Any]
    fees: Dict[str, str]  # {'trading_fee': '0.1', 'network_fee': '0.001'}


class OrderExecutionModule(SingleFunctionModule):
    """
    Single Function Module: Order Execution
    Verantwortlichkeit: Ausschließlich Order-Execution-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_execution", event_bus)
        
        # Execution Configuration
        self.execution_counter = 0
        self.active_executions = {}
        self.completed_executions = {}
        
        # Trading Fees Configuration (Bitpanda Pro Simulation)
        self.trading_fees = {
            'BTC_EUR': Decimal('0.0015'),  # 0.15%
            'ETH_EUR': Decimal('0.0015'),  # 0.15%
            'ADA_EUR': Decimal('0.002'),   # 0.2%
            'DOT_EUR': Decimal('0.002')    # 0.2%
        }
        
        # Market Simulation Data
        self.market_prices = {
            'BTC_EUR': Decimal('45000'),
            'ETH_EUR': Decimal('2500'),
            'ADA_EUR': Decimal('0.50'),
            'DOT_EUR': Decimal('25.00')
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order Execution
        
        Args:
            input_data: {
                'order_request': OrderRequest dict,
                'credentials': broker credentials,
                'execution_strategy': optional execution parameters
            }
            
        Returns:
            Dict mit Execution-Result
        """
        order_request_data = input_data.get('order_request')
        credentials = input_data.get('credentials', {})
        execution_strategy = input_data.get('execution_strategy', {})
        
        if not order_request_data:
            raise ValueError('No order request provided for execution')
        
        # OrderRequest parsieren
        try:
            order_request = OrderRequest(**order_request_data)
        except Exception as e:
            raise ValueError(f'Invalid order request format: {str(e)}')
        
        # Order ausführen
        execution_result = await self._execute_order_with_broker(
            order_request, credentials, execution_strategy
        )
        
        # Execution Result in Cache speichern
        self.completed_executions[execution_result.execution_id] = execution_result
        
        return {
            'execution_id': execution_result.execution_id,
            'order_id': execution_result.order_id,
            'status': execution_result.status.value,
            'filled_amount': execution_result.filled_amount,
            'average_price': execution_result.average_price,
            'execution_time': execution_result.execution_time.isoformat(),
            'fees': execution_result.fees,
            'broker_response': execution_result.broker_response
        }
    
    async def _execute_order_with_broker(self, order_request: OrderRequest, 
                                       credentials: Dict[str, Any],
                                       execution_strategy: Dict[str, Any]) -> ExecutionResult:
        """
        Order bei Broker ausführen (Bitpanda API Simulation)
        """
        self.execution_counter += 1
        execution_id = f"EXEC-{int(time.time())}-{self.execution_counter:04d}"
        order_id = f"ORD-{execution_id}"
        
        # Execution als aktiv markieren
        self.active_executions[execution_id] = {
            'start_time': datetime.now(),
            'order_request': order_request,
            'status': 'executing'
        }
        
        try:
            # Simulate market execution
            execution_result = await self._simulate_market_execution(
                execution_id, order_id, order_request, execution_strategy
            )
            
            # Execution als abgeschlossen markieren
            del self.active_executions[execution_id]
            
            self.logger.info(f"Order executed successfully",
                           execution_id=execution_id,
                           order_id=order_id,
                           filled_amount=execution_result.filled_amount,
                           average_price=execution_result.average_price)
            
            return execution_result
            
        except Exception as e:
            # Execution als fehlgeschlagen markieren
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            self.logger.error(f"Order execution failed",
                            execution_id=execution_id,
                            error=str(e))
            raise
    
    async def _simulate_market_execution(self, execution_id: str, order_id: str,
                                       order_request: OrderRequest,
                                       execution_strategy: Dict[str, Any]) -> ExecutionResult:
        """
        Simuliert Market Order Execution mit realistischen Parametern
        """
        # Execution Delay simulieren (Market Latenz)
        execution_delay = self._calculate_execution_delay(order_request)
        await asyncio.sleep(execution_delay)
        
        # Market Price und Slippage berechnen
        execution_price = await self._get_execution_price(order_request)
        
        # Fill-Amount berechnen (normalerweise 100% für Market Orders)
        fill_percentage = self._calculate_fill_percentage(order_request, execution_strategy)
        filled_amount = Decimal(order_request.amount) * fill_percentage
        
        # Trading Fees berechnen
        fees = await self._calculate_trading_fees(order_request, filled_amount, execution_price)
        
        # Execution Status bestimmen
        if fill_percentage >= Decimal('1.0'):
            status = OrderStatus.FILLED
        elif fill_percentage > Decimal('0.0'):
            status = OrderStatus.PARTIALLY_FILLED
        else:
            status = OrderStatus.REJECTED
        
        # Broker Response simulieren
        broker_response = {
            'exchange': 'bitpanda_pro',
            'order_book_depth': self._simulate_order_book_depth(order_request.instrument_code),
            'market_impact': float(abs(execution_price - self.market_prices.get(order_request.instrument_code, execution_price)) / execution_price),
            'execution_venue': 'primary_exchange',
            'settlement_date': (datetime.now() + timedelta(days=2)).isoformat()
        }
        
        execution_result = ExecutionResult(
            execution_id=execution_id,
            order_id=order_id,
            status=status,
            filled_amount=str(filled_amount),
            average_price=str(execution_price),
            execution_time=datetime.now(),
            broker_response=broker_response,
            fees=fees
        )
        
        return execution_result
    
    def _calculate_execution_delay(self, order_request: OrderRequest) -> float:
        """Berechnet realistische Execution-Latenz"""
        base_delay = 0.1  # 100ms base latency
        
        # Größere Orders brauchen länger
        amount = Decimal(order_request.amount)
        size_factor = min(float(amount) / 1000.0, 2.0)
        
        # Market Orders sind schneller als Limit Orders
        type_factor = 1.0 if order_request.type.value == 'MARKET' else 1.5
        
        # Instrument-spezifische Latenz
        instrument_factors = {
            'BTC_EUR': 1.0,
            'ETH_EUR': 1.1,
            'ADA_EUR': 1.3,
            'DOT_EUR': 1.2
        }
        instrument_factor = instrument_factors.get(order_request.instrument_code, 1.5)
        
        total_delay = base_delay * size_factor * type_factor * instrument_factor
        return min(total_delay, 5.0)  # Max 5 seconds
    
    async def _get_execution_price(self, order_request: OrderRequest) -> Decimal:
        """Berechnet Execution Price mit Slippage"""
        base_price = self.market_prices.get(order_request.instrument_code, Decimal('1000'))
        
        # Market Impact/Slippage simulieren
        amount = Decimal(order_request.amount)
        
        # Größere Orders haben mehr Slippage
        slippage_factor = min(float(amount) / 10000.0, 0.002)  # Max 0.2% slippage
        
        if order_request.side == OrderSide.BUY:
            # Buy orders execute at slightly higher price
            execution_price = base_price * (Decimal('1.0') + Decimal(str(slippage_factor)))
        else:
            # Sell orders execute at slightly lower price
            execution_price = base_price * (Decimal('1.0') - Decimal(str(slippage_factor)))
        
        return execution_price.quantize(Decimal('0.01'))  # 2 decimal places
    
    def _calculate_fill_percentage(self, order_request: OrderRequest, 
                                 execution_strategy: Dict[str, Any]) -> Decimal:
        """Berechnet Fill Percentage (normalerweise 100% für Market Orders)"""
        
        # Market Orders werden normalerweise vollständig gefüllt
        if order_request.type.value == 'MARKET':
            return Decimal('1.0')
        
        # Limit Orders können partiell gefüllt werden
        if order_request.type.value == 'LIMIT':
            # Simulation: 90% Chance auf vollständige Füllung
            import random
            if random.random() < 0.9:
                return Decimal('1.0')
            else:
                # Partielle Füllung zwischen 50-99%
                partial_fill = 0.5 + random.random() * 0.49
                return Decimal(str(partial_fill)).quantize(Decimal('0.001'))
        
        return Decimal('1.0')
    
    async def _calculate_trading_fees(self, order_request: OrderRequest, 
                                    filled_amount: Decimal, 
                                    execution_price: Decimal) -> Dict[str, str]:
        """Berechnet Trading Fees"""
        
        # Trading Fee basierend auf Instrument
        fee_rate = self.trading_fees.get(order_request.instrument_code, Decimal('0.002'))
        
        # Trade Value berechnen
        trade_value = filled_amount * execution_price
        trading_fee = trade_value * fee_rate
        
        # Network Fee (für Crypto withdrawals)
        network_fees = {
            'BTC_EUR': Decimal('0.0005'),
            'ETH_EUR': Decimal('0.005'),
            'ADA_EUR': Decimal('1.0'),
            'DOT_EUR': Decimal('0.1')
        }
        network_fee = network_fees.get(order_request.instrument_code, Decimal('0.001'))
        
        return {
            'trading_fee': str(trading_fee.quantize(Decimal('0.00001'))),
            'network_fee': str(network_fee),
            'total_fees': str((trading_fee + network_fee).quantize(Decimal('0.00001')))
        }
    
    def _simulate_order_book_depth(self, instrument_code: str) -> Dict[str, Any]:
        """Simuliert Order Book Depth für Broker Response"""
        return {
            'bid_depth': '125000.50',
            'ask_depth': '89000.25',
            'spread': '0.05',
            'last_trade_size': '1.25000'
        }
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_execution',
            'description': 'Executes validated trading orders with broker',
            'responsibility': 'Order execution logic only',
            'input_parameters': {
                'order_request': 'OrderRequest object to execute',
                'credentials': 'Broker authentication credentials',
                'execution_strategy': 'Optional execution parameters'
            },
            'output_format': {
                'execution_id': 'Unique execution identifier',
                'order_id': 'Associated order identifier',
                'status': 'Execution status (FILLED, PARTIALLY_FILLED, etc.)',
                'filled_amount': 'Amount successfully filled',
                'average_price': 'Average execution price',
                'execution_time': 'Execution timestamp',
                'fees': 'Trading and network fees',
                'broker_response': 'Detailed broker response data'
            },
            'supported_brokers': ['bitpanda_pro'],
            'trading_fees': {k: str(v) for k, v in self.trading_fees.items()},
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Execution Statistiken abrufen"""
        total_executions = len(self.completed_executions)
        active_executions = len(self.active_executions)
        
        if total_executions == 0:
            return {
                'total_executions': 0,
                'active_executions': active_executions,
                'success_rate': 0.0,
                'average_execution_time': 0.0
            }
        
        # Success Rate berechnen
        successful_executions = sum(1 for exec_result in self.completed_executions.values() 
                                  if exec_result.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED])
        success_rate = successful_executions / total_executions
        
        return {
            'total_executions': total_executions,
            'active_executions': active_executions,
            'successful_executions': successful_executions,
            'success_rate': success_rate,
            'average_execution_time': self.average_execution_time

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