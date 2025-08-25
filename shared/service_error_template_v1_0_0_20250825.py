#!/usr/bin/env python3
"""
Service Error Handling Template v1.0.0 - Clean Architecture
Wiederverwendbares Template für einheitliches Error Handling in Services

SHARED TEMPLATE - ERROR HANDLING INTEGRATION:
- FastAPI Application Setup mit Error Framework
- Standardisierte Exception Handler Registration
- Logging-Integration für Service Context
- Template für Service-spezifische Exception-Definition
- Dependency Injection Integration

DESIGN PATTERNS:
- Template Method Pattern: Standardisierter Setup-Prozess
- Factory Pattern: Service-spezifische Exception Creation
- Strategy Pattern: Verschiedene Logging Strategien

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 1.0.0
"""

import logging
import sys
from typing import Dict, Any, List, Type, Optional
from abc import ABC, abstractmethod
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import shared error framework
from error_handling_framework_v1_0_0_20250825 import (
    BaseServiceError,
    create_exception_handlers,
    setup_error_logging,
    ValidationError,
    NotFoundError,
    BusinessLogicError,
    DatabaseError
)


# =============================================================================
# SERVICE ERROR TEMPLATE BASE CLASSES
# =============================================================================

class ServiceErrorTemplate(ABC):
    """
    Abstract base class für Service-spezifische Error Templates
    
    Definiert Standard-Pattern für Service Error Handling Setup.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def create_service_exceptions(self) -> Dict[str, Type[BaseServiceError]]:
        """
        Erstellt Service-spezifische Exception-Klassen
        
        Returns:
            Dictionary mit Exception-Namen und Klassen
        """
        pass
    
    @abstractmethod
    def get_service_specific_config(self) -> Dict[str, Any]:
        """
        Liefert Service-spezifische Konfiguration
        
        Returns:
            Konfigurationsdictionary für Service
        """
        pass
    
    def setup_logging(self, log_file_path: str = None):
        """Setup strukturiertes Logging für Service"""
        if not log_file_path:
            log_file_path = f'/opt/aktienanalyse-ökosystem/logs/{self.service_name}.log'
        
        setup_error_logging(
            service_name=self.service_name,
            log_file_path=log_file_path
        )
        
        self.logger.info(f"Error handling logging configured for {self.service_name}")
    
    def create_fastapi_app(
        self,
        title: str = None,
        description: str = None,
        version: str = "1.0.0",
        lifespan: callable = None
    ) -> FastAPI:
        """
        Erstellt FastAPI Application mit Error Handling
        
        Args:
            title: Service title für API documentation
            description: Service description  
            version: Service version
            lifespan: Optional lifespan context manager
        
        Returns:
            Konfigurierte FastAPI Application
        """
        
        app_title = title or f"{self.service_name.replace('-', ' ').title()}"
        app_description = description or f"{app_title} with Clean Architecture and Error Framework"
        
        # Create FastAPI app with error handlers
        app = FastAPI(
            title=app_title,
            description=app_description,
            version=version,
            docs_url="/docs",
            redoc_url="/redoc",
            lifespan=lifespan,
            exception_handlers=create_exception_handlers()
        )
        
        # Add CORS middleware for private development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Private development - permissive CORS
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.logger.info(f"FastAPI application created for {self.service_name}")
        return app


# =============================================================================
# COMMON SERVICE EXCEPTION PATTERNS
# =============================================================================

class ServiceNotFoundErrorMixin:
    """Mixin für "Not Found" Fehler in Services"""
    
    @staticmethod
    def create_not_found_error(
        resource_type: str,
        resource_id: str,
        service_name: str
    ) -> NotFoundError:
        return NotFoundError(
            message=f"{resource_type.title()} {resource_id} not found in {service_name}",
            resource_type=resource_type,
            resource_id=resource_id
        )


class ServiceValidationErrorMixin:
    """Mixin für Validierungsfehler in Services"""
    
    @staticmethod
    def create_validation_error(
        message: str,
        field: str = None,
        service_name: str = None
    ) -> ValidationError:
        context = {"service": service_name} if service_name else {}
        if field:
            context["field"] = field
            
        return ValidationError(
            message=message,
            context=context
        )


class ServiceBusinessRuleErrorMixin:
    """Mixin für Business Rule Violations"""
    
    @staticmethod
    def create_business_rule_error(
        message: str,
        rule_name: str,
        service_name: str = None
    ) -> BusinessLogicError:
        return BusinessLogicError(
            message=message,
            rule=rule_name,
            context={"service": service_name} if service_name else {}
        )


# =============================================================================
# STANDARD SERVICE ERROR TEMPLATES
# =============================================================================

class DataServiceErrorTemplate(ServiceErrorTemplate):
    """Template für datenbasierte Services (Storage, Analytics, etc.)"""
    
    def create_service_exceptions(self) -> Dict[str, Type[BaseServiceError]]:
        """Standard Data Service Exceptions"""
        
        class DataNotFoundError(NotFoundError):
            def __init__(self, data_type: str, identifier: str, **kwargs):
                super().__init__(
                    message=f"{data_type} {identifier} not found",
                    resource_type=data_type,
                    resource_id=identifier,
                    **kwargs
                )
        
        class DataValidationError(ValidationError):
            def __init__(self, message: str, data_field: str = None, **kwargs):
                super().__init__(
                    message=message,
                    field=data_field,
                    **kwargs
                )
        
        class DataStorageError(DatabaseError):
            def __init__(self, message: str, operation: str = None, **kwargs):
                super().__init__(
                    message=message,
                    operation=operation,
                    **kwargs
                )
        
        return {
            "data_not_found": DataNotFoundError,
            "data_validation": DataValidationError,
            "data_storage": DataStorageError
        }
    
    def get_service_specific_config(self) -> Dict[str, Any]:
        return {
            "error_recovery": {
                "enable_retries": True,
                "max_retry_attempts": 3,
                "retry_backoff_factor": 2.0
            },
            "data_validation": {
                "strict_mode": False,
                "allow_partial_updates": True
            }
        }


class APIServiceErrorTemplate(ServiceErrorTemplate):
    """Template für API Gateway Services und External Integrations"""
    
    def create_service_exceptions(self) -> Dict[str, Type[BaseServiceError]]:
        """Standard API Service Exceptions"""
        
        class APIRequestError(ValidationError):
            def __init__(self, message: str, endpoint: str = None, **kwargs):
                super().__init__(
                    message=message,
                    context={"endpoint": endpoint} if endpoint else {},
                    **kwargs
                )
        
        class APIResponseError(BaseServiceError):
            def __init__(self, message: str, status_code: int = None, **kwargs):
                super().__init__(
                    message=message,
                    error_code="API_RESPONSE_ERROR",
                    context={"status_code": status_code} if status_code else {},
                    **kwargs
                )
        
        class APIRateLimitError(BaseServiceError):
            def __init__(self, message: str = "API rate limit exceeded", **kwargs):
                super().__init__(
                    message=message,
                    error_code="API_RATE_LIMIT_ERROR",
                    **kwargs
                )
        
        return {
            "api_request": APIRequestError,
            "api_response": APIResponseError,
            "api_rate_limit": APIRateLimitError
        }
    
    def get_service_specific_config(self) -> Dict[str, Any]:
        return {
            "api_timeouts": {
                "default_timeout": 30,
                "external_service_timeout": 60
            },
            "rate_limiting": {
                "enable_rate_limiting": True,
                "requests_per_minute": 60
            }
        }


class ProcessingServiceErrorTemplate(ServiceErrorTemplate):
    """Template für Processing Services (ML, Analytics, Calculations)"""
    
    def create_service_exceptions(self) -> Dict[str, Type[BaseServiceError]]:
        """Standard Processing Service Exceptions"""
        
        class ProcessingError(BaseServiceError):
            def __init__(self, message: str, process_id: str = None, **kwargs):
                super().__init__(
                    message=message,
                    error_code="PROCESSING_ERROR",
                    context={"process_id": process_id} if process_id else {},
                    **kwargs
                )
        
        class ProcessingTimeoutError(BaseServiceError):
            def __init__(self, message: str = "Processing timeout", timeout_seconds: int = None, **kwargs):
                super().__init__(
                    message=message,
                    error_code="PROCESSING_TIMEOUT_ERROR",
                    context={"timeout_seconds": timeout_seconds} if timeout_seconds else {},
                    **kwargs
                )
        
        class ProcessingResourceError(BaseServiceError):
            def __init__(self, message: str, resource_type: str = None, **kwargs):
                super().__init__(
                    message=message,
                    error_code="PROCESSING_RESOURCE_ERROR",
                    context={"resource_type": resource_type} if resource_type else {},
                    **kwargs
                )
        
        return {
            "processing": ProcessingError,
            "processing_timeout": ProcessingTimeoutError,
            "processing_resource": ProcessingResourceError
        }
    
    def get_service_specific_config(self) -> Dict[str, Any]:
        return {
            "processing": {
                "default_timeout": 300,  # 5 minutes
                "max_parallel_processes": 5,
                "enable_background_tasks": True
            },
            "resource_limits": {
                "max_memory_mb": 1024,
                "max_cpu_percent": 80
            }
        }


# =============================================================================
# SERVICE ERROR TEMPLATE FACTORY
# =============================================================================

class ServiceErrorTemplateFactory:
    """Factory für Service Error Templates"""
    
    @staticmethod
    def create_template(
        service_type: str,
        service_name: str
    ) -> ServiceErrorTemplate:
        """
        Erstellt Error Template basierend auf Service-Typ
        
        Args:
            service_type: Art des Service ("data", "api", "processing")
            service_name: Name des Service
        
        Returns:
            Passende ServiceErrorTemplate Instanz
        """
        
        template_mapping = {
            "data": DataServiceErrorTemplate,
            "api": APIServiceErrorTemplate,
            "processing": ProcessingServiceErrorTemplate
        }
        
        template_class = template_mapping.get(service_type, DataServiceErrorTemplate)
        return template_class(service_name)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def setup_service_error_handling(
    service_name: str,
    service_type: str = "data",
    log_file_path: str = None
) -> ServiceErrorTemplate:
    """
    One-liner Setup für Service Error Handling
    
    Args:
        service_name: Name des Service
        service_type: Art des Service ("data", "api", "processing") 
        log_file_path: Optional custom log file path
    
    Returns:
        Konfiguriertes ServiceErrorTemplate
    """
    
    template = ServiceErrorTemplateFactory.create_template(service_type, service_name)
    template.setup_logging(log_file_path)
    
    return template


def create_standard_fastapi_app(
    service_name: str,
    service_type: str = "data", 
    version: str = "1.0.0",
    lifespan: callable = None
) -> FastAPI:
    """
    One-liner für FastAPI App mit Error Handling
    
    Args:
        service_name: Name des Service
        service_type: Art des Service
        version: Service version
        lifespan: Optional lifespan context manager
    
    Returns:
        Konfigurierte FastAPI Application
    """
    
    template = setup_service_error_handling(service_name, service_type)
    return template.create_fastapi_app(version=version, lifespan=lifespan)


# =============================================================================
# HEALTH CHECK ERROR INTEGRATION
# =============================================================================

def create_health_check_with_error_context(
    service_name: str,
    additional_checks: List[callable] = None
) -> callable:
    """
    Erstellt Health Check Endpoint mit Error Context
    
    Args:
        service_name: Name des Service
        additional_checks: Zusätzliche Health Checks
    
    Returns:
        Health check function für FastAPI endpoint
    """
    
    async def health_check():
        health_data = {
            "service": service_name,
            "status": "healthy",
            "timestamp": logging.time.time(),
            "error_framework": "v1.0.0"
        }
        
        if additional_checks:
            for check in additional_checks:
                try:
                    check_result = await check() if asyncio.iscoroutinefunction(check) else check()
                    health_data.update(check_result)
                except Exception as e:
                    health_data["status"] = "degraded"
                    health_data["errors"] = health_data.get("errors", [])
                    health_data["errors"].append({
                        "check": check.__name__,
                        "error": str(e)
                    })
        
        return health_data
    
    return health_check