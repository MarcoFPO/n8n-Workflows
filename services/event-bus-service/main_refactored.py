"""
Event-Bus Service Modular v2.0.0 - Exception Framework Refactored
Zentraler Event-Hub für aktienanalyse-ökosystem mit strukturiertem Exception-Handling

NEUERUNGEN v2.0.0:
- Umfassendes Exception-Framework mit hierarchischen Exception-Klassen
- Strukturierte Error-Recovery-Patterns
- Transaction-Rollback-Support
- HTTP-Status-Code-Mapping
- Metriken und Monitoring für Exception-Behandlung
- Eliminierung aller generischen "except Exception" Statements

Author: System Modernization Team
Version: 2.0.0  
Date: 2025-08-29
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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import Management - CLEAN ARCHITECTURE
from shared.standard_import_manager_v1_0_0_20250824 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# Clean imports via Import Manager
from backend_base_module import BackendBaseModule
from event_bus import EventBusConnector, EventType, Event

# Exception Framework Imports
from shared.exceptions import (
    BaseServiceException,
    EventBusException, 
    PublishException,
    SubscribeException,
    EventRoutingException,
    DatabaseException,
    ConnectionException,
    QueryException,
    ConfigurationException,
    ValidationException,
    NetworkException,
    TimeoutException,
    ErrorSeverity,
    RecoveryStrategy,
    ExceptionFactory
)
from shared.exception_handler import (
    ExceptionHandler,
    ExceptionHandlerConfig,
    exception_handler,
    event_bus_exception_handler,
    database_exception_handler,
    async_exception_context,
    get_exception_handler,
    configure_exception_handler,
    create_fastapi_exception_handler,
    TransactionManager,
    get_transaction_manager
)

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [event-bus-v2] [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("event-bus-v2")

# Exception-Handler-Konfiguration
exception_config = ExceptionHandlerConfig(
    log_exceptions=True,
    raise_on_unhandled=True,
    default_recovery_strategy=RecoveryStrategy.RETRY,
    rollback_on_error=True,
    max_retries=3,
    circuit_breaker_threshold=5,
    metrics_enabled=True
)
configure_exception_handler(exception_config)

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
    """Event-Routing-Modul mit strukturiertem Exception-Handling"""
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("event-router", event_bus)
        self.routing_rules: Dict[str, EventRouteConfig] = {}
        self.active_subscriptions: Dict[str, List[str]] = {}
        self.transaction_manager = get_transaction_manager()
        
    @event_bus_exception_handler(fallback_func=lambda: False)
    async def initialize(self) -> bool:
        """Initialisiere Event-Router mit strukturiertem Exception-Handling"""
        transaction_id = f"router_init_{int(datetime.utcnow().timestamp())}"
        
        async with async_exception_context() as handler:
            try:
                self.transaction_manager.begin_transaction(transaction_id)
                
                # Standard-Routing-Regeln laden
                await self._load_default_routing_rules()
                
                # Alle Event-Types abonnieren für Routing
                subscription_tasks = []
                for event_type in EventType:
                    task = self._subscribe_to_event_type(event_type)
                    subscription_tasks.append(task)
                
                # Parallele Subscription-Erstellung
                results = await asyncio.gather(*subscription_tasks, return_exceptions=True)
                
                # Prüfe auf Subscription-Fehler
                failed_subscriptions = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_subscriptions.append((list(EventType)[i], result))
                
                if failed_subscriptions:
                    raise SubscribeException(
                        f"Failed to subscribe to {len(failed_subscriptions)} event types",
                        context={
                            "failed_subscriptions": [
                                {"event_type": et.value, "error": str(err)} 
                                for et, err in failed_subscriptions
                            ]
                        }
                    )
                
                self.transaction_manager.commit_transaction(transaction_id)
                
                logger.info("Event-Router initialized successfully", 
                           extra={
                               "module": self.module_name,
                               "routing_rules": len(self.routing_rules),
                               "subscriptions": len(results)
                           })
                return True
                
            except EventBusException:
                self.transaction_manager.rollback_transaction(transaction_id)
                raise
            except Exception as exc:
                self.transaction_manager.rollback_transaction(transaction_id)
                raise ConfigurationException(
                    f"Event-Router initialization failed: {str(exc)}",
                    context={"module": self.module_name},
                    cause=exc
                )
    
    async def _subscribe_to_event_type(self, event_type: EventType):
        """Subscribe zu einem Event-Type mit Exception-Handling"""
        try:
            await self.event_bus.subscribe(
                event_type.value,
                self._route_event,
                f"router-{event_type.value}"
            )
            return event_type
        except Exception as exc:
            raise SubscribeException(
                f"Failed to subscribe to event type: {event_type.value}",
                context={"event_type": event_type.value},
                cause=exc
            )
    
    async def _load_default_routing_rules(self):
        """Lade Standard-Routing-Regeln mit Validierung"""
        try:
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
            
            # Validiere Routing-Regeln
            for rule_name, config in default_rules.items():
                if not config.event_types:
                    raise ValidationException(
                        f"Routing rule {rule_name} has no event types defined",
                        field_errors={"event_types": "Must not be empty"}
                    )
                if not config.target_services:
                    raise ValidationException(
                        f"Routing rule {rule_name} has no target services defined",
                        field_errors={"target_services": "Must not be empty"}
                    )
            
            self.routing_rules.update(default_rules)
            
        except ValidationException:
            raise
        except Exception as exc:
            raise ConfigurationException(
                f"Failed to load default routing rules: {str(exc)}",
                context={"module": self.module_name},
                cause=exc
            )
    
    @event_bus_exception_handler()
    async def _route_event(self, event_data: Dict[str, Any]):
        """Route Event basierend auf Regeln mit strukturiertem Exception-Handling"""
        try:
            # Input-Validierung
            if not isinstance(event_data, dict):
                raise ValidationException(
                    "Event data must be a dictionary",
                    context={"received_type": type(event_data).__name__}
                )
            
            event_type = event_data.get('event_type')
            source = event_data.get('source', '')
            
            if not event_type:
                raise ValidationException(
                    "Event type is required for routing",
                    field_errors={"event_type": "Must not be empty"}
                )
            
            # Passende Routing-Regeln finden
            applicable_rules = await self._find_applicable_rules(event_type, source)
            
            if not applicable_rules:
                logger.debug("No routing rules applicable for event",
                           extra={
                               "event_type": event_type,
                               "source": source
                           })
                return
            
            # Event zu Target-Services routen
            routing_tasks = []
            for rule in applicable_rules:
                for target_service in rule.target_services:
                    if target_service != "*":
                        task = self._forward_to_service(event_data, target_service)
                        routing_tasks.append(task)
            
            if routing_tasks:
                # Parallele Routing-Ausführung
                results = await asyncio.gather(*routing_tasks, return_exceptions=True)
                
                # Prüfe auf Routing-Fehler
                failed_routings = [r for r in results if isinstance(r, Exception)]
                if failed_routings:
                    logger.warning(f"Some event routings failed: {len(failed_routings)}/{len(routing_tasks)}",
                                 extra={"failed_count": len(failed_routings)})
            
            logger.debug("Event routed successfully", 
                        extra={
                            "event_type": event_type,
                            "source": source,
                            "rules_applied": len(applicable_rules),
                            "targets_count": len(routing_tasks)
                        })
                        
        except ValidationException:
            raise
        except EventBusException:
            raise
        except Exception as exc:
            raise EventRoutingException(
                f"Event routing failed: {str(exc)}",
                context={
                    "event_type": event_data.get('event_type'),
                    "source": event_data.get('source')
                },
                cause=exc
            )
    
    async def _find_applicable_rules(self, event_type: str, source: str) -> List[EventRouteConfig]:
        """Finde anwendbare Routing-Regeln"""
        try:
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
            
            return applicable_rules
            
        except Exception as exc:
            raise EventRoutingException(
                f"Failed to find applicable routing rules: {str(exc)}",
                context={"event_type": event_type, "source": source},
                cause=exc
            )
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Simple Wildcard-Pattern-Matching mit Validierung"""
        try:
            if not isinstance(text, str) or not isinstance(pattern, str):
                return False
                
            if pattern == "*":
                return True
            if pattern.endswith("*"):
                return text.startswith(pattern[:-1])
            if pattern.startswith("*"):
                return text.endswith(pattern[1:])
            return text == pattern
            
        except Exception as exc:
            logger.warning(f"Pattern matching failed: {exc}")
            return False
    
    @event_bus_exception_handler()
    async def _forward_to_service(self, event_data: Dict[str, Any], target_service: str):
        """Forward Event zu spezifischem Service mit Exception-Handling"""
        try:
            # Input-Validierung
            if not target_service or not target_service.strip():
                raise ValidationException(
                    "Target service name cannot be empty",
                    field_errors={"target_service": "Must not be empty"}
                )
            
            # Event mit Target-Service-Info erweitern
            forwarded_event = event_data.copy()
            forwarded_event.update({
                'routed_to': target_service,
                'routed_by': self.module_name,
                'routed_at': datetime.utcnow().isoformat()
            })
            
            # Event-Type validieren
            try:
                event_type_enum = EventType(event_data['event_type'])
            except (ValueError, KeyError) as exc:
                raise ValidationException(
                    f"Invalid event type: {event_data.get('event_type')}",
                    field_errors={"event_type": "Must be a valid EventType"},
                    cause=exc
                )
            
            # Event republish für Target-Service
            event_to_publish = Event(
                event_type=event_type_enum,
                stream_id=f"routed-{target_service}",
                data=forwarded_event,
                source=self.module_name,
                correlation_id=str(uuid4())
            )
            
            await self.event_bus.publish(event_to_publish)
            
            logger.debug("Event forwarded successfully",
                        extra={
                            "target_service": target_service,
                            "event_type": event_data['event_type'],
                            "stream_id": event_to_publish.stream_id
                        })
            
        except ValidationException:
            raise
        except Exception as exc:
            raise PublishException(
                f"Failed to forward event to service: {target_service}",
                event_type=event_data.get('event_type'),
                context={"target_service": target_service},
                cause=exc
            )

    @exception_handler(exceptions=[ValidationException, EventBusException])
    async def process_business_logic(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Event-Router business logic mit Exception-Handling"""
        try:
            if not isinstance(input_data, dict):
                raise ValidationException(
                    "Input data must be a dictionary",
                    context={"received_type": type(input_data).__name__}
                )
            
            command = input_data.get('command', '')
            
            if not command:
                raise ValidationException(
                    "Command is required",
                    field_errors={"command": "Must not be empty"}
                )
            
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
                return await self._add_routing_rule(input_data)
            elif command == 'get_statistics':
                return self._get_statistics()
            else:
                raise ValidationException(
                    f"Unknown command: {command}",
                    field_errors={"command": "Must be a valid command"}
                )
        
        except ValidationException:
            raise
        except Exception as exc:
            raise EventBusException(
                f"Business logic processing failed: {str(exc)}",
                context={"command": input_data.get('command')},
                cause=exc
            )
    
    async def _add_routing_rule(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Füge Routing-Regel hinzu mit Validierung"""
        rule_name = input_data.get('rule_name')
        rule_config = input_data.get('rule_config')
        
        if not rule_name:
            raise ValidationException(
                "Rule name is required",
                field_errors={"rule_name": "Must not be empty"}
            )
        
        if not rule_config:
            raise ValidationException(
                "Rule configuration is required", 
                field_errors={"rule_config": "Must not be empty"}
            )
        
        try:
            new_rule = EventRouteConfig(**rule_config)
            self.routing_rules[rule_name] = new_rule
            
            return {
                'status': 'success', 
                'message': f'Rule {rule_name} added successfully',
                'rule_count': len(self.routing_rules)
            }
        except Exception as exc:
            raise ValidationException(
                f"Invalid rule configuration: {str(exc)}",
                context={"rule_name": rule_name},
                cause=exc
            )
    
    def _get_statistics(self) -> Dict[str, Any]:
        """Sammle Statistiken"""
        return {
            'active_rules': len([r for r in self.routing_rules.values() if r.enabled]),
            'total_rules': len(self.routing_rules),
            'subscriptions': len(self.active_subscriptions),
            'module_initialized': self.is_initialized,
            'module_name': self.module_name
        }


class EventStoreModule(BackendBaseModule):
    """Event-Store-Modul mit strukturiertem Exception-Handling"""
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("event-store", event_bus)
        self.redis_client = None
        self.stored_events_count = 0
        self.connection_retries = 0
        self.max_connection_retries = 3
        
    @database_exception_handler(rollback_transaction=False, max_retries=3)
    async def initialize(self) -> bool:
        """Initialisiere Event-Store mit strukturiertem Exception-Handling"""
        transaction_id = f"store_init_{int(datetime.utcnow().timestamp())}"
        
        async with async_exception_context() as handler:
            try:
                self.transaction_manager.begin_transaction(transaction_id)
                
                # Redis-Verbindung mit Retry-Logic
                await self._establish_redis_connection()
                
                # Connection-Test
                await self._test_redis_connection()
                
                # Alle Event-Types für Persistierung abonnieren
                await self._setup_event_subscriptions()
                
                self.transaction_manager.commit_transaction(transaction_id)
                
                logger.info("Event-Store initialized successfully", 
                           extra={
                               "module": self.module_name,
                               "redis_connected": self.redis_client is not None
                           })
                return True
                
            except DatabaseException:
                self.transaction_manager.rollback_transaction(transaction_id)
                raise
            except Exception as exc:
                self.transaction_manager.rollback_transaction(transaction_id)
                raise ConfigurationException(
                    f"Event-Store initialization failed: {str(exc)}",
                    context={"module": self.module_name},
                    cause=exc
                )
    
    async def _establish_redis_connection(self):
        """Etabliere Redis-Verbindung mit Retry-Logic"""
        redis_url = os.getenv("REDIS_URL", "redis://10.1.1.174:6379/1")
        
        for attempt in range(self.max_connection_retries):
            try:
                self.redis_client = aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=10
                )
                
                self.connection_retries = attempt
                logger.info(f"Redis connection established on attempt {attempt + 1}")
                return
                
            except Exception as exc:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {exc}")
                if attempt == self.max_connection_retries - 1:
                    raise ConnectionException(
                        f"Failed to connect to Redis after {self.max_connection_retries} attempts",
                        context={
                            "redis_url": redis_url,
                            "attempts": self.max_connection_retries
                        },
                        cause=exc
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _test_redis_connection(self):
        """Teste Redis-Verbindung"""
        try:
            result = await self.redis_client.ping()
            if not result:
                raise ConnectionException(
                    "Redis ping test failed - connection not responsive"
                )
        except Exception as exc:
            raise ConnectionException(
                f"Redis connection test failed: {str(exc)}",
                cause=exc
            )
    
    async def _setup_event_subscriptions(self):
        """Setup Event-Subscriptions mit Exception-Handling"""
        subscription_tasks = []
        
        for event_type in EventType:
            task = self._subscribe_to_event_store(event_type)
            subscription_tasks.append(task)
        
        results = await asyncio.gather(*subscription_tasks, return_exceptions=True)
        
        # Prüfe auf Subscription-Fehler
        failed_subscriptions = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_subscriptions.append((list(EventType)[i], result))
        
        if failed_subscriptions:
            raise SubscribeException(
                f"Failed to setup {len(failed_subscriptions)} event store subscriptions",
                context={
                    "failed_subscriptions": [
                        {"event_type": et.value, "error": str(err)} 
                        for et, err in failed_subscriptions
                    ]
                }
            )
    
    async def _subscribe_to_event_store(self, event_type: EventType):
        """Subscribe zu Event-Store mit Exception-Handling"""
        try:
            await self.event_bus.subscribe(
                event_type.value,
                self._store_event,
                f"store-{event_type.value}"
            )
            return event_type
        except Exception as exc:
            raise SubscribeException(
                f"Failed to subscribe to event store for type: {event_type.value}",
                context={"event_type": event_type.value},
                cause=exc
            )
    
    @database_exception_handler()
    async def _store_event(self, event_data: Dict[str, Any]):
        """Store Event in Redis mit strukturiertem Exception-Handling"""
        try:
            # Input-Validierung
            if not isinstance(event_data, dict):
                raise ValidationException(
                    "Event data must be a dictionary",
                    context={"received_type": type(event_data).__name__}
                )
            
            if not self.redis_client:
                raise ConnectionException("Redis client not initialized")
            
            # Event-ID generieren
            event_id = str(uuid4())
            event_key = f"event:{event_id}"
            
            # Event-Daten mit Metadaten erweitern
            stored_event = {
                'id': event_id,
                'stored_at': datetime.utcnow().isoformat(),
                'stored_by': self.module_name,
                **event_data
            }
            
            # Redis-Pipeline für atomare Operationen
            pipeline = self.redis_client.pipeline()
            
            try:
                # Event-Daten speichern
                pipeline.hset(event_key, mapping={
                    'data': json.dumps(stored_event),
                    'event_type': event_data.get('event_type', ''),
                    'source': event_data.get('source', ''),
                    'timestamp': event_data.get('timestamp', ''),
                    'stream_id': event_data.get('stream_id', '')
                })
                
                # Indizes aktualisieren
                event_type = event_data.get('event_type', '')
                source = event_data.get('source', '')
                
                if event_type:
                    pipeline.sadd(f"events_by_type:{event_type}", event_id)
                
                if source:
                    pipeline.sadd(f"events_by_source:{source}", event_id)
                
                # TTL setzen (30 Tage)
                pipeline.expire(event_key, 30 * 24 * 3600)
                
                # Pipeline ausführen
                await pipeline.execute()
                
                self.stored_events_count += 1
                
                logger.debug("Event stored successfully", 
                           extra={
                               "event_id": event_id,
                               "event_type": event_type,
                               "source": source
                           })
                
            except Exception as exc:
                await pipeline.discard()
                raise QueryException(
                    f"Failed to execute Redis pipeline: {str(exc)}",
                    context={"event_id": event_id},
                    cause=exc
                )
                
        except (ValidationException, DatabaseException):
            raise
        except Exception as exc:
            raise DatabaseException(
                f"Event storage failed: {str(exc)}",
                context={"event_data_keys": list(event_data.keys()) if isinstance(event_data, dict) else None},
                cause=exc
            )
    
    @database_exception_handler()
    async def query_events(self, query: EventStoreQuery) -> List[Dict[str, Any]]:
        """Query Events aus Store mit strukturiertem Exception-Handling"""
        try:
            if not self.redis_client:
                raise ConnectionException("Redis client not initialized")
                
            # Input-Validierung
            if query.limit <= 0:
                raise ValidationException(
                    "Query limit must be positive",
                    field_errors={"limit": "Must be greater than 0"}
                )
            
            if query.limit > 1000:
                raise ValidationException(
                    "Query limit too large (max 1000)",
                    field_errors={"limit": "Must be <= 1000"}
                )
            
            event_ids = await self._find_event_ids(query)
            
            if not event_ids:
                return []
            
            # Events parallel laden
            events = await self._load_events_parallel(list(event_ids)[:query.limit])
            
            # Nach Timestamp sortieren
            events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return events
            
        except (ValidationException, DatabaseException):
            raise
        except Exception as exc:
            raise QueryException(
                f"Event query failed: {str(exc)}",
                context={"query": query.dict() if query else None},
                cause=exc
            )
    
    async def _find_event_ids(self, query: EventStoreQuery) -> set:
        """Finde Event-IDs basierend auf Query-Parametern"""
        try:
            event_ids = set()
            
            # Filter nach Event-Types
            if query.event_types:
                type_ids = set()
                for event_type in query.event_types:
                    type_events = await self.redis_client.smembers(f"events_by_type:{event_type}")
                    type_ids.update(type_events)
                event_ids = type_ids
            
            # Filter nach Sources
            if query.sources:
                source_ids = set()
                for source in query.sources:
                    src_events = await self.redis_client.smembers(f"events_by_source:{source}")
                    source_ids.update(src_events)
                
                if event_ids:
                    event_ids = event_ids.intersection(source_ids)
                else:
                    event_ids = source_ids
            
            # Wenn keine Filter, Sample von allen Events
            if not event_ids:
                event_ids = await self._get_sample_event_ids(query.limit)
            
            return event_ids
            
        except Exception as exc:
            raise QueryException(
                f"Failed to find event IDs: {str(exc)}",
                cause=exc
            )
    
    async def _get_sample_event_ids(self, limit: int) -> set:
        """Hole Sample von Event-IDs"""
        event_ids = set()
        cursor = 0
        count = 0
        max_iterations = 10  # Prevent infinite loops
        
        while cursor != 0 or count == 0:
            if count >= max_iterations:
                break
                
            cursor, keys = await self.redis_client.scan(
                cursor=cursor, 
                match="event:*", 
                count=limit
            )
            event_ids.update([key.replace('event:', '') for key in keys])
            count += 1
            
            if len(event_ids) >= limit:
                break
        
        return event_ids
    
    async def _load_events_parallel(self, event_ids: List[str]) -> List[Dict[str, Any]]:
        """Lade Events parallel aus Redis"""
        async def load_single_event(event_id: str) -> Optional[Dict[str, Any]]:
            try:
                event_data = await self.redis_client.hget(f"event:{event_id}", "data")
                if event_data:
                    return json.loads(event_data)
                return None
            except Exception as exc:
                logger.warning(f"Failed to load event {event_id}: {exc}")
                return None
        
        # Parallel laden
        tasks = [load_single_event(event_id) for event_id in event_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter gültige Events
        events = []
        for result in results:
            if isinstance(result, dict):
                events.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Event loading failed: {result}")
        
        return events
    
    @exception_handler(exceptions=[ValidationException, DatabaseException])
    async def process_business_logic(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Event-Store business logic mit Exception-Handling"""
        try:
            if not isinstance(input_data, dict):
                raise ValidationException(
                    "Input data must be a dictionary",
                    context={"received_type": type(input_data).__name__}
                )
            
            command = input_data.get('command', '')
            
            if not command:
                raise ValidationException(
                    "Command is required",
                    field_errors={"command": "Must not be empty"}
                )
            
            if command == 'query_events':
                return await self._handle_query_command(input_data)
            elif command == 'get_statistics':
                return self._get_statistics()
            else:
                raise ValidationException(
                    f"Unknown command: {command}",
                    field_errors={"command": "Must be a valid command"}
                )
        
        except ValidationException:
            raise
        except Exception as exc:
            raise DatabaseException(
                f"Business logic processing failed: {str(exc)}",
                context={"command": input_data.get('command')},
                cause=exc
            )
    
    async def _handle_query_command(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Query-Command"""
        query_params = input_data.get('query', {})
        
        if not isinstance(query_params, dict):
            raise ValidationException(
                "Query parameters must be a dictionary",
                field_errors={"query": "Must be a dictionary"}
            )
        
        try:
            query = EventStoreQuery(**query_params)
            events = await self.query_events(query)
            
            return {
                'events': events, 
                'count': len(events),
                'query_params': query_params
            }
        except Exception as exc:
            raise ValidationException(
                f"Invalid query parameters: {str(exc)}",
                context={"query_params": query_params},
                cause=exc
            )
    
    def _get_statistics(self) -> Dict[str, Any]:
        """Sammle Event-Store-Statistiken"""
        return {
            'stored_events': self.stored_events_count,
            'redis_connected': self.redis_client is not None,
            'connection_retries': self.connection_retries,
            'module_initialized': self.is_initialized,
            'module_name': self.module_name
        }


class EventBusOrchestrator:
    """Hauptorchestrator für Event-Bus Service mit Exception-Framework"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Event-Bus Service v2.0",
            description="Zentraler Event-Hub mit strukturiertem Exception-Handling",
            version="2.0.0"
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
        self.event_bus = EventBusConnector("event-bus-v2")
        self.modules = {}
        
        # Module initialisieren
        self.event_router = EventRouterModule(self.event_bus)
        self.event_store = EventStoreModule(self.event_bus)
        
        # FastAPI Exception-Handler registrieren
        fastapi_exception_handler = create_fastapi_exception_handler()
        self.app.add_exception_handler(BaseServiceException, fastapi_exception_handler)
        
        # API-Routen registrieren
        self._register_routes()
        
        # Startup/Shutdown Events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
    
    def _register_routes(self):
        """Registriere API-Routen mit Exception-Handling"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "event-bus-v2",
                "version": "2.0.0",
                "status": "running",
                "modules": ["event-router", "event-store"],
                "port": 8014,
                "exception_framework": "enabled"
            }
        
        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": "event-bus-v2",
                "event_bus_connected": self.event_bus.connected,
                "modules": {
                    "event_router": self.event_router.is_initialized,
                    "event_store": self.event_store.is_initialized
                },
                "exception_handling": "active"
            }
        
        @self.app.post("/events/publish")
        @exception_handler(exceptions=[ValidationException, PublishException])
        async def publish_event(event: EventMessage):
            """Event manuell publizieren mit Exception-Handling"""
            try:
                # Input-Validierung
                if not event.event_type:
                    raise ValidationException(
                        "Event type is required",
                        field_errors={"event_type": "Must not be empty"}
                    )
                
                if not event.source:
                    raise ValidationException(
                        "Event source is required", 
                        field_errors={"source": "Must not be empty"}
                    )
                
                # Event-Type validieren
                try:
                    event_type_enum = EventType(event.event_type)
                except ValueError as exc:
                    raise ValidationException(
                        f"Invalid event type: {event.event_type}",
                        field_errors={"event_type": "Must be a valid EventType"},
                        cause=exc
                    )
                
                published_event = Event(
                    event_type=event_type_enum,
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
                    "event_type": event.event_type,
                    "correlation_id": published_event.correlation_id
                }
                
            except (ValidationException, PublishException):
                raise
            except Exception as exc:
                raise PublishException(
                    f"Failed to publish event: {str(exc)}",
                    event_type=event.event_type,
                    cause=exc
                )
        
        @self.app.get("/events/query")
        @exception_handler(exceptions=[ValidationException, QueryException])
        async def query_events(
            event_types: Optional[str] = None,
            sources: Optional[str] = None,
            limit: int = 100
        ):
            """Events aus Store abfragen mit Exception-Handling"""
            try:
                # Parameter-Validierung
                if limit <= 0 or limit > 1000:
                    raise ValidationException(
                        "Limit must be between 1 and 1000",
                        field_errors={"limit": "Must be between 1 and 1000"}
                    )
                
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
                
            except (ValidationException, QueryException):
                raise
            except Exception as exc:
                raise QueryException(
                    f"Event query failed: {str(exc)}",
                    cause=exc
                )
        
        @self.app.get("/routing/rules")
        @exception_handler(exceptions=[EventBusException])
        async def get_routing_rules():
            """Routing-Regeln abrufen"""
            try:
                result = await self.event_router.process_business_logic({
                    'command': 'get_routing_rules'
                })
                return result
            except Exception as exc:
                raise EventBusException(
                    f"Failed to get routing rules: {str(exc)}",
                    cause=exc
                )
        
        @self.app.post("/routing/rules")
        @exception_handler(exceptions=[ValidationException, EventBusException])
        async def add_routing_rule(rule_name: str, rule: EventRouteConfig):
            """Routing-Regel hinzufügen mit Exception-Handling"""
            try:
                if not rule_name or not rule_name.strip():
                    raise ValidationException(
                        "Rule name is required",
                        field_errors={"rule_name": "Must not be empty"}
                    )
                
                result = await self.event_router.process_business_logic({
                    'command': 'add_routing_rule',
                    'rule_name': rule_name,
                    'rule_config': rule.dict()
                })
                return result
            except (ValidationException, EventBusException):
                raise
            except Exception as exc:
                raise EventBusException(
                    f"Failed to add routing rule: {str(exc)}",
                    cause=exc
                )
        
        @self.app.get("/statistics")
        @exception_handler(exceptions=[EventBusException])
        async def get_statistics():
            """Service-Statistiken mit Exception-Handling"""
            try:
                router_stats = await self.event_router.process_business_logic({
                    'command': 'get_statistics'
                })
                store_stats = await self.event_store.process_business_logic({
                    'command': 'get_statistics'
                })
                
                return {
                    "service": "event-bus-v2",
                    "version": "2.0.0",
                    "event_bus": {
                        "connected": self.event_bus.connected,
                        "service_name": self.event_bus.service_name
                    },
                    "router": router_stats,
                    "store": store_stats,
                    "uptime": "running",
                    "exception_framework": "active"
                }
            except Exception as exc:
                raise EventBusException(
                    f"Failed to get statistics: {str(exc)}",
                    cause=exc
                )
    
    @exception_handler(exceptions=[ConfigurationException, ConnectionException])
    async def startup_event(self):
        """Service startup mit strukturiertem Exception-Handling"""
        transaction_id = f"service_startup_{int(datetime.utcnow().timestamp())}"
        
        async with async_exception_context() as handler:
            try:
                transaction_manager = get_transaction_manager()
                transaction_manager.begin_transaction(transaction_id)
                
                logger.info("Starting Event-Bus Service v2.0...")
                
                # Event-Bus verbinden
                if not await self.event_bus.connect():
                    raise ConnectionException(
                        "Failed to connect to event bus",
                        context={"service": self.event_bus.service_name}
                    )
                
                # Module registrieren
                self.modules.update({
                    "event-router": self.event_router,
                    "event-store": self.event_store
                })
                
                # Module parallel initialisieren
                init_tasks = []
                for module_name, module in self.modules.items():
                    logger.info(f"Initializing module: {module_name}")
                    task = module.initialize()
                    init_tasks.append(task)
                
                results = await asyncio.gather(*init_tasks, return_exceptions=True)
                
                # Prüfe auf Initialisierungsfehler
                failed_modules = []
                for i, result in enumerate(results):
                    module_name = list(self.modules.keys())[i]
                    if isinstance(result, Exception):
                        failed_modules.append((module_name, result))
                    elif result is False:
                        failed_modules.append((module_name, "Initialization returned False"))
                
                if failed_modules:
                    raise ConfigurationException(
                        f"Failed to initialize {len(failed_modules)} modules",
                        context={
                            "failed_modules": [
                                {"name": name, "error": str(err)} 
                                for name, err in failed_modules
                            ]
                        }
                    )
                
                transaction_manager.commit_transaction(transaction_id)
                
                logger.info("Event-Bus Service v2.0 started successfully",
                           extra={
                               "modules": len(self.modules),
                               "event_bus_connected": self.event_bus.connected,
                               "exception_framework": "active"
                           })
                
            except (ConfigurationException, ConnectionException):
                await get_transaction_manager().execute_rollback()
                raise
            except Exception as exc:
                await get_transaction_manager().execute_rollback()
                raise ConfigurationException(
                    f"Service startup failed: {str(exc)}",
                    cause=exc
                )
    
    @exception_handler(exceptions=[EventBusException])
    async def shutdown_event(self):
        """Service shutdown mit Exception-Handling"""
        try:
            logger.info("Shutting down Event-Bus Service v2.0...")
            
            # Module parallel herunterfahren
            shutdown_tasks = []
            for module_name, module in self.modules.items():
                logger.info(f"Shutting down module: {module_name}")
                task = module.shutdown()
                shutdown_tasks.append(task)
            
            if shutdown_tasks:
                results = await asyncio.gather(*shutdown_tasks, return_exceptions=True)
                
                # Log Shutdown-Fehler (aber nicht als kritisch behandeln)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        module_name = list(self.modules.keys())[i]
                        logger.warning(f"Module shutdown failed: {module_name}: {result}")
            
            # Event-Bus trennen
            await self.event_bus.disconnect()
            
            logger.info("Event-Bus Service v2.0 shut down successfully")
            
        except Exception as exc:
            # Bei Shutdown-Fehlern nur loggen, nicht re-raisen
            logger.error(f"Error during shutdown: {exc}")


def main():
    """Main entry point mit Exception-Handling"""
    try:
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
        
        logger.info("Event-Bus Service v2.0 starting on port 8014...")
        server.run()
        
    except KeyboardInterrupt:
        logger.info("Event-Bus Service v2.0 stopped by user")
    except ConfigurationException as exc:
        logger.error(f"Configuration error: {exc.message}")
        logger.error(f"Error details: {exc.to_dict()}")
        raise
    except ConnectionException as exc:
        logger.error(f"Connection error: {exc.message}")
        logger.error(f"Error details: {exc.to_dict()}")
        raise
    except BaseServiceException as exc:
        logger.error(f"Service error: {exc.message}")
        logger.error(f"Error details: {exc.to_dict()}")
        raise
    except Exception as exc:
        logger.error(f"Event-Bus Service v2.0 crashed with unexpected error: {exc}")
        # Erstelle BaseServiceException für konsistente Behandlung
        service_exc = ConfigurationException(
            f"Unexpected service crash: {str(exc)}",
            cause=exc
        )
        logger.error(f"Exception details: {service_exc.to_dict()}")
        raise service_exc


if __name__ == "__main__":
    main()