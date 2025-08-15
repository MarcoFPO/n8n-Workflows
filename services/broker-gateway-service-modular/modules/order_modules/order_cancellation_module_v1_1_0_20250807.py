"""
Order Cancellation Module - Single Function Module
Verantwortlich ausschließlich für Order Cancellation Logic
"""

import time
from typing import Dict, Any, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderStatus


class CancellationRequest(BaseModel):
    order_id: str
    reason: Optional[str] = None
    force_cancel: bool = False


class CancellationResult(BaseModel):
    order_id: str
    status: OrderStatus
    cancellation_time: datetime
    original_status: OrderStatus
    cancelled_amount: str
    remaining_amount: str
    broker_response: Dict[str, Any]


class OrderCancellationModule(SingleFunctionModule):
    """
    Single Function Module: Order Cancellation
    Verantwortlichkeit: Ausschließlich Order-Cancellation-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_cancellation", event_bus)
        
        # Cancellation Tracking
        self.cancellation_requests = {}
        self.cancelled_orders = {}
        self.cancellation_counter = 0
        
        # Cancellation Rules
        self.cancellable_statuses = [
            OrderStatus.OPEN, 
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.PENDING
        ]
        
        self.non_cancellable_statuses = [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED, 
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order Cancellation
        
        Args:
            input_data: {
                'cancellation_request': CancellationRequest dict,
                'credentials': broker credentials,
                'current_order_status': optional current order status
            }
            
        Returns:
            Dict mit Cancellation-Result
        """
        cancellation_request_data = input_data.get('cancellation_request')
        credentials = input_data.get('credentials', {})
        current_order_status = input_data.get('current_order_status')
        
        if not cancellation_request_data:
            raise ValueError('No cancellation request provided')
        
        # CancellationRequest parsieren
        try:
            cancellation_request = CancellationRequest(**cancellation_request_data)
        except Exception as e:
            raise ValueError(f'Invalid cancellation request format: {str(e)}')
        
        # Order Cancellation ausführen
        cancellation_result = await self._cancel_order_with_broker(
            cancellation_request, credentials, current_order_status
        )
        
        # Cancellation Result in Cache speichern
        self.cancelled_orders[cancellation_result.order_id] = cancellation_result
        
        return {
            'order_id': cancellation_result.order_id,
            'status': cancellation_result.status.value,
            'cancellation_time': cancellation_result.cancellation_time.isoformat(),
            'original_status': cancellation_result.original_status.value,
            'cancelled_amount': cancellation_result.cancelled_amount,
            'remaining_amount': cancellation_result.remaining_amount,
            'broker_response': cancellation_result.broker_response
        }
    
    async def _cancel_order_with_broker(self, cancellation_request: CancellationRequest,
                                      credentials: Dict[str, Any],
                                      current_order_status: Optional[str]) -> CancellationResult:
        """
        Order bei Broker stornieren (Bitpanda API Simulation)
        """
        self.cancellation_counter += 1
        order_id = cancellation_request.order_id
        
        # Request als aktiv markieren
        self.cancellation_requests[order_id] = {
            'start_time': datetime.now(),
            'request': cancellation_request,
            'status': 'processing'
        }
        
        try:
            # Current Order Status bestimmen (Simulation)
            original_status = self._determine_current_status(order_id, current_order_status)
            
            # Cancellation-Berechtigung prüfen
            can_cancel, reason = await self._check_cancellation_eligibility(
                order_id, original_status, cancellation_request
            )
            
            if not can_cancel and not cancellation_request.force_cancel:
                # Cancellation nicht möglich
                self._cleanup_cancellation_request(order_id)
                raise ValueError(f"Cannot cancel order {order_id}: {reason}")
            
            # Simulate cancellation processing
            cancellation_result = await self._simulate_broker_cancellation(
                order_id, original_status, cancellation_request
            )
            
            # Request als abgeschlossen markieren
            self._cleanup_cancellation_request(order_id)
            
            self.logger.info(f"Order cancelled successfully",
                           order_id=order_id,
                           original_status=original_status.value,
                           final_status=cancellation_result.status.value)
            
            return cancellation_result
            
        except Exception as e:
            # Request cleanup
            self._cleanup_cancellation_request(order_id)
            
            self.logger.error(f"Order cancellation failed",
                            order_id=order_id,
                            error=str(e))
            raise
    
    def _determine_current_status(self, order_id: str, provided_status: Optional[str]) -> OrderStatus:
        """Aktuellen Order-Status bestimmen"""
        if provided_status:
            try:
                return OrderStatus(provided_status)
            except ValueError:
                pass
        
        # Fallback: Simulate order status lookup
        # In Produktion: Echter API-Call zum Status abrufen
        import random
        statuses = [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED]
        weights = [0.6, 0.3, 0.1]  # Mehr offene Orders wahrscheinlich
        
        return random.choices(statuses, weights=weights)[0]
    
    async def _check_cancellation_eligibility(self, order_id: str, current_status: OrderStatus,
                                            cancellation_request: CancellationRequest) -> tuple[bool, str]:
        """Prüft ob Order stornierbar ist"""
        
        # Status-basierte Prüfung
        if current_status in self.non_cancellable_statuses:
            return False, f"Order is in {current_status.value} status and cannot be cancelled"
        
        if current_status not in self.cancellable_statuses:
            return False, f"Order status {current_status.value} is not eligible for cancellation"
        
        # Zusätzliche Business Rules
        # Beispiel: Keine Stornierung von sehr alten Orders
        # Beispiel: Keine Stornierung während Settlement
        
        return True, "Order is eligible for cancellation"
    
    async def _simulate_broker_cancellation(self, order_id: str, original_status: OrderStatus,
                                          cancellation_request: CancellationRequest) -> CancellationResult:
        """Simuliert Broker-Stornierung mit realistischen Parametern"""
        
        # Cancellation Delay simulieren (Broker-Latenz)
        import asyncio
        cancellation_delay = 0.05 + (hash(order_id) % 100) / 1000  # 50-150ms
        await asyncio.sleep(cancellation_delay)
        
        # Cancelled/Remaining Amount berechnen
        cancelled_amount, remaining_amount = self._calculate_cancelled_amounts(
            order_id, original_status
        )
        
        # Final Status bestimmen
        if original_status == OrderStatus.PARTIALLY_FILLED:
            # Partially filled orders können nur den offenen Teil stornieren
            final_status = OrderStatus.PARTIALLY_FILLED  # Bleibt partially filled
        else:
            final_status = OrderStatus.CANCELLED
        
        # Broker Response simulieren
        broker_response = {
            'exchange': 'bitpanda_pro',
            'cancellation_id': f"CANCEL-{int(time.time())}-{self.cancellation_counter:04d}",
            'processing_time_ms': cancellation_delay * 1000,
            'reason': cancellation_request.reason or 'User requested cancellation',
            'settlement_info': {
                'cancelled_portion': cancelled_amount,
                'remaining_open': remaining_amount,
                'fees_charged': '0.0'  # Normalerweise keine Fees für Stornierung
            }
        }
        
        cancellation_result = CancellationResult(
            order_id=order_id,
            status=final_status,
            cancellation_time=datetime.now(),
            original_status=original_status,
            cancelled_amount=cancelled_amount,
            remaining_amount=remaining_amount,
            broker_response=broker_response
        )
        
        return cancellation_result
    
    def _calculate_cancelled_amounts(self, order_id: str, original_status: OrderStatus) -> tuple[str, str]:
        """Berechnet stornierte und verbleibende Mengen"""
        
        # Simulation: Original Order Amount (würde normalerweise aus DB/Cache kommen)
        import random
        original_amount = random.uniform(0.1, 10.0)
        
        if original_status == OrderStatus.OPEN:
            # Vollständige Stornierung möglich
            cancelled_amount = str(original_amount)
            remaining_amount = "0.0"
            
        elif original_status == OrderStatus.PARTIALLY_FILLED:
            # Nur offener Teil kann storniert werden
            filled_percentage = random.uniform(0.1, 0.8)  # 10-80% bereits gefüllt
            filled_amount = original_amount * filled_percentage
            open_amount = original_amount - filled_amount
            
            cancelled_amount = str(round(open_amount, 8))
            remaining_amount = str(round(filled_amount, 8))
            
        else:
            # Fallback für andere Status
            cancelled_amount = str(original_amount)
            remaining_amount = "0.0"
        
        return cancelled_amount, remaining_amount
    
    def _cleanup_cancellation_request(self, order_id: str):
        """Cleanup Cancellation Request"""
        if order_id in self.cancellation_requests:
            del self.cancellation_requests[order_id]
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_cancellation',
            'description': 'Cancels open or partially filled trading orders',
            'responsibility': 'Order cancellation logic only',
            'input_parameters': {
                'cancellation_request': 'CancellationRequest object with order ID and reason',
                'credentials': 'Broker authentication credentials',
                'current_order_status': 'Optional current status of the order'
            },
            'output_format': {
                'order_id': 'Order identifier that was cancelled',
                'status': 'Final order status after cancellation',
                'cancellation_time': 'Cancellation execution timestamp',
                'original_status': 'Order status before cancellation',
                'cancelled_amount': 'Amount successfully cancelled',
                'remaining_amount': 'Amount that remains (for partial fills)',
                'broker_response': 'Detailed broker cancellation response'
            },
            'cancellation_rules': {
                'cancellable_statuses': [status.value for status in self.cancellable_statuses],
                'non_cancellable_statuses': [status.value for status in self.non_cancellable_statuses],
                'supports_force_cancel': True
            },
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_cancellation_statistics(self) -> Dict[str, Any]:
        """Cancellation Statistiken abrufen"""
        total_cancellations = len(self.cancelled_orders)
        active_requests = len(self.cancellation_requests)
        
        if total_cancellations == 0:
            return {
                'total_cancellations': 0,
                'active_requests': active_requests,
                'success_rate': 0.0
            }
        
        # Success Rate berechnen (basierend auf erfolgreich stornierten Orders)
        successful_cancellations = sum(1 for result in self.cancelled_orders.values() 
                                     if result.status == OrderStatus.CANCELLED)
        success_rate = successful_cancellations / total_cancellations
        
        return {
            'total_cancellations': total_cancellations,
            'active_requests': active_requests,
            'successful_cancellations': successful_cancellations,
            'success_rate': success_rate,
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