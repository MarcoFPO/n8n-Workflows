"""
🎨 Frontend Integration für Market Data Services
Integration in das bestehende FastAPI Frontend
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
import logging

import importlib.util
import sys
import os

# Import market_data_factory
try:
    from market_data_factory import create_market_data_service_from_env
except ImportError:
    # Import using absolute path
    base_dir = os.path.dirname(__file__)
    factory_path = os.path.join(base_dir, 'market_data_factory.py')
    spec = importlib.util.spec_from_file_location('market_data_factory', factory_path)
    factory_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(factory_module)
    create_market_data_service_from_env = factory_module.create_market_data_service_from_env

# Import from data_aggregation
try:
    from data_aggregation.market_data_aggregator import AggregationResult
except ImportError:
    # Import using absolute path
    aggregator_path = os.path.join(base_dir, 'data_aggregation', 'market_data_aggregator.py')
    spec = importlib.util.spec_from_file_location('market_data_aggregator', aggregator_path)
    aggregator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aggregator_module)
    AggregationResult = aggregator_module.AggregationResult

# Import from source_adapters  
try:
    from source_adapters.base_market_data_adapter import Exchange, MarketDataPoint
except ImportError:
    # Import using absolute path
    base_adapter_path = os.path.join(base_dir, 'source_adapters', 'base_market_data_adapter.py')
    spec = importlib.util.spec_from_file_location('base_market_data_adapter', base_adapter_path)
    base_adapter_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base_adapter_module)
    Exchange = base_adapter_module.Exchange
    MarketDataPoint = base_adapter_module.MarketDataPoint

class MarketDataFrontendService:
    """
    🎨 Frontend Service für Market Data Integration
    
    Stellt eine einfache API für das Frontend bereit und
    konvertiert die Market Data in Frontend-kompatible Formate
    """
    
    def __init__(self):
        self.logger = logging.getLogger("market_data_frontend")
        self.aggregator = None
        
    async def initialize(self):
        """Service initialisieren"""
        try:
            self.aggregator = create_market_data_service_from_env()
            await self.aggregator.__aenter__()
            self.logger.info("Market Data Frontend Service initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Market Data Service: {e}")
            raise
    
    async def cleanup(self):
        """Service cleanup"""
        if self.aggregator:
            await self.aggregator.__aexit__(None, None, None)
    
    async def get_global_stock_data(self, limit: int = 100) -> Dict[str, Any]:
        """
        Globale Aktienanalyse für Frontend-Integration
        Ersetzt die aktuellen 5 Beispiel-Aktien mit echten weltweiten Daten
        """
        if not self.aggregator:
            await self.initialize()
        
        # Top-Aktien aus verschiedenen globalen Märkten
        global_stocks = [
            # US Tech (NASDAQ/NYSE)
            {"symbol": "NVDA", "exchange": None, "region": "US", "sector": "Technology"},
            {"symbol": "AAPL", "exchange": None, "region": "US", "sector": "Technology"},
            {"symbol": "GOOGL", "exchange": None, "region": "US", "sector": "Technology"},
            {"symbol": "MSFT", "exchange": None, "region": "US", "sector": "Technology"},
            {"symbol": "TSLA", "exchange": None, "region": "US", "sector": "Automotive"},
            
            # Deutsche Aktien (XETRA)
            {"symbol": "SAP", "exchange": Exchange.XETRA, "region": "Germany", "sector": "Technology"},
            {"symbol": "ASML", "exchange": Exchange.XETRA, "region": "Germany", "sector": "Technology"},
            {"symbol": "BMW", "exchange": Exchange.XETRA, "region": "Germany", "sector": "Automotive"},
            
            # UK Aktien (LSE)
            {"symbol": "SHEL", "exchange": Exchange.LSE, "region": "UK", "sector": "Energy"},
            {"symbol": "AZN", "exchange": Exchange.LSE, "region": "UK", "sector": "Healthcare"},
            
            # Japan Aktien (TSE)
            {"symbol": "7203", "exchange": Exchange.TSE, "region": "Japan", "sector": "Automotive"}, # Toyota
            {"symbol": "6758", "exchange": Exchange.TSE, "region": "Japan", "sector": "Technology"}, # Sony
            
            # Hong Kong (HKEX)
            {"symbol": "0700", "exchange": Exchange.HKEX, "region": "Hong Kong", "sector": "Technology"}, # Tencent
            
            # Kanada (TSX)
            {"symbol": "SHOP", "exchange": Exchange.TSX, "region": "Canada", "sector": "E-commerce"},
            
            # Australien (ASX)  
            {"symbol": "CSL", "exchange": Exchange.ASX, "region": "Australia", "sector": "Healthcare"}
        ]
        
        # Parallel alle Kursdaten abrufen (limitiert auf gewünschte Anzahl)
        import asyncio
        tasks = []
        
        for stock in global_stocks[:limit]:
            task = self._get_stock_with_prediction(
                stock["symbol"], 
                stock.get("exchange"), 
                stock["region"], 
                stock["sector"]
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Erfolgreiche Ergebnisse sammeln
        valid_stocks = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"Failed to get data for {global_stocks[i]['symbol']}: {result}")
                continue
                
            if result:
                valid_stocks.append(result)
        
        # Nach ML-Score sortieren (höchste zuerst)
        valid_stocks.sort(key=lambda x: x.get("ml_score", 0), reverse=True)
        
        self.logger.info(f"Retrieved data for {len(valid_stocks)} global stocks")
        
        return {
            "total_stocks_analyzed": len(valid_stocks),
            "global_coverage": {
                "regions": len(set(stock.get("region") for stock in valid_stocks)),
                "exchanges": len(set(stock.get("exchange") for stock in valid_stocks if stock.get("exchange"))),
                "sectors": len(set(stock.get("sector") for stock in valid_stocks))
            },
            "top_performers": valid_stocks[:10],  # Top 10
            "all_stocks": valid_stocks,
            "last_updated": datetime.now().isoformat(),
            "metadata": {
                "data_sources": ["Alpha Vantage", "Yahoo Finance", "Financial Modeling Prep"],
                "includes_global_markets": True,
                "real_time_data": True
            }
        }
    
    async def _get_stock_with_prediction(self, symbol: str, exchange: Optional[Exchange], 
                                       region: str, sector: str) -> Optional[Dict[str, Any]]:
        """Einzelne Aktie mit Vorhersage-Daten abrufen"""
        try:
            # Aktuelle Kursdaten abrufen
            quote_result = await self.aggregator.get_real_time_quote(symbol, exchange)
            
            if not quote_result.success:
                return None
            
            quote: MarketDataPoint = quote_result.data
            
            # Historische Daten für Trend-Berechnung (letzte 30 Tage)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            historical_result = await self.aggregator.get_historical_data(
                symbol, start_date, end_date, "1day", exchange
            )
            
            # Performance-Berechnung
            performance_30d = 0.0
            volatility = 0.0
            
            if historical_result.success and len(historical_result.data) >= 2:
                historical_data = historical_result.data
                current_price = float(quote.close_price)
                price_30d_ago = float(historical_data[-1].close_price)  # Ältester Wert
                
                performance_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
                
                # Einfache Volatilitäts-Berechnung
                prices = [float(d.close_price) for d in historical_data]
                if len(prices) > 1:
                    import statistics
                    volatility = statistics.stdev(prices) / statistics.mean(prices) * 100
            
            # ML-Score simulieren (basierend auf verschiedenen Faktoren)
            ml_score = self._calculate_ml_score(quote, performance_30d, volatility, sector)
            
            # Risiko-Bewertung
            risk_level = "Niedrig"
            if volatility > 30:
                risk_level = "Hoch"
            elif volatility > 15:
                risk_level = "Mittel"
            
            # Prognose-Preis (einfache Simulation basierend auf Trend)
            current_price = float(quote.close_price)
            predicted_price = current_price * (1 + (performance_30d / 100) * 0.5)  # Gedämpfte Prognose
            predicted_return = ((predicted_price - current_price) / current_price) * 100
            
            return {
                "symbol": symbol,
                "name": self._get_company_name(symbol, exchange, region),
                "current_price": f"${current_price:.2f}",
                "predicted_price": f"${predicted_price:.2f}",
                "predicted_return": f"{predicted_return:+.1f}%",
                "sharpe_ratio": round(performance_30d / max(volatility, 1) if volatility > 0 else 0, 2),
                "ml_score": ml_score,
                "risk_level": risk_level,
                "volume": int(quote.volume) if quote.volume else 0,
                "market_cap": int(quote.market_cap) if quote.market_cap else None,
                "exchange": exchange.value if exchange else "NASDAQ",
                "currency": quote.currency,
                "region": region,
                "sector": sector,
                "performance_30d": f"{performance_30d:+.1f}%",
                "volatility": f"{volatility:.1f}%",
                "last_updated": quote.timestamp.isoformat(),
                "data_source": quote_result.primary_source.value,
                "data_quality": round(quote_result.data_quality_score, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting stock data for {symbol}: {e}")
            return None
    
    def _calculate_ml_score(self, quote: MarketDataPoint, performance_30d: float, 
                          volatility: float, sector: str) -> float:
        """ML-Score simulieren basierend auf verschiedenen Faktoren"""
        base_score = 50.0
        
        # Performance-Faktor
        if performance_30d > 10:
            base_score += 20
        elif performance_30d > 5:
            base_score += 10
        elif performance_30d < -10:
            base_score -= 20
        elif performance_30d < -5:
            base_score -= 10
        
        # Volatilitäts-Faktor (niedrige Volatilität = besser)
        if volatility < 10:
            base_score += 15
        elif volatility < 20:
            base_score += 5
        elif volatility > 40:
            base_score -= 15
        elif volatility > 30:
            base_score -= 10
        
        # Sektor-Faktor
        sector_multipliers = {
            "Technology": 1.1,
            "Healthcare": 1.05,
            "Energy": 0.95,
            "Automotive": 1.0,
            "E-commerce": 1.1
        }
        base_score *= sector_multipliers.get(sector, 1.0)
        
        # Volume-Faktor (hohe Liquidität = besser)
        if quote.volume and quote.volume > 1000000:
            base_score += 5
        elif quote.volume and quote.volume < 100000:
            base_score -= 5
        
        # PE-Ratio Faktor (wenn verfügbar)
        if quote.pe_ratio:
            if 10 <= quote.pe_ratio <= 25:
                base_score += 10  # Gesunde PE-Ratio
            elif quote.pe_ratio > 50:
                base_score -= 10  # Überbewertet
        
        return max(0, min(100, round(base_score, 1)))
    
    def _get_company_name(self, symbol: str, exchange: Optional[Exchange], region: str) -> str:
        """Firmenname basierend auf Symbol und Region bestimmen"""
        company_names = {
            # US
            "NVDA": "NVIDIA Corp",
            "AAPL": "Apple Inc", 
            "GOOGL": "Alphabet Inc",
            "MSFT": "Microsoft Corp",
            "TSLA": "Tesla Inc",
            
            # Deutschland
            "SAP": "SAP SE",
            "ASML": "ASML Holding",
            "BMW": "Bayerische Motoren Werke AG",
            
            # UK
            "SHEL": "Shell plc",
            "AZN": "AstraZeneca PLC",
            
            # Japan
            "7203": "Toyota Motor Corp",
            "6758": "Sony Group Corp",
            
            # Hong Kong
            "0700": "Tencent Holdings Ltd",
            
            # Kanada
            "SHOP": "Shopify Inc",
            
            # Australien
            "CSL": "CSL Limited"
        }
        
        return company_names.get(symbol, f"{symbol} ({region})")
    
    async def get_chart_data(self, symbols: List[str], days: int = 180) -> Dict[str, Any]:
        """Chart-Daten für Frontend generieren"""
        if not self.aggregator:
            await self.initialize()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        chart_data = {
            "labels": [],
            "datasets": []
        }
        
        # Daten für jeden Symbol abrufen
        for i, symbol in enumerate(symbols[:5]):  # Max 5 Symbole für Performance
            try:
                result = await self.aggregator.get_historical_data(
                    symbol, start_date, end_date, "1day"
                )
                
                if result.success and result.data:
                    historical_data = result.data
                    historical_data.sort(key=lambda x: x.timestamp)  # Chronologisch sortieren
                    
                    # Labels nur beim ersten Symbol setzen
                    if i == 0:
                        chart_data["labels"] = [
                            d.timestamp.strftime("%d.%m") for d in historical_data
                        ]
                    
                    # Dataset für diesen Symbol
                    colors = ["#10B981", "#3B82F6", "#EF4444", "#F59E0B", "#8B5CF6"]
                    dataset = {
                        "label": f"{symbol} Kursverlauf ($)",
                        "data": [float(d.close_price) for d in historical_data],
                        "borderColor": colors[i % len(colors)],
                        "backgroundColor": f"{colors[i % len(colors)]}1A",  # 10% opacity
                        "tension": 0.4,
                        "borderWidth": 3,
                        "pointRadius": 2
                    }
                    
                    chart_data["datasets"].append(dataset)
                    
            except Exception as e:
                self.logger.error(f"Failed to get chart data for {symbol}: {e}")
                continue
        
        return chart_data

# Global instance für Frontend-Integration
market_data_service = MarketDataFrontendService()