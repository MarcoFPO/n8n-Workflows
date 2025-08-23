"""
Redis Event-Bus System Integration für aktienanalyse-ökosystem
Complete Integration Interface für alle Services mit dem Production-Ready Event-Bus
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import asdict

# Import all Redis Event-Bus components
from shared.redis_event_bus import RedisEventBus, Event, EventPriority
from shared.redis_event_bus_factory import (
    initialize_event_bus_system, shutdown_event_bus_system, 
    get_event_bus, ServiceEventBusRegistry
)
from shared.redis_event_publishers import PublisherFactory
from shared.redis_event_subscribers import SubscriberFactory
from shared.redis_event_performance import run_performance_tests, run_single_load_test, LoadTestConfig, LoadTestType
from shared.redis_event_monitoring import start_system_monitoring, stop_system_monitoring, get_system_overview
from shared.redis_event_test_runner import run_comprehensive_tests, run_basic_performance_check

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


class AktienAnalyseEventBusIntegration:
    """
    Central Integration Interface for all aktienanalyse-ökosystem Services
    Provides unified interface to the Redis Event-Bus Infrastructure
    """
    
    def __init__(self):
        self.logger = logger.bind(component="aktienanalyse_integration")
        self.initialized = False
        self.service_publishers: Dict[str, Any] = {}
        self.service_subscribers: Dict[str, Any] = {}
        
        # aktienanalyse-ökosystem service mapping
        self.service_mapping = {
            'account': 'account-service',
            'order': 'order-service',
            'data-analysis': 'data-analysis-service', 
            'intelligent-core': 'intelligent-core-service',
            'market-data': 'market-data-service',
            'frontend': 'frontend-service'
        }
    
    async def initialize_system(self) -> bool:
        """Initialize complete Redis Event-Bus system for aktienanalyse-ökosystem"""
        try:
            self.logger.info("Initializing aktienanalyse-ökosystem Event-Bus system")
            
            # Initialize Redis Event-Bus infrastructure
            success = await initialize_event_bus_system()
            if not success:
                return False
            
            # Initialize service-specific publishers and subscribers
            await self._initialize_service_components()
            
            # Start system monitoring
            await start_system_monitoring(list(self.service_mapping.values()))
            
            self.initialized = True
            self.logger.info("aktienanalyse-ökosystem Event-Bus system initialized successfully")
            
            return True
            
        except Exception as e:
            self.logger.error("System initialization failed", error=str(e))
            return False
    
    async def shutdown_system(self):
        """Shutdown complete Event-Bus system"""
        try:
            self.logger.info("Shutting down aktienanalyse-ökosystem Event-Bus system")
            
            # Stop monitoring
            await stop_system_monitoring()
            
            # Shutdown Event-Bus infrastructure
            await shutdown_event_bus_system()
            
            self.initialized = False
            self.logger.info("System shutdown completed")
            
        except Exception as e:
            self.logger.error("System shutdown failed", error=str(e))
    
    async def _initialize_service_components(self):
        """Initialize publishers and subscribers for all services"""
        try:
            # Initialize publishers for each service
            for service_key, service_name in self.service_mapping.items():
                try:
                    # Create service-specific publishers
                    if service_key == 'market-data':
                        publisher = await PublisherFactory.create_market_data_publisher(service_name)
                        self.service_publishers[f'{service_key}_market'] = publisher
                    elif service_key == 'data-analysis':
                        publisher = await PublisherFactory.create_analysis_publisher(service_name)
                        self.service_publishers[f'{service_key}_analysis'] = publisher
                    elif service_key == 'intelligent-core':
                        publisher = await PublisherFactory.create_intelligence_publisher(service_name)
                        self.service_publishers[f'{service_key}_intelligence'] = publisher
                    elif service_key == 'order':
                        publisher = await PublisherFactory.create_order_publisher(service_name)
                        self.service_publishers[f'{service_key}_orders'] = publisher
                    elif service_key == 'account':
                        publisher = await PublisherFactory.create_account_publisher(service_name)
                        self.service_publishers[f'{service_key}_accounts'] = publisher
                    
                    # All services get system publisher
                    system_publisher = await PublisherFactory.create_system_publisher(service_name)
                    self.service_publishers[f'{service_key}_system'] = system_publisher
                    
                except Exception as e:
                    self.logger.warning(f"Failed to create publishers for {service_name}", error=str(e))
            
            # Initialize subscribers for each service
            for service_key, service_name in self.service_mapping.items():
                try:
                    # Create service-specific subscribers based on needs
                    if service_key == 'intelligent-core':
                        # Intelligence service subscribes to analysis and market data
                        analysis_subscriber = await SubscriberFactory.create_analysis_subscriber(service_name)
                        market_subscriber = await SubscriberFactory.create_market_data_subscriber(service_name)
                        self.service_subscribers[f'{service_key}_analysis'] = analysis_subscriber
                        self.service_subscribers[f'{service_key}_market'] = market_subscriber
                    elif service_key == 'order':
                        # Order service subscribes to intelligence recommendations
                        intelligence_subscriber = await SubscriberFactory.create_intelligence_subscriber(service_name)
                        self.service_subscribers[f'{service_key}_intelligence'] = intelligence_subscriber
                    elif service_key == 'frontend':
                        # Frontend subscribes to all types for dashboard updates
                        system_subscriber = await SubscriberFactory.create_system_subscriber(service_name)
                        self.service_subscribers[f'{service_key}_system'] = system_subscriber
                    
                except Exception as e:
                    self.logger.warning(f"Failed to create subscribers for {service_name}", error=str(e))
            
            self.logger.info("Service components initialized", 
                           publishers=len(self.service_publishers),
                           subscribers=len(self.service_subscribers))
            
        except Exception as e:
            self.logger.error("Failed to initialize service components", error=str(e))
    
    async def publish_market_data_event(self, symbol: str, price: float, 
                                       volume: int, indicators: Dict[str, float]) -> bool:
        """Publish market data price update event"""
        if not self.initialized:
            await self.initialize_system()
        
        publisher = self.service_publishers.get('market-data_market')
        if not publisher:
            self.logger.error("Market data publisher not available")
            return False
        
        from shared.redis_event_publishers import MarketDataEvent
        
        market_event = MarketDataEvent(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=datetime.now(),
            indicators=indicators
        )
        
        return await publisher.publish_price_update(market_event, EventPriority.HIGH)
    
    async def publish_analysis_complete(self, symbol: str, analysis_type: str,
                                      results: Dict[str, Any], confidence: float) -> bool:
        """Publish analysis completion event"""
        if not self.initialized:
            await self.initialize_system()
        
        publisher = self.service_publishers.get('data-analysis_analysis')
        if not publisher:
            self.logger.error("Analysis publisher not available")
            return False
        
        from shared.redis_event_publishers import AnalysisEvent
        
        analysis_event = AnalysisEvent(
            symbol=symbol,
            analysis_type=analysis_type,
            results=results,
            confidence=confidence,
            timestamp=datetime.now()
        )
        
        return await publisher.publish_analysis_complete(analysis_event)
    
    async def publish_intelligence_recommendation(self, symbol: str, recommendation: str,
                                                confidence: float, reasoning: List[str],
                                                risk_assessment: Dict[str, Any]) -> bool:
        """Publish intelligence recommendation event"""
        if not self.initialized:
            await self.initialize_system()
        
        publisher = self.service_publishers.get('intelligent-core_intelligence')
        if not publisher:
            self.logger.error("Intelligence publisher not available")
            return False
        
        from shared.redis_event_publishers import IntelligenceEvent
        
        intelligence_event = IntelligenceEvent(
            symbol=symbol,
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            risk_assessment=risk_assessment,
            timestamp=datetime.now()
        )
        
        return await publisher.publish_recommendation(intelligence_event, EventPriority.HIGH)
    
    async def publish_order_event(self, order_id: str, symbol: str, action: str,
                                order_type: str, quantity: float, price: Optional[float],
                                status: str) -> bool:
        """Publish order event"""
        if not self.initialized:
            await self.initialize_system()
        
        publisher = self.service_publishers.get('order_orders')
        if not publisher:
            self.logger.error("Order publisher not available")
            return False
        
        from shared.redis_event_publishers import OrderEvent
        
        order_event = OrderEvent(
            order_id=order_id,
            symbol=symbol,
            action=action,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=status,
            timestamp=datetime.now()
        )
        
        if action == "create":
            return await publisher.publish_order_created(order_event)
        elif action == "update":
            return await publisher.publish_order_updated(order_event)
        elif action == "execute":
            return await publisher.publish_order_executed(order_id, symbol, quantity, price or 0.0)
        elif action == "cancel":
            return await publisher.publish_order_cancelled(order_id, symbol, "User cancellation")
        
        return False
    
    async def publish_system_health_event(self, service_name: str, health_data: Dict[str, Any]) -> bool:
        """Publish system health check event"""
        if not self.initialized:
            await self.initialize_system()
        
        # Map service name to our internal mapping
        service_key = None
        for key, mapped_name in self.service_mapping.items():
            if mapped_name == service_name or key == service_name:
                service_key = key
                break
        
        if not service_key:
            service_key = 'frontend'  # Default fallback
        
        publisher = self.service_publishers.get(f'{service_key}_system')
        if not publisher:
            self.logger.error("System publisher not available", service=service_name)
            return False
        
        return await publisher.publish_health_check(health_data)
    
    async def run_system_performance_tests(self) -> Dict[str, Any]:
        """Run comprehensive performance tests on the system"""
        if not self.initialized:
            await self.initialize_system()
        
        self.logger.info("Starting comprehensive performance tests")
        return await run_comprehensive_tests()
    
    async def run_quick_health_check(self) -> Dict[str, Any]:
        """Run quick system health check"""
        if not self.initialized:
            await self.initialize_system()
        
        return await run_basic_performance_check()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status overview"""
        if not self.initialized:
            return {
                'status': 'not_initialized',
                'message': 'Event-Bus system not initialized'
            }
        
        return get_system_overview()
    
    async def setup_service_event_handlers(self, service_name: str, handlers: Dict[str, callable]):
        """Setup event handlers for a specific service"""
        try:
            # Map service name
            service_key = None
            for key, mapped_name in self.service_mapping.items():
                if mapped_name == service_name or key == service_name:
                    service_key = key
                    break
            
            if not service_key:
                self.logger.error("Unknown service name", service=service_name)
                return False
            
            # Get event bus for service
            event_bus = await get_event_bus(self.service_mapping[service_key])
            if not event_bus:
                self.logger.error("Event bus not available for service", service=service_name)
                return False
            
            # Subscribe to events with provided handlers
            for event_type, handler in handlers.items():
                success = await event_bus.subscribe(event_type, handler)
                if success:
                    self.logger.info("Event handler registered", 
                                   service=service_name, 
                                   event_type=event_type)
                else:
                    self.logger.error("Failed to register event handler",
                                    service=service_name,
                                    event_type=event_type)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to setup event handlers", 
                            service=service_name, error=str(e))
            return False


# Global integration instance for the aktienanalyse-ökosystem
aktienanalyse_event_bus = AktienAnalyseEventBusIntegration()

# Convenience functions for easy integration
async def initialize_aktienanalyse_event_system() -> bool:
    """Initialize the complete Event-Bus system for aktienanalyse-ökosystem"""
    return await aktienanalyse_event_bus.initialize_system()

async def shutdown_aktienanalyse_event_system():
    """Shutdown the Event-Bus system"""
    await aktienanalyse_event_bus.shutdown_system()

# Event publishing convenience functions
async def publish_market_update(symbol: str, price: float, volume: int, indicators: Dict[str, float] = None) -> bool:
    """Quick market data update"""
    return await aktienanalyse_event_bus.publish_market_data_event(
        symbol, price, volume, indicators or {}
    )

async def publish_analysis_result(symbol: str, analysis_type: str, results: Dict[str, Any], confidence: float) -> bool:
    """Quick analysis result publish"""
    return await aktienanalyse_event_bus.publish_analysis_complete(
        symbol, analysis_type, results, confidence
    )

async def publish_trading_recommendation(symbol: str, recommendation: str, confidence: float, 
                                       reasoning: List[str], risk_assessment: Dict[str, Any]) -> bool:
    """Quick trading recommendation publish"""
    return await aktienanalyse_event_bus.publish_intelligence_recommendation(
        symbol, recommendation, confidence, reasoning, risk_assessment
    )

async def publish_order_update(order_id: str, symbol: str, action: str, order_type: str,
                              quantity: float, price: float = None, status: str = "pending") -> bool:
    """Quick order update publish"""
    return await aktienanalyse_event_bus.publish_order_event(
        order_id, symbol, action, order_type, quantity, price, status
    )

async def publish_health_status(service_name: str, health_data: Dict[str, Any]) -> bool:
    """Quick health status publish"""
    return await aktienanalyse_event_bus.publish_system_health_event(service_name, health_data)

# System monitoring convenience functions
def get_current_system_status() -> Dict[str, Any]:
    """Get current system status"""
    return aktienanalyse_event_bus.get_system_status()

async def run_performance_validation() -> Dict[str, Any]:
    """Run performance validation tests"""
    return await aktienanalyse_event_bus.run_quick_health_check()

async def run_comprehensive_system_tests() -> Dict[str, Any]:
    """Run comprehensive system tests"""
    return await aktienanalyse_event_bus.run_system_performance_tests()

# Service integration helper
async def register_service_handlers(service_name: str, event_handlers: Dict[str, callable]) -> bool:
    """Register event handlers for a service"""
    return await aktienanalyse_event_bus.setup_service_event_handlers(service_name, event_handlers)


# Example usage for aktienanalyse-ökosystem services:
"""
# In any service, use the integration like this:

from shared.redis_event_system_integration import (
    initialize_aktienanalyse_event_system,
    publish_market_update,
    publish_analysis_result,
    publish_trading_recommendation,
    register_service_handlers
)

# Initialize the event system (once per application)
await initialize_aktienanalyse_event_system()

# Publish events
await publish_market_update("AAPL", 150.25, 1000000, {"rsi": 65.2, "macd": 1.8})
await publish_analysis_result("AAPL", "technical", {"score": 8.5, "trend": "bullish"}, 0.87)
await publish_trading_recommendation("AAPL", "BUY", 0.87, ["Technical indicators positive"], {"risk_level": "medium"})

# Register event handlers
handlers = {
    "analysis.complete": handle_analysis_complete,
    "intelligence.recommendation": handle_recommendation,
    "market_data.price_update": handle_price_update
}
await register_service_handlers("intelligent-core-service", handlers)
"""