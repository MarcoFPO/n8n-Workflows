"""
Market Data Module für Broker-Gateway-Service
Real-time Market Data und Price Feeds
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from backend_base_module import BackendBaseModule
from event_bus import EventType
import structlog


class MarketData(BaseModel):
    instrument_code: str
    last_price: str
    best_bid: str
    best_ask: str
    price_change: str
    price_change_percentage: str
    high_24h: str
    low_24h: str
    volume_24h: str
    timestamp: datetime


class MarketDataModule(BackendBaseModule):
    """Market Data Management und Real-time Price Feeds"""
    
    def __init__(self, event_bus):
        super().__init__("market_data", event_bus)
        self.market_data_cache = {}
        self.price_feeds = {}
        self.supported_instruments = []
        self.cache_ttl = 30  # 30 Sekunden für Market Data
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _initialize_module(self) -> bool:
        """Initialize market data module"""
        try:
            self.logger.info("Initializing Market Data Module")
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "aktienanalyse-broker-gateway/1.0"}
            )
            
            # Initialize supported instruments
            self.supported_instruments = [
                "BTC_EUR", "ETH_EUR", "ADA_EUR", "DOT_EUR",
                "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"
            ]
            
            # Test market data fetch
            test_data = await self._fetch_mock_market_data("BTC_EUR")
            
            self.logger.info("Market data module initialized successfully",
                           supported_instruments=len(self.supported_instruments),
                           test_data_available=test_data is not None)
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize market data module", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        await self.subscribe_to_event(
            EventType.DATA_SYNCHRONIZED,
            self._handle_data_sync_event
        )
        await self.subscribe_to_event(
            EventType.CONFIG_UPDATED,
            self._handle_config_event
        )
        await self.subscribe_to_event(
            EventType.SYSTEM_ALERT_RAISED,
            self._handle_system_alert_event
        )
    
    async def _cleanup_module(self):
        """Cleanup module resources"""
        if self.session:
            await self.session.close()
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main market data processing logic"""
        try:
            request_type = data.get('type', 'get_market_data')
            
            if request_type == 'get_market_data':
                return await self._process_market_data_request(data)
            elif request_type == 'get_instruments':
                return await self._get_supported_instruments()
            elif request_type == 'price_feed':
                return await self._setup_price_feed(data)
            elif request_type == 'historical_data':
                return await self._get_historical_data(data)
            else:
                return {
                    'success': False,
                    'error': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            self.logger.error("Error in market data processing", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_market_data_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process market data request"""
        try:
            instrument_code = data.get('instrument_code', 'BTC_EUR')
            
            # Validate instrument
            if instrument_code not in self.supported_instruments:
                return {
                    'success': False,
                    'error': f'Instrument {instrument_code} not supported',
                    'supported_instruments': self.supported_instruments
                }
            
            # Check cache first
            cache_key = f"market_data_{instrument_code}"
            if cache_key in self.market_data_cache:
                cache_entry = self.market_data_cache[cache_key]
                cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
                if cache_age < self.cache_ttl:
                    self.logger.debug("Returning cached market data", instrument=instrument_code)
                    return {
                        'success': True,
                        'data': cache_entry['data'],
                        'source': 'cache',
                        'cache_age_seconds': cache_age
                    }
            
            # Fetch fresh market data
            market_data = await self._fetch_market_data(instrument_code)
            
            if market_data is None:
                return {
                    'success': False,
                    'error': f'Failed to fetch market data for {instrument_code}'
                }
            
            # Cache result
            self.market_data_cache[cache_key] = {
                'data': market_data,
                'timestamp': datetime.now()
            }
            
            # Publish market data event
            await self.publish_module_event(
                EventType.DATA_SYNCHRONIZED,
                {
                    'instrument': instrument_code,
                    'price': market_data.last_price,
                    'volume': market_data.volume_24h,
                    'source': 'market_data_module'
                },
                f"market-data-{instrument_code}"
            )
            
            return {
                'success': True,
                'data': market_data,
                'source': 'live',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error processing market data request", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _fetch_market_data(self, instrument_code: str) -> Optional[MarketData]:
        """Fetch market data from external API or mock data"""
        try:
            # For demo purposes, return mock data
            # In production, integrate with real market data providers
            
            if instrument_code.endswith('_EUR'):
                # Crypto pair
                return await self._fetch_crypto_market_data(instrument_code)
            else:
                # Stock symbol
                return await self._fetch_stock_market_data(instrument_code)
                
        except Exception as e:
            self.logger.error("Error fetching market data", 
                            instrument=instrument_code, 
                            error=str(e))
            return None
    
    async def _fetch_crypto_market_data(self, instrument_code: str) -> MarketData:
        """Fetch crypto market data (mock implementation)"""
        # Mock crypto data - in production use real Bitpanda Pro API
        base_prices = {
            "BTC_EUR": 45000.0,
            "ETH_EUR": 2800.0,
            "ADA_EUR": 0.85,
            "DOT_EUR": 12.50
        }
        
        base_price = base_prices.get(instrument_code, 1000.0)
        
        # Add some realistic variation
        import random
        price_variation = random.uniform(-0.05, 0.05)  # ±5% variation
        current_price = base_price * (1 + price_variation)
        
        # Calculate bid/ask spread (typically 0.1-0.5% for crypto)
        spread = current_price * 0.002  # 0.2% spread
        best_bid = current_price - spread / 2
        best_ask = current_price + spread / 2
        
        # Mock daily change
        daily_change = base_price * random.uniform(-0.08, 0.08)  # ±8% daily change
        daily_change_percent = (daily_change / base_price) * 100
        
        return MarketData(
            instrument_code=instrument_code,
            last_price=f"{current_price:.2f}",
            best_bid=f"{best_bid:.2f}",
            best_ask=f"{best_ask:.2f}",
            price_change=f"{daily_change:.2f}",
            price_change_percentage=f"{daily_change_percent:.2f}",
            high_24h=f"{current_price * 1.05:.2f}",
            low_24h=f"{current_price * 0.95:.2f}",
            volume_24h=f"{random.uniform(100, 1000):.1f}",
            timestamp=datetime.now()
        )
    
    async def _fetch_stock_market_data(self, symbol: str) -> MarketData:
        """Fetch stock market data (mock implementation)"""
        # Mock stock data - in production use real stock data API
        base_prices = {
            "AAPL": 180.0,
            "TSLA": 250.0,
            "MSFT": 380.0,
            "GOOGL": 140.0,
            "AMZN": 160.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # Add realistic stock variation
        import random
        price_variation = random.uniform(-0.03, 0.03)  # ±3% variation
        current_price = base_price * (1 + price_variation)
        
        # Stock bid/ask spread (typically tighter than crypto)
        spread = current_price * 0.001  # 0.1% spread
        best_bid = current_price - spread / 2
        best_ask = current_price + spread / 2
        
        # Mock daily change
        daily_change = base_price * random.uniform(-0.05, 0.05)  # ±5% daily change
        daily_change_percent = (daily_change / base_price) * 100
        
        return MarketData(
            instrument_code=symbol,
            last_price=f"{current_price:.2f}",
            best_bid=f"{best_bid:.2f}",
            best_ask=f"{best_ask:.2f}",
            price_change=f"{daily_change:.2f}",
            price_change_percentage=f"{daily_change_percent:.2f}",
            high_24h=f"{current_price * 1.04:.2f}",
            low_24h=f"{current_price * 0.96:.2f}",
            volume_24h=f"{random.uniform(1000000, 10000000):.0f}",
            timestamp=datetime.now()
        )
    
    async def _fetch_mock_market_data(self, instrument_code: str) -> Optional[MarketData]:
        """Fetch mock market data for testing"""
        try:
            if instrument_code.endswith('_EUR'):
                return await self._fetch_crypto_market_data(instrument_code)
            else:
                return await self._fetch_stock_market_data(instrument_code)
        except Exception as e:
            self.logger.error("Error fetching mock market data", error=str(e))
            return None
    
    async def _get_supported_instruments(self) -> Dict[str, Any]:
        """Get list of supported instruments"""
        return {
            'success': True,
            'instruments': self.supported_instruments,
            'crypto_pairs': [inst for inst in self.supported_instruments if '_' in inst],
            'stocks': [inst for inst in self.supported_instruments if '_' not in inst],
            'total_count': len(self.supported_instruments)
        }
    
    async def _setup_price_feed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Setup real-time price feed for instrument"""
        try:
            instrument_code = data.get('instrument_code')
            if not instrument_code:
                return {
                    'success': False,
                    'error': 'No instrument code provided'
                }
            
            if instrument_code not in self.supported_instruments:
                return {
                    'success': False,
                    'error': f'Instrument {instrument_code} not supported'
                }
            
            # Mock price feed setup (in production, establish WebSocket connection)
            feed_id = f"feed_{instrument_code}_{int(datetime.now().timestamp())}"
            
            self.price_feeds[feed_id] = {
                'instrument_code': instrument_code,
                'status': 'active',
                'created_at': datetime.now(),
                'last_update': datetime.now()
            }
            
            # Start mock price feed (in production, start WebSocket listener)
            asyncio.create_task(self._mock_price_feed_worker(feed_id, instrument_code))
            
            return {
                'success': True,
                'feed_id': feed_id,
                'instrument_code': instrument_code,
                'status': 'active'
            }
            
        except Exception as e:
            self.logger.error("Error setting up price feed", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _mock_price_feed_worker(self, feed_id: str, instrument_code: str):
        """Mock price feed worker (simulates real-time updates)"""
        try:
            while feed_id in self.price_feeds:
                # Fetch updated market data
                market_data = await self._fetch_market_data(instrument_code)
                
                if market_data:
                    # Update cache
                    cache_key = f"market_data_{instrument_code}"
                    self.market_data_cache[cache_key] = {
                        'data': market_data,
                        'timestamp': datetime.now()
                    }
                    
                    # Update feed status
                    if feed_id in self.price_feeds:
                        self.price_feeds[feed_id]['last_update'] = datetime.now()
                    
                    # Publish real-time data event
                    await self.publish_module_event(
                        EventType.DATA_SYNCHRONIZED,
                        {
                            'instrument': instrument_code,
                            'price': market_data.last_price,
                            'feed_id': feed_id,
                            'update_type': 'real_time'
                        },
                        f"price-feed-{instrument_code}"
                    )
                
                # Wait before next update (30 seconds for mock)
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            self.logger.info("Price feed worker cancelled", feed_id=feed_id)
        except Exception as e:
            self.logger.error("Error in price feed worker", 
                            feed_id=feed_id, 
                            error=str(e))
    
    async def _get_historical_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get historical market data"""
        try:
            instrument_code = data.get('instrument_code')
            period = data.get('period', '1d')  # 1d, 1w, 1m
            
            if not instrument_code:
                return {
                    'success': False,
                    'error': 'No instrument code provided'
                }
            
            # Mock historical data (in production, fetch from data provider)
            periods = {'1d': 24, '1w': 168, '1m': 720}  # hours
            hours = periods.get(period, 24)
            
            historical_data = []
            current_time = datetime.now()
            
            # Generate mock historical data points
            for i in range(hours):
                timestamp = current_time - timedelta(hours=i)
                
                # Get base price and add historical variation
                market_data = await self._fetch_mock_market_data(instrument_code)
                if market_data:
                    import random
                    historical_price = float(market_data.last_price) * (1 + random.uniform(-0.02, 0.02))
                    historical_volume = float(market_data.volume_24h) * (1 + random.uniform(-0.3, 0.3))
                    
                    historical_data.append({
                        'timestamp': timestamp.isoformat(),
                        'price': f"{historical_price:.2f}",
                        'volume': f"{historical_volume:.1f}"
                    })
            
            return {
                'success': True,
                'instrument_code': instrument_code,
                'period': period,
                'data_points': len(historical_data),
                'historical_data': historical_data[::-1]  # Reverse to chronological order
            }
            
        except Exception as e:
            self.logger.error("Error getting historical data", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_data_sync_event(self, event):
        """Handle data synchronization events"""
        try:
            self.logger.debug("Received data sync event")
            # Clear market data cache on sync events
            self.market_data_cache.clear()
        except Exception as e:
            self.logger.error("Error handling data sync event", error=str(e))
    
    async def _handle_config_event(self, event):
        """Handle configuration update events"""
        try:
            self.logger.info("Received config update event")
            
            # Update supported instruments if provided
            config_data = event.data
            if 'supported_instruments' in config_data:
                self.supported_instruments = config_data['supported_instruments']
                self.logger.info("Supported instruments updated", 
                               count=len(self.supported_instruments))
            
            # Update cache TTL if provided
            if 'market_data_cache_ttl' in config_data:
                self.cache_ttl = config_data['market_data_cache_ttl']
                self.logger.info("Market data cache TTL updated", ttl=self.cache_ttl)
                
        except Exception as e:
            self.logger.error("Error handling config event", error=str(e))
    
    async def _handle_system_alert_event(self, event):
        """Handle system alert events"""
        try:
            self.logger.info("Received system alert event")
            
            alert_type = event.data.get('alert_type')
            if alert_type == 'market_data_outage':
                # Handle market data outage
                self.logger.warning("Market data outage reported")
                # Could implement fallback data sources
                
        except Exception as e:
            self.logger.error("Error handling system alert event", error=str(e))
    
    def get_active_feeds(self) -> Dict[str, Any]:
        """Get information about active price feeds"""
        return {
            'active_feeds': len(self.price_feeds),
            'feeds': {
                feed_id: {
                    'instrument_code': feed_info['instrument_code'],
                    'status': feed_info['status'],
                    'uptime_seconds': (datetime.now() - feed_info['created_at']).total_seconds(),
                    'last_update': feed_info['last_update'].isoformat()
                }
                for feed_id, feed_info in self.price_feeds.items()
            }
        }
    
    def stop_price_feed(self, feed_id: str) -> bool:
        """Stop a specific price feed"""
        try:
            if feed_id in self.price_feeds:
                del self.price_feeds[feed_id]
                self.logger.info("Price feed stopped", feed_id=feed_id)
                return True
            return False
        except Exception as e:
            self.logger.error("Error stopping price feed", feed_id=feed_id, error=str(e))
            return False