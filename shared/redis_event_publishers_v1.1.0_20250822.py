"""
Redis Event Publishers - Specialized Event Publishing Components
High-level event publishing abstractions for different event types
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from shared.redis_event_bus import RedisEventBus, Event, EventMetadata, EventPriority
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
class MarketDataEvent:
    """Market data event structure"""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    indicators: Dict[str, float]
    source: str = "market_data_service"


@dataclass
class AnalysisEvent:
    """Analysis result event structure"""
    symbol: str
    analysis_type: str
    results: Dict[str, Any]
    confidence: float
    timestamp: datetime
    source: str = "data_analysis_service"


@dataclass
class IntelligenceEvent:
    """Intelligence decision event structure"""
    symbol: str
    recommendation: str
    confidence: float
    reasoning: List[str]
    risk_assessment: Dict[str, Any]
    timestamp: datetime
    source: str = "intelligent_core_service"


@dataclass
class OrderEvent:
    """Order event structure"""
    order_id: str
    symbol: str
    action: str  # create, update, cancel, execute
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    timestamp: datetime
    source: str = "order_service"


@dataclass
class AccountEvent:
    """Account event structure"""
    account_id: str
    event_type: str  # balance_update, transaction, limit_change
    data: Dict[str, Any]
    timestamp: datetime
    source: str = "account_service"


class BaseEventPublisher:
    """Base class for specialized event publishers"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.event_bus: Optional[RedisEventBus] = None
        self.logger = logger.bind(service=service_name)
        
        # Event metrics
        self.metrics = {
            'events_published': 0,
            'events_failed': 0,
            'last_publish_time': None
        }
    
    async def initialize(self):
        """Initialize the event publisher"""
        try:
            self.event_bus = await get_event_bus(self.service_name)
            self.logger.info("Event publisher initialized")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize event publisher", error=str(e))
            return False
    
    async def _publish_event(self, event_type: str, data: Dict[str, Any], 
                           priority: EventPriority = EventPriority.NORMAL,
                           correlation_id: Optional[str] = None) -> bool:
        """Internal method to publish events"""
        try:
            if not self.event_bus:
                await self.initialize()
            
            event = await self.event_bus.create_event(
                event_type=event_type,
                data=data,
                priority=priority,
                correlation_id=correlation_id
            )
            
            success = await self.event_bus.publish(event)
            
            if success:
                self.metrics['events_published'] += 1
                self.metrics['last_publish_time'] = datetime.now()
            else:
                self.metrics['events_failed'] += 1
            
            return success
            
        except Exception as e:
            self.metrics['events_failed'] += 1
            self.logger.error("Failed to publish event", 
                            event_type=event_type, 
                            error=str(e))
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get publisher metrics"""
        return self.metrics.copy()


class MarketDataPublisher(BaseEventPublisher):
    """Publisher for market data events"""
    
    async def publish_price_update(self, market_data: MarketDataEvent, 
                                 priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish real-time price update"""
        data = {
            'symbol': market_data.symbol,
            'price': market_data.price,
            'volume': market_data.volume,
            'timestamp': market_data.timestamp.isoformat(),
            'indicators': market_data.indicators,
            'source': market_data.source
        }
        
        return await self._publish_event(
            event_type='market_data.price_update',
            data=data,
            priority=priority
        )
    
    async def publish_indicator_update(self, symbol: str, indicators: Dict[str, float],
                                     priority: EventPriority = EventPriority.NORMAL) -> bool:
        """Publish technical indicators update"""
        data = {
            'symbol': symbol,
            'indicators': indicators,
            'timestamp': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='market_data.indicators_update',
            data=data,
            priority=priority
        )
    
    async def publish_market_status(self, status: str, details: Dict[str, Any] = None,
                                  priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish market status change"""
        data = {
            'status': status,
            'details': details or {},
            'timestamp': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='market_data.status_change',
            data=data,
            priority=priority
        )
    
    async def publish_batch_updates(self, updates: List[MarketDataEvent]) -> bool:
        """Publish batch of market data updates"""
        batch_data = {
            'updates': [
                {
                    'symbol': update.symbol,
                    'price': update.price,
                    'volume': update.volume,
                    'timestamp': update.timestamp.isoformat(),
                    'indicators': update.indicators
                }
                for update in updates
            ],
            'batch_timestamp': datetime.now().isoformat(),
            'batch_size': len(updates),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='market_data.batch_update',
            data=batch_data,
            priority=EventPriority.HIGH
        )


class AnalysisPublisher(BaseEventPublisher):
    """Publisher for analysis events"""
    
    async def publish_analysis_complete(self, analysis: AnalysisEvent,
                                      priority: EventPriority = EventPriority.NORMAL) -> bool:
        """Publish completed analysis results"""
        data = {
            'symbol': analysis.symbol,
            'analysis_type': analysis.analysis_type,
            'results': analysis.results,
            'confidence': analysis.confidence,
            'timestamp': analysis.timestamp.isoformat(),
            'source': analysis.source
        }
        
        return await self._publish_event(
            event_type='analysis.complete',
            data=data,
            priority=priority
        )
    
    async def publish_analysis_request(self, symbol: str, analysis_types: List[str],
                                     priority: EventPriority = EventPriority.NORMAL,
                                     correlation_id: Optional[str] = None) -> bool:
        """Publish analysis request"""
        data = {
            'symbol': symbol,
            'analysis_types': analysis_types,
            'requested_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='analysis.request',
            data=data,
            priority=priority,
            correlation_id=correlation_id
        )
    
    async def publish_analysis_error(self, symbol: str, analysis_type: str, error: str,
                                   priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish analysis error"""
        data = {
            'symbol': symbol,
            'analysis_type': analysis_type,
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='analysis.error',
            data=data,
            priority=priority
        )


class IntelligencePublisher(BaseEventPublisher):
    """Publisher for intelligence decision events"""
    
    async def publish_recommendation(self, intelligence: IntelligenceEvent,
                                   priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish investment recommendation"""
        data = {
            'symbol': intelligence.symbol,
            'recommendation': intelligence.recommendation,
            'confidence': intelligence.confidence,
            'reasoning': intelligence.reasoning,
            'risk_assessment': intelligence.risk_assessment,
            'timestamp': intelligence.timestamp.isoformat(),
            'source': intelligence.source
        }
        
        return await self._publish_event(
            event_type='intelligence.recommendation',
            data=data,
            priority=priority
        )
    
    async def publish_decision_request(self, symbol: str, context: Dict[str, Any],
                                     priority: EventPriority = EventPriority.NORMAL,
                                     correlation_id: Optional[str] = None) -> bool:
        """Publish decision request"""
        data = {
            'symbol': symbol,
            'context': context,
            'requested_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='intelligence.decision_request',
            data=data,
            priority=priority,
            correlation_id=correlation_id
        )
    
    async def publish_model_update(self, model_name: str, version: str, 
                                 performance: Dict[str, float],
                                 priority: EventPriority = EventPriority.NORMAL) -> bool:
        """Publish ML model update"""
        data = {
            'model_name': model_name,
            'version': version,
            'performance': performance,
            'updated_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='intelligence.model_update',
            data=data,
            priority=priority
        )


class OrderPublisher(BaseEventPublisher):
    """Publisher for order events"""
    
    async def publish_order_created(self, order: OrderEvent,
                                  priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish order creation"""
        data = {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'action': order.action,
            'order_type': order.order_type,
            'quantity': order.quantity,
            'price': order.price,
            'status': order.status,
            'timestamp': order.timestamp.isoformat(),
            'source': order.source
        }
        
        return await self._publish_event(
            event_type='order.created',
            data=data,
            priority=priority
        )
    
    async def publish_order_updated(self, order: OrderEvent,
                                  priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish order update"""
        data = {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'action': order.action,
            'order_type': order.order_type,
            'quantity': order.quantity,
            'price': order.price,
            'status': order.status,
            'timestamp': order.timestamp.isoformat(),
            'source': order.source
        }
        
        return await self._publish_event(
            event_type='order.updated',
            data=data,
            priority=priority
        )
    
    async def publish_order_executed(self, order_id: str, symbol: str, 
                                   executed_quantity: float, executed_price: float,
                                   priority: EventPriority = EventPriority.CRITICAL) -> bool:
        """Publish order execution"""
        data = {
            'order_id': order_id,
            'symbol': symbol,
            'executed_quantity': executed_quantity,
            'executed_price': executed_price,
            'executed_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='order.executed',
            data=data,
            priority=priority
        )
    
    async def publish_order_cancelled(self, order_id: str, symbol: str, reason: str,
                                    priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish order cancellation"""
        data = {
            'order_id': order_id,
            'symbol': symbol,
            'reason': reason,
            'cancelled_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='order.cancelled',
            data=data,
            priority=priority
        )


class AccountPublisher(BaseEventPublisher):
    """Publisher for account events"""
    
    async def publish_balance_update(self, account: AccountEvent,
                                   priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish account balance update"""
        data = {
            'account_id': account.account_id,
            'event_type': account.event_type,
            'data': account.data,
            'timestamp': account.timestamp.isoformat(),
            'source': account.source
        }
        
        return await self._publish_event(
            event_type='account.balance_update',
            data=data,
            priority=priority
        )
    
    async def publish_transaction(self, account_id: str, transaction_data: Dict[str, Any],
                                priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish account transaction"""
        data = {
            'account_id': account_id,
            'transaction_data': transaction_data,
            'timestamp': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='account.transaction',
            data=data,
            priority=priority
        )
    
    async def publish_limit_change(self, account_id: str, limit_type: str, 
                                 old_value: float, new_value: float,
                                 priority: EventPriority = EventPriority.NORMAL) -> bool:
        """Publish account limit change"""
        data = {
            'account_id': account_id,
            'limit_type': limit_type,
            'old_value': old_value,
            'new_value': new_value,
            'changed_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='account.limit_change',
            data=data,
            priority=priority
        )


class SystemPublisher(BaseEventPublisher):
    """Publisher for system events"""
    
    async def publish_service_started(self, service_details: Dict[str, Any],
                                    priority: EventPriority = EventPriority.NORMAL) -> bool:
        """Publish service startup"""
        data = {
            'service_name': self.service_name,
            'details': service_details,
            'started_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='system.service_started',
            data=data,
            priority=priority
        )
    
    async def publish_service_stopped(self, reason: str = "normal_shutdown",
                                    priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish service shutdown"""
        data = {
            'service_name': self.service_name,
            'reason': reason,
            'stopped_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='system.service_stopped',
            data=data,
            priority=priority
        )
    
    async def publish_health_check(self, health_data: Dict[str, Any],
                                 priority: EventPriority = EventPriority.LOW) -> bool:
        """Publish health check result"""
        data = {
            'service_name': self.service_name,
            'health_data': health_data,
            'checked_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='system.health_check',
            data=data,
            priority=priority
        )
    
    async def publish_error(self, error_type: str, error_message: str, 
                          error_context: Dict[str, Any] = None,
                          priority: EventPriority = EventPriority.HIGH) -> bool:
        """Publish system error"""
        data = {
            'service_name': self.service_name,
            'error_type': error_type,
            'error_message': error_message,
            'error_context': error_context or {},
            'occurred_at': datetime.now().isoformat(),
            'source': self.service_name
        }
        
        return await self._publish_event(
            event_type='system.error',
            data=data,
            priority=priority
        )


# Publisher factory for easy creation
class PublisherFactory:
    """Factory for creating specialized publishers"""
    
    @staticmethod
    async def create_market_data_publisher(service_name: str = "market_data_service") -> MarketDataPublisher:
        """Create market data publisher"""
        publisher = MarketDataPublisher(service_name)
        await publisher.initialize()
        return publisher
    
    @staticmethod
    async def create_analysis_publisher(service_name: str = "data_analysis_service") -> AnalysisPublisher:
        """Create analysis publisher"""
        publisher = AnalysisPublisher(service_name)
        await publisher.initialize()
        return publisher
    
    @staticmethod
    async def create_intelligence_publisher(service_name: str = "intelligent_core_service") -> IntelligencePublisher:
        """Create intelligence publisher"""
        publisher = IntelligencePublisher(service_name)
        await publisher.initialize()
        return publisher
    
    @staticmethod
    async def create_order_publisher(service_name: str = "order_service") -> OrderPublisher:
        """Create order publisher"""
        publisher = OrderPublisher(service_name)
        await publisher.initialize()
        return publisher
    
    @staticmethod
    async def create_account_publisher(service_name: str = "account_service") -> AccountPublisher:
        """Create account publisher"""
        publisher = AccountPublisher(service_name)
        await publisher.initialize()
        return publisher
    
    @staticmethod
    async def create_system_publisher(service_name: str) -> SystemPublisher:
        """Create system publisher"""
        publisher = SystemPublisher(service_name)
        await publisher.initialize()
        return publisher