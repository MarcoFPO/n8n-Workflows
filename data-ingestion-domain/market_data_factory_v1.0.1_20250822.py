"""
🏭 Market Data Factory - Zentrale Initialisierung und Konfiguration
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

import importlib.util
import sys

# Import MarketDataAggregator
base_dir = os.path.dirname(__file__)
aggregator_path = os.path.join(base_dir, 'data_aggregation', 'market_data_aggregator.py')
spec = importlib.util.spec_from_file_location('market_data_aggregator', aggregator_path)
aggregator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aggregator_module)
MarketDataAggregator = aggregator_module.MarketDataAggregator

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

@dataclass
class MarketDataConfig:
    """Konfiguration für Market Data Services"""
    alpha_vantage_api_key: Optional[str] = None
    fmp_api_key: Optional[str] = None
    
    # Cache-Konfiguration
    enable_caching: bool = True
    cache_ttl_minutes: int = 15
    
    # Rate Limiting
    enable_rate_limiting: bool = True
    conservative_limits: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_api_calls: bool = False
    
    # Fallback-Strategien
    enable_fallback: bool = True
    max_retries: int = 3
    
    @classmethod
    def from_environment(cls) -> 'MarketDataConfig':
        """Konfiguration aus Umgebungsvariablen laden"""
        return cls(
            alpha_vantage_api_key=os.getenv('ALPHA_VANTAGE_API_KEY'),
            fmp_api_key=os.getenv('FMP_API_KEY'),
            enable_caching=os.getenv('MARKET_DATA_CACHE', 'true').lower() == 'true',
            cache_ttl_minutes=int(os.getenv('MARKET_DATA_CACHE_TTL', '15')),
            enable_rate_limiting=os.getenv('MARKET_DATA_RATE_LIMITING', 'true').lower() == 'true',
            conservative_limits=os.getenv('MARKET_DATA_CONSERVATIVE_LIMITS', 'true').lower() == 'true',
            log_level=os.getenv('MARKET_DATA_LOG_LEVEL', 'INFO'),
            log_api_calls=os.getenv('MARKET_DATA_LOG_API_CALLS', 'false').lower() == 'true',
            enable_fallback=os.getenv('MARKET_DATA_FALLBACK', 'true').lower() == 'true',
            max_retries=int(os.getenv('MARKET_DATA_MAX_RETRIES', '3'))
        )

class MarketDataFactory:
    """
    🏭 Factory für Market Data Services
    
    Zentrale Stelle für:
    - Service-Initialisierung
    - Konfiguration-Management
    - Dependency Injection
    - Logging-Setup
    """
    
    def __init__(self, config: Optional[MarketDataConfig] = None):
        self.config = config or MarketDataConfig.from_environment()
        self._setup_logging()
        self.logger = logging.getLogger("market_data_factory")
        
    def _setup_logging(self):
        """Logging konfigurieren"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if self.config.log_api_calls:
            # API-Call-Logging aktivieren
            api_logger = logging.getLogger("market_data")
            api_logger.setLevel(logging.DEBUG)
    
    def create_aggregator(self) -> MarketDataAggregator:
        """MarketDataAggregator mit vollständiger Konfiguration erstellen"""
        self.logger.info("Creating MarketDataAggregator with configuration")
        
        # API-Keys validieren
        self._validate_api_keys()
        
        # Aggregator erstellen
        aggregator = MarketDataAggregator(
            alpha_vantage_key=self.config.alpha_vantage_api_key,
            fmp_key=self.config.fmp_api_key
        )
        
        # Cache-Konfiguration anwenden
        if hasattr(aggregator, '_cache_ttl'):
            from datetime import timedelta
            aggregator._cache_ttl = timedelta(minutes=self.config.cache_ttl_minutes)
        
        self.logger.info(f"MarketDataAggregator created with {len(aggregator.adapters)} adapters")
        return aggregator
    
    def create_alpha_vantage_adapter(self) -> Optional[AlphaVantageAdapter]:
        """Alpha Vantage Adapter erstellen"""
        if not self.config.alpha_vantage_api_key:
            self.logger.warning("No Alpha Vantage API key provided")
            return None
            
        self.logger.info("Creating Alpha Vantage adapter")
        return AlphaVantageAdapter(self.config.alpha_vantage_api_key)
    
    def create_yahoo_finance_adapter(self) -> YahooFinanceAdapter:
        """Yahoo Finance Adapter erstellen (immer verfügbar)"""
        self.logger.info("Creating Yahoo Finance adapter")
        return YahooFinanceAdapter()
    
    def create_fmp_adapter(self) -> Optional[FMPAdapter]:
        """FMP Adapter erstellen"""
        if not self.config.fmp_api_key:
            self.logger.warning("No FMP API key provided")
            return None
            
        self.logger.info("Creating FMP adapter")
        return FMPAdapter(self.config.fmp_api_key)
    
    def _validate_api_keys(self):
        """API-Keys validieren"""
        available_sources = []
        
        if self.config.alpha_vantage_api_key:
            available_sources.append("Alpha Vantage")
        else:
            self.logger.warning("Alpha Vantage API key not configured - premium features unavailable")
            
        # Yahoo Finance ist immer verfügbar
        available_sources.append("Yahoo Finance")
        
        if self.config.fmp_api_key:
            available_sources.append("Financial Modeling Prep")
        else:
            self.logger.warning("FMP API key not configured - fundamental data limited")
        
        self.logger.info(f"Available data sources: {', '.join(available_sources)}")
        
        if len(available_sources) == 1:
            self.logger.warning("Only Yahoo Finance available - consider adding API keys for better coverage")
    
    def get_supported_features(self) -> Dict[str, Any]:
        """Unterstützte Features basierend auf Konfiguration zurückgeben"""
        features = {
            "real_time_quotes": True,  # Yahoo Finance always available
            "historical_data": True,   # Yahoo Finance always available
            "global_markets": True,    # Yahoo Finance covers all markets
            "technical_indicators": False,
            "fundamental_data": False,
            "premium_quality": False
        }
        
        if self.config.alpha_vantage_api_key:
            features.update({
                "technical_indicators": True,
                "fundamental_data": True, 
                "premium_quality": True
            })
            
        if self.config.fmp_api_key:
            features.update({
                "fundamental_data": True,
                "financial_statements": True,
                "analyst_estimates": True
            })
            
        return features
    
    async def health_check(self) -> Dict[str, Any]:
        """Gesundheitsstatus aller Services prüfen"""
        health_status = {
            "status": "healthy",
            "services": {},
            "configuration": {
                "caching_enabled": self.config.enable_caching,
                "rate_limiting_enabled": self.config.enable_rate_limiting,
                "fallback_enabled": self.config.enable_fallback
            }
        }
        
        # Aggregator-Status prüfen
        try:
            aggregator = self.create_aggregator()
            async with aggregator:
                adapter_status = await aggregator.get_adapter_status()
                
                for source, status in adapter_status.items():
                    health_status["services"][source.value] = {
                        "healthy": status.is_healthy,
                        "error_count": status.error_count,
                        "last_successful_call": status.last_successful_call.isoformat() if status.last_successful_call else None,
                        "api_limits": {
                            "calls_remaining": status.api_limits.calls_remaining_today if status.api_limits else "unknown",
                            "daily_limit": status.api_limits.calls_per_day if status.api_limits else "unknown"
                        } if status.api_limits else None
                    }
                    
                    if not status.is_healthy:
                        health_status["status"] = "degraded"
                        
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status

# Convenience-Funktionen für einfache Nutzung
def create_market_data_service(alpha_vantage_key: Optional[str] = None,
                             fmp_key: Optional[str] = None) -> MarketDataAggregator:
    """Einfache Erstellung eines MarketDataAggregator"""
    config = MarketDataConfig(
        alpha_vantage_api_key=alpha_vantage_key,
        fmp_api_key=fmp_key
    )
    factory = MarketDataFactory(config)
    return factory.create_aggregator()

def create_market_data_service_from_env() -> MarketDataAggregator:
    """MarketDataAggregator aus Umgebungsvariablen erstellen"""
    factory = MarketDataFactory()
    return factory.create_aggregator()