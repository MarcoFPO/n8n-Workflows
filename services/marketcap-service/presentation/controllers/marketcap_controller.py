#!/usr/bin/env python3
"""
MarketCap Service - Presentation Controller
Clean Architecture Presentation Layer

CLEAN ARCHITECTURE - PRESENTATION LAYER:
- HTTP request/response handling
- FastAPI integration
- Request validation and response formatting

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...application.use_cases.get_market_data_use_case import (
    GetMarketDataUseCase,
    GetAllMarketDataUseCase
)


logger = logging.getLogger(__name__)


class MarketCapController:
    """
    MarketCap Service Presentation Controller
    
    PRESENTATION LAYER: Handles HTTP requests and responses
    SINGLE RESPONSIBILITY: Coordinates between HTTP layer and application layer
    DEPENDENCY INJECTION: Receives use cases via constructor
    """
    
    def __init__(
        self,
        get_market_data_use_case: GetMarketDataUseCase,
        get_all_market_data_use_case: GetAllMarketDataUseCase
    ):
        self.get_market_data_use_case = get_market_data_use_case
        self.get_all_market_data_use_case = get_all_market_data_use_case
    
    async def get_market_data(
        self,
        symbol: str,
        use_cache: bool = True,
        source: str = "marketcap_service"
    ) -> Dict[str, Any]:
        """
        Get market data for a single symbol
        
        Args:
            symbol: Stock symbol to retrieve
            use_cache: Whether to use cache
            source: Data source identifier
            
        Returns:
            Market data response
        """
        try:
            logger.info(f"Controller processing request for symbol: {symbol}")
            
            # Execute use case
            result = await self.get_market_data_use_case.execute(
                symbol=symbol,
                use_cache=use_cache,
                source=source
            )
            
            # Add controller metadata
            result['controller_info'] = {
                'processed_at': datetime.now().isoformat(),
                'controller': 'MarketCapController.get_market_data',
                'version': '6.0.0'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Controller error processing request for symbol {symbol}: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'MarketCapController.get_market_data',
                    'version': '6.0.0'
                }
            }
    
    async def get_all_market_data(
        self,
        cap_classification: Optional[str] = None,
        fresh_only: bool = True
    ) -> Dict[str, Any]:
        """
        Get all market data with optional filtering
        
        Args:
            cap_classification: Filter by cap size
            fresh_only: Only return fresh data
            
        Returns:
            All market data response
        """
        try:
            logger.info(f"Controller processing request for all market data (cap: {cap_classification}, fresh_only: {fresh_only})")
            
            # Execute use case
            result = await self.get_all_market_data_use_case.execute(
                cap_classification=cap_classification,
                fresh_only=fresh_only
            )
            
            # Add controller metadata
            result['controller_info'] = {
                'processed_at': datetime.now().isoformat(),
                'controller': 'MarketCapController.get_all_market_data',
                'version': '6.0.0'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Controller error processing request for all market data: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'MarketCapController.get_all_market_data',
                    'version': '6.0.0'
                }
            }
    
    async def get_symbols(self) -> Dict[str, Any]:
        """
        Get all available symbols
        
        Returns:
            Available symbols response
        """
        try:
            logger.info("Controller processing request for available symbols")
            
            # Use the get_all_market_data_use_case to get symbols
            result = await self.get_all_market_data_use_case.execute(fresh_only=False)
            
            if result['success']:
                symbols = [item['symbol'] for item in result['data']]
                return {
                    'success': True,
                    'data': {
                        'symbols': symbols,
                        'count': len(symbols)
                    },
                    'controller_info': {
                        'processed_at': datetime.now().isoformat(),
                        'controller': 'MarketCapController.get_symbols',
                        'version': '6.0.0'
                    }
                }
            else:
                return result
            
        except Exception as e:
            logger.error(f"Controller error processing request for symbols: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    async def get_cap_distribution(self) -> Dict[str, Any]:
        """
        Get market cap distribution statistics
        
        Returns:
            Cap distribution response
        """
        try:
            logger.info("Controller processing request for cap distribution")
            
            # Get all market data
            all_data_result = await self.get_all_market_data_use_case.execute(fresh_only=False)
            
            if not all_data_result['success']:
                return all_data_result
            
            # Calculate distribution
            distribution = {"Large Cap": 0, "Mid Cap": 0, "Small Cap": 0}
            positive_performance = 0
            total_market_cap = 0
            
            for item in all_data_result['data']:
                cap_class = item['cap_classification']
                distribution[cap_class] += 1
                
                if item['is_positive_performance']:
                    positive_performance += 1
                
                total_market_cap += float(item['market_cap'])
            
            total_symbols = len(all_data_result['data'])
            
            return {
                'success': True,
                'data': {
                    'distribution': distribution,
                    'total_symbols': total_symbols,
                    'positive_performance_count': positive_performance,
                    'negative_performance_count': total_symbols - positive_performance,
                    'positive_performance_percentage': round((positive_performance / total_symbols * 100), 2) if total_symbols > 0 else 0,
                    'total_market_cap': total_market_cap,
                    'average_market_cap': round(total_market_cap / total_symbols, 2) if total_symbols > 0 else 0
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'MarketCapController.get_cap_distribution',
                    'version': '6.0.0'
                }
            }
            
        except Exception as e:
            logger.error(f"Controller error processing request for cap distribution: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller processing error',
                    'code': 'CONTROLLER_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Controller-level health check
        
        Returns:
            Health check response
        """
        try:
            return {
                'success': True,
                'data': {
                    'controller': 'MarketCapController',
                    'status': 'healthy',
                    'version': '6.0.0',
                    'capabilities': [
                        'get_market_data',
                        'get_all_market_data',
                        'get_symbols',
                        'get_cap_distribution',
                        'health_check'
                    ]
                },
                'controller_info': {
                    'processed_at': datetime.now().isoformat(),
                    'controller': 'MarketCapController.health_check',
                    'version': '6.0.0'
                }
            }
            
        except Exception as e:
            logger.error(f"Controller health check error: {e}")
            return {
                'success': False,
                'error': {
                    'message': 'Controller health check failed',
                    'code': 'HEALTH_CHECK_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            }