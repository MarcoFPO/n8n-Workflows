"""
Umfassendes Exception-Handling-Framework für das Aktienanalyse-Ökosystem

Dieses Modul implementiert eine hierarchische Exception-Struktur zur Eliminierung
von generischen Exception-Catches und bietet strukturierte Fehlerbehandlung
mit HTTP-Status-Code-Mapping, Rollback-Support und Recovery-Patterns.

Author: System Modernization Team
Version: 1.0.0
Date: 2025-08-29
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
import logging
import traceback
from datetime import datetime

# Logger für Exception-Framework
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Schweregrade von Exceptions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Kategorien von Exceptions"""
    DATABASE = "database"
    NETWORK = "network"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    CONFIGURATION = "configuration"
    EXTERNAL_API = "external_api"
    SYSTEM = "system"


class RecoveryStrategy(Enum):
    """Recovery-Strategien für Exceptions"""
    NONE = "none"
    RETRY = "retry"
    FALLBACK = "fallback"
    ROLLBACK = "rollback"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"


class BaseServiceException(Exception):
    """
    Basis-Exception für alle Service-spezifischen Fehler
    
    Bietet strukturierte Fehlerbehandlung mit:
    - HTTP-Status-Code-Mapping
    - Benutzer- und Entwickler-Nachrichten
    - Contextuelle Informationen
    - Recovery-Strategien
    - Logging-Integration
    """
    
    def __init__(
        self,
        message: str,
        *,
        user_message: Optional[str] = None,
        error_code: Optional[str] = None,
        http_status_code: int = 500,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        rollback_required: bool = False,
        retry_count: int = 0,
        max_retries: int = 3
    ):
        super().__init__(message)
        
        self.message = message
        self.user_message = user_message or "Ein unerwarteter Fehler ist aufgetreten."
        self.http_status_code = http_status_code
        self.severity = severity
        self.category = category
        self.recovery_strategy = recovery_strategy
        self.context = context or {}
        self.cause = cause
        self.rollback_required = rollback_required
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()
        
        # Error-Code nach allen anderen Attributen generieren
        self.error_code = error_code or self._generate_error_code()
        
        # Automatisches Logging basierend auf Schweregrad
        self._auto_log()
    
    def _generate_error_code(self) -> str:
        """Generiert einen eindeutigen Error-Code"""
        return f"{self.__class__.__name__.upper()}_{self.category.value.upper()}_{int(self.timestamp.timestamp())}"
    
    def _auto_log(self):
        """Automatisches Logging basierend auf Schweregrad"""
        log_data = {
            "error_code": self.error_code,
            "error_message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "http_status": self.http_status_code,
            "context": self.context,
            "recovery_strategy": self.recovery_strategy.value
        }
        
        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR: {self.message}", extra=log_data)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY: {self.message}", extra=log_data)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY: {self.message}", extra=log_data)
        else:
            logger.info(f"LOW SEVERITY: {self.message}", extra=log_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Exception zu Dictionary für API-Responses"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "recovery_strategy": self.recovery_strategy.value,
            "http_status_code": self.http_status_code
        }
    
    def can_retry(self) -> bool:
        """Prüft ob Retry möglich ist"""
        return (
            self.recovery_strategy == RecoveryStrategy.RETRY and
            self.retry_count < self.max_retries
        )
    
    def increment_retry(self):
        """Erhöht Retry-Counter"""
        self.retry_count += 1


# =============================================================================
# DATABASE EXCEPTIONS
# =============================================================================

class DatabaseException(BaseServiceException):
    """Basis-Exception für Datenbankfehler"""
    
    def __init__(self, message: str, **kwargs):
        # Setze Defaults falls nicht überschrieben
        kwargs.setdefault('category', ErrorCategory.DATABASE)
        kwargs.setdefault('http_status_code', 500)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.RETRY)
        kwargs.setdefault('rollback_required', True)
        
        super().__init__(message, **kwargs)


class ConnectionException(DatabaseException):
    """Exception für Datenbankverbindungsfehler"""
    
    def __init__(self, message: str = "Datenbankverbindung fehlgeschlagen", **kwargs):
        super().__init__(
            message,
            user_message="Temporäre Datenbankprobleme. Bitte versuchen Sie es später erneut.",
            http_status_code=503,
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.CIRCUIT_BREAKER,
            **kwargs
        )


class QueryException(DatabaseException):
    """Exception für fehlerhafte Datenbankabfragen"""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        context = kwargs.pop('context', {})
        if query:
            context['failed_query'] = query
        
        super().__init__(
            message,
            user_message="Fehler beim Verarbeiten der Datenanfrage.",
            http_status_code=500,
            severity=ErrorSeverity.HIGH,
            context=context,
            **kwargs
        )


class TransactionException(DatabaseException):
    """Exception für Transaktionsfehler"""
    
    def __init__(self, message: str = "Transaktionsfehler aufgetreten", **kwargs):
        super().__init__(
            message,
            user_message="Transaktion konnte nicht abgeschlossen werden.",
            http_status_code=500,
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.ROLLBACK,
            rollback_required=True,
            **kwargs
        )


class DataIntegrityException(DatabaseException):
    """Exception für Datenintegritätsfehler"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Datenintegrität verletzt. Operation abgebrochen.",
            http_status_code=409,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.ROLLBACK,
            rollback_required=True,
            **kwargs
        )


# =============================================================================
# EVENT BUS EXCEPTIONS
# =============================================================================

class EventBusException(BaseServiceException):
    """Basis-Exception für Event-Bus-Fehler"""
    
    def __init__(self, message: str, **kwargs):
        # Setze Defaults nur wenn nicht bereits in kwargs vorhanden
        kwargs.setdefault('category', ErrorCategory.SYSTEM)
        kwargs.setdefault('http_status_code', 500)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        
        super().__init__(message, **kwargs)


class PublishException(EventBusException):
    """Exception für Event-Publishing-Fehler"""
    
    def __init__(self, message: str, event_type: Optional[str] = None, **kwargs):
        context = kwargs.pop('context', {})
        if event_type:
            context['event_type'] = event_type
        
        # Setze spezifische Defaults für PublishException
        kwargs.setdefault('user_message', "Event konnte nicht publiziert werden.")
        kwargs.setdefault('http_status_code', 500)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.RETRY)
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


class SubscribeException(EventBusException):
    """Exception für Event-Subscription-Fehler"""
    
    def __init__(self, message: str, subscription_id: Optional[str] = None, **kwargs):
        context = kwargs.pop('context', {})
        if subscription_id:
            context['subscription_id'] = subscription_id
        
        # Setze spezifische Defaults für SubscribeException
        kwargs.setdefault('user_message', "Event-Subscription konnte nicht erstellt werden.")
        kwargs.setdefault('http_status_code', 500)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.FALLBACK)
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


class EventRoutingException(EventBusException):
    """Exception für Event-Routing-Fehler"""
    
    def __init__(self, message: str, routing_rule: Optional[str] = None, **kwargs):
        context = kwargs.pop('context', {})
        if routing_rule:
            context['routing_rule'] = routing_rule
        
        # Setze spezifische Defaults für EventRoutingException
        kwargs.setdefault('user_message', "Event-Routing fehlgeschlagen.")
        kwargs.setdefault('http_status_code', 500)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.FALLBACK)
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


# =============================================================================
# EXTERNAL API EXCEPTIONS
# =============================================================================

class ExternalAPIException(BaseServiceException):
    """Basis-Exception für externe API-Fehler"""
    
    def __init__(self, message: str, **kwargs):
        # Setze Defaults nur wenn nicht bereits in kwargs vorhanden
        kwargs.setdefault('category', ErrorCategory.EXTERNAL_API)
        kwargs.setdefault('http_status_code', 502)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.RETRY)
        
        super().__init__(message, **kwargs)


class RateLimitException(ExternalAPIException):
    """Exception für API-Rate-Limit-Fehler"""
    
    def __init__(self, message: str = "API-Rate-Limit erreicht", **kwargs):
        # Setze spezifische Defaults für RateLimitException
        kwargs.setdefault('user_message', "Service temporär nicht verfügbar. Bitte versuchen Sie es später erneut.")
        kwargs.setdefault('http_status_code', 429)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.CIRCUIT_BREAKER)
        
        super().__init__(message, **kwargs)


class AuthenticationException(ExternalAPIException):
    """Exception für API-Authentifizierungsfehler"""
    
    def __init__(self, message: str = "API-Authentifizierung fehlgeschlagen", **kwargs):
        # Setze spezifische Defaults für AuthenticationException
        kwargs.setdefault('user_message', "Authentifizierungsfehler. Bitte wenden Sie sich an den Support.")
        kwargs.setdefault('http_status_code', 401)
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.NONE)
        
        super().__init__(message, **kwargs)


# =============================================================================
# VALIDATION EXCEPTIONS
# =============================================================================

class ValidationException(BaseServiceException):
    """Exception für Validierungsfehler"""
    
    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        context = kwargs.pop('context', {})
        if field_errors:
            context['field_errors'] = field_errors
        
        # Setze spezifische Defaults für ValidationException
        kwargs.setdefault('user_message', "Eingabedaten sind ungültig. Bitte prüfen Sie Ihre Eingabe.")
        kwargs.setdefault('category', ErrorCategory.VALIDATION)
        kwargs.setdefault('http_status_code', 400)
        kwargs.setdefault('severity', ErrorSeverity.LOW)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.NONE)
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


# =============================================================================
# CONFIGURATION EXCEPTIONS
# =============================================================================

class ConfigurationException(BaseServiceException):
    """Exception für Konfigurationsfehler"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        context = kwargs.pop('context', {})
        if config_key:
            context['config_key'] = config_key
        
        super().__init__(
            message,
            user_message="Systemkonfigurationsfehler. Service nicht verfügbar.",
            category=ErrorCategory.CONFIGURATION,
            http_status_code=503,
            severity=ErrorSeverity.CRITICAL,
            recovery_strategy=RecoveryStrategy.NONE,
            context=context,
            **kwargs
        )


# =============================================================================
# BUSINESS LOGIC EXCEPTIONS
# =============================================================================

class BusinessLogicException(BaseServiceException):
    """Exception für Business-Logic-Fehler"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.BUSINESS_LOGIC,
            http_status_code=422,
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.NONE,
            **kwargs
        )


# =============================================================================
# NETWORK EXCEPTIONS
# =============================================================================

class NetworkException(BaseServiceException):
    """Exception für Netzwerkfehler"""
    
    def __init__(self, message: str, **kwargs):
        # Setze Defaults nur wenn nicht bereits in kwargs vorhanden
        kwargs.setdefault('user_message', "Netzwerkfehler. Bitte versuchen Sie es später erneut.")
        kwargs.setdefault('category', ErrorCategory.NETWORK)
        kwargs.setdefault('http_status_code', 503)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.RETRY)
        
        super().__init__(message, **kwargs)


class TimeoutException(NetworkException):
    """Exception für Timeout-Fehler"""
    
    def __init__(self, message: str = "Request-Timeout", timeout_duration: Optional[float] = None, **kwargs):
        context = kwargs.pop('context', {})
        if timeout_duration:
            context['timeout_duration'] = timeout_duration
        
        # Setze spezifische Defaults für TimeoutException
        kwargs.setdefault('user_message', "Anfrage dauert zu lange. Bitte versuchen Sie es erneut.")
        kwargs.setdefault('http_status_code', 408)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('recovery_strategy', RecoveryStrategy.RETRY)
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


# =============================================================================
# HTTP STATUS CODE MAPPING
# =============================================================================

def get_http_status_for_exception(exc: BaseServiceException) -> int:
    """
    Ermittelt den passenden HTTP-Status-Code für eine Exception
    
    Args:
        exc: Die Exception
        
    Returns:
        HTTP-Status-Code
    """
    return exc.http_status_code


def get_error_response(exc: BaseServiceException) -> Dict[str, Any]:
    """
    Erstellt eine standardisierte Error-Response für APIs
    
    Args:
        exc: Die Exception
        
    Returns:
        Dictionary mit Error-Response-Daten
    """
    return {
        "success": False,
        "error": exc.to_dict(),
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# EXCEPTION FACTORY
# =============================================================================

class ExceptionFactory:
    """Factory-Klasse zur Erstellung von Exceptions basierend auf Context"""
    
    @staticmethod
    def create_database_exception(
        error_type: str,
        message: str,
        **kwargs
    ) -> DatabaseException:
        """Erstellt eine Database-Exception basierend auf Error-Type"""
        
        exception_map = {
            'connection': ConnectionException,
            'query': QueryException,
            'transaction': TransactionException,
            'integrity': DataIntegrityException
        }
        
        exc_class = exception_map.get(error_type.lower(), DatabaseException)
        return exc_class(message, **kwargs)
    
    @staticmethod
    def create_event_bus_exception(
        error_type: str,
        message: str,
        **kwargs
    ) -> EventBusException:
        """Erstellt eine Event-Bus-Exception basierend auf Error-Type"""
        
        exception_map = {
            'publish': PublishException,
            'subscribe': SubscribeException,
            'routing': EventRoutingException
        }
        
        exc_class = exception_map.get(error_type.lower(), EventBusException)
        return exc_class(message, **kwargs)
    
    @staticmethod
    def create_api_exception(
        error_type: str,
        message: str,
        **kwargs
    ) -> ExternalAPIException:
        """Erstellt eine API-Exception basierend auf Error-Type"""
        
        exception_map = {
            'rate_limit': RateLimitException,
            'authentication': AuthenticationException
        }
        
        exc_class = exception_map.get(error_type.lower(), ExternalAPIException)
        return exc_class(message, **kwargs)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def handle_exception_with_recovery(
    exc: BaseServiceException,
    recovery_func: Optional[callable] = None
) -> Any:
    """
    Behandelt Exception mit Recovery-Strategy
    
    Args:
        exc: Die Exception
        recovery_func: Recovery-Funktion (optional)
        
    Returns:
        Ergebnis der Recovery-Funktion oder None
    """
    if exc.recovery_strategy == RecoveryStrategy.RETRY and exc.can_retry():
        exc.increment_retry()
        logger.info(f"Retrying operation (attempt {exc.retry_count}/{exc.max_retries})")
        return recovery_func() if recovery_func else None
    
    elif exc.recovery_strategy == RecoveryStrategy.FALLBACK and recovery_func:
        logger.info("Executing fallback strategy")
        return recovery_func()
    
    elif exc.recovery_strategy == RecoveryStrategy.ROLLBACK:
        logger.warning("Rollback required - transaction will be rolled back")
        # Rollback-Logic wird in Service-spezifischen Implementierungen behandelt
        return None
    
    else:
        # Re-raise wenn keine Recovery-Strategy verfügbar ist
        raise exc


def log_exception_metrics(exc: BaseServiceException):
    """
    Loggt Exception-Metriken für Monitoring
    
    Args:
        exc: Die Exception
    """
    logger.info(
        "Exception metrics",
        extra={
            "metric_type": "exception",
            "error_code": exc.error_code,
            "category": exc.category.value,
            "severity": exc.severity.value,
            "recovery_strategy": exc.recovery_strategy.value,
            "http_status": exc.http_status_code,
            "retry_count": exc.retry_count
        }
    )