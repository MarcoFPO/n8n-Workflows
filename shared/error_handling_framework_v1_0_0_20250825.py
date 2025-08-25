#!/usr/bin/env python3
"""
Shared Error Handling Framework v1.0.0 - Clean Architecture
Einheitliche Fehlerbehandlung für alle Services im Aktienanalyse-Ökosystem

SHARED INFRASTRUCTURE - ERROR HANDLING:
- Konsistente Exception-Hierarchie
- Strukturierte Fehler-Responses  
- Logging-Integration mit Context
- HTTP Status Code Mapping
- Error Recovery Patterns

DESIGN PATTERNS IMPLEMENTIERT:
- Strategy Pattern: Verschiedene Error Handler
- Chain of Responsibility: Error Processing Pipeline
- Factory Pattern: Exception Creation
- Observer Pattern: Error Logging und Monitoring

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 1.0.0
"""

import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Type
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


# =============================================================================
# BASE EXCEPTION HIERARCHY
# =============================================================================

class BaseServiceError(Exception):
    """
    Basis-Exception für alle Service-Fehler
    
    Bietet einheitliche Struktur für Fehlerbehandlung mit:
    - Error Codes für maschinenlesbare Identifikation
    - HTTP Status Code Mapping
    - Context-Informationen für Debugging
    - Structured Logging Support
    """
    
    def __init__(
        self, 
        message: str,
        error_code: str = "GENERIC_ERROR",
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Exception zu Dictionary für API Response"""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None
        }
    
    def get_http_status(self) -> int:
        """Standard HTTP Status Code für diese Exception"""
        return status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# DOMAIN EXCEPTION CATEGORIES
# =============================================================================

class ValidationError(BaseServiceError):
    """Validierungsfehler - Ungültige Input-Daten"""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            context={"field": field} if field else {},
            **kwargs
        )
    
    def get_http_status(self) -> int:
        return status.HTTP_422_UNPROCESSABLE_ENTITY


class NotFoundError(BaseServiceError):
    """Resource nicht gefunden"""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="NOT_FOUND_ERROR",
            context={
                "resource_type": resource_type,
                "resource_id": resource_id
            } if resource_type else {},
            **kwargs
        )
    
    def get_http_status(self) -> int:
        return status.HTTP_404_NOT_FOUND


class DatabaseError(BaseServiceError):
    """Datenbankfehler - Connection, Query, Transaction Issues"""
    
    def __init__(self, message: str, operation: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            context={"operation": operation} if operation else {},
            **kwargs
        )
    
    def get_http_status(self) -> int:
        return status.HTTP_503_SERVICE_UNAVAILABLE


class ExternalServiceError(BaseServiceError):
    """Fehler bei externen Service-Aufrufen"""
    
    def __init__(self, message: str, service: str = None, endpoint: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR", 
            context={
                "service": service,
                "endpoint": endpoint
            } if service else {},
            **kwargs
        )
    
    def get_http_status(self) -> int:
        return status.HTTP_502_BAD_GATEWAY


class BusinessLogicError(BaseServiceError):
    """Geschäftslogik-Verletzungen"""
    
    def __init__(self, message: str, rule: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            context={"rule": rule} if rule else {},
            **kwargs
        )
    
    def get_http_status(self) -> int:
        return status.HTTP_400_BAD_REQUEST


class AuthenticationError(BaseServiceError):
    """Authentifizierungsfehler"""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            **kwargs
        )
    
    def get_http_status(self) -> int:
        return status.HTTP_401_UNAUTHORIZED


class AuthorizationError(BaseServiceError):
    """Autorisierungsfehler - Insufficient permissions"""
    
    def __init__(self, message: str = "Insufficient permissions", action: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            context={"action": action} if action else {},
            **kwargs
        )
    
    def get_http_status(self) -> int:
        return status.HTTP_403_FORBIDDEN


class ConfigurationError(BaseServiceError):
    """Service-Konfigurationsfehler"""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            context={"config_key": config_key} if config_key else {},
            **kwargs
        )


class RateLimitError(BaseServiceError):
    """Rate Limiting Fehler"""
    
    def __init__(self, message: str = "Rate limit exceeded", limit: int = None, **kwargs):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            context={"limit": limit} if limit else {},
            **kwargs
        )
    
    def get_http_status(self) -> int:
        return status.HTTP_429_TOO_MANY_REQUESTS


# =============================================================================
# ERROR HANDLER INTERFACE
# =============================================================================

class IErrorHandler(ABC):
    """Interface für Error Handler Implementierungen"""
    
    @abstractmethod
    async def handle_error(
        self, 
        error: Exception, 
        request: Optional[Request] = None
    ) -> JSONResponse:
        """Behandelt Fehler und erstellt HTTP Response"""
        pass
    
    @abstractmethod
    def can_handle(self, error: Exception) -> bool:
        """Prüft ob dieser Handler den Fehler behandeln kann"""
        pass


# =============================================================================
# CONCRETE ERROR HANDLERS
# =============================================================================

class ServiceErrorHandler(IErrorHandler):
    """Handler für BaseServiceError und Subklassen"""
    
    def can_handle(self, error: Exception) -> bool:
        return isinstance(error, BaseServiceError)
    
    async def handle_error(
        self, 
        error: BaseServiceError, 
        request: Optional[Request] = None
    ) -> JSONResponse:
        
        # Structured Logging mit Context
        logger.error(
            f"Service Error: {error.error_code}",
            extra={
                "error_code": error.error_code,
                "message": error.message,
                "context": error.context,
                "timestamp": error.timestamp.isoformat(),
                "request_path": request.url.path if request else None,
                "cause": str(error.cause) if error.cause else None
            }
        )
        
        return JSONResponse(
            status_code=error.get_http_status(),
            content=error.to_dict()
        )


class HTTPExceptionHandler(IErrorHandler):
    """Handler für FastAPI HTTPExceptions"""
    
    def can_handle(self, error: Exception) -> bool:
        return isinstance(error, HTTPException)
    
    async def handle_error(
        self, 
        error: HTTPException, 
        request: Optional[Request] = None
    ) -> JSONResponse:
        
        logger.warning(
            f"HTTP Exception: {error.status_code}",
            extra={
                "status_code": error.status_code,
                "detail": error.detail,
                "request_path": request.url.path if request else None
            }
        )
        
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": True,
                "error_code": "HTTP_ERROR",
                "message": error.detail,
                "status_code": error.status_code,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


class GenericErrorHandler(IErrorHandler):
    """Fallback-Handler für unbekannte Exceptions"""
    
    def can_handle(self, error: Exception) -> bool:
        return True  # Kann alle Fehler behandeln (Fallback)
    
    async def handle_error(
        self, 
        error: Exception, 
        request: Optional[Request] = None
    ) -> JSONResponse:
        
        # Log mit Stack Trace für unerwartete Fehler
        logger.error(
            f"Unhandled Exception: {type(error).__name__}",
            extra={
                "exception_type": type(error).__name__,
                "message": str(error),
                "request_path": request.url.path if request else None,
                "stack_trace": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error occurred",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# =============================================================================
# ERROR HANDLER CHAIN
# =============================================================================

class ErrorHandlerChain:
    """
    Chain of Responsibility für Error Handling
    
    Durchläuft registrierte Handler bis einer den Fehler behandeln kann.
    """
    
    def __init__(self):
        self.handlers: List[IErrorHandler] = [
            ServiceErrorHandler(),
            HTTPExceptionHandler(),
            GenericErrorHandler()  # Muss letzter sein (Fallback)
        ]
    
    def add_handler(self, handler: IErrorHandler, index: int = -1):
        """Fügt Handler zur Chain hinzu (vor GenericErrorHandler)"""
        if index == -1:
            # Vor dem letzten Handler (GenericErrorHandler) einfügen
            self.handlers.insert(-1, handler)
        else:
            self.handlers.insert(index, handler)
    
    async def handle_error(
        self, 
        error: Exception, 
        request: Optional[Request] = None
    ) -> JSONResponse:
        """Durchläuft Handler-Chain bis einer den Fehler behandeln kann"""
        
        for handler in self.handlers:
            if handler.can_handle(error):
                return await handler.handle_error(error, request)
        
        # Sollte nie erreicht werden wegen GenericErrorHandler
        logger.critical("No error handler could handle the error - this should never happen!")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "error_code": "CRITICAL_ERROR", 
                "message": "Critical error in error handling system"
            }
        )


# =============================================================================
# GLOBAL ERROR HANDLER INSTANCE
# =============================================================================

# Global Handler Chain (Singleton pattern)
global_error_handler = ErrorHandlerChain()


# =============================================================================
# FASTAPI INTEGRATION UTILITIES
# =============================================================================

def create_exception_handlers() -> Dict[Type[Exception], callable]:
    """
    Erstellt FastAPI Exception Handler Mapping
    
    Returns:
        Dictionary für FastAPI exception_handlers Parameter
    """
    
    async def service_error_handler(request: Request, exc: BaseServiceError):
        return await global_error_handler.handle_error(exc, request)
    
    async def http_exception_handler(request: Request, exc: HTTPException):
        return await global_error_handler.handle_error(exc, request)
    
    async def generic_exception_handler(request: Request, exc: Exception):
        return await global_error_handler.handle_error(exc, request)
    
    return {
        BaseServiceError: service_error_handler,
        HTTPException: http_exception_handler,
        Exception: generic_exception_handler
    }


def setup_error_logging(service_name: str, log_file_path: str = None):
    """
    Konfiguriert strukturiertes Logging für Service
    
    Args:
        service_name: Name des Service für Log-Context
        log_file_path: Optional log file path
    """
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handlers = [logging.StreamHandler()]
    
    if log_file_path:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Add service context to all logs
    logger = logging.getLogger()
    logger = logging.LoggerAdapter(logger, {"service": service_name})


# =============================================================================
# ERROR RECOVERY UTILITIES
# =============================================================================

class RetryPolicy:
    """Retry-Policy für fehlerhafte Operationen"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        exponential_backoff: bool = True,
        retryable_exceptions: List[Type[Exception]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.exponential_backoff = exponential_backoff
        self.retryable_exceptions = retryable_exceptions or [DatabaseError, ExternalServiceError]
    
    def is_retryable(self, error: Exception) -> bool:
        """Prüft ob Fehler retry-fähig ist"""
        return any(isinstance(error, exc_type) for exc_type in self.retryable_exceptions)
    
    def get_delay(self, attempt: int) -> float:
        """Berechnet Delay für Retry-Attempt"""
        if self.exponential_backoff:
            return self.base_delay * (2 ** (attempt - 1))
        return self.base_delay


async def retry_operation(
    operation: callable,
    policy: RetryPolicy,
    *args,
    **kwargs
):
    """
    Führt Operation mit Retry-Logic aus
    
    Args:
        operation: Async function to retry
        policy: RetryPolicy configuration
        *args, **kwargs: Arguments for operation
    
    Returns:
        Result of successful operation
    
    Raises:
        Last exception if all retries failed
    """
    
    last_error = None
    
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            if not policy.is_retryable(e) or attempt == policy.max_attempts:
                raise e
            
            delay = policy.get_delay(attempt)
            logger.warning(
                f"Operation failed (attempt {attempt}/{policy.max_attempts}), retrying in {delay}s",
                extra={
                    "attempt": attempt,
                    "max_attempts": policy.max_attempts,
                    "delay": delay,
                    "error": str(e)
                }
            )
            
            import asyncio
            await asyncio.sleep(delay)
    
    # Sollte nie erreicht werden
    raise last_error


# =============================================================================
# HEALTH CHECK ERROR INDICATORS
# =============================================================================

class HealthStatus(Enum):
    """Health Status Enum für Service Health Checks"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


def get_health_status(errors: List[Exception]) -> HealthStatus:
    """
    Bestimmt Health Status basierend auf aufgetretenen Fehlern
    
    Args:
        errors: Liste der aufgetretenen Fehler
    
    Returns:
        HealthStatus basierend auf Error-Analyse
    """
    
    if not errors:
        return HealthStatus.HEALTHY
    
    # Kritische Fehler = UNHEALTHY
    critical_errors = [DatabaseError, ConfigurationError]
    if any(isinstance(error, tuple(critical_errors)) for error in errors):
        return HealthStatus.UNHEALTHY
    
    # Degradierte Fehler = DEGRADED
    degraded_errors = [ExternalServiceError, RateLimitError]
    if any(isinstance(error, tuple(degraded_errors)) for error in errors):
        return HealthStatus.DEGRADED
    
    # Andere Fehler = DEGRADED
    return HealthStatus.DEGRADED