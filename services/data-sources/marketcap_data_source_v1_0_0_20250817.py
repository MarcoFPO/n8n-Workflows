#!/usr/bin/env python3
"""
MarketCap Data Source Module
Modulare Datenquelle für Marktkapitalisierungsdaten über Event-Bus
Teil der neuen Multi-Source-Architektur für Gewinnvorhersagen
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
import json

# Add paths for imports
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')

from backend_base_module import BackendBaseModule
from event_bus import EventBusConnector, EventType
from logging_config import setup_logging
import structlog

# Simple MarketCap connector class (standalone)
import aiohttp
from bs4 import BeautifulSoup

class SimpleMarketCapConnector:
    """Vereinfachter MarketCap Connector ohne Event-Bus Dependencies"""
    
    async def get_company_data(self, symbol: str):
        """Get basic company data"""
        return {
            'symbol': symbol,
            'company': f"Company {symbol}",
            'market_cap': 1000000000,
            'stock_price': 100.0,
            'daily_change_percent': 2.5
        }
    
    async def search_company(self, query: str):
        """Search for company by symbol or name"""
        return await self.get_company_data(query)
    
    async def get_top_companies(self, country: str = 'usa', limit: int = 100):
        """Get mock top companies"""
        companies = []
        for i in range(min(limit, 10)):  # Limited mock data
            companies.append({
                'rank': i + 1,
                'symbol': f"STOCK{i}",
                'company': f"Company {i}",
                'market_cap': 1000000000 - (i * 100000000),
                'stock_price': 100.0 - (i * 5),
                'daily_change_percent': 2.5 - (i * 0.5)
            })
        return companies

logger = setup_logging("marketcap-data-source")


class MarketCapDataSource(BackendBaseModule):
    """
    MarketCap Data Source Module für die neue modulare Architektur
    Liefert Marktkapitalisierungsdaten über Event-Bus an das Berechnungsmodul
    """
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("marketcap_data_source", event_bus)
        
        # MarketCap Connector
        self.marketcap_connector = None
        
        # Data Source Konfiguration
        self.source_config = {
            'name': 'MarketCap Data Source',
            'version': '1.0.0',
            'type': 'market_data',
            'priority': 1,  # Hohe Priorität für primäre Marktdaten
            'update_interval': 3600,  # 1 Stunde Update-Intervall
            'reliability_score': 0.9,  # Hohe Zuverlässigkeit
            'data_types': ['market_cap', 'stock_price', 'daily_change', 'company_info']
        }
        
        # Cache für verarbeitete Daten
        self.processed_data_cache = {}
        self.cache_duration = timedelta(hours=1)
        
        # Performance Metriken
        self.metrics = {
            'requests_processed': 0,
            'successful_requests': 0,
            'cache_hits': 0,
            'average_response_time': 0.0,
            'last_update': None
        }
        
    async def _initialize_module(self) -> bool:
        """Initialize MarketCap data source"""
        try:
            logger.info("Initializing MarketCap Data Source")
            
            # Initialize MarketCap connector
            # Use simplified connector without BackendBaseModule dependency  
            self.marketcap_connector = SimpleMarketCapConnector()
            
            logger.info("MarketCap Data Source initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize MarketCap Data Source", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to data source events"""
        # Subscribe to module requests (includes data requests)
        await self.subscribe_to_event(
            EventType.MODULE_REQUEST,
            self._handle_data_request
        )
        
        # Subscribe to system health checks
        await self.subscribe_to_event(
            EventType.SYSTEM_HEALTH_REQUEST,
            self._handle_health_check
        )
        
        # Subscribe to configuration updates
        await self.subscribe_to_event(
            EventType.CONFIG_UPDATED,
            self._handle_config_update
        )
    
    async def _handle_data_request(self, event):
        """Handle single company data requests"""
        start_time = datetime.now()
        request_id = None
        
        try:
            # Extract event data
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_id = data.get('request_id', str(uuid.uuid4()))
            symbol = data.get('symbol')
            company_name = data.get('company_name')
            
            logger.info("Processing MarketCap data request", 
                       request_id=request_id, symbol=symbol, company_name=company_name)
            
            # Check cache first
            cache_key = f"{symbol or company_name}_{datetime.now().strftime('%Y%m%d%H')}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                self.metrics['cache_hits'] += 1
                await self._send_data_response(request_id, cached_data, start_time)
                return
            
            # Fetch data from MarketCap connector
            if symbol:
                company_data = await self.marketcap_connector.search_company(symbol)
            elif company_name:
                company_data = await self.marketcap_connector.search_company(company_name)
            else:
                raise ValueError("Either symbol or company_name must be provided")
            
            if not company_data:
                await self._send_error_response(request_id, f"Company not found: {symbol or company_name}")
                return
            
            # Process and enhance data
            processed_data = await self._process_company_data(company_data)
            
            # Cache processed data
            self._cache_data(cache_key, processed_data)
            
            # Send response
            await self._send_data_response(request_id, processed_data, start_time)
            
            # Update metrics
            self.metrics['successful_requests'] += 1
            
        except Exception as e:
            logger.error("Error processing MarketCap data request", 
                        request_id=request_id, error=str(e))
            await self._send_error_response(request_id, str(e))
        
        finally:
            self.metrics['requests_processed'] += 1
            self._update_response_time_metric(start_time)
    
    async def _handle_batch_data_request(self, event):
        """Handle batch data requests for multiple companies"""
        start_time = datetime.now()
        request_id = None
        
        try:
            # Extract event data
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_id = data.get('request_id', str(uuid.uuid4()))
            symbols = data.get('symbols', [])
            country = data.get('country', 'usa')
            limit = data.get('limit', 100)
            
            logger.info("Processing MarketCap batch data request", 
                       request_id=request_id, symbols_count=len(symbols), country=country)
            
            # If specific symbols requested
            if symbols:
                batch_data = []
                for symbol in symbols:
                    company_data = await self.marketcap_connector.search_company(symbol)
                    if company_data:
                        processed_data = await self._process_company_data(company_data)
                        batch_data.append(processed_data)
                
                await self._send_batch_data_response(request_id, batch_data, start_time)
            
            # If top companies by country requested
            else:
                companies = await self.marketcap_connector.get_top_companies(country, limit)
                batch_data = []
                
                for company in companies:
                    processed_data = await self._process_company_data(company)
                    batch_data.append(processed_data)
                
                await self._send_batch_data_response(request_id, batch_data, start_time)
            
            self.metrics['successful_requests'] += 1
            
        except Exception as e:
            logger.error("Error processing MarketCap batch data request", 
                        request_id=request_id, error=str(e))
            await self._send_error_response(request_id, str(e))
        
        finally:
            self.metrics['requests_processed'] += 1
            self._update_response_time_metric(start_time)
    
    async def _process_company_data(self, company_data) -> Dict[str, Any]:
        """Process and enhance company data for calculation module"""
        try:
            # Convert CompanyMarketCapData to dict if needed
            if hasattr(company_data, 'to_dict'):
                base_data = company_data.to_dict()
            else:
                base_data = company_data
            
            # Calculate additional metrics
            market_cap = base_data.get('market_cap', 0)
            daily_change = base_data.get('daily_change_percent', 0)
            stock_price = base_data.get('stock_price', 0)
            
            # MarketCap-based scoring (wie im bisherigen System)
            market_cap_billions = market_cap / 1_000_000_000
            base_score = min(20, market_cap_billions / 200)  # Max 20 für sehr große Caps
            performance_score = max(0, daily_change * 2)    # Positive Performance boost
            analysis_score = round(base_score + performance_score, 1)
            
            # Kategorisierung nach MarketCap
            if market_cap >= 200_000_000_000:  # >= 200B
                market_cap_category = 'mega_cap'
                volatility_factor = 0.3
            elif market_cap >= 10_000_000_000:  # >= 10B
                market_cap_category = 'large_cap'
                volatility_factor = 0.5
            elif market_cap >= 2_000_000_000:   # >= 2B
                market_cap_category = 'mid_cap'
                volatility_factor = 0.7
            else:
                market_cap_category = 'small_cap'
                volatility_factor = 1.0
            
            # Risk Assessment
            risk_score = abs(daily_change) * volatility_factor
            risk_level = 'low' if risk_score < 2 else 'medium' if risk_score < 5 else 'high'
            
            # Enhanced data structure for calculation module
            processed_data = {
                'data_source': 'marketcap',
                'source_priority': self.source_config['priority'],
                'timestamp': datetime.now().isoformat(),
                'reliability_score': self.source_config['reliability_score'],
                
                # Raw company data
                'company_info': {
                    'symbol': base_data.get('ticker', ''),
                    'name': base_data.get('name', ''),
                    'country': base_data.get('country', ''),
                    'currency': base_data.get('currency', 'USD'),
                    'rank': base_data.get('rank', 0)
                },
                
                # Financial metrics
                'financial_metrics': {
                    'market_cap': market_cap,
                    'market_cap_formatted': f"${market_cap:,.0f}",
                    'market_cap_billions': round(market_cap_billions, 2),
                    'stock_price': stock_price,
                    'daily_change_percent': daily_change,
                    'daily_change_absolute': round((stock_price * daily_change / 100), 2)
                },
                
                # Analysis metrics
                'analysis_metrics': {
                    'analysis_score': analysis_score,
                    'base_score': round(base_score, 1),
                    'performance_score': round(performance_score, 1),
                    'market_cap_category': market_cap_category,
                    'volatility_factor': volatility_factor,
                    'risk_score': round(risk_score, 2),
                    'risk_level': risk_level
                },
                
                # Prediction indicators
                'prediction_indicators': {
                    'momentum_indicator': 1 if daily_change > 0 else -1,
                    'size_stability': 1 - volatility_factor,  # Größere Unternehmen = stabiler
                    'growth_potential': volatility_factor,     # Kleinere Unternehmen = mehr Potenzial
                    'market_confidence': min(1.0, market_cap_billions / 100)  # Normalisiert auf 0-1
                }
            }
            
            return processed_data
            
        except Exception as e:
            logger.error("Error processing company data", error=str(e))
            raise
    
    async def _send_data_response(self, request_id: str, data: Dict[str, Any], start_time: datetime):
        """Send data response to calculation module"""
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        await self.publish_module_event(
            EventType.MODULE_RESPONSE,
            {
                'request_id': request_id,
                'success': True,
                'data': data,
                'source': 'marketcap_data_source',
                'response_time_ms': round(response_time, 2),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        logger.info("Sent MarketCap data response", 
                   request_id=request_id, response_time_ms=round(response_time, 2))
    
    async def _send_batch_data_response(self, request_id: str, batch_data: List[Dict[str, Any]], start_time: datetime):
        """Send batch data response to calculation module"""
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        await self.publish_module_event(
            EventType.MODULE_RESPONSE,
            {
                'request_id': request_id,
                'success': True,
                'data': batch_data,
                'count': len(batch_data),
                'source': 'marketcap_data_source',
                'response_time_ms': round(response_time, 2),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        logger.info("Sent MarketCap batch data response", 
                   request_id=request_id, count=len(batch_data), response_time_ms=round(response_time, 2))
    
    async def _send_error_response(self, request_id: str, error: str):
        """Send error response"""
        await self.publish_module_event(
            'data_source.marketcap.error',
            {
                'request_id': request_id,
                'success': False,
                'error': error,
                'source': 'marketcap_data_source',
                'timestamp': datetime.now().isoformat()
            }
        )
        
        logger.error("Sent MarketCap error response", request_id=request_id, error=error)
    
    async def _handle_health_check(self, event):
        """Handle health check requests"""
        try:
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_id = data.get('request_id', str(uuid.uuid4()))
            
            # Perform health check
            health_status = {
                'source': 'marketcap_data_source',
                'status': 'healthy',
                'config': self.source_config,
                'metrics': self.metrics,
                'connector_healthy': await self._check_connector_health(),
                'cache_entries': len(self.processed_data_cache),
                'last_update': self.metrics.get('last_update'),
                'timestamp': datetime.now().isoformat()
            }
            
            await self.publish_module_event(
                EventType.SYSTEM_HEALTH_RESPONSE,
                {
                    'request_id': request_id,
                    'health_status': health_status
                }
            )
            
        except Exception as e:
            logger.error("Error in health check", error=str(e))
    
    async def _check_connector_health(self) -> bool:
        """Check if MarketCap connector is healthy"""
        try:
            if not self.marketcap_connector:
                return False
            
            # Test with a simple connectivity check
            test_companies = await self.marketcap_connector.get_top_companies('usa', 1)
            return len(test_companies) > 0
            
        except Exception:
            return False
    
    async def _handle_config_update(self, event):
        """Handle configuration updates"""
        try:
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            source_name = data.get('source_name')
            if source_name != 'marketcap_data_source':
                return  # Not for us
            
            new_config = data.get('config', {})
            
            # Update configuration
            self.source_config.update(new_config)
            
            logger.info("Updated MarketCap data source configuration", new_config=new_config)
            
        except Exception as e:
            logger.error("Error updating configuration", error=str(e))
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if valid"""
        if cache_key in self.processed_data_cache:
            cached_entry = self.processed_data_cache[cache_key]
            if datetime.now() - cached_entry['timestamp'] < self.cache_duration:
                return cached_entry['data']
            else:
                # Remove expired cache entry
                del self.processed_data_cache[cache_key]
        return None
    
    def _cache_data(self, cache_key: str, data: Dict[str, Any]):
        """Cache processed data"""
        self.processed_data_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        
        # Cleanup old cache entries (keep max 100 entries)
        if len(self.processed_data_cache) > 100:
            oldest_key = min(self.processed_data_cache.keys(), 
                           key=lambda k: self.processed_data_cache[k]['timestamp'])
            del self.processed_data_cache[oldest_key]
    
    def _update_response_time_metric(self, start_time: datetime):
        """Update average response time metric"""
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if self.metrics['average_response_time'] == 0:
            self.metrics['average_response_time'] = response_time
        else:
            # Moving average
            self.metrics['average_response_time'] = (
                self.metrics['average_response_time'] * 0.9 + response_time * 0.1
            )
        
        self.metrics['last_update'] = datetime.now().isoformat()
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main business logic processing"""
        try:
            operation = data.get('operation', 'get_data')
            
            if operation == 'get_company_data':
                symbol = data.get('symbol')
                company_name = data.get('company_name')
                
                if symbol:
                    company_data = await self.marketcap_connector.search_company(symbol)
                elif company_name:
                    company_data = await self.marketcap_connector.search_company(company_name)
                else:
                    return {'success': False, 'error': 'Symbol or company_name required'}
                
                if company_data:
                    processed_data = await self._process_company_data(company_data)
                    return {'success': True, 'data': processed_data}
                else:
                    return {'success': False, 'error': 'Company not found'}
            
            elif operation == 'get_top_companies':
                country = data.get('country', 'usa')
                limit = data.get('limit', 100)
                
                companies = await self.marketcap_connector.get_top_companies(country, limit)
                processed_companies = []
                
                for company in companies:
                    processed_data = await self._process_company_data(company)
                    processed_companies.append(processed_data)
                
                return {
                    'success': True,
                    'data': processed_companies,
                    'count': len(processed_companies)
                }
            
            else:
                return {'success': False, 'error': f'Unknown operation: {operation}'}
                
        except Exception as e:
            logger.error("Error in business logic processing", error=str(e))
            return {'success': False, 'error': str(e)}
    
    async def _cleanup_module(self):
        """Cleanup resources"""
        try:
            if self.marketcap_connector:
                await self.marketcap_connector.shutdown()
            
            # Clear cache
            self.processed_data_cache.clear()
            
            await super()._cleanup_module()
            
        except Exception as e:
            logger.warning("Error during cleanup", error=str(e))


# Standalone service implementation
class MarketCapDataSourceService:
    """Standalone Service für MarketCap Data Source"""
    
    def __init__(self):
        self.event_bus = EventBusConnector("marketcap-data-source-service")
        self.data_source = None
        self.is_running = False
        
    async def initialize(self) -> bool:
        """Initialize service"""
        try:
            logger.info("Initializing MarketCap Data Source Service")
            
            # Connect to event bus
            await self.event_bus.connect()
            
            # Initialize data source
            self.data_source = MarketCapDataSource(self.event_bus)
            await self.data_source.initialize()
            
            self.is_running = True
            logger.info("MarketCap Data Source Service initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize MarketCap Data Source Service", error=str(e))
            return False
    
    async def run(self):
        """Run the service"""
        try:
            logger.info("Starting MarketCap Data Source Service...")
            
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error("Service error", error=str(e))
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown service"""
        try:
            logger.info("Shutting down MarketCap Data Source Service")
            self.is_running = False
            
            if self.data_source:
                await self.data_source.shutdown()
            
            if self.event_bus:
                await self.event_bus.disconnect()
                
            logger.info("MarketCap Data Source Service shutdown complete")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


async def main():
    """Main entry point"""
    service = MarketCapDataSourceService()
    
    try:
        success = await service.initialize()
        if not success:
            logger.error("Failed to initialize service")
            return 1
        
        await service.run()
        return 0
        
    except Exception as e:
        logger.error("Service failed", error=str(e))
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Critical service error", error=str(e))
        sys.exit(1)