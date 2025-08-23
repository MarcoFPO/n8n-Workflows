"""
Redis Event Subscribers - Specialized Event Subscription Components
High-level event subscription abstractions with automatic retry and error handling
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

from shared.redis_event_bus import RedisEventBus, Event, EventPriority
from shared.redis_event_bus_factory import get_event_bus

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"ℹ️ {msg} {kwargs}")
        def debug(self, msg, **kwargs): print(f"🐛 {msg} {kwargs}")
        def error(self, msg, **kwargs): print(f"❌ {msg} {kwargs}")
        def warning(self, msg, **kwargs): print(f"⚠️ {msg} {kwargs}")
    logger = MockLogger()


@dataclass
class SubscriptionConfig:
    """Configuration for event subscriptions"""
    event_types: List[str]
    handler: Callable
    retry_count: int = 3
    retry_delay: float = 1.0
    dead_letter_enabled: bool = True
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    batch_processing: bool = False
    batch_size: int = 10
    batch_timeout: float = 5.0


class EventHandler(ABC):
    """Abstract base class for event handlers"""
    
    @abstractmethod
    async def handle(self, event_data: Dict[str, Any]) -> bool:
        """Handle event data. Return True for success, False for failure"""
        pass
    
    @abstractmethod
    def get_event_types(self) -> List[str]:
        """Get list of event types this handler processes"""
        pass


class BaseEventSubscriber:
    """Base class for event subscribers with error handling and retries"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.event_bus: Optional[RedisEventBus] = None
        self.logger = logger.bind(service=service_name)
        
        # Subscription tracking
        self.active_subscriptions: Dict[str, SubscriptionConfig] = {}
        self.handlers: Dict[str, List[Callable]] = {}
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = {
            'events_received': 0,
            'events_processed': 0,
            'events_failed': 0,
            'handlers_active': 0,
            'circuit_breakers_open': 0,
            'last_event_time': None
        }
    
    async def initialize(self):
        """Initialize the event subscriber"""
        try:
            self.event_bus = await get_event_bus(self.service_name)
            self.logger.info("Event subscriber initialized")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize event subscriber", error=str(e))
            return False
    
    async def subscribe(self, config: SubscriptionConfig) -> bool:
        """Subscribe to events with configuration"""
        try:
            if not self.event_bus:
                await self.initialize()
            
            # Register handlers for each event type
            for event_type in config.event_types:
                success = await self.event_bus.subscribe(
                    event_type, 
                    self._create_handler_wrapper(event_type, config)
                )
                
                if success:
                    if event_type not in self.handlers:
                        self.handlers[event_type] = []
                    self.handlers[event_type].append(config.handler)
                    
                    # Store subscription configuration
                    self.active_subscriptions[event_type] = config
                    
                    # Initialize circuit breaker
                    if config.circuit_breaker_enabled:
                        self.circuit_breakers[event_type] = {
                            'failures': 0,
                            'last_failure': None,
                            'state': 'closed'
                        }
                    
                    self.metrics['handlers_active'] += 1
                    self.logger.info("Subscribed to event type", event_type=event_type)
                else:
                    self.logger.error("Failed to subscribe to event type", event_type=event_type)
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to subscribe", error=str(e))
            return False
    
    def _create_handler_wrapper(self, event_type: str, config: SubscriptionConfig) -> Callable:
        """Create wrapper for event handler with error handling and retries"""
        
        async def handler_wrapper(event_data: Dict[str, Any]):
            try:
                # Check circuit breaker
                if not await self._check_circuit_breaker(event_type, config):
                    self.logger.warning("Circuit breaker open, dropping event", 
                                      event_type=event_type)
                    return
                
                self.metrics['events_received'] += 1
                self.metrics['last_event_time'] = datetime.now()
                
                # Execute handler with retry logic
                success = await self._execute_with_retry(event_type, config, event_data)
                
                if success:
                    self.metrics['events_processed'] += 1
                    await self._circuit_breaker_success(event_type)
                else:
                    self.metrics['events_failed'] += 1
                    await self._circuit_breaker_failure(event_type, config)
                
            except Exception as e:
                self.metrics['events_failed'] += 1
                self.logger.error("Handler wrapper error", 
                                event_type=event_type, 
                                error=str(e))
                await self._circuit_breaker_failure(event_type, config)
        
        return handler_wrapper
    
    async def _execute_with_retry(self, event_type: str, config: SubscriptionConfig, 
                                event_data: Dict[str, Any]) -> bool:
        """Execute handler with retry logic"""
        last_error = None
        
        for attempt in range(config.retry_count + 1):
            try:
                # Execute handler
                if asyncio.iscoroutinefunction(config.handler):
                    result = await config.handler(event_data)
                else:
                    result = config.handler(event_data)
                
                # Consider None or True as success
                if result is None or result is True:
                    if attempt > 0:
                        self.logger.info("Handler succeeded after retries", 
                                       event_type=event_type, 
                                       attempt=attempt)
                    return True
                
                # Handler returned False - consider as failure
                last_error = f"Handler returned False for event type: {event_type}"
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning("Handler execution failed", 
                                  event_type=event_type, 
                                  attempt=attempt, 
                                  error=str(e))
            
            # Wait before retry (except for last attempt)
            if attempt < config.retry_count:
                await asyncio.sleep(config.retry_delay * (2 ** attempt))  # Exponential backoff
        
        # All retries exhausted
        self.logger.error("Handler failed after all retries", 
                         event_type=event_type, 
                         retries=config.retry_count,
                         last_error=last_error)
        
        # Send to dead letter queue if enabled
        if config.dead_letter_enabled:
            await self._send_to_dead_letter(event_type, event_data, last_error)
        
        return False
    
    async def _check_circuit_breaker(self, event_type: str, config: SubscriptionConfig) -> bool:
        """Check circuit breaker state"""
        if not config.circuit_breaker_enabled or event_type not in self.circuit_breakers:
            return True
        
        cb_state = self.circuit_breakers[event_type]
        current_time = datetime.now()
        
        if cb_state['state'] == 'open':
            # Check if timeout has passed
            if (cb_state['last_failure'] and 
                (current_time - cb_state['last_failure']).total_seconds() > config.circuit_breaker_timeout):
                cb_state['state'] = 'half_open'
                self.logger.info("Circuit breaker half-open", event_type=event_type)
                return True
            return False
        
        return True
    
    async def _circuit_breaker_success(self, event_type: str):
        """Record successful event processing"""
        if event_type not in self.circuit_breakers:
            return
        
        cb_state = self.circuit_breakers[event_type]
        if cb_state['state'] == 'half_open':
            cb_state['state'] = 'closed'
            cb_state['failures'] = 0
            self.logger.info("Circuit breaker closed", event_type=event_type)
    
    async def _circuit_breaker_failure(self, event_type: str, config: SubscriptionConfig):
        """Record failed event processing"""
        if not config.circuit_breaker_enabled or event_type not in self.circuit_breakers:
            return
        
        cb_state = self.circuit_breakers[event_type]
        cb_state['failures'] += 1
        cb_state['last_failure'] = datetime.now()
        
        if cb_state['failures'] >= config.circuit_breaker_threshold:
            cb_state['state'] = 'open'
            self.metrics['circuit_breakers_open'] += 1
            self.logger.warning("Circuit breaker opened", 
                              event_type=event_type, 
                              failures=cb_state['failures'])
    
    async def _send_to_dead_letter(self, event_type: str, event_data: Dict[str, Any], error: str):
        """Send failed event to dead letter queue"""
        try:
            # This would typically send to a dead letter queue
            # For now, just log the failure
            self.logger.error("Event sent to dead letter queue", 
                            event_type=event_type, 
                            error=error,
                            event_data_sample=str(event_data)[:200])
        except Exception as e:
            self.logger.error("Failed to send to dead letter queue", error=str(e))
    
    async def unsubscribe(self, event_type: str) -> bool:
        """Unsubscribe from event type"""
        try:
            if event_type in self.active_subscriptions:
                success = await self.event_bus.unsubscribe(event_type)
                if success:
                    del self.active_subscriptions[event_type]
                    if event_type in self.handlers:
                        del self.handlers[event_type]
                    if event_type in self.circuit_breakers:
                        del self.circuit_breakers[event_type]
                    self.metrics['handlers_active'] -= 1
                    self.logger.info("Unsubscribed from event type", event_type=event_type)
                return success
            return True
        except Exception as e:
            self.logger.error("Failed to unsubscribe", event_type=event_type, error=str(e))
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get subscriber metrics"""
        return {
            **self.metrics.copy(),
            'active_subscriptions': len(self.active_subscriptions),
            'circuit_breaker_states': {
                event_type: cb['state'] 
                for event_type, cb in self.circuit_breakers.items()
            }
        }


class MarketDataSubscriber(BaseEventSubscriber):
    """Subscriber for market data events"""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.price_handlers: List[Callable] = []
        self.indicator_handlers: List[Callable] = []
        self.status_handlers: List[Callable] = []
    
    async def subscribe_to_price_updates(self, handler: Callable, 
                                       retry_count: int = 3) -> bool:
        """Subscribe to real-time price updates"""
        config = SubscriptionConfig(
            event_types=['market_data.price_update'],
            handler=handler,
            retry_count=retry_count,
            circuit_breaker_enabled=True
        )
        
        self.price_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_indicator_updates(self, handler: Callable,
                                           retry_count: int = 2) -> bool:
        """Subscribe to technical indicator updates"""
        config = SubscriptionConfig(
            event_types=['market_data.indicators_update'],
            handler=handler,
            retry_count=retry_count
        )
        
        self.indicator_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_status_changes(self, handler: Callable,
                                        retry_count: int = 5) -> bool:
        """Subscribe to market status changes"""
        config = SubscriptionConfig(
            event_types=['market_data.status_change'],
            handler=handler,
            retry_count=retry_count,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3
        )
        
        self.status_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_batch_updates(self, handler: Callable,
                                       batch_size: int = 50) -> bool:
        """Subscribe to batch market data updates"""
        config = SubscriptionConfig(
            event_types=['market_data.batch_update'],
            handler=handler,
            retry_count=3,
            batch_processing=True,
            batch_size=batch_size
        )
        
        return await self.subscribe(config)


class AnalysisSubscriber(BaseEventSubscriber):
    """Subscriber for analysis events"""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.analysis_handlers: List[Callable] = []
        self.request_handlers: List[Callable] = []
    
    async def subscribe_to_analysis_complete(self, handler: Callable,
                                           retry_count: int = 3) -> bool:
        """Subscribe to completed analysis results"""
        config = SubscriptionConfig(
            event_types=['analysis.complete'],
            handler=handler,
            retry_count=retry_count
        )
        
        self.analysis_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_analysis_requests(self, handler: Callable,
                                           retry_count: int = 2) -> bool:
        """Subscribe to analysis requests"""
        config = SubscriptionConfig(
            event_types=['analysis.request'],
            handler=handler,
            retry_count=retry_count,
            circuit_breaker_threshold=10  # Higher threshold for requests
        )
        
        self.request_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_analysis_errors(self, handler: Callable) -> bool:
        """Subscribe to analysis errors"""
        config = SubscriptionConfig(
            event_types=['analysis.error'],
            handler=handler,
            retry_count=1,  # Don't retry error notifications much
            dead_letter_enabled=False
        )
        
        return await self.subscribe(config)


class IntelligenceSubscriber(BaseEventSubscriber):
    """Subscriber for intelligence decision events"""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.recommendation_handlers: List[Callable] = []
        self.decision_request_handlers: List[Callable] = []
    
    async def subscribe_to_recommendations(self, handler: Callable,
                                         retry_count: int = 5) -> bool:
        """Subscribe to investment recommendations"""
        config = SubscriptionConfig(
            event_types=['intelligence.recommendation'],
            handler=handler,
            retry_count=retry_count,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3
        )
        
        self.recommendation_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_decision_requests(self, handler: Callable,
                                           retry_count: int = 3) -> bool:
        """Subscribe to decision requests"""
        config = SubscriptionConfig(
            event_types=['intelligence.decision_request'],
            handler=handler,
            retry_count=retry_count
        )
        
        self.decision_request_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_model_updates(self, handler: Callable) -> bool:
        """Subscribe to ML model updates"""
        config = SubscriptionConfig(
            event_types=['intelligence.model_update'],
            handler=handler,
            retry_count=2,
            dead_letter_enabled=False
        )
        
        return await self.subscribe(config)


class OrderSubscriber(BaseEventSubscriber):
    """Subscriber for order events"""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.order_handlers: List[Callable] = []
    
    async def subscribe_to_order_events(self, handler: Callable,
                                      retry_count: int = 5) -> bool:
        """Subscribe to all order events"""
        config = SubscriptionConfig(
            event_types=[
                'order.created',
                'order.updated', 
                'order.executed',
                'order.cancelled'
            ],
            handler=handler,
            retry_count=retry_count,
            circuit_breaker_enabled=True
        )
        
        self.order_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_order_executions(self, handler: Callable,
                                          retry_count: int = 10) -> bool:
        """Subscribe specifically to order executions"""
        config = SubscriptionConfig(
            event_types=['order.executed'],
            handler=handler,
            retry_count=retry_count,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=2  # Low tolerance for execution failures
        )
        
        return await self.subscribe(config)


class AccountSubscriber(BaseEventSubscriber):
    """Subscriber for account events"""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.balance_handlers: List[Callable] = []
        self.transaction_handlers: List[Callable] = []
    
    async def subscribe_to_balance_updates(self, handler: Callable,
                                         retry_count: int = 5) -> bool:
        """Subscribe to account balance updates"""
        config = SubscriptionConfig(
            event_types=['account.balance_update'],
            handler=handler,
            retry_count=retry_count,
            circuit_breaker_enabled=True
        )
        
        self.balance_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_transactions(self, handler: Callable,
                                      retry_count: int = 7) -> bool:
        """Subscribe to account transactions"""
        config = SubscriptionConfig(
            event_types=['account.transaction'],
            handler=handler,
            retry_count=retry_count,
            circuit_breaker_enabled=True
        )
        
        self.transaction_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_limit_changes(self, handler: Callable) -> bool:
        """Subscribe to account limit changes"""
        config = SubscriptionConfig(
            event_types=['account.limit_change'],
            handler=handler,
            retry_count=3
        )
        
        return await self.subscribe(config)


class SystemSubscriber(BaseEventSubscriber):
    """Subscriber for system events"""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.health_handlers: List[Callable] = []
        self.error_handlers: List[Callable] = []
    
    async def subscribe_to_health_checks(self, handler: Callable) -> bool:
        """Subscribe to system health checks"""
        config = SubscriptionConfig(
            event_types=['system.health_check'],
            handler=handler,
            retry_count=1,
            dead_letter_enabled=False
        )
        
        self.health_handlers.append(handler)
        return await self.subscribe(config)
    
    async def subscribe_to_service_events(self, handler: Callable) -> bool:
        """Subscribe to service start/stop events"""
        config = SubscriptionConfig(
            event_types=[
                'system.service_started',
                'system.service_stopped'
            ],
            handler=handler,
            retry_count=2
        )
        
        return await self.subscribe(config)
    
    async def subscribe_to_errors(self, handler: Callable) -> bool:
        """Subscribe to system errors"""
        config = SubscriptionConfig(
            event_types=['system.error'],
            handler=handler,
            retry_count=3,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=20  # High threshold for error events
        )
        
        self.error_handlers.append(handler)
        return await self.subscribe(config)


# Subscriber factory for easy creation
class SubscriberFactory:
    """Factory for creating specialized subscribers"""
    
    @staticmethod
    async def create_market_data_subscriber(service_name: str) -> MarketDataSubscriber:
        """Create market data subscriber"""
        subscriber = MarketDataSubscriber(service_name)
        await subscriber.initialize()
        return subscriber
    
    @staticmethod
    async def create_analysis_subscriber(service_name: str) -> AnalysisSubscriber:
        """Create analysis subscriber"""
        subscriber = AnalysisSubscriber(service_name)
        await subscriber.initialize()
        return subscriber
    
    @staticmethod
    async def create_intelligence_subscriber(service_name: str) -> IntelligenceSubscriber:
        """Create intelligence subscriber"""
        subscriber = IntelligenceSubscriber(service_name)
        await subscriber.initialize()
        return subscriber
    
    @staticmethod
    async def create_order_subscriber(service_name: str) -> OrderSubscriber:
        """Create order subscriber"""
        subscriber = OrderSubscriber(service_name)
        await subscriber.initialize()
        return subscriber
    
    @staticmethod
    async def create_account_subscriber(service_name: str) -> AccountSubscriber:
        """Create account subscriber"""
        subscriber = AccountSubscriber(service_name)
        await subscriber.initialize()
        return subscriber
    
    @staticmethod
    async def create_system_subscriber(service_name: str) -> SystemSubscriber:
        """Create system subscriber"""
        subscriber = SystemSubscriber(service_name)
        await subscriber.initialize()
        return subscriber


# Event handler decorators for easy handler creation
def market_data_handler(event_types: List[str] = None, retry_count: int = 3):
    """Decorator for market data event handlers"""
    def decorator(func):
        func._event_types = event_types or ['market_data.price_update']
        func._retry_count = retry_count
        func._handler_type = 'market_data'
        return func
    return decorator


def analysis_handler(event_types: List[str] = None, retry_count: int = 3):
    """Decorator for analysis event handlers"""
    def decorator(func):
        func._event_types = event_types or ['analysis.complete']
        func._retry_count = retry_count
        func._handler_type = 'analysis'
        return func
    return decorator


def intelligence_handler(event_types: List[str] = None, retry_count: int = 5):
    """Decorator for intelligence event handlers"""
    def decorator(func):
        func._event_types = event_types or ['intelligence.recommendation']
        func._retry_count = retry_count
        func._handler_type = 'intelligence'
        return func
    return decorator


def order_handler(event_types: List[str] = None, retry_count: int = 5):
    """Decorator for order event handlers"""
    def decorator(func):
        func._event_types = event_types or ['order.created', 'order.updated', 'order.executed', 'order.cancelled']
        func._retry_count = retry_count
        func._handler_type = 'order'
        return func
    return decorator


def account_handler(event_types: List[str] = None, retry_count: int = 5):
    """Decorator for account event handlers"""
    def decorator(func):
        func._event_types = event_types or ['account.balance_update', 'account.transaction']
        func._retry_count = retry_count
        func._handler_type = 'account'
        return func
    return decorator


def system_handler(event_types: List[str] = None, retry_count: int = 2):
    """Decorator for system event handlers"""
    def decorator(func):
        func._event_types = event_types or ['system.health_check', 'system.error']
        func._retry_count = retry_count
        func._handler_type = 'system'
        return func
    return decorator