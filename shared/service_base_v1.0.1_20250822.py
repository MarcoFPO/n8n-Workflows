#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Base Classes für aktienanalyse-ökosystem
Eliminiert Setup-Code-Duplikation in Services
"""

import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import structlog
import asyncpg

# Eigene Imports
from .security_config import SecurityConfig
from .logging_config import setup_logging

class BaseService(ABC):
    """
    Basis-Klasse für alle Services
    Eliminiert FastAPI-Setup-Duplikation
    """
    
    def __init__(self, service_name: str, version: str = "1.0.0", port: int = 8000):
        self.service_name = service_name
        self.version = version
        self.port = port
        self.startup_time = datetime.now()
        
        # Logger Setup
        self.logger = setup_logging(service_name)
        
        # FastAPI App erstellen
        self.app = FastAPI(
            title=f"Aktienanalyse {service_name.title()} Service",
            description=f"{service_name.title()} Service für aktienanalyse-ökosystem",
            version=version
        )
        
        # Standard Middleware Setup
        self._setup_middleware()
        
        # Standard Routes Setup
        self._setup_standard_routes()
        
        # Service-spezifische Initialisierung
        self._setup_service()
    
    def _setup_middleware(self):
        """Setup Standard-Middleware für alle Services"""
        # CORS Middleware mit Security Config
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=SecurityConfig.get_cors_origins(),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        
        # Request Logging Middleware
        @self.app.middleware("http")
        async def log_requests(request, call_next):
            start_time = datetime.now()
            response = await call_next(request)
            process_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(
                "Request processed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=process_time
            )
            return response
    
    def _setup_standard_routes(self):
        """Setup Standard-Routes für alle Services"""
        
        @self.app.get("/health")
        async def health_check():
            """Standard Health Check für alle Services"""
            uptime = (datetime.now() - self.startup_time).total_seconds()
            
            health_data = {
                "service": self.service_name,
                "status": "healthy",
                "version": self.version,
                "startup_time": self.startup_time.isoformat(),
                "uptime_seconds": uptime,
                "timestamp": datetime.now().isoformat()
            }
            
            # Service-spezifische Health-Daten hinzufügen
            additional_health = await self._get_health_details()
            health_data.update(additional_health)
            
            return health_data
        
        @self.app.get("/")
        async def root():
            """Root Route für alle Services"""
            return {
                "service": self.service_name,
                "version": self.version,
                "status": "running",
                "endpoints": {
                    "health": "/health",
                    "docs": "/docs",
                    "openapi": "/openapi.json"
                }
            }
    
    @abstractmethod
    async def _setup_service(self):
        """Service-spezifische Setup-Logik (muss implementiert werden)"""
        pass
    
    async def _get_health_details(self) -> Dict[str, Any]:
        """Service-spezifische Health-Details (optional überschreibbar)"""
        return {}
    
    def run(self, host: str = "0.0.0.0", debug: bool = False):
        """Service starten"""
        self.logger.info(f"Starting {self.service_name} service on {host}:{self.port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=self.port,
            log_level="info" if not debug else "debug",
            access_log=True
        )


class ModularService(BaseService):
    """
    Basis-Klasse für modulare Services
    Erweitert BaseService um Modul-Management
    """
    
    def __init__(self, service_name: str, version: str = "1.0.0", port: int = 8000):
        self.modules: Dict[str, Any] = {}
        self.event_bus = None
        super().__init__(service_name, version, port)
    
    def register_module(self, module_name: str, module_instance: Any):
        """Modul registrieren"""
        self.modules[module_name] = module_instance
        self.logger.info(f"Module {module_name} registered")
    
    async def _get_health_details(self) -> Dict[str, Any]:
        """Health-Details für modulare Services"""
        module_health = {}
        for name, module in self.modules.items():
            if hasattr(module, 'get_health'):
                module_health[name] = await module.get_health()
            else:
                module_health[name] = {"status": "registered"}
        
        return {
            "modules": {
                "total": len(self.modules),
                "details": module_health
            },
            "event_bus": {
                "connected": self.event_bus is not None
            }
        }


class DatabaseMixin:
    """
    Mixin für Services mit Datenbank-Verbindung
    Eliminiert Database-Connection-Duplikation
    """
    
    def __init__(self):
        self.db_pool = None
        self.redis_client = None
    
    async def setup_postgres(self, min_size: int = 2, max_size: int = 10):
        """PostgreSQL Connection Pool Setup"""
        try:
            postgres_url = SecurityConfig.get_postgres_url()
            self.db_pool = await asyncpg.create_pool(
                postgres_url, 
                min_size=min_size, 
                max_size=max_size
            )
            self.logger.info("PostgreSQL connection pool established")
            return True
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {e}")
            return False
    
    async def setup_redis(self):
        """Redis Connection Setup"""
        try:
            import redis.asyncio as redis
            redis_url = SecurityConfig.get_redis_url()
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
            self.logger.info("Redis connection established")
            return True
        except Exception as e:
            self.logger.error(f"Redis connection failed: {e}")
            return False
    
    async def close_connections(self):
        """Alle Datenbankverbindungen schließen"""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()


class EventBusMixin:
    """
    Mixin für Services mit Event-Bus-Verbindung
    Eliminiert Event-Bus-Setup-Duplikation
    """
    
    def __init__(self):
        self.event_bus = None
        self.rabbitmq_connection = None
    
    async def setup_event_bus(self, service_name: str):
        """Event-Bus Connection Setup"""
        try:
            # Import hier um zirkuläre Imports zu vermeiden
            from ..event_bus.event_bus import EventBusConnector
            
            self.event_bus = EventBusConnector(service_name, {})
            await self.event_bus.connect()
            self.logger.info("Event-Bus connection established")
            return True
        except Exception as e:
            self.logger.error(f"Event-Bus connection failed: {e}")
            return False
    
    async def setup_rabbitmq(self):
        """RabbitMQ Connection Setup"""
        try:
            import aio_pika
            rabbitmq_url = SecurityConfig.get_rabbitmq_url()
            self.rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
            self.logger.info("RabbitMQ connection established")
            return True
        except Exception as e:
            self.logger.error(f"RabbitMQ connection failed: {e}")
            return False