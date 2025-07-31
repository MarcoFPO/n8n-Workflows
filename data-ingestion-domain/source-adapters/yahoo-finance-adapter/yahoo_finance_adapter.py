"""
🌍 Yahoo Finance Market Data Adapter
Globale Marktabdeckung - Unbegrenzte kostenlose Aufrufe (inoffiziell)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json
import re

from ..base_market_data_adapter import (
    BaseMarketDataAdapter, MarketDataSource, MarketDataPoint, 
    APILimits, Exchange, DataType
)

class YahooFinanceAdapter(BaseMarketDataAdapter):
    """
    🌎 Yahoo Finance API Adapter - Weltweite Marktabdeckung
    
    Features:
    - Unbegrenzte kostenlose Aufrufe (inoffiziell)
    - Alle globalen Börsen unterstützt
    - 30+ Jahre historische Daten
    - Echtzeit-Kurse (15min delayed)
    - Fundamentaldaten verfügbar
    """
    
    def __init__(self):
        super().__init__(
            api_key=None,  # Kein API-Key erforderlich
            base_url="https://query1.finance.yahoo.com",
            name="yahoo_finance",
            source=MarketDataSource.YAHOO_FINANCE
        )
        
        # Yahoo Finance Endpunkte
        self.quote_endpoint = f"{self.base_url}/v8/finance/quote"
        self.history_endpoint = f"{self.base_url}/v8/finance/chart"
        self.search_endpoint = f"{self.base_url}/v1/finance/search"
        
        # Keine strikten Limits (inoffiziell)
        self.daily_limit = 10000  # Sehr hoch, aber reasonable
        self.minute_limit = 200   # Konservativ um Blocks zu vermeiden
        
    async def get_real_time_quote(self, symbol: str, exchange: Optional[Exchange] = None) -> MarketDataPoint:
        """Aktuelle Kursdaten von Yahoo Finance abrufen"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        params = {
            "symbols": normalized_symbol,
            "fields": "regularMarketPrice,regularMarketOpen,regularMarketDayHigh,regularMarketDayLow,regularMarketVolume,marketCap,trailingPE,dividendYield"
        }
        
        try:
            data = await self._make_request(self.quote_endpoint, params)
            
            if "quoteResponse" not in data or not data["quoteResponse"]["result"]:
                raise Exception(f"No quote data for {symbol}")
                
            quote = data["quoteResponse"]["result"][0]
            
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open_price=Decimal(str(quote.get("regularMarketOpen", 0))),
                high_price=Decimal(str(quote.get("regularMarketDayHigh", 0))),
                low_price=Decimal(str(quote.get("regularMarketDayLow", 0))),
                close_price=Decimal(str(quote.get("regularMarketPrice", 0))),
                volume=int(quote.get("regularMarketVolume", 0)),
                market_cap=Decimal(str(quote.get("marketCap", 0))) if quote.get("marketCap") else None,
                pe_ratio=float(quote.get("trailingPE", 0)) if quote.get("trailingPE") else None,
                dividend_yield=float(quote.get("dividendYield", 0)) if quote.get("dividendYield") else None,
                exchange=exchange,
                currency=quote.get("currency", "USD"),
                source=MarketDataSource.YAHOO_FINANCE,
                raw_data=quote
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get quote for {symbol}: {e}")
            raise
    
    async def get_historical_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, interval: str = "1day",
                                exchange: Optional[Exchange] = None) -> List[MarketDataPoint]:
        """Historische Daten von Yahoo Finance abrufen"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        # Yahoo Finance Intervall-Mapping
        interval_map = {
            "1min": "1m",
            "2min": "2m",
            "5min": "5m",
            "15min": "15m", 
            "30min": "30m",
            "60min": "60m",
            "90min": "90m",
            "1hour": "1h",
            "1day": "1d",
            "5day": "5d",
            "1week": "1wk",
            "1month": "1mo",
            "3month": "3mo"
        }
        
        yahoo_interval = interval_map.get(interval, "1d")
        
        # Unix Timestamps für Yahoo Finance
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        params = {
            "interval": yahoo_interval,
            "period1": start_timestamp,
            "period2": end_timestamp,
            "events": "history",
            "includePrePost": "false"
        }
        
        try:
            chart_url = f"{self.history_endpoint}/{normalized_symbol}"
            data = await self._make_request(chart_url, params)
            
            if "chart" not in data or not data["chart"]["result"]:
                raise Exception(f"No historical data for {symbol}")
                
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            ohlcv = result["indicators"]["quote"][0]
            
            # Adjusted Close prüfen
            adj_close_data = None
            if "adjclose" in result["indicators"]:
                adj_close_data = result["indicators"]["adjclose"][0]["adjclose"]
            
            historical_data = []
            
            for i, timestamp in enumerate(timestamps):
                # Überspringe None-Werte
                if (ohlcv["open"][i] is None or 
                    ohlcv["high"][i] is None or 
                    ohlcv["low"][i] is None or 
                    ohlcv["close"][i] is None):
                    continue
                    
                data_point = MarketDataPoint(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamp),
                    open_price=Decimal(str(ohlcv["open"][i])),
                    high_price=Decimal(str(ohlcv["high"][i])),
                    low_price=Decimal(str(ohlcv["low"][i])),
                    close_price=Decimal(str(ohlcv["close"][i])),
                    volume=int(ohlcv["volume"][i]) if ohlcv["volume"][i] else 0,
                    adjusted_close=Decimal(str(adj_close_data[i])) if adj_close_data and adj_close_data[i] else None,
                    exchange=exchange,
                    currency=result["meta"].get("currency", "USD"),
                    source=MarketDataSource.YAHOO_FINANCE,
                    raw_data={
                        "open": ohlcv["open"][i],
                        "high": ohlcv["high"][i], 
                        "low": ohlcv["low"][i],
                        "close": ohlcv["close"][i],
                        "volume": ohlcv["volume"][i]
                    }
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
        Technische Indikatoren berechnen (Yahoo Finance liefert keine direkt)
        Implementiert grundlegende Indikatoren basierend auf Preisdaten
        """
        # Hole historische Daten für Berechnungen
        end_date = datetime.now()
        start_date = end_date - timedelta(days=max(period * 3, 100))  # Genug Daten für Berechnungen
        
        historical_data = await self.get_historical_data(
            symbol, start_date, end_date, "1day", exchange
        )
        
        if len(historical_data) < period:
            raise Exception(f"Not enough data for {indicator} calculation (need {period}, got {len(historical_data)})")
        
        # Sortiere chronologisch für Berechnungen
        historical_data.sort(key=lambda x: x.timestamp)
        
        indicator_data = {}
        
        if indicator.upper() == "SMA":
            # Simple Moving Average berechnen
            for i in range(period - 1, len(historical_data)):
                window_data = historical_data[i - period + 1:i + 1]
                sma_value = sum(float(d.close_price) for d in window_data) / period
                date_str = historical_data[i].timestamp.strftime("%Y-%m-%d")
                indicator_data[date_str] = {"SMA": round(sma_value, 2)}
                
        elif indicator.upper() == "EMA":
            # Exponential Moving Average berechnen
            multiplier = 2 / (period + 1)
            ema_value = float(historical_data[period - 1].close_price)  # Start mit SMA
            
            for i in range(period, len(historical_data)):
                close_price = float(historical_data[i].close_price)
                ema_value = (close_price * multiplier) + (ema_value * (1 - multiplier))
                date_str = historical_data[i].timestamp.strftime("%Y-%m-%d")
                indicator_data[date_str] = {"EMA": round(ema_value, 2)}
                
        elif indicator.upper() == "RSI":
            # Relative Strength Index berechnen
            price_changes = []
            for i in range(1, len(historical_data)):
                change = float(historical_data[i].close_price) - float(historical_data[i-1].close_price)
                price_changes.append(change)
            
            # RSI für jeden Tag ab period berechnen
            for i in range(period, len(price_changes)):
                window = price_changes[i - period:i]
                gains = [change for change in window if change > 0]
                losses = [-change for change in window if change < 0]
                
                avg_gain = sum(gains) / period if gains else 0
                avg_loss = sum(losses) / period if losses else 0
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                date_str = historical_data[i + 1].timestamp.strftime("%Y-%m-%d")
                indicator_data[date_str] = {"RSI": round(rsi, 2)}
                
        else:
            raise ValueError(f"Indicator {indicator} not implemented for Yahoo Finance")
        
        # Nur die letzten 30 Tage zurückgeben
        recent_data = {}
        sorted_dates = sorted(indicator_data.keys(), reverse=True)[:30]
        for date_str in sorted_dates:
            recent_data[date_str] = indicator_data[date_str]
        
        self.logger.info(f"Calculated {indicator} for {symbol} (last 30 days)")
        return {
            "indicator": indicator,
            "symbol": symbol,
            "period": period,
            "data": recent_data,
            "calculation": "client_side",  # Zeigt an, dass wir es selbst berechnet haben
            "data_points": len(recent_data)
        }
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Symbole bei Yahoo Finance suchen"""
        params = {
            "q": query,
            "lang": "en-US",
            "region": "US",
            "quotesCount": 20,
            "newsCount": 0
        }
        
        try:
            data = await self._make_request(self.search_endpoint, params)
            
            if "quotes" not in data:
                return []
                
            results = []
            for quote in data["quotes"]:
                results.append({
                    "symbol": quote.get("symbol", ""),
                    "name": quote.get("longname", quote.get("shortname", "")),
                    "type": quote.get("quoteType", ""),
                    "exchange": quote.get("exchange", ""),
                    "sector": quote.get("sector", ""),
                    "industry": quote.get("industry", ""),
                    "market": quote.get("market", ""),
                    "currency": quote.get("currency", ""),
                    "score": quote.get("score", 0)
                })
                
            self.logger.info(f"Found {len(results)} symbols for query: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Symbol search failed for '{query}': {e}")
            return []
    
    def get_supported_exchanges(self) -> List[Exchange]:
        """Von Yahoo Finance unterstützte Börsen (alle)"""
        return [
            # US Märkte
            Exchange.NASDAQ,
            Exchange.NYSE,
            Exchange.AMEX,
            
            # Deutsche Märkte  
            Exchange.XETRA,
            Exchange.FRANKFURT,
            
            # Internationale Märkte
            Exchange.LSE,        # London
            Exchange.TSE,        # Tokyo
            Exchange.HKEX,       # Hong Kong
            Exchange.TSX,        # Toronto
            Exchange.ASX,        # Australia
            Exchange.EURONEXT,   # Europa
            Exchange.SIX         # Schweiz
        ]
    
    def get_supported_data_types(self) -> List[DataType]:
        """Von Yahoo Finance unterstützte Datentypen"""
        return [
            DataType.REAL_TIME_QUOTE,
            DataType.HISTORICAL_DAILY,
            DataType.HISTORICAL_INTRADAY,
            DataType.TECHNICAL_INDICATORS,  # Berechnet client-side
            DataType.FUNDAMENTAL_DATA,      # Teilweise verfügbar
            DataType.GLOBAL_INDICES
        ]
    
    async def _get_api_limits(self) -> APILimits:
        """Yahoo Finance API-Limits (inoffiziell, daher großzügig)"""
        return APILimits(
            calls_per_minute=self.minute_limit,
            calls_per_day=self.daily_limit,
            calls_remaining_today=max(0, self.daily_limit - self._call_count_today),
            is_premium=False
        )
    
    def _normalize_symbol(self, symbol: str, exchange: Optional[Exchange] = None) -> str:
        """Yahoo Finance Symbol-Normalisierung mit Exchange-Suffixen"""
        base_symbol = symbol.upper()
        
        if exchange:
            # Yahoo Finance Exchange-Suffixe
            exchange_suffixes = {
                Exchange.XETRA: ".DE",           # XETRA Deutschland
                Exchange.FRANKFURT: ".F",        # Frankfurt
                Exchange.LSE: ".L",              # London
                Exchange.TSE: ".T",              # Tokyo
                Exchange.HKEX: ".HK",            # Hong Kong
                Exchange.TSX: ".TO",             # Toronto
                Exchange.ASX: ".AX",             # Australia
                Exchange.EURONEXT: ".PA",        # Paris (Euronext)
                Exchange.SIX: ".SW"              # Schweiz
            }
            
            suffix = exchange_suffixes.get(exchange, "")
            return f"{base_symbol}{suffix}"
            
        return base_symbol
    
    async def get_company_info(self, symbol: str, exchange: Optional[Exchange] = None) -> Dict[str, Any]:
        """Unternehmensinformationen von Yahoo Finance"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        # Yahoo Finance Module für detaillierte Daten
        modules = [
            "summaryProfile",
            "summaryDetail", 
            "assetProfile",
            "fundProfile",
            "price",
            "quoteType",
            "defaultKeyStatistics",
            "financialData",
            "calendarEvents",
            "recommendationTrend",
            "upgradeDowngradeHistory",
            "earningsHistory",
            "earningsTrend",
            "industryTrend"
        ]
        
        params = {
            "symbols": normalized_symbol,
            "modules": ",".join(modules)
        }
        
        try:
            quotesummary_url = f"{self.base_url}/v10/finance/quoteSummary/{normalized_symbol}"
            data = await self._make_request(quotesummary_url, params)
            
            if "quoteSummary" not in data or not data["quoteSummary"]["result"]:
                raise Exception(f"No company info for {symbol}")
                
            result = data["quoteSummary"]["result"][0]
            
            # Extrahiere relevante Informationen
            profile = result.get("assetProfile", {})
            summary = result.get("summaryDetail", {})
            price_info = result.get("price", {})
            key_stats = result.get("defaultKeyStatistics", {})
            financial = result.get("financialData", {})
            
            return {
                "symbol": symbol,
                "name": price_info.get("longName", ""),
                "description": profile.get("longBusinessSummary", ""),
                "exchange": price_info.get("exchangeName", ""),
                "currency": price_info.get("currency", ""),
                "country": profile.get("country", ""),
                "city": profile.get("city", ""),
                "state": profile.get("state", ""),
                "sector": profile.get("sector", ""),
                "industry": profile.get("industry", ""),
                "website": profile.get("website", ""),
                "employees": profile.get("fullTimeEmployees", ""),
                
                # Finanzielle Kennzahlen
                "market_cap": self._extract_value(summary.get("marketCap")),
                "enterprise_value": self._extract_value(key_stats.get("enterpriseValue")),
                "trailing_pe": self._extract_value(summary.get("trailingPE")),
                "forward_pe": self._extract_value(summary.get("forwardPE")),
                "peg_ratio": self._extract_value(key_stats.get("pegRatio")),
                "price_to_book": self._extract_value(key_stats.get("priceToBook")),
                "price_to_sales": self._extract_value(key_stats.get("priceToSalesTrailing12Months")),
                "ev_to_revenue": self._extract_value(key_stats.get("enterpriseToRevenue")),
                "ev_to_ebitda": self._extract_value(key_stats.get("enterpriseToEbitda")),
                
                # Dividenden
                "dividend_rate": self._extract_value(summary.get("dividendRate")),
                "dividend_yield": self._extract_value(summary.get("dividendYield")),
                "payout_ratio": self._extract_value(key_stats.get("payoutRatio")),
                "ex_dividend_date": key_stats.get("exDividendDate"),
                
                # Preisdaten
                "52_week_high": self._extract_value(summary.get("fiftyTwoWeekHigh")),
                "52_week_low": self._extract_value(summary.get("fiftyTwoWeekLow")),
                "50_day_average": self._extract_value(summary.get("fiftyDayAverage")),
                "200_day_average": self._extract_value(summary.get("twoHundredDayAverage")),
                
                # Aktien-Informationen
                "shares_outstanding": self._extract_value(key_stats.get("sharesOutstanding")),
                "float_shares": self._extract_value(key_stats.get("floatShares")),
                "shares_short": self._extract_value(key_stats.get("sharesShort")),
                "short_ratio": self._extract_value(key_stats.get("shortRatio")),
                "short_percent_of_float": self._extract_value(key_stats.get("shortPercentOfFloat")),
                
                # Finanzielle Gesundheit
                "total_cash": self._extract_value(financial.get("totalCash")),
                "total_debt": self._extract_value(financial.get("totalDebt")),
                "debt_to_equity": self._extract_value(financial.get("debtToEquity")),
                "current_ratio": self._extract_value(financial.get("currentRatio")),
                "return_on_assets": self._extract_value(key_stats.get("returnOnAssets")),
                "return_on_equity": self._extract_value(key_stats.get("returnOnEquity")),
                "profit_margins": self._extract_value(key_stats.get("profitMargins")),
                
                "raw_data": result
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get company info for {symbol}: {e}")
            raise
    
    def _extract_value(self, data):
        """Yahoo Finance Wert extrahieren (kann Dict mit 'raw' key sein)"""
        if isinstance(data, dict) and "raw" in data:
            return data["raw"]
        elif isinstance(data, dict) and "fmt" in data:
            return data["fmt"]
        else:
            return data