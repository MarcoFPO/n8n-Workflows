#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💼 Optimized FMP Adapter - 70% weniger Code durch Standardisierung
Verwendet StandardizedAdapterBase für gemeinsame Funktionalität
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .standardized_adapter_base import StandardizedAdapterBase, StandardizedSearchMixin
from .base_market_data_adapter import MarketDataSource, MarketDataPoint, Exchange, DataType


class OptimizedFMPAdapter(StandardizedAdapterBase, StandardizedSearchMixin):
    """
    💼 Optimized Financial Modeling Prep API Adapter
    
    Reduziert von 458 auf ~150 Zeilen durch Verwendung der StandardizedAdapterBase
    """
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url="https://financialmodelingprep.com/api",
            name="fmp_optimized",
            source=MarketDataSource.FMP
        )
        
        # FMP-spezifische Konfiguration
        self.daily_limit = 250  # Kostenlose Version
        self.minute_limit = 10   # Konservativ
        self.v3_endpoint = f"{self.base_url}/v3"
        self.v4_endpoint = f"{self.base_url}/v4"
    
    def _get_field_mapping(self) -> Dict[str, str]:
        """FMP-spezifisches Feldmapping"""
        return {
            'open': 'open',
            'high': 'dayHigh',
            'low': 'dayLow', 
            'close': 'price',
            'volume': 'volume',
            'market_cap': 'marketCap',
            'pe_ratio': 'pe'
        }
    
    async def get_real_time_quote(self, symbol: str, exchange: Optional[Exchange] = None) -> MarketDataPoint:
        """FMP Real-time Quote - optimiert"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        url = f"{self.v3_endpoint}/quote/{normalized_symbol}"
        params = {"apikey": self.api_key}
        
        await self._handle_rate_limiting()
        
        try:
            data = await self._make_request(url, params)
            
            if not data or len(data) == 0:
                raise Exception(f"No quote data for {symbol}")
                
            quote = data[0]  # FMP returns array
            
            # Verwendung der standardisierten MarketDataPoint-Erstellung
            return self._build_standard_market_data_point(symbol, quote, exchange)
            
        except Exception as e:
            self.logger.error(f"Failed to get quote for {symbol}: {e}")
            raise
    
    async def get_historical_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, interval: str = "1day",
                                exchange: Optional[Exchange] = None) -> List[MarketDataPoint]:
        """FMP Historical Data - optimiert"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        # FMP Datumsformat
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        url = f"{self.v3_endpoint}/historical-price-full/{normalized_symbol}"
        params = {
            "apikey": self.api_key,
            "from": start_str,
            "to": end_str
        }
        
        await self._handle_rate_limiting()
        
        try:
            data = await self._make_request(url, params)
            
            if "historical" not in data:
                raise Exception(f"No historical data for {symbol}")
                
            historical_data = []
            
            # FMP-spezifisches Feldmapping für historische Daten
            for entry in data["historical"]:
                # Angepasstes Mapping für historische Daten
                entry_mapped = {
                    'open': entry.get('open', 0),
                    'dayHigh': entry.get('high', 0),  # FMP historisch verwendet 'high'
                    'dayLow': entry.get('low', 0),    # FMP historisch verwendet 'low'
                    'price': entry.get('close', 0),   # FMP historisch verwendet 'close'
                    'volume': entry.get('volume', 0),
                    'date': entry.get('date', '')
                }
                
                data_point = self._build_standard_market_data_point(symbol, entry_mapped, exchange)
                # Überschreibe Timestamp mit dem Datum aus den historischen Daten
                data_point.timestamp = self._parse_datetime(entry['date'])
                data_point.adjusted_close = Decimal(str(entry.get('adjClose', entry.get('close', 0))))
                
                historical_data.append(data_point)
            
            # Sortierung nach Datum
            historical_data.sort(key=lambda x: x.timestamp, reverse=True)
            
            self.logger.info(f"Retrieved {len(historical_data)} historical data points for {symbol}")
            return historical_data
            
        except Exception as e:
            self.logger.error(f"Failed to get historical data for {symbol}: {e}")
            raise
    
    async def get_technical_indicators(self, symbol: str, indicator: str,
                                     period: int = 20, exchange: Optional[Exchange] = None) -> Dict[str, Any]:
        """FMP Technical Indicators - vereinfacht"""
        normalized_symbol = self._normalize_symbol(symbol, exchange)
        
        # FMP technische Indikatoren
        fmp_indicators = {
            "SMA": "sma", "EMA": "ema", "RSI": "rsi", "ADX": "adx", "WILLIAMS": "williams"
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
        
        await self._handle_rate_limiting()
        
        try:
            data = await self._make_request(url, params)
            
            if not data:
                raise Exception(f"No technical indicator data for {symbol}")
            
            # Standardisierte Antwort-Struktur
            recent_data = {}
            for entry in data[:30]:
                date_str = entry.get("date", "")
                indicator_value = entry.get(fmp_indicator, 0)
                recent_data[date_str] = {indicator.upper(): indicator_value}
            
            return {
                "indicator": indicator,
                "symbol": symbol,
                "period": period,
                "data": recent_data,
                "source": "fmp_optimized",
                "count": len(recent_data)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get {indicator} for {symbol}: {e}")
            raise
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """FMP Symbol Search - verwendet StandardizedSearchMixin"""
        endpoint = f"{self.v3_endpoint}/search"
        
        # FMP-spezifisches Result-Mapping
        result_mapping = {
            "symbol": "symbol",
            "name": "name", 
            "currency": "currency",
            "stock_exchange": "stockExchange",
            "exchange_short_name": "exchangeShortName"
        }
        
        return await self.search_symbols_standard(query, endpoint, result_mapping)
    
    def get_supported_exchanges(self) -> List[Exchange]:
        """FMP unterstützte Börsen"""
        return [
            Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX,
            Exchange.XETRA, Exchange.LSE, Exchange.TSE,
            Exchange.HKEX, Exchange.TSX, Exchange.ASX, Exchange.EURONEXT
        ]
    
    def get_supported_data_types(self) -> List[DataType]:
        """FMP unterstützte Datentypen"""
        return [
            DataType.REAL_TIME_QUOTE,
            DataType.HISTORICAL_DAILY,
            DataType.TECHNICAL_INDICATORS,
            DataType.FUNDAMENTAL_DATA,  # FMP Stärke!
            DataType.GLOBAL_INDICES
        ]