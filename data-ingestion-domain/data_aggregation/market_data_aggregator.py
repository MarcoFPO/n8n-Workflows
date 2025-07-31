"""
🌍 Multi-Source Market Data Aggregator
Intelligente Aggregation von Alpha Vantage, Yahoo Finance & FMP mit Fallback-Strategien
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from decimal import Decimal

import importlib.util
import os

# Import base adapter using absolute path
base_dir = os.path.dirname(os.path.dirname(__file__))
base_adapter_path = os.path.join(base_dir, 'source_adapters', 'base_market_data_adapter.py')
spec = importlib.util.spec_from_file_location('base_market_data_adapter', base_adapter_path)
base_adapter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_adapter_module)
BaseMarketDataAdapter = base_adapter_module.BaseMarketDataAdapter
MarketDataSource = base_adapter_module.MarketDataSource
MarketDataPoint = base_adapter_module.MarketDataPoint
APILimits = base_adapter_module.APILimits
Exchange = base_adapter_module.Exchange
DataType = base_adapter_module.DataType
AdapterStatus = base_adapter_module.AdapterStatus

# Import AlphaVantageAdapter
alpha_path = os.path.join(base_dir, 'source_adapters', 'alpha_vantage_adapter', 'alpha_vantage_adapter.py')
spec = importlib.util.spec_from_file_location('alpha_vantage_adapter', alpha_path)
alpha_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alpha_module)
AlphaVantageAdapter = alpha_module.AlphaVantageAdapter

# Import YahooFinanceAdapter
yahoo_path = os.path.join(base_dir, 'source_adapters', 'yahoo_finance_adapter', 'yahoo_finance_adapter.py')
spec = importlib.util.spec_from_file_location('yahoo_finance_adapter', yahoo_path)
yahoo_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yahoo_module)
YahooFinanceAdapter = yahoo_module.YahooFinanceAdapter

# Import FMPAdapter
fmp_path = os.path.join(base_dir, 'source_adapters', 'fmp_adapter', 'fmp_adapter.py')
spec = importlib.util.spec_from_file_location('fmp_adapter', fmp_path)
fmp_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fmp_module)
FMPAdapter = fmp_module.FMPAdapter

class DataPriority(Enum):
    """Priorität der Datenquellen für verschiedene Anfragen"""
    REAL_TIME_QUOTES = "real_time_quotes"
    HISTORICAL_DATA = "historical_data"  
    TECHNICAL_INDICATORS = "technical_indicators"
    FUNDAMENTAL_DATA = "fundamental_data"
    GLOBAL_COVERAGE = "global_coverage"

@dataclass
class AggregationResult:
    """Ergebnis einer Multi-Source-Aggregation"""
    success: bool
    data: Any
    primary_source: MarketDataSource
    fallback_sources_used: List[MarketDataSource] = field(default_factory=list)
    errors: Dict[MarketDataSource, str] = field(default_factory=dict)
    response_time_ms: float = 0.0
    data_quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SourcePriorityConfig:
    """Konfiguration der Quellen-Prioritäten für verschiedene Anfrage-Typen"""
    real_time_quotes: List[MarketDataSource] = field(default_factory=lambda: [
        MarketDataSource.ALPHA_VANTAGE,  # NASDAQ-Partner, hohe Qualität
        MarketDataSource.YAHOO_FINANCE,  # Schnell, global
        MarketDataSource.FMP            # Backup
    ])
    
    historical_data: List[MarketDataSource] = field(default_factory=lambda: [
        MarketDataSource.YAHOO_FINANCE,  # Beste globale Abdeckung
        MarketDataSource.ALPHA_VANTAGE,  # Premium Qualität  
        MarketDataSource.FMP            # Fundamentals
    ])
    
    technical_indicators: List[MarketDataSource] = field(default_factory=lambda: [
        MarketDataSource.ALPHA_VANTAGE,  # 50+ Indikatoren
        MarketDataSource.FMP,           # Einige Indikatoren
        MarketDataSource.YAHOO_FINANCE  # Client-side berechnet
    ])
    
    fundamental_data: List[MarketDataSource] = field(default_factory=lambda: [
        MarketDataSource.FMP,           # Spezialist für Fundamentals
        MarketDataSource.ALPHA_VANTAGE, # Company Overview
        MarketDataSource.YAHOO_FINANCE  # Basis-Fundamentals
    ])
    
    global_markets: List[MarketDataSource] = field(default_factory=lambda: [
        MarketDataSource.YAHOO_FINANCE,  # Beste globale Abdeckung
        MarketDataSource.ALPHA_VANTAGE,  # Internationale Märkte
        MarketDataSource.FMP            # 90+ Börsen
    ])

class MarketDataAggregator:
    """
    🎯 Intelligenter Multi-Source Market Data Aggregator
    
    Features:
    - Automatisches Fallback zwischen Quellen
    - Load Balancing basierend auf API-Limits
    - Datenqualitäts-Scoring
    - Cache-Integration
    - Error Recovery
    - Performance-Optimierung
    """
    
    def __init__(self, alpha_vantage_key: Optional[str] = None, 
                 fmp_key: Optional[str] = None):
        self.logger = logging.getLogger("market_data_aggregator")
        
        # Adapter initialisieren
        self.adapters: Dict[MarketDataSource, BaseMarketDataAdapter] = {}
        
        if alpha_vantage_key:
            self.adapters[MarketDataSource.ALPHA_VANTAGE] = AlphaVantageAdapter(alpha_vantage_key)
            
        # Yahoo Finance ist immer verfügbar (kostenlos)
        self.adapters[MarketDataSource.YAHOO_FINANCE] = YahooFinanceAdapter()
        
        if fmp_key:
            self.adapters[MarketDataSource.FMP] = FMPAdapter(fmp_key)
        
        # Prioritäts-Konfiguration
        self.priority_config = SourcePriorityConfig()
        
        # Adapter-Status tracking
        self.adapter_status: Dict[MarketDataSource, AdapterStatus] = {}
        
        # Performance-Metriken
        self.performance_metrics: Dict[MarketDataSource, Dict[str, float]] = {}
        
        # Cache (vereinfacht - in Produktion würde Redis/Memcached verwendet)
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=15)  # 15 Minuten Cache
        
        self.logger.info(f"Initialized with {len(self.adapters)} adapters: {list(self.adapters.keys())}")
        
    async def __aenter__(self):
        """Async Context Manager Entry"""
        for adapter in self.adapters.values():
            await adapter.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async Context Manager Exit"""
        for adapter in self.adapters.values():
            await adapter.__aexit__(exc_type, exc_val, exc_tb)
    
    async def get_real_time_quote(self, symbol: str, exchange: Optional[Exchange] = None) -> AggregationResult:
        """Aktuelle Kursdaten mit Multi-Source-Fallback"""
        start_time = datetime.now()
        cache_key = f"quote_{symbol}_{exchange}"
        
        # Cache prüfen
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return AggregationResult(
                success=True,
                data=cached_result,
                primary_source=MarketDataSource.YAHOO_FINANCE,  # Cache-Marker
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                metadata={"from_cache": True}
            )
        
        # Source-Priorität für Real-Time Quotes
        sources = self._get_priority_sources(DataPriority.REAL_TIME_QUOTES, exchange)
        
        errors = {}
        fallback_sources = []
        
        for source in sources:
            if source not in self.adapters:
                continue
                
            try:
                adapter = self.adapters[source]
                
                # API-Limits prüfen
                if not await self._check_api_limits(adapter):
                    self.logger.warning(f"API limits reached for {source}, trying next source")
                    errors[source] = "API limits reached"
                    continue
                
                quote = await adapter.get_real_time_quote(symbol, exchange)
                
                # Cache speichern
                self._save_to_cache(cache_key, quote)
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return AggregationResult(
                    success=True,
                    data=quote,
                    primary_source=source,
                    fallback_sources_used=fallback_sources,
                    errors=errors,
                    response_time_ms=response_time,
                    data_quality_score=self._calculate_data_quality(quote, source),
                    metadata={"from_cache": False}
                )
                
            except Exception as e:
                self.logger.warning(f"Failed to get quote from {source}: {e}")
                errors[source] = str(e)
                fallback_sources.append(source)
                continue
        
        # Alle Quellen fehlgeschlagen
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        return AggregationResult(
            success=False,
            data=None,
            primary_source=sources[0] if sources else MarketDataSource.YAHOO_FINANCE,
            fallback_sources_used=fallback_sources,
            errors=errors,
            response_time_ms=response_time,
            data_quality_score=0.0
        )
    
    async def get_historical_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, interval: str = "1day",
                                exchange: Optional[Exchange] = None) -> AggregationResult:
        """Historische Daten mit Multi-Source-Fallback"""
        start_time = datetime.now()
        
        # Source-Priorität für Historical Data
        sources = self._get_priority_sources(DataPriority.HISTORICAL_DATA, exchange)
        
        errors = {}
        fallback_sources = []
        
        for source in sources:
            if source not in self.adapters:
                continue
                
            try:
                adapter = self.adapters[source]
                
                # API-Limits prüfen
                if not await self._check_api_limits(adapter):
                    self.logger.warning(f"API limits reached for {source}, trying next source")
                    errors[source] = "API limits reached"
                    continue
                
                historical_data = await adapter.get_historical_data(
                    symbol, start_date, end_date, interval, exchange
                )
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return AggregationResult(
                    success=True,
                    data=historical_data,
                    primary_source=source,
                    fallback_sources_used=fallback_sources,
                    errors=errors,
                    response_time_ms=response_time,
                    data_quality_score=self._calculate_historical_data_quality(historical_data, source),
                    metadata={"data_points": len(historical_data), "interval": interval}
                )
                
            except Exception as e:
                self.logger.warning(f"Failed to get historical data from {source}: {e}")
                errors[source] = str(e)
                fallback_sources.append(source)
                continue
        
        # Alle Quellen fehlgeschlagen
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        return AggregationResult(
            success=False,
            data=None,
            primary_source=sources[0] if sources else MarketDataSource.YAHOO_FINANCE,
            fallback_sources_used=fallback_sources,
            errors=errors,
            response_time_ms=response_time,
            data_quality_score=0.0
        )
    
    async def get_technical_indicators(self, symbol: str, indicator: str,
                                     period: int = 20, exchange: Optional[Exchange] = None) -> AggregationResult:
        """Technische Indikatoren mit Multi-Source-Fallback"""
        start_time = datetime.now()
        
        # Source-Priorität für Technical Indicators
        sources = self._get_priority_sources(DataPriority.TECHNICAL_INDICATORS, exchange)
        
        errors = {}
        fallback_sources = []
        
        for source in sources:
            if source not in self.adapters:
                continue
                
            try:
                adapter = self.adapters[source]
                
                # API-Limits prüfen
                if not await self._check_api_limits(adapter):
                    self.logger.warning(f"API limits reached for {source}, trying next source")
                    errors[source] = "API limits reached"
                    continue
                
                tech_data = await adapter.get_technical_indicators(symbol, indicator, period, exchange)
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return AggregationResult(
                    success=True,
                    data=tech_data,
                    primary_source=source,
                    fallback_sources_used=fallback_sources,
                    errors=errors,
                    response_time_ms=response_time,
                    data_quality_score=self._calculate_indicator_quality(tech_data, source),
                    metadata={"indicator": indicator, "period": period}
                )
                
            except Exception as e:
                self.logger.warning(f"Failed to get {indicator} from {source}: {e}")
                errors[source] = str(e)
                fallback_sources.append(source)
                continue
        
        # Alle Quellen fehlgeschlagen
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        return AggregationResult(
            success=False,
            data=None,
            primary_source=sources[0] if sources else MarketDataSource.ALPHA_VANTAGE,
            fallback_sources_used=fallback_sources,
            errors=errors,
            response_time_ms=response_time,
            data_quality_score=0.0
        )
    
    async def search_symbols(self, query: str) -> AggregationResult:
        """Symbol-Suche mit Multi-Source-Aggregation"""
        start_time = datetime.now()
        
        # Alle verfügbaren Quellen parallel abfragen für bessere Ergebnisse
        tasks = []
        for source, adapter in self.adapters.items():
            if await self._check_api_limits(adapter):
                task = self._search_from_source(adapter, source, query)
                tasks.append(task)
        
        if not tasks:
            return AggregationResult(
                success=False,
                data=[],
                primary_source=MarketDataSource.YAHOO_FINANCE,
                errors={"all_sources": "No adapters available or API limits reached"}
            )
        
        # Parallel ausführen
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Ergebnisse aggregieren
        all_symbols = []
        errors = {}
        successful_sources = []
        
        for i, result in enumerate(results):
            source = list(self.adapters.keys())[i]
            
            if isinstance(result, Exception):
                errors[source] = str(result)
            else:
                symbols, error = result
                if error:
                    errors[source] = error
                else:
                    all_symbols.extend(symbols)
                    successful_sources.append(source)
        
        # Duplikate entfernen basierend auf Symbol
        unique_symbols = {}
        for symbol_data in all_symbols:
            symbol = symbol_data.get("symbol", "")
            if symbol and symbol not in unique_symbols:
                unique_symbols[symbol] = symbol_data
        
        final_results = list(unique_symbols.values())
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return AggregationResult(
            success=len(final_results) > 0,
            data=final_results,
            primary_source=successful_sources[0] if successful_sources else MarketDataSource.YAHOO_FINANCE,
            fallback_sources_used=successful_sources[1:] if len(successful_sources) > 1 else [],
            errors=errors,
            response_time_ms=response_time,
            data_quality_score=1.0 if final_results else 0.0,
            metadata={"total_results": len(final_results), "sources_used": len(successful_sources)}
        )
    
    async def get_adapter_status(self) -> Dict[MarketDataSource, AdapterStatus]:
        """Status aller Adapter prüfen"""
        status_tasks = []
        
        for source, adapter in self.adapters.items():
            task = adapter.health_check()
            status_tasks.append((source, task))
        
        results = {}
        for source, task in status_tasks:
            try:
                status = await task
                results[source] = status
                self.adapter_status[source] = status
            except Exception as e:
                self.logger.error(f"Health check failed for {source}: {e}")
                results[source] = AdapterStatus(
                    source=source,
                    is_healthy=False,
                    error_count=999
                )
        
        return results
    
    def _get_priority_sources(self, priority_type: DataPriority, 
                            exchange: Optional[Exchange] = None) -> List[MarketDataSource]:
        """Source-Priorität basierend auf Anfrage-Typ und Börse bestimmen"""
        
        # Basis-Prioritäten
        if priority_type == DataPriority.REAL_TIME_QUOTES:
            sources = self.priority_config.real_time_quotes.copy()
        elif priority_type == DataPriority.HISTORICAL_DATA:
            sources = self.priority_config.historical_data.copy()
        elif priority_type == DataPriority.TECHNICAL_INDICATORS:
            sources = self.priority_config.technical_indicators.copy()
        elif priority_type == DataPriority.FUNDAMENTAL_DATA:
            sources = self.priority_config.fundamental_data.copy()
        else:
            sources = self.priority_config.global_markets.copy()
        
        # Anpassung basierend auf Börse
        if exchange and exchange not in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
            # Für internationale Märkte Yahoo Finance bevorzugen
            sources = [MarketDataSource.YAHOO_FINANCE] + [s for s in sources if s != MarketDataSource.YAHOO_FINANCE]
        
        # Nur verfügbare Adapter zurückgeben
        available_sources = [s for s in sources if s in self.adapters]
        
        # Adapter-Gesundheit berücksichtigen
        healthy_sources = []
        unhealthy_sources = []
        
        for source in available_sources:
            status = self.adapter_status.get(source)
            if status and status.is_healthy:
                healthy_sources.append(source)
            else:
                unhealthy_sources.append(source)
        
        # Gesunde Quellen zuerst, dann ungesunde als Fallback
        return healthy_sources + unhealthy_sources
    
    async def _check_api_limits(self, adapter: BaseMarketDataAdapter) -> bool:
        """API-Limits eines Adapters prüfen"""
        try:
            limits = await adapter._get_api_limits()
            return limits.calls_remaining_today > 0
        except:
            # Bei Fehlern konservativ annehmen, dass Limits OK sind
            return True
    
    async def _search_from_source(self, adapter: BaseMarketDataAdapter, 
                                source: MarketDataSource, query: str) -> Tuple[List[Dict], Optional[str]]:
        """Symbol-Suche von einer einzelnen Quelle"""
        try:
            results = await adapter.search_symbols(query)
            return results, None
        except Exception as e:
            return [], str(e)
    
    def _calculate_data_quality(self, data_point: MarketDataPoint, source: MarketDataSource) -> float:
        """Datenqualitäts-Score berechnen"""
        score = 1.0
        
        # Source-basierte Bewertung
        source_scores = {
            MarketDataSource.ALPHA_VANTAGE: 1.0,  # NASDAQ-Partner
            MarketDataSource.YAHOO_FINANCE: 0.8,  # Inoffiziell aber zuverlässig
            MarketDataSource.FMP: 0.9             # Professionell
        }
        score *= source_scores.get(source, 0.7)
        
        # Daten-Vollständigkeit
        if data_point.volume and data_point.volume > 0:
            score *= 1.0
        else:
            score *= 0.8  # Kein Volume
            
        if data_point.market_cap:
            score *= 1.0
        else:
            score *= 0.9  # Keine Market Cap
            
        return min(score, 1.0)
    
    def _calculate_historical_data_quality(self, data: List[MarketDataPoint], 
                                         source: MarketDataSource) -> float:
        """Qualitäts-Score für historische Daten"""
        if not data:
            return 0.0
            
        base_score = 1.0
        
        # Source-Quality
        source_scores = {
            MarketDataSource.ALPHA_VANTAGE: 1.0,
            MarketDataSource.YAHOO_FINANCE: 0.9,
            MarketDataSource.FMP: 0.95
        }
        base_score *= source_scores.get(source, 0.7)
        
        # Daten-Vollständigkeit
        complete_records = sum(1 for d in data if d.volume and d.volume > 0)
        completeness_ratio = complete_records / len(data)
        base_score *= completeness_ratio
        
        return min(base_score, 1.0)
    
    def _calculate_indicator_quality(self, indicator_data: Dict, source: MarketDataSource) -> float:
        """Qualitäts-Score für technische Indikatoren"""
        base_score = 1.0
        
        # Source-basierte Bewertung für Indikatoren
        source_scores = {
            MarketDataSource.ALPHA_VANTAGE: 1.0,  # Native API-Indikatoren
            MarketDataSource.FMP: 0.9,           # Einige native Indikatoren
            MarketDataSource.YAHOO_FINANCE: 0.7  # Client-side berechnet
        }
        base_score *= source_scores.get(source, 0.5)
        
        # Datenpunkt-Anzahl
        data_points = len(indicator_data.get("data", {}))
        if data_points >= 20:
            base_score *= 1.0
        elif data_points >= 10:
            base_score *= 0.8
        else:
            base_score *= 0.6
            
        return min(base_score, 1.0)
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Daten aus Cache abrufen"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                return data
            else:
                del self._cache[key]
        return None
    
    def _save_to_cache(self, key: str, data: Any):
        """Daten in Cache speichern"""
        self._cache[key] = (data, datetime.now())
        
        # Cache-Größe begrenzen (einfache Implementierung)
        if len(self._cache) > 1000:  # Max 1000 Einträge
            # Älteste Einträge entfernen
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for old_key, _ in sorted_items[:100]:  # 100 älteste entfernen
                del self._cache[old_key]