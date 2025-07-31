"""
API Routes - Frontend-Domain
Integration der bestehenden API-Endpoints in die modulare Architektur
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from .api_gateway_connector import get_api_gateway
from .event_bus_connector import get_event_bus

logger = logging.getLogger(__name__)

# Router Setup
api_router = APIRouter(prefix="/api", tags=["frontend-api"])

# Services
api_gateway = get_api_gateway()
event_bus = get_event_bus()


@api_router.get("/predictions/{timeframe}")
async def get_predictions_data(timeframe: str):
    """
    API für dynamische Gewinn-Vorhersagen basierend auf Zeitraum
    Integriert mit Data-Ingestion Domain über API-Gateway
    """
    try:
        logger.info(f"📈 Predictions request: {timeframe}")
        
        # Event: Predictions angefordert
        await event_bus.emit("frontend.api.predictions.requested", {
            "timeframe": timeframe,
            "source": "api_endpoint"
        })
        
        # Daten von API-Gateway abrufen
        data = await api_gateway.get_predictions_data(timeframe)
        
        # Event: Predictions geliefert
        await event_bus.emit("frontend.api.predictions.delivered", {
            "timeframe": timeframe,
            "stock_count": len(data.get("stocks", [])),
            "fallback": data.get("fallback", False)
        })
        
        return data
        
    except Exception as e:
        logger.error(f"❌ Predictions API error: {e}")
        
        # Event: API-Fehler
        await event_bus.emit("frontend.api.error", {
            "endpoint": f"/predictions/{timeframe}",
            "error": str(e)
        })
        
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/monitoring/metrics")
async def get_monitoring_metrics():
    """
    System-Metriken von Monitoring Domain
    """
    try:
        logger.info("🏥 Monitoring metrics request")
        
        # Event: Monitoring angefordert
        await event_bus.emit("frontend.api.monitoring.requested", {
            "source": "api_endpoint"
        })
        
        # Metriken von API-Gateway abrufen
        data = await api_gateway.get_monitoring_metrics()
        
        return data
        
    except Exception as e:
        logger.error(f"❌ Monitoring API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/event-bus/status")
async def get_event_bus_status():
    """
    Event-Bus Status abrufen
    """
    try:
        logger.info("🚌 Event-Bus status request")
        
        # Status von API-Gateway abrufen
        data = await api_gateway.get_event_bus_status()
        
        return data
        
    except Exception as e:
        logger.error(f"❌ Event-Bus API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/events/emit")
async def emit_custom_event(event_data: Dict[str, Any]):
    """
    Manuelles Event über Frontend senden
    """
    try:
        event_type = event_data.get("type", "frontend.custom.event")
        payload = event_data.get("data", {})
        
        logger.info(f"📤 Manual event emit: {event_type}")
        
        # Event senden
        await event_bus.emit(event_type, payload)
        
        return {
            "status": "success",
            "event_type": event_type,
            "timestamp": payload.get("timestamp", "N/A")
        }
        
    except Exception as e:
        logger.error(f"❌ Event emit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/health/full")
async def get_full_health_status():
    """
    Vollständiger Health-Check aller Domains
    """
    try:
        logger.info("🏥 Full health check request")
        
        # Multi-Domain Health Check
        health_status = {
            "frontend_domain": {
                "status": "healthy",
                "event_bus_connected": event_bus.connected
            },
            "monitoring_domain": await api_gateway.get_monitoring_metrics(),
            "event_bus": await api_gateway.get_event_bus_status()
        }
        
        # Predictions API testen
        try:
            predictions_test = await api_gateway.get_predictions_data("1M")
            health_status["data_ingestion"] = {
                "status": "healthy" if not predictions_test.get("fallback") else "fallback",
                "stocks_available": len(predictions_test.get("stocks", []))
            }
        except:
            health_status["data_ingestion"] = {"status": "error"}
        
        return health_status
    
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))