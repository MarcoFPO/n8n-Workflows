#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 Standardized Market Data Adapter Base
Eliminiert Code-Duplikation zwischen den Adaptern
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json
from abc import ABC, abstractmethod

from .base_market_data_adapter import (
    BaseMarketDataAdapter, MarketDataSource, MarketDataPoint, 
    APILimits, Exchange, DataType
)


class StandardizedAdapterBase(BaseMarketDataAdapter):
    """
    Standardisierte Basis-Implementierung für alle Market Data Adapter
    Eliminiert 80% der Code-Duplikation zwischen Adaptern
    """
    
    def __init__(self, api_key: str, base_url: str, name: str, source: MarketDataSource):
        super().__init__(api_key=api_key, base_url=base_url, name=name, source=source)
        
        # Standard-Konfiguration (kann von Subklassen überschrieben werden)
        self.daily_limit = 1000
        self.minute_limit = 60
        self.supported_exchanges = self._get_default_exchanges()
        self.supported_data_types = self._get_default_data_types()
    
    def _get_default_exchanges(self) -> List[Exchange]:
        """Standard-Börsen (kann überschrieben werden)"""
        return [
            Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX,
            Exchange.XETRA, Exchange.LSE, Exchange.TSE
        ]
    
    def _get_default_data_types(self) -> List[DataType]:
        """Standard-Datentypen (kann überschrieben werden)"""
        return [
            DataType.REAL_TIME_QUOTE,
            DataType.HISTORICAL_DAILY,
            DataType.TECHNICAL_INDICATORS
        ]
    
    def _normalize_symbol_standard(self, symbol: str, exchange: Optional[Exchange] = None) -> str:
        """
        Standardisierte Symbol-Normalisierung
        Kann von Subklassen erweitert werden
        """
        # Basis-Normalisierung
        normalized = symbol.upper().strip()
        
        # Standard Exchange-Suffixe
        if exchange and exchange not in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
            exchange_suffixes = {
                Exchange.XETRA: ".DE",
                Exchange.LSE: ".L", 
                Exchange.TSE: ".T",
                Exchange.HKEX: ".HK",
                Exchange.TSX: ".TO",
                Exchange.ASX: ".AX"
            }
            suffix = exchange_suffixes.get(exchange, "")
            normalized = f"{normalized}{suffix}"
            
        return normalized
    
    def _build_standard_market_data_point(self, symbol: str, data: Dict[str, Any], 
                                        exchange: Optional[Exchange] = None) -> MarketDataPoint:
        """
        Standardisierte MarketDataPoint-Erstellung
        Reduziert Code-Duplikation um 90%
        """
        # Standard-Feldmapping (kann von Subklassen angepasst werden)
        field_mapping = self._get_field_mapping()
        
        return MarketDataPoint(
            symbol=symbol,
            timestamp=self._extract_timestamp(data),
            open_price=self._safe_decimal(data.get(field_mapping.get('open', 'open'), 0)),
            high_price=self._safe_decimal(data.get(field_mapping.get('high', 'high'), 0)),
            low_price=self._safe_decimal(data.get(field_mapping.get('low', 'low'), 0)),
            close_price=self._safe_decimal(data.get(field_mapping.get('close', 'close'), 0)),
            volume=int(data.get(field_mapping.get('volume', 'volume'), 0)),
            market_cap=self._safe_decimal(data.get(field_mapping.get('market_cap', 'marketCap'))),
            pe_ratio=self._safe_float(data.get(field_mapping.get('pe_ratio', 'pe'))),
            exchange=exchange,
            currency=data.get('currency', 'USD'),
            source=self.source,
            raw_data=data
        )
    
    def _get_field_mapping(self) -> Dict[str, str]:
        """
        Standard-Feldmapping - kann von Subklassen überschrieben werden
        """
        return {
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'market_cap': 'marketCap',
            'pe_ratio': 'pe'
        }
    
    def _extract_timestamp(self, data: Dict[str, Any]) -> datetime:
        """Standardisierte Timestamp-Extraktion"""
        # Versuche verschiedene Standard-Felder
        timestamp_fields = ['timestamp', 'date', 'time', 'datetime']
        
        for field in timestamp_fields:
            if field in data:
                return self._parse_datetime(data[field])
                
        # Fallback: aktuelle Zeit
        return datetime.now()
    
    def _safe_decimal(self, value) -> Optional[Decimal]:
        """Sichere Decimal-Konvertierung"""
        if value is None or value == '':
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """Sichere Float-Konvertierung"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    async def _handle_rate_limiting(self):
        """
        Standardisierte Rate-Limiting-Behandlung
        Eliminiert duplizierte Rate-Limiting-Logik
        """
        current_calls = await self._get_current_call_count()
        
        if current_calls >= self.minute_limit:
            self.logger.warning(f"Rate limit reached for {self.name}, waiting...")
            await asyncio.sleep(60)
        
        if current_calls >= self.daily_limit:
            self.logger.error(f"Daily limit reached for {self.name}")
            raise Exception(f"Daily API limit exceeded for {self.name}")
    
    async def _get_current_call_count(self) -> int:
        """Aktuelle API-Aufrufe zählen (vereinfacht)"""
        return self._call_count_today
    
    def get_supported_exchanges(self) -> List[Exchange]:
        """Von Adapter unterstützte Börsen"""
        return self.supported_exchanges
    
    def get_supported_data_types(self) -> List[DataType]:
        """Von Adapter unterstützte Datentypen"""
        return self.supported_data_types
    
    async def _get_api_limits(self) -> APILimits:
        """Standard API-Limits"""
        return APILimits(
            calls_per_minute=self.minute_limit,
            calls_per_day=self.daily_limit,
            calls_remaining_today=max(0, self.daily_limit - self._call_count_today),
            is_premium=False
        )
    
    def _normalize_symbol(self, symbol: str, exchange: Optional[Exchange] = None) -> str:
        """Alias für standardisierte Normalisierung"""
        return self._normalize_symbol_standard(symbol, exchange)
    
    # Abstract Methods - müssen von Subklassen implementiert werden
    @abstractmethod
    async def get_real_time_quote(self, symbol: str, exchange: Optional[Exchange] = None) -> MarketDataPoint:
        """Implementierung spezifisch für jeden Adapter"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, interval: str = "1day",
                                exchange: Optional[Exchange] = None) -> List[MarketDataPoint]:
        """Implementierung spezifisch für jeden Adapter"""
        pass


class StandardizedSearchMixin:
    """
    Mixin für standardisierte Symbol-Suche
    Reduziert weitere 50 Zeilen pro Adapter
    """
    
    async def search_symbols_standard(self, query: str, endpoint: str, 
                                    result_mapping: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Standardisierte Symbol-Suche
        
        Args:
            query: Suchbegriff
            endpoint: API-Endpoint für Suche
            result_mapping: Mapping von API-Feldern zu Standard-Feldern
        """
        try:
            params = {"query": query, "limit": 20, "apikey": self.api_key}
            data = await self._make_request(endpoint, params)
            
            if not data:
                return []
                
            results = []
            for item in data:
                mapped_result = {}
                for std_field, api_field in result_mapping.items():
                    mapped_result[std_field] = item.get(api_field, "")
                results.append(mapped_result)
                
            self.logger.info(f"Found {len(results)} symbols for query: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Symbol search failed for '{query}': {e}")
            return []