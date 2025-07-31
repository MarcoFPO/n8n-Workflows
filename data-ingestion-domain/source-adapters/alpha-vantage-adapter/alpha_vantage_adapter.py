"""
📊 Alpha Vantage Market Data Adapter
NASDAQ-Partner für Premium-Marktdaten - 500 kostenlose API-Aufrufe/Tag
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

class AlphaVantageAdapter(BaseMarketDataAdapter):
    """
    🏆 Alpha Vantage API Adapter - NASDAQ-Partner
    
    Features:
    - 500 kostenlose API-Aufrufe/Tag
    - 50+ technische Indikatoren
    - Globale Börsen (US, Europa, Asien)
    - Fundamentaldaten
    - Echtzeit-Daten (15min delayed)
    """
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://www.alphavantage.co/query",
            name="alpha_vantage",
            source=MarketDataSource.ALPHA_VANTAGE
        )
        
        # Alpha Vantage spezifische Konfiguration
        self.daily_limit = 500
        self.minute_limit = 5  # Konservativ für kostenlose Version
        
    async def get_real_time_quote(self, symbol: str, exchange: Optional[Exchange] = None) -> MarketDataPoint:
        """Aktuelle Kursdaten von Alpha Vantage abrufen"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": normalized_symbol,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(self.base_url, params)
            
            if "Global Quote" not in data:
                raise Exception(f"No quote data for {symbol}: {data}")
                
            quote = data["Global Quote"]
            
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open_price=Decimal(quote.get("02. open", "0")),
                high_price=Decimal(quote.get("03. high", "0")), 
                low_price=Decimal(quote.get("04. low", "0")),
                close_price=Decimal(quote.get("05. price", "0")),
                volume=int(quote.get("06. volume", "0")),
                exchange=exchange,
                source=MarketDataSource.ALPHA_VANTAGE,
                raw_data=quote
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get quote for {symbol}: {e}")
            raise
    
    async def get_historical_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, interval: str = "1day",
                                exchange: Optional[Exchange] = None) -> List[MarketDataPoint]:
        """Historische Daten von Alpha Vantage abrufen"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        # Alpha Vantage Funktions-Mapping
        function_map = {
            "1min": "TIME_SERIES_INTRADAY",
            "5min": "TIME_SERIES_INTRADAY", 
            "15min": "TIME_SERIES_INTRADAY",
            "30min": "TIME_SERIES_INTRADAY",
            "60min": "TIME_SERIES_INTRADAY",
            "1day": "TIME_SERIES_DAILY",
            "1week": "TIME_SERIES_WEEKLY",
            "1month": "TIME_SERIES_MONTHLY"
        }
        
        function = function_map.get(interval, "TIME_SERIES_DAILY")
        
        params = {
            "function": function,
            "symbol": normalized_symbol,
            "apikey": self.api_key,
            "outputsize": "full"  # Vollständige historische Daten
        }
        
        # Intraday-spezifische Parameter
        if function == "TIME_SERIES_INTRADAY":
            params["interval"] = interval
            
        try:
            data = await self._make_request(self.base_url, params)
            
            # Alpha Vantage Response-Keys finden
            time_series_key = None
            for key in data.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break
                    
            if not time_series_key:
                raise Exception(f"No time series data for {symbol}: {list(data.keys())}")
                
            time_series = data[time_series_key]
            historical_data = []
            
            for date_str, values in time_series.items():
                timestamp = self._parse_datetime(date_str.split()[0])  # Nur Datum nehmen
                
                # Filterung nach Zeitraum
                if timestamp < start_date or timestamp > end_date:
                    continue
                    
                data_point = MarketDataPoint(
                    symbol=symbol,
                    timestamp=timestamp,
                    open_price=Decimal(values.get("1. open", "0")),
                    high_price=Decimal(values.get("2. high", "0")),
                    low_price=Decimal(values.get("3. low", "0")),
                    close_price=Decimal(values.get("4. close", "0")),
                    volume=int(values.get("5. volume", "0")),
                    adjusted_close=Decimal(values.get("5. adjusted close", values.get("4. close", "0"))),
                    exchange=exchange,
                    source=MarketDataSource.ALPHA_VANTAGE,
                    raw_data=values
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
        """Technische Indikatoren von Alpha Vantage berechnen"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        # Alpha Vantage Indikator-Mapping
        indicator_map = {
            "SMA": "SMA",       # Simple Moving Average
            "EMA": "EMA",       # Exponential Moving Average
            "RSI": "RSI",       # Relative Strength Index
            "MACD": "MACD",     # Moving Average Convergence Divergence
            "BBANDS": "BBANDS", # Bollinger Bands
            "STOCH": "STOCH",   # Stochastic Oscillator
            "ADX": "ADX",       # Average Directional Index
            "CCI": "CCI",       # Commodity Channel Index
            "AROON": "AROON",   # Aroon Indicator
            "OBV": "OBV"        # On Balance Volume
        }
        
        av_indicator = indicator_map.get(indicator.upper())
        if not av_indicator:
            raise ValueError(f"Unsupported indicator: {indicator}")
            
        params = {
            "function": av_indicator,
            "symbol": normalized_symbol,
            "interval": "daily",  # Standard für technische Indikatoren
            "time_period": period,
            "series_type": "close",
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(self.base_url, params)
            
            # Alpha Vantage Technical Analysis Response-Keys finden
            tech_key = None
            for key in data.keys():
                if "Technical Analysis" in key:
                    tech_key = key
                    break
                    
            if not tech_key:
                raise Exception(f"No technical analysis data for {symbol}: {list(data.keys())}")
                
            tech_data = data[tech_key]
            
            # Neueste Werte extrahieren (letzten 30 Tage)
            recent_data = {}
            sorted_dates = sorted(tech_data.keys(), reverse=True)[:30]
            
            for date_str in sorted_dates:
                values = tech_data[date_str]
                recent_data[date_str] = values
                
            self.logger.info(f"Retrieved {indicator} data for {symbol} (last 30 days)")
            return {
                "indicator": indicator,
                "symbol": symbol,
                "period": period,
                "data": recent_data,
                "metadata": data.get("Meta Data", {}),
                "raw_response": data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get {indicator} for {symbol}: {e}")
            raise
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Symbole bei Alpha Vantage suchen"""
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(self.base_url, params)
            
            if "bestMatches" not in data:
                return []
                
            results = []
            for match in data["bestMatches"]:
                results.append({
                    "symbol": match.get("1. symbol", ""),
                    "name": match.get("2. name", ""),
                    "type": match.get("3. type", ""),
                    "region": match.get("4. region", ""),
                    "market_open": match.get("5. marketOpen", ""),
                    "market_close": match.get("6. marketClose", ""),
                    "timezone": match.get("7. timezone", ""),
                    "currency": match.get("8. currency", ""),
                    "match_score": match.get("9. matchScore", "")
                })
                
            self.logger.info(f"Found {len(results)} symbols for query: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Symbol search failed for '{query}': {e}")
            return []
    
    def get_supported_exchanges(self) -> List[Exchange]:
        """Von Alpha Vantage unterstützte Börsen"""
        return [
            # US Märkte (vollständig unterstützt)
            Exchange.NASDAQ,
            Exchange.NYSE, 
            Exchange.AMEX,
            
            # Internationale Märkte (teilweise unterstützt)
            Exchange.XETRA,      # Deutschland
            Exchange.LSE,        # UK
            Exchange.TSE,        # Japan
            Exchange.HKEX,       # Hong Kong
            Exchange.TSX,        # Kanada
            Exchange.ASX,        # Australien
            Exchange.EURONEXT    # Europa
        ]
    
    def get_supported_data_types(self) -> List[DataType]:
        """Von Alpha Vantage unterstützte Datentypen"""
        return [
            DataType.REAL_TIME_QUOTE,
            DataType.HISTORICAL_DAILY,
            DataType.HISTORICAL_INTRADAY,
            DataType.TECHNICAL_INDICATORS,
            DataType.FUNDAMENTAL_DATA,
            DataType.GLOBAL_INDICES
        ]
    
    async def _get_api_limits(self) -> APILimits:
        """Alpha Vantage API-Limits"""
        return APILimits(
            calls_per_minute=self.minute_limit,
            calls_per_day=self.daily_limit,
            calls_remaining_today=max(0, self.daily_limit - self._call_count_today),
            is_premium=False
        )
    
    def _normalize_symbol(self, symbol: str, exchange: Optional[Exchange] = None) -> str:
        """Alpha Vantage Symbol-Normalisierung"""
        # Alpha Vantage unterstützt sowohl US-Symbole direkt als auch internationale mit Suffix
        if exchange and exchange not in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
            # Internationale Märkte - Alpha Vantage Format
            exchange_suffixes = {
                Exchange.XETRA: ".DEX",      # XETRA (Deutschland)
                Exchange.FRANKFURT: ".FRK",   # Frankfurt
                Exchange.LSE: ".LON",         # London
                Exchange.TSE: ".TYO",         # Tokyo
                Exchange.HKEX: ".HKG",        # Hong Kong
                Exchange.TSX: ".TOR",         # Toronto
                Exchange.ASX: ".AUS",         # Australia
                Exchange.EURONEXT: ".PAR"     # Paris
            }
            suffix = exchange_suffixes.get(exchange, "")
            return f"{symbol.upper()}{suffix}"
            
        return symbol.upper()
    
    async def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """Unternehmensdaten von Alpha Vantage (Fundamentals)"""
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        try:
            data = await self._make_request(self.base_url, params)
            
            if not data or "Symbol" not in data:
                raise Exception(f"No company data for {symbol}")
                
            return {
                "symbol": data.get("Symbol", ""),
                "name": data.get("Name", ""),
                "description": data.get("Description", ""),
                "exchange": data.get("Exchange", ""),
                "currency": data.get("Currency", ""),
                "country": data.get("Country", ""),
                "sector": data.get("Sector", ""),
                "industry": data.get("Industry", ""),
                "market_cap": data.get("MarketCapitalization", ""),
                "pe_ratio": data.get("PERatio", ""),
                "peg_ratio": data.get("PEGRatio", ""),
                "book_value": data.get("BookValue", ""),
                "dividend_per_share": data.get("DividendPerShare", ""),
                "dividend_yield": data.get("DividendYield", ""),
                "eps": data.get("EPS", ""),
                "revenue_per_share": data.get("RevenuePerShareTTM", ""),
                "profit_margin": data.get("ProfitMargin", ""),
                "operating_margin": data.get("OperatingMarginTTM", ""),
                "return_on_assets": data.get("ReturnOnAssetsTTM", ""),
                "return_on_equity": data.get("ReturnOnEquityTTM", ""),
                "revenue": data.get("RevenueTTM", ""),
                "gross_profit": data.get("GrossProfitTTM", ""),
                "diluted_eps": data.get("DilutedEPSTTM", ""),
                "quarterly_earnings_growth": data.get("QuarterlyEarningsGrowthYOY", ""),
                "quarterly_revenue_growth": data.get("QuarterlyRevenueGrowthYOY", ""),
                "analyst_target_price": data.get("AnalystTargetPrice", ""),
                "trailing_pe": data.get("TrailingPE", ""),
                "forward_pe": data.get("ForwardPE", ""),
                "price_to_sales_ratio": data.get("PriceToSalesRatioTTM", ""),
                "price_to_book_ratio": data.get("PriceToBookRatio", ""),
                "ev_to_revenue": data.get("EVToRevenue", ""),
                "ev_to_ebitda": data.get("EVToEBITDA", ""),
                "beta": data.get("Beta", ""),
                "52_week_high": data.get("52WeekHigh", ""),
                "52_week_low": data.get("52WeekLow", ""),
                "50_day_moving_avg": data.get("50DayMovingAverage", ""),
                "200_day_moving_avg": data.get("200DayMovingAverage", ""),
                "shares_outstanding": data.get("SharesOutstanding", ""),
                "shares_float": data.get("SharesFloat", ""),
                "shares_short": data.get("SharesShort", ""),
                "shares_short_prior_month": data.get("SharesShortPriorMonth", ""),
                "short_ratio": data.get("ShortRatio", ""),
                "short_percent_outstanding": data.get("ShortPercentOutstanding", ""),
                "short_percent_float": data.get("ShortPercentFloat", ""),
                "percent_insiders": data.get("PercentInsiders", ""),
                "percent_institutions": data.get("PercentInstitutions", ""),
                "forward_annual_dividend_rate": data.get("ForwardAnnualDividendRate", ""),
                "forward_annual_dividend_yield": data.get("ForwardAnnualDividendYield", ""),
                "payout_ratio": data.get("PayoutRatio", ""),
                "dividend_date": data.get("DividendDate", ""),
                "ex_dividend_date": data.get("ExDividendDate", ""),
                "last_split_factor": data.get("LastSplitFactor", ""),
                "last_split_date": data.get("LastSplitDate", ""),
                "raw_data": data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get company overview for {symbol}: {e}")
            raise