#!/usr/bin/env python3
"""
Infrastructure Layer - Yahoo Finance Market Data Adapter
Unified Profit Engine Enhanced v6.0 - Clean Architecture

EXTERNAL SERVICE ADAPTER:
- Implementiert MarketDataRepository Interface
- Kapseliert Yahoo Finance API Integration
- Error Handling und Retry Logic
- Data Mapping zu Domain Objects

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
Autor: Claude Code - Architecture Refactoring Specialist  
Datum: 24. August 2025
"""

import asyncio
import yfinance as yf
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
import logging

from ...domain.repositories import MarketDataRepository, MarketData


logger = logging.getLogger(__name__)


class YahooFinanceMarketDataAdapter(MarketDataRepository):
    """Yahoo Finance Implementation für Market Data Repository"""
    
    def __init__(self, retry_count: int = 3, timeout: float = 10.0):
        self.retry_count = retry_count
        self.timeout = timeout
        
        # Market Region Mapping
        self.region_mapping = {
            ".DE": "EU",
            ".L": "EU", 
            ".PA": "EU",
            ".MI": "EU",
            ".AS": "EU",
            ".SW": "EU",
            ".HE": "EU",
            ".VI": "EU",
            ".MC": "EU",
            ".OL": "EU",
            ".CO": "EU",
            ".ST": "EU",
            ".T": "ASIA",
            ".HK": "ASIA",
            ".SS": "ASIA",
            ".SZ": "ASIA",
            ".TW": "ASIA",
            ".KS": "ASIA",
            ".BO": "ASIA",
            ".NS": "ASIA",
            ".JK": "ASIA",
            ".BK": "ASIA",
            ".KL": "ASIA",
            "default": "US"
        }
    
    async def get_current_data(self, symbol: str) -> MarketData:
        """
        Lädt aktuelle Marktdaten von Yahoo Finance
        Implements Retry Pattern und Error Handling
        """
        for attempt in range(self.retry_count):
            try:
                logger.info(f"Loading current market data for {symbol} (attempt {attempt + 1})")
                
                # Yahoo Finance Ticker erstellen
                ticker = yf.Ticker(symbol)
                
                # Historische Daten für aktuellen Preis (da .info oft unzuverlässig)
                hist = ticker.history(period="5d", interval="1d")
                if hist.empty:
                    raise ValueError(f"No historical data available for {symbol}")
                
                # Company Info laden (mit Fallback)
                info = await self._get_ticker_info_safe(ticker)
                company_name = info.get('longName') or info.get('shortName') or symbol
                
                # Market Region bestimmen
                market_region = self._determine_market_region(symbol)
                
                # Aktuellste Marktdaten extrahieren
                latest_data = hist.iloc[-1]
                current_price = Decimal(str(latest_data['Close']))
                volume = int(latest_data['Volume'])
                
                # Zusätzliche Metriken aus Info extrahieren
                market_cap = self._safe_decimal(info.get('marketCap'))
                pe_ratio = info.get('trailingPE') or info.get('forwardPE')
                dividend_yield = info.get('dividendYield')
                beta = info.get('beta')
                
                # Historical Data für Repository Format aufbereiten
                historical_data = {
                    "prices": hist['Close'].to_dict(),
                    "volumes": hist['Volume'].to_dict(),
                    "dates": [d.strftime('%Y-%m-%d') for d in hist.index],
                    "period": "5d"
                }
                
                market_data = MarketData(
                    symbol=symbol,
                    company_name=company_name,
                    market_region=market_region,
                    current_price=current_price,
                    volume=volume,
                    historical_data=historical_data,
                    timestamp=datetime.now(),
                    market_cap=market_cap,
                    pe_ratio=pe_ratio,
                    dividend_yield=dividend_yield,
                    beta=beta
                )
                
                logger.info(f"Successfully loaded market data for {symbol}: {current_price}")
                return market_data
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                
                if attempt == self.retry_count - 1:
                    logger.error(f"Failed to load market data for {symbol} after {self.retry_count} attempts: {e}")
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    async def get_historical_data(self, symbol: str, days: int) -> List[MarketData]:
        """Lädt historische Marktdaten für spezifizierten Zeitraum"""
        try:
            logger.info(f"Loading {days} days of historical data for {symbol}")
            
            ticker = yf.Ticker(symbol)
            
            # Period für Yahoo Finance bestimmen
            if days <= 7:
                period = "7d"
            elif days <= 30:
                period = "1mo"
            elif days <= 90:
                period = "3mo"
            elif days <= 365:
                period = "1y"
            else:
                period = "2y"
            
            # Historische Daten laden
            hist = ticker.history(period=period, interval="1d")
            if hist.empty:
                raise ValueError(f"No historical data available for {symbol}")
            
            # Company Info einmal laden
            info = await self._get_ticker_info_safe(ticker)
            company_name = info.get('longName') or info.get('shortName') or symbol
            market_region = self._determine_market_region(symbol)
            
            # Zu MarketData Liste konvertieren
            historical_market_data = []
            
            # Nur die letzten N Tage nehmen
            recent_hist = hist.tail(days)
            
            for date, row in recent_hist.iterrows():
                market_data = MarketData(
                    symbol=symbol,
                    company_name=company_name,
                    market_region=market_region,
                    current_price=Decimal(str(row['Close'])),
                    volume=int(row['Volume']),
                    historical_data={"single_day": True},
                    timestamp=datetime.combine(date.date(), datetime.min.time()),
                    market_cap=self._safe_decimal(info.get('marketCap')),
                    pe_ratio=info.get('trailingPE'),
                    dividend_yield=info.get('dividendYield'),
                    beta=info.get('beta')
                )
                historical_market_data.append(market_data)
            
            logger.info(f"Loaded {len(historical_market_data)} historical data points for {symbol}")
            return historical_market_data
            
        except Exception as e:
            logger.error(f"Failed to load historical data for {symbol}: {e}")
            raise
    
    async def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """Lädt Company Information von Yahoo Finance"""
        try:
            logger.info(f"Loading company info for {symbol}")
            
            ticker = yf.Ticker(symbol)
            info = await self._get_ticker_info_safe(ticker)
            
            # Wichtigste Company-Informationen extrahieren
            company_info = {
                "symbol": symbol,
                "longName": info.get('longName'),
                "shortName": info.get('shortName'), 
                "industry": info.get('industry'),
                "sector": info.get('sector'),
                "country": info.get('country'),
                "website": info.get('website'),
                "business_summary": info.get('businessSummary'),
                "market_cap": info.get('marketCap'),
                "enterprise_value": info.get('enterpriseValue'),
                "trailing_pe": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "peg_ratio": info.get('pegRatio'),
                "price_to_book": info.get('priceToBook'),
                "dividend_yield": info.get('dividendYield'),
                "payout_ratio": info.get('payoutRatio'),
                "beta": info.get('beta'),
                "52_week_high": info.get('fiftyTwoWeekHigh'),
                "52_week_low": info.get('fiftyTwoWeekLow'),
                "50_day_average": info.get('fiftyDayAverage'),
                "200_day_average": info.get('twoHundredDayAverage'),
                "volume": info.get('volume'),
                "average_volume": info.get('averageVolume'),
                "market_region": self._determine_market_region(symbol),
                "currency": info.get('currency', 'USD'),
                "exchange": info.get('exchange'),
                "quote_type": info.get('quoteType')
            }
            
            logger.info(f"Loaded company info for {symbol}: {company_info.get('longName')}")
            return company_info
            
        except Exception as e:
            logger.error(f"Failed to load company info for {symbol}: {e}")
            raise
    
    async def _get_ticker_info_safe(self, ticker) -> Dict[str, Any]:
        """Sicherer Zugriff auf Ticker Info mit Fallback"""
        try:
            # info kann manchmal fehlschlagen, daher mit Timeout
            info = ticker.info
            return info or {}
        except Exception as e:
            logger.warning(f"Failed to load ticker info: {e}")
            return {}
    
    def _determine_market_region(self, symbol: str) -> str:
        """Bestimmt Market Region basierend auf Symbol-Suffix"""
        for suffix, region in self.region_mapping.items():
            if suffix == "default":
                continue
            if symbol.endswith(suffix):
                return region
        
        return self.region_mapping["default"]
    
    def _safe_decimal(self, value) -> Optional[Decimal]:
        """Sichere Konvertierung zu Decimal"""
        if value is None:
            return None
        
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, DecimalError):
            return None