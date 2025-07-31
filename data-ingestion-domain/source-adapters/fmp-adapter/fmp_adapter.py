"""
💼 Financial Modeling Prep (FMP) Market Data Adapter  
Fokus auf Fundamentaldaten - 250 kostenlose API-Aufrufe/Tag
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json

from ..base_market_data_adapter import (
    BaseMarketDataAdapter, MarketDataSource, MarketDataPoint, 
    APILimits, Exchange, DataType
)

class FMPAdapter(BaseMarketDataAdapter):
    """
    💼 Financial Modeling Prep API Adapter - Fundamentaldaten-Spezialist
    
    Features:
    - 250 kostenlose API-Aufrufe/Tag
    - 90+ Börsen weltweit (70,000+ Symbole)
    - 30+ Jahre historische Daten
    - Detaillierte Fundamentaldaten (Bilanzen, GuV, Cashflow)
    - Analystenbewertungen und Preisziele
    """
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://financialmodelingprep.com/api",
            name="fmp",
            source=MarketDataSource.FMP
        )
        
        # FMP spezifische Konfiguration
        self.daily_limit = 250  # Kostenlose Version
        self.minute_limit = 10   # Konservativ
        
        # FMP API Versionen
        self.v3_endpoint = f"{self.base_url}/v3"
        self.v4_endpoint = f"{self.base_url}/v4"
        
    async def get_real_time_quote(self, symbol: str, exchange: Optional[Exchange] = None) -> MarketDataPoint:
        """Aktuelle Kursdaten von FMP abrufen"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        url = f"{self.v3_endpoint}/quote/{normalized_symbol}"
        params = {"apikey": self.api_key}
        
        try:
            data = await self._make_request(url, params)
            
            if not data or len(data) == 0:
                raise Exception(f"No quote data for {symbol}")
                
            quote = data[0]  # FMP returns array
            
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open_price=Decimal(str(quote.get("open", 0))),
                high_price=Decimal(str(quote.get("dayHigh", 0))),
                low_price=Decimal(str(quote.get("dayLow", 0))),
                close_price=Decimal(str(quote.get("price", 0))),
                volume=int(quote.get("volume", 0)),
                market_cap=Decimal(str(quote.get("marketCap", 0))) if quote.get("marketCap") else None,
                pe_ratio=float(quote.get("pe", 0)) if quote.get("pe") else None,
                exchange=exchange,
                currency="USD",  # FMP hauptsächlich USD
                source=MarketDataSource.FMP,
                raw_data=quote
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get quote for {symbol}: {e}")
            raise
    
    async def get_historical_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, interval: str = "1day",
                                exchange: Optional[Exchange] = None) -> List[MarketDataPoint]:
        """Historische Daten von FMP abrufen"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        # FMP unterstützt hauptsächlich daily data im kostenlosen Tier
        if interval != "1day":
            self.logger.warning(f"FMP free tier mainly supports daily data, requested: {interval}")
        
        # FMP Datumsformat: YYYY-MM-DD
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        url = f"{self.v3_endpoint}/historical-price-full/{normalized_symbol}"
        params = {
            "apikey": self.api_key,
            "from": start_str,
            "to": end_str
        }
        
        try:
            data = await self._make_request(url, params)
            
            if "historical" not in data:
                raise Exception(f"No historical data for {symbol}: {list(data.keys())}")
                
            historical_data = []
            
            for entry in data["historical"]:
                timestamp = self._parse_datetime(entry["date"])
                
                data_point = MarketDataPoint(
                    symbol=symbol,
                    timestamp=timestamp,
                    open_price=Decimal(str(entry.get("open", 0))),
                    high_price=Decimal(str(entry.get("high", 0))),
                    low_price=Decimal(str(entry.get("low", 0))),
                    close_price=Decimal(str(entry.get("close", 0))),
                    volume=int(entry.get("volume", 0)),
                    adjusted_close=Decimal(str(entry.get("adjClose", entry.get("close", 0)))),
                    exchange=exchange,
                    currency="USD",
                    source=MarketDataSource.FMP,
                    raw_data=entry
                )
                
                historical_data.append(data_point)
            
            # Sortierung nach Datum (neueste zuerst) 
            historical_data.sort(key=lambda x: x.timestamp, reverse=True)
            
            self.logger.info(f"Retrieved {len(historical_data)} historical data points for {symbol}")
            return historical_data
            
        except Exception as e:
            self.logger.error(f"Failed to get historical data for {symbol}: {e}")
            raise
    
    async def get_technical_indicators(self, symbol: str, indicator: str,
                                     period: int = 20, exchange: Optional[Exchange] = None) -> Dict[str, Any]:
        """
        Technische Indikatoren von FMP abrufen
        FMP bietet einige technische Indikatoren in der API
        """
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        # FMP technische Indikatoren verfügbar
        fmp_indicators = {
            "SMA": "sma",
            "EMA": "ema", 
            "RSI": "rsi",
            "ADX": "adx",
            "WILLIAMS": "williams"
        }
        
        fmp_indicator = fmp_indicators.get(indicator.upper())
        if not fmp_indicator:
            raise ValueError(f"Technical indicator {indicator} not supported by FMP")
        
        url = f"{self.v3_endpoint}/technical_indicator/daily/{normalized_symbol}"
        params = {
            "period": period,
            "type": fmp_indicator,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(url, params)
            
            if not data:
                raise Exception(f"No technical indicator data for {symbol}")
            
            # Extrahiere die letzten 30 Datenpunkte
            recent_data = {}
            for entry in data[:30]:  # Neueste 30 Einträge
                date_str = entry.get("date", "")
                indicator_value = entry.get(fmp_indicator, 0)
                recent_data[date_str] = {indicator.upper(): indicator_value}
            
            self.logger.info(f"Retrieved {indicator} data for {symbol} (last 30 days)")
            return {
                "indicator": indicator,
                "symbol": symbol,
                "period": period,
                "data": recent_data,
                "source": "fmp_api",
                "raw_response": data[:30]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get {indicator} for {symbol}: {e}")
            raise
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Symbole bei FMP suchen"""
        url = f"{self.v3_endpoint}/search"
        params = {
            "query": query,
            "limit": 20,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(url, params)
            
            if not data:
                return []
                
            results = []
            for item in data:
                results.append({
                    "symbol": item.get("symbol", ""),
                    "name": item.get("name", ""),
                    "currency": item.get("currency", ""),
                    "stock_exchange": item.get("stockExchange", ""),
                    "exchange_short_name": item.get("exchangeShortName", "")
                })
                
            self.logger.info(f"Found {len(results)} symbols for query: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Symbol search failed for '{query}': {e}")
            return []
    
    def get_supported_exchanges(self) -> List[Exchange]:
        """Von FMP unterstützte Börsen"""
        return [
            # US Märkte (vollständig unterstützt)
            Exchange.NASDAQ,
            Exchange.NYSE,
            Exchange.AMEX,
            
            # Internationale Märkte (90+ Börsen laut FMP)
            Exchange.XETRA,      # Deutschland
            Exchange.LSE,        # UK
            Exchange.TSE,        # Japan
            Exchange.HKEX,       # Hong Kong
            Exchange.TSX,        # Kanada
            Exchange.ASX,        # Australien
            Exchange.EURONEXT    # Europa
        ]
    
    def get_supported_data_types(self) -> List[DataType]:
        """Von FMP unterstützte Datentypen"""
        return [
            DataType.REAL_TIME_QUOTE,
            DataType.HISTORICAL_DAILY,
            DataType.TECHNICAL_INDICATORS,
            DataType.FUNDAMENTAL_DATA,      # FMP Stärke!
            DataType.GLOBAL_INDICES
        ]
    
    async def _get_api_limits(self) -> APILimits:
        """FMP API-Limits"""
        return APILimits(
            calls_per_minute=self.minute_limit,
            calls_per_day=self.daily_limit,
            calls_remaining_today=max(0, self.daily_limit - self._call_count_today),
            is_premium=False
        )
    
    def _normalize_symbol(self, symbol: str, exchange: Optional[Exchange] = None) -> str:
        """FMP Symbol-Normalisierung"""
        # FMP verwendet hauptsächlich Standard-US-Symbole
        # Internationale Symbole können Exchange-Suffixe haben
        if exchange and exchange not in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
            # FMP Exchange-Suffixe (falls erforderlich)
            exchange_suffixes = {
                Exchange.XETRA: ".DE",
                Exchange.LSE: ".L", 
                Exchange.TSE: ".T",
                Exchange.HKEX: ".HK",
                Exchange.TSX: ".TO",
                Exchange.ASX: ".AX"
            }
            suffix = exchange_suffixes.get(exchange, "")
            return f"{symbol.upper()}{suffix}"
            
        return symbol.upper()
    
    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Detailliertes Unternehmensprofil von FMP"""
        url = f"{self.v3_endpoint}/profile/{symbol}"
        params = {"apikey": self.api_key}
        
        try:
            data = await self._make_request(url, params)
            
            if not data or len(data) == 0:
                raise Exception(f"No company profile for {symbol}")
                
            profile = data[0]
            
            return {
                "symbol": profile.get("symbol", ""),
                "company_name": profile.get("companyName", ""),
                "price": profile.get("price", 0),
                "beta": profile.get("beta", 0),
                "vol_avg": profile.get("volAvg", 0),
                "market_cap": profile.get("mktCap", 0),
                "last_div": profile.get("lastDiv", 0),
                "range": profile.get("range", ""),
                "changes": profile.get("changes", 0),
                "changes_percentage": profile.get("changesPercentage", ""),
                "currency": profile.get("currency", "USD"),
                "cik": profile.get("cik", ""),
                "isin": profile.get("isin", ""),
                "cusip": profile.get("cusip", ""),
                "exchange": profile.get("exchange", ""),
                "exchange_short_name": profile.get("exchangeShortName", ""),
                "industry": profile.get("industry", ""),
                "website": profile.get("website", ""),
                "description": profile.get("description", ""),
                "ceo": profile.get("ceo", ""),
                "sector": profile.get("sector", ""),
                "country": profile.get("country", ""),
                "full_time_employees": profile.get("fullTimeEmployees", ""),
                "phone": profile.get("phone", ""),
                "address": profile.get("address", ""),
                "city": profile.get("city", ""),
                "state": profile.get("state", ""),
                "zip": profile.get("zip", ""),
                "dcf_diff": profile.get("dcfDiff", 0),
                "dcf": profile.get("dcf", 0),
                "image": profile.get("image", ""),
                "ipo_date": profile.get("ipoDate", ""),
                "default_image": profile.get("defaultImage", False),
                "is_etf": profile.get("isEtf", False),
                "is_actively_trading": profile.get("isActivelyTrading", True),
                "is_adr": profile.get("isAdr", False),
                "is_fund": profile.get("isFund", False),
                "raw_data": profile
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get company profile for {symbol}: {e}")
            raise
    
    async def get_financial_statements(self, symbol: str, statement_type: str = "income", 
                                     period: str = "annual", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Finanzberichte von FMP abrufen
        statement_type: 'income', 'balance-sheet', 'cash-flow'
        period: 'annual', 'quarter'
        """
        url = f"{self.v3_endpoint}/{statement_type}-statement/{symbol}"
        params = {
            "period": period,
            "limit": limit,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(url, params)
            
            if not data:
                raise Exception(f"No {statement_type} statements for {symbol}")
            
            self.logger.info(f"Retrieved {len(data)} {statement_type} statements for {symbol}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to get {statement_type} statements for {symbol}: {e}")
            raise
    
    async def get_key_metrics(self, symbol: str, period: str = "annual", limit: int = 5) -> List[Dict[str, Any]]:
        """Wichtige Finanzkennzahlen von FMP"""
        url = f"{self.v3_endpoint}/key-metrics/{symbol}"
        params = {
            "period": period,
            "limit": limit,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(url, params)
            
            if not data:
                raise Exception(f"No key metrics for {symbol}")
            
            self.logger.info(f"Retrieved key metrics for {symbol}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to get key metrics for {symbol}: {e}")
            raise
    
    async def get_financial_ratios(self, symbol: str, period: str = "annual", limit: int = 5) -> List[Dict[str, Any]]:
        """Finanzkennzahlen von FMP"""
        url = f"{self.v3_endpoint}/ratios/{symbol}"
        params = {
            "period": period,
            "limit": limit,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(url, params)
            
            if not data:
                raise Exception(f"No financial ratios for {symbol}")
            
            self.logger.info(f"Retrieved financial ratios for {symbol}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to get financial ratios for {symbol}: {e}")
            raise
            
    async def get_analyst_estimates(self, symbol: str) -> Dict[str, Any]:
        """Analystenschätzungen von FMP"""
        url = f"{self.v3_endpoint}/analyst-estimates/{symbol}"
        params = {
            "limit": 10,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(url, params)
            
            if not data:
                raise Exception(f"No analyst estimates for {symbol}")
            
            self.logger.info(f"Retrieved analyst estimates for {symbol}")
            return {
                "symbol": symbol,
                "estimates": data,
                "count": len(data)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get analyst estimates for {symbol}: {e}")
            raise
    
    async def get_price_target(self, symbol: str) -> Dict[str, Any]:
        """Analystenkursziele von FMP"""
        url = f"{self.v4_endpoint}/price-target"
        params = {
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(url, params)
            
            if not data:
                raise Exception(f"No price targets for {symbol}")
            
            self.logger.info(f"Retrieved price targets for {symbol}")
            return {
                "symbol": symbol,
                "price_targets": data,
                "count": len(data)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get price targets for {symbol}: {e}")
            raise