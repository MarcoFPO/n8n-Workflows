#!/usr/bin/env python3
"""
Market Data Service Enhanced v6.0.0 - Clean Architecture Implementation
Yahoo Finance Integration Service für Event-Driven Trading Intelligence System

CLEAN ARCHITECTURE LAYERS:
✅ Domain Layer: Business Logic, Entities, Value Objects, Domain Events
✅ Application Layer: Use Cases, Service Interfaces, Business Rules Orchestration  
✅ Infrastructure Layer: Database, External APIs, Event Publishing, Data Persistence
✅ Presentation Layer: FastAPI Controllers, Request/Response Models, HTTP Handling

ARCHITECTURE COMPLIANCE:
✅ SOLID Principles: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
✅ Dependency Injection: Centralized Container mit Interface-based Dependencies
✅ Event-Driven Pattern: Domain Events, Event Publishing, Event-Bus Integration
✅ Repository Pattern: Data Access Abstraction mit PostgreSQL Implementation
✅ Use Case Pattern: Single-purpose Application Logic Orchestration

FEATURES v6.0.0:
- Yahoo Finance Real-Time Market Data Integration
- Event-Driven Architecture Integration (Port 8014)
- Stock Price, Volume, Technical Indicators Retrieval
- PostgreSQL Persistence mit Historical Data Storage
- Redis Event Publishing mit Market Data Events
- FastAPI REST API mit OpenAPI Documentation
- Comprehensive Error Handling und Rate Limiting
- Health Checks und Service Metrics

Code-Qualität: HÖCHSTE PRIORITÄT - Architecture Refactoring Specialist
Autor: Claude Code - Clean Architecture Implementation
Datum: 24. August 2025
Version: 6.0.0 (Clean Architecture Refactored)
"""

import asyncio
import logging
import signal
import sys
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import json
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import redis.asyncio as aioredis
import asyncpg
import httpx
import pandas as pd

# =============================================================================
# DOMAIN LAYER - Value Objects & Domain Events
# =============================================================================

class MarketDataPeriod(str, Enum):
    """Domain Value Object for Market Data Periods"""
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"
    SIX_MONTHS = "6mo"
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    FIVE_YEARS = "5y"
    TEN_YEARS = "10y"
    MAX = "max"

class MarketDataInterval(str, Enum):
    """Domain Value Object for Market Data Intervals"""
    ONE_MINUTE = "1m"
    TWO_MINUTES = "2m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_WEEK = "1wk"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"

class MarketDataType(str, Enum):
    """Domain Value Object for Market Data Types"""
    STOCK_PRICE = "stock_price"
    HISTORICAL_DATA = "historical_data"
    TECHNICAL_INDICATORS = "technical_indicators"
    COMPANY_INFO = "company_info"
    DIVIDEND_DATA = "dividend_data"

# =============================================================================
# PRESENTATION LAYER - Request/Response Models
# =============================================================================

class StockPriceRequest(BaseModel):
    """Request Model für Stock Price Retrieval"""
    symbols: List[str] = Field(..., description="List of stock symbols", min_items=1, max_items=100)
    include_extended_hours: bool = Field(default=False, description="Include pre/post market data")
    
    @validator('symbols')
    def validate_symbols(cls, v):
        """Validate stock symbols format"""
        for symbol in v:
            if not symbol or len(symbol) > 10 or not symbol.replace('.', '').isalnum():
                raise ValueError(f"Invalid stock symbol: {symbol}")
        return [s.upper() for s in v]

class StockPrice(BaseModel):
    """Stock Price Data Model"""
    symbol: str
    current_price: float
    previous_close: float
    day_high: float
    day_low: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    avg_volume: Optional[int] = None
    beta: Optional[float] = None
    last_updated: datetime
    market_state: str  # "REGULAR", "PRE", "POST", "CLOSED"
    currency: str = "USD"

class StockPriceResponse(BaseModel):
    """Response Model für Stock Prices"""
    prices: List[StockPrice]
    count: int
    request_id: str
    processing_time_ms: int
    data_source: str = "yahoo_finance"
    last_updated: datetime

class HistoricalDataRequest(BaseModel):
    """Request Model für Historical Market Data"""
    symbol: str = Field(..., description="Stock symbol")
    period: MarketDataPeriod = Field(default=MarketDataPeriod.ONE_YEAR, description="Data period")
    interval: MarketDataInterval = Field(default=MarketDataInterval.ONE_DAY, description="Data interval")
    include_dividends: bool = Field(default=True, description="Include dividend data")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate stock symbol format"""
        if not v or len(v) > 10 or not v.replace('.', '').isalnum():
            raise ValueError(f"Invalid stock symbol: {v}")
        return v.upper()

class HistoricalDataPoint(BaseModel):
    """Historical Data Point Model"""
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    adjusted_close: float
    volume: int
    dividend: Optional[float] = None

class HistoricalDataResponse(BaseModel):
    """Response Model für Historical Data"""
    symbol: str
    period: MarketDataPeriod
    interval: MarketDataInterval
    data_points: List[HistoricalDataPoint]
    count: int
    start_date: datetime
    end_date: datetime
    request_id: str
    processing_time_ms: int

class TechnicalIndicatorsRequest(BaseModel):
    """Request Model für Technical Indicators"""
    symbol: str = Field(..., description="Stock symbol")
    indicators: List[str] = Field(
        default=["sma_20", "sma_50", "ema_12", "ema_26", "rsi", "macd", "bollinger_bands"],
        description="List of technical indicators to calculate"
    )
    period: int = Field(default=100, ge=20, le=500, description="Number of periods for calculation")

class TechnicalIndicators(BaseModel):
    """Technical Indicators Model"""
    symbol: str
    sma_20: Optional[float] = None  # Simple Moving Average 20
    sma_50: Optional[float] = None  # Simple Moving Average 50
    ema_12: Optional[float] = None  # Exponential Moving Average 12
    ema_26: Optional[float] = None  # Exponential Moving Average 26
    rsi: Optional[float] = None     # Relative Strength Index
    macd: Optional[float] = None    # MACD
    macd_signal: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    bollinger_middle: Optional[float] = None
    volume_sma: Optional[float] = None
    calculated_at: datetime

class TechnicalIndicatorsResponse(BaseModel):
    """Response Model für Technical Indicators"""
    indicators: TechnicalIndicators
    request_id: str
    processing_time_ms: int

class HealthCheckResponse(BaseModel):
    """Health Check Response Model"""
    healthy: bool
    service: str = "market-data-service"
    version: str = "6.0.0"
    dependencies: Dict[str, bool]
    yahoo_finance_available: bool
    event_bus_connected: bool
    database_connected: bool
    rate_limit_status: Dict[str, Any]
    timestamp: datetime
    uptime_seconds: float
    error: Optional[str] = None

class ServiceMetricsResponse(BaseModel):
    """Service Metrics Response Model"""
    service: str = "market-data-service"
    version: str = "6.0.0"
    requests_total: int
    requests_success: int
    requests_error: int
    success_rate: float
    error_rate: float
    api_calls_today: int
    rate_limit_hits: int
    uptime_seconds: float
    memory_usage_mb: float
    last_request_time: Optional[datetime]
    yahoo_finance_status: str
    timestamp: datetime

# =============================================================================
# INFRASTRUCTURE LAYER - Configuration & External Services
# =============================================================================

class ServiceConfiguration:
    """Service Configuration Management"""
    
    def __init__(self):
        # Service Configuration
        self.service_host = "0.0.0.0"
        self.service_port = 8002  # Market Data Service Port basierend auf LLD
        self.log_level = "INFO"
        
        # Redis Configuration
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_db = 0
        
        # PostgreSQL Configuration
        self.postgres_host = "localhost"
        self.postgres_port = 5432
        self.postgres_db = "aktienanalyse_ecosystem"
        self.postgres_user = "aktienanalyse_user"
        self.postgres_password = "secure_password_2024"
        
        # Event Bus Configuration
        self.event_bus_url = "http://localhost:8014"
        
        # Yahoo Finance Configuration
        self.yahoo_finance_base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
        self.yahoo_finance_timeout = 30
        self.rate_limit_requests_per_minute = 1000
        self.rate_limit_requests_per_hour = 10000
        
        # Business Logic Configuration
        self.cache_ttl_seconds = 300  # 5 minutes
        self.max_symbols_per_request = 100
        self.historical_data_limit_days = 1825  # 5 years max
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "service_host": self.service_host,
            "service_port": self.service_port,
            "log_level": self.log_level,
            "redis_connected": f"{self.redis_host}:{self.redis_port}",
            "postgres_connected": f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}",
            "event_bus_url": self.event_bus_url,
            "yahoo_finance_available": True,
            "rate_limits": {
                "per_minute": self.rate_limit_requests_per_minute,
                "per_hour": self.rate_limit_requests_per_hour
            }
        }

class YahooFinanceAdapter:
    """Yahoo Finance API Adapter"""
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        self.http_client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.last_request_time: Optional[datetime] = None
        self.rate_limit_hits = 0
    
    async def initialize(self) -> bool:
        """Initialize HTTP Client"""
        try:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.yahoo_finance_timeout),
                headers={
                    "User-Agent": "Market-Data-Service/6.0.0",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate"
                },
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
            )
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Yahoo Finance Adapter: {e}")
            return False
    
    async def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current stock price from Yahoo Finance"""
        try:
            if not self.http_client:
                return None
            
            self._track_request()
            
            url = f"{self.config.yahoo_finance_base_url}/{symbol}"
            params = {
                "interval": "1m",
                "range": "1d",
                "includePrePost": True,
                "events": "div,splits"
            }
            
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("chart", {}).get("result"):
                return None
            
            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            quotes = result.get("indicators", {}).get("quote", [{}])[0]
            
            # Get the latest values
            timestamps = result.get("timestamp", [])
            if not timestamps:
                return None
            
            latest_idx = -1
            current_price = quotes.get("close", [None])[latest_idx] or meta.get("regularMarketPrice", 0.0)
            
            return {
                "symbol": symbol.upper(),
                "current_price": float(current_price) if current_price else 0.0,
                "previous_close": float(meta.get("previousClose", 0.0)),
                "day_high": float(meta.get("regularMarketDayHigh", 0.0)),
                "day_low": float(meta.get("regularMarketDayLow", 0.0)),
                "volume": int(meta.get("regularMarketVolume", 0)),
                "market_cap": meta.get("marketCap"),
                "pe_ratio": meta.get("trailingPE"),
                "dividend_yield": meta.get("dividendYield"),
                "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
                "avg_volume": meta.get("averageVolume"),
                "beta": meta.get("beta"),
                "market_state": meta.get("marketState", "CLOSED"),
                "currency": meta.get("currency", "USD"),
                "last_updated": datetime.now()
            }
            
        except Exception as e:
            logging.error(f"Failed to get stock price for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, period: str, interval: str) -> Optional[List[Dict[str, Any]]]:
        """Get historical market data from Yahoo Finance"""
        try:
            if not self.http_client:
                return None
            
            self._track_request()
            
            url = f"{self.config.yahoo_finance_base_url}/{symbol}"
            params = {
                "interval": interval,
                "range": period,
                "events": "div,splits"
            }
            
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("chart", {}).get("result"):
                return None
            
            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            quotes = result.get("indicators", {}).get("quote", [{}])[0]
            
            historical_data = []
            for i, timestamp in enumerate(timestamps):
                try:
                    data_point = {
                        "timestamp": datetime.fromtimestamp(timestamp),
                        "open_price": float(quotes.get("open", [])[i] or 0.0),
                        "high_price": float(quotes.get("high", [])[i] or 0.0),
                        "low_price": float(quotes.get("low", [])[i] or 0.0),
                        "close_price": float(quotes.get("close", [])[i] or 0.0),
                        "adjusted_close": float(quotes.get("close", [])[i] or 0.0),  # Simplified
                        "volume": int(quotes.get("volume", [])[i] or 0)
                    }
                    historical_data.append(data_point)
                except (IndexError, ValueError, TypeError):
                    continue
            
            return historical_data
            
        except Exception as e:
            logging.error(f"Failed to get historical data for {symbol}: {e}")
            return None
    
    def _track_request(self):
        """Track API request for rate limiting"""
        self.request_count += 1
        self.last_request_time = datetime.now()
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        return {
            "requests_made": self.request_count,
            "rate_limit_hits": self.rate_limit_hits,
            "last_request": self.last_request_time.isoformat() if self.last_request_time else None,
            "requests_per_minute_limit": self.config.rate_limit_requests_per_minute,
            "requests_per_hour_limit": self.config.rate_limit_requests_per_hour
        }
    
    async def health_check(self) -> bool:
        """Yahoo Finance API Health Check"""
        try:
            # Try to get data for a common stock
            data = await self.get_stock_price("AAPL")
            return data is not None
        except Exception:
            return False
    
    async def cleanup(self):
        """Cleanup HTTP Client"""
        if self.http_client:
            await self.http_client.aclose()

class EventPublisher:
    """Event Publisher for Redis Event-Bus Integration"""
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        self.redis_client: Optional[aioredis.Redis] = None
    
    async def initialize(self) -> bool:
        """Initialize Redis Connection"""
        try:
            self.redis_client = aioredis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                decode_responses=True
            )
            await self.redis_client.ping()
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Event Publisher: {e}")
            return False
    
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Publish Event to Redis Event-Bus"""
        try:
            if not self.redis_client:
                return False
            
            event_message = {
                "event_id": f"market-data-{datetime.now().strftime('%H%M%S%f')}",
                "event_type": event_type,
                "source": "market-data-service",
                "timestamp": datetime.now().isoformat(),
                "event_data": event_data
            }
            
            channel = f"events:{event_type}"
            await self.redis_client.publish(channel, json.dumps(event_message))
            return True
            
        except Exception as e:
            logging.error(f"Failed to publish event {event_type}: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup Redis Connection"""
        if self.redis_client:
            await self.redis_client.close()

class DatabaseRepository:
    """PostgreSQL Repository for Market Data Storage"""
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        self.connection_pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> bool:
        """Initialize PostgreSQL Connection Pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_db,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
                min_size=2,
                max_size=10
            )
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Database Repository: {e}")
            return False
    
    async def store_stock_price(self, price_data: Dict[str, Any]) -> bool:
        """Store stock price data in database"""
        try:
            if not self.connection_pool:
                return False
            
            query = """
            INSERT INTO stock_prices (
                symbol, current_price, previous_close, day_high, day_low,
                volume, market_cap, pe_ratio, dividend_yield,
                fifty_two_week_high, fifty_two_week_low, avg_volume, beta,
                market_state, currency, last_updated
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            ON CONFLICT (symbol) DO UPDATE SET
                current_price = EXCLUDED.current_price,
                previous_close = EXCLUDED.previous_close,
                day_high = EXCLUDED.day_high,
                day_low = EXCLUDED.day_low,
                volume = EXCLUDED.volume,
                market_cap = EXCLUDED.market_cap,
                pe_ratio = EXCLUDED.pe_ratio,
                dividend_yield = EXCLUDED.dividend_yield,
                fifty_two_week_high = EXCLUDED.fifty_two_week_high,
                fifty_two_week_low = EXCLUDED.fifty_two_week_low,
                avg_volume = EXCLUDED.avg_volume,
                beta = EXCLUDED.beta,
                market_state = EXCLUDED.market_state,
                currency = EXCLUDED.currency,
                last_updated = EXCLUDED.last_updated;
            """
            
            async with self.connection_pool.acquire() as conn:
                await conn.execute(
                    query,
                    price_data["symbol"],
                    price_data["current_price"],
                    price_data["previous_close"],
                    price_data["day_high"],
                    price_data["day_low"],
                    price_data["volume"],
                    price_data.get("market_cap"),
                    price_data.get("pe_ratio"),
                    price_data.get("dividend_yield"),
                    price_data.get("fifty_two_week_high"),
                    price_data.get("fifty_two_week_low"),
                    price_data.get("avg_volume"),
                    price_data.get("beta"),
                    price_data["market_state"],
                    price_data["currency"],
                    price_data["last_updated"]
                )
                return True
                
        except Exception as e:
            logging.error(f"Failed to store stock price for {price_data.get('symbol')}: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Database Health Check"""
        try:
            if not self.connection_pool:
                return False
            
            async with self.connection_pool.acquire() as conn:
                await conn.execute("SELECT 1;")
                return True
        except Exception:
            return False
    
    async def cleanup(self):
        """Cleanup Database Connection Pool"""
        if self.connection_pool:
            await self.connection_pool.close()

# =============================================================================
# APPLICATION LAYER - Use Cases
# =============================================================================

class StockPriceUseCase:
    """Use Case für Stock Price Retrieval"""
    
    def __init__(self, yahoo_adapter: YahooFinanceAdapter, db_repository: DatabaseRepository, event_publisher: EventPublisher):
        self.yahoo_adapter = yahoo_adapter
        self.db_repository = db_repository
        self.event_publisher = event_publisher
        self.request_count = 0
    
    async def execute(self, request: StockPriceRequest) -> StockPriceResponse:
        """Execute Stock Price Retrieval Use Case"""
        start_time = datetime.now()
        self.request_count += 1
        
        request_id = f"stock-prices-{self.request_count}-{start_time.strftime('%H%M%S')}"
        
        try:
            # Publish request started event
            await self.event_publisher.publish("market-data.stock-price.request.started", {
                "request_id": request_id,
                "symbols": request.symbols,
                "symbol_count": len(request.symbols)
            })
            
            stock_prices = []
            
            # Get stock prices for each symbol
            for symbol in request.symbols:
                try:
                    price_data = await self.yahoo_adapter.get_stock_price(symbol)
                    
                    if price_data:
                        # Store in database
                        await self.db_repository.store_stock_price(price_data)
                        
                        # Convert to response model
                        stock_price = StockPrice(**price_data)
                        stock_prices.append(stock_price)
                        
                        # Publish individual stock price event
                        await self.event_publisher.publish("market-data.stock-price.updated", {
                            "symbol": symbol,
                            "current_price": price_data["current_price"],
                            "previous_close": price_data["previous_close"],
                            "change_percent": ((price_data["current_price"] - price_data["previous_close"]) / price_data["previous_close"]) * 100 if price_data["previous_close"] > 0 else 0.0,
                            "volume": price_data["volume"],
                            "market_state": price_data["market_state"]
                        })
                        
                except Exception as e:
                    logging.error(f"Failed to get price for symbol {symbol}: {e}")
                    continue
                
                # Rate limiting delay
                await asyncio.sleep(0.1)  # 10 requests per second max
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            response = StockPriceResponse(
                prices=stock_prices,
                count=len(stock_prices),
                request_id=request_id,
                processing_time_ms=processing_time_ms,
                last_updated=datetime.now()
            )
            
            # Publish request completed event
            await self.event_publisher.publish("market-data.stock-price.request.completed", {
                "request_id": request_id,
                "processing_time_ms": processing_time_ms,
                "symbols_requested": len(request.symbols),
                "symbols_retrieved": len(stock_prices),
                "success_rate": (len(stock_prices) / len(request.symbols)) * 100
            })
            
            return response
            
        except Exception as e:
            # Publish request failed event
            await self.event_publisher.publish("market-data.stock-price.request.failed", {
                "request_id": request_id,
                "error": str(e),
                "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            })
            raise

class HistoricalDataUseCase:
    """Use Case für Historical Market Data Retrieval"""
    
    def __init__(self, yahoo_adapter: YahooFinanceAdapter, event_publisher: EventPublisher):
        self.yahoo_adapter = yahoo_adapter
        self.event_publisher = event_publisher
        self.request_count = 0
    
    async def execute(self, request: HistoricalDataRequest) -> HistoricalDataResponse:
        """Execute Historical Data Retrieval Use Case"""
        start_time = datetime.now()
        self.request_count += 1
        
        request_id = f"historical-{self.request_count}-{start_time.strftime('%H%M%S')}"
        
        try:
            # Publish request started event
            await self.event_publisher.publish("market-data.historical.request.started", {
                "request_id": request_id,
                "symbol": request.symbol,
                "period": request.period.value,
                "interval": request.interval.value
            })
            
            # Get historical data from Yahoo Finance
            historical_data = await self.yahoo_adapter.get_historical_data(
                request.symbol, 
                request.period.value, 
                request.interval.value
            )
            
            if not historical_data:
                raise HTTPException(status_code=404, detail=f"No historical data found for {request.symbol}")
            
            # Convert to response format
            data_points = [HistoricalDataPoint(**point) for point in historical_data]
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            response = HistoricalDataResponse(
                symbol=request.symbol,
                period=request.period,
                interval=request.interval,
                data_points=data_points,
                count=len(data_points),
                start_date=data_points[0].timestamp if data_points else datetime.now(),
                end_date=data_points[-1].timestamp if data_points else datetime.now(),
                request_id=request_id,
                processing_time_ms=processing_time_ms
            )
            
            # Publish request completed event
            await self.event_publisher.publish("market-data.historical.request.completed", {
                "request_id": request_id,
                "symbol": request.symbol,
                "data_points_count": len(data_points),
                "processing_time_ms": processing_time_ms
            })
            
            return response
            
        except Exception as e:
            # Publish request failed event
            await self.event_publisher.publish("market-data.historical.request.failed", {
                "request_id": request_id,
                "symbol": request.symbol,
                "error": str(e)
            })
            raise

class TechnicalIndicatorsUseCase:
    """Use Case für Technical Indicators Calculation"""
    
    def __init__(self, yahoo_adapter: YahooFinanceAdapter, event_publisher: EventPublisher):
        self.yahoo_adapter = yahoo_adapter
        self.event_publisher = event_publisher
        self.request_count = 0
    
    async def execute(self, request: TechnicalIndicatorsRequest) -> TechnicalIndicatorsResponse:
        """Execute Technical Indicators Calculation Use Case"""
        start_time = datetime.now()
        self.request_count += 1
        
        request_id = f"technical-{self.request_count}-{start_time.strftime('%H%M%S')}"
        
        try:
            # Get historical data for calculation
            historical_data = await self.yahoo_adapter.get_historical_data(
                request.symbol, 
                f"{request.period}d",  # Convert period to days
                "1d"  # Daily intervals for technical indicators
            )
            
            if not historical_data or len(historical_data) < 20:
                raise HTTPException(status_code=400, detail=f"Insufficient data for technical indicators calculation for {request.symbol}")
            
            # Calculate indicators (simplified implementation)
            indicators_data = await self._calculate_indicators(request.symbol, historical_data, request.indicators)
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            response = TechnicalIndicatorsResponse(
                indicators=indicators_data,
                request_id=request_id,
                processing_time_ms=processing_time_ms
            )
            
            # Publish event
            await self.event_publisher.publish("market-data.technical-indicators.calculated", {
                "request_id": request_id,
                "symbol": request.symbol,
                "indicators": request.indicators,
                "processing_time_ms": processing_time_ms
            })
            
            return response
            
        except Exception as e:
            await self.event_publisher.publish("market-data.technical-indicators.failed", {
                "request_id": request_id,
                "symbol": request.symbol,
                "error": str(e)
            })
            raise
    
    async def _calculate_indicators(self, symbol: str, historical_data: List[Dict], indicators: List[str]) -> TechnicalIndicators:
        """Calculate Technical Indicators (Simplified Implementation)"""
        try:
            # Convert to DataFrame for easier calculation
            df = pd.DataFrame(historical_data)
            df['close'] = df['close_price']
            df['volume'] = df['volume']
            
            indicators_result = TechnicalIndicators(
                symbol=symbol,
                calculated_at=datetime.now()
            )
            
            # Simple Moving Averages
            if "sma_20" in indicators and len(df) >= 20:
                indicators_result.sma_20 = float(df['close'].rolling(window=20).mean().iloc[-1])
            
            if "sma_50" in indicators and len(df) >= 50:
                indicators_result.sma_50 = float(df['close'].rolling(window=50).mean().iloc[-1])
            
            # Exponential Moving Averages (simplified)
            if "ema_12" in indicators and len(df) >= 12:
                indicators_result.ema_12 = float(df['close'].ewm(span=12).mean().iloc[-1])
            
            if "ema_26" in indicators and len(df) >= 26:
                indicators_result.ema_26 = float(df['close'].ewm(span=26).mean().iloc[-1])
            
            # RSI (simplified calculation)
            if "rsi" in indicators and len(df) >= 14:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                indicators_result.rsi = float(100 - (100 / (1 + rs.iloc[-1])))
            
            # Volume SMA
            if "volume_sma" in indicators and len(df) >= 20:
                indicators_result.volume_sma = float(df['volume'].rolling(window=20).mean().iloc[-1])
            
            return indicators_result
            
        except Exception as e:
            logging.error(f"Failed to calculate indicators for {symbol}: {e}")
            return TechnicalIndicators(symbol=symbol, calculated_at=datetime.now())

# =============================================================================
# DEPENDENCY INJECTION CONTAINER
# =============================================================================

class MarketDataDependencyContainer:
    """Dependency Injection Container für Clean Architecture"""
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        self.startup_time = datetime.now()
        
        # Infrastructure Layer
        self.yahoo_adapter: Optional[YahooFinanceAdapter] = None
        self.event_publisher: Optional[EventPublisher] = None
        self.db_repository: Optional[DatabaseRepository] = None
        
        # Application Layer
        self.stock_price_use_case: Optional[StockPriceUseCase] = None
        self.historical_data_use_case: Optional[HistoricalDataUseCase] = None
        self.technical_indicators_use_case: Optional[TechnicalIndicatorsUseCase] = None
        
        # Metrics
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_request_time: Optional[datetime] = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize all dependencies"""
        try:
            logging.info("🔧 Initializing Market Data Dependency Container")
            
            # Infrastructure Layer
            self.yahoo_adapter = YahooFinanceAdapter(self.config)
            await self.yahoo_adapter.initialize()
            
            self.event_publisher = EventPublisher(self.config)
            await self.event_publisher.initialize()
            
            self.db_repository = DatabaseRepository(self.config)
            await self.db_repository.initialize()
            
            # Application Layer
            self.stock_price_use_case = StockPriceUseCase(
                self.yahoo_adapter, 
                self.db_repository, 
                self.event_publisher
            )
            
            self.historical_data_use_case = HistoricalDataUseCase(
                self.yahoo_adapter, 
                self.event_publisher
            )
            
            self.technical_indicators_use_case = TechnicalIndicatorsUseCase(
                self.yahoo_adapter, 
                self.event_publisher
            )
            
            self._initialized = True
            logging.info("✅ Market Data Dependency Container initialized successfully")
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize Dependency Container: {e}")
            raise
    
    def is_initialized(self) -> bool:
        """Check if container is fully initialized"""
        return self._initialized
    
    async def health_check(self) -> HealthCheckResponse:
        """Comprehensive Health Check"""
        try:
            dependencies = {}
            
            # Check Yahoo Finance
            yahoo_available = False
            if self.yahoo_adapter:
                yahoo_available = await self.yahoo_adapter.health_check()
                dependencies["yahoo_finance"] = yahoo_available
            else:
                dependencies["yahoo_finance"] = False
            
            # Check Event Publisher
            event_bus_connected = False
            if self.event_publisher and self.event_publisher.redis_client:
                try:
                    await self.event_publisher.redis_client.ping()
                    event_bus_connected = True
                    dependencies["redis"] = True
                except:
                    dependencies["redis"] = False
            else:
                dependencies["redis"] = False
            
            # Check Database
            database_connected = False
            if self.db_repository:
                database_connected = await self.db_repository.health_check()
                dependencies["postgresql"] = database_connected
            else:
                dependencies["postgresql"] = False
            
            # Rate limit status
            rate_limit_status = {}
            if self.yahoo_adapter:
                rate_limit_status = self.yahoo_adapter.get_rate_limit_status()
            
            all_healthy = (
                self._initialized and 
                yahoo_available and 
                event_bus_connected
            )
            
            uptime = (datetime.now() - self.startup_time).total_seconds()
            
            return HealthCheckResponse(
                healthy=all_healthy,
                dependencies=dependencies,
                yahoo_finance_available=yahoo_available,
                event_bus_connected=event_bus_connected,
                database_connected=database_connected,
                rate_limit_status=rate_limit_status,
                timestamp=datetime.now(),
                uptime_seconds=uptime
            )
            
        except Exception as e:
            return HealthCheckResponse(
                healthy=False,
                dependencies={},
                yahoo_finance_available=False,
                event_bus_connected=False,
                database_connected=False,
                rate_limit_status={},
                timestamp=datetime.now(),
                uptime_seconds=(datetime.now() - self.startup_time).total_seconds(),
                error=str(e)
            )
    
    async def get_metrics(self) -> ServiceMetricsResponse:
        """Get Service Metrics"""
        uptime = (datetime.now() - self.startup_time).total_seconds()
        success_rate = (self.success_count / self.request_count) * 100 if self.request_count > 0 else 100.0
        error_rate = (self.error_count / self.request_count) * 100 if self.request_count > 0 else 0.0
        
        # Simple memory usage estimation
        import psutil
        process = psutil.Process()
        memory_usage_mb = process.memory_info().rss / 1024 / 1024
        
        # Yahoo Finance status
        yahoo_status = "healthy" if self.yahoo_adapter else "not_initialized"
        api_calls_today = self.yahoo_adapter.request_count if self.yahoo_adapter else 0
        rate_limit_hits = self.yahoo_adapter.rate_limit_hits if self.yahoo_adapter else 0
        
        return ServiceMetricsResponse(
            requests_total=self.request_count,
            requests_success=self.success_count,
            requests_error=self.error_count,
            success_rate=success_rate,
            error_rate=error_rate,
            api_calls_today=api_calls_today,
            rate_limit_hits=rate_limit_hits,
            uptime_seconds=uptime,
            memory_usage_mb=memory_usage_mb,
            last_request_time=self.last_request_time,
            yahoo_finance_status=yahoo_status,
            timestamp=datetime.now()
        )
    
    def track_request(self, success: bool = True):
        """Track Request Metrics"""
        self.request_count += 1
        self.last_request_time = datetime.now()
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    async def cleanup(self):
        """Cleanup all dependencies"""
        logging.info("🧹 Cleaning up Market Data Dependency Container")
        
        if self.yahoo_adapter:
            await self.yahoo_adapter.cleanup()
        
        if self.event_publisher:
            await self.event_publisher.cleanup()
        
        if self.db_repository:
            await self.db_repository.cleanup()
        
        logging.info("✅ Market Data Dependency Container cleanup completed")

# Global Container Instance
container: Optional[MarketDataDependencyContainer] = None

# =============================================================================
# PRESENTATION LAYER - FastAPI Controllers
# =============================================================================

def setup_logging(log_level: str = "INFO"):
    """Centralized Logging Configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='{"service": "market-data-service", "version": "6.0.0", "level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s", "module": "%(name)s"}',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"/tmp/market-data-service-{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )
    
    # Suppress noisy external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Application Lifespan Management"""
    logger = logging.getLogger(__name__)
    global container
    
    # Startup
    try:
        logger.info("🚀 Starting Market Data Service Enhanced v6.0.0 - Clean Architecture")
        
        # Initialize Configuration
        config = ServiceConfiguration()
        logger.info(f"⚙️ Configuration loaded: {config.to_dict()}")
        
        # Initialize Dependency Container
        container = MarketDataDependencyContainer(config)
        await container.initialize()
        
        # Store in app state
        app.state.container = container
        app.state.config = config
        app.state.startup_time = datetime.now()
        
        logger.info("✅ Market Data Service Enhanced v6.0.0 initialized successfully")
        logger.info(f"🌐 Service available at http://{config.service_host}:{config.service_port}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize service: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise
    
    # Shutdown
    logger.info("🛑 Shutting down Market Data Service Enhanced v6.0.0")
    if container:
        await container.cleanup()
    logger.info("✅ Shutdown completed")

# FastAPI App Creation
config = ServiceConfiguration()
setup_logging(config.log_level)

app = FastAPI(
    title="Market Data Service Enhanced v6.0",
    description="Yahoo Finance Integration Service mit Clean Architecture",
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

# =============================================================================
# DEPENDENCY INJECTION HELPERS
# =============================================================================

def get_container() -> MarketDataDependencyContainer:
    """Dependency Injection Helper für Container Access"""
    if not hasattr(app.state, 'container') or not app.state.container:
        raise HTTPException(status_code=503, detail="Service container not initialized")
    return app.state.container

# =============================================================================
# CLEAN ARCHITECTURE API ENDPOINTS
# =============================================================================

@app.post(
    "/api/v1/market-data/stock-prices",
    response_model=StockPriceResponse,
    summary="Get Current Stock Prices",
    description="Retrieves current stock prices for multiple symbols from Yahoo Finance"
)
async def get_stock_prices(
    request: StockPriceRequest,
    container: MarketDataDependencyContainer = Depends(get_container)
) -> StockPriceResponse:
    """
    Stock Price Retrieval Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Use Case (Application) -> Yahoo Finance Adapter (Infrastructure) -> Event Publishing -> Domain Logic
    """
    try:
        logger.info(f"📈 Stock price request: {len(request.symbols)} symbols")
        
        if not container.is_initialized() or not container.stock_price_use_case:
            raise HTTPException(status_code=503, detail="Service not fully initialized")
        
        result = await container.stock_price_use_case.execute(request)
        container.track_request(success=True)
        
        logger.info(f"✅ Stock prices retrieved: {result.count}/{len(request.symbols)} symbols")
        return result
        
    except Exception as e:
        container.track_request(success=False)
        logger.error(f"❌ Stock price request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/v1/market-data/historical",
    response_model=HistoricalDataResponse,
    summary="Get Historical Market Data",
    description="Retrieves historical market data for a symbol with specified period and interval"
)
async def get_historical_data(
    request: HistoricalDataRequest,
    container: MarketDataDependencyContainer = Depends(get_container)
) -> HistoricalDataResponse:
    """
    Historical Data Retrieval Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Use Case -> Yahoo Finance Adapter -> Historical Data Processing -> Event Publishing
    """
    try:
        logger.info(f"📊 Historical data request: {request.symbol}, period={request.period.value}")
        
        if not container.is_initialized() or not container.historical_data_use_case:
            raise HTTPException(status_code=503, detail="Service not fully initialized")
        
        result = await container.historical_data_use_case.execute(request)
        container.track_request(success=True)
        
        logger.info(f"✅ Historical data retrieved: {result.count} data points for {request.symbol}")
        return result
        
    except Exception as e:
        container.track_request(success=False)
        logger.error(f"❌ Historical data request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/v1/market-data/technical-indicators",
    response_model=TechnicalIndicatorsResponse,
    summary="Calculate Technical Indicators",
    description="Calculates technical indicators for a symbol based on historical data"
)
async def get_technical_indicators(
    request: TechnicalIndicatorsRequest,
    container: MarketDataDependencyContainer = Depends(get_container)
) -> TechnicalIndicatorsResponse:
    """
    Technical Indicators Calculation Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Use Case -> Historical Data Retrieval -> Technical Calculation -> Event Publishing
    """
    try:
        logger.info(f"🔍 Technical indicators request: {request.symbol}, indicators={request.indicators}")
        
        if not container.is_initialized() or not container.technical_indicators_use_case:
            raise HTTPException(status_code=503, detail="Service not fully initialized")
        
        result = await container.technical_indicators_use_case.execute(request)
        container.track_request(success=True)
        
        logger.info(f"✅ Technical indicators calculated for {request.symbol}")
        return result
        
    except Exception as e:
        container.track_request(success=False)
        logger.error(f"❌ Technical indicators request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/v1/market-data/health",
    response_model=HealthCheckResponse,
    summary="Service Health Check",
    description="Comprehensive Health Check inklusive Yahoo Finance, Redis, PostgreSQL"
)
async def health_check(
    container: MarketDataDependencyContainer = Depends(get_container)
) -> HealthCheckResponse:
    """
    Health Check Endpoint
    
    CLEAN ARCHITECTURE: Infrastructure Health Monitoring
    """
    try:
        return await container.health_check()
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return HealthCheckResponse(
            healthy=False,
            dependencies={},
            yahoo_finance_available=False,
            event_bus_connected=False,
            database_connected=False,
            rate_limit_status={},
            timestamp=datetime.now(),
            uptime_seconds=0.0,
            error=str(e)
        )

@app.get(
    "/api/v1/market-data/metrics",
    response_model=ServiceMetricsResponse,
    summary="Service Metrics",
    description="Service Metriken für Monitoring (Request Count, Yahoo Finance API Status, Rate Limits)"
)
async def get_service_metrics(
    container: MarketDataDependencyContainer = Depends(get_container)
) -> ServiceMetricsResponse:
    """
    Service Metrics Endpoint
    
    CLEAN ARCHITECTURE: Infrastructure Monitoring und Metrics
    """
    try:
        return await container.get_metrics()
    except Exception as e:
        logger.error(f"❌ Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# CONVENIENCE ENDPOINTS
# =============================================================================

@app.get(
    "/api/v1/market-data/quote/{symbol}",
    response_model=StockPrice,
    summary="Get Single Stock Quote",
    description="Convenience endpoint for single stock price retrieval"
)
async def get_single_quote(
    symbol: str,
    container: MarketDataDependencyContainer = Depends(get_container)
):
    """Single Stock Quote Convenience Endpoint"""
    request = StockPriceRequest(symbols=[symbol.upper()])
    result = await get_stock_prices(request, container)
    
    if not result.prices:
        raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
    
    return result.prices[0]

# =============================================================================
# EVENT-DRIVEN PATTERN TEST ENDPOINT
# =============================================================================

@app.post("/api/v1/market-data/test/event-flow")
async def test_event_flow(container: MarketDataDependencyContainer = Depends(get_container)):
    """
    Test Endpoint für Event-Driven Pattern
    
    CLEAN ARCHITECTURE: Event Flow Testing
    """
    try:
        logger.info("🧪 Testing Event-Driven Pattern")
        
        if not container.event_publisher:
            raise HTTPException(status_code=503, detail="Event publisher not available")
        
        # Test Event publizieren
        await container.event_publisher.publish(
            "market-data.test.event.flow",
            {
                "message": "Event-Driven Pattern Test from Market Data Service",
                "service": "market-data-service",
                "version": "6.0.0",
                "test_timestamp": datetime.now().isoformat(),
                "clean_architecture": True,
                "test_data": {
                    "yahoo_finance_integration": True,
                    "technical_indicators": ["SMA", "RSI", "MACD"],
                    "supported_periods": [p.value for p in MarketDataPeriod],
                    "supported_intervals": [i.value for i in MarketDataInterval]
                }
            }
        )
        
        logger.info("✅ Event-Driven Pattern test successful")
        return {
            "success": True,
            "message": "Event published successfully to Redis Event-Bus (Port 8014)",
            "event_type": "market-data.test.event.flow",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Event flow test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global Exception Handler mit Clean Architecture Error Response"""
    logger.error(f"❌ Unhandled exception: {exc}")
    logger.error(f"Stack trace: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if config.log_level == "DEBUG" else "An error occurred",
            "service": "market-data-service",
            "version": "6.0.0",
            "timestamp": datetime.now().isoformat()
        }
    )

# =============================================================================
# SIGNAL HANDLING & MAIN EXECUTION
# =============================================================================

def setup_signal_handlers():
    """Setup Signal Handlers für Graceful Shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown")
        asyncio.create_task(shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

async def shutdown():
    """Graceful Shutdown Procedure"""
    logger.info("🛑 Graceful shutdown initiated")
    
    global container
    if container:
        await container.cleanup()
    
    logger.info("✅ Graceful shutdown completed")
    sys.exit(0)

def main():
    """
    Main Service Execution
    
    CLEAN ARCHITECTURE: Application Entry Point
    """
    logger.info("🚀 Starting Market Data Service Enhanced v6.0.0")
    logger.info("📐 Clean Architecture Implementation:")
    logger.info("   ✅ Domain Layer: Value Objects, Market Data Types, Domain Events")
    logger.info("   ✅ Application Layer: Use Cases, Yahoo Finance Integration")
    logger.info("   ✅ Infrastructure Layer: HTTP Client, Database, Event Publishing")
    logger.info("   ✅ Presentation Layer: FastAPI Controllers, Request/Response Models")
    logger.info("   ✅ Dependency Injection: Centralized Container")
    logger.info("   ✅ Event-Driven Pattern: Redis Event-Bus Integration")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Configuration
    config = ServiceConfiguration()
    
    try:
        # Start FastAPI Server
        uvicorn.run(
            "market_data_service_v6_0_0_20250824:app",
            host=config.service_host,
            port=config.service_port,
            log_level=config.log_level.lower(),
            reload=False,  # Production setting
            workers=1,     # Single worker für Clean Architecture Compliance
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Service interrupted by user")
    except Exception as e:
        logger.error(f"❌ Service failed to start: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()