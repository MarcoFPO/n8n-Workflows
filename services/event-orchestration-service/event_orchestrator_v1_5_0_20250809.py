#!/usr/bin/env python3
"""
Event Orchestration Service - Phase 2
Service-übergreifende Event-Bus Orchestration und Message Routing
"""

import sys
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import uuid

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

# Simplified imports for Phase 2 development
try:
    from shared.common_imports import datetime, BaseModel
    import structlog
except ImportError:
    from datetime import datetime
    from typing import Any
    
    # Mock BaseModel for development
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    # Mock structlog for development
    class MockLogger:
        def info(self, msg, **kwargs): print(f"ℹ️ {msg} {kwargs}")
        def error(self, msg, **kwargs): print(f"❌ {msg} {kwargs}")
        def warning(self, msg, **kwargs): print(f"⚠️ {msg} {kwargs}")
        def debug(self, msg, **kwargs): print(f"🔍 {msg} {kwargs}")
    
    class MockStructlog:
        @staticmethod
        def get_logger(name): return MockLogger()
    
    structlog = MockStructlog()


class EventRoute(BaseModel):
    """Event Route Configuration"""
    source_service: str
    event_type: str
    target_services: List[str]
    transformation_rules: Optional[Dict[str, Any]] = None
    retry_count: int = 3
    timeout_seconds: int = 30
    priority: int = 1  # 1=low, 3=high


class EventOrchestrationMetrics(BaseModel):
    """Event Orchestration Metrics"""
    total_events_processed: int
    events_by_service: Dict[str, int]
    successful_routings: int
    failed_routings: int
    average_processing_time_ms: float
    active_routes: int
    last_updated: datetime


class EventOrchestrator:
    """
    Service-übergreifender Event Orchestrator
    Koordiniert Event-Routing zwischen allen Services
    """
    
    def __init__(self, event_bus=None):
        self.logger = structlog.get_logger(__name__)
        self.event_bus = event_bus
        
        # Event Routing Configuration
        self.event_routes = {}
        self.service_registry = {}
        self.event_history = []
        
        # Performance Metrics
        self.metrics = EventOrchestrationMetrics(
            total_events_processed=0,
            events_by_service={},
            successful_routings=0,
            failed_routings=0,
            average_processing_time_ms=0.0,
            active_routes=0,
            last_updated=datetime.now()
        )
        
        # Event Processors
        self.event_processors = {}
        self.transformation_functions = {}
        
        # Setup default routing rules
        self._setup_default_routing_rules()
        
        self.logger.info("Event Orchestrator initialized")
    
    def _setup_default_routing_rules(self):
        """Setup default cross-service routing rules"""
        
        # Account -> Frontend routing
        self.add_event_route(EventRoute(
            source_service="account_service",
            event_type="account.balance.updated",
            target_services=["frontend_service"],
            transformation_rules={
                "target_event_type": "dashboard.balance.refresh",
                "include_portfolio_summary": True
            }
        ))
        
        # Order -> Account routing
        self.add_event_route(EventRoute(
            source_service="order_service", 
            event_type="order.executed",
            target_services=["account_service"],
            transformation_rules={
                "target_event_type": "account.balance.sync",
                "trigger_portfolio_update": True
            }
        ))
        
        # Market Data -> All Services routing
        self.add_event_route(EventRoute(
            source_service="market_data_service",
            event_type="market.prices.updated",
            target_services=["account_service", "order_service", "frontend_service"],
            priority=3
        ))
        
        # System Health routing to all services
        self.add_event_route(EventRoute(
            source_service="monitoring_service",
            event_type="system.health.request",
            target_services=["account_service", "order_service", "frontend_service"],
            priority=2
        ))
    
    def add_event_route(self, route: EventRoute):
        """Add new event routing rule"""
        route_key = f"{route.source_service}:{route.event_type}"
        self.event_routes[route_key] = route
        self.metrics.active_routes = len(self.event_routes)
        
        self.logger.info("Event route added",
                       source=route.source_service,
                       event_type=route.event_type,
                       targets=route.target_services)
    
    def register_service(self, service_name: str, service_info: Dict[str, Any]):
        """Register a service with the orchestrator"""
        self.service_registry[service_name] = {
            **service_info,
            'registered_at': datetime.now(),
            'last_seen': datetime.now(),
            'status': 'active'
        }
        
        self.logger.info("Service registered",
                       service=service_name,
                       info=service_info)
    
    async def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming event and orchestrate routing"""
        start_time = datetime.now()
        processing_id = str(uuid.uuid4())
        
        try:
            source_service = event.get('source', 'unknown')
            event_type = event.get('event_type', 'unknown')
            
            self.logger.info("Processing event for orchestration",
                           processing_id=processing_id,
                           source=source_service,
                           event_type=event_type)
            
            # Update service last seen
            if source_service in self.service_registry:
                self.service_registry[source_service]['last_seen'] = datetime.now()
            
            # Find matching routes
            route_key = f"{source_service}:{event_type}"
            matching_routes = []
            
            # Exact match
            if route_key in self.event_routes:
                matching_routes.append(self.event_routes[route_key])
            
            # Wildcard matches
            for existing_route_key, route in self.event_routes.items():
                if route.event_type.endswith('*') and event_type.startswith(route.event_type[:-1]):
                    matching_routes.append(route)
            
            if not matching_routes:
                self.logger.debug("No routing rules found",
                                event_type=event_type,
                                source=source_service)
                return {'routed': False, 'reason': 'no_matching_routes'}
            
            # Process each matching route
            routing_results = []
            for route in matching_routes:
                result = await self._execute_event_route(event, route, processing_id)
                routing_results.append(result)
            
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics(source_service, processing_time, routing_results)
            
            # Store in history
            self._store_event_history(event, routing_results, processing_id, processing_time)
            
            # Count successful service targets (not just successful routes)
            successful_service_targets = 0
            for route_result in routing_results:
                if route_result.get('success', False) and 'target_results' in route_result:
                    successful_service_targets += len([
                        tr for tr in route_result['target_results'] 
                        if tr.get('success', False)
                    ])
            
            return {
                'routed': True,
                'processing_id': processing_id,
                'routes_processed': len(routing_results),
                'successful_routes': successful_service_targets,
                'processing_time_ms': processing_time
            }
            
        except Exception as e:
            self.logger.error("Failed to process event orchestration",
                            error=str(e),
                            processing_id=processing_id)
            self.metrics.failed_routings += 1
            return {'routed': False, 'error': str(e), 'processing_id': processing_id}
    
    async def _execute_event_route(self, original_event: Dict[str, Any], 
                                 route: EventRoute, processing_id: str) -> Dict[str, Any]:
        """Execute a single event route"""
        
        try:
            # Transform event if transformation rules exist
            transformed_event = await self._transform_event(original_event, route)
            
            # Route to each target service
            routing_results = []
            for target_service in route.target_services:
                try:
                    result = await self._route_to_service(
                        transformed_event, target_service, route, processing_id
                    )
                    routing_results.append({
                        'target_service': target_service,
                        'success': True,
                        'result': result
                    })
                    
                except Exception as e:
                    self.logger.error("Failed to route to service",
                                    target_service=target_service,
                                    error=str(e),
                                    processing_id=processing_id)
                    routing_results.append({
                        'target_service': target_service,
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'route': f"{route.source_service}:{route.event_type}",
                'target_results': routing_results
            }
            
        except Exception as e:
            self.logger.error("Failed to execute event route",
                            error=str(e),
                            route=f"{route.source_service}:{route.event_type}",
                            processing_id=processing_id)
            return {
                'success': False,
                'error': str(e),
                'route': f"{route.source_service}:{route.event_type}"
            }
    
    async def _transform_event(self, event: Dict[str, Any], route: EventRoute) -> Dict[str, Any]:
        """Transform event according to route transformation rules"""
        
        if not route.transformation_rules:
            return event
        
        transformed_event = event.copy()
        
        # Apply transformation rules
        for rule_key, rule_value in route.transformation_rules.items():
            if rule_key == 'target_event_type':
                transformed_event['event_type'] = rule_value
            elif rule_key == 'add_data':
                if 'data' not in transformed_event:
                    transformed_event['data'] = {}
                transformed_event['data'].update(rule_value)
            elif rule_key.startswith('data.'):
                # Nested data transformation
                data_key = rule_key[5:]  # Remove 'data.' prefix
                if 'data' not in transformed_event:
                    transformed_event['data'] = {}
                transformed_event['data'][data_key] = rule_value
            else:
                # Direct property transformation
                if 'data' not in transformed_event:
                    transformed_event['data'] = {}
                transformed_event['data'][rule_key] = rule_value
        
        # Add orchestration metadata
        transformed_event['orchestration'] = {
            'processing_id': str(uuid.uuid4()),
            'original_event_type': event.get('event_type'),
            'route_applied': f"{route.source_service}:{route.event_type}",
            'transformed_at': datetime.now().isoformat()
        }
        
        return transformed_event
    
    async def _route_to_service(self, event: Dict[str, Any], target_service: str, 
                              route: EventRoute, processing_id: str) -> Dict[str, Any]:
        """Route event to specific target service"""
        
        if not self.event_bus:
            raise Exception("Event bus not available")
        
        # Create service-specific event
        service_event = {
            **event,
            'target_service': target_service,
            'routing_metadata': {
                'processing_id': processing_id,
                'route_priority': route.priority,
                'routed_at': datetime.now().isoformat(),
                'source_route': f"{route.source_service}:{route.event_type}"
            }
        }
        
        # Publish to service-specific stream
        stream_id = f"{target_service}-orchestrated"
        
        await self.event_bus.publish(service_event, stream_id=stream_id)
        
        return {
            'published': True,
            'stream_id': stream_id,
            'timestamp': datetime.now().isoformat()
        }
    
    def _update_metrics(self, source_service: str, processing_time: float, 
                       routing_results: List[Dict[str, Any]]):
        """Update orchestration metrics"""
        
        self.metrics.total_events_processed += 1
        
        # Update per-service metrics
        if source_service not in self.metrics.events_by_service:
            self.metrics.events_by_service[source_service] = 0
        self.metrics.events_by_service[source_service] += 1
        
        # Update success/failure counts
        successful_routes = len([r for r in routing_results if r['success']])
        failed_routes = len([r for r in routing_results if not r['success']])
        
        self.metrics.successful_routings += successful_routes
        self.metrics.failed_routings += failed_routes
        
        # Update average processing time
        total_events = self.metrics.total_events_processed
        current_avg = self.metrics.average_processing_time_ms
        self.metrics.average_processing_time_ms = (
            (current_avg * (total_events - 1) + processing_time) / total_events
        )
        
        self.metrics.last_updated = datetime.now()
    
    def _store_event_history(self, event: Dict[str, Any], routing_results: List[Dict[str, Any]],
                           processing_id: str, processing_time: float):
        """Store event processing history"""
        
        history_entry = {
            'processing_id': processing_id,
            'timestamp': datetime.now().isoformat(),
            'source_service': event.get('source', 'unknown'),
            'event_type': event.get('event_type', 'unknown'),
            'routing_results': routing_results,
            'processing_time_ms': processing_time,
            'success': len([r for r in routing_results if r['success']]) > 0
        }
        
        self.event_history.append(history_entry)
        
        # Limit history to last 1000 events
        if len(self.event_history) > 1000:
            self.event_history.pop(0)
    
    def get_orchestration_metrics(self) -> Dict[str, Any]:
        """Get current orchestration metrics"""
        return {
            'metrics': self.metrics.dict(),
            'active_routes': len(self.event_routes),
            'registered_services': len(self.service_registry),
            'recent_events': len([
                h for h in self.event_history 
                if (datetime.now() - datetime.fromisoformat(h['timestamp'])).seconds < 3600
            ])
        }
    
    def get_service_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all registered services"""
        
        service_health = {}
        current_time = datetime.now()
        
        for service_name, service_info in self.service_registry.items():
            last_seen = service_info['last_seen']
            time_since_seen = (current_time - last_seen).total_seconds()
            
            if time_since_seen < 300:  # 5 minutes
                status = 'healthy'
            elif time_since_seen < 1800:  # 30 minutes
                status = 'warning'
            else:
                status = 'unhealthy'
            
            service_health[service_name] = {
                'status': status,
                'last_seen': last_seen.isoformat(),
                'seconds_since_seen': time_since_seen,
                'events_processed': self.metrics.events_by_service.get(service_name, 0)
            }
        
        return {
            'services': service_health,
            'total_services': len(service_health),
            'healthy_services': len([s for s in service_health.values() if s['status'] == 'healthy']),
            'warning_services': len([s for s in service_health.values() if s['status'] == 'warning']),
            'unhealthy_services': len([s for s in service_health.values() if s['status'] == 'unhealthy'])
        }
    
    async def setup_orchestration_subscriptions(self):
        """Setup Event-Bus subscriptions for orchestration"""
        if not self.event_bus:
            self.logger.warning("Event bus not available for orchestration subscriptions")
            return
        
        try:
            # Subscribe to all events for orchestration
            await self.event_bus.subscribe('*', self.process_event)
            
            # Subscribe to orchestration-specific events
            await self.event_bus.subscribe('orchestration.health.request', self._handle_health_request)
            await self.event_bus.subscribe('orchestration.metrics.request', self._handle_metrics_request)
            
            self.logger.info("Event orchestration subscriptions setup completed")
            
        except Exception as e:
            self.logger.error("Failed to setup orchestration subscriptions", error=str(e))
    
    async def _handle_health_request(self, event):
        """Handle orchestration health requests"""
        try:
            health_summary = self.get_service_health_summary()
            
            response_event = {
                'event_type': 'orchestration.health.response',
                'stream_id': event.get('stream_id', 'orchestration-health'),
                'data': health_summary,
                'source': 'event_orchestrator',
                'correlation_id': event.get('correlation_id')
            }
            
            await self.event_bus.publish(response_event)
            
        except Exception as e:
            self.logger.error("Failed to handle health request", error=str(e))
    
    async def _handle_metrics_request(self, event):
        """Handle orchestration metrics requests"""
        try:
            metrics = self.get_orchestration_metrics()
            
            response_event = {
                'event_type': 'orchestration.metrics.response',
                'stream_id': event.get('stream_id', 'orchestration-metrics'),
                'data': metrics,
                'source': 'event_orchestrator',
                'correlation_id': event.get('correlation_id')
            }
            
            await self.event_bus.publish(response_event)
            
        except Exception as e:
            self.logger.error("Failed to handle metrics request", error=str(e))


async def main():
    """Main orchestration service"""
    print("🎭 Event Orchestration Service - Phase 2")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = EventOrchestrator()
    
    # Setup subscriptions
    await orchestrator.setup_orchestration_subscriptions()
    
    print("✅ Event Orchestration Service initialized")
    print(f"📊 Active Routes: {orchestrator.metrics.active_routes}")
    print(f"🏥 Registered Services: {len(orchestrator.service_registry)}")
    
    # Keep service running
    try:
        while True:
            await asyncio.sleep(10)
            
            # Log metrics every 60 seconds
            if orchestrator.metrics.total_events_processed % 6 == 0:
                metrics = orchestrator.get_orchestration_metrics()
                print(f"📈 Events Processed: {metrics['metrics']['total_events_processed']}")
                print(f"✅ Success Rate: {metrics['metrics']['successful_routings']}/{metrics['metrics']['successful_routings'] + metrics['metrics']['failed_routings']}")
    
    except KeyboardInterrupt:
        print("\n🛑 Event Orchestration Service shutting down...")


if __name__ == "__main__":
    asyncio.run(main())