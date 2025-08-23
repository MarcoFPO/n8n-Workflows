#!/usr/bin/env python3
"""
Service Base v1.0.0
Basis-Klasse für alle ML-Services

Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ServiceBase(ABC):
    """
    Abstrakte Basis-Klasse für ML-Services
    Bietet gemeinsame Funktionalität für alle Services
    """
    
    def __init__(self, service_name: str, service_port: Optional[int] = None):
        self.service_name = service_name
        self.service_port = service_port
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
        
        # Service State
        self.is_initialized = False
        self.start_time = None
        self.last_heartbeat = None
        
        # Error Tracking
        self.error_count = 0
        self.last_error = None
        self.last_error_time = None
        
        # Performance Metrics
        self.request_count = 0
        self.total_processing_time = 0.0
    
    @abstractmethod
    async def initialize_service(self) -> bool:
        """
        Initialisiert den Service
        Muss von jeder Service-Implementierung überschrieben werden
        """
        pass
    
    @abstractmethod
    async def shutdown_service(self):
        """
        Graceful Shutdown des Services
        Muss von jeder Service-Implementierung überschrieben werden
        """
        pass
    
    async def start_service(self) -> bool:
        """Startet den Service"""
        try:
            self.logger.info(f"Starting service: {self.service_name}")
            self.start_time = datetime.utcnow()
            
            # Service initialisieren
            success = await self.initialize_service()
            
            if success:
                self.is_initialized = True
                self.logger.info(f"Service {self.service_name} started successfully")
                return True
            else:
                self.logger.error(f"Failed to initialize service: {self.service_name}")
                return False
                
        except Exception as e:
            self._record_error(e)
            self.logger.error(f"Error starting service {self.service_name}: {str(e)}")
            return False
    
    async def stop_service(self):
        """Stoppt den Service"""
        try:
            self.logger.info(f"Stopping service: {self.service_name}")
            
            await self.shutdown_service()
            
            self.is_initialized = False
            self.logger.info(f"Service {self.service_name} stopped")
            
        except Exception as e:
            self._record_error(e)
            self.logger.error(f"Error stopping service {self.service_name}: {str(e)}")
    
    def _record_error(self, error: Exception):
        """Zeichnet Fehler für Monitoring auf"""
        self.error_count += 1
        self.last_error = str(error)
        self.last_error_time = datetime.utcnow()
        
        self.logger.error(f"Service error recorded: {str(error)}")
    
    def _record_request(self, processing_time: float):
        """Zeichnet Request-Metriken auf"""
        self.request_count += 1
        self.total_processing_time += processing_time
        self.last_heartbeat = datetime.utcnow()
    
    def get_uptime_seconds(self) -> float:
        """Berechnet Service-Uptime in Sekunden"""
        if not self.start_time:
            return 0.0
        
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    def get_average_processing_time(self) -> float:
        """Berechnet durchschnittliche Verarbeitungszeit"""
        if self.request_count == 0:
            return 0.0
        
        return self.total_processing_time / self.request_count
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Basis-Service-Status
        Kann von Services erweitert werden
        """
        return {
            'service_name': self.service_name,
            'service_port': self.service_port,
            'status': 'running' if self.is_initialized else 'stopped',
            'uptime_seconds': self.get_uptime_seconds(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'performance_metrics': {
                'request_count': self.request_count,
                'error_count': self.error_count,
                'avg_processing_time_ms': round(self.get_average_processing_time() * 1000, 2)
            },
            'last_error': {
                'message': self.last_error,
                'timestamp': self.last_error_time.isoformat() if self.last_error_time else None
            } if self.last_error else None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Health Check für Service
        Kann von Services erweitert werden
        """
        try:
            uptime = self.get_uptime_seconds()
            error_rate = self.error_count / max(self.request_count, 1)
            
            # Health Status bestimmen
            if not self.is_initialized:
                status = 'down'
            elif error_rate > 0.1:  # > 10% Fehlerrate
                status = 'critical'
            elif error_rate > 0.05:  # > 5% Fehlerrate
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'service_name': self.service_name,
                'status': status,
                'uptime_seconds': uptime,
                'error_rate': round(error_rate * 100, 2),
                'last_heartbeat_ago_seconds': (
                    (datetime.utcnow() - self.last_heartbeat).total_seconds()
                    if self.last_heartbeat else None
                ),
                'details': await self.get_service_status()
            }
            
        except Exception as e:
            return {
                'service_name': self.service_name,
                'status': 'critical',
                'error': str(e)
            }
    
    def log_performance(self, operation: str, duration_ms: float, success: bool = True):
        """Loggt Performance-Metriken"""
        if success:
            self.logger.debug(f"{operation} completed in {duration_ms:.1f}ms")
        else:
            self.logger.warning(f"{operation} failed after {duration_ms:.1f}ms")
        
        self._record_request(duration_ms / 1000.0)
    
    async def execute_with_metrics(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Führt Operation mit automatischem Performance-Tracking aus
        """
        start_time = time.time()
        
        try:
            result = await operation_func(*args, **kwargs)
            
            duration_ms = (time.time() - start_time) * 1000
            self.log_performance(operation_name, duration_ms, success=True)
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_performance(operation_name, duration_ms, success=False)
            self._record_error(e)
            raise
    
    def is_healthy(self) -> bool:
        """Schnelle Health-Check-Methode"""
        if not self.is_initialized:
            return False
        
        # Service ist ungesund wenn zu viele Fehler aufgetreten sind
        error_rate = self.error_count / max(self.request_count, 1)
        if error_rate > 0.1:  # > 10% Fehlerrate
            return False
        
        # Service ist ungesund wenn letzter Heartbeat zu lange her ist
        if self.last_heartbeat:
            heartbeat_age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
            if heartbeat_age > 300:  # > 5 Minuten
                return False
        
        return True
    
    async def reset_metrics(self):
        """Setzt Performance-Metriken zurück"""
        self.request_count = 0
        self.total_processing_time = 0.0
        self.error_count = 0
        self.last_error = None
        self.last_error_time = None
        
        self.logger.info(f"Metrics reset for service: {self.service_name}")
    
    def __str__(self) -> str:
        return f"Service({self.service_name}, port={self.service_port}, initialized={self.is_initialized})"
    
    def __repr__(self) -> str:
        return self.__str__()