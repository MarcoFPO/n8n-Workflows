#!/usr/bin/env python3
"""
HTTP Client Interface - Application Layer
Frontend Service Clean Architecture v1.0.0

APPLICATION LAYER - INTERFACES:
- HTTP Client Service Interface
- External Service Communication Contract
- Dependency Inversion Implementation

CLEAN ARCHITECTURE PRINCIPLES:
- Interface Segregation: Specific HTTP operations
- Dependency Inversion: Abstract over concrete implementations
- Single Responsibility: Only HTTP communication contract

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class IHTTPClient(ABC):
    """
    HTTP Client Interface
    
    INTERFACE SEGREGATION PRINCIPLE:
    - Only essential HTTP operations
    - Clean contract for external service communication
    - No implementation details in interface
    """
    
    @abstractmethod
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute HTTP GET request
        
        Args:
            url: Target URL
            params: Query parameters (optional)
            
        Returns:
            Response data as dictionary
            
        Raises:
            HTTPClientError: On communication errors
            TimeoutError: On request timeout
        """
        pass
    
    @abstractmethod
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute HTTP POST request
        
        Args:
            url: Target URL
            data: Request body data (optional)
            
        Returns:
            Response data as dictionary
            
        Raises:
            HTTPClientError: On communication errors
            TimeoutError: On request timeout
        """
        pass
    
    @abstractmethod
    async def get_text(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute HTTP GET request returning text
        
        Args:
            url: Target URL
            params: Query parameters (optional)
            
        Returns:
            Response as text string
            
        Raises:
            HTTPClientError: On communication errors
            TimeoutError: On request timeout
        """
        pass
    
    @abstractmethod
    async def health_check(self, url: str, timeout_seconds: int = 5) -> bool:
        """
        Perform health check on service
        
        Args:
            url: Service health check URL
            timeout_seconds: Request timeout
            
        Returns:
            True if service is healthy, False otherwise
        """
        pass


class IServiceClient(ABC):
    """
    Service Client Interface
    
    Higher-level interface for specific service communication
    Built on top of IHTTPClient
    """
    
    @abstractmethod
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status information
        
        Returns:
            Service status data
        """
        pass
    
    @abstractmethod
    async def get_service_health(self) -> bool:
        """
        Check if service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        pass


class HTTPClientError(Exception):
    """HTTP Client specific error"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, url: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url
        self.timestamp = datetime.now()


class ServiceUnavailableError(HTTPClientError):
    """Service unavailable error"""
    pass


class TimeoutError(HTTPClientError):
    """Request timeout error"""
    pass


class AuthenticationError(HTTPClientError):
    """Authentication error"""
    pass


class ValidationError(HTTPClientError):
    """Request validation error"""
    pass