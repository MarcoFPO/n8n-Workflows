#!/usr/bin/env python3
"""
Service Client Pool - Infrastructure Layer
Frontend Service Clean Architecture v1.0.0

INFRASTRUCTURE LAYER - SERVICE INTEGRATION:
- Service Client Pool Management
- External Service Communication
- Connection Pool Optimization
- Service Discovery Pattern

CLEAN ARCHITECTURE PRINCIPLES:
- Infrastructure Layer Responsibility
- Service Integration Abstraction
- Performance Optimization

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from ...application.interfaces.http_client_interface import IHTTPClient, HTTPClientError


logger = logging.getLogger(__name__)


class ServiceClientPool:
    """
    Service Client Pool for External Service Communication
    
    RESPONSIBILITIES:
    - Manage connections to external services
    - Provide service-specific client interfaces
    - Handle service discovery and failover
    - Monitor service health and performance
    
    DESIGN PATTERNS:
    - Object Pool Pattern: Reuse service clients
    - Proxy Pattern: Abstraction for service communication
    - Circuit Breaker Pattern: Prevent cascade failures
    """
    
    def __init__(self, http_client: IHTTPClient, service_urls: Dict[str, str]):
        """
        Initialize Service Client Pool
        
        Args:
            http_client: HTTP client for communication
            service_urls: Dictionary of service URLs
        """
        self._http_client = http_client
        self._service_urls = service_urls
        self._service_clients: Dict[str, 'ServiceClient'] = {}
        self._is_initialized = False
        
        # Service health tracking
        self._service_health: Dict[str, bool] = {}
        self._last_health_check: Dict[str, datetime] = {}
        
        logger.info(f"Service Client Pool initialized with {len(service_urls)} services")
    
    async def initialize(self) -> None:
        """Initialize service client pool"""
        if self._is_initialized:
            return
        
        try:
            # Create service clients for each configured service
            for service_name, service_url in self._service_urls.items():
                client = ServiceClient(
                    service_name=service_name,
                    service_url=service_url,
                    http_client=self._http_client
                )
                await client.initialize()
                self._service_clients[service_name] = client
                
                # Initialize health status
                self._service_health[service_name] = False
                self._last_health_check[service_name] = datetime.now()
            
            self._is_initialized = True
            logger.info(f"Service Client Pool initialized with {len(self._service_clients)} clients")
            
        except Exception as e:
            logger.error(f"Service Client Pool initialization failed: {str(e)}")
            raise HTTPClientError(f"Pool initialization failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown service client pool"""
        try:
            for client in self._service_clients.values():
                await client.shutdown()
            
            self._service_clients.clear()
            self._is_initialized = False
            
            logger.info("Service Client Pool shutdown completed")
            
        except Exception as e:
            logger.error(f"Service Client Pool shutdown error: {str(e)}")
    
    def get_service_client(self, service_name: str) -> Optional['ServiceClient']:
        """
        Get service client by name
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service client instance or None if not found
        """
        return self._service_clients.get(service_name)
    
    async def health_check_all_services(self) -> Dict[str, bool]:
        """
        Perform health check on all services
        
        Returns:
            Dictionary mapping service names to health status
        """
        health_results = {}
        
        for service_name, client in self._service_clients.items():
            try:
                is_healthy = await client.health_check()
                health_results[service_name] = is_healthy
                self._service_health[service_name] = is_healthy
                self._last_health_check[service_name] = datetime.now()
                
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {str(e)}")
                health_results[service_name] = False
                self._service_health[service_name] = False
        
        return health_results
    
    def get_service_health_summary(self) -> Dict[str, Any]:
        """Get service health summary"""
        healthy_services = sum(1 for is_healthy in self._service_health.values() if is_healthy)
        total_services = len(self._service_health)
        
        return {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": total_services - healthy_services,
            "health_percentage": (healthy_services / total_services * 100) if total_services > 0 else 0,
            "service_details": {
                service_name: {
                    "healthy": is_healthy,
                    "last_check": self._last_health_check.get(service_name)
                }
                for service_name, is_healthy in self._service_health.items()
            }
        }
    
    def get_available_services(self) -> List[str]:
        """Get list of available service names"""
        return list(self._service_clients.keys())
    
    def is_service_healthy(self, service_name: str) -> bool:
        """Check if specific service is healthy"""
        return self._service_health.get(service_name, False)


class ServiceClient:
    """
    Individual Service Client
    
    RESPONSIBILITIES:
    - Handle communication with specific external service
    - Provide service-specific API methods
    - Track service performance metrics
    """
    
    def __init__(self, service_name: str, service_url: str, http_client: IHTTPClient):
        """
        Initialize Service Client
        
        Args:
            service_name: Name of the service
            service_url: Base URL of the service
            http_client: HTTP client for communication
        """
        self._service_name = service_name
        self._service_url = service_url.rstrip('/')
        self._http_client = http_client
        
        # Performance metrics
        self._request_count = 0
        self._error_count = 0
        self._total_response_time = 0.0
        self._last_successful_request = None
        
        logger.debug(f"Service Client created for {service_name}: {service_url}")
    
    async def initialize(self) -> None:
        """Initialize service client"""
        # Perform initial health check to validate service availability
        try:
            await self.health_check()
            logger.debug(f"Service Client initialized for {self._service_name}")
        except Exception as e:
            logger.warning(f"Initial health check failed for {self._service_name}: {str(e)}")
    
    async def shutdown(self) -> None:
        """Shutdown service client"""
        logger.debug(f"Service Client shutdown for {self._service_name}")
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute GET request to service endpoint
        
        Args:
            endpoint: Service endpoint path
            params: Query parameters
            
        Returns:
            Response data
        """
        url = self._build_url(endpoint)
        
        try:
            start_time = datetime.now()
            response = await self._http_client.get(url, params)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Update metrics
            self._request_count += 1
            self._total_response_time += response_time
            self._last_successful_request = datetime.now()
            
            logger.debug(f"GET {url} completed in {response_time:.3f}s")
            return response
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"GET {url} failed: {str(e)}")
            raise
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute POST request to service endpoint
        
        Args:
            endpoint: Service endpoint path
            data: Request body data
            
        Returns:
            Response data
        """
        url = self._build_url(endpoint)
        
        try:
            start_time = datetime.now()
            response = await self._http_client.post(url, data)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Update metrics
            self._request_count += 1
            self._total_response_time += response_time
            self._last_successful_request = datetime.now()
            
            logger.debug(f"POST {url} completed in {response_time:.3f}s")
            return response
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"POST {url} failed: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """
        Perform health check on service
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            health_url = f"{self._service_url}/health"
            is_healthy = await self._http_client.health_check(health_url)
            
            if is_healthy:
                self._last_successful_request = datetime.now()
            
            return is_healthy
            
        except Exception as e:
            logger.warning(f"Health check failed for {self._service_name}: {str(e)}")
            return False
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics"""
        avg_response_time = (
            self._total_response_time / self._request_count 
            if self._request_count > 0 else 0.0
        )
        
        error_rate = (
            self._error_count / self._request_count * 100 
            if self._request_count > 0 else 0.0
        )
        
        return {
            "service_name": self._service_name,
            "service_url": self._service_url,
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate_percent": error_rate,
            "average_response_time_seconds": avg_response_time,
            "last_successful_request": self._last_successful_request
        }
    
    def _build_url(self, endpoint: str) -> str:
        """Build complete URL for endpoint"""
        endpoint = endpoint.lstrip('/')
        return f"{self._service_url}/{endpoint}"
    
    @property
    def service_name(self) -> str:
        """Get service name"""
        return self._service_name
    
    @property
    def service_url(self) -> str:
        """Get service URL"""
        return self._service_url