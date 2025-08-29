#!/usr/bin/env python3
"""
Service Base Classes - BaseServiceOrchestrator Implementation
Issue #61 - Service Base-Klasse zur Code-Duplikation-Eliminierung

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Jede Service-Klasse hat eine spezielle Aufgabe
- Open/Closed: Erweiterbar durch Templates ohne Änderung der Basis
- Liskov Substitution: Alle Services implementieren identische Interfaces
- Interface Segregation: Template-Methods nur für benötigte Features
- Dependency Inversion: Konfiguration-basierte Abhängigkeiten

Code-Duplikation Eliminierung:
- FastAPI App Setup
- CORS Middleware
- Event Handlers (startup/shutdown)  
- Health Endpoints
- Logging Setup
- Configuration Loading
"""

import asyncio
import logging
import os
import signal
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Union
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# =============================================================================
# SERVICE CONFIGURATION BASE
# =============================================================================

class ServiceConfig(BaseModel):
    """Service Configuration Base"""
    service_name: str
    version: str = "1.0.0"
    description: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    # CORS Configuration
    cors_origins: List[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
    
    # Health Endpoint Configuration
    health_endpoint: str = "/health"
    include_root_endpoint: bool = True
    
    # Custom Environment Variables
    environment_prefix: str = ""


# =============================================================================  
# BASE SERVICE ORCHESTRATOR - TEMPLATE METHOD PATTERN
# =============================================================================

class BaseServiceOrchestrator(ABC):
    """
    Base Service Orchestrator - Template Method Pattern
    
    ELIMINIERT 30% CODE-DUPLIKATION durch:
    - Standardisiertes FastAPI App Setup
    - Einheitliche CORS-Konfiguration
    - Konsistente Event Handler (startup/shutdown)
    - Automatische Health Endpoints
    - Strukturiertes Logging Setup
    - Environment-basierte Konfiguration
    
    Template Methods:
    - configure_service() - Service-spezifische Konfiguration
    - register_routes() - Service-spezifische API Routes
    - startup_hook() - Service-spezifische Startup-Logik
    - shutdown_hook() - Service-spezifische Shutdown-Logik
    - health_check_details() - Service-spezifische Health-Details
    """
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.app: Optional[FastAPI] = None
        self.logger = self._setup_logging()
        self.is_healthy = False
        self.startup_timestamp: Optional[datetime] = None
        self._shutdown_event = asyncio.Event()
        
        # Service state tracking
        self._modules: Dict[str, Any] = {}
        self._background_tasks: List[asyncio.Task] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Setup Structured Logging"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    f"/opt/aktienanalyse-ökosystem/logs/{self.config.service_name}.log"
                )
            ]
        )
        
        logger = logging.getLogger(self.config.service_name)
        logger.setLevel(log_level)
        return logger
    
    def create_app(self) -> FastAPI:
        """
        CREATE FASTAPI APP - Template Method
        Eliminiert FastAPI App Setup Duplikation
        """
        if self.app is not None:
            return self.app
        
        # Lifespan Context Manager für startup/shutdown
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self._startup_event()
            yield
            # Shutdown  
            await self._handle_shutdown()
        
        # FastAPI App mit Lifespan
        self.app = FastAPI(
            title=self.config.service_name,
            description=self.config.description,
            version=self.config.version,
            lifespan=lifespan
        )
        
        # CORS Middleware - Eliminiert CORS Setup Duplikation
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=self.config.cors_credentials,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers,
        )
        
        # Service-spezifische Konfiguration
        self.configure_service()
        
        # Standard Routes registrieren
        self._register_standard_routes()
        
        # Service-spezifische Routes
        self.register_routes()
        
        return self.app
    
    def _register_standard_routes(self):
        """
        STANDARD ROUTES - Eliminiert Health Endpoint Duplikation
        """
        
        @self.app.get(self.config.health_endpoint)
        async def health():
            """Standard Health Check Endpoint"""
            base_health = {
                "status": "healthy" if self.is_healthy else "unhealthy",
                "service": self.config.service_name,
                "version": self.config.version,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": int((datetime.utcnow() - self.startup_timestamp).total_seconds()) if self.startup_timestamp else 0
            }
            
            # Service-spezifische Health Details hinzufügen
            service_details = await self.health_check_details()
            if service_details:
                base_health.update(service_details)
            
            status_code = 200 if self.is_healthy else 503
            return JSONResponse(content=base_health, status_code=status_code)
        
        # Optional: Root Endpoint
        if self.config.include_root_endpoint:
            @self.app.get("/")
            async def root():
                """Root Service Information"""
                return {
                    "service": self.config.service_name,
                    "version": self.config.version,
                    "status": "running",
                    "health_endpoint": self.config.health_endpoint,
                    "timestamp": datetime.utcnow().isoformat()
                }
    
    async def _startup_event(self):
        """
        STARTUP EVENT HANDLER - Template Method
        Eliminiert Startup Handler Duplikation
        """
        try:
            self.startup_timestamp = datetime.utcnow()
            self.logger.info(f"🚀 Starting {self.config.service_name} v{self.config.version}")
            
            # Service-spezifische Startup-Logik
            await self.startup_hook()
            
            self.is_healthy = True
            
            self.logger.info(f"✅ {self.config.service_name} started successfully on {self.config.host}:{self.config.port}")
            
        except Exception as e:
            self.logger.error(f"❌ Startup failed: {str(e)}")
            self.is_healthy = False
            raise RuntimeError(f"Service startup failed: {str(e)}")
    
    async def _handle_shutdown(self):
        """
        SHUTDOWN EVENT HANDLER - Template Method  
        Eliminiert Shutdown Handler Duplikation
        """
        try:
            self.logger.info(f"🛑 Shutting down {self.config.service_name}...")
            
            # Background Tasks beenden
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Service-spezifische Shutdown-Logik
            await self.shutdown_hook()
            
            self.is_healthy = False
            self.logger.info(f"✅ {self.config.service_name} shut down successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Shutdown error: {str(e)}")
    
    # =============================================================================
    # TEMPLATE METHODS - Service-spezifische Implementierung erforderlich
    # =============================================================================
    
    @abstractmethod
    def configure_service(self):
        """
        TEMPLATE METHOD: Service-spezifische Konfiguration
        
        Beispiel:
        def configure_service(self):
            self.event_bus = EventBusConnector(self.config.service_name)
            self.modules['router'] = EventRouterModule(self.event_bus)
        """
        pass
    
    @abstractmethod 
    def register_routes(self):
        """
        TEMPLATE METHOD: Service-spezifische API Routes
        
        Beispiel:
        def register_routes(self):
            @self.app.post("/events/publish")
            async def publish_event(event: EventMessage):
                return await self.event_bus.publish(event)
        """
        pass
    
    async def startup_hook(self):
        """
        TEMPLATE METHOD: Service-spezifische Startup-Logik
        Optional - Default: Keine zusätzliche Startup-Logik
        
        Beispiel:
        async def startup_hook(self):
            await self.event_bus.connect()
            await self.modules['router'].initialize()
        """
        pass
    
    async def shutdown_hook(self):
        """
        TEMPLATE METHOD: Service-spezifische Shutdown-Logik  
        Optional - Default: Keine zusätzliche Shutdown-Logik
        
        Beispiel:
        async def shutdown_hook(self):
            await self.event_bus.disconnect()
        """
        pass
    
    async def health_check_details(self) -> Optional[Dict[str, Any]]:
        """
        TEMPLATE METHOD: Service-spezifische Health Check Details
        Optional - Default: Keine zusätzlichen Details
        
        Beispiel:
        async def health_check_details(self):
            return {
                "event_bus_connected": self.event_bus.connected,
                "modules_initialized": len([m for m in self.modules.values() if m.is_initialized])
            }
        """
        return None
    
    # =============================================================================
    # UTILITY METHODS - Gemeinsame Service-Funktionalitäten  
    # =============================================================================
    
    def register_module(self, name: str, module: Any):
        """Register Service Module"""
        self._modules[name] = module
        self.logger.info(f"📦 Module registered: {name}")
    
    def get_module(self, name: str) -> Optional[Any]:
        """Get Registered Module"""
        return self._modules.get(name)
    
    def add_background_task(self, coro: Callable) -> asyncio.Task:
        """Add Background Task with Tracking"""
        task = asyncio.create_task(coro())
        self._background_tasks.append(task)
        return task
    
    def run(self, **uvicorn_kwargs):
        """
        RUN SERVICE - Eliminiert Uvicorn Setup Duplikation
        """
        app = self.create_app()
        
        # Default uvicorn config
        uvicorn_config = {
            "app": app,
            "host": self.config.host,
            "port": self.config.port,
            "log_level": self.config.log_level.lower(),
            "access_log": True
        }
        
        # Override mit custom kwargs
        uvicorn_config.update(uvicorn_kwargs)
        
        self.logger.info(f"🚀 Launching {self.config.service_name} on {self.config.host}:{self.config.port}")
        
        # Signal Handler für graceful shutdown
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            uvicorn.run(**uvicorn_config)
        except KeyboardInterrupt:
            self.logger.info("Service stopped by user")
        except Exception as e:
            self.logger.error(f"Service crashed: {str(e)}")
            raise


# =============================================================================
# LEGACY COMPATIBILITY - Für bestehende Services
# =============================================================================

class BaseService(ABC):
    """Legacy Base Service Class - Backwards Compatibility"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.is_running = False
    
    @abstractmethod
    async def start(self):
        """Start Service"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop Service"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Health Check"""
        pass


class ModularService(BaseService):
    """Legacy Modular Service mit Module Management - Backwards Compatibility"""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self.modules = {}
        self.app = FastAPI(title=service_name)
    
    def register_module(self, name: str, module: Any):
        """Register Module"""
        self.modules[name] = module
        self.logger.info(f"Module registered: {name}")
    
    async def start(self):
        """Start Service und Module"""
        self.logger.info("Starting modular service")
        
        for name, module in self.modules.items():
            if hasattr(module, 'start'):
                await module.start()
        
        self.is_running = True
        self.logger.info("Modular service started")
    
    async def stop(self):
        """Stop Service und Module"""
        self.logger.info("Stopping modular service")
        
        for name, module in self.modules.items():
            if hasattr(module, 'stop'):
                await module.stop()
        
        self.is_running = False
        self.logger.info("Modular service stopped")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check"""
        module_health = {}
        overall_healthy = True
        
        for name, module in self.modules.items():
            if hasattr(module, 'health_check'):
                try:
                    health = await module.health_check()
                    module_health[name] = health
                    if health.get('status') != 'healthy':
                        overall_healthy = False
                except Exception as e:
                    module_health[name] = {'status': 'error', 'error': str(e)}
                    overall_healthy = False
            else:
                module_health[name] = {'status': 'unknown'}
        
        return {
            'service': self.service_name,
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'running': self.is_running,
            'modules': module_health
        }


# =============================================================================
# MIXINS - Für spezielle Service-Features
# =============================================================================

class DatabaseMixin:
    """Database Mixin"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_pool = None
    
    async def setup_database(self, database_url: str):
        """Setup Database Connection"""
        # Placeholder for database setup
        self.logger.info("Database setup placeholder", extra={"url": database_url})


class EventBusMixin:
    """Event Bus Mixin"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_bus = None
    
    async def setup_event_bus(self, event_bus_config: Dict[str, Any]):
        """Setup Event Bus"""
        # Placeholder for event bus setup
        self.logger.info("Event bus setup placeholder", extra={"config": event_bus_config})