#!/usr/bin/env python3
"""
MarketCap Service - Get Market Data Use Case
Application Layer Business Logic Orchestration

CLEAN ARCHITECTURE - APPLICATION LAYER:
- Orchestrates business logic flow
- Uses domain entities and repository interfaces
- Independent of external frameworks

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from ...domain.entities.market_data import MarketData, MarketDataRequest
from ...domain.repositories.market_data_repository import (
    IMarketDataRepository,
    IMarketDataCache,
    IMarketDataProvider
)
from ..interfaces.event_publisher import IEventPublisher


logger = logging.getLogger(__name__)


class GetMarketDataUseCase:
    """
    Get Market Data Use Case
    
    APPLICATION LAYER: Orchestrates market data retrieval business logic
    SINGLE RESPONSIBILITY: Handles one specific use case
    DEPENDENCY INVERSION: Depends on abstractions, not implementations
    """
    
    def __init__(
        self,
        repository: IMarketDataRepository,
        cache: Optional[IMarketDataCache] = None,
        provider: Optional[IMarketDataProvider] = None,
        event_publisher: Optional[IEventPublisher] = None
    ):
        self.repository = repository
        self.cache = cache
        self.provider = provider
        self.event_publisher = event_publisher
    
    async def execute(self, symbol: str, use_cache: bool = True, source: str = "marketcap_service") -> Dict[str, Any]:
        """
        Execute Get Market Data Use Case
        
        BUSINESS LOGIC FLOW:
        1. Validate request
        2. Check cache (if enabled)
        3. Check repository
        4. Fetch from provider (if needed)
        5. Update cache and repository
        6. Publish event
        7. Return result
        
        Args:
            symbol: Stock symbol to retrieve
            use_cache: Whether to use cache
            source: Data source identifier
            
        Returns:
            Dictionary with market data result
        """
        try:
            # 1. Validate and create request
            request = MarketDataRequest(
                symbol=symbol.upper().strip(),
                requested_at=datetime.now(),
                source=source
            )
            
            logger.info(f"Processing market data request for symbol: {request.symbol}")
            
            # Validate request
            if not request.is_request_valid():
                return self._create_error_response("Request is no longer valid", "INVALID_REQUEST")
            
            # 2. Try cache first (if enabled and requested)
            market_data = None
            data_source = "cache"
            
            if use_cache and self.cache:
                market_data = await self._try_get_from_cache(request.symbol)
                if market_data and market_data.is_data_fresh():
                    logger.debug(f"Cache hit for symbol: {request.symbol}")
                    return await self._create_success_response(market_data, data_source, request)
            
            # 3. Try repository
            market_data = await self._try_get_from_repository(request.symbol)
            data_source = "repository"
            
            if market_data and market_data.is_data_fresh():
                logger.debug(f"Repository hit for symbol: {request.symbol}")
                
                # Update cache if available
                if self.cache:
                    await self._try_cache_data(market_data)
                
                return await self._create_success_response(market_data, data_source, request)
            
            # 4. Fetch from external provider
            if self.provider:
                market_data = await self._try_get_from_provider(request.symbol)
                data_source = "provider"
                
                if market_data:
                    logger.info(f"Fetched fresh data from provider for symbol: {request.symbol}")
                    
                    # Save to repository
                    await self._try_save_to_repository(market_data)
                    
                    # Update cache
                    if self.cache:
                        await self._try_cache_data(market_data)
                    
                    return await self._create_success_response(market_data, data_source, request)
            
            # 5. No data available
            logger.warning(f"No market data available for symbol: {request.symbol}")
            return self._create_error_response(f"No market data available for symbol: {request.symbol}", "DATA_NOT_FOUND")
            
        except ValueError as e:
            logger.error(f"Validation error for symbol {symbol}: {e}")
            return self._create_error_response(str(e), "VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error processing request for symbol {symbol}: {e}")
            return self._create_error_response("Internal server error", "INTERNAL_ERROR")
    
    async def _try_get_from_cache(self, symbol: str) -> Optional[MarketData]:
        """Try to get data from cache"""
        try:
            if self.cache:
                return await self.cache.get_cached_data(symbol)
        except Exception as e:
            logger.warning(f"Cache retrieval failed for symbol {symbol}: {e}")
        return None
    
    async def _try_get_from_repository(self, symbol: str) -> Optional[MarketData]:
        """Try to get data from repository"""
        try:
            return await self.repository.get_market_data(symbol)
        except Exception as e:
            logger.warning(f"Repository retrieval failed for symbol {symbol}: {e}")
        return None
    
    async def _try_get_from_provider(self, symbol: str) -> Optional[MarketData]:
        """Try to get data from external provider"""
        try:
            if self.provider and await self.provider.is_available():
                return await self.provider.fetch_market_data(symbol)
        except Exception as e:
            logger.warning(f"Provider retrieval failed for symbol {symbol}: {e}")
        return None
    
    async def _try_save_to_repository(self, market_data: MarketData) -> bool:
        """Try to save data to repository"""
        try:
            return await self.repository.save_market_data(market_data)
        except Exception as e:
            logger.warning(f"Repository save failed for symbol {market_data.symbol}: {e}")
            return False
    
    async def _try_cache_data(self, market_data: MarketData) -> bool:
        """Try to cache data"""
        try:
            if self.cache:
                return await self.cache.cache_data(market_data)
        except Exception as e:
            logger.warning(f"Cache save failed for symbol {market_data.symbol}: {e}")
        return False
    
    async def _create_success_response(
        self,
        market_data: MarketData,
        data_source: str,
        request: MarketDataRequest
    ) -> Dict[str, Any]:
        """Create success response and publish event"""
        
        response = {
            'success': True,
            'data': market_data.to_dict(),
            'source': data_source,
            'request_info': request.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Publish success event
        await self._publish_event('market_data.retrieved.success', {
            'symbol': market_data.symbol,
            'source': data_source,
            'cap_classification': market_data.get_cap_classification(),
            'is_positive_performance': market_data.is_positive_performance()
        })
        
        return response
    
    def _create_error_response(self, message: str, error_code: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            'success': False,
            'error': {
                'message': message,
                'code': error_code,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    async def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish event if publisher is available"""
        try:
            if self.event_publisher:
                await self.event_publisher.publish(event_type, {
                    **data,
                    'service': 'marketcap_service',
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.warning(f"Event publishing failed: {e}")


class GetAllMarketDataUseCase:
    """
    Get All Market Data Use Case
    
    APPLICATION LAYER: Retrieves all available market data
    """
    
    def __init__(self, repository: IMarketDataRepository):
        self.repository = repository
    
    async def execute(self, cap_classification: Optional[str] = None, fresh_only: bool = True) -> Dict[str, Any]:
        """
        Execute Get All Market Data Use Case
        
        Args:
            cap_classification: Filter by cap size ("Large Cap", "Mid Cap", "Small Cap")
            fresh_only: Only return fresh data
            
        Returns:
            Dictionary with all market data results
        """
        try:
            if cap_classification:
                market_data_list = await self.repository.get_market_data_by_cap_size(cap_classification)
            elif fresh_only:
                market_data_list = await self.repository.get_fresh_market_data()
            else:
                symbols = await self.repository.get_all_symbols()
                market_data_list = []
                for symbol in symbols:
                    data = await self.repository.get_market_data(symbol)
                    if data:
                        market_data_list.append(data)
            
            # Convert to dict format
            results = [data.to_dict() for data in market_data_list]
            
            return {
                'success': True,
                'data': results,
                'count': len(results),
                'filter': {
                    'cap_classification': cap_classification,
                    'fresh_only': fresh_only
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error retrieving all market data: {e}")
            return {
                'success': False,
                'error': {
                    'message': "Failed to retrieve market data",
                    'code': "RETRIEVAL_ERROR",
                    'timestamp': datetime.now().isoformat()
                }
            }