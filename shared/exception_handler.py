"""
Exception-Handler-Framework für strukturierte Fehlerbehandlung

Bietet Decorators und Handler-Klassen für einheitliche Exception-Behandlung
mit automatischem Rollback, Recovery-Patterns und strukturiertem Logging.

Author: System Modernization Team  
Version: 1.0.0
Date: 2025-08-29
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Dict, Optional, Type, Union, List
from contextlib import asynccontextmanager, contextmanager
import inspect

from .exceptions import (
    BaseServiceException, 
    DatabaseException, 
    EventBusException,
    ExternalAPIException,
    ValidationException,
    ConfigurationException,
    BusinessLogicException,
    NetworkException,
    AuthenticationException,
    ErrorSeverity,
    RecoveryStrategy,
    handle_exception_with_recovery,
    log_exception_metrics,
    get_error_response
)

# Logger für Exception-Handler
logger = logging.getLogger(__name__)


class ExceptionHandlerConfig:
    """Konfiguration für Exception-Handler"""
    
    def __init__(
        self,
        log_exceptions: bool = True,
        raise_on_unhandled: bool = True,
        default_recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
        rollback_on_error: bool = True,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        metrics_enabled: bool = True
    ):
        self.log_exceptions = log_exceptions
        self.raise_on_unhandled = raise_on_unhandled
        self.default_recovery_strategy = default_recovery_strategy
        self.rollback_on_error = rollback_on_error
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.metrics_enabled = metrics_enabled


class ExceptionHandler:
    """Zentrale Exception-Handler-Klasse"""
    
    def __init__(self, config: Optional[ExceptionHandlerConfig] = None):
        self.config = config or ExceptionHandlerConfig()
        self._circuit_breaker_counts = {}
        self._rollback_handlers = []
    
    def register_rollback_handler(self, handler: Callable[[], None]):
        """Registriert einen Rollback-Handler"""
        self._rollback_handlers.append(handler)
    
    def clear_rollback_handlers(self):
        """Löscht alle Rollback-Handler"""
        self._rollback_handlers.clear()
    
    async def execute_rollback(self):
        """Führt alle registrierten Rollback-Handler aus"""
        for handler in reversed(self._rollback_handlers):  # LIFO order
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
                logger.info(f"Rollback handler executed: {handler.__name__}")
            except Exception as e:
                logger.error(f"Rollback handler failed: {handler.__name__}: {e}")
    
    def handle_exception(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None,
        recovery_func: Optional[Callable] = None
    ) -> Any:
        """
        Behandelt eine Exception mit der konfigurierten Strategie
        
        Args:
            exc: Die aufgetretene Exception
            context: Zusätzlicher Kontext
            recovery_func: Recovery-Funktion
            
        Returns:
            Ergebnis der Recovery-Funktion oder None
        """
        # Konvertiere zu BaseServiceException falls nötig
        if not isinstance(exc, BaseServiceException):
            exc = self._convert_to_service_exception(exc, context)
        
        # Logging
        if self.config.log_exceptions:
            logger.error(f"Exception handled: {exc.message}", 
                        extra={"error_code": exc.error_code, "context": context})
        
        # Metriken
        if self.config.metrics_enabled:
            log_exception_metrics(exc)
        
        # Circuit Breaker Check
        if self._should_circuit_break(exc):
            logger.warning("Circuit breaker activated - stopping operation")
            raise exc
        
        # Rollback wenn erforderlich
        if exc.rollback_required and self.config.rollback_on_error:
            # Prüfe ob wir in einem Event-Loop sind
            try:
                loop = asyncio.get_running_loop()
                # Falls in Event-Loop, erstelle Task
                asyncio.create_task(self.execute_rollback())
            except RuntimeError:
                # Falls kein Event-Loop, führe synchron aus (für Tests)
                asyncio.run(self.execute_rollback())
        
        # Recovery versuchen
        try:
            return handle_exception_with_recovery(exc, recovery_func)
        except BaseServiceException:
            if self.config.raise_on_unhandled:
                raise
            return None
    
    def _convert_to_service_exception(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> BaseServiceException:
        """Konvertiert Standard-Exception zu BaseServiceException"""
        
        # Stelle sicher dass Context vorhanden ist
        context = context or {}
        
        # Füge recovery_strategy zum Context hinzu falls nicht vorhanden
        if 'recovery_strategy' not in context:
            context['recovery_strategy'] = self.config.default_recovery_strategy
        
        # Exception-Type-Mapping
        exception_mapping = {
            ValueError: ValidationException,
            TypeError: ValidationException,
            ConnectionError: NetworkException,
            TimeoutError: NetworkException,
            PermissionError: AuthenticationException,
            FileNotFoundError: ConfigurationException
        }
        
        exc_class = exception_mapping.get(type(exc), BaseServiceException)
        
        return exc_class(
            message=str(exc),
            context=context,
            cause=exc,
            recovery_strategy=self.config.default_recovery_strategy,
            max_retries=self.config.max_retries
        )
    
    def _should_circuit_break(self, exc: BaseServiceException) -> bool:
        """Prüft ob Circuit Breaker aktiviert werden soll"""
        if exc.recovery_strategy != RecoveryStrategy.CIRCUIT_BREAKER:
            return False
        
        error_key = f"{exc.category.value}:{type(exc).__name__}"
        
        self._circuit_breaker_counts[error_key] = (
            self._circuit_breaker_counts.get(error_key, 0) + 1
        )
        
        return self._circuit_breaker_counts[error_key] >= self.config.circuit_breaker_threshold


# Globaler Exception-Handler
_global_handler = ExceptionHandler()


def configure_exception_handler(config: ExceptionHandlerConfig):
    """Konfiguriert den globalen Exception-Handler"""
    global _global_handler
    _global_handler = ExceptionHandler(config)


def get_exception_handler() -> ExceptionHandler:
    """Gibt den globalen Exception-Handler zurück"""
    return _global_handler


# =============================================================================
# DECORATORS
# =============================================================================

def exception_handler(
    exceptions: Union[Type[Exception], List[Type[Exception]], None] = None,
    recovery_func: Optional[Callable] = None,
    rollback_on_error: bool = True,
    log_exceptions: bool = True,
    raise_on_unhandled: bool = True
):
    """
    Decorator für strukturierte Exception-Behandlung
    
    Args:
        exceptions: Exception-Typen die behandelt werden sollen (None = alle)
        recovery_func: Recovery-Funktion bei Fehlern
        rollback_on_error: Ob bei Fehlern Rollback ausgeführt werden soll
        log_exceptions: Ob Exceptions geloggt werden sollen
        raise_on_unhandled: Ob unbehandelte Exceptions re-raised werden sollen
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            handler = get_exception_handler()
            
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                # Prüfe ob Exception behandelt werden soll
                if exceptions and not isinstance(exc, exceptions):
                    raise
                
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args": str(args)[:200],  # Begrenzt für Logging
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
                }
                
                return handler.handle_exception(exc, context, recovery_func)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            handler = get_exception_handler()
            
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                # Prüfe ob Exception behandelt werden soll
                if exceptions and not isinstance(exc, exceptions):
                    raise
                
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args": str(args)[:200],
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
                }
                
                return handler.handle_exception(exc, context, recovery_func)
        
        # Wähle den passenden Wrapper basierend auf Funktions-Type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def database_exception_handler(
    rollback_transaction: bool = True,
    max_retries: int = 3
):
    """Spezialisierter Decorator für Database-Exceptions"""
    
    def decorator(func: Callable) -> Callable:
        return exception_handler(
            exceptions=[DatabaseException, ConnectionError, Exception],
            rollback_on_error=rollback_transaction,
            recovery_func=lambda: None  # Kann durch Service überschrieben werden
        )(func)
    
    return decorator


def event_bus_exception_handler(
    fallback_func: Optional[Callable] = None
):
    """Spezialisierter Decorator für Event-Bus-Exceptions"""
    
    def decorator(func: Callable) -> Callable:
        return exception_handler(
            exceptions=[EventBusException],
            recovery_func=fallback_func,
            rollback_on_error=False
        )(func)
    
    return decorator


def api_exception_handler(
    timeout_seconds: int = 30,
    max_retries: int = 3
):
    """Spezialisierter Decorator für API-Exceptions"""
    
    def decorator(func: Callable) -> Callable:
        return exception_handler(
            exceptions=[ExternalAPIException, NetworkException],
            rollback_on_error=False
        )(func)
    
    return decorator


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

@contextmanager
def exception_context(
    handler: Optional[ExceptionHandler] = None,
    rollback_func: Optional[Callable] = None
):
    """
    Context Manager für Exception-Behandlung mit automatischem Rollback
    
    Args:
        handler: Spezifischer Exception-Handler (optional)
        rollback_func: Rollback-Funktion
    """
    _handler = handler or get_exception_handler()
    
    if rollback_func:
        _handler.register_rollback_handler(rollback_func)
    
    try:
        yield _handler
    except BaseServiceException as exc:
        _handler.handle_exception(exc)
        raise
    finally:
        if rollback_func:
            _handler.clear_rollback_handlers()


@asynccontextmanager
async def async_exception_context(
    handler: Optional[ExceptionHandler] = None,
    rollback_func: Optional[Callable] = None
):
    """Async Context Manager für Exception-Behandlung"""
    _handler = handler or get_exception_handler()
    
    if rollback_func:
        _handler.register_rollback_handler(rollback_func)
    
    try:
        yield _handler
    except BaseServiceException as exc:
        _handler.handle_exception(exc)
        raise
    finally:
        if rollback_func:
            await _handler.execute_rollback()
            _handler.clear_rollback_handlers()


# =============================================================================
# TRANSACTION ROLLBACK SUPPORT
# =============================================================================

class TransactionManager:
    """Manager für Transaktions-Rollback-Support"""
    
    def __init__(self):
        self._transaction_stack = []
        self._rollback_handlers = []
    
    def begin_transaction(self, transaction_id: str):
        """Startet eine neue Transaktion"""
        self._transaction_stack.append(transaction_id)
        logger.debug(f"Transaction started: {transaction_id}")
    
    def commit_transaction(self, transaction_id: str):
        """Committet eine Transaktion"""
        if transaction_id in self._transaction_stack:
            self._transaction_stack.remove(transaction_id)
            logger.debug(f"Transaction committed: {transaction_id}")
    
    def rollback_transaction(self, transaction_id: str):
        """Rollt eine Transaktion zurück"""
        if transaction_id in self._transaction_stack:
            self._transaction_stack.remove(transaction_id)
            
            # Führe Rollback-Handler aus
            for handler in reversed(self._rollback_handlers):
                try:
                    handler(transaction_id)
                except Exception as e:
                    logger.error(f"Rollback handler failed: {e}")
            
            logger.info(f"Transaction rolled back: {transaction_id}")
    
    def register_rollback_handler(self, handler: Callable[[str], None]):
        """Registriert einen Rollback-Handler"""
        self._rollback_handlers.append(handler)
    
    def has_active_transactions(self) -> bool:
        """Prüft ob aktive Transaktionen vorhanden sind"""
        return len(self._transaction_stack) > 0
    
    def get_active_transactions(self) -> List[str]:
        """Gibt Liste aktiver Transaktionen zurück"""
        return self._transaction_stack.copy()


# Globaler Transaction-Manager
_transaction_manager = TransactionManager()


def get_transaction_manager() -> TransactionManager:
    """Gibt den globalen Transaction-Manager zurück"""
    return _transaction_manager


# =============================================================================
# FASTAPI INTEGRATION
# =============================================================================

def create_fastapi_exception_handler():
    """
    Erstellt einen FastAPI-kompatiblen Exception-Handler
    
    Returns:
        FastAPI Exception-Handler-Function
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse
    
    async def fastapi_exception_handler(request: Request, exc: BaseServiceException):
        """FastAPI Exception-Handler"""
        
        logger.error(
            f"FastAPI Exception: {exc.message}",
            extra={
                "url": str(request.url),
                "method": request.method,
                "error_code": exc.error_code
            }
        )
        
        return JSONResponse(
            status_code=exc.http_status_code,
            content=get_error_response(exc)
        )
    
    return fastapi_exception_handler


# =============================================================================
# UTILITY FUNCTIONS  
# =============================================================================

def wrap_function_with_exception_handling(
    func: Callable,
    exception_types: Optional[List[Type[Exception]]] = None,
    recovery_func: Optional[Callable] = None
) -> Callable:
    """
    Wrapped eine Funktion mit Exception-Handling
    
    Args:
        func: Die zu wrappende Funktion
        exception_types: Exception-Typen die behandelt werden sollen
        recovery_func: Recovery-Funktion
        
    Returns:
        Gewrappte Funktion
    """
    return exception_handler(
        exceptions=exception_types,
        recovery_func=recovery_func
    )(func)


def create_exception_from_error(
    error: Any,
    error_type: str = "general",
    context: Optional[Dict[str, Any]] = None
) -> BaseServiceException:
    """
    Erstellt eine BaseServiceException aus einem beliebigen Error
    
    Args:
        error: Der ursprüngliche Error
        error_type: Type des Errors für Mapping
        context: Zusätzlicher Kontext
        
    Returns:
        BaseServiceException
    """
    from .exceptions import ExceptionFactory
    
    if isinstance(error, BaseServiceException):
        return error
    
    message = str(error)
    
    # Error-Type-Mapping
    if "database" in error_type.lower() or "connection" in str(error).lower():
        return ExceptionFactory.create_database_exception("connection", message, context=context)
    elif "event" in error_type.lower():
        return ExceptionFactory.create_event_bus_exception("publish", message, context=context)
    elif "api" in error_type.lower():
        return ExceptionFactory.create_api_exception("general", message, context=context)
    else:
        return BaseServiceException(message, context=context, cause=error)