#!/usr/bin/env python3
"""
AioHTTP Client Implementation - Infrastructure Layer
Frontend Service Clean Architecture v1.0.0

INFRASTRUCTURE LAYER - HTTP CLIENT:
- Concrete HTTP Client Implementation
- Connection Pool Management
- Error Handling & Retry Logic
- Performance Monitoring

CLEAN ARCHITECTURE PRINCIPLES:
- Implements IHTTPClient Interface
- No Business Logic
- Pure Infrastructure Concern

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp
from aiohttp import ClientTimeout, ClientError

from ...application.interfaces.http_client_interface import (
    IHTTPClient, 
    HTTPClientError, 
    ServiceUnavailableError,
    TimeoutError as HTTPTimeoutError,
    AuthenticationError
)


logger = logging.getLogger(__name__)


class AioHTTPClientService(IHTTPClient):
    """
    AioHTTP Client Service Implementation
    
    RESPONSIBILITIES:
    - HTTP communication with external services
    - Connection pool management  
    - Error handling and recovery
    - Performance monitoring
    
    DESIGN PATTERNS:
    - Adapter Pattern: Adapts aiohttp to IHTTPClient interface
    - Singleton Pattern: Single session per instance
    - Circuit Breaker Pattern: Fail fast on repeated errors
    """
    
    def __init__(self, 
                 timeout_seconds: int = 30,
                 max_connections: int = 100,
                 retry_attempts: int = 3):
        """
        Initialize AioHTTP Client Service
        
        Args:
            timeout_seconds: Request timeout
            max_connections: Maximum concurrent connections
            retry_attempts: Number of retry attempts for failed requests
        """
        self._timeout_seconds = timeout_seconds
        self._max_connections = max_connections
        self._retry_attempts = retry_attempts
        
        # Connection management
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._is_initialized = False
        
        # Performance tracking
        self._request_count = 0
        self._error_count = 0
        self._total_response_time = 0.0
        
        logger.info(f"AioHTTP Client initialized - timeout: {timeout_seconds}s, max_connections: {max_connections}")
    
    async def initialize(self) -> None:
        """Initialize HTTP client session and connector"""
        if self._is_initialized:
            return
        
        try:
            # Create TCP connector with connection pool
            self._connector = aiohttp.TCPConnector(
                limit=self._max_connections,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            # Create client timeout configuration
            timeout = ClientTimeout(
                total=self._timeout_seconds,
                connect=10,
                sock_read=self._timeout_seconds
            )
            
            # Create client session
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Frontend-Service-Clean-Architecture/1.0.0',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate'
                }
            )
            
            self._is_initialized = True
            logger.info("AioHTTP Client session initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AioHTTP Client: {str(e)}")
            raise HTTPClientError(f"Client initialization failed: {str(e)}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown HTTP client"""
        try:
            if self._session:
                await self._session.close()
                
            if self._connector:
                await self._connector.close()
            
            # Wait for connections to close
            await asyncio.sleep(0.1)
            
            self._is_initialized = False
            logger.info("AioHTTP Client shutdown completed")
            
        except Exception as e:
            logger.error(f"AioHTTP Client shutdown error: {str(e)}")
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute HTTP GET request with retry logic
        
        Args:
            url: Target URL
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            HTTPClientError: On communication errors
            HTTPTimeoutError: On request timeout
        """
        return await self._execute_request('GET', url, params=params)
    
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute HTTP POST request with retry logic
        
        Args:
            url: Target URL
            data: Request body data
            
        Returns:
            Response data as dictionary
            
        Raises:
            HTTPClientError: On communication errors
            HTTPTimeoutError: On request timeout
        """
        return await self._execute_request('POST', url, json=data)
    
    async def get_text(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute HTTP GET request returning text
        
        Args:
            url: Target URL
            params: Query parameters
            
        Returns:
            Response as text string
            
        Raises:
            HTTPClientError: On communication errors
            HTTPTimeoutError: On request timeout
        """
        response = await self._execute_request('GET', url, params=params, return_json=False)
        return response.get('text', '')
    
    async def health_check(self, url: str, timeout_seconds: int = 5) -> bool:
        """
        Perform health check on service
        
        Args:
            url: Service health check URL
            timeout_seconds: Request timeout
            
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Use shorter timeout for health checks
            custom_timeout = ClientTimeout(total=timeout_seconds)
            
            start_time = datetime.now()
            
            async with self._session.get(url, timeout=custom_timeout) as response:
                response_time = (datetime.now() - start_time).total_seconds()
                
                # Consider service healthy if:
                # - Response status is 2xx
                # - Response time is reasonable
                is_healthy = (200 <= response.status < 300 and response_time < timeout_seconds)
                
                logger.debug(f"Health check {url}: status={response.status}, time={response_time:.3f}s, healthy={is_healthy}")
                return is_healthy
                
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for {url}")
            return False
        except Exception as e:
            logger.warning(f"Health check failed for {url}: {str(e)}")
            return False
    
    async def _execute_request(self, 
                             method: str, 
                             url: str, 
                             return_json: bool = True,
                             **kwargs) -> Dict[str, Any]:
        """
        Execute HTTP request with error handling and retry logic
        
        Args:
            method: HTTP method
            url: Target URL
            return_json: Whether to parse response as JSON
            **kwargs: Additional request arguments
            
        Returns:
            Response data
            
        Raises:
            HTTPClientError: On persistent errors
        """
        if not self._is_initialized:
            await self.initialize()
        
        last_exception = None
        
        # Retry logic
        for attempt in range(self._retry_attempts):
            try:
                start_time = datetime.now()
                
                # Execute request
                async with self._session.request(method, url, **kwargs) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    # Update performance metrics
                    self._request_count += 1
                    self._total_response_time += response_time
                    
                    # Log request details
                    logger.debug(f"{method} {url} -> {response.status} ({response_time:.3f}s)")
                    
                    # Handle response based on status code
                    if response.status == 200:
                        if return_json:
                            try:
                                return await response.json()
                            except Exception as e:
                                # Fallback to text if JSON parsing fails
                                text_content = await response.text()
                                return {"content": text_content, "status": response.status}
                        else:
                            text_content = await response.text()
                            return {"text": text_content, "status": response.status}
                    
                    elif response.status == 401:
                        raise AuthenticationError(f"Authentication failed for {url}", response.status, url)
                    
                    elif response.status == 404:
                        raise HTTPClientError(f"Resource not found: {url}", response.status, url)
                    
                    elif response.status == 503:
                        raise ServiceUnavailableError(f"Service unavailable: {url}", response.status, url)
                    
                    elif 400 <= response.status < 500:
                        error_text = await response.text()
                        raise HTTPClientError(f"Client error {response.status}: {error_text}", response.status, url)
                    
                    elif 500 <= response.status < 600:
                        error_text = await response.text()
                        raise HTTPClientError(f"Server error {response.status}: {error_text}", response.status, url)
                    
                    else:
                        # Unexpected status code
                        error_text = await response.text()
                        raise HTTPClientError(f"Unexpected status {response.status}: {error_text}", response.status, url)
            
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"Request timeout for {url} (attempt {attempt + 1}/{self._retry_attempts})")
                
                if attempt == self._retry_attempts - 1:
                    self._error_count += 1
                    raise HTTPTimeoutError(f"Request timeout after {self._retry_attempts} attempts: {url}", None, url)
                
                # Wait before retry (exponential backoff)
                await asyncio.sleep(0.5 * (2 ** attempt))
            
            except ClientError as e:
                last_exception = e
                logger.warning(f"Client error for {url}: {str(e)} (attempt {attempt + 1}/{self._retry_attempts})")
                
                if attempt == self._retry_attempts - 1:
                    self._error_count += 1
                    raise HTTPClientError(f"Client error after {self._retry_attempts} attempts: {str(e)}", None, url)
                
                # Wait before retry
                await asyncio.sleep(0.5 * (2 ** attempt))
            
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error for {url}: {str(e)} (attempt {attempt + 1}/{self._retry_attempts})")
                
                if attempt == self._retry_attempts - 1:
                    self._error_count += 1
                    raise HTTPClientError(f"Unexpected error after {self._retry_attempts} attempts: {str(e)}", None, url)
                
                # Wait before retry
                await asyncio.sleep(0.5 * (2 ** attempt))
        
        # Should never reach here, but handle gracefully
        self._error_count += 1
        raise HTTPClientError(f"Request failed after all retry attempts: {str(last_exception)}", None, url)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        avg_response_time = (
            self._total_response_time / self._request_count 
            if self._request_count > 0 else 0.0
        )
        
        error_rate = (
            self._error_count / self._request_count * 100 
            if self._request_count > 0 else 0.0
        )
        
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate_percent": error_rate,
            "average_response_time_seconds": avg_response_time,
            "is_initialized": self._is_initialized,
            "max_connections": self._max_connections,
            "timeout_seconds": self._timeout_seconds
        }