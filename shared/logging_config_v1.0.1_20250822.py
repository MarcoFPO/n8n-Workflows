#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralized Logging Configuration für aktienanalyse-ökosystem
Eliminiert Logging-Setup-Duplikation in Services
"""

import os
import sys
import structlog
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Standard-Log-Formatierung
def setup_logging(service_name: str, log_level: str = None) -> structlog.stdlib.BoundLogger:
    """
    Zentrales Logging-Setup für alle Services
    
    Args:
        service_name: Name des Services für Log-Context
        log_level: Optional Log-Level (aus ENV wenn nicht gesetzt)
    
    Returns:
        Konfigurierter structlog Logger
    """
    
    # Log-Level aus Environment oder Parameter
    if not log_level:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Log-Verzeichnis sicherstellen
    log_dir = Path('/opt/aktienanalyse-ökosystem/logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Strukturiertes Logging konfigurieren
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.stdlib.add_logger_name,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Service-spezifischen Logger erstellen
    logger = structlog.get_logger(service_name)
    
    # Service-Context hinzufügen
    logger = logger.bind(
        service=service_name,
        environment="production",
        version="1.0.0",
        server="10.1.1.174"
    )
    
    logger.info(f"Logging initialized for {service_name}", log_level=log_level)
    
    return logger


def get_request_logger(service_name: str, request_id: str = None) -> structlog.stdlib.BoundLogger:
    """
    Request-spezifischen Logger erstellen
    
    Args:
        service_name: Name des Services
        request_id: Optional Request-ID für Tracing
    
    Returns:
        Logger mit Request-Context
    """
    logger = structlog.get_logger(service_name)
    
    context = {
        "service": service_name,
        "request_type": "api_request"
    }
    
    if request_id:
        context["request_id"] = request_id
    
    return logger.bind(**context)


def log_service_startup(logger: structlog.stdlib.BoundLogger, service_config: Dict[str, Any]):
    """
    Standard Service-Startup-Logging
    
    Args:
        logger: Service Logger
        service_config: Service-Konfiguration für Logging
    """
    logger.info(
        "Service starting up",
        **service_config,
        startup_time=datetime.now().isoformat()
    )


def log_health_check(logger: structlog.stdlib.BoundLogger, health_data: Dict[str, Any]):
    """
    Standard Health-Check-Logging
    
    Args:
        logger: Service Logger
        health_data: Health-Check-Daten
    """
    logger.info(
        "Health check performed",
        **health_data
    )


def log_database_connection(logger: structlog.stdlib.BoundLogger, db_type: str, success: bool, error: str = None):
    """
    Standard Database-Connection-Logging
    
    Args:
        logger: Service Logger
        db_type: Typ der Datenbank (postgres, redis, rabbitmq)
        success: Erfolgreich verbunden
        error: Error-Message bei Fehlschlag
    """
    if success:
        logger.info(f"{db_type} connection established", database=db_type, status="connected")
    else:
        logger.error(f"{db_type} connection failed", database=db_type, status="failed", error=error)


def log_event_bus_activity(logger: structlog.stdlib.BoundLogger, event_type: str, event_data: Dict[str, Any]):
    """
    Standard Event-Bus-Activity-Logging
    
    Args:
        logger: Service Logger
        event_type: Typ des Events
        event_data: Event-Daten
    """
    logger.info(
        "Event bus activity",
        event_type=event_type,
        **event_data
    )


class LoggerMixin:
    """
    Mixin für Services mit Standard-Logging-Funktionalität
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = setup_logging(service_name)
    
    def log_startup(self, config: Dict[str, Any]):
        """Service-Startup loggen"""
        log_service_startup(self.logger, config)
    
    def log_health(self, health_data: Dict[str, Any]):
        """Health-Check loggen"""
        log_health_check(self.logger, health_data)
    
    def log_db_connection(self, db_type: str, success: bool, error: str = None):
        """Database-Connection loggen"""
        log_database_connection(self.logger, db_type, success, error)
    
    def log_event(self, event_type: str, event_data: Dict[str, Any]):
        """Event-Bus-Activity loggen"""
        log_event_bus_activity(self.logger, event_type, event_data)


# Legacy-Support für bestehende Services
def get_logger(service_name: str):
    """Legacy-Funktion für Backwards Compatibility"""
    return setup_logging(service_name)