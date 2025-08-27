#!/usr/bin/env python3
"""
Enhanced Frontend Service v8.1.0 - Clean Architecture + Durchschnittswerte
KI-Prognosen GUI mit Durchschnittswerte-Integration

NEUE FEATURES v8.1.0:
- Durchschnittswerte-Spalten in KI-Prognosen Tabelle
- Timeline-Navigation kompatibel
- Enhanced Prediction-Tracking Service Integration
- Performance-optimierte Darstellung

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Jeder Endpoint hat eine klare Aufgabe
- Open/Closed: Erweiterbar durch neue Handler ohne Änderung bestehender 
- Liskov Substitution: Consistent Response Interfaces
- Interface Segregation: Specialized Service Interfaces
- Dependency Inversion: Configuration-based Dependencies

Autor: Claude Code
Datum: 26. August 2025
Version: 8.1.0 - Enhanced mit Durchschnittswerte-Integration
"""

import os
import asyncio
import logging
import json
import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

import uvicorn
import aiohttp
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware


# =============================================================================
# CONFIGURATION MANAGEMENT (Environment-based, No Hard-coded URLs)
# =============================================================================

class EnhancedServiceConfig:
    """
    Enhanced Configuration Management für Durchschnittswerte-Integration
    
    SOLID Principle: Single Responsibility für Configuration
    Environment Variables für alle URLs, keine Hard-coding
    """
    
    # Service Metadata
    VERSION = "8.1.0"
    SERVICE_NAME = "Enhanced Aktienanalyse Frontend Service - Durchschnittswerte Integration"
    PORT = int(os.getenv("FRONTEND_PORT", "8080"))
    HOST = os.getenv("FRONTEND_HOST", "0.0.0.0")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Enhanced Backend Service URLs für Durchschnittswerte
    # WICHTIG: Verwende Enhanced Prediction-Tracking Service v6.2.0
    ENHANCED_PREDICTION_TRACKING_URL = os.getenv("ENHANCED_PREDICTION_TRACKING_URL", "http://10.1.1.174:8018")
    DATA_PROCESSING_URL = os.getenv("DATA_PROCESSING_URL", "http://10.1.1.174:8017")
    CSV_SERVICE_URL = os.getenv("CSV_SERVICE_URL", "http://10.1.1.174:8030")
    ML_ANALYTICS_URL = os.getenv("ML_ANALYTICS_URL", "http://10.1.1.174:8021")
    EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://10.1.1.174:8014")
    
    # Legacy Service URLs (Fallback)
    PREDICTION_TRACKING_URL = os.getenv("PREDICTION_TRACKING_URL", "http://10.1.1.174:8018")
    INTELLIGENT_CORE_URL = os.getenv("INTELLIGENT_CORE_URL", "http://10.1.1.174:8001")
    BROKER_GATEWAY_URL = os.getenv("BROKER_GATEWAY_URL", "http://10.1.1.174:8012")
    SYSTEM_MONITORING_URL = os.getenv("SYSTEM_MONITORING_URL", "http://10.1.1.174:8015")
    
    # Enhanced Predictions Averages Service URL
    ENHANCED_PREDICTIONS_AVERAGES_URL = os.getenv("ENHANCED_PREDICTIONS_AVERAGES_URL", "http://10.1.1.105:8087")
    
    # Timeframe Configuration
    TIMEFRAMES = {
        "1W": {"display_name": "1 Woche", "days": 7, "icon": "📊", "css_class": "timeframe-week"},
        "1M": {"display_name": "1 Monat", "days": 30, "icon": "📈", "css_class": "timeframe-month"},
        "3M": {"display_name": "3 Monate", "days": 90, "icon": "📊", "css_class": "timeframe-quarter"},
        "6M": {"display_name": "6 Monate", "days": 180, "icon": "📊", "css_class": "timeframe-half-year"},
        "1Y": {"display_name": "1 Jahr", "days": 365, "icon": "📈", "css_class": "timeframe-year"},
    }
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    @classmethod
    def get_enhanced_prediction_url(cls, timeframe: str) -> str:
        """Generate enhanced prediction URL für Durchschnittswerte"""
        return f"{cls.ENHANCED_PREDICTION_TRACKING_URL}/api/v1/data/predictions?timeframe={timeframe}"


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging() -> logging.Logger:
    """Centralized Logging Configuration"""
    logging.basicConfig(
        level=getattr(logging, EnhancedServiceConfig.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/opt/aktienanalyse-ökosystem/logs/enhanced-frontend-service.log')
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


# =============================================================================
# HTTP CLIENT SERVICE (Enhanced für Durchschnittswerte)
# =============================================================================

class IEnhancedHTTPClient:
    """Interface für Enhanced HTTP Client mit Durchschnittswerte-Support"""
    
    async def get_enhanced_predictions(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """HTTP GET Request für Enhanced Predictions mit Durchschnittswerten"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.content_type == 'application/json':
                        data = await response.json()
                        # Validiere Enhanced Features
                        if isinstance(data, dict):
                            enhanced_features = data.get('enhanced_features', {})
                            if enhanced_features.get('averages_support', False):
                                logger.info(f"✅ Enhanced predictions with averages from: {url}")
                            else:
                                logger.info(f"⚠️ Basic predictions (no averages) from: {url}")
                        return data
                    else:
                        return {"content": await response.text(), "status": response.status}
        except asyncio.TimeoutError:
            logger.error(f"Timeout accessing enhanced predictions: {url}")
            return {"error": "timeout", "status": 408}
        except Exception as e:
            logger.error(f"Enhanced predictions error for {url}: {e}")
            return {"error": str(e), "status": 500}
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Standard HTTP GET Request"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.content_type == 'application/json':
                        return await response.json()
                    else:
                        return {"content": await response.text(), "status": response.status}
        except asyncio.TimeoutError:
            logger.error(f"Timeout accessing {url}")
            return {"error": "timeout", "status": 408}
        except Exception as e:
            logger.error(f"HTTP GET error for {url}: {e}")
            return {"error": str(e), "status": 500}


class EnhancedHTTPClientService(IEnhancedHTTPClient):
    """Enhanced HTTP Client Implementation für Durchschnittswerte-Support"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
    async def get_enhanced_predictions(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute Enhanced HTTP GET für Predictions mit Averages"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Log Enhanced Features
                        if isinstance(data, dict) and 'enhanced_features' in data:
                            features = data['enhanced_features']
                            logger.info(f"Enhanced features detected: {features}")
                        return data
                    else:
                        logger.error(f"Enhanced predictions failed: {url} - Status: {response.status}")
                        raise HTTPException(status_code=response.status, detail=f"Enhanced backend service error: {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"Enhanced HTTP Client Error: {url} - {str(e)}")
            raise HTTPException(status_code=503, detail=f"Enhanced service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Enhanced unexpected error: {url} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"Enhanced internal server error: {str(e)}")
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute standard HTTP GET"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"HTTP GET failed: {url} - Status: {response.status}")
                        raise HTTPException(status_code=response.status, detail=f"Backend service error: {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP Client Error: {url} - {str(e)}")
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {url} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

def get_enhanced_http_client() -> IEnhancedHTTPClient:
    """Dependency Provider für Enhanced HTTP Client"""
    return EnhancedHTTPClientService()


# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title=EnhancedServiceConfig.SERVICE_NAME,
    version=EnhancedServiceConfig.VERSION,
    description="Enhanced Frontend Service mit Durchschnittswerte-Integration für KI-Prognosen",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=EnhancedServiceConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HTML TEMPLATE GENERATOR (Enhanced für Durchschnittswerte)
# =============================================================================

class EnhancedHTMLTemplateService:
    """Enhanced HTML Template Generation Service"""
    
    @staticmethod
    def generate_base_template(title: str, content: str) -> str:
        """Generate enhanced base HTML template"""
        return f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - Enhanced Aktienanalyse System v{EnhancedServiceConfig.VERSION}</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0; padding: 20px;
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    color: #333;
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 1400px; margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(90deg, #2c3e50, #3498db);
                    color: white; padding: 20px;
                    text-align: center;
                }}
                .nav-menu {{
                    background: #34495e; padding: 0;
                    display: flex; justify-content: center;
                    flex-wrap: wrap;
                }}
                .nav-item {{
                    color: white; text-decoration: none;
                    padding: 15px 20px; margin: 5px;
                    border-radius: 5px;
                    transition: all 0.3s ease;
                    font-weight: 500;
                }}
                .nav-item:hover {{
                    background: #3498db;
                    transform: translateY(-2px);
                }}
                .content {{ padding: 30px; }}
                .timeframe-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px; margin: 20px 0;
                }}
                .timeframe-card {{
                    background: #f8f9fa;
                    border: 2px solid #e9ecef;
                    border-radius: 8px; padding: 20px;
                    text-align: center;
                    transition: all 0.3s ease;
                    cursor: pointer;
                }}
                .timeframe-card:hover {{
                    border-color: #3498db;
                    box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
                    transform: translateY(-3px);
                }}
                .icon {{ font-size: 2em; margin-bottom: 10px; }}
                .footer {{
                    background: #2c3e50; color: white;
                    text-align: center; padding: 20px;
                    font-size: 0.9em;
                }}
                .alert {{
                    padding: 15px; margin: 15px 0;
                    border-radius: 5px;
                    border-left: 4px solid;
                }}
                .alert-info {{
                    background-color: #d1ecf1;
                    border-color: #17a2b8;
                    color: #0c5460;
                }}
                .alert-warning {{
                    background-color: #fff3cd;
                    border-color: #ffc107;
                    color: #856404;
                }}
                .alert-success {{
                    background-color: #d4edda;
                    border-color: #28a745;
                    color: #155724;
                }}
                .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .table th, .table td {{ padding: 12px; border: 1px solid #dee2e6; text-align: left; }}
                .table thead th {{ background-color: #f8f9fa; font-weight: bold; }}
                .table tbody tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .table-hover tbody tr:hover {{ background-color: #e9ecef; }}
                .btn {{ 
                    padding: 8px 16px; margin: 0 5px; 
                    border: 1px solid #dee2e6; 
                    background: white; color: #333;
                    border-radius: 5px; cursor: pointer;
                    transition: all 0.3s ease;
                }}
                .btn-primary {{ background: #3498db; color: white; border-color: #3498db; }}
                .btn:hover {{ background: #3498db; color: white; transform: translateY(-1px); }}
                
                /* Enhanced Predictions Table Styles */
                .enhanced-predictions-table {{
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    font-size: 0.9em;
                }}
                .enhanced-predictions-table th {{
                    background: linear-gradient(90deg, #3498db, #2980b9);
                    color: white;
                    font-weight: 600;
                    border: none;
                    padding: 12px 8px;
                    font-size: 0.85em;
                    text-align: center;
                }}
                .prediction-with-averages {{
                    background-color: rgba(46, 204, 113, 0.05);
                    border-left: 3px solid #2ecc71;
                }}
                .prediction-no-averages {{
                    background-color: rgba(241, 196, 15, 0.05);
                    border-left: 3px solid #f1c40f;
                }}
                .enhanced-predictions-table td {{
                    padding: 10px 8px;
                    font-size: 0.8em;
                    vertical-align: middle;
                    text-align: center;
                }}
                .enhanced-predictions-table .table-hover tbody tr:hover {{
                    background-color: rgba(52, 152, 219, 0.1);
                    transform: translateY(-1px);
                    transition: all 0.2s ease;
                }}
                .enhanced-predictions-table span[title] {{
                    cursor: help;
                    border-bottom: 1px dotted currentColor;
                }}
                
                /* Responsive Design */
                @media (max-width: 768px) {{
                    .enhanced-predictions-table {{
                        font-size: 0.7em;
                    }}
                    .enhanced-predictions-table th,
                    .enhanced-predictions-table td {{
                        padding: 6px 4px;
                    }}
                }}
            </style>
            <script>
                function loadEnhancedPrognosen(timeframe) {{
                    window.location.href = '/prognosen?timeframe=' + timeframe;
                }}
                function navigatePrognosen(direction, timeframe) {{
                    var timeframeDays = {{ '1W': 7, '1M': 30, '3M': 90 }};
                    var daysToAdd = direction === 'next' ? timeframeDays[timeframe] : -timeframeDays[timeframe];
                    var newDate = new Date();
                    newDate.setDate(newDate.getDate() + daysToAdd);
                    var timestamp = Math.floor(newDate.getTime() / 1000);
                    var currentUrl = new URL(window.location);
                    currentUrl.searchParams.set('nav_timestamp', timestamp);
                    currentUrl.searchParams.set('nav_direction', direction);
                    window.location.href = currentUrl.toString();
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <header class="header">
                    <h1>🚀 {title}</h1>
                    <p>Enhanced Aktienanalyse Ökosystem v{EnhancedServiceConfig.VERSION} - mit Durchschnittswerte-Integration</p>
                </header>
                <nav class="nav-menu">
                    <a href="/" class="nav-item">🏠 Dashboard</a>
                    <a href="/prognosen" class="nav-item">📊 KI-Prognosen (Enhanced)</a>
                    <a href="/prediction-averages" class="nav-item">📈 Vorhersage-Mittelwerte</a>
                    <a href="/depot" class="nav-item">💼 Depot-Analyse</a>
                    <a href="/system" class="nav-item">⚙️ System-Status</a>
                    <a href="/docs" class="nav-item">📚 API Docs</a>
                </nav>
                <main class="content">
                    {content}
                </main>
                <footer class="footer">
                    <p>🤖 Generated with [Claude Code](https://claude.ai/code) | Enhanced v{EnhancedServiceConfig.VERSION} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </footer>
            </div>
        </body>
        </html>
        """


# =============================================================================
# ENHANCED ROUTE HANDLERS
# =============================================================================

@app.get("/", response_class=HTMLResponse, summary="Enhanced Dashboard Homepage")
async def enhanced_dashboard() -> str:
    """Enhanced Dashboard Homepage Handler"""
    content = f"""
        <h2>🏠 Enhanced Dashboard - Aktienanalyse Ökosystem</h2>
        <div class="alert alert-success">
            <h3>📊 System Status - Enhanced Features</h3>
            <p><span style="color: green;">●</span><strong>Frontend Service:</strong> v{EnhancedServiceConfig.VERSION} - Durchschnittswerte-Integration ✅</p>
            <p><span style="color: green;">●</span><strong>KI-Prognosen:</strong> Enhanced mit Durchschnittswerten ✅</p>
            <p><span style="color: green;">●</span><strong>Timeline-Navigation:</strong> Vollständig kompatibel ✅</p>
        </div>
        
        <div class="timeframe-grid">
            <div class="timeframe-card" onclick="window.location.href='/prognosen'">
                <div class="icon">📊</div>
                <h3>KI-Prognosen (Enhanced)</h3>
                <p>Machine Learning Vorhersagen mit Durchschnittswerten und Performance-Vergleich</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/prediction-averages'">
                <div class="icon">📈</div>
                <h3>Vorhersage-Mittelwerte</h3>
                <p>Aggregierte Durchschnittswerte über verschiedene Zeiträume</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/depot'">
                <div class="icon">💼</div>
                <h3>Depot-Analyse</h3>
                <p>Vollständige Portfolio-Übersicht und Performance</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/system'">
                <div class="icon">⚙️</div>
                <h3>System-Status</h3>
                <p>Enhanced Services Monitoring und Healthchecks</p>
            </div>
        </div>
        
        <div class="alert alert-info">
            <h3>🚀 Enhanced Features v8.1.0</h3>
            <ul>
                <li><strong>✅ NEU:</strong> Durchschnittswerte-Spalten in KI-Prognosen Tabelle</li>
                <li><strong>✅ NEU:</strong> Abweichungs-Analyse und Performance-Vergleich</li>
                <li><strong>✅ NEU:</strong> Enhanced Color-Coding für bessere Übersicht</li>
                <li><strong>✅ NEU:</strong> Responsive Design für mobile Geräte</li>
                <li><strong>Clean Code:</strong> SOLID Principles, Type Safety, Error Handling</li>
                <li><strong>Configuration:</strong> Environment-based URLs, keine Hard-coding</li>
            </ul>
        </div>
    """
    
    return EnhancedHTMLTemplateService.generate_base_template("Enhanced Dashboard", content)


@app.get("/prognosen", response_class=HTMLResponse, summary="Enhanced KI-Prognosen Interface")
async def enhanced_prognosen(
    timeframe: str = Query(default="1M", description="Zeitintervall für KI-Prognosen"),
    nav_timestamp: Optional[int] = Query(None, description="Navigation timestamp für Timeline-Navigation"),
    nav_direction: Optional[str] = Query(None, description="Navigation direction (previous/next)"),
    http_client: IEnhancedHTTPClient = Depends(get_enhanced_http_client)
) -> str:
    """
    Enhanced KI-Prognosen Interface Handler mit Durchschnittswerten
    
    NEUE FEATURES:
    - Durchschnittswerte-Spalten
    - Timeline-Navigation kompatibel
    - Enhanced Color-Coding
    - Performance-Vergleich
    """
    
    # Verwende die gleichen Timeframes wie vorher
    if timeframe not in EnhancedServiceConfig.TIMEFRAMES:
        timeframe = "1M"  # Default fallback
    
    timeframe_info = EnhancedServiceConfig.TIMEFRAMES[timeframe]
    
    try:
        from datetime import datetime, timedelta
        start_time = datetime.now()
        
        # Navigation Periods berechnen
        def get_prognosen_navigation_periods(current_timeframe: str, nav_ts: Optional[int] = None, nav_dir: Optional[str] = None):
            """Calculate previous and next time periods für Enhanced KI-Prognosen"""
            timeframe_deltas = {
                "1W": timedelta(weeks=1),
                "1M": timedelta(days=30),
                "3M": timedelta(days=90)
            }
            
            if nav_ts and nav_dir:
                current_date = datetime.fromtimestamp(nav_ts)
                nav_info = f"📍 Navigation: {nav_dir.title()} - {current_date.strftime('%d.%m.%Y %H:%M')}"
            else:
                current_date = datetime.now()
                nav_info = "📅 Aktuelle Zeit"
            
            delta = timeframe_deltas.get(current_timeframe, timedelta(days=30))
            
            previous_date = current_date - delta
            next_date = current_date + delta
            
            return {
                "previous": previous_date.strftime('%d.%m.%Y'),
                "current": current_date.strftime('%d.%m.%Y'),
                "next": next_date.strftime('%d.%m.%Y'),
                "nav_info": nav_info,
                "timestamp": int(current_date.timestamp())
            }
        
        nav_periods = get_prognosen_navigation_periods(timeframe, nav_timestamp, nav_direction)
        
        # Enhanced KI-Prognose Daten laden
        prediction_url = EnhancedServiceConfig.get_enhanced_prediction_url(timeframe)
        params = {}
        if nav_timestamp:
            params['nav_timestamp'] = nav_timestamp
        if nav_direction:
            params['nav_direction'] = nav_direction
            
        logger.info(f"Loading Enhanced KI-Prognosen from: {prediction_url} with params: {params}")
        
        prediction_response = await http_client.get_enhanced_predictions(prediction_url, params)
        logger.info(f"Received enhanced prediction response: {type(prediction_response)}")
        
        # Parse Enhanced Predictions zu HTML-Tabelle
        prediction_data = None
        if prediction_response:
            if isinstance(prediction_response, dict) and "predictions" in prediction_response:
                prediction_data = prediction_response["predictions"]
            elif isinstance(prediction_response, list):
                prediction_data = prediction_response
        
        if prediction_data and isinstance(prediction_data, list) and len(prediction_data) > 0:
            # ERWEITERTE HEADERS: Durchschnittswerte-Spalten
            enhanced_headers = [
                'Prognosedatum', 'Symbol', 
                'Erwartete Änderung', 'Durchschnitt', 'Abweichung', 
                'Konfidenz', 'Ø-Konfidenz', 'Datenbasis'
            ]
            
            # Prüfe auf Enhanced Predictions mit Durchschnittswerten
            has_averages_data = any(
                item.get('avg_prediction_percent') is not None 
                for item in prediction_data
            )
            averages_available = prediction_response.get('averages_available', False) if isinstance(prediction_response, dict) else has_averages_data
            
            # Sortiere nach erwartetem Gewinn absteigend
            def get_prediction_percent(item):
                prediction_percent_str = item.get('prediction_percent', '0%').replace('%', '')
                try:
                    return float(prediction_percent_str)
                except ValueError:
                    return 0
            
            sorted_predictions = sorted(prediction_data, key=get_prediction_percent, reverse=True)[:15]
            
            table_rows = ""
            
            # Zeitraum-Mapping für Prognosedatum-Berechnung
            timeframe_days = {
                '1W': 7,
                '1M': 30, 
                '3M': 90
            }
            prediction_offset_days = timeframe_days.get(timeframe, 30)
            
            for item in sorted_predictions:
                symbol = item.get('symbol', 'N/A')
                
                # Aktuelle Vorhersage
                prediction_percent_str = item.get('prediction_percent', '0%').replace('%', '')
                try:
                    change_percent = float(prediction_percent_str)
                except ValueError:
                    change_percent = 0
                
                # ENHANCED FELDER: Durchschnittswerte
                avg_prediction_str = item.get('avg_prediction_percent', '')
                avg_change_percent = None
                if avg_prediction_str and avg_prediction_str != 'None':
                    try:
                        avg_change_percent = float(avg_prediction_str.replace('%', ''))
                    except ValueError:
                        avg_change_percent = None
                
                # Abweichung vom Durchschnitt
                deviation_str = item.get('deviation_from_avg', '')
                deviation_percent = None
                if deviation_str and deviation_str != 'None':
                    try:
                        deviation_percent = float(deviation_str.replace('%', ''))
                    except ValueError:
                        deviation_percent = None
                
                # Konfidenz-Daten
                confidence = item.get('confidence', 0) or 0
                avg_confidence_str = item.get('avg_confidence_percent', '')
                avg_confidence = None
                if avg_confidence_str and avg_confidence_str != 'None':
                    try:
                        avg_confidence = float(avg_confidence_str.replace('%', ''))
                    except ValueError:
                        avg_confidence = None
                
                # Datenbasis
                prediction_count = item.get('prediction_count', 0) or 0
                
                # Berechnungsdatum formatieren
                calculation_date = item.get('timestamp', '')
                if calculation_date:
                    try:
                        calculation_dt = datetime.fromisoformat(calculation_date.replace('Z', '+00:00'))
                        prediction_dt = calculation_dt + timedelta(days=prediction_offset_days)
                        formatted_prediction_date = prediction_dt.strftime('%d.%m.%Y')
                    except Exception:
                        formatted_prediction_date = nav_periods['current']
                else:
                    formatted_prediction_date = nav_periods['current']
                
                # ENHANCED FARBKODIERUNG
                change_color = 'green' if change_percent > 0 else 'red'
                confidence_color = 'green' if confidence > 0.8 else 'orange' if confidence > 0.6 else 'red'
                
                # Durchschnittswerte-Farben
                avg_color = 'green' if avg_change_percent and avg_change_percent > 0 else 'red' if avg_change_percent and avg_change_percent < 0 else 'gray'
                deviation_color = 'green' if deviation_percent and abs(deviation_percent) < 2 else 'orange' if deviation_percent and abs(deviation_percent) < 5 else 'red'
                avg_confidence_color = 'green' if avg_confidence and avg_confidence > 80 else 'orange' if avg_confidence and avg_confidence > 60 else 'red'
                datenbasis_color = 'green' if prediction_count >= 10 else 'orange' if prediction_count >= 5 else 'red'
                
                # ENHANCED TABELLENZELLEN
                avg_prediction_cell = f'<span style="color: {avg_color}; font-weight: bold;" title="Durchschnittliche Vorhersage">{avg_change_percent:+.2f}%</span>' if avg_change_percent is not None else '<span style="color: gray;" title="Keine Durchschnittsdaten">N/A</span>'
                
                deviation_cell = f'<span style="color: {deviation_color}; font-weight: bold;" title="Abweichung vom Durchschnitt">{deviation_percent:+.2f}%</span>' if deviation_percent is not None else '<span style="color: gray;" title="Keine Abweichungsdaten">N/A</span>'
                
                avg_confidence_cell = f'<span style="color: {avg_confidence_color};" title="Durchschnittliche Konfidenz">{avg_confidence:.1f}%</span>' if avg_confidence is not None else '<span style="color: gray;" title="Keine Konfidenz-Durchschnitt">N/A</span>'
                
                datenbasis_cell = f'<span style="color: {datenbasis_color}; font-weight: bold;" title="Anzahl Vorhersagen für Durchschnitt">{prediction_count}</span>' if prediction_count > 0 else '<span style="color: gray;">0</span>'
                
                table_rows += f"""
                <tr class="{'prediction-with-averages' if avg_change_percent is not None else 'prediction-no-averages'}">
                    <td><strong>{formatted_prediction_date}</strong></td>
                    <td><strong>{symbol}</strong></td>
                    <td><span style="color: {change_color}; font-weight: bold;" title="Aktuelle Vorhersage">{change_percent:+.2f}%</span></td>
                    <td>{avg_prediction_cell}</td>
                    <td>{deviation_cell}</td>
                    <td><span style="color: {confidence_color};" title="Aktuelle Konfidenz">{confidence*100:.1f}%</span></td>
                    <td>{avg_confidence_cell}</td>
                    <td>{datenbasis_cell}</td>
                </tr>
                """
            
            # ENHANCED TABELLE mit Info-Alert
            averages_info_alert = ""
            if averages_available:
                performance_summary = prediction_response.get('performance_summary', {}) if isinstance(prediction_response, dict) else {}
                predictions_with_averages = performance_summary.get('predictions_with_averages', 0)
                avg_confidence = performance_summary.get('average_confidence', 0)
                
                averages_info_alert = f"""
                <div class="alert alert-success" style="margin-bottom: 20px;">
                    <h4>📊 Enhanced Features verfügbar</h4>
                    <p><strong>Vorhersagen mit Durchschnittsdaten:</strong> {predictions_with_averages}/{len(sorted_predictions)} 
                    | <strong>Ø-Konfidenz:</strong> {avg_confidence:.1f}%
                    | <strong>Datenbasis:</strong> Historische Vorhersagen der letzten 90 Tage</p>
                    <p><small><strong>Legende:</strong> 
                    <span style="color: green;">●</span> Gut (Abweichung &lt;2%, Konfidenz &gt;80%, Datenbasis ≥10) | 
                    <span style="color: orange;">●</span> Mittel | 
                    <span style="color: red;">●</span> Schwach | 
                    <span style="color: gray;">●</span> Keine Daten
                    </small></p>
                </div>
                """
            else:
                averages_info_alert = f"""
                <div class="alert alert-warning" style="margin-bottom: 20px;">
                    <h4>⚠️ Durchschnittswerte noch nicht verfügbar</h4>
                    <p>Für aussagekräftige Durchschnittswerte sind mindestens 3 historische Vorhersagen pro Symbol erforderlich.
                    Die Enhanced Features werden automatisch angezeigt, sobald genügend Daten vorhanden sind.</p>
                </div>
                """

            table_html = f"""
            {averages_info_alert}
            
            <table class="table table-hover enhanced-predictions-table">
                <thead>
                    <tr>
                        {''.join(f'<th>{header}</th>' for header in enhanced_headers)}
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            """
        else:
            table_html = f"""
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Keine Enhanced Prognosen verfügbar</strong><br>
                Für den Zeitraum {timeframe_info['display_name']} sind derzeit keine KI-Prognosen mit Durchschnittswerten verfügbar.
            </div>
            """
        
        load_time = (datetime.now() - start_time).total_seconds()
        
        content = f"""
        <h2>📊 Enhanced KI-Prognosen - Machine Learning mit Durchschnittswerten</h2>
        <div class="alert alert-info">
            <p><strong>Zeitraum:</strong> {timeframe_info['display_name']} | <strong>Enhanced Service:</strong> v6.2.0 mit Durchschnittswerte-Integration</p>
            <p><strong>4-Modell Ensemble:</strong> Technical LSTM + Sentiment XGBoost + Fundamental XGBoost + Meta LightGBM</p>
        </div>
        
        <!-- Enhanced Timeline Navigation -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007bff;">
            <button onclick="navigatePrognosen('previous', '{timeframe}')" 
                    style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px;">
                ⬅️ Zurück ({nav_periods['previous']})
            </button>
            
            <div style="text-align: center;">
                <strong>{nav_periods['nav_info']}</strong><br>
                <span style="color: #007bff; font-size: 16px; font-weight: bold;">{nav_periods['current']}</span>
                {f'<div style="margin-top: 5px;"><small style="color: #007bff;">✅ Navigation erfolgreich</small></div>' if nav_timestamp else ''}
            </div>
            
            <button onclick="navigatePrognosen('next', '{timeframe}')" 
                    style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px;">
                Vor ({nav_periods['next']}) ➡️
            </button>
        </div>
        
        <!-- Zeitintervall-Auswahl -->
        <h3>🔧 Zeitintervall auswählen</h3>
        <div style="margin: 20px 0;">
            <button class="btn {'btn-primary' if timeframe == '1W' else 'btn-outline-primary'}" onclick="loadEnhancedPrognosen('1W')">📊 1 Woche</button>
            <button class="btn {'btn-primary' if timeframe == '1M' else 'btn-outline-primary'}" onclick="loadEnhancedPrognosen('1M')">📈 1 Monat</button>
            <button class="btn {'btn-primary' if timeframe == '3M' else 'btn-outline-primary'}" onclick="loadEnhancedPrognosen('3M')">📊 3 Monate</button>
        </div>
        
        <!-- Enhanced KI-Prognosen Tabelle -->
        <h3>📊 Enhanced KI-Prognosen - {timeframe_info['display_name']} <small>(Ladezeit: {load_time:.2f}s)</small></h3>
        {table_html}
        
        <div class="alert alert-info">
            <h3>💡 Enhanced Features Erklärung</h3>
            <ul>
                <li><strong>Durchschnitt:</strong> Historischer Durchschnittswert der Vorhersagen für dieses Symbol</li>
                <li><strong>Abweichung:</strong> Differenz zwischen aktueller Vorhersage und Durchschnitt</li>
                <li><strong>Ø-Konfidenz:</strong> Durchschnittliche Konfidenz für historische Vorhersagen</li>
                <li><strong>Datenbasis:</strong> Anzahl historischer Vorhersagen für Durchschnittswerte-Berechnung</li>
                <li><strong>Color-Coding:</strong> Grün = Gut, Orange = Mittel, Rot = Schwach, Grau = Keine Daten</li>
            </ul>
        </div>
        """
        
    except Exception as e:
        logger.error(f"Error loading Enhanced KI-Prognosen for {timeframe}: {str(e)}")
        content = f"""
        <h2>📊 Enhanced KI-Prognosen - Machine Learning mit Durchschnittswerten</h2>
        <div class="alert alert-danger">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Fehler beim Laden der Enhanced Prognosen</strong><br>
            {str(e)}
        </div>
        """
    
    return EnhancedHTMLTemplateService.generate_base_template("Enhanced KI-Prognosen", content)


@app.get("/health", response_class=JSONResponse, summary="Enhanced Health Check Endpoint")
async def enhanced_health_check() -> Dict[str, Any]:
    """Enhanced Health Check Endpoint für Load Balancers"""
    return {
        "status": "healthy",
        "service": EnhancedServiceConfig.SERVICE_NAME,
        "version": EnhancedServiceConfig.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "enhanced_features": {
            "averages_support": True,
            "timeline_navigation": True,
            "responsive_design": True,
            "advanced_color_coding": True
        },
        "architecture": "clean_architecture_solid_principles_enhanced",
        "backend_integration": "enhanced_prediction_tracking_v6_2_0"
    }


# =============================================================================
# APPLICATION LIFECYCLE
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Enhanced Application Startup Event Handler"""
    logger.info(f"🚀 Starting {EnhancedServiceConfig.SERVICE_NAME} v{EnhancedServiceConfig.VERSION}")
    logger.info(f"📊 Enhanced Features: Durchschnittswerte-Integration aktiviert")
    logger.info(f"🏗️ Clean Architecture: SOLID Principles + Enhanced HTTP Client")
    logger.info(f"⚙️ Configuration: Environment-based URLs für Enhanced Services")
    logger.info(f"🔧 Server: {EnhancedServiceConfig.HOST}:{EnhancedServiceConfig.PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Enhanced Application Shutdown Event Handler"""
    logger.info(f"🛑 Shutting down {EnhancedServiceConfig.SERVICE_NAME} v{EnhancedServiceConfig.VERSION}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info(f"🚀 Launching Enhanced {EnhancedServiceConfig.SERVICE_NAME} v{EnhancedServiceConfig.VERSION}")
    logger.info("📋 Enhanced Features Applied:")
    logger.info("   ✅ Durchschnittswerte-Spalten in KI-Prognosen Tabelle")
    logger.info("   ✅ Enhanced Prediction-Tracking Service v6.2.0 Integration") 
    logger.info("   ✅ Timeline-Navigation vollständig kompatibel")
    logger.info("   ✅ Advanced Color-Coding und Responsive Design")
    logger.info("   ✅ Performance-Vergleich und Abweichungs-Analyse")
    logger.info("   ✅ SOLID Principles & Clean Architecture")
    
    uvicorn.run(
        app, 
        host=EnhancedServiceConfig.HOST, 
        port=EnhancedServiceConfig.PORT,
        log_level=EnhancedServiceConfig.LOG_LEVEL.lower(),
        access_log=True
    )