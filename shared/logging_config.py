"""
Centralized logging configuration for Aktienanalyse-Ökosystem
Eliminates duplicate logging setup across services
"""

import os
import sys
import structlog
from typing import Optional, Dict, Any
import logging.config


class LoggingConfig:
    """Centralized logging configuration"""
    
    def __init__(self, service_name: str = "aktienanalyse-service"):
        self.service_name = service_name
        self.log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "json").lower()
        self.log_retention_days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
        
    def configure_structlog(self) -> None:
        """Configure structlog with consistent settings"""
        
        # Choose processors based on format
        if self.log_format == "json":
            processors = [
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                self._add_service_info,
                structlog.processors.JSONRenderer()
            ]
        else:
            # Human-readable format for development
            processors = [
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                self._add_service_info,
                structlog.dev.ConsoleRenderer()
            ]
        
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, self.log_level, logging.INFO),
        )
    
    def _add_service_info(self, logger, name, event_dict):
        """Add service information to log entries"""
        event_dict["service"] = self.service_name
        event_dict["version"] = os.getenv("APP_VERSION", "1.0.0")
        event_dict["environment"] = os.getenv("APP_ENV", "development")
        return event_dict
    
    def configure_uvicorn_logging(self) -> Dict[str, Any]:
        """Configure uvicorn logging to match structlog"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(message)s",
                    "use_colors": None,
                },
                "access": {
                    "()": "uvicorn.logging.AccessFormatter",
                    "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": self.log_level},
                "uvicorn.error": {"level": self.log_level},
                "uvicorn.access": {"handlers": ["access"], "level": self.log_level, "propagate": False},
            },
        }


class ServiceLogger:
    """Service-specific logger with context"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = structlog.get_logger(service_name)
        
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        return self.logger.info(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        return self.logger.error(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        return self.logger.warning(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        return self.logger.debug(message, **kwargs)
    
    def bind(self, **kwargs) -> 'ServiceLogger':
        """Bind additional context to logger"""
        bound_logger = self.logger.bind(**kwargs)
        new_service_logger = ServiceLogger(self.service_name)
        new_service_logger.logger = bound_logger
        return new_service_logger


class SecurityLogger:
    """Security-specific logging"""
    
    def __init__(self, service_name: str):
        self.logger = ServiceLogger(f"{service_name}.security")
    
    def log_authentication_attempt(self, user_id: str, success: bool, ip_address: str):
        """Log authentication attempt"""
        self.logger.info(
            "Authentication attempt",
            user_id=user_id,
            success=success,
            ip_address=ip_address,
            event_type="auth_attempt"
        )
    
    def log_rate_limit_exceeded(self, client_id: str, ip_address: str, endpoint: str):
        """Log rate limit exceeded"""
        self.logger.warning(
            "Rate limit exceeded",
            client_id=client_id,
            ip_address=ip_address,
            endpoint=endpoint,
            event_type="rate_limit_exceeded"
        )
    
    def log_suspicious_activity(self, description: str, ip_address: str, **kwargs):
        """Log suspicious activity"""
        self.logger.error(
            "Suspicious activity detected",
            description=description,
            ip_address=ip_address,
            event_type="suspicious_activity",
            **kwargs
        )
    
    def log_input_validation_error(self, input_type: str, value: str, error: str, ip_address: str):
        """Log input validation error"""
        self.logger.warning(
            "Input validation error",
            input_type=input_type,
            value=value[:100],  # Truncate for safety
            error=error,
            ip_address=ip_address,
            event_type="input_validation_error"
        )


class PerformanceLogger:
    """Performance and metrics logging"""
    
    def __init__(self, service_name: str):
        self.logger = ServiceLogger(f"{service_name}.performance")
    
    def log_request_duration(self, endpoint: str, method: str, duration_ms: float, 
                           status_code: int, user_id: str = None):
        """Log request performance"""
        self.logger.info(
            "Request completed",
            endpoint=endpoint,
            method=method,
            duration_ms=duration_ms,
            status_code=status_code,
            user_id=user_id,
            event_type="request_performance"
        )
    
    def log_database_query(self, query_type: str, duration_ms: float, row_count: int = None):
        """Log database query performance"""
        self.logger.debug(
            "Database query executed",
            query_type=query_type,
            duration_ms=duration_ms,
            row_count=row_count,
            event_type="db_query_performance"
        )
    
    def log_external_api_call(self, api_name: str, endpoint: str, duration_ms: float, 
                            status_code: int, error: str = None):
        """Log external API call performance"""
        self.logger.info(
            "External API call",
            api_name=api_name,
            endpoint=endpoint,
            duration_ms=duration_ms,
            status_code=status_code,
            error=error,
            event_type="external_api_performance"
        )


# Convenience functions for quick setup
def setup_logging(service_name: str) -> ServiceLogger:
    """Setup logging for a service"""
    config = LoggingConfig(service_name)
    config.configure_structlog()
    return ServiceLogger(service_name)


def setup_security_logging(service_name: str) -> SecurityLogger:
    """Setup security logging for a service"""
    config = LoggingConfig(service_name)
    config.configure_structlog()
    return SecurityLogger(service_name)


def setup_performance_logging(service_name: str) -> PerformanceLogger:
    """Setup performance logging for a service"""
    config = LoggingConfig(service_name)
    config.configure_structlog()
    return PerformanceLogger(service_name)


def get_uvicorn_log_config(service_name: str) -> Dict[str, Any]:
    """Get uvicorn logging configuration"""
    config = LoggingConfig(service_name)
    return config.configure_uvicorn_logging()