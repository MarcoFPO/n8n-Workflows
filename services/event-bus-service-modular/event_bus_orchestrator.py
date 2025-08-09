"""
Event-Bus Service Modular - Zentraler Event-Hub für aktienanalyse-ökosystem
Orchestrator für Event-Routing, Pub/Sub und Event-Store Management
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

import redis.asyncio as aioredis
import aio_pika
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import structlog

# Add shared module path
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')

from backend_base_module import BackendBaseModule
from event_bus import EventBusConnector, EventType, Event

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("event-bus-modular")

# Pydantic Models für API
class EventMessage(BaseModel):
    event_type: str
    stream_id: Optional[str] = None
    data: Dict[str, Any]
    source: str
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class EventRouteConfig(BaseModel):
    source_pattern: str
    target_services: List[str]
    event_types: List[str]
    enabled: bool = True

class EventStoreQuery(BaseModel):
    event_types: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: int = 100


class EventRouterModule(BackendBaseModule):
    """Event-Routing-Modul für intelligente Event-Verteilung"""
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("event-router", event_bus)
        self.routing_rules: Dict[str, EventRouteConfig] = {}
        self.active_subscriptions: Dict[str, List[str]] = {}
        
    async def initialize(self) -> bool:
        """Initialisiere Event-Router"""
        try:
            # Standard-Routing-Regeln laden
            await self._load_default_routing_rules()
            
            # Alle Event-Types abonnieren für Routing
            for event_type in EventType:
                await self.event_bus.subscribe(
                    event_type.value,
                    self._route_event,
                    f"router-{event_type.value}"
                )
            
            logger.info("Event-Router initialized", 
                       module=self.module_name,
                       routing_rules=len(self.routing_rules))
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Event-Router", 
                        module=self.module_name, error=str(e))
            return False
    
    async def _load_default_routing_rules(self):
        """Lade Standard-Routing-Regeln"""
        default_rules = {
            "analysis_broadcast": EventRouteConfig(
                source_pattern="intelligent-core-*",
                target_services=["frontend", "diagnostic", "monitoring"],
                event_types=["analysis.state.changed"]
            ),
            "trading_broadcast": EventRouteConfig(
                source_pattern="broker-gateway-*",
                target_services=["frontend", "intelligent-core", "diagnostic"],
                event_types=["trading.state.changed"]
            ),
            "system_alerts": EventRouteConfig(
                source_pattern="*",
                target_services=["frontend", "monitoring", "diagnostic"],
                event_types=["system.alert.raised"]
            ),
            "data_sync": EventRouteConfig(
                source_pattern="*",
                target_services=["*"],
                event_types=["data.synchronized"]
            )
        }
        
        for rule_name, config in default_rules.items():
            self.routing_rules[rule_name] = config
    
    async def _route_event(self, event_data: Dict[str, Any]):
        """Route Event basierend auf Regeln"""
        try:
            event_type = event_data.get('event_type')
            source = event_data.get('source', '')
            
            # Passende Routing-Regeln finden
            applicable_rules = []
            for rule_name, rule in self.routing_rules.items():
                if not rule.enabled:
                    continue
                    
                # Event-Type prüfen
                if event_type not in rule.event_types:
                    continue
                    
                # Source-Pattern prüfen (Wildcard-Support)
                if rule.source_pattern != "*" and not self._matches_pattern(source, rule.source_pattern):
                    continue
                    
                applicable_rules.append(rule)
            
            # Event zu Target-Services routen
            for rule in applicable_rules:
                for target_service in rule.target_services:
                    if target_service != "*":
                        await self._forward_to_service(event_data, target_service)
                        
            logger.debug("Event routed", 
                        event_type=event_type,
                        source=source,
                        rules_applied=len(applicable_rules))
                        
        except Exception as e:
            logger.error("Event routing failed", error=str(e))
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Simple Wildcard-Pattern-Matching"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return text.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return text.endswith(pattern[1:])
        return text == pattern
    
    async def _forward_to_service(self, event_data: Dict[str, Any], target_service: str):
        """Forward Event zu spezifischem Service"""
        try:
            # Event mit Target-Service-Info erweitern
            forwarded_event = event_data.copy()
            forwarded_event['routed_to'] = target_service
            forwarded_event['routed_by'] = self.module_name
            
            # Event republish für Target-Service
            await self.event_bus.publish(Event(
                event_type=EventType(event_data['event_type']),
                stream_id=f"routed-{target_service}",
                data=forwarded_event,
                source=self.module_name,
                correlation_id=str(uuid4())
            ))
            
        except Exception as e:
            logger.error("Event forwarding failed", 
                        target=target_service, error=str(e))

    async def process_business_logic(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Event-Router business logic"""
        command = input_data.get('command', '')
        
        if command == 'get_routing_rules':
            return {
                'routing_rules': {name: {
                    'source_pattern': rule.source_pattern,
                    'target_services': rule.target_services,
                    'event_types': rule.event_types,
                    'enabled': rule.enabled
                } for name, rule in self.routing_rules.items()}
            }
        elif command == 'add_routing_rule':
            rule_name = input_data.get('rule_name')
            rule_config = input_data.get('rule_config')
            if rule_name and rule_config:
                self.routing_rules[rule_name] = EventRouteConfig(**rule_config)
                return {'status': 'success', 'message': f'Rule {rule_name} added'}
        elif command == 'get_statistics':
            return {
                'active_rules': len([r for r in self.routing_rules.values() if r.enabled]),
                'total_rules': len(self.routing_rules),
                'subscriptions': len(self.active_subscriptions)
            }
        
        return {'error': 'Unknown command'}


class EventStoreModule(BackendBaseModule):
    """Event-Store-Modul für Event-Persistierung"""
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("event-store", event_bus)
        self.redis_client = None
        self.stored_events_count = 0
        
    async def initialize(self) -> bool:
        """Initialisiere Event-Store"""
        try:
            # Redis-Verbindung für Event-Store
            self.redis_client = aioredis.from_url(
                "redis://localhost:6379/1",  # Separate DB für Event-Store
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            
            # Alle Event-Types für Persistierung abonnieren
            for event_type in EventType:
                await self.event_bus.subscribe(
                    event_type.value,
                    self._store_event,
                    f"store-{event_type.value}"
                )
            
            logger.info("Event-Store initialized", 
                       module=self.module_name)
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Event-Store", 
                        module=self.module_name, error=str(e))
            return False
    
    async def _store_event(self, event_data: Dict[str, Any]):
        """Store Event in Redis"""
        try:
            if not self.redis_client:
                return
                
            event_id = str(uuid4())
            event_key = f"event:{event_id}"
            
            # Event-Daten mit Metadaten erweitern
            stored_event = {
                'id': event_id,
                'stored_at': datetime.utcnow().isoformat(),
                'stored_by': self.module_name,
                **event_data
            }
            
            # Als JSON in Redis speichern
            await self.redis_client.hset(event_key, mapping={
                'data': json.dumps(stored_event),
                'event_type': event_data.get('event_type', ''),
                'source': event_data.get('source', ''),
                'timestamp': event_data.get('timestamp', ''),
                'stream_id': event_data.get('stream_id', '')
            })
            
            # Event-Type-Index aktualisieren
            event_type = event_data.get('event_type', '')
            await self.redis_client.sadd(f"events_by_type:{event_type}", event_id)
            
            # Source-Index aktualisieren
            source = event_data.get('source', '')
            await self.redis_client.sadd(f"events_by_source:{source}", event_id)
            
            # TTL setzen (30 Tage)
            await self.redis_client.expire(event_key, 30 * 24 * 3600)
            
            self.stored_events_count += 1
            
            logger.debug("Event stored", 
                        event_id=event_id,
                        event_type=event_type,
                        source=source)
                        
        except Exception as e:
            logger.error("Event storage failed", error=str(e))
    
    async def query_events(self, query: EventStoreQuery) -> List[Dict[str, Any]]:
        """Query Events aus Store"""
        try:
            if not self.redis_client:
                return []
                
            event_ids = set()
            
            # Filter nach Event-Types
            if query.event_types:
                for event_type in query.event_types:
                    type_events = await self.redis_client.smembers(f"events_by_type:{event_type}")
                    event_ids.update(type_events)
            
            # Filter nach Sources
            if query.sources:
                source_events = set()
                for source in query.sources:
                    src_events = await self.redis_client.smembers(f"events_by_source:{source}")
                    source_events.update(src_events)
                
                if event_ids:
                    event_ids = event_ids.intersection(source_events)
                else:
                    event_ids = source_events
            
            # Wenn keine Filter, alle Events holen (begrenzt)
            if not event_ids:
                cursor = 0
                count = 0
                while cursor != 0 or count == 0:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor, 
                        match="event:*", 
                        count=query.limit
                    )
                    event_ids.update([key.replace('event:', '') for key in keys])
                    count += 1
                    if len(event_ids) >= query.limit:
                        break
            
            # Events laden
            events = []
            for event_id in list(event_ids)[:query.limit]:
                event_data = await self.redis_client.hget(f"event:{event_id}", "data")
                if event_data:
                    events.append(json.loads(event_data))
            
            # Nach Timestamp sortieren
            events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return events
            
        except Exception as e:
            logger.error("Event query failed", error=str(e))
            return []

    async def process_business_logic(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Event-Store business logic"""
        command = input_data.get('command', '')
        
        if command == 'query_events':
            query_params = input_data.get('query', {})
            query = EventStoreQuery(**query_params)
            events = await self.query_events(query)
            return {'events': events, 'count': len(events)}
        elif command == 'get_statistics':
            return {
                'stored_events': self.stored_events_count,
                'redis_connected': self.redis_client is not None
            }
        
        return {'error': 'Unknown command'}


class EventBusOrchestrator:
    """Hauptorchestrator für Event-Bus Service"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Event-Bus Service Modular",
            description="Zentraler Event-Hub für aktienanalyse-ökosystem",
            version="1.0.0"
        )
        
        # CORS aktivieren
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Event-Bus und Module
        self.event_bus = EventBusConnector("event-bus-modular")
        self.modules = {}
        
        # Module initialisieren
        self.event_router = EventRouterModule(self.event_bus)
        self.event_store = EventStoreModule(self.event_bus)
        
        # API-Routen registrieren
        self._register_routes()
        
        # Startup/Shutdown Events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
    
    def _register_routes(self):
        """Registriere API-Routen"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "event-bus-modular",
                "version": "1.0.0",
                "status": "running",
                "modules": ["event-router", "event-store"],
                "port": 8014
            }
        
        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": "event-bus-modular",
                "event_bus_connected": self.event_bus.connected,
                "modules": {
                    "event_router": self.event_router.is_initialized,
                    "event_store": self.event_store.is_initialized
                }
            }
        
        @self.app.post("/events/publish")
        async def publish_event(event: EventMessage):
            """Event manuell publizieren"""
            try:
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
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/events/query")
        async def query_events(
            event_types: Optional[str] = None,
            sources: Optional[str] = None,
            limit: int = 100
        ):
            """Events aus Store abfragen"""
            try:
                query = EventStoreQuery(
                    event_types=event_types.split(',') if event_types else None,
                    sources=sources.split(',') if sources else None,
                    limit=limit
                )
                
                result = await self.event_store.process_business_logic({
                    'command': 'query_events',
                    'query': query.dict()
                })
                
                return result
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/routing/rules")
        async def get_routing_rules():
            """Routing-Regeln abrufen"""
            result = await self.event_router.process_business_logic({
                'command': 'get_routing_rules'
            })
            return result
        
        @self.app.post("/routing/rules")
        async def add_routing_rule(rule_name: str, rule: EventRouteConfig):
            """Routing-Regel hinzufügen"""
            result = await self.event_router.process_business_logic({
                'command': 'add_routing_rule',
                'rule_name': rule_name,
                'rule_config': rule.dict()
            })
            return result
        
        @self.app.get("/statistics")
        async def get_statistics():
            """Service-Statistiken"""
            router_stats = await self.event_router.process_business_logic({
                'command': 'get_statistics'
            })
            store_stats = await self.event_store.process_business_logic({
                'command': 'get_statistics'
            })
            
            return {
                "service": "event-bus-modular",
                "event_bus": {
                    "connected": self.event_bus.connected,
                    "service_name": self.event_bus.service_name
                },
                "router": router_stats,
                "store": store_stats,
                "uptime": "running"
            }
    
    async def startup_event(self):
        """Service startup"""
        try:
            logger.info("Starting Event-Bus Service Modular...")
            
            # Event-Bus verbinden
            if not await self.event_bus.connect():
                raise RuntimeError("Failed to connect to event bus")
            
            # Module registrieren
            self.modules["event-router"] = self.event_router
            self.modules["event-store"] = self.event_store
            
            # Module initialisieren
            for module_name, module in self.modules.items():
                logger.info(f"Initializing module: {module_name}")
                await module.initialize()
            
            logger.info("Event-Bus Service Modular started successfully",
                       modules=len(self.modules),
                       event_bus_connected=self.event_bus.connected)
            
        except Exception as e:
            logger.error("Failed to start Event-Bus Service", error=str(e))
            raise RuntimeError("Service initialization failed")
    
    async def shutdown_event(self):
        """Service shutdown"""
        try:
            logger.info("Shutting down Event-Bus Service Modular...")
            
            # Module herunterfahren
            for module_name, module in self.modules.items():
                logger.info(f"Shutting down module: {module_name}")
                await module.shutdown()
            
            # Event-Bus trennen
            await self.event_bus.disconnect()
            
            logger.info("Event-Bus Service Modular shut down successfully")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


def main():
    """Main entry point"""
    orchestrator = EventBusOrchestrator()
    
    # Uvicorn-Server konfiguration
    config = uvicorn.Config(
        app=orchestrator.app,
        host="0.0.0.0",
        port=8014,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    
    logger.info("Event-Bus Service Modular starting on port 8014...")
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Event-Bus Service stopped by user")
    except Exception as e:
        logger.error("Event-Bus Service crashed", error=str(e))
        raise


if __name__ == "__main__":
    main()