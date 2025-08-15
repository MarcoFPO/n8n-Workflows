"""
Market Data Fetcher Module - Single Function Module
Fetches market data from Yahoo Finance
"""

import yfinance as yf
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase
from event_bus import EventType


class MarketDataFetcherModule(SingleFunctionModuleBase):
    """Fetch market data from external sources (yFinance)"""
    
    def __init__(self, event_bus):
        super().__init__("market_data_fetcher", event_bus)
        self.data_cache = {}
        self.cache_ttl = 60  # 1 Minute für Market Data
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('market_data.fetch.request', self.process_event)
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions", error=str(e))
    
    async def process_event(self, event):
        """Process incoming events"""
        event_type = event.get('event_type', '')
        
        if event_type == 'system.health.request':
            health_response = {
                'event_type': 'system.health.response',
                'module': self.module_name,
                'status': 'healthy',
                'cache_size': len(self.data_cache),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'market_data.fetch.request':
            symbol = event.get('symbol', '')
            period = event.get('period', '1mo')
            
            market_data = await self.fetch_market_data(symbol, period)
            
            response_event = {
                'event_type': 'market_data.fetch.response',
                'symbol': symbol,
                'period': period,
                'success': market_data is not None,
                'data': market_data.to_dict('records') if market_data is not None else None,
                'data_points': len(market_data) if market_data is not None else 0,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def fetch_market_data(self, symbol: str, period: str) -> pd.DataFrame:
        """Fetch market data from Yahoo Finance"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{period}"
            if cache_key in self.data_cache:
                cache_entry = self.data_cache[cache_key]
                cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
                if cache_age < self.cache_ttl:
                    self.logger.debug("Returning cached market data", 
                                    symbol=symbol, 
                                    cache_age=cache_age)
                    return cache_entry['data']
            
            # Fetch from yFinance
            ticker = yf.Ticker(symbol)
            hist_data = ticker.history(period=period)
            
            if hist_data.empty:
                self.logger.warning("No market data found", symbol=symbol)
                return None
            
            # Cache the result
            self.data_cache[cache_key] = {
                'data': hist_data,
                'timestamp': datetime.now()
            }
            
            # Cleanup old cache entries
            await self._cleanup_old_cache_entries()
            
            self.logger.info("Market data fetched successfully", 
                           symbol=symbol, 
                           period=period,
                           data_points=len(hist_data))
            return hist_data
            
        except Exception as e:
            self.logger.error("Failed to fetch market data", 
                            symbol=symbol, 
                            period=period,
                            error=str(e))
            return None
    
    async def _cleanup_old_cache_entries(self):
        """Remove old cache entries to prevent memory buildup"""
        try:
            current_time = datetime.now()
            keys_to_remove = []
            
            for key, entry in self.data_cache.items():
                cache_age = (current_time - entry['timestamp']).total_seconds()
                if cache_age > self.cache_ttl * 10:  # Remove after 10x TTL
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.data_cache[key]
            
            if keys_to_remove:
                self.logger.debug("Cache cleanup completed", 
                                entries_removed=len(keys_to_remove))
                
        except Exception as e:
            self.logger.error("Error during cache cleanup", error=str(e))
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'market_data_fetcher',
            'cache_entries': len(self.data_cache),
            'cache_ttl_seconds': self.cache_ttl,
            'description': 'Fetches market data from Yahoo Finance with caching'
        }