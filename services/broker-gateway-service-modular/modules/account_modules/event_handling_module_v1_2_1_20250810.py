from typing import Dict, Any, List, Optional, Callable
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Event Handling Module - Single Function Module
Verantwortlich ausschließlich für Account Event Handling Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, BaseModel, structlog
)


class EventHandlingRequest(BaseModel):
    event_type: str
    event_data: Dict[str, Any]
    event_source: str
    event_timestamp: datetime
    priority: str = 'normal'  # 'low', 'normal', 'high', 'critical'


class EventHandlingResult(BaseModel):
    event_processed: bool
    processing_actions: List[str]
    downstream_events: List[Dict[str, Any]]
    processing_time_ms: float
    error_details: Optional[str] = None


class EventHandlingModule(SingleFunctionModule):
    """
    Single Function Module: Account Event Handling
    Verantwortlichkeit: Ausschließlich Account-Event-Handling-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("event_handling", event_bus)
        
        # Event Handler Registry
        self.event_handlers = {}
        self.register_default_event_handlers()
        
        # Event Processing History
        self.processing_history = []
        self.processing_counter = 0
        
        # Event Processing Statistics
        self.event_statistics = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'events_by_type': {},
            'events_by_source': {},
            'average_processing_time': 0.0
        }
        
        # Event Queue für High Priority Events
        self.priority_queue = []
        
        # Event Handling Configuration
        self.handling_config = {
            'max_processing_time_ms': 5000,  # 5 seconds max per event
            'max_retry_attempts': 3,
            'batch_processing_size': 10,
            'priority_processing_enabled': True,
            'downstream_event_propagation': True
        }
        
        # Account State für Event Context
        self.account_state = {
            'balances': {},
            'active_orders': [],
            'recent_transactions': [],
            'account_status': 'active',
            'limits': {},
            'last_activity': datetime.now()
        }
        

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def register_default_event_handlers(self):
        """Registriert Standard Event Handlers"""
        
        self.event_handlers = {
            'trading_state_changed': self._handle_trading_event,
            'portfolio_state_changed': self._handle_portfolio_event,
            'config_updated': self._handle_config_event,
            'system_alert_raised': self._handle_system_alert_event,
            'transaction_completed': self._handle_transaction_event,
            'order_status_changed': self._handle_order_event,
            'balance_updated': self._handle_balance_event,
            'limits_exceeded': self._handle_limits_event,
            'account_frozen': self._handle_account_freeze_event,
            'withdrawal_requested': self._handle_withdrawal_event
        }
    
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Account Event Handling
        
        Args:
            input_data: {
                'event_type': required string,
                'event_data': required dict,
                'event_source': optional string (default: 'unknown'),
                'event_timestamp': optional string (default: now),
                'priority': optional string (default: 'normal'),
                'handle_synchronously': optional bool (default: true),
                'enable_downstream_events': optional bool (default: true)
            }
            
        Returns:
            Dict mit Event-Handling-Result
        """
        start_time = datetime.now()
        
        try:
            # Event Handling Request erstellen
            handling_request = EventHandlingRequest(
                event_type=input_data.get('event_type'),
                event_data=input_data.get('event_data', {}),
                event_source=input_data.get('event_source', 'unknown'),
                event_timestamp=datetime.fromisoformat(
                    input_data.get('event_timestamp', datetime.now().isoformat()).replace('Z', '+00:00')
                ),
                priority=input_data.get('priority', 'normal')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid event handling request: {str(e)}'
            }
        
        handle_synchronously = input_data.get('handle_synchronously', True)
        enable_downstream = input_data.get('enable_downstream_events', True)
        
        # Event Processing
        if handle_synchronously:
            handling_result = await self._process_event(handling_request, enable_downstream)
        else:
            # Queue für asynchrone Verarbeitung
            handling_result = await self._queue_event_for_processing(handling_request)
        
        # Statistics Update
        self.processing_counter += 1
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Processing History
        self.processing_history.append({
            'timestamp': datetime.now(),
            'event_type': handling_request.event_type,
            'event_source': handling_request.event_source,
            'priority': handling_request.priority,
            'processed_successfully': handling_result.event_processed,
            'processing_time_ms': processing_time_ms,
            'actions_count': len(handling_result.processing_actions),
            'downstream_events_count': len(handling_result.downstream_events),
            'processing_id': self.processing_counter
        })
        
        # Limit History
        if len(self.processing_history) > 500:
            self.processing_history.pop(0)
        
        # Update Statistics
        await self._update_event_statistics(handling_request, handling_result, processing_time_ms)
        
        self.logger.info(f"Event processed",
                       event_type=handling_request.event_type,
                       event_source=handling_request.event_source,
                       processed_successfully=handling_result.event_processed,
                       processing_time_ms=round(processing_time_ms, 2),
                       processing_id=self.processing_counter)
        
        return {
            'success': True,
            'event_processed': handling_result.event_processed,
            'processing_actions': handling_result.processing_actions,
            'downstream_events': handling_result.downstream_events if enable_downstream else [],
            'processing_time_ms': round(handling_result.processing_time_ms, 2),
            'error_details': handling_result.error_details
        }
    
    async def _process_event(self, request: EventHandlingRequest, 
                           enable_downstream: bool) -> EventHandlingResult:
        """Verarbeitet Event synchron"""
        
        start_time = datetime.now()
        processing_actions = []
        downstream_events = []
        error_details = None
        event_processed = False
        
        try:
            # Event Handler finden
            handler = self.event_handlers.get(request.event_type)
            
            if not handler:
                processing_actions.append(f'No handler found for event type: {request.event_type}')
                self.logger.warning(f"No handler for event type", event_type=request.event_type)
                return EventHandlingResult(
                    event_processed=False,
                    processing_actions=processing_actions,
                    downstream_events=[],
                    processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    error_details=f'No handler for event type: {request.event_type}'
                )
            
            # Event Context vorbereiten
            event_context = {
                'account_state': self.account_state,
                'event_timestamp': request.event_timestamp,
                'event_source': request.event_source,
                'priority': request.priority
            }
            
            # Event Handler ausführen
            handler_result = await handler(request.event_data, event_context)
            
            if handler_result:
                processing_actions.extend(handler_result.get('actions', []))
                if enable_downstream and self.handling_config['downstream_event_propagation']:
                    downstream_events.extend(handler_result.get('downstream_events', []))
                event_processed = handler_result.get('success', True)
                error_details = handler_result.get('error')
            else:
                processing_actions.append('Event handler executed with no result')
                event_processed = True
            
            # Account State Update falls erforderlich
            if handler_result and handler_result.get('update_account_state'):
                await self._update_account_state(handler_result['update_account_state'])
                processing_actions.append('Account state updated')
            
        except Exception as e:
            error_details = str(e)
            processing_actions.append(f'Event processing failed: {error_details}')
            self.logger.error(f"Event processing failed",
                            event_type=request.event_type,
                            error=error_details)
        
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return EventHandlingResult(
            event_processed=event_processed,
            processing_actions=processing_actions,
            downstream_events=downstream_events,
            processing_time_ms=processing_time_ms,
            error_details=error_details
        )
    
    async def _queue_event_for_processing(self, request: EventHandlingRequest) -> EventHandlingResult:
        """Queued Event für asynchrone Verarbeitung"""
        
        # Add to priority queue based on priority
        priority_order = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}
        priority_level = priority_order.get(request.priority, 2)
        
        queue_item = {
            'request': request,
            'priority_level': priority_level,
            'queued_at': datetime.now()
        }
        
        self.priority_queue.append(queue_item)
        self.priority_queue.sort(key=lambda x: (x['priority_level'], x['queued_at']))
        
        return EventHandlingResult(
            event_processed=False,  # Queued, not yet processed
            processing_actions=[f'Event queued for asynchronous processing with priority: {request.priority}'],
            downstream_events=[],
            processing_time_ms=0.1,  # Minimal time for queueing
            error_details=None
        )
    
    async def _handle_trading_event(self, event_data: Dict[str, Any], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Trading State Changed Events"""
        
        actions = ['Processing trading state change event']
        downstream_events = []
        
        action = event_data.get('action')
        
        if action == 'order_placed':
            # Lock funds für placed orders
            order_id = event_data.get('order_id')
            instrument = event_data.get('instrument')
            side = event_data.get('side')
            amount = event_data.get('amount')
            
            actions.append(f'Processing order placement: {order_id}')
            
            # Determine currency to lock
            if side == 'BUY':
                lock_currency = 'EUR' if '_EUR' in str(instrument) else 'USD'
            else:
                lock_currency = str(instrument).split('_')[0] if '_' in str(instrument) else str(instrument)
            
            # Create downstream transaction event
            downstream_events.append({
                'event_type': 'transaction_requested',
                'event_data': {
                    'transaction_type': 'lock',
                    'currency_code': lock_currency,
                    'amount': amount,
                    'description': f'Locked for order {order_id}',
                    'order_id': order_id
                },
                'event_source': 'trading_event_handler',
                'priority': 'high'
            })
            
            actions.append(f'Created lock transaction request for {amount} {lock_currency}')
        
        elif action == 'order_filled':
            order_id = event_data.get('order_id')
            actions.append(f'Processing order fill: {order_id}')
            
            # Unlock funds and process trade
            downstream_events.append({
                'event_type': 'transaction_requested',
                'event_data': {
                    'transaction_type': 'unlock',
                    'currency_code': event_data.get('currency_code', 'EUR'),
                    'amount': event_data.get('amount', 0),
                    'order_id': order_id
                },
                'event_source': 'trading_event_handler'
            })
            
            actions.append(f'Created unlock transaction for filled order {order_id}')
        
        elif action == 'order_cancelled':
            order_id = event_data.get('order_id')
            actions.append(f'Processing order cancellation: {order_id}')
            
            # Unlock funds
            downstream_events.append({
                'event_type': 'transaction_requested',
                'event_data': {
                    'transaction_type': 'unlock',
                    'currency_code': event_data.get('currency_code', 'EUR'),
                    'amount': event_data.get('amount', 0),
                    'order_id': order_id
                },
                'event_source': 'trading_event_handler'
            })
            
            actions.append(f'Created unlock transaction for cancelled order {order_id}')
        
        return {
            'success': True,
            'actions': actions,
            'downstream_events': downstream_events
        }
    
    async def _handle_portfolio_event(self, event_data: Dict[str, Any], 
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Portfolio State Changed Events"""
        
        actions = ['Processing portfolio state change event']
        
        transaction_id = event_data.get('transaction_id')
        currency_code = event_data.get('currency_code')
        transaction_type = event_data.get('transaction_type')
        amount = event_data.get('amount')
        
        actions.append(f'Portfolio changed due to {transaction_type}: {amount} {currency_code}')
        
        # Update account state
        update_account_state = {
            'last_activity': datetime.now(),
            'recent_transactions': [
                {
                    'transaction_id': transaction_id,
                    'type': transaction_type,
                    'currency': currency_code,
                    'amount': amount,
                    'timestamp': datetime.now()
                }
            ]
        }
        
        # Portfolio Rebalancing Check für große Transaktionen
        downstream_events = []
        if abs(float(amount)) > 10000:  # Large transaction
            downstream_events.append({
                'event_type': 'portfolio_analysis_requested',
                'event_data': {
                    'trigger': 'large_transaction',
                    'transaction_id': transaction_id,
                    'amount': amount,
                    'currency': currency_code
                },
                'event_source': 'portfolio_event_handler'
            })
            actions.append('Requested portfolio analysis due to large transaction')
        
        return {
            'success': True,
            'actions': actions,
            'downstream_events': downstream_events,
            'update_account_state': update_account_state
        }
    
    async def _handle_config_event(self, event_data: Dict[str, Any], 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Configuration Update Events"""
        
        actions = ['Processing configuration update event']
        
        config_section = event_data.get('section')
        config_changes = event_data.get('changes', {})
        
        actions.append(f'Configuration section updated: {config_section}')
        
        # Account-spezifische Config Updates
        if config_section == 'account_limits':
            actions.append(f'Account limits updated: {list(config_changes.keys())}')
            
            # Update local account state
            update_account_state = {
                'limits': config_changes,
                'config_last_updated': datetime.now()
            }
            
            return {
                'success': True,
                'actions': actions,
                'update_account_state': update_account_state
            }
        
        elif config_section == 'withdrawal_limits':
            actions.append(f'Withdrawal limits updated for currencies: {list(config_changes.keys())}')
        
        return {
            'success': True,
            'actions': actions
        }
    
    async def _handle_system_alert_event(self, event_data: Dict[str, Any], 
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt System Alert Events"""
        
        actions = ['Processing system alert event']
        
        alert_type = event_data.get('alert_type')
        alert_severity = event_data.get('severity', 'medium')
        alert_message = event_data.get('message', '')
        
        actions.append(f'System alert: {alert_type} - {alert_severity}')
        
        downstream_events = []
        
        if alert_type == 'account_frozen':
            actions.append('Account freeze alert received - implementing protective measures')
            
            # Update account state
            update_account_state = {
                'account_status': 'frozen',
                'freeze_reason': alert_message,
                'freeze_timestamp': datetime.now()
            }
            
            # Create notification event
            downstream_events.append({
                'event_type': 'account_status_changed',
                'event_data': {
                    'old_status': 'active',
                    'new_status': 'frozen',
                    'reason': alert_message
                },
                'event_source': 'system_alert_handler',
                'priority': 'critical'
            })
            
            return {
                'success': True,
                'actions': actions,
                'downstream_events': downstream_events,
                'update_account_state': update_account_state
            }
        
        elif alert_type == 'security_breach':
            actions.append('Security breach alert - initiating lockdown procedures')
            
            # Emergency account protection
            downstream_events.append({
                'event_type': 'emergency_lockdown',
                'event_data': {
                    'reason': 'security_breach',
                    'alert_message': alert_message
                },
                'event_source': 'system_alert_handler',
                'priority': 'critical'
            })
        
        return {
            'success': True,
            'actions': actions,
            'downstream_events': downstream_events
        }
    
    async def _handle_transaction_event(self, event_data: Dict[str, Any], 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Transaction Completed Events"""
        
        actions = ['Processing transaction completed event']
        
        transaction_id = event_data.get('transaction_id')
        transaction_type = event_data.get('transaction_type')
        currency_code = event_data.get('currency_code')
        amount = event_data.get('amount')
        new_balance = event_data.get('new_balance')
        
        actions.append(f'Transaction completed: {transaction_id} - {transaction_type}')
        
        # Update account state
        update_account_state = {
            'last_activity': datetime.now()
        }
        
        # Balance update
        if new_balance:
            if 'balances' not in update_account_state:
                update_account_state['balances'] = {}
            update_account_state['balances'][currency_code] = new_balance
            actions.append(f'Balance updated for {currency_code}: {new_balance}')
        
        return {
            'success': True,
            'actions': actions,
            'update_account_state': update_account_state
        }
    
    async def _handle_order_event(self, event_data: Dict[str, Any], 
                                context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Order Status Changed Events"""
        
        actions = ['Processing order status change event']
        
        order_id = event_data.get('order_id')
        old_status = event_data.get('old_status')
        new_status = event_data.get('new_status')
        
        actions.append(f'Order {order_id}: {old_status} -> {new_status}')
        
        return {
            'success': True,
            'actions': actions
        }
    
    async def _handle_balance_event(self, event_data: Dict[str, Any], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Balance Updated Events"""
        
        actions = ['Processing balance update event']
        
        currency_code = event_data.get('currency_code')
        old_balance = event_data.get('old_balance', {})
        new_balance = event_data.get('new_balance', {})
        
        actions.append(f'Balance updated for {currency_code}')
        
        # Calculate balance change
        old_total = float(old_balance.get('total', '0'))
        new_total = float(new_balance.get('total', '0'))
        balance_change = new_total - old_total
        
        if abs(balance_change) > 0.01:  # Significant change
            actions.append(f'Balance change: {balance_change:+.2f} {currency_code}')
        
        return {
            'success': True,
            'actions': actions
        }
    
    async def _handle_limits_event(self, event_data: Dict[str, Any], 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Limits Exceeded Events"""
        
        actions = ['Processing limits exceeded event']
        
        limit_type = event_data.get('limit_type')
        current_value = event_data.get('current_value')
        limit_value = event_data.get('limit_value')
        
        actions.append(f'Limit exceeded: {limit_type} - {current_value}/{limit_value}')
        
        # Generate warning event
        downstream_events = [{
            'event_type': 'compliance_warning',
            'event_data': {
                'warning_type': 'limit_exceeded',
                'limit_type': limit_type,
                'current_value': current_value,
                'limit_value': limit_value
            },
            'event_source': 'limits_event_handler',
            'priority': 'high'
        }]
        
        return {
            'success': True,
            'actions': actions,
            'downstream_events': downstream_events
        }
    
    async def _handle_account_freeze_event(self, event_data: Dict[str, Any], 
                                         context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Account Frozen Events"""
        
        actions = ['Processing account freeze event']
        
        freeze_reason = event_data.get('reason', 'Unknown')
        freeze_duration = event_data.get('duration', 'indefinite')
        
        actions.append(f'Account frozen: {freeze_reason} for {freeze_duration}')
        
        # Update account state
        update_account_state = {
            'account_status': 'frozen',
            'freeze_reason': freeze_reason,
            'freeze_duration': freeze_duration,
            'freeze_timestamp': datetime.now()
        }
        
        return {
            'success': True,
            'actions': actions,
            'update_account_state': update_account_state
        }
    
    async def _handle_withdrawal_event(self, event_data: Dict[str, Any], 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Behandelt Withdrawal Requested Events"""
        
        actions = ['Processing withdrawal request event']
        
        withdrawal_id = event_data.get('withdrawal_id')
        currency_code = event_data.get('currency_code')
        amount = event_data.get('amount')
        
        actions.append(f'Withdrawal requested: {withdrawal_id} - {amount} {currency_code}')
        
        # Create transaction processing event
        downstream_events = [{
            'event_type': 'transaction_requested',
            'event_data': {
                'transaction_type': 'withdrawal',
                'currency_code': currency_code,
                'amount': amount,
                'description': f'Withdrawal {withdrawal_id}',
                'withdrawal_id': withdrawal_id
            },
            'event_source': 'withdrawal_event_handler',
            'priority': 'high'
        }]
        
        return {
            'success': True,
            'actions': actions,
            'downstream_events': downstream_events
        }
    
    async def _update_account_state(self, state_updates: Dict[str, Any]):
        """Aktualisiert Account State basierend auf Event Processing"""
        
        for key, value in state_updates.items():
            if key == 'recent_transactions':
                if 'recent_transactions' not in self.account_state:
                    self.account_state['recent_transactions'] = []
                self.account_state['recent_transactions'].extend(value)
                
                # Keep only last 50 transactions
                self.account_state['recent_transactions'] = self.account_state['recent_transactions'][-50:]
            else:
                self.account_state[key] = value
        
        self.logger.debug(f"Account state updated",
                        updated_keys=list(state_updates.keys()))
    
    async def _update_event_statistics(self, request: EventHandlingRequest, 
                                     result: EventHandlingResult,
                                     processing_time_ms: float):
        """Aktualisiert Event Processing Statistics"""
        
        self.event_statistics['total_processed'] += 1
        
        if result.event_processed:
            self.event_statistics['successful_processed'] += 1
        else:
            self.event_statistics['failed_processed'] += 1
        
        # Event Type Statistics
        event_type = request.event_type
        if event_type not in self.event_statistics['events_by_type']:
            self.event_statistics['events_by_type'][event_type] = 0
        self.event_statistics['events_by_type'][event_type] += 1
        
        # Event Source Statistics
        event_source = request.event_source
        if event_source not in self.event_statistics['events_by_source']:
            self.event_statistics['events_by_source'][event_source] = 0
        self.event_statistics['events_by_source'][event_source] += 1
        
        # Update average processing time
        current_avg = self.event_statistics['average_processing_time']
        total_processed = self.event_statistics['total_processed']
        self.event_statistics['average_processing_time'] = round(
            ((current_avg * (total_processed - 1)) + processing_time_ms) / total_processed, 2
        )
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Registriert neuen Event Handler"""
        self.event_handlers[event_type] = handler
        self.logger.info(f"Event handler registered", event_type=event_type)
    
    def unregister_event_handler(self, event_type: str):
        """Entfernt Event Handler"""
        if event_type in self.event_handlers:
            del self.event_handlers[event_type]
            self.logger.info(f"Event handler unregistered", event_type=event_type)
    
    def get_registered_event_types(self) -> List[str]:
        """Gibt Liste der registrierten Event Types zurück"""
        return list(self.event_handlers.keys())
    
    def get_account_state(self) -> Dict[str, Any]:
        """Gibt aktuellen Account State zurück"""
        return self.account_state.copy()
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'event_handling',
            'description': 'Handles account-related events with comprehensive processing logic',
            'responsibility': 'Account event handling logic only',
            'input_parameters': {
                'event_type': 'Required event type to handle',
                'event_data': 'Required event data dictionary',
                'event_source': 'Optional event source (default: unknown)',
                'event_timestamp': 'Optional event timestamp (default: now)',
                'priority': 'Optional event priority (low, normal, high, critical)',
                'handle_synchronously': 'Whether to handle synchronously (default: true)',
                'enable_downstream_events': 'Whether to enable downstream events (default: true)'
            },
            'output_format': {
                'event_processed': 'Whether the event was processed successfully',
                'processing_actions': 'List of actions taken during processing',
                'downstream_events': 'List of events generated as result',
                'processing_time_ms': 'Time taken to process the event',
                'error_details': 'Error details if processing failed'
            },
            'supported_event_types': list(self.event_handlers.keys()),
            'handling_configuration': self.handling_config,
            'priority_levels': ['low', 'normal', 'high', 'critical'],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_event_handling_statistics(self) -> Dict[str, Any]:
        """Event Handling Module Statistiken"""
        
        total_processed = self.event_statistics['total_processed']
        
        if total_processed == 0:
            return {
                'total_events_processed': 0,
                'registered_event_handlers': len(self.event_handlers),
                'queued_events': len(self.priority_queue)
            }
        
        # Success Rate
        success_rate = round(
            (self.event_statistics['successful_processed'] / total_processed) * 100, 1
        ) if total_processed > 0 else 0
        
        # Recent Activity
        recent_events = [
            event for event in self.processing_history
            if (datetime.now() - event['timestamp']).seconds < 3600  # Last hour
        ]
        
        # Most Common Event Types
        event_types_sorted = dict(sorted(
            self.event_statistics['events_by_type'].items(),
            key=lambda x: x[1], reverse=True
        ))
        
        return {
            'total_events_processed': total_processed,
            'successful_events': self.event_statistics['successful_processed'],
            'failed_events': self.event_statistics['failed_processed'],
            'success_rate_percent': success_rate,
            'recent_events_last_hour': len(recent_events),
            'registered_event_handlers': len(self.event_handlers),
            'queued_events': len(self.priority_queue),
            'events_by_type_distribution': event_types_sorted,
            'events_by_source_distribution': dict(sorted(
                self.event_statistics['events_by_source'].items(),
                key=lambda x: x[1], reverse=True
            )),
            'average_processing_time_ms': self.event_statistics['average_processing_time'],
            'module_processing_time': self.average_execution_time
        }

    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions"""
        try:
            # Subscribe to relevant events for this module
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            
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
                        'execution_count': getattr(self, 'execution_history', []),
                        'average_execution_time_ms': self.average_execution_time,
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
            
            else:
                self.logger.debug("Unhandled event type", 
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)
