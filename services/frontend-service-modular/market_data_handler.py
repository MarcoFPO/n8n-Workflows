"""
Market Data Handler - Single Function Module
Verantwortlich ausschließlich für Market Data Management Logic
"""

from typing import Dict, Any, List, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, timedelta, BaseModel, structlog
)
from modules.single_function_module_base import SingleFunctionModule
from shared.event_bus import Event, EventType


class MarketDataRequest(BaseModel):
    request_type: str  # 'get_symbol', 'get_watchlist', 'update_data', 'add_to_watchlist', 'remove_from_watchlist'
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = None  # '1m', '5m', '15m', '1h', '4h', '1d', '1w'
    limit: Optional[int] = None


class MarketDataPoint(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    timestamp: datetime
    source: str = "bitpanda_simulation"


class WatchlistEntry(BaseModel):
    symbol: str
    display_name: str
    category: str  # 'crypto', 'stocks', 'forex', 'commodities'
    priority: int  # 1-5, 1 = highest priority
    alerts_enabled: bool = True
    price_alert_threshold: Optional[float] = None
    added_timestamp: datetime
    last_viewed: Optional[datetime] = None


class MarketDataResult(BaseModel):
    data_successful: bool
    market_data: Dict[str, MarketDataPoint]
    watchlist_symbols: List[str]
    watchlist_details: Dict[str, WatchlistEntry]
    data_timestamp: datetime
    data_source: str
    market_status: str  # 'open', 'closed', 'pre_market', 'after_hours'
    next_market_event: Optional[str] = None
    data_warnings: List[str]


class MarketDataHandler(SingleFunctionModule):
    """
    Single Function Module: Market Data Management
    Verantwortlichkeit: Ausschließlich Market-Data-Management-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("market_data_handler", event_bus)
        
        # Market Data Storage
        self.market_data = {
            "AAPL": MarketDataPoint(
                symbol="AAPL",
                price=182.50,
                change=2.75,
                change_percent=1.53,
                volume=45230000,
                bid=182.45,
                ask=182.55,
                high_24h=184.20,
                low_24h=179.80,
                timestamp=datetime.now(),
                source="bitpanda_simulation"
            ),
            "MSFT": MarketDataPoint(
                symbol="MSFT",
                price=378.90,
                change=-1.25,
                change_percent=-0.33,
                volume=28450000,
                bid=378.85,
                ask=378.95,
                high_24h=381.50,
                low_24h=376.20,
                timestamp=datetime.now(),
                source="bitpanda_simulation"
            ),
            "GOOGL": MarketDataPoint(
                symbol="GOOGL",
                price=142.85,
                change=0.95,
                change_percent=0.67,
                volume=19870000,
                bid=142.80,
                ask=142.90,
                high_24h=144.20,
                low_24h=141.50,
                timestamp=datetime.now(),
                source="bitpanda_simulation"
            ),
            "TSLA": MarketDataPoint(
                symbol="TSLA",
                price=248.75,
                change=-8.50,
                change_percent=-3.31,
                volume=89450000,
                bid=248.60,
                ask=248.80,
                high_24h=259.80,
                low_24h=246.90,
                timestamp=datetime.now(),
                source="bitpanda_simulation"
            ),
            "BTC": MarketDataPoint(
                symbol="BTC",
                price=43250.00,
                change=1150.00,
                change_percent=2.73,
                volume=1250000000,
                bid=43245.00,
                ask=43255.00,
                high_24h=43580.00,
                low_24h=41900.00,
                timestamp=datetime.now(),
                source="bitpanda_simulation"
            ),
            "ETH": MarketDataPoint(
                symbol="ETH",
                price=2385.75,
                change=85.25,
                change_percent=3.71,
                volume=890000000,
                bid=2384.50,
                ask=2387.00,
                high_24h=2420.00,
                low_24h=2290.00,
                timestamp=datetime.now(),
                source="bitpanda_simulation"
            )
        }
        
        # Watchlist Management
        self.watchlist_entries = {
            "AAPL": WatchlistEntry(
                symbol="AAPL",
                display_name="Apple Inc.",
                category="stocks",
                priority=1,
                alerts_enabled=True,
                price_alert_threshold=180.00,
                added_timestamp=datetime.now() - timedelta(days=30),
                last_viewed=datetime.now() - timedelta(hours=2)
            ),
            "MSFT": WatchlistEntry(
                symbol="MSFT",
                display_name="Microsoft Corporation",
                category="stocks",
                priority=1,
                alerts_enabled=True,
                added_timestamp=datetime.now() - timedelta(days=25),
                last_viewed=datetime.now() - timedelta(hours=1)
            ),
            "GOOGL": WatchlistEntry(
                symbol="GOOGL",
                display_name="Alphabet Inc.",
                category="stocks",
                priority=2,
                alerts_enabled=True,
                added_timestamp=datetime.now() - timedelta(days=20),
                last_viewed=datetime.now() - timedelta(minutes=30)
            ),
            "TSLA": WatchlistEntry(
                symbol="TSLA",
                display_name="Tesla Inc.",
                category="stocks",
                priority=2,
                alerts_enabled=True,
                price_alert_threshold=250.00,
                added_timestamp=datetime.now() - timedelta(days=15),
                last_viewed=datetime.now() - timedelta(hours=3)
            ),
            "BTC": WatchlistEntry(
                symbol="BTC",
                display_name="Bitcoin",
                category="crypto",
                priority=1,
                alerts_enabled=True,
                price_alert_threshold=45000.00,
                added_timestamp=datetime.now() - timedelta(days=45),
                last_viewed=datetime.now() - timedelta(minutes=5)
            ),
            "ETH": WatchlistEntry(
                symbol="ETH",
                display_name="Ethereum",
                category="crypto",
                priority=1,
                alerts_enabled=True,
                price_alert_threshold=2500.00,
                added_timestamp=datetime.now() - timedelta(days=40),
                last_viewed=datetime.now() - timedelta(minutes=10)
            )
        }
        
        # Market Data Configuration
        self.market_config = {
            'auto_refresh_enabled': True,
            'refresh_interval_seconds': 30,
            'max_watchlist_size': 50,
            'enable_real_time_updates': True,
            'cache_market_data': True,
            'cache_expiry_seconds': 60,
            'enable_price_alerts': True,
            'alert_price_threshold_percent': 2.0,  # Alert for 2%+ price changes
            'supported_timeframes': ['1m', '5m', '15m', '1h', '4h', '1d', '1w'],
            'data_provider': 'bitpanda_simulation',
            'fallback_providers': ['yahoo_finance', 'alpha_vantage']
        }
        
        # Market Status Tracking
        self.market_status = {
            'current_status': 'open',  # 'open', 'closed', 'pre_market', 'after_hours'
            'next_market_open': None,
            'next_market_close': None,
            'trading_session': 'regular',
            'timezone': 'Europe/Berlin'
        }
        
        # Market Data Processing History
        self.market_history = []
        self.market_counter = 0
        
        # Price Alert Tracking
        self.triggered_alerts = []
        self.alert_counter = 0
        
        # Historical Data Cache (simplified)
        self.historical_data_cache = {}
        
        # Market Categories
        self.market_categories = {
            'stocks': {
                'display_name': 'Stocks',
                'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN', 'META'],
                'market_hours': {'open': '15:30', 'close': '22:00'},  # UTC+1
                'currency': 'USD'
            },
            'crypto': {
                'display_name': 'Cryptocurrency',
                'symbols': ['BTC', 'ETH', 'ADA', 'DOT', 'SOL', 'AVAX'],
                'market_hours': {'open': '00:00', 'close': '23:59'},  # 24/7
                'currency': 'EUR'
            },
            'forex': {
                'display_name': 'Forex',
                'symbols': ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD'],
                'market_hours': {'open': '22:00', 'close': '22:00'},  # 24/5
                'currency': 'USD'
            },
            'commodities': {
                'display_name': 'Commodities',
                'symbols': ['GOLD', 'SILVER', 'OIL', 'GAS'],
                'market_hours': {'open': '09:00', 'close': '17:30'},
                'currency': 'USD'
            }
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Market Data Management
        
        Args:
            input_data: {
                'request_type': required string ('get_symbol', 'get_watchlist', 'update_data', 'add_to_watchlist', 'remove_from_watchlist'),
                'symbol': optional string for single symbol requests,
                'symbols': optional list of symbols for multi-symbol requests,
                'timeframe': optional string for historical data,
                'limit': optional int for limiting results,
                'force_refresh': optional bool (default: false),
                'include_historical': optional bool (default: false),
                'alert_check': optional bool (default: true)
            }
            
        Returns:
            Dict mit Market-Data-Result
        """
        start_time = datetime.now()
        
        try:
            # Market Data Request erstellen
            market_request = MarketDataRequest(
                request_type=input_data.get('request_type'),
                symbol=input_data.get('symbol'),
                symbols=input_data.get('symbols'),
                timeframe=input_data.get('timeframe'),
                limit=input_data.get('limit')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid market data request: {str(e)}'
            }
        
        force_refresh = input_data.get('force_refresh', False)
        include_historical = input_data.get('include_historical', False)
        alert_check = input_data.get('alert_check', True)
        
        # Market Data Processing
        market_result = await self._process_market_data_request(
            market_request, force_refresh, include_historical, alert_check
        )
        
        # Statistics Update
        self.market_counter += 1
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Market History
        self.market_history.append({
            'timestamp': datetime.now(),
            'request_type': market_request.request_type,
            'symbol': market_request.symbol,
            'data_successful': market_result.data_successful,
            'symbols_count': len(market_result.market_data),
            'warnings_count': len(market_result.data_warnings),
            'processing_time_ms': processing_time_ms,
            'market_id': self.market_counter
        })
        
        # Limit History
        if len(self.market_history) > 300:
            self.market_history.pop(0)
        
        # Event Publishing für Market Data Updates
        await self._publish_market_data_event(market_result, market_request)
        
        self.logger.info(f"Market data request processed",
                       request_type=market_request.request_type,
                       symbol=market_request.symbol,
                       data_successful=market_result.data_successful,
                       symbols_count=len(market_result.market_data),
                       warnings_count=len(market_result.data_warnings),
                       processing_time_ms=round(processing_time_ms, 2),
                       market_id=self.market_counter)
        
        return {
            'success': True,
            'data_successful': market_result.data_successful,
            'market_data': {k: {
                'symbol': v.symbol,
                'price': v.price,
                'change': v.change,
                'change_percent': v.change_percent,
                'volume': v.volume,
                'bid': v.bid,
                'ask': v.ask,
                'high_24h': v.high_24h,
                'low_24h': v.low_24h,
                'timestamp': v.timestamp.isoformat(),
                'source': v.source
            } for k, v in market_result.market_data.items()},
            'watchlist_symbols': market_result.watchlist_symbols,
            'watchlist_details': {k: {
                'symbol': v.symbol,
                'display_name': v.display_name,
                'category': v.category,
                'priority': v.priority,
                'alerts_enabled': v.alerts_enabled,
                'price_alert_threshold': v.price_alert_threshold,
                'added_timestamp': v.added_timestamp.isoformat(),
                'last_viewed': v.last_viewed.isoformat() if v.last_viewed else None
            } for k, v in market_result.watchlist_details.items()},
            'data_timestamp': market_result.data_timestamp.isoformat(),
            'data_source': market_result.data_source,
            'market_status': market_result.market_status,
            'next_market_event': market_result.next_market_event,
            'data_warnings': market_result.data_warnings
        }
    
    async def _process_market_data_request(self, request: MarketDataRequest,
                                         force_refresh: bool,
                                         include_historical: bool,
                                         alert_check: bool) -> MarketDataResult:
        """Verarbeitet Market Data Request komplett"""
        
        data_warnings = []
        
        if request.request_type == 'get_symbol':
            # Einzelnes Symbol abrufen
            if not request.symbol:
                data_warnings.append('No symbol specified for get_symbol request')
                market_data = {}
            else:
                market_data = await self._get_symbol_data(request.symbol, force_refresh)
                if not market_data:
                    data_warnings.append(f'Symbol {request.symbol} not found')
                
        elif request.request_type == 'get_watchlist':
            # Watchlist Daten abrufen
            market_data = await self._get_watchlist_data(force_refresh)
            
        elif request.request_type == 'update_data':
            # Market Data aktualisieren
            symbols_to_update = request.symbols or list(self.watchlist_entries.keys())
            market_data = await self._update_market_data(symbols_to_update)
            
        elif request.request_type == 'add_to_watchlist':
            # Symbol zur Watchlist hinzufügen
            if request.symbol:
                await self._add_to_watchlist(request.symbol)
                market_data = await self._get_watchlist_data(force_refresh)
            else:
                data_warnings.append('No symbol specified for add_to_watchlist')
                market_data = {}
                
        elif request.request_type == 'remove_from_watchlist':
            # Symbol aus Watchlist entfernen
            if request.symbol:
                await self._remove_from_watchlist(request.symbol)
                market_data = await self._get_watchlist_data(force_refresh)
            else:
                data_warnings.append('No symbol specified for remove_from_watchlist')
                market_data = {}
                
        else:
            # Fallback: Watchlist abrufen
            market_data = await self._get_watchlist_data(force_refresh)
            data_warnings.append(f'Unknown request type: {request.request_type}, fallback to watchlist')
        
        # Price Alerts prüfen
        if alert_check:
            await self._check_price_alerts(market_data)
        
        # Market Status aktualisieren
        market_status = await self._get_current_market_status()
        
        return MarketDataResult(
            data_successful=len(market_data) > 0,
            market_data=market_data,
            watchlist_symbols=list(self.watchlist_entries.keys()),
            watchlist_details=self.watchlist_entries,
            data_timestamp=datetime.now(),
            data_source=self.market_config['data_provider'],
            market_status=market_status['status'],
            next_market_event=market_status.get('next_event'),
            data_warnings=data_warnings
        )
    
    async def _get_symbol_data(self, symbol: str, force_refresh: bool = False) -> Dict[str, MarketDataPoint]:
        """Holt Daten für einzelnes Symbol"""
        
        symbol = symbol.upper()
        
        if symbol not in self.market_data:
            return {}
        
        # Cache Check
        if not force_refresh:
            data_age = (datetime.now() - self.market_data[symbol].timestamp).total_seconds()
            if data_age < self.market_config['cache_expiry_seconds']:
                return {symbol: self.market_data[symbol]}
        
        # Data Refresh
        await self._refresh_symbol_data(symbol)
        
        return {symbol: self.market_data[symbol]}
    
    async def _get_watchlist_data(self, force_refresh: bool = False) -> Dict[str, MarketDataPoint]:
        """Holt Daten für alle Watchlist Symbols"""
        
        watchlist_data = {}
        
        for symbol in self.watchlist_entries.keys():
            symbol_data = await self._get_symbol_data(symbol, force_refresh)
            watchlist_data.update(symbol_data)
        
        # Update last_viewed for watchlist entries
        current_time = datetime.now()
        for symbol in watchlist_data.keys():
            if symbol in self.watchlist_entries:
                self.watchlist_entries[symbol].last_viewed = current_time
        
        return watchlist_data
    
    async def _update_market_data(self, symbols: List[str]) -> Dict[str, MarketDataPoint]:
        """Aktualisiert Market Data für spezifische Symbols"""
        
        updated_data = {}
        
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol in self.market_data:
                await self._refresh_symbol_data(symbol)
                updated_data[symbol] = self.market_data[symbol]
        
        return updated_data
    
    async def _refresh_symbol_data(self, symbol: str):
        """Refresht Daten für einzelnes Symbol"""
        
        # Mock Data Refresh - in Produktion würde hier API-Call stattfinden
        import random
        
        if symbol in self.market_data:
            current_data = self.market_data[symbol]
            
            # Realistische Preisbewegung simulieren
            price_change_percent = random.uniform(-0.05, 0.05)  # ±5% max change
            new_price = current_data.price * (1 + price_change_percent)
            absolute_change = new_price - current_data.price
            
            # Volume Simulation
            volume_change = random.uniform(0.8, 1.2)  # ±20% volume change
            new_volume = int(current_data.volume * volume_change)
            
            # Bid/Ask Spread Simulation
            spread_percent = 0.001  # 0.1% spread
            bid_price = new_price * (1 - spread_percent)
            ask_price = new_price * (1 + spread_percent)
            
            # 24h High/Low Update
            new_high = max(current_data.high_24h or 0, new_price)
            new_low = min(current_data.low_24h or float('inf'), new_price)
            
            # Update Market Data Point
            self.market_data[symbol] = MarketDataPoint(
                symbol=symbol,
                price=round(new_price, 2),
                change=round(absolute_change, 2),
                change_percent=round(price_change_percent * 100, 2),
                volume=new_volume,
                bid=round(bid_price, 2),
                ask=round(ask_price, 2),
                high_24h=round(new_high, 2),
                low_24h=round(new_low, 2),
                timestamp=datetime.now(),
                source=self.market_config['data_provider']
            )
    
    async def _add_to_watchlist(self, symbol: str):
        """Fügt Symbol zur Watchlist hinzu"""
        
        symbol = symbol.upper()
        
        # Check if already in watchlist
        if symbol in self.watchlist_entries:
            self.logger.info(f"Symbol already in watchlist: {symbol}")
            return
        
        # Check watchlist size limit
        if len(self.watchlist_entries) >= self.market_config['max_watchlist_size']:
            self.logger.warning(f"Watchlist size limit reached: {self.market_config['max_watchlist_size']}")
            return
        
        # Determine category based on symbol
        category = await self._determine_symbol_category(symbol)
        
        # Create watchlist entry
        self.watchlist_entries[symbol] = WatchlistEntry(
            symbol=symbol,
            display_name=await self._get_symbol_display_name(symbol),
            category=category,
            priority=3,  # Default priority
            alerts_enabled=True,
            added_timestamp=datetime.now()
        )
        
        # Initialize market data if not exists
        if symbol not in self.market_data:
            await self._initialize_symbol_data(symbol)
        
        self.logger.info(f"Added symbol to watchlist",
                       symbol=symbol,
                       category=category,
                       watchlist_size=len(self.watchlist_entries))
    
    async def _remove_from_watchlist(self, symbol: str):
        """Entfernt Symbol aus Watchlist"""
        
        symbol = symbol.upper()
        
        if symbol not in self.watchlist_entries:
            self.logger.warning(f"Symbol not in watchlist: {symbol}")
            return
        
        # Remove from watchlist
        del self.watchlist_entries[symbol]
        
        self.logger.info(f"Removed symbol from watchlist",
                       symbol=symbol,
                       watchlist_size=len(self.watchlist_entries))
    
    async def _determine_symbol_category(self, symbol: str) -> str:
        """Bestimmt Kategorie für Symbol"""
        
        # Crypto symbols
        if symbol in ['BTC', 'ETH', 'ADA', 'DOT', 'SOL', 'AVAX', 'MATIC', 'LINK']:
            return 'crypto'
        
        # Stock symbols (common US stocks)
        if symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD']:
            return 'stocks'
        
        # Forex pairs
        if '/' in symbol and len(symbol.split('/')) == 2:
            return 'forex'
        
        # Commodities
        if symbol in ['GOLD', 'SILVER', 'OIL', 'GAS']:
            return 'commodities'
        
        # Default to stocks
        return 'stocks'
    
    async def _get_symbol_display_name(self, symbol: str) -> str:
        """Holt Display Name für Symbol"""
        
        # Mock Display Names - in Produktion würde aus API/Database kommen
        display_names = {
            'AAPL': 'Apple Inc.',
            'MSFT': 'Microsoft Corporation',
            'GOOGL': 'Alphabet Inc.',
            'TSLA': 'Tesla Inc.',
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'ADA': 'Cardano',
            'DOT': 'Polkadot'
        }
        
        return display_names.get(symbol, symbol)
    
    async def _initialize_symbol_data(self, symbol: str):
        """Initialisiert Market Data für neues Symbol"""
        
        # Mock initialization - in Produktion API-Call
        import random
        
        base_prices = {
            'BTC': 43000,
            'ETH': 2400,
            'ADA': 0.45,
            'DOT': 7.50,
            'AAPL': 180,
            'MSFT': 380,
            'GOOGL': 140,
            'TSLA': 250
        }
        
        base_price = base_prices.get(symbol, 100.0)
        price_variation = random.uniform(0.95, 1.05)
        price = base_price * price_variation
        
        self.market_data[symbol] = MarketDataPoint(
            symbol=symbol,
            price=round(price, 2),
            change=round(random.uniform(-5, 5), 2),
            change_percent=round(random.uniform(-2, 2), 2),
            volume=random.randint(1000000, 100000000),
            bid=round(price * 0.999, 2),
            ask=round(price * 1.001, 2),
            high_24h=round(price * 1.05, 2),
            low_24h=round(price * 0.95, 2),
            timestamp=datetime.now(),
            source=self.market_config['data_provider']
        )
    
    async def _check_price_alerts(self, market_data: Dict[str, MarketDataPoint]):
        """Prüft Price Alerts für Market Data"""
        
        if not self.market_config['enable_price_alerts']:
            return
        
        for symbol, data_point in market_data.items():
            if symbol not in self.watchlist_entries:
                continue
            
            watchlist_entry = self.watchlist_entries[symbol]
            
            if not watchlist_entry.alerts_enabled:
                continue
            
            # Threshold Alert
            if watchlist_entry.price_alert_threshold:
                if data_point.price >= watchlist_entry.price_alert_threshold:
                    await self._trigger_price_alert(symbol, 'threshold_reached', data_point)
            
            # Percentage Change Alert
            alert_threshold = self.market_config['alert_price_threshold_percent']
            if abs(data_point.change_percent) >= alert_threshold:
                alert_type = 'significant_increase' if data_point.change_percent > 0 else 'significant_decrease'
                await self._trigger_price_alert(symbol, alert_type, data_point)
    
    async def _trigger_price_alert(self, symbol: str, alert_type: str, data_point: MarketDataPoint):
        """Löst Price Alert aus"""
        
        self.alert_counter += 1
        
        alert_info = {
            'alert_id': self.alert_counter,
            'symbol': symbol,
            'alert_type': alert_type,
            'price': data_point.price,
            'change_percent': data_point.change_percent,
            'timestamp': datetime.now(),
            'message': f'{symbol} {alert_type}: {data_point.price} ({data_point.change_percent:+.2f}%)'
        }
        
        self.triggered_alerts.append(alert_info)
        
        # Limit alerts history
        if len(self.triggered_alerts) > 100:
            self.triggered_alerts.pop(0)
        
        self.logger.info(f"Price alert triggered",
                       symbol=symbol,
                       alert_type=alert_type,
                       price=data_point.price,
                       change_percent=data_point.change_percent,
                       alert_id=self.alert_counter)
    
    async def _get_current_market_status(self) -> Dict[str, Any]:
        """Ermittelt aktuellen Market Status"""
        
        current_time = datetime.now()
        current_hour = current_time.hour
        
        # Simplified market hours (would be more complex in production)
        if 15 <= current_hour < 22:  # 15:30 - 22:00 UTC+1 (US market hours)
            status = 'open'
            next_event = 'Market closes at 22:00'
        elif current_hour < 15:
            status = 'pre_market'
            next_event = 'Market opens at 15:30'
        else:
            status = 'after_hours'
            next_event = 'Market opens tomorrow at 15:30'
        
        # Crypto is always open
        crypto_status = 'open'
        
        return {
            'status': status,
            'crypto_status': crypto_status,
            'next_event': next_event,
            'timestamp': current_time
        }
    
    async def _publish_market_data_event(self, result: MarketDataResult,
                                       request: MarketDataRequest):
        """Published Market Data Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        # Nur für relevante Updates publishen
        if request.request_type in ['update_data', 'add_to_watchlist', 'remove_from_watchlist']:
            from event_bus import Event
            
            event = Event(
                event_type="market_data_updated",
                stream_id=f"market-data-{self.market_counter}",
                data={
                    'request_type': request.request_type,
                    'symbol': request.symbol,
                    'data_successful': result.data_successful,
                    'symbols_count': len(result.market_data),
                    'watchlist_size': len(result.watchlist_symbols),
                    'market_status': result.market_status,
                    'update_timestamp': result.data_timestamp.isoformat()
                },
                source="market_data_handler"
            )
            
            await self.event_bus.publish(event)
    
    async def _setup_event_subscriptions(self):
        """
        Setup Event-Bus subscriptions for market data updates
        Event-Bus Compliance: Subscribe to relevant events instead of direct calls
        """
        if not self.event_bus or not self.event_bus.connected:
            return
        
        try:
            # Subscribe to market data requests
            await self.event_bus.subscribe(
                EventType.MARKET_DATA_REQUEST.value,
                self._handle_market_data_request,
                f"market_data_request_{self.module_name}"
            )
            
            # Subscribe to system health requests
            await self.event_bus.subscribe(
                EventType.SYSTEM_HEALTH_REQUEST.value,
                self._handle_health_event,
                f"market_data_health_{self.module_name}"
            )
            
            self.logger.info("Market data event subscriptions established")
            
        except Exception as e:
            self.logger.error(f"Failed to setup event subscriptions: {e}")
    
    async def _handle_market_data_request(self, event: Event):
        """
        Handle market data request events
        Event-Bus Compliance: Process requests via events
        """
        try:
            request_data = event.data
            
            # Process market data request
            result = await self.execute_function(request_data)
            
            # Send response via event-bus
            response_event = Event(
                event_type=EventType.MARKET_DATA_RESPONSE.value,
                stream_id=event.stream_id,
                data=result,
                source=self.module_name,
                correlation_id=event.correlation_id
            )
            
            await self.event_bus.publish(response_event)
            self.logger.debug("Market data response sent via event")
            
        except Exception as e:
            self.logger.error(f"Failed to handle market data request: {e}")
    
    async def _handle_health_event(self, event: Event):
        """
        Handle system health request events
        Event-Bus Compliance: Respond to health checks via events
        """
        try:
            request_data = event.data
            
            if request_data.get('request_type') == 'market_data_health':
                # Respond with market data health status
                health_response = Event(
                    event_type=EventType.SYSTEM_HEALTH_RESPONSE.value,
                    stream_id=f"market-data-health-{event.stream_id}",
                    data={
                        'module': 'market_data_handler',
                        'status': 'healthy',
                        'symbols_tracked': len(self.market_data),
                        'watchlist_size': len(self.watchlist_entries),
                        'active_alerts': len(self.price_alerts),
                        'market_status': (await self._get_current_market_status())['status'],
                        'last_update': max([data.timestamp for data in self.market_data.values()], default=datetime.now()).isoformat()
                    },
                    source=self.module_name,
                    correlation_id=event.correlation_id
                )
                
                await self.event_bus.publish(health_response)
                self.logger.debug("Market data health response sent via event")
            
        except Exception as e:
            self.logger.error(f"Failed to handle health event: {e}")
    
    async def process_event(self, event: Event):
        """
        Process incoming events - Event-Bus Compliance
        """
        try:
            if event.event_type == EventType.MARKET_DATA_REQUEST.value:
                await self._handle_market_data_request(event)
            
            elif event.event_type == EventType.SYSTEM_HEALTH_REQUEST.value:
                await self._handle_health_event(event)
            
            else:
                self.logger.debug(f"Unhandled event type: {event.event_type}")
        
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_type}: {e}")
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Gibt Market Data Summary zurück"""
        
        # Watchlist Statistics
        total_symbols = len(self.market_data)
        watchlist_size = len(self.watchlist_entries)
        
        # Category Distribution
        category_distribution = {}
        for entry in self.watchlist_entries.values():
            category = entry.category
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        # Price Changes
        positive_changes = sum(1 for data in self.market_data.values() if data.change > 0)
        negative_changes = sum(1 for data in self.market_data.values() if data.change < 0)
        
        # Alerts
        recent_alerts = [
            alert for alert in self.triggered_alerts
            if (datetime.now() - alert['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_symbols': total_symbols,
            'watchlist_size': watchlist_size,
            'max_watchlist_size': self.market_config['max_watchlist_size'],
            'category_distribution': category_distribution,
            'positive_changes': positive_changes,
            'negative_changes': negative_changes,
            'neutral_changes': total_symbols - positive_changes - negative_changes,
            'recent_alerts_count': len(recent_alerts),
            'total_alerts_triggered': len(self.triggered_alerts),
            'data_provider': self.market_config['data_provider'],
            'auto_refresh_enabled': self.market_config['auto_refresh_enabled'],
            'refresh_interval_seconds': self.market_config['refresh_interval_seconds'],
            'alerts_enabled': self.market_config['enable_price_alerts']
        }
    
    def configure_alerts(self, symbol: str, alert_config: Dict[str, Any]):
        """Konfiguriert Alerts für Symbol"""
        
        symbol = symbol.upper()
        
        if symbol not in self.watchlist_entries:
            self.logger.warning(f"Symbol not in watchlist for alert configuration: {symbol}")
            return
        
        entry = self.watchlist_entries[symbol]
        
        if 'alerts_enabled' in alert_config:
            entry.alerts_enabled = alert_config['alerts_enabled']
        
        if 'price_alert_threshold' in alert_config:
            entry.price_alert_threshold = alert_config['price_alert_threshold']
        
        if 'priority' in alert_config:
            entry.priority = max(1, min(5, alert_config['priority']))
        
        self.logger.info(f"Alert configuration updated",
                       symbol=symbol,
                       alerts_enabled=entry.alerts_enabled,
                       threshold=entry.price_alert_threshold,
                       priority=entry.priority)
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Holt Recent Alerts"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self.triggered_alerts
            if alert['timestamp'] >= cutoff_time
        ]
        
        # Convert datetime objects to strings for JSON serialization
        for alert in recent_alerts:
            alert['timestamp'] = alert['timestamp'].isoformat()
        
        return sorted(recent_alerts, key=lambda x: x['timestamp'], reverse=True)
    
    def reset_market_data(self):
        """Reset Market Data to defaults (Administrative Function)"""
        
        # Clear alerts
        self.triggered_alerts.clear()
        self.alert_counter = 0
        
        # Reset timestamps
        current_time = datetime.now()
        for data_point in self.market_data.values():
            data_point.timestamp = current_time
        
        for entry in self.watchlist_entries.values():
            entry.last_viewed = current_time
        
        self.logger.warning("Market data reset to defaults")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'market_data_handler',
            'description': 'Complete market data management with watchlist and real-time price alerts',
            'responsibility': 'Market data management logic only',
            'input_parameters': {
                'request_type': 'Required request type (get_symbol, get_watchlist, update_data, add_to_watchlist, remove_from_watchlist)',
                'symbol': 'Optional symbol for single symbol operations',
                'symbols': 'Optional list of symbols for multi-symbol operations',
                'timeframe': 'Optional timeframe for historical data',
                'limit': 'Optional limit for results',
                'force_refresh': 'Whether to force refresh market data (default: false)',
                'include_historical': 'Whether to include historical data (default: false)',
                'alert_check': 'Whether to check for price alerts (default: true)'
            },
            'output_format': {
                'data_successful': 'Whether market data operation was successful',
                'market_data': 'Current market data for requested symbols',
                'watchlist_symbols': 'List of symbols in watchlist',
                'watchlist_details': 'Detailed watchlist information',
                'data_timestamp': 'Timestamp of market data',
                'data_source': 'Source of market data',
                'market_status': 'Current market status',
                'next_market_event': 'Next market event description',
                'data_warnings': 'List of data warnings if any'
            },
            'supported_request_types': ['get_symbol', 'get_watchlist', 'update_data', 'add_to_watchlist', 'remove_from_watchlist'],
            'supported_categories': list(self.market_categories.keys()),
            'supported_timeframes': self.market_config['supported_timeframes'],
            'market_configuration': self.market_config,
            'market_categories': self.market_categories,
            'watchlist_size_limit': self.market_config['max_watchlist_size'],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_market_data_statistics(self) -> Dict[str, Any]:
        """Market Data Handler Module Statistiken"""
        total_requests = len(self.market_history)
        
        if total_requests == 0:
            return {
                'total_requests': 0,
                'total_symbols': len(self.market_data),
                'watchlist_size': len(self.watchlist_entries)
            }
        
        # Success Rate
        successful_requests = sum(1 for h in self.market_history if h['data_successful'])
        success_rate = round((successful_requests / total_requests) * 100, 1) if total_requests > 0 else 0
        
        # Request Type Distribution
        request_type_distribution = {}
        for request in self.market_history:
            req_type = request['request_type']
            request_type_distribution[req_type] = request_type_distribution.get(req_type, 0) + 1
        
        # Symbol Popularity
        symbol_requests = {}
        for request in self.market_history:
            if request['symbol']:
                symbol = request['symbol']
                symbol_requests[symbol] = symbol_requests.get(symbol, 0) + 1
        
        # Alert Statistics
        alerts_by_type = {}
        for alert in self.triggered_alerts:
            alert_type = alert['alert_type']
            alerts_by_type[alert_type] = alerts_by_type.get(alert_type, 0) + 1
        
        # Recent Activity
        recent_requests = [
            h for h in self.market_history
            if (datetime.now() - h['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate_percent': success_rate,
            'recent_requests_last_hour': len(recent_requests),
            'request_type_distribution': dict(sorted(
                request_type_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'popular_symbols': dict(sorted(
                symbol_requests.items(), key=lambda x: x[1], reverse=True
            )[:10]),  # Top 10
            'total_symbols': len(self.market_data),
            'watchlist_size': len(self.watchlist_entries),
            'alerts_triggered_total': len(self.triggered_alerts),
            'alerts_by_type': alerts_by_type,
            'cache_hit_rate': 0.85,  # Mock cache hit rate
            'average_processing_time': self.average_execution_time
        }