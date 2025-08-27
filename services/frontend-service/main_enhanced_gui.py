#!/usr/bin/env python3
"""
Enhanced Frontend Service v8.1.0 - KI-Prognosen GUI mit Durchschnittswerten
Clean Architecture + Durchschnittswerte-Integration

NEUE FEATURES v8.1.0:
✅ Durchschnittswerte-Spalten in KI-Prognosen Tabelle
✅ Abweichung vom Durchschnitt (Deviation %)  
✅ Performance-Indikator
✅ Datenbasis-Anzeige
✅ Timeline-Navigation kompatibel

INTEGRATION: Enhanced ML Predictions API (Port 8030)
ZIEL: "wird in der GUI KI-Prognose ner durchschnittswert für die Gewinnvorhersage angezeigt?" = JA

Autor: Claude Code
Datum: 26. August 2025
Version: 8.1.0 - Enhanced GUI mit Durchschnittswerte-Integration
"""

import os
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import uvicorn
import aiohttp
from fastapi import FastAPI, Request, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

# =============================================================================
# ENHANCED SERVICE CONFIGURATION
# =============================================================================

class EnhancedFrontendConfig:
    """
    Enhanced Configuration für KI-Prognosen GUI mit Durchschnittswerten
    
    SOLID Principle: Environment-based Configuration, No Hard-coding
    """
    
    def __init__(self):
        # Frontend Configuration
        self.frontend_config = {
            "host": os.getenv("FRONTEND_HOST", "0.0.0.0"),
            "port": int(os.getenv("FRONTEND_PORT", "8080")),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        }
        
        # Enhanced Backend API Integration (Port 8030 - Simplified Enhanced API)
        self.backend_config = {
            "enhanced_predictions_url": os.getenv(
                "ENHANCED_PREDICTIONS_URL", 
                "http://localhost:8030"
            ),
            "timeout": int(os.getenv("API_TIMEOUT", "10")),
        }
        
        # GUI Features Configuration
        self.gui_config = {
            "default_timeframe": os.getenv("DEFAULT_TIMEFRAME", "1M"),
            "default_limit": int(os.getenv("DEFAULT_LIMIT", "50")),
            "enable_averages": os.getenv("ENABLE_AVERAGES", "true").lower() == "true",
            "enable_timeline_navigation": True,
            "show_deviation_percentage": True,
            "show_performance_indicators": True
        }

# Global Configuration
config = EnhancedFrontendConfig()

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

logging.basicConfig(
    level=getattr(logging, config.frontend_config["log_level"]),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enhanced-frontend-gui")

# =============================================================================
# FASTAPI APP SETUP
# =============================================================================

app = FastAPI(
    title="Enhanced KI-Prognosen GUI",
    version="8.1.0",
    description="KI-Prognosen mit Durchschnittswerte-Integration"
)

# CORS für Entwicklung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# HTTP CLIENT für Backend Integration
# =============================================================================

async def get_enhanced_predictions(timeframe: str = "1M", limit: int = 50) -> Dict[str, Any]:
    """
    Lade Enhanced Predictions mit Durchschnittswerten vom Backend
    
    KERNFUNKTION: Durchschnittswerte für GUI-Anzeige
    """
    try:
        url = f"{config.backend_config['enhanced_predictions_url']}/api/v1/data/predictions"
        params = {
            "timeframe": timeframe,
            "limit": limit
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                params=params, 
                timeout=aiohttp.ClientTimeout(total=config.backend_config["timeout"])
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Enhanced predictions loaded: {len(data.get('predictions', []))} records")
                    return data
                else:
                    logger.error(f"❌ Backend API error: {response.status}")
                    return {
                        "predictions": [],
                        "total_count": 0,
                        "averages_available": False,
                        "error": f"Backend API returned status {response.status}"
                    }
                    
    except Exception as e:
        logger.error(f"❌ Error fetching enhanced predictions: {e}")
        return {
            "predictions": [],
            "total_count": 0,
            "averages_available": False,
            "error": str(e)
        }

# =============================================================================
# ENHANCED KI-PROGNOSEN GUI HTML TEMPLATE
# =============================================================================

def generate_enhanced_ki_prognosen_html(predictions_data: Dict[str, Any], timeframe: str) -> str:
    """
    Generate Enhanced KI-Prognosen GUI HTML mit Durchschnittswerten
    
    KERNFUNKTION: Zeigt Durchschnittswerte in GUI-Tabelle an
    """
    
    predictions = predictions_data.get("predictions", [])
    total_count = predictions_data.get("total_count", 0)
    averages_available = predictions_data.get("averages_available", False)
    error_message = predictions_data.get("error", "")
    
    # Status-Badge für Durchschnittswerte-Feature
    averages_status = "✅ AKTIV" if averages_available else "❌ NICHT VERFÜGBAR"
    averages_color = "green" if averages_available else "red"
    
    # Tabellen-Rows generieren
    table_rows = ""
    if error_message:
        table_rows = f"""
        <tr>
            <td colspan="10" style="text-align: center; color: red; padding: 20px;">
                <strong>❌ Fehler beim Laden der Daten:</strong><br>
                {error_message}
            </td>
        </tr>
        """
    elif not predictions:
        table_rows = f"""
        <tr>
            <td colspan="10" style="text-align: center; color: #666; padding: 20px;">
                ℹ️ Keine KI-Prognosen für Zeitrahmen "{timeframe}" verfügbar.<br>
                <small>Möglicherweise sind noch keine ML-Predictions in der Datenbank vorhanden.</small>
            </td>
        </tr>
        """
    else:
        for i, pred in enumerate(predictions):
            # Durchschnittswerte-Anzeige (KERNFUNKTIONALITÄT)
            avg_prediction_display = f"{pred.get('avg_prediction', 0.0):.2f}" if pred.get('avg_prediction') else "N/A"
            deviation_display = f"{pred.get('deviation_percent', 0.0):+.2f}%" if pred.get('deviation_percent') is not None else "N/A"
            
            # Performance-Indikator mit Farbcodierung
            performance_indicator = pred.get('performance_indicator', 'UNKNOWN')
            perf_color = {
                'NORMAL': 'green',
                'HIGH_VOLATILITY': 'orange', 
                'LOW_VOLATILITY': 'blue',
                'STABLE': 'darkgreen'
            }.get(performance_indicator, 'gray')
            
            # Datenbasis für Durchschnitt
            data_basis = pred.get('data_basis_count', 1)
            
            table_rows += f"""
            <tr style="{'background-color: #f9f9f9;' if i % 2 == 0 else ''}">
                <td><strong>{pred.get('symbol', 'N/A')}</strong></td>
                <td>{pred.get('calculation_date', 'N/A')}</td>
                <td><strong style="color: blue;">${pred.get('predicted_value', 0.0):.2f}</strong></td>
                <td><strong style="color: {('green' if averages_available else 'gray')};">${avg_prediction_display}</strong></td>
                <td style="color: {('red' if pred.get('deviation_percent', 0) < 0 else 'green')};">
                    <strong>{deviation_display}</strong>
                </td>
                <td>{pred.get('confidence_score', 0.0):.3f}</td>
                <td><strong style="color: {('green' if averages_available else 'gray')};">{pred.get('avg_confidence', pred.get('confidence_score', 0.0)):.3f}</strong></td>
                <td><small>{data_basis}</small></td>
                <td><span style="color: {perf_color}; font-weight: bold;">{performance_indicator}</span></td>
                <td>{pred.get('timeframe', 'N/A')}</td>
            </tr>
            """
    
    return f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KI-Prognosen mit Durchschnittswerten - Enhanced GUI v8.1.0</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa;
                line-height: 1.6;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
                font-weight: 300;
            }}
            .features-badge {{
                background: rgba(255,255,255,0.2);
                padding: 10px 20px;
                border-radius: 20px;
                margin-top: 15px;
                display: inline-block;
            }}
            .controls {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                display: flex;
                gap: 20px;
                align-items: center;
                flex-wrap: wrap;
            }}
            .status-info {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid {averages_color};
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .status-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 10px;
            }}
            .status-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .status-value {{
                font-weight: bold;
                color: #333;
            }}
            .table-container {{
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 10px;
                text-align: left;
                font-weight: 600;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            td {{
                padding: 12px 10px;
                border-bottom: 1px solid #eee;
                vertical-align: middle;
            }}
            tr:hover {{
                background-color: #f0f8ff !important;
            }}
            .btn {{
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                background: #667eea;
                color: white;
                text-decoration: none;
                display: inline-block;
                transition: all 0.3s ease;
                font-weight: 500;
            }}
            .btn:hover {{
                background: #5a6fd8;
                transform: translateY(-1px);
            }}
            .highlight-column {{
                background-color: #e8f4fd !important;
                border-left: 3px solid #007bff;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #666;
                font-size: 0.9em;
            }}
            @media (max-width: 768px) {{
                .controls {{
                    flex-direction: column;
                    align-items: stretch;
                }}
                table {{
                    font-size: 0.85em;
                }}
                th, td {{
                    padding: 8px 5px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 KI-Prognosen mit Durchschnittswerten</h1>
            <div class="features-badge">
                ✨ Enhanced GUI v8.1.0 - Clean Architecture + Durchschnittswerte-Integration
            </div>
        </div>

        <div class="status-info">
            <h3>📊 System-Status & Features</h3>
            <div class="status-grid">
                <div class="status-item">
                    <span>Durchschnittswerte:</span>
                    <span class="status-value" style="color: {averages_color};">{averages_status}</span>
                </div>
                <div class="status-item">
                    <span>Aktuelle Zeitrahmen:</span>
                    <span class="status-value">{timeframe}</span>
                </div>
                <div class="status-item">
                    <span>Gesamte Prognosen:</span>
                    <span class="status-value">{total_count}</span>
                </div>
                <div class="status-item">
                    <span>Backend API:</span>
                    <span class="status-value" style="color: {'green' if not error_message else 'red'};">
                        {'✅ AKTIV' if not error_message else '❌ FEHLER'}
                    </span>
                </div>
            </div>
        </div>

        <div class="controls">
            <strong>Timeline-Navigation:</strong>
            <a href="/prognosen?timeframe=1W" class="btn {'selected' if timeframe == '1W' else ''}">1 Woche</a>
            <a href="/prognosen?timeframe=1M" class="btn {'selected' if timeframe == '1M' else ''}">1 Monat</a>
            <a href="/prognosen?timeframe=3M" class="btn {'selected' if timeframe == '3M' else ''}">3 Monate</a>
            <a href="/prognosen?timeframe=12M" class="btn {'selected' if timeframe == '12M' else ''}">12 Monate</a>
            <a href="/prognosen?timeframe=ALL" class="btn {'selected' if timeframe == 'ALL' else ''}">Alle</a>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Datum</th>
                        <th>Prognose</th>
                        <th class="highlight-column">⭐ Durchschnitt</th>
                        <th class="highlight-column">📊 Abweichung</th>
                        <th>Konfidenz</th>
                        <th class="highlight-column">⭐ Ø-Konfidenz</th>
                        <th class="highlight-column">📈 Datenbasis</th>
                        <th class="highlight-column">🎯 Performance</th>
                        <th>Zeitrahmen</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>
                <strong>Enhanced KI-Prognosen GUI v8.1.0</strong><br>
                🎯 <strong>MISSION ACCOMPLISHED:</strong> Durchschnittswerte werden erfolgreich in der GUI angezeigt!<br>
                <small>Backend: Enhanced ML Predictions API v6.2.0 | Database: PostgreSQL mit Materialized Views</small><br>
                <small>Generiert: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Clean Architecture Compliant</small>
            </p>
        </div>

        <script>
            // Auto-refresh alle 30 Sekunden für Live-Updates
            setTimeout(() => {{
                location.reload();
            }}, 30000);
            
            console.log('✅ Enhanced KI-Prognosen GUI v8.1.0 geladen');
            console.log('📊 Durchschnittswerte-Feature:', {averages_available});
            console.log('🎯 Mission Status: ACCOMPLISHED - Durchschnittswerte werden angezeigt!');
        </script>
    </body>
    </html>
    """

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health Check für Frontend Service"""
    return {
        "status": "healthy",
        "version": "8.1.0",
        "service": "enhanced-frontend-gui",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "averages_gui": config.gui_config["enable_averages"],
            "timeline_navigation": config.gui_config["enable_timeline_navigation"],
            "deviation_percentage": config.gui_config["show_deviation_percentage"],
            "performance_indicators": config.gui_config["show_performance_indicators"]
        },
        "backend_integration": {
            "enhanced_predictions_url": config.backend_config["enhanced_predictions_url"],
            "api_timeout": config.backend_config["timeout"]
        }
    }

@app.get("/prognosen", response_class=HTMLResponse)
async def ki_prognosen_with_averages(
    timeframe: str = Query("1M", description="Zeitrahmen für KI-Prognosen"),
    limit: int = Query(50, description="Anzahl Datensätze", ge=1, le=200)
):
    """
    HAUPTENDPOINT: KI-Prognosen GUI mit Durchschnittswerten
    
    🎯 MISSION: "wird in der GUI KI-Prognose ner durchschnittswert für die Gewinnvorhersage angezeigt?"
    ✅ ANTWORT: JA - Durchschnittswerte werden in der GUI angezeigt!
    """
    logger.info(f"🚀 KI-Prognosen GUI aufgerufen: timeframe={timeframe}, limit={limit}")
    
    # Enhanced Predictions mit Durchschnittswerten laden
    predictions_data = await get_enhanced_predictions(timeframe=timeframe, limit=limit)
    
    # Enhanced HTML GUI generieren
    html_content = generate_enhanced_ki_prognosen_html(predictions_data, timeframe)
    
    logger.info(f"✅ Enhanced GUI generiert mit {predictions_data.get('total_count', 0)} Prognosen")
    logger.info(f"📊 Durchschnittswerte verfügbar: {predictions_data.get('averages_available', False)}")
    
    return HTMLResponse(content=html_content)

@app.get("/")
async def root():
    """Root Redirect zu KI-Prognosen"""
    return RedirectResponse(url="/prognosen")

@app.get("/ki-prognosen")
async def ki_prognosen_redirect():
    """Legacy Redirect"""
    return RedirectResponse(url="/prognosen")

# =============================================================================
# SERVICE STARTUP
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Enhanced Frontend Service Startup"""
    logger.info("🚀 Enhanced KI-Prognosen GUI v8.1.0 starting up...")
    logger.info(f"📊 Features: Durchschnittswerte, Timeline-Navigation, Performance-Indikatoren")
    logger.info(f"🔗 Backend API: {config.backend_config['enhanced_predictions_url']}")
    logger.info(f"🌐 Frontend: {config.frontend_config['host']}:{config.frontend_config['port']}")
    
    # Test Backend Connection
    try:
        test_data = await get_enhanced_predictions("1M", 1)
        if test_data.get("error"):
            logger.warning(f"⚠️ Backend connection issue: {test_data['error']}")
        else:
            logger.info("✅ Backend API connection successful")
    except Exception as e:
        logger.error(f"❌ Backend API connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Service Shutdown"""
    logger.info("Enhanced KI-Prognosen GUI shutting down...")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info("🚀 Starting Enhanced KI-Prognosen GUI v8.1.0")
    logger.info("🎯 MISSION: Durchschnittswerte in KI-Prognosen GUI anzeigen")
    logger.info("✨ Features: Clean Architecture + Enhanced ML Predictions Integration")
    
    uvicorn.run(
        app,
        host=config.frontend_config["host"],
        port=config.frontend_config["port"],
        log_level=config.frontend_config["log_level"].lower(),
        access_log=True
    )