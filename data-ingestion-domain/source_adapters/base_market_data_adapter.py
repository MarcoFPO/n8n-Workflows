"""
🌍 Base Market Data Adapter Interface
Modulare Basis-Klasse für alle Marktdaten-APIs gemäß Domain-Driven Design
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio
import aiohttp
from decimal import Decimal

class MarketDataSource(Enum):
    """Verfügbare Marktdaten-Quellen"""
    ALPHA_VANTAGE = "alpha_vantage"
    YAHOO_FINANCE = "yahoo_finance"
    FMP = "financial_modeling_prep"
    TWELVE_DATA = "twelve_data"
    IEX_CLOUD = "iex_cloud"

class DataType(Enum):
    """Verfügbare Datentypen"""
    REAL_TIME_QUOTE = "real_time_quote"
    HISTORICAL_DAILY = "historical_daily"
    HISTORICAL_INTRADAY = "historical_intraday"
    TECHNICAL_INDICATORS = "technical_indicators"
    FUNDAMENTAL_DATA = "fundamental_data"
    NEWS_SENTIMENT = "news_sentiment"
    GLOBAL_INDICES = "global_indices"

class Exchange(Enum):
    """Unterstützte Börsen weltweit"""
    # US Märkte
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"
    AMEX = "AMEX"
    
    # Deutsche Märkte
    XETRA = "XETRA"
    FRANKFURT = "FSE"
    
    # Internationale Märkte
    LSE = "LSE"          # London Stock Exchange
    TSE = "TSE"          # Tokyo Stock Exchange
    HKEX = "HKEX"        # Hong Kong Exchange
    TSX = "TSX"          # Toronto Stock Exchange
    ASX = "ASX"          # Australian Securities Exchange
    
    # Weitere europäische Märkte
    EURONEXT = "EPA"     # Euronext Paris
    SIX = "VTX"          # SIX Swiss Exchange

@dataclass
class MarketDataRequest:
    """Standard-Request-Format für alle Adapter"""
    symbol: str
    data_type: DataType
    exchange: Optional[Exchange] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    interval: Optional[str] = "1day"  # 1min, 5min, 15min, 30min, 1hour, 1day
    limit: Optional[int] = 100
    technical_indicator: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MarketDataPoint:
    """Standard-Datenformat für alle Quellen"""
    symbol: str
    timestamp: datetime
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    volume: Optional[int] = None
    adjusted_close: Optional[Decimal] = None
    
    # Technische Indikatoren (optional)
    technical_indicators: Dict[str, float] = field(default_factory=dict)
    
    # Fundamentaldaten (optional)
    market_cap: Optional[Decimal] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    
    # Metadaten
    exchange: Optional[Exchange] = None
    currency: Optional[str] = "USD"
    source: Optional[MarketDataSource] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

@dataclass 
class APILimits:
    """API-Limits für Rate-Limiting"""
    calls_per_minute: int
    calls_per_day: int
    calls_remaining_today: int
    reset_time: Optional[datetime] = None
    is_premium: bool = False

@dataclass
class AdapterStatus:
    """Status eines Marktdaten-Adapters"""
    source: MarketDataSource
    is_healthy: bool
    last_successful_call: Optional[datetime] = None
    error_count: int = 0
    api_limits: Optional[APILimits] = None
    supported_exchanges: List[Exchange] = field(default_factory=list)
    supported_data_types: List[DataType] = field(default_factory=list)

class BaseMarketDataAdapter(ABC):
    """
    🌍 Abstrakte Basis-Klasse für alle Marktdaten-Adapter
    
    Implementiert gemeinsame Funktionalität wie:
    - Rate Limiting
    - Error Handling
    - Caching
    - Logging
    - Health Checks
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "", 
                 name: str = "", source: MarketDataSource = None):
        self.api_key = api_key
        self.base_url = base_url
        self.name = name
        self.source = source
        self.logger = logging.getLogger(f"market_data.{name}")
        
        # Rate Limiting
        self._last_call_time = datetime.now()
        self._call_count_today = 0
        self._call_count_minute = 0
        
        # Error Tracking
        self._error_count = 0
        self._last_error = None
        
        # Session für HTTP Requests
        self.session = None
        
    async def __aenter__(self):
        """Async Context Manager Entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async Context Manager Exit"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def get_real_time_quote(self, symbol: str, exchange: Optional[Exchange] = None) -> MarketDataPoint:
        """Aktuelle Kursdaten abrufen"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, interval: str = "1day",
                                exchange: Optional[Exchange] = None) -> List[MarketDataPoint]:
        """Historische Kursdaten abrufen"""
        pass
    
    @abstractmethod 
    async def get_technical_indicators(self, symbol: str, indicator: str,
                                     period: int = 20, exchange: Optional[Exchange] = None) -> Dict[str, Any]:
        """Technische Indikatoren berechnen"""
        pass
    
    @abstractmethod
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Symbole suchen"""
        pass
    
    @abstractmethod
    def get_supported_exchanges(self) -> List[Exchange]:
        """Unterstützte Börsen zurückgeben"""
        pass
    
    @abstractmethod
    def get_supported_data_types(self) -> List[DataType]:
        """Unterstützte Datentypen zurückgeben"""
        pass
    
    async def health_check(self) -> AdapterStatus:
        """Gesundheitsstatus des Adapters prüfen"""
        try:
            # Test mit einem bekannten Symbol
            test_symbol = "AAPL"
            start_time = datetime.now()
            
            await self.get_real_time_quote(test_symbol)
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return AdapterStatus(
                source=self.source,
                is_healthy=True,
                last_successful_call=datetime.now(),
                error_count=self._error_count,
                api_limits=await self._get_api_limits(),
                supported_exchanges=self.get_supported_exchanges(),
                supported_data_types=self.get_supported_data_types()
            )
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self._error_count += 1
            
            return AdapterStatus(
                source=self.source,
                is_healthy=False,
                error_count=self._error_count,
                supported_exchanges=self.get_supported_exchanges(),
                supported_data_types=self.get_supported_data_types()
            )
    
    async def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """HTTP Request mit Rate Limiting und Error Handling"""
        await self._enforce_rate_limits()
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self._call_count_today += 1
                    self._call_count_minute += 1
                    self._last_call_time = datetime.now()
                    return data
                else:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
                    
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            self.logger.error(f"Request failed for {url}: {e}")
            raise
    
    async def _enforce_rate_limits(self):
        """Rate Limiting durchsetzen"""
        limits = await self._get_api_limits()
        if not limits:
            return
            
        # Minute Rate Limit prüfen
        if self._call_count_minute >= limits.calls_per_minute:
            sleep_time = 60 - (datetime.now() - self._last_call_time).seconds
            if sleep_time > 0:
                self.logger.info(f"Rate limit reached, sleeping for {sleep_time}s")
                await asyncio.sleep(sleep_time)
                self._call_count_minute = 0
        
        # Daily Rate Limit prüfen  
        if self._call_count_today >= limits.calls_per_day:
            raise Exception(f"Daily API limit of {limits.calls_per_day} reached")
    
    @abstractmethod
    async def _get_api_limits(self) -> Optional[APILimits]:
        """API-Limits für diesen Adapter zurückgeben"""
        pass
    
    def _normalize_symbol(self, symbol: str, exchange: Optional[Exchange] = None) -> str:
        """Symbol für spezifische API normalisieren"""
        # Basis-Implementierung - kann in Subklassen überschrieben werden
        if exchange and exchange != Exchange.NASDAQ and exchange != Exchange.NYSE:
            # Füge Börsen-Suffix hinzu für internationale Märkte
            exchange_suffixes = {
                Exchange.XETRA: ".DE",
                Exchange.FRANKFURT: ".F", 
                Exchange.LSE: ".L",
                Exchange.TSE: ".T",
                Exchange.HKEX: ".HK",
                Exchange.TSX: ".TO",
                Exchange.ASX: ".AX"
            }
            suffix = exchange_suffixes.get(exchange, "")
            return f"{symbol}{suffix}"
        
        return symbol.upper()
    
    def _parse_datetime(self, date_str: str) -> datetime:
        """Datum-String in DateTime konvertieren"""
        # Häufige Formate unterstützen
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S", 
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y%m%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        raise ValueError(f"Could not parse date: {date_str}")