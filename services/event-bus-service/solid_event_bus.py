#!/usr/bin/env python3
"""
SOLID-konformer Event-Bus Service
Issue #62 - SOLID-Prinzipien durchsetzen

SRP-Refactoring des EventBusOrchestrators:
- APIRouter: Nur API-Routing
- ServiceManager: Nur Service-Lifecycle
- HealthMonitor: Nur Health-Checks
- EventBusController: Business-Logik

Author: System Modernization Team
Version: 1.0.0
Date: 2025-08-29
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# SOLID Foundation
from ...shared.solid_foundations import (
    SOLIDServiceOrchestrator,
    ServiceContainer,
    Startable,
    Stoppable,
    Healthable,
    Configurable,
    Routable,
    APIRouter,
    ServiceManager,
    HealthMonitor
)

# Exception Framework
from ...shared.exceptions import (
    BaseServiceException,
    EventBusException,
    ValidationException,
    get_error_response
)
from ...shared.exception_handler import (
    ExceptionHandler,
    handle_exceptions
)

# Event-Bus Components
from .event_bus_connector import EventBusConnector
from .modules.event_router_module import EventRouterModule
from .modules.event_store_module import EventStoreModule
from .schemas import EventMessage, EventStoreQuery, EventRouteConfig
from .models import Event, EventType

# Logger
logger = logging.getLogger(__name__)


# =============================================================================
# SRP: SEPARATE COMPONENTS
# =============================================================================

class EventBusAPIController(Routable):
    """SRP: Nur verantwortlich für API-Endpoints Definition"""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.logger = logging.getLogger("event-bus.api-controller")
    
    def register_routes(self) -> Dict[str, Any]:
        """API-Routes definieren"""
        return {
            'GET:/': self.root_endpoint,
            'GET:/health': self.health_endpoint,
            'POST:/events/publish': self.publish_event,
            'GET:/events/query': self.query_events,
            'GET:/routing/rules': self.get_routing_rules,
            'POST:/routing/rules': self.add_routing_rule,
            'GET:/statistics': self.get_statistics
        }
    
    async def root_endpoint(self) -> Dict[str, Any]:
        """Root endpoint"""
        return {
            "service": "event-bus-solid",
            "version": "1.0.0",
            "status": "running",
            "modules": ["event-router", "event-store"],
            "port": 8014,
            "architecture": "SOLID-compliant"
        }
    
    async def health_endpoint(self) -> Dict[str, Any]:
        """Health endpoint - delegiert an HealthMonitor"""
        health_monitor = self.container.resolve(HealthMonitor)
        return await health_monitor.check_all()
    
    @handle_exceptions
    async def publish_event(self, event: EventMessage) -> Dict[str, Any]:
        """Event publizieren"""
        try:
            event_bus_service = self.container.resolve_optional(EventBusService)
            if not event_bus_service:
                raise EventBusException("EventBusService not available")
            
            result = await event_bus_service.publish_event(event)
            return result
            
        except Exception as e:
            self.logger.error(f"Error publishing event: {e}")
            raise EventBusException(
                "Failed to publish event",
                original_exception=e,
                context={'event_type': event.event_type}
            )
    
    @handle_exceptions
    async def query_events(
        self, 
        event_types: Optional[str] = None,
        sources: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Events abfragen"""
        try:
            event_bus_service = self.container.resolve_optional(EventBusService)
            if not event_bus_service:
                raise EventBusException("EventBusService not available")
            
            query = EventStoreQuery(
                event_types=event_types.split(',') if event_types else None,
                sources=sources.split(',') if sources else None,
                limit=limit
            )
            
            result = await event_bus_service.query_events(query)
            return result
            
        except Exception as e:
            self.logger.error(f"Error querying events: {e}")
            raise EventBusException(
                "Failed to query events",
                original_exception=e,
                context={'query_params': {'event_types': event_types, 'sources': sources, 'limit': limit}}
            )
    
    @handle_exceptions
    async def get_routing_rules(self) -> Dict[str, Any]:
        """Routing-Regeln abrufen"""
        try:
            event_bus_service = self.container.resolve_optional(EventBusService)
            if not event_bus_service:
                raise EventBusException("EventBusService not available")
            
            return await event_bus_service.get_routing_rules()
            
        except Exception as e:
            self.logger.error(f"Error getting routing rules: {e}")
            raise EventBusException(
                "Failed to get routing rules",
                original_exception=e
            )
    
    @handle_exceptions
    async def add_routing_rule(self, rule_name: str, rule: EventRouteConfig) -> Dict[str, Any]:
        """Routing-Regel hinzufügen"""
        try:
            event_bus_service = self.container.resolve_optional(EventBusService)
            if not event_bus_service:
                raise EventBusException("EventBusService not available")
            
            return await event_bus_service.add_routing_rule(rule_name, rule)
            
        except Exception as e:
            self.logger.error(f"Error adding routing rule: {e}")
            raise EventBusException(
                "Failed to add routing rule",
                original_exception=e,
                context={'rule_name': rule_name}
            )
    
    @handle_exceptions
    async def get_statistics(self) -> Dict[str, Any]:
        """Service-Statistiken abrufen"""
        try:
            event_bus_service = self.container.resolve_optional(EventBusService)
            if not event_bus_service:
                raise EventBusException("EventBusService not available")
            
            return await event_bus_service.get_statistics()
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            raise EventBusException(
                "Failed to get statistics",
                original_exception=e
            )


class EventBusService(Startable, Stoppable, Healthable):
    """SRP: Nur verantwortlich für Event-Bus Business-Logik"""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.logger = logging.getLogger("event-bus.service")
        
        # Event-Bus Components
        self.event_bus: Optional[EventBusConnector] = None
        self.event_router: Optional[EventRouterModule] = None
        self.event_store: Optional[EventStoreModule] = None
        
        # State
        self.is_started = False
        self.startup_timestamp: Optional[datetime] = None
    
    async def startup(self) -> bool:
        """Service starten"""
        try:
            self.logger.info("Starting Event-Bus Service...")
            
            # Event-Bus initialisieren
            self.event_bus = EventBusConnector("event-bus-solid")
            if not await self.event_bus.connect():
                raise EventBusException("Failed to connect to event bus")
            
            # Module initialisieren
            self.event_router = EventRouterModule(self.event_bus)
            self.event_store = EventStoreModule(self.event_bus)
            
            await self.event_router.initialize()
            await self.event_store.initialize()
            
            # Container Services registrieren
            self.container.register_singleton(EventBusConnector, self.event_bus)
            self.container.register_singleton(EventRouterModule, self.event_router)
            self.container.register_singleton(EventStoreModule, self.event_store)
            
            self.is_started = True
            self.startup_timestamp = datetime.utcnow()
            
            self.logger.info("Event-Bus Service started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Event-Bus Service: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Service stoppen"""
        try:
            self.logger.info("Stopping Event-Bus Service...")
            
            # Module herunterfahren
            if self.event_router:
                await self.event_router.shutdown()
            if self.event_store:
                await self.event_store.shutdown()
            
            # Event-Bus trennen
            if self.event_bus:
                await self.event_bus.disconnect()
            
            self.is_started = False
            self.logger.info("Event-Bus Service stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping Event-Bus Service: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Health-Status prüfen"""
        health_status = {
            'service': 'event-bus-service',
            'status': 'healthy' if self.is_started else 'unhealthy',
            'started': self.is_started,
            'startup_timestamp': self.startup_timestamp.isoformat() if self.startup_timestamp else None,
            'components': {}
        }
        
        # Event-Bus Status
        if self.event_bus:
            health_status['components']['event_bus'] = {
                'connected': self.event_bus.connected,
                'service_name': self.event_bus.service_name
            }
        
        # Module Status
        if self.event_router:
            health_status['components']['event_router'] = {
                'initialized': self.event_router.is_initialized
            }
        
        if self.event_store:
            health_status['components']['event_store'] = {
                'initialized': self.event_store.is_initialized
            }
        
        return health_status
    
    async def publish_event(self, event: EventMessage) -> Dict[str, Any]:
        """Event publizieren"""
        if not self.is_started or not self.event_bus:
            raise EventBusException("Service not started")
        
        published_event = Event(
            event_type=EventType(event.event_type),
            stream_id=event.stream_id or f"manual-{uuid4()}",
            data=event.data,
            source=event.source,
            correlation_id=event.correlation_id or str(uuid4()),
            metadata=event.metadata or {}
        )
        
        await self.event_bus.publish(published_event)
        
        return {
            "status": "published",
            "event_id": published_event.stream_id,
            "event_type": event.event_type
        }
    
    async def query_events(self, query: EventStoreQuery) -> Dict[str, Any]:
        """Events abfragen"""
        if not self.is_started or not self.event_store:
            raise EventBusException("Service not started")
        
        result = await self.event_store.process_business_logic({
            'command': 'query_events',
            'query': query.dict()
        })
        
        return result
    
    async def get_routing_rules(self) -> Dict[str, Any]:
        """Routing-Regeln abrufen"""
        if not self.is_started or not self.event_router:
            raise EventBusException("Service not started")
        
        result = await self.event_router.process_business_logic({
            'command': 'get_routing_rules'
        })
        
        return result
    
    async def add_routing_rule(self, rule_name: str, rule: EventRouteConfig) -> Dict[str, Any]:
        """Routing-Regel hinzufügen"""
        if not self.is_started or not self.event_router:
            raise EventBusException("Service not started")
        
        result = await self.event_router.process_business_logic({
            'command': 'add_routing_rule',
            'rule_name': rule_name,
            'rule_config': rule.dict()
        })
        
        return result
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Service-Statistiken abrufen"""
        if not self.is_started or not self.event_router or not self.event_store:
            raise EventBusException("Service not started")
        
        router_stats = await self.event_router.process_business_logic({
            'command': 'get_statistics'
        })
        store_stats = await self.event_store.process_business_logic({
            'command': 'get_statistics'
        })
        
        return {
            "service": "event-bus-solid",
            "architecture": "SOLID-compliant",
            "event_bus": {
                "connected": self.event_bus.connected,
                "service_name": self.event_bus.service_name
            },
            "router": router_stats,
            "store": store_stats,
            "uptime": (datetime.utcnow() - self.startup_timestamp).total_seconds() if self.startup_timestamp else 0
        }


class FastAPIAdapter(Configurable):
    """SRP: Nur verantwortlich für FastAPI-Integration"""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.app: Optional[FastAPI] = None
        self.logger = logging.getLogger("event-bus.fastapi-adapter")
        self.config = {
            'title': 'Event-Bus Service SOLID',
            'description': 'SOLID-konforme Event-Bus Implementation',
            'version': '1.0.0',
            'host': '0.0.0.0',
            'port': 8014
        }
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """FastAPI konfigurieren"""
        try:
            self.config.update(config)
            
            # FastAPI App erstellen
            self.app = FastAPI(
                title=self.config['title'],
                description=self.config['description'],
                version=self.config['version']
            )
            
            # CORS Middleware
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"]
            )
            
            # Exception Handler registrieren
            exception_handler = self.container.resolve_optional(ExceptionHandler)
            if exception_handler:
                @self.app.exception_handler(BaseServiceException)
                async def service_exception_handler(request: Request, exc: BaseServiceException):
                    return JSONResponse(
                        status_code=exc.status_code,
                        content=get_error_response(exc)
                    )
            
            # Routes registrieren
            self._register_routes()
            
            self.logger.info(f"FastAPI configured: {self.config['title']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure FastAPI: {e}")
            return False
    
    def _register_routes(self):
        """Routes aus API Controller registrieren"""
        api_controller = self.container.resolve_optional(EventBusAPIController)
        if not api_controller:
            self.logger.warning("No API Controller found")
            return
        
        routes = api_controller.register_routes()
        
        for route_key, handler in routes.items():
            method, path = route_key.split(':', 1)
            
            if method == 'GET':
                self.app.get(path)(handler)
            elif method == 'POST':
                self.app.post(path)(handler)
            elif method == 'PUT':
                self.app.put(path)(handler)
            elif method == 'DELETE':
                self.app.delete(path)(handler)
            
            self.logger.debug(f"Route registered: {method} {path}")
    
    def get_app(self) -> FastAPI:
        """FastAPI App abrufen"""
        if not self.app:
            raise EventBusException("FastAPI not configured")
        return self.app


# =============================================================================
# SOLID EVENT-BUS ORCHESTRATOR
# =============================================================================

class SOLIDEventBusOrchestrator:
    """
    SOLID-konformer Event-Bus Orchestrator
    
    Implementiert alle SOLID-Prinzipien:
    - SRP: Getrennte Verantwortlichkeiten (API, Service, Health, etc.)
    - OCP: Erweiterbar durch Container-Registrierung
    - LSP: Konsistente Interface-Implementation
    - ISP: Spezifische Interfaces (Startable, Healthable, etc.)
    - DIP: Dependency Injection über Container
    """
    
    def __init__(self):
        self.logger = logging.getLogger("event-bus.solid-orchestrator")
        
        # SOLID Foundation
        self.solid_orchestrator = SOLIDServiceOrchestrator("event-bus-solid")
        self.container = self.solid_orchestrator.get_container()
        
        # Services registrieren
        self._register_services()
        
        # FastAPI App
        self.fastapi_adapter = FastAPIAdapter(self.container)
        self.app: Optional[FastAPI] = None
    
    def _register_services(self):
        """Alle Services im Container registrieren"""
        
        # Exception Handler
        exception_handler = ExceptionHandler()
        self.container.register_singleton(ExceptionHandler, exception_handler)
        
        # Event-Bus Service
        event_bus_service = EventBusService(self.container)
        self.container.register_singleton(EventBusService, event_bus_service)
        
        # API Controller
        api_controller = EventBusAPIController(self.container)
        self.container.register_singleton(EventBusAPIController, api_controller)
        
        # FastAPI Adapter
        self.container.register_singleton(FastAPIAdapter, self.fastapi_adapter)
        
        # Services im Service Manager registrieren
        service_manager = self.solid_orchestrator.get_service_manager()
        service_manager.register_service("event-bus", event_bus_service, priority=1)
        
        # Health Checks registrieren
        health_monitor = self.solid_orchestrator.get_health_monitor()
        health_monitor.register_health_check("event-bus", event_bus_service.health_check)
        
        self.logger.info("All services registered in container")
    
    async def initialize(self) -> bool:
        """Orchestrator initialisieren"""
        try:
            self.logger.info("Initializing SOLID Event-Bus Orchestrator...")
            
            # SOLID Orchestrator initialisieren
            if not await self.solid_orchestrator.initialize():
                return False
            
            # FastAPI konfigurieren
            if not self.fastapi_adapter.configure({}):
                return False
            
            self.app = self.fastapi_adapter.get_app()
            
            self.logger.info("SOLID Event-Bus Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    async def start(self) -> bool:
        """Orchestrator starten"""
        if not self.app:
            if not await self.initialize():
                return False
        
        return await self.solid_orchestrator.start()
    
    async def stop(self) -> bool:
        """Orchestrator stoppen"""
        return await self.solid_orchestrator.stop()
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive Health Check"""
        return await self.solid_orchestrator.health_check()
    
    def get_app(self) -> FastAPI:
        """FastAPI App für Uvicorn abrufen"""
        if not self.app:
            raise EventBusException("Orchestrator not initialized")
        return self.app


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def create_solid_event_bus() -> SOLIDEventBusOrchestrator:
    """Factory-Function für SOLID Event-Bus"""
    return SOLIDEventBusOrchestrator()


async def main():
    """Main entry point"""
    orchestrator = create_solid_event_bus()
    
    # Initialisieren
    if not await orchestrator.initialize():
        logger.error("Failed to initialize Event-Bus Orchestrator")
        return
    
    # Starten
    if not await orchestrator.start():
        logger.error("Failed to start Event-Bus Service")
        return
    
    # Uvicorn Server
    config = uvicorn.Config(
        app=orchestrator.get_app(),
        host="0.0.0.0",
        port=8014,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    logger.info("SOLID Event-Bus Service starting on port 8014...")
    
    try:
        await server.serve()
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())