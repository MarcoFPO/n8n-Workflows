"""
API Gateway Connector - Frontend-Domain
Kommunikation mit anderen Domains über API-Gateway
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class APIGatewayConnector:
    """Connector für API-Gateway Communication"""
    
    def __init__(self, gateway_base_url: str = "http://10.1.1.174"):
        self.gateway_base_url = gateway_base_url
        self.session = None
        self.logger = logger
        
    async def _get_session(self):
        """HTTP Session erstellen"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(verify_ssl=False)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        return self.session
    
    async def get_predictions_data(self, timeframe: str = "1M") -> Dict[str, Any]:
        """Predictions-Daten von Data-Ingestion Domain abrufen"""
        try:
            session = await self._get_session()
            
            # Via bestehende API (Integration Bridge)
            url = f"{self.gateway_base_url}:8084/api/predictions/{timeframe}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info(f"✅ Predictions data loaded: {timeframe}")
                    return data
                else:
                    self.logger.error(f"❌ Predictions API error: {response.status}")
                    return self._get_fallback_predictions(timeframe)
                    
        except Exception as e:
            self.logger.error(f"❌ Predictions API request failed: {e}")
            return self._get_fallback_predictions(timeframe)
    
    async def get_monitoring_metrics(self) -> Dict[str, Any]:
        """System-Metriken von Monitoring Domain abrufen"""
        try:
            session = await self._get_session()
            
            url = f"{self.gateway_base_url}:8083/metrics/overview"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info("✅ Monitoring metrics loaded")
                    return data
                else:
                    return self._get_fallback_metrics()
                    
        except Exception as e:
            self.logger.error(f"❌ Monitoring API request failed: {e}")
            return self._get_fallback_metrics()
    
    async def get_event_bus_status(self) -> Dict[str, Any]:
        """Event-Bus Status abrufen"""
        try:
            session = await self._get_session()
            
            url = f"{self.gateway_base_url}:8081/health"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info("✅ Event-Bus status loaded")
                    return data
                else:
                    return {"status": "unavailable", "message": f"HTTP {response.status}"}
                    
        except Exception as e:
            self.logger.error(f"❌ Event-Bus API request failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_fallback_predictions(self, timeframe: str) -> Dict[str, Any]:
        """Fallback Predictions-Daten"""
        
        # Timeframe-spezifische Anpassungen
        base_return = 15.0
        if timeframe == "7D":
            multiplier = 0.2
        elif timeframe == "1M":
            multiplier = 0.5
        elif timeframe == "3M":
            multiplier = 1.0
        elif timeframe == "6M":
            multiplier = 1.8
        elif timeframe == "1Y":
            multiplier = 3.5
        else:
            multiplier = 1.0
            
        stocks = []
        symbols = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "SAP", "ASML", "BTC", "ETH", "ADBE", "CRM", "NFLX", "AMD"]
        
        for i, symbol in enumerate(symbols):
            predicted_return = base_return * multiplier * (1 - i * 0.08)  # Abnehmend
            current_price = 100 + i * 25  # Basis-Preis
            predicted_price = current_price * (1 + predicted_return / 100)
            
            stocks.append({
                "symbol": symbol,
                "name": f"{symbol} Corporation",
                "current_price": f"€{current_price:.2f}",
                "predicted_price": f"€{predicted_price:.2f}",
                "predicted_return": f"+{predicted_return:.1f}%",
                "sharpe_ratio": f"{1.2 + i * 0.15:.2f}",
                "ml_score": max(60, 95 - i * 2),
                "risk_level": "Niedrig" if i < 3 else "Mittel" if i < 10 else "Hoch"
            })
        
        return {
            "stocks": stocks,
            "timeframe": timeframe,
            "total_analyzed": len(stocks),
            "currency": "EUR",
            "fallback": True
        }
    
    def _get_fallback_metrics(self) -> Dict[str, Any]:
        """Fallback System-Metriken"""
        return {
            "system": {
                "cpu_percent": 12.5,
                "memory_percent": 28.3,
                "disk_percent": 45.2,
                "cpu_count": 4,
                "memory_total_gb": 16.0,
                "memory_used_gb": 4.5,
                "disk_total_gb": 500.0,
                "disk_used_gb": 226.0
            },
            "summary": {
                "active_services": 4,
                "total_services": 6,
                "health_status": "warning"
            },
            "fallback": True
        }
    
    async def cleanup(self):
        """Connector beenden"""
        if self.session:
            await self.session.close()
            self.session = None


# Global API Gateway Instance
_api_gateway_instance = None

def get_api_gateway() -> APIGatewayConnector:
    """Singleton API Gateway Instance"""
    global _api_gateway_instance
    if _api_gateway_instance is None:
        _api_gateway_instance = APIGatewayConnector()
    return _api_gateway_instance