#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""  
🔄 Unified Fallback Provider - Zentrales Fallback-System
Ersetzt alle duplizierten Fallback-Implementierungen
"""

from typing import Dict, List, Any
from datetime import datetime


class UnifiedFallbackProvider:
    """Zentraler Fallback-Provider für alle Services"""
    
    @staticmethod
    def get_stock_data(limit: int = 15) -> Dict[str, Any]:
        """Einheitliche Fallback-Aktienmarktdaten"""
        stocks = [
            {
                "symbol": "NVDA", "name": "NVIDIA Corporation",
                "current_price": 875.32, "change": 23.45, "change_percent": 2.75,
                "currency": "USD", "market": "NASDAQ", "sector": "Technology"
            },
            {
                "symbol": "AAPL", "name": "Apple Inc.",
                "current_price": 193.42, "change": 1.87, "change_percent": 0.98,
                "currency": "USD", "market": "NASDAQ", "sector": "Technology"
            },
            {
                "symbol": "MSFT", "name": "Microsoft Corporation",
                "current_price": 421.18, "change": 5.23, "change_percent": 1.26,
                "currency": "USD", "market": "NASDAQ", "sector": "Technology"
            },
            {
                "symbol": "GOOGL", "name": "Alphabet Inc.",
                "current_price": 2598.35, "change": -12.45, "change_percent": -0.48,
                "currency": "USD", "market": "NASDAQ", "sector": "Technology"
            },
            {
                "symbol": "AMZN", "name": "Amazon.com Inc.",
                "current_price": 143.22, "change": -2.34, "change_percent": -1.61,
                "currency": "USD", "market": "NASDAQ", "sector": "E-Commerce"
            },
            {
                "symbol": "TSLA", "name": "Tesla Inc.",
                "current_price": 228.07, "change": 12.45, "change_percent": 5.77,
                "currency": "USD", "market": "NASDAQ", "sector": "Automotive"
            },
            {
                "symbol": "META", "name": "Meta Platforms Inc.",
                "current_price": 489.33, "change": 15.67, "change_percent": 3.31,
                "currency": "USD", "market": "NASDAQ", "sector": "Social Media"
            },
            {
                "symbol": "SAP", "name": "SAP SE",
                "current_price": 138.20, "change": 2.15, "change_percent": 1.58,
                "currency": "EUR", "market": "XETRA", "sector": "Technology"
            }
        ]
        
        return {
            "stocks": stocks[:limit],
            "status": "success",
            "data_source": "Unified Fallback System",
            "timestamp": datetime.now().isoformat(),
            "total_count": min(limit, len(stocks))
        }
    
    @staticmethod
    def get_predictions(timeframe: str = "1M") -> List[Dict[str, Any]]:
        """Einheitliche Fallback-Vorhersagedaten"""
        # Timeframe-basierte Multipliers
        multipliers = {
            "7D": 1.02, "1M": 1.07, "3M": 1.15, 
            "6M": 1.25, "1Y": 1.45
        }
        
        multiplier = multipliers.get(timeframe, 1.1)
        base_stocks = UnifiedFallbackProvider.get_stock_data(15)["stocks"]
        predictions = []
        
        for i, stock in enumerate(base_stocks):
            current_price = stock["current_price"]
            predicted_price = current_price * multiplier
            profit_potential = ((predicted_price - current_price) / current_price) * 100
            
            predictions.append({
                "symbol": stock["symbol"],
                "name": stock["name"],
                "current_price": f"€{current_price:.2f}",
                "predicted_price": f"€{predicted_price:.2f}",
                "predicted_return": f"+{profit_potential:.1f}%",
                "sharpe_ratio": f"{1.2 + i * 0.1:.2f}",
                "ml_score": max(60, 95 - i * 2),
                "risk_level": "Niedrig" if i < 3 else "Mittel" if i < 10 else "Hoch",
                "timeframe": timeframe,
                "currency": "EUR",
                "sector": stock["sector"],
                "market": stock["market"]
            })
        
        # Nach Gewinn-Potenzial sortieren
        predictions.sort(key=lambda x: float(x["predicted_return"].strip("+%")), reverse=True)
        return predictions
    
    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """Einheitliche Fallback-Metriken"""
        return {
            "summary": {
                "active_services": 4,
                "total_services": 6,
                "cpu_usage": 12.5,
                "memory_usage": 28.3,
                "disk_usage": 45.7
            },
            "services": {
                "event_bus": {"status": "active", "uptime": "2d 14h"},
                "core": {"status": "active", "uptime": "2d 14h"},
                "broker": {"status": "active", "uptime": "1d 8h"},
                "monitoring": {"status": "active", "uptime": "2d 14h"},
                "data_ingestion": {"status": "inactive", "uptime": "0h"},
                "ml_engine": {"status": "inactive", "uptime": "0h"}
            },
            "system": {
                "os": "Linux",
                "python_version": "3.11.2",
                "memory_total": "16GB",
                "memory_available": "11.5GB"
            },
            "timestamp": datetime.now().isoformat(),
            "fallback": True
        }


# Global Instance
fallback_provider = UnifiedFallbackProvider()

# Convenience Functions
def get_fallback_stock_data(limit: int = 15) -> Dict[str, Any]:
    return fallback_provider.get_stock_data(limit)

def get_fallback_predictions(timeframe: str = "1M") -> List[Dict[str, Any]]:
    return fallback_provider.get_predictions(timeframe)

def get_fallback_metrics() -> Dict[str, Any]:
    return fallback_provider.get_metrics()