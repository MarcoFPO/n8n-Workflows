"""
Order Modification Module - Single Function Module
Verantwortlich ausschließlich für Order Modification Logic
"""

from typing import Dict, Any, Optional
from decimal import Decimal
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderStatus, OrderSide, OrderType


class ModificationRequest(BaseModel):
    order_id: str
    new_amount: Optional[str] = None
    new_price: Optional[str] = None
    new_stop_price: Optional[str] = None
    new_time_in_force: Optional[str] = None
    reason: Optional[str] = None


class ModificationResult(BaseModel):
    order_id: str
    modification_id: str
    status: OrderStatus
    original_values: Dict[str, Any]
    new_values: Dict[str, Any]
    modification_time: datetime
    broker_response: Dict[str, Any]


class OrderModificationModule(SingleFunctionModule):
    """
    Single Function Module: Order Modification
    Verantwortlichkeit: Ausschließlich Order-Modification-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_modification", event_bus)
        
        # Modification Tracking
        self.modification_requests = {}
        self.modification_history = {}
        self.modification_counter = 0
        
        # Modification Rules
        self.modifiable_statuses = [
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED
        ]
        
        self.non_modifiable_statuses = [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
        
        # Modification Constraints
        self.max_price_deviation_percent = 10.0  # Max 10% price change
        self.min_modification_amount = Decimal('0.001')  # Minimum amount change
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order Modification
        
        Args:
            input_data: {
                'modification_request': ModificationRequest dict,
                'credentials': broker credentials,
                'current_order_data': optional current order information
            }
            
        Returns:
            Dict mit Modification-Result
        """
        modification_request_data = input_data.get('modification_request')
        credentials = input_data.get('credentials', {})
        current_order_data = input_data.get('current_order_data')
        
        if not modification_request_data:
            raise ValueError('No modification request provided')
        
        # ModificationRequest parsieren
        try:
            modification_request = ModificationRequest(**modification_request_data)
        except Exception as e:
            raise ValueError(f'Invalid modification request format: {str(e)}')
        
        # Order Modification ausführen
        modification_result = await self._modify_order_with_broker(
            modification_request, credentials, current_order_data
        )
        
        # Modification Result in History speichern
        self.modification_history[modification_result.modification_id] = modification_result
        
        return {
            'order_id': modification_result.order_id,
            'modification_id': modification_result.modification_id,
            'status': modification_result.status.value,
            'original_values': modification_result.original_values,
            'new_values': modification_result.new_values,
            'modification_time': modification_result.modification_time.isoformat(),
            'broker_response': modification_result.broker_response
        }
    
    async def _modify_order_with_broker(self, modification_request: ModificationRequest,
                                      credentials: Dict[str, Any],
                                      current_order_data: Optional[Dict]) -> ModificationResult:
        """
        Order bei Broker modifizieren (Bitpanda API Simulation)
        """
        self.modification_counter += 1
        order_id = modification_request.order_id
        modification_id = f"MOD-{int(datetime.now().timestamp())}-{self.modification_counter:04d}"
        
        # Request als aktiv markieren
        self.modification_requests[modification_id] = {
            'start_time': datetime.now(),
            'request': modification_request,
            'status': 'processing'
        }
        
        try:
            # Current Order Data simulieren falls nicht bereitgestellt
            if not current_order_data:
                current_order_data = await self._fetch_current_order_data(order_id)
            
            # Modification-Berechtigung prüfen
            can_modify, reason = await self._check_modification_eligibility(
                order_id, current_order_data, modification_request
            )
            
            if not can_modify:
                self._cleanup_modification_request(modification_id)
                raise ValueError(f"Cannot modify order {order_id}: {reason}")
            
            # Modification Values validieren
            validation_result = await self._validate_modification_values(
                modification_request, current_order_data
            )
            
            if not validation_result['valid']:
                self._cleanup_modification_request(modification_id)
                raise ValueError(f"Invalid modification values: {validation_result['error']}")
            
            # Broker Modification simulieren
            modification_result = await self._simulate_broker_modification(
                modification_id, order_id, modification_request, current_order_data
            )
            
            # Request als abgeschlossen markieren
            self._cleanup_modification_request(modification_id)
            
            self.logger.info(f"Order modified successfully",
                           order_id=order_id,
                           modification_id=modification_id,
                           changes=len([k for k, v in modification_result.new_values.items() 
                                      if k in modification_result.original_values and 
                                      v != modification_result.original_values[k]]))
            
            return modification_result
            
        except Exception as e:
            # Request cleanup
            self._cleanup_modification_request(modification_id)
            
            self.logger.error(f"Order modification failed",
                            order_id=order_id,
                            modification_id=modification_id,
                            error=str(e))
            raise
    
    async def _fetch_current_order_data(self, order_id: str) -> Dict[str, Any]:
        """Current Order Data abrufen (Simulation)"""
        # In Produktion: echter API Call zum Status abrufen
        import random
        
        # Simulate current order data
        statuses = ['OPEN', 'PARTIALLY_FILLED']
        status = random.choice(statuses)
        
        original_amount = round(random.uniform(0.1, 10.0), 8)
        filled_amount = round(original_amount * random.uniform(0.0, 0.7), 8) if status == 'PARTIALLY_FILLED' else 0.0
        
        return {
            'order_id': order_id,
            'status': status,
            'instrument_code': 'BTC_EUR',
            'side': 'BUY',
            'type': 'LIMIT',
            'original_amount': str(original_amount),
            'filled_amount': str(filled_amount),
            'remaining_amount': str(original_amount - filled_amount),
            'price': str(round(random.uniform(40000, 50000), 2)),
            'time_in_force': 'GTC'
        }
    
    async def _check_modification_eligibility(self, order_id: str, current_order_data: Dict,
                                           modification_request: ModificationRequest) -> tuple[bool, str]:
        """Prüft ob Order modifizierbar ist"""
        
        current_status = OrderStatus(current_order_data['status'])
        
        # Status-basierte Prüfung
        if current_status in self.non_modifiable_statuses:
            return False, f"Order is in {current_status.value} status and cannot be modified"
        
        if current_status not in self.modifiable_statuses:
            return False, f"Order status {current_status.value} is not eligible for modification"
        
        # Type-basierte Prüfung (nur LIMIT orders sind normalerweise modifizierbar)
        order_type = OrderType(current_order_data['type'])
        if order_type == OrderType.MARKET:
            return False, "MARKET orders cannot be modified after placement"
        
        # Modification Content Prüfung
        if not any([
            modification_request.new_amount,
            modification_request.new_price,
            modification_request.new_stop_price,
            modification_request.new_time_in_force
        ]):
            return False, "No modification parameters provided"
        
        return True, "Order is eligible for modification"
    
    async def _validate_modification_values(self, modification_request: ModificationRequest,
                                          current_order_data: Dict) -> Dict[str, Any]:
        """Validiert Modification Values"""
        
        errors = []
        
        # New Amount Validation
        if modification_request.new_amount:
            try:
                new_amount = Decimal(modification_request.new_amount)
                current_amount = Decimal(current_order_data['original_amount'])
                filled_amount = Decimal(current_order_data['filled_amount'])
                
                if new_amount <= filled_amount:
                    errors.append(f"New amount ({new_amount}) must be greater than filled amount ({filled_amount})")
                
                # Minimum Change Check
                amount_change = abs(new_amount - current_amount)
                if amount_change < self.min_modification_amount:
                    errors.append(f"Amount change too small: {amount_change} (min: {self.min_modification_amount})")
                    
            except Exception as e:
                errors.append(f"Invalid new_amount format: {str(e)}")
        
        # New Price Validation
        if modification_request.new_price:
            try:
                new_price = Decimal(modification_request.new_price)
                current_price = Decimal(current_order_data['price'])
                
                # Price Deviation Check
                price_deviation = abs((new_price - current_price) / current_price) * 100
                if price_deviation > self.max_price_deviation_percent:
                    errors.append(f"Price deviation too large: {price_deviation:.1f}% (max: {self.max_price_deviation_percent}%)")
                    
            except Exception as e:
                errors.append(f"Invalid new_price format: {str(e)}")
        
        # New Stop Price Validation
        if modification_request.new_stop_price:
            try:
                new_stop_price = Decimal(modification_request.new_stop_price)
                if new_stop_price <= 0:
                    errors.append("Stop price must be greater than zero")
            except Exception as e:
                errors.append(f"Invalid new_stop_price format: {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'error': '; '.join(errors) if errors else None,
            'errors': errors
        }
    
    async def _simulate_broker_modification(self, modification_id: str, order_id: str,
                                          modification_request: ModificationRequest,
                                          current_order_data: Dict) -> ModificationResult:
        """Simuliert Broker-Modification mit realistischen Parametern"""
        
        # Modification Delay simulieren
        import asyncio
        modification_delay = 0.1 + (hash(order_id) % 100) / 1000  # 100-200ms
        await asyncio.sleep(modification_delay)
        
        # Original Values sammeln
        original_values = {
            'amount': current_order_data['original_amount'],
            'price': current_order_data.get('price'),
            'stop_price': current_order_data.get('stop_price'),
            'time_in_force': current_order_data.get('time_in_force', 'GTC')
        }
        
        # New Values erstellen
        new_values = original_values.copy()
        
        if modification_request.new_amount:
            new_values['amount'] = modification_request.new_amount
        if modification_request.new_price:
            new_values['price'] = modification_request.new_price
        if modification_request.new_stop_price:
            new_values['stop_price'] = modification_request.new_stop_price
        if modification_request.new_time_in_force:
            new_values['time_in_force'] = modification_request.new_time_in_force
        
        # Status nach Modification (normalerweise bleibt OPEN oder PARTIALLY_FILLED)
        final_status = OrderStatus(current_order_data['status'])
        
        # Broker Response simulieren
        broker_response = {
            'exchange': 'bitpanda_pro',
            'modification_id': modification_id,
            'processing_time_ms': modification_delay * 1000,
            'reason': modification_request.reason or 'User requested modification',
            'changes_applied': {
                k: {'from': original_values[k], 'to': new_values[k]} 
                for k in new_values 
                if k in original_values and new_values[k] != original_values[k]
            },
            'fees_charged': '0.0',  # Normalerweise keine Fees für Modification
            'new_order_version': int(datetime.now().timestamp())
        }
        
        modification_result = ModificationResult(
            order_id=order_id,
            modification_id=modification_id,
            status=final_status,
            original_values=original_values,
            new_values=new_values,
            modification_time=datetime.now(),
            broker_response=broker_response
        )
        
        return modification_result
    
    def _cleanup_modification_request(self, modification_id: str):
        """Cleanup Modification Request"""
        if modification_id in self.modification_requests:
            del self.modification_requests[modification_id]
    
    def get_modification_by_id(self, modification_id: str) -> Optional[ModificationResult]:
        """Modification Result nach ID abrufen"""
        return self.modification_history.get(modification_id)
    
    def get_modifications_for_order(self, order_id: str) -> List[ModificationResult]:
        """Alle Modifications für eine Order abrufen"""
        return [result for result in self.modification_history.values() 
                if result.order_id == order_id]
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_modification',
            'description': 'Modifies existing trading orders with validation',
            'responsibility': 'Order modification logic only',
            'input_parameters': {
                'modification_request': 'ModificationRequest object with order ID and new values',
                'credentials': 'Broker authentication credentials',
                'current_order_data': 'Optional current order information'
            },
            'output_format': {
                'order_id': 'Order identifier that was modified',
                'modification_id': 'Unique modification identifier',
                'status': 'Order status after modification',
                'original_values': 'Original order values before modification',
                'new_values': 'New order values after modification',
                'modification_time': 'Modification execution timestamp',
                'broker_response': 'Detailed broker modification response'
            },
            'modification_rules': {
                'modifiable_statuses': [status.value for status in self.modifiable_statuses],
                'non_modifiable_statuses': [status.value for status in self.non_modifiable_statuses],
                'max_price_deviation_percent': self.max_price_deviation_percent,
                'min_modification_amount': str(self.min_modification_amount)
            },
            'supported_modifications': [
                'amount_increase_decrease',
                'price_adjustment',
                'stop_price_adjustment',
                'time_in_force_change'
            ],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_modification_statistics(self) -> Dict[str, Any]:
        """Modification Statistiken abrufen"""
        total_modifications = len(self.modification_history)
        active_requests = len(self.modification_requests)
        
        if total_modifications == 0:
            return {
                'total_modifications': 0,
                'active_requests': active_requests,
                'success_rate': 0.0,
                'average_processing_time': 0.0
            }
        
        # Success Rate berechnen (basierend auf erfolgreich modifizierten Orders)
        successful_modifications = sum(1 for result in self.modification_history.values() 
                                     if result.status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED])
        success_rate = successful_modifications / total_modifications
        
        return {
            'total_modifications': total_modifications,
            'active_requests': active_requests,
            'successful_modifications': successful_modifications,
            'success_rate': success_rate,
            'average_processing_time': self.average_execution_time,
            'modification_constraints': {
                'max_price_deviation_percent': self.max_price_deviation_percent,
                'min_modification_amount': str(self.min_modification_amount)
            }

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