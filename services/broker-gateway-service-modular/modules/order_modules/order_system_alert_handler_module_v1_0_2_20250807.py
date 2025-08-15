"""
Order System Alert Handler Module - Single Function Module
Verantwortlich ausschließlich für System Alert Event Handling Logic
"""

import asyncio
from typing import Dict, Any, List, Optional
from enum import Enum
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderStatus


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertCategory(str, Enum):
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    BROKER_CONNECTION = "BROKER_CONNECTION"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    DATA_QUALITY = "DATA_QUALITY"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"


class SystemAlert(BaseModel):
    alert_id: str
    severity: AlertSeverity
    category: AlertCategory
    title: str
    description: str
    source_service: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    affects_trading: bool = False


class AlertResponse(BaseModel):
    alert_id: str
    response_action: str  # 'order_pause', 'order_cancel', 'position_reduce', 'monitoring_increased', 'no_action'
    affected_orders: List[str]
    reasoning: str
    severity_assessment: AlertSeverity
    auto_resolved: bool
    response_timestamp: datetime
    follow_up_required: bool


class OrderSystemAlertHandlerModule(SingleFunctionModule):
    """
    Single Function Module: Order System Alert Handler
    Verantwortlichkeit: Ausschließlich System-Alert-Event-Handling-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_system_alert_handler", event_bus)
        
        # Alert Processing History
        self.processed_alerts = {}
        self.alert_responses = {}
        self.alert_counter = 0
        
        # Alert Response Rules
        self.alert_response_rules = {
            AlertCategory.BROKER_CONNECTION: {
                AlertSeverity.CRITICAL: 'order_pause',
                AlertSeverity.ERROR: 'order_pause',
                AlertSeverity.WARNING: 'monitoring_increased',
                AlertSeverity.INFO: 'no_action'
            },
            AlertCategory.RISK_MANAGEMENT: {
                AlertSeverity.CRITICAL: 'position_reduce',
                AlertSeverity.ERROR: 'order_cancel',
                AlertSeverity.WARNING: 'monitoring_increased',
                AlertSeverity.INFO: 'no_action'
            },
            AlertCategory.SYSTEM_HEALTH: {
                AlertSeverity.CRITICAL: 'order_pause',
                AlertSeverity.ERROR: 'monitoring_increased',
                AlertSeverity.WARNING: 'no_action',
                AlertSeverity.INFO: 'no_action'
            },
            AlertCategory.DATA_QUALITY: {
                AlertSeverity.CRITICAL: 'order_pause',
                AlertSeverity.ERROR: 'monitoring_increased',
                AlertSeverity.WARNING: 'no_action',
                AlertSeverity.INFO: 'no_action'
            },
            AlertCategory.PERFORMANCE: {
                AlertSeverity.CRITICAL: 'monitoring_increased',
                AlertSeverity.ERROR: 'monitoring_increased',
                AlertSeverity.WARNING: 'no_action',
                AlertSeverity.INFO: 'no_action'
            },
            AlertCategory.SECURITY: {
                AlertSeverity.CRITICAL: 'order_pause',
                AlertSeverity.ERROR: 'order_pause',
                AlertSeverity.WARNING: 'monitoring_increased',
                AlertSeverity.INFO: 'no_action'
            }
        }
        
        # Auto-Resolution Patterns
        self.auto_resolution_patterns = {
            'broker_reconnected': 'Broker connection restored',
            'system_health_ok': 'System health returned to normal',
            'performance_improved': 'Performance metrics improved',
            'data_quality_restored': 'Data quality issues resolved'
        }
        
        # Order Management State
        self.paused_orders = set()
        self.monitoring_increased_orders = set()
        self.last_alert_check = datetime.now()
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: System Alert Event Handling
        
        Args:
            input_data: {
                'event': system alert event data,
                'current_orders': optional list of current orders,
                'system_status': optional current system status
            }
            
        Returns:
            Dict mit Alert-Response
        """
        event_data = input_data.get('event')
        current_orders = input_data.get('current_orders', [])
        system_status = input_data.get('system_status', {})
        
        if not event_data:
            raise ValueError('No system alert event provided')
        
        # System Alert extrahieren
        system_alert = await self._extract_system_alert(event_data)
        
        # Alert verarbeiten
        alert_response = await self._process_system_alert(
            system_alert, current_orders, system_status
        )
        
        # Response in History speichern
        self.alert_responses[alert_response.alert_id] = alert_response
        
        return {
            'alert_id': alert_response.alert_id,
            'response_action': alert_response.response_action,
            'affected_orders': alert_response.affected_orders,
            'reasoning': alert_response.reasoning,
            'severity_assessment': alert_response.severity_assessment.value,
            'auto_resolved': alert_response.auto_resolved,
            'response_timestamp': alert_response.response_timestamp.isoformat(),
            'follow_up_required': alert_response.follow_up_required
        }
    
    async def _extract_system_alert(self, event_data: Dict[str, Any]) -> SystemAlert:
        """Extrahiert System Alert aus Event Data"""
        self.alert_counter += 1
        
        # Event Data parsen
        data = event_data.get('data', {})
        
        # Alert ID generieren falls nicht vorhanden
        alert_id = data.get('alert_id', f"ALERT-{int(datetime.now().timestamp())}-{self.alert_counter:04d}")
        
        system_alert = SystemAlert(
            alert_id=alert_id,
            severity=AlertSeverity(data.get('severity', 'WARNING')),
            category=AlertCategory(data.get('category', 'SYSTEM_HEALTH')),
            title=data.get('title', 'Unknown Alert'),
            description=data.get('description', 'No description provided'),
            source_service=data.get('source_service', 'unknown'),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            metadata=data.get('metadata', {}),
            affects_trading=data.get('affects_trading', False)
        )
        
        # Alert in Processing History speichern
        self.processed_alerts[alert_id] = system_alert
        
        return system_alert
    
    async def _process_system_alert(self, system_alert: SystemAlert,
                                  current_orders: List[Dict],
                                  system_status: Dict[str, Any]) -> AlertResponse:
        """Verarbeitet System Alert und bestimmt Response Action"""
        
        alert_id = system_alert.alert_id
        
        # Auto-Resolution Check
        auto_resolved = await self._check_auto_resolution(system_alert, system_status)
        
        if auto_resolved:
            return AlertResponse(
                alert_id=alert_id,
                response_action="no_action",
                affected_orders=[],
                reasoning="Alert auto-resolved - no action required",
                severity_assessment=system_alert.severity,
                auto_resolved=True,
                response_timestamp=datetime.now(),
                follow_up_required=False
            )
        
        # Response Action basierend auf Rules bestimmen
        response_action = self._determine_response_action(system_alert)
        
        # Betroffene Orders identifizieren
        affected_orders = await self._identify_affected_orders(
            system_alert, current_orders, response_action
        )
        
        # Response Action ausführen
        execution_result = await self._execute_response_action(
            response_action, affected_orders, system_alert
        )
        
        # Reasoning generieren
        reasoning = self._generate_response_reasoning(
            system_alert, response_action, affected_orders, execution_result
        )
        
        # Follow-up Requirements bestimmen
        follow_up_required = self._requires_follow_up(system_alert, response_action)
        
        alert_response = AlertResponse(
            alert_id=alert_id,
            response_action=response_action,
            affected_orders=affected_orders,
            reasoning=reasoning,
            severity_assessment=system_alert.severity,
            auto_resolved=auto_resolved,
            response_timestamp=datetime.now(),
            follow_up_required=follow_up_required
        )
        
        # Event-Bus Notification für kritische Responses
        if response_action in ['order_pause', 'order_cancel', 'position_reduce']:
            await self._publish_critical_response_event(alert_response, system_alert)
        
        self.logger.info(f"System alert processed",
                       alert_id=alert_id,
                       severity=system_alert.severity.value,
                       category=system_alert.category.value,
                       response_action=response_action,
                       affected_orders_count=len(affected_orders))
        
        return alert_response
    
    async def _check_auto_resolution(self, system_alert: SystemAlert, 
                                   system_status: Dict[str, Any]) -> bool:
        """Prüft ob Alert auto-resolved werden kann"""
        
        # Status-basierte Auto-Resolution
        if system_alert.category == AlertCategory.BROKER_CONNECTION:
            if system_status.get('broker_connected', False):
                return True
        
        if system_alert.category == AlertCategory.SYSTEM_HEALTH:
            if system_status.get('system_health', 'unknown') == 'healthy':
                return True
        
        if system_alert.category == AlertCategory.PERFORMANCE:
            performance_score = system_status.get('performance_score', 0)
            if performance_score > 0.8:  # Good performance
                return True
        
        if system_alert.category == AlertCategory.DATA_QUALITY:
            data_quality_score = system_status.get('data_quality_score', 0)
            if data_quality_score > 0.9:  # High data quality
                return True
        
        return False
    
    def _determine_response_action(self, system_alert: SystemAlert) -> str:
        """Bestimmt Response Action basierend auf Alert Rules"""
        
        category_rules = self.alert_response_rules.get(system_alert.category, {})
        response_action = category_rules.get(system_alert.severity, 'no_action')
        
        # Trading Impact Consideration
        if system_alert.affects_trading and response_action == 'no_action':
            if system_alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
                response_action = 'monitoring_increased'
        
        return response_action
    
    async def _identify_affected_orders(self, system_alert: SystemAlert,
                                      current_orders: List[Dict],
                                      response_action: str) -> List[str]:
        """Identifiziert betroffene Orders basierend auf Alert und Response Action"""
        
        if response_action == 'no_action':
            return []
        
        affected_order_ids = []
        
        # Alle aktiven Orders
        active_orders = [
            order for order in current_orders
            if order.get('status') in ['OPEN', 'PARTIALLY_FILLED']
        ]
        
        # Response Action spezifische Logic
        if response_action == 'order_pause':
            # Alle aktiven Orders pausieren
            affected_order_ids = [order.get('order_id') for order in active_orders]
        
        elif response_action == 'order_cancel':
            # Riskante Orders canceln (größere Orders, Market Orders)
            risky_orders = [
                order for order in active_orders
                if (order.get('type') == 'MARKET' or 
                    float(order.get('amount', '0')) * 45000 > 5000)  # > €5k orders
            ]
            affected_order_ids = [order.get('order_id') for order in risky_orders]
        
        elif response_action == 'position_reduce':
            # Größte Positionen reduzieren
            large_orders = sorted(
                active_orders,
                key=lambda x: float(x.get('amount', '0')) * 45000,
                reverse=True
            )[:3]  # Top 3 größte Orders
            affected_order_ids = [order.get('order_id') for order in large_orders]
        
        elif response_action == 'monitoring_increased':
            # Alle Orders unter verstärkte Überwachung
            affected_order_ids = [order.get('order_id') for order in active_orders]
        
        # Category-spezifische Adjustments
        if system_alert.category == AlertCategory.BROKER_CONNECTION:
            # Nur Orders die Broker-Verbindung benötigen
            pass  # Alle Orders betroffen
        
        elif system_alert.category == AlertCategory.RISK_MANAGEMENT:
            # Instrument-spezifische Filter falls in Metadata
            instrument_filter = system_alert.metadata.get('affected_instrument')
            if instrument_filter:
                affected_order_ids = [
                    order_id for order_id, order in zip(affected_order_ids, active_orders)
                    if order.get('instrument_code') == instrument_filter
                ]
        
        return affected_order_ids
    
    async def _execute_response_action(self, response_action: str, 
                                     affected_orders: List[str],
                                     system_alert: SystemAlert) -> Dict[str, Any]:
        """Führt Response Action aus"""
        
        execution_results = {
            'action': response_action,
            'orders_processed': len(affected_orders),
            'success_count': 0,
            'failure_count': 0,
            'details': []
        }
        
        for order_id in affected_orders:
            try:
                if response_action == 'order_pause':
                    result = await self._simulate_order_pause(order_id)
                    self.paused_orders.add(order_id)
                
                elif response_action == 'order_cancel':
                    result = await self._simulate_order_cancel(order_id)
                
                elif response_action == 'position_reduce':
                    result = await self._simulate_position_reduction(order_id)
                
                elif response_action == 'monitoring_increased':
                    result = await self._increase_order_monitoring(order_id)
                    self.monitoring_increased_orders.add(order_id)
                
                else:
                    result = {'success': True, 'message': 'No action required'}
                
                if result.get('success', False):
                    execution_results['success_count'] += 1
                else:
                    execution_results['failure_count'] += 1
                
                execution_results['details'].append({
                    'order_id': order_id,
                    'success': result.get('success', False),
                    'message': result.get('message', 'Unknown result')
                })
                
            except Exception as e:
                execution_results['failure_count'] += 1
                execution_results['details'].append({
                    'order_id': order_id,
                    'success': False,
                    'message': f'Execution error: {str(e)}'
                })
        
        return execution_results
    
    async def _simulate_order_pause(self, order_id: str) -> Dict[str, Any]:
        """Simuliert Order Pause (in Produktion: echter API Call)"""
        self.logger.info(f"Simulated order pause", order_id=order_id)
        return {'success': True, 'message': 'Order paused due to system alert'}
    
    async def _simulate_order_cancel(self, order_id: str) -> Dict[str, Any]:
        """Simuliert Order Cancellation"""
        self.logger.info(f"Simulated order cancellation", order_id=order_id)
        return {'success': True, 'message': 'Order cancelled due to system alert'}
    
    async def _simulate_position_reduction(self, order_id: str) -> Dict[str, Any]:
        """Simuliert Position Reduction"""
        self.logger.info(f"Simulated position reduction", order_id=order_id)
        return {'success': True, 'message': 'Position reduced due to risk alert'}
    
    async def _increase_order_monitoring(self, order_id: str) -> Dict[str, Any]:
        """Erhöht Order Monitoring"""
        self.logger.info(f"Increased monitoring for order", order_id=order_id)
        return {'success': True, 'message': 'Monitoring increased for order'}
    
    def _generate_response_reasoning(self, system_alert: SystemAlert,
                                   response_action: str,
                                   affected_orders: List[str],
                                   execution_result: Dict[str, Any]) -> str:
        """Generiert Response Reasoning"""
        
        base_reasoning = f"Alert '{system_alert.title}' (severity: {system_alert.severity.value}) "
        
        if response_action == 'no_action':
            return base_reasoning + "requires no immediate action"
        
        elif response_action == 'order_pause':
            return base_reasoning + f"requires pausing {len(affected_orders)} active orders for safety"
        
        elif response_action == 'order_cancel':
            return base_reasoning + f"requires cancelling {len(affected_orders)} risky orders"
        
        elif response_action == 'position_reduce':
            return base_reasoning + f"requires reducing {len(affected_orders)} large positions"
        
        elif response_action == 'monitoring_increased':
            return base_reasoning + f"requires increased monitoring of {len(affected_orders)} orders"
        
        else:
            return base_reasoning + f"triggered response action '{response_action}'"
    
    def _requires_follow_up(self, system_alert: SystemAlert, response_action: str) -> bool:
        """Bestimmt ob Follow-up erforderlich ist"""
        
        # Critical Alerts immer Follow-up
        if system_alert.severity == AlertSeverity.CRITICAL:
            return True
        
        # Actions die Orders beeinträchtigen
        if response_action in ['order_pause', 'order_cancel', 'position_reduce']:
            return True
        
        # Trading-Impact Alerts
        if system_alert.affects_trading:
            return True
        
        return False
    
    async def _publish_critical_response_event(self, alert_response: AlertResponse, 
                                             system_alert: SystemAlert):
        """Publisht Critical Response Event über Event-Bus"""
        if not self.event_bus or not self.event_bus.connected:
            return
        
        from event_bus import Event
        
        event = Event(
            event_type="order_critical_alert_response",
            stream_id=f"alert-response-{alert_response.alert_id}",
            data={
                'alert_id': alert_response.alert_id,
                'original_alert': {
                    'severity': system_alert.severity.value,
                    'category': system_alert.category.value,
                    'title': system_alert.title,
                    'description': system_alert.description
                },
                'response_action': alert_response.response_action,
                'affected_orders_count': len(alert_response.affected_orders),
                'affected_orders': alert_response.affected_orders,
                'reasoning': alert_response.reasoning,
                'follow_up_required': alert_response.follow_up_required,
                'response_timestamp': alert_response.response_timestamp.isoformat()
            },
            source="order_system_alert_handler"
        )
        
        await self.event_bus.publish(event)
    
    def get_paused_orders(self) -> List[str]:
        """Gibt Liste der pausiert Orders zurück"""
        return list(self.paused_orders)
    
    def get_monitored_orders(self) -> List[str]:
        """Gibt Liste der Orders mit erhöhtem Monitoring zurück"""
        return list(self.monitoring_increased_orders)
    
    def resume_paused_order(self, order_id: str):
        """Nimmt pausierte Order wieder auf"""
        self.paused_orders.discard(order_id)
        self.logger.info(f"Order resumed from pause", order_id=order_id)
    
    def reduce_monitoring(self, order_id: str):
        """Reduziert Monitoring für Order"""
        self.monitoring_increased_orders.discard(order_id)
        self.logger.info(f"Order monitoring reduced to normal", order_id=order_id)
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_system_alert_handler',
            'description': 'Processes system alerts and takes appropriate order management actions',
            'responsibility': 'System alert event handling and order safety actions only',
            'input_parameters': {
                'event': 'System alert event with severity, category, and details',
                'current_orders': 'Optional list of current orders for impact analysis',
                'system_status': 'Optional current system status for auto-resolution'
            },
            'output_format': {
                'alert_id': 'Processed alert identifier',
                'response_action': 'Action taken in response to alert',
                'affected_orders': 'List of order IDs affected by response',
                'reasoning': 'Explanation of response decision',
                'severity_assessment': 'Alert severity assessment',
                'auto_resolved': 'Whether alert was auto-resolved',
                'response_timestamp': 'Response processing timestamp',
                'follow_up_required': 'Whether manual follow-up is needed'
            },
            'alert_categories': [category.value for category in AlertCategory],
            'alert_severities': [severity.value for severity in AlertSeverity],
            'response_actions': ['order_pause', 'order_cancel', 'position_reduce', 'monitoring_increased', 'no_action'],
            'response_rules': self.alert_response_rules,
            'auto_resolution_patterns': list(self.auto_resolution_patterns.keys()),
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Alert Processing Statistiken abrufen"""
        total_alerts = len(self.processed_alerts)
        total_responses = len(self.alert_responses)
        
        if total_responses == 0:
            return {
                'total_alerts_processed': total_alerts,
                'total_responses_generated': 0,
                'response_action_distribution': {},
                'severity_distribution': {},
                'category_distribution': {},
                'current_paused_orders': len(self.paused_orders),
                'current_monitored_orders': len(self.monitoring_increased_orders)
            }
        
        # Distributions
        responses = list(self.alert_responses.values())
        alerts = list(self.processed_alerts.values())
        
        action_dist = {}
        severity_dist = {}
        category_dist = {}
        
        for response in responses:
            action_dist[response.response_action] = action_dist.get(response.response_action, 0) + 1
        
        for alert in alerts:
            severity_dist[alert.severity.value] = severity_dist.get(alert.severity.value, 0) + 1
            category_dist[alert.category.value] = category_dist.get(alert.category.value, 0) + 1
        
        # Follow-up Requirements
        follow_ups_required = sum(1 for r in responses if r.follow_up_required)
        auto_resolved_count = sum(1 for r in responses if r.auto_resolved)
        
        return {
            'total_alerts_processed': total_alerts,
            'total_responses_generated': total_responses,
            'response_action_distribution': action_dist,
            'severity_distribution': severity_dist,
            'category_distribution': category_dist,
            'follow_ups_required': follow_ups_required,
            'auto_resolved_count': auto_resolved_count,
            'current_paused_orders': len(self.paused_orders),
            'current_monitored_orders': len(self.monitoring_increased_orders),
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