#!/usr/bin/env python3
"""
Frontend Service v8.0.1 - Clean Architecture
Konsolidierte Version + SOLL-IST Vergleich Endpoints

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Jeder Endpoint hat eine klare Aufgabe
- Open/Closed: Erweiterbar durch neue Handler ohne Änderung bestehender 
- Liskov Substitution: Consistent Response Interfaces
- Interface Segregation: Specialized Service Interfaces
- Dependency Inversion: Configuration-based Dependencies

WIEDERHERGESTELLTE FUNKTIONEN:
- /vergleichsanalyse - SOLL-IST Vergleichsanalyse mit CSV-Service Integration
- /api/content/vergleichsanalyse - API Endpoint für Vergleichsanalyse

Autor: Claude Code
Datum: 23. August 2025
Version: 8.0.1 (FIXED - Ursprüngliche Funktionen wiederhergestellt)
Konsolidiert: 13 → 1 Frontend Service Versionen + Missing Features Fix
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

class ServiceConfig:
    """
    Centralized Configuration Management
    
    SOLID Principle: Single Responsibility für Configuration
    Environment Variables für alle URLs, keine Hard-coding
    """
    
    # Service Metadata
    VERSION = "8.0.1"
    SERVICE_NAME = "Aktienanalyse Frontend Service - Consolidated + Fixed"
    PORT = int(os.getenv("FRONTEND_PORT", "8080"))
    HOST = os.getenv("FRONTEND_HOST", "0.0.0.0")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Backend Service URLs (Environment-configurable)
    # Production-ready service URLs - 10.1.1.174 deployment
    DATA_PROCESSING_URL = os.getenv("DATA_PROCESSING_URL", "http://10.1.1.174:8091")  # Enhanced service
    CSV_SERVICE_URL = os.getenv("CSV_SERVICE_URL", "http://10.1.1.174:8030")
    PREDICTION_TRACKING_URL = os.getenv("PREDICTION_TRACKING_URL", "http://10.1.1.174:8018")
    ML_ANALYTICS_URL = os.getenv("ML_ANALYTICS_URL", "http://10.1.1.174:8021")
    EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://10.1.1.174:8014")
    INTELLIGENT_CORE_URL = os.getenv("INTELLIGENT_CORE_URL", "http://10.1.1.174:8001")
    BROKER_GATEWAY_URL = os.getenv("BROKER_GATEWAY_URL", "http://10.1.1.174:8012")
    SYSTEM_MONITORING_URL = os.getenv("SYSTEM_MONITORING_URL", "http://10.1.1.174:8015")
    
    # Vergleichsanalyse Service URL (SOLL-IST Service)
    VERGLEICHSANALYSE_SERVICE_URL = os.getenv("VERGLEICHSANALYSE_SERVICE_URL", "http://10.1.1.174:8025")
    
    # Enhanced Predictions Averages Service URL
    ENHANCED_PREDICTIONS_AVERAGES_URL = os.getenv("ENHANCED_PREDICTIONS_AVERAGES_URL", "http://10.1.1.105:8087")
    
    # Timeframe Configuration
    TIMEFRAMES = {
        "1W": {"display_name": "1 Woche", "days": 7, "icon": "📊", "css_class": "timeframe-week"},
        "1M": {"display_name": "1 Monat", "days": 30, "icon": "📈", "css_class": "timeframe-month"},
        "3M": {"display_name": "3 Monate", "days": 90, "icon": "📊", "css_class": "timeframe-quarter"},
        "6M": {"display_name": "6 Monate", "days": 180, "icon": "📊", "css_class": "timeframe-half-year"},
        "12M": {"display_name": "12 Monate", "days": 365, "icon": "📈", "css_class": "timeframe-year"},
        "1Y": {"display_name": "1 Jahr", "days": 365, "icon": "📈", "css_class": "timeframe-year"},
    }
    
    # Vergleichsanalyse Timeframes - Korrigiert für Prediction-Tracking Service
    VERGLEICHSANALYSE_TIMEFRAMES = {
        "1W": {
            "display_name": "1 Woche", 
            "description": "Wöchentliche SOLL-IST Vergleiche", 
            "days": 7, 
            "icon": "📊", 
            "url": f"{os.getenv('PREDICTION_TRACKING_URL', 'http://10.1.1.174:8018')}/api/v1/soll-ist-comparison?days_back=7"
        },
        "1M": {
            "display_name": "1 Monat", 
            "description": "Monatliche SOLL-IST Vergleiche", 
            "days": 30, 
            "icon": "📈", 
            "url": f"{os.getenv('PREDICTION_TRACKING_URL', 'http://10.1.1.174:8018')}/api/v1/soll-ist-comparison?days_back=30"
        },
        "3M": {
            "display_name": "3 Monate", 
            "description": "Quartalsweise SOLL-IST Vergleiche", 
            "days": 90, 
            "icon": "📊", 
            "url": f"{os.getenv('PREDICTION_TRACKING_URL', 'http://10.1.1.174:8018')}/api/v1/soll-ist-comparison?days_back=90"
        },
        "12M": {
            "display_name": "12 Monate", 
            "description": "Jährliche SOLL-IST Vergleiche", 
            "days": 365, 
            "icon": "📈", 
            "url": f"{os.getenv('PREDICTION_TRACKING_URL', 'http://10.1.1.174:8018')}/api/v1/soll-ist-comparison?days_back=365"
        }
    }
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    @classmethod
    def get_prediction_url(
        cls, 
        timeframe: str, 
        nav_timestamp: Optional[int] = None, 
        nav_direction: Optional[str] = None
    ) -> str:
        """
        Generate prediction URL for timeframe with optional navigation parameters
        
        KI-PROGNOSEN-NAV-002 Fix: Frontend supports nav_timestamp and nav_direction
        """
        base_url = f"{cls.DATA_PROCESSING_URL}/api/v1/data/predictions"
        params = [f"timeframe={timeframe}"]
        
        # Add navigation parameters if provided
        if nav_timestamp is not None:
            params.append(f"nav_timestamp={nav_timestamp}")
        
        if nav_direction is not None:
            params.append(f"nav_direction={nav_direction}")
        
        return f"{base_url}?{'&'.join(params)}"
    
    @classmethod
    def get_timeline_navigation_url(
        cls,
        timeframe: str,
        nav_timestamp: Optional[int] = None,
        nav_direction: Optional[str] = None
    ) -> str:
        """Generate dedicated timeline navigation URL"""
        base_url = f"{cls.DATA_PROCESSING_URL}/api/v1/data/timeline-navigation"
        params = [f"timeframe={timeframe}"]
        
        if nav_timestamp is not None:
            params.append(f"nav_timestamp={nav_timestamp}")
        
        if nav_direction is not None:
            params.append(f"nav_direction={nav_direction}")
            
        return f"{base_url}?{'&'.join(params)}"


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging() -> logging.Logger:
    """
    Centralized Logging Configuration
    
    Single Responsibility: Nur Logging Setup
    Enhanced Debug-Logging für KI-Prognosen Bug Debugging
    """
    # Force DEBUG level für intensive Debugging
    log_level = logging.DEBUG if ServiceConfig.LOG_LEVEL.upper() == 'DEBUG' else getattr(logging, ServiceConfig.LOG_LEVEL.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/opt/aktienanalyse-ökosystem/logs/frontend-service.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    
    # Aktiviere auch aiohttp-Logging für HTTP-Client Debugging
    aiohttp_logger = logging.getLogger('aiohttp.client')
    aiohttp_logger.setLevel(log_level)
    
    logger.info(f"Enhanced Logging Setup: Level={log_level}, File=/opt/aktienanalyse-ökosystem/logs/frontend-service.log")
    return logger


logger = setup_logging()


# =============================================================================
# HTTP CLIENT SERVICE (Dependency Inversion)
# =============================================================================

class IHTTPClient:
    """Interface für HTTP Client (Interface Segregation Principle)"""
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """HTTP GET Request"""
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
    
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """HTTP POST Request"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.content_type == 'application/json':
                        return await response.json()
                    else:
                        return {"content": await response.text(), "status": response.status}
        except asyncio.TimeoutError:
            logger.error(f"Timeout accessing {url}")
            return {"error": "timeout", "status": 408}
        except Exception as e:
            logger.error(f"HTTP POST error for {url}: {e}")
            return {"error": str(e), "status": 500}
    
    async def get_text(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """HTTP GET Request returning text"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return await response.text()
        except asyncio.TimeoutError:
            logger.error(f"Timeout accessing {url}")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"HTTP GET text error for {url}: {e}")
            return f"Error: {str(e)}"


class HTTPClientService(IHTTPClient):
    """
    Concrete HTTP Client Implementation
    
    SOLID Principles:
    - Single Responsibility: Nur HTTP Operations
    - Dependency Inversion: Implementiert Interface
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute HTTP GET with error handling"""
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
    
    async def get_text(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Execute HTTP GET returning text"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.error(f"HTTP GET TEXT failed: {url} - Status: {response.status}")
                        raise HTTPException(status_code=response.status, detail=f"Backend service error: {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP Client Error: {url} - {str(e)}")
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {url} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute HTTP POST with error handling"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=data) as response:
                    if response.status in [200, 201]:
                        return await response.json()
                    else:
                        logger.error(f"HTTP POST failed: {url} - Status: {response.status}")
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

def get_http_client() -> IHTTPClient:
    """Dependency Provider für HTTP Client"""
    return HTTPClientService()


# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title=ServiceConfig.SERVICE_NAME,
    version=ServiceConfig.VERSION,
    description="Konsolidierte Frontend Service Implementation mit wiederhergestellten Analyse-Funktionen",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ServiceConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HTML TEMPLATE GENERATOR (Single Responsibility)
# =============================================================================

class HTMLTemplateService:
    """
    HTML Template Generation Service
    
    Single Responsibility: Nur HTML Template Generation
    Open/Closed: Erweiterbar für neue Templates
    """
    
    @staticmethod
    def generate_base_template(title: str, content: str) -> str:
        """Generate base HTML template"""
        return f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - Aktienanalyse System v{ServiceConfig.VERSION}</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0; padding: 20px;
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    color: #333;
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 1200px; margin: 0 auto;
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
                .status-indicator {{
                    display: inline-block;
                    width: 10px; height: 10px;
                    border-radius: 50%;
                    margin-right: 8px;
                }}
                .status-active {{ background-color: #27ae60; }}
                .status-inactive {{ background-color: #e74c3c; }}
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
                .alert-error {{
                    background-color: #f8d7da;
                    border-color: #dc3545;
                    color: #721c24;
                }}
                .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .table th, .table td {{ padding: 12px; border: 1px solid #dee2e6; text-align: left; }}
                .table thead th {{ background-color: #f8f9fa; font-weight: bold; }}
                .table tbody tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .table-hover tbody tr:hover {{ background-color: #e9ecef; }}
                .btn-group {{ display: inline-flex; margin: 10px 0; }}
                .btn {{ 
                    padding: 8px 16px; margin: 0 5px; 
                    border: 1px solid #dee2e6; 
                    background: white; color: #333;
                    border-radius: 5px; cursor: pointer;
                    transition: all 0.3s ease;
                }}
                .btn-primary {{ background: #3498db; color: white; border-color: #3498db; }}
                .btn-outline-primary {{ color: #3498db; border-color: #3498db; }}
                .btn:hover {{ background: #3498db; color: white; transform: translateY(-1px); }}
            </style>
            <script>
                function loadVergleichsanalyse(timeframe) {{
                    window.location.href = '/vergleichsanalyse?timeframe=' + timeframe;
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <header class="header">
                    <h1>🚀 {title}</h1>
                    <p>Aktienanalyse Ökosystem v{ServiceConfig.VERSION} - Clean Architecture Frontend (FIXED)</p>
                </header>
                <nav class="nav-menu">
                    <a href="/dashboard" class="nav-item">📈 Dashboard</a>
                    <a href="/ki-vorhersage" class="nav-item">🤖 KI-Vorhersage</a>
                    <a href="/soll-ist-vergleich" class="nav-item">📊 SOLL-IST Vergleich</a>
                    <a href="/depot" class="nav-item">💼 Depot</a>
                    <a href="/prediction-averages" class="nav-item">📈 Vorhersage-Mittelwerte</a>
                    <a href="/system" class="nav-item">⚙️ System-Status</a>
                    <a href="/docs" class="nav-item">📚 API Docs</a>
                </nav>
                <main class="content">
                    {content}
                </main>
                <footer class="footer">
                    <p>🤖 Generated with [Claude Code](https://claude.ai/code) | Version {ServiceConfig.VERSION} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </footer>
            </div>
        </body>
        </html>
        """


# =============================================================================
# ROUTE HANDLERS (Single Responsibility per Endpoint)
# =============================================================================

@app.get("/", response_class=HTMLResponse, summary="Dashboard Homepage")
async def dashboard() -> str:
    """Dashboard Homepage Handler"""
    content = f"""
        <h2>🏠 Dashboard - Aktienanalyse Ökosystem</h2>
        <div class="alert alert-info">
            <h3>📊 System Status</h3>
            <p><span class="status-indicator status-active"></span><strong>Frontend Service:</strong> v{ServiceConfig.VERSION} - Konsolidierte Version mit wiederhergestellten Funktionen ✅</p>
            <p><span class="status-indicator status-active"></span><strong>SOLL-IST Vergleich:</strong> Wiederhergestellt ✅</p>
        </div>
        
        <div class="timeframe-grid">
            <div class="timeframe-card" onclick="window.location.href='/prognosen'">
                <div class="icon">📊</div>
                <h3>KI-Prognosen</h3>
                <p>Machine Learning Vorhersagen für verschiedene Zeiträume</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/prediction-averages'">
                <div class="icon">📈</div>
                <h3>Vorhersage-Mittelwerte</h3>
                <p>Mittelwerte über 1W, 1M, 3M und 12M Zeiträume</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/vergleichsanalyse'">
                <div class="icon">⚖️</div>
                <h3>SOLL-IST Vergleich</h3>
                <p>Vergleich zwischen Prognosen und tatsächlichen Ergebnissen</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/depot'">
                <div class="icon">💼</div>
                <h3>Depot-Analyse</h3>
                <p>Vollständige Portfolio-Übersicht und Performance</p>
            </div>
        </div>
        
        <div class="alert alert-warning">
            <h3>🚀 Recent Updates v8.0.1</h3>
            <ul>
                <li><strong>✅ FIXED:</strong> SOLL-IST Vergleichsanalyse mit CSV-Service Integration</li>
                <li><strong>Clean Code:</strong> SOLID Principles, Type Safety, Error Handling</li>
                <li><strong>Configuration:</strong> Environment-based URLs, keine Hard-coding</li>
            </ul>
        </div>
    """
    
    return HTMLTemplateService.generate_base_template("Dashboard", content)


@app.get("/prognosen", response_class=HTMLResponse, summary="KI-Prognosen Interface")
async def prognosen(
    timeframe: str = Query(default="1M", description="Zeitintervall für KI-Prognosen"),
    nav_timestamp: Optional[int] = Query(None, description="Navigation timestamp für Timeline-Navigation"),
    nav_direction: Optional[str] = Query(None, description="Navigation direction (previous/next)"),
    http_client: IHTTPClient = Depends(get_http_client)
) -> str:
    """KI-Prognosen Interface Handler mit Zeitraum-Navigation"""
    
    # Verwende die gleichen Timeframes wie SOLL-IST Vergleich
    if timeframe not in ServiceConfig.VERGLEICHSANALYSE_TIMEFRAMES:
        timeframe = "1M"  # Default fallback
    
    timeframe_info = ServiceConfig.VERGLEICHSANALYSE_TIMEFRAMES[timeframe]
    
    try:
        from datetime import datetime, timedelta
        start_time = datetime.now()
        
        # Navigation Periods berechnen (gleiche Logik wie SOLL-IST Vergleich)
        def get_prognosen_navigation_periods(current_timeframe: str, nav_ts: Optional[int] = None, nav_dir: Optional[str] = None):
            """Calculate previous and next time periods for KI-Prognosen"""
            timeframe_deltas = {
                "1W": timedelta(weeks=1),
                "1M": timedelta(days=30),
                "3M": timedelta(days=90)
            }
            
            # Use navigation timestamp if provided, otherwise current time
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
        
        # KI-Prognose Daten laden mit Timeline Navigation Parameters (KI-PROGNOSEN-NAV-002 Fix)
        prediction_url = ServiceConfig.get_prediction_url(timeframe, nav_timestamp, nav_direction)
        logger.info(f"Loading KI-Prognosen with navigation params from: {prediction_url}")
        logger.info(f"Navigation context: timestamp={nav_timestamp}, direction={nav_direction}")
        
        prediction_data = None
        try:
            # Erweiterte Exception-Logging für Debugging
            logger.info(f"CRITICAL DEBUG: Starting prediction request to {prediction_url}")
            prediction_response = await http_client.get(prediction_url)
            logger.info(f"CRITICAL DEBUG: Received response, type: {type(prediction_response).__name__}, size: {len(str(prediction_response))} bytes")
            
            # Detaillierte Response-Analyse
            if prediction_response:
                logger.info(f"CRITICAL DEBUG: Response keys: {list(prediction_response.keys()) if isinstance(prediction_response, dict) else 'not_dict'}")
                
                if isinstance(prediction_response, dict) and "predictions" in prediction_response:
                    prediction_data = prediction_response["predictions"]
                    logger.info(f"CRITICAL DEBUG: Successfully parsed {len(prediction_data)} predictions from dict")
                elif isinstance(prediction_response, list):
                    prediction_data = prediction_response
                    logger.info(f"CRITICAL DEBUG: Successfully parsed {len(prediction_data)} predictions from list")
                else:
                    logger.error(f"CRITICAL DEBUG: Unexpected response format - type: {type(prediction_response).__name__}, content: {str(prediction_response)[:200]}...")
                    # Log response structure for debugging
                    if hasattr(prediction_response, '__dict__'):
                        logger.error(f"CRITICAL DEBUG: Response attributes: {prediction_response.__dict__}")
            else:
                logger.error("CRITICAL DEBUG: Empty or None prediction_response received")
                
        except aiohttp.ClientError as e:
            logger.error(f"CRITICAL DEBUG: HTTP Client Error: {str(e)}")
            logger.error(f"CRITICAL DEBUG: Error type: {type(e).__name__}")
            import traceback
            logger.error(f"CRITICAL DEBUG: Traceback: {traceback.format_exc()}")
            prediction_data = None
        except asyncio.TimeoutError as e:
            logger.error(f"CRITICAL DEBUG: Timeout Error: {str(e)}")
            import traceback
            logger.error(f"CRITICAL DEBUG: Traceback: {traceback.format_exc()}")
            prediction_data = None
        except json.JSONDecodeError as e:
            logger.error(f"CRITICAL DEBUG: JSON Parse Error: {str(e)}")
            import traceback
            logger.error(f"CRITICAL DEBUG: Traceback: {traceback.format_exc()}")
            prediction_data = None
        except Exception as e:
            logger.error(f"CRITICAL DEBUG: Unexpected Exception in prediction loading: {str(e)}")
            logger.error(f"CRITICAL DEBUG: Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"CRITICAL DEBUG: Full traceback: {traceback.format_exc()}")
            prediction_data = None
        
        if prediction_data and isinstance(prediction_data, list) and len(prediction_data) > 0:
            # ERWEITERTE HEADERS: Durchschnittswerte-Spalten hinzugefügt
            enhanced_headers = [
                'Prognosedatum', 'Berechnungsdatum', 'Symbol', 
                'Erwartete Änderung', 'Durchschnitt', 'Abweichung', 
                'Konfidenz', 'Ø-Konfidenz', 'Datenbasis'
            ]
            
            # Prüfe auf Enhanced Predictions mit Durchschnittswerten
            has_averages_data = any(
                item.get('avg_prediction_percent') is not None 
                for item in prediction_data
            )
            averages_available = prediction_response.get('averages_available', False) if isinstance(prediction_response, dict) else has_averages_data
            
            # Sortiere nach erwartetem Gewinn (prediction_percent) absteigend
            def get_prediction_percent(item):
                prediction_percent_str = item.get('prediction_percent', '0%').replace('%', '')
                try:
                    return float(prediction_percent_str)
                except ValueError:
                    return 0
            
            # Sortiere und nehme die besten 15 Prognosen
            sorted_predictions = sorted(prediction_data, key=get_prediction_percent, reverse=True)[:15]
            
            table_rows = ""
            
            # Zeitraum-Mapping für Prognosedatum-Berechnung
            timeframe_days = {
                '1W': 7,
                '1M': 30, 
                '3M': 90
            }
            prediction_offset_days = timeframe_days.get(timeframe, 30)
            
            # Einheitliches Basis-Datum für alle Vorhersagen (FESTE BASIS für Konsistenz)
            from datetime import datetime, timedelta
            # Verwende aktuelles Datum um 12:00 Uhr als einheitliche Basis für alle Vorhersagen
            base_date = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
            unified_prediction_date = base_date + timedelta(days=prediction_offset_days)
            formatted_unified_prediction_date = unified_prediction_date.strftime('%d.%m.%Y')
            
            logger.info(f"UNIFIED DATE DEBUG: base_date={base_date.isoformat()}, offset_days={prediction_offset_days}, unified_date={formatted_unified_prediction_date}")
            
            for item in sorted_predictions:  # Top 15 Prognosen nach Gewinn sortiert
                symbol = item.get('symbol', 'N/A')
                
                # Aktuelle Vorhersage
                prediction_percent_str = item.get('prediction_percent', '0%').replace('%', '')
                try:
                    change_percent = float(prediction_percent_str)
                except ValueError:
                    change_percent = 0
                
                # NEUE FELDER: Durchschnittswerte
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
                
                # Relative Performance
                relative_performance_str = item.get('relative_performance', '')
                
                # Konfidenz-Daten
                confidence = item.get('confidence', 0) or 0
                avg_confidence_str = item.get('avg_confidence_percent', '')
                avg_confidence = None
                if avg_confidence_str and avg_confidence_str != 'None':
                    try:
                        avg_confidence = float(avg_confidence_str.replace('%', ''))
                    except ValueError:
                        avg_confidence = None
                
                # Datenbasis (Anzahl Vorhersagen für Durchschnitt)
                prediction_count = item.get('prediction_count', 0) or 0
                
                # Berechnungsdatum aus Backend-Timestamp formatieren
                calculation_date = item.get('timestamp', '')
                if calculation_date:
                    try:
                        # Parse ISO timestamp 
                        calculation_dt = datetime.fromisoformat(calculation_date.replace('Z', '+00:00'))
                        formatted_calculation_date = calculation_dt.strftime('%d.%m.%Y %H:%M')
                        
                        # Einheitliches Prognosedatum für alle Vorhersagen verwenden
                        formatted_prediction_date = formatted_unified_prediction_date
                        
                    except Exception:
                        formatted_calculation_date = calculation_date[:16]  # Fallback
                        formatted_prediction_date = formatted_unified_prediction_date  # Einheitliches Datum auch als Fallback
                else:
                    formatted_calculation_date = 'N/A'
                    formatted_prediction_date = formatted_unified_prediction_date  # Einheitliches Datum auch als Fallback
                
                # ERWEITERTE FARBKODIERUNG für Durchschnittswerte
                change_color = 'green' if change_percent > 0 else 'red'
                confidence_color = 'green' if confidence > 0.8 else 'orange' if confidence > 0.6 else 'red'
                
                # Durchschnittswerte-Farben
                avg_color = 'green' if avg_change_percent and avg_change_percent > 0 else 'red' if avg_change_percent and avg_change_percent < 0 else 'gray'
                deviation_color = 'green' if deviation_percent and abs(deviation_percent) < 2 else 'orange' if deviation_percent and abs(deviation_percent) < 5 else 'red'
                avg_confidence_color = 'green' if avg_confidence and avg_confidence > 80 else 'orange' if avg_confidence and avg_confidence > 60 else 'red'
                datenbasis_color = 'green' if prediction_count >= 10 else 'orange' if prediction_count >= 5 else 'red'
                
                # ERWEITERTE TABELLENZELLEN mit Durchschnittswerten
                avg_prediction_cell = f"""<span style="color: {avg_color};" title="Durchschnittliche Vorhersage">{avg_change_percent:+.2f}%</span>""" if avg_change_percent is not None else """<span style="color: gray;" title="Keine Durchschnittsdaten">N/A</span>"""
                
                deviation_cell = f"""<span style="color: {deviation_color};" title="Abweichung vom Durchschnitt">{deviation_percent:+.2f}%</span>""" if deviation_percent is not None else """<span style="color: gray;" title="Keine Abweichungsdaten">N/A</span>"""
                
                avg_confidence_cell = f"""<span style="color: {avg_confidence_color};" title="Durchschnittliche Konfidenz">{avg_confidence:.1f}%</span>""" if avg_confidence is not None else """<span style="color: gray;" title="Keine Konfidenz-Durchschnitt">N/A</span>"""
                
                datenbasis_cell = f"""<span style="color: {datenbasis_color};" title="Anzahl Vorhersagen für Durchschnitt">{prediction_count}</span>""" if prediction_count > 0 else """<span style="color: gray;">0</span>"""
                
                table_rows += f"""
                <tr class="{'prediction-with-averages' if avg_change_percent is not None else 'prediction-no-averages'}">
                    <td><strong>{formatted_prediction_date}</strong></td>
                    <td><small>{formatted_calculation_date}</small></td>
                    <td><strong>{symbol}</strong></td>
                    <td><span style="color: {change_color};" title="Aktuelle Vorhersage">{change_percent:+.2f}%</span></td>
                    <td>{avg_prediction_cell}</td>
                    <td>{deviation_cell}</td>
                    <td><span style="color: {confidence_color};" title="Aktuelle Konfidenz">{confidence*100:.1f}%</span></td>
                    <td>{avg_confidence_cell}</td>
                    <td>{datenbasis_cell}</td>
                </tr>
                """
            
            table_html = f"""
            <table class="table table-hover">
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
            # Erweiterte Fallback-Meldung mit Debug-Info
            debug_info = f"prediction_data={'✓' if prediction_data is not None else '✗'}, type={type(prediction_data).__name__}, len={len(prediction_data) if isinstance(prediction_data, list) else 'N/A'}"
            logger.warning(f"No predictions available: {debug_info}, backend_url={prediction_url}")
            
            table_html = f"""
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Keine Prognosen verfügbar</strong><br>
                Für den Zeitraum {timeframe_info['display_name']} sind derzeit keine KI-Prognosen verfügbar.
                <br><small style="color: #6c757d;">Debug: {debug_info}</small>
                <br><small style="color: #6c757d;">Backend: {prediction_url}</small>
            </div>
            """
        
        load_time = (datetime.now() - start_time).total_seconds()
        
        content = f"""
        <h2>📊 KI-Prognosen - Machine Learning Vorhersagen</h2>
        <div class="alert alert-info">
            <p><strong>Zeitraum:</strong> {timeframe_info['display_name']} | <strong>Beschreibung:</strong> {timeframe_info['description']}</p>
            <p><strong>4-Modell Ensemble:</strong> Technical LSTM + Sentiment XGBoost + Fundamental XGBoost + Meta LightGBM</p>
        </div>
        
        <!-- Timeline Navigation für KI-Prognosen -->
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
        <div class="btn-group">
            <button class="btn {'btn-primary' if timeframe == '1W' else 'btn-outline-primary'}" onclick="loadPrognosen('1W')">📊 1 Woche</button>
            <button class="btn {'btn-primary' if timeframe == '1M' else 'btn-outline-primary'}" onclick="loadPrognosen('1M')">📈 1 Monat</button>
            <button class="btn {'btn-primary' if timeframe == '3M' else 'btn-outline-primary'}" onclick="loadPrognosen('3M')">📊 3 Monate</button>
            <button class="btn {'btn-primary' if timeframe == '6M' else 'btn-outline-primary'}" onclick="loadPrognosen('6M')">📊 6 Monate</button>
            <button class="btn {'btn-primary' if timeframe == '12M' else 'btn-outline-primary'}" onclick="loadPrognosen('12M')">📈 12 Monate</button>
        </div>
        
        <!-- KI-Prognosen Tabelle mit Datum -->
        <h3>📊 KI-Prognosen - {timeframe_info['display_name']} <small>(Ladezeit: {load_time:.2f}s)</small></h3>
        {table_html}
        
        
        <script>
            function navigatePrognosen(direction, timeframe) {{
                // Calculate new date based on direction and timeframe
                var timeframeDays = {{
                    '1W': 7,
                    '1M': 30,
                    '3M': 90,
                    '6M': 180,
                    '12M': 365
                }};
                
                var daysToAdd = direction === 'next' ? timeframeDays[timeframe] : -timeframeDays[timeframe];
                var newDate = new Date();
                newDate.setDate(newDate.getDate() + daysToAdd);
                
                // Refresh page with navigation parameters
                var timestamp = Math.floor(newDate.getTime() / 1000);
                var currentUrl = new URL(window.location);
                currentUrl.searchParams.set('nav_timestamp', timestamp);
                currentUrl.searchParams.set('nav_direction', direction);
                
                window.location.href = currentUrl.toString();
            }}
            
            function loadPrognosen(timeframe) {{
                window.location.href = '/prognosen?timeframe=' + timeframe;
            }}
        </script>
        """
        
    except Exception as e:
        logger.error(f"CRITICAL DEBUG: MAIN EXCEPTION in prognosen() handler for {timeframe}: {str(e)}")
        logger.error(f"CRITICAL DEBUG: Main exception type: {type(e).__name__}")
        import traceback
        logger.error(f"CRITICAL DEBUG: Full main exception traceback: {traceback.format_exc()}")
        
        # Re-raise the exception to see the full stack trace instead of silent fallback
        raise HTTPException(
            status_code=500,
            detail=f"KI-Prognosen loading failed: {str(e)} (Type: {type(e).__name__})"
        )
        
        # Alternative: Keep old fallback behavior for graceful degradation
        content = f"""
        <h2>📊 KI-Prognosen - Machine Learning Vorhersagen</h2>
        <div class="alert alert-danger">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>CRITICAL ERROR beim Laden der Prognosen</strong><br>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><strong>Error Type:</strong> {type(e).__name__}</p>
            <p><strong>Backend URL:</strong> {ServiceConfig.get_prediction_url(timeframe)}</p>
        </div>
        """
    
    return HTMLTemplateService.generate_base_template("KI-Prognosen", content)


@app.get("/prognosen/{timeframe}", summary="Prognosen für spezifischen Zeitraum - Redirect")
async def prognosen_timeframe_redirect(
    timeframe: str,
    nav_timestamp: Optional[int] = Query(None),
    nav_direction: Optional[str] = Query(None)
):
    """Redirect alte Prognosen-URLs zur neuen Hauptroute"""
    from fastapi.responses import RedirectResponse
    
    # Build redirect URL with parameters
    redirect_url = f"/prognosen?timeframe={timeframe}"
    if nav_timestamp:
        redirect_url += f"&nav_timestamp={nav_timestamp}"
    if nav_direction:
        redirect_url += f"&nav_direction={nav_direction}"
    
    return RedirectResponse(url=redirect_url, status_code=301)



@app.get("/vergleichsanalyse", response_class=HTMLResponse, summary="SOLL-IST Vergleichsanalyse")
async def vergleichsanalyse(
    timeframe: str = Query(default="1M", description="Zeitintervall für SOLL-IST Vergleich"),
    nav_timestamp: Optional[int] = Query(None, description="Navigation timestamp für Timeline-Navigation"),
    nav_direction: Optional[str] = Query(None, description="Navigation direction (previous/next)"),
    http_client: IHTTPClient = Depends(get_http_client)
) -> str:
    """
    SOLL-IST Vergleichsanalyse Handler
    
    Single Responsibility: Nur SOLL-IST Vergleich
    Wiederhergestellte Funktionalität aus ursprünglichen Versionen
    """
    
    if timeframe not in ServiceConfig.VERGLEICHSANALYSE_TIMEFRAMES:
        timeframe = "1M"  # Default fallback
    
    timeframe_info = ServiceConfig.VERGLEICHSANALYSE_TIMEFRAMES[timeframe]
    
    try:
        start_time = datetime.now()
        
        # Calculate navigation periods first (needed for table data)
        def get_vergleichsanalyse_navigation_periods(current_timeframe: str, nav_ts: Optional[int] = None, nav_dir: Optional[str] = None):
            """Calculate previous and next time periods based on current timeframe and navigation state"""
            from datetime import datetime, timedelta
            
            timeframe_deltas = {
                "1W": timedelta(weeks=1),
                "1M": timedelta(days=30),
                "3M": timedelta(days=90)
            }
            
            # Use navigation timestamp if provided, otherwise current time
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
        
        nav_periods = get_vergleichsanalyse_navigation_periods(timeframe, nav_timestamp, nav_direction)
        
        # JSON-Daten von Prediction-Tracking Service laden
        api_url = timeframe_info["url"]
        logger.info(f"Loading SOLL-IST comparison from: {api_url}")
        
        comparison_data = await http_client.get(api_url)
        logger.info(f"Received comparison data: {comparison_data}")
        
        # Parse JSON zu HTML-Tabelle (korrigiertes Parsing)
        comparison_list = None
        if comparison_data:
            if isinstance(comparison_data, dict) and "comparisons" in comparison_data:
                comparison_list = comparison_data["comparisons"]
            elif isinstance(comparison_data, list):
                comparison_list = comparison_data
        
        if comparison_list and isinstance(comparison_list, list) and len(comparison_list) > 0:
            # JSON-Daten vorhanden - erweiterte Tabelle erstellen
            enhanced_headers = ['Vergleichsdatum', 'Symbol', 'SOLL-Performance', 'IST-Performance', 'Abweichung', 'Genauigkeit']
            
            table_rows = ""
            comparison_date = nav_periods['current']
            
            for item in comparison_list[:15]:  # Top 15 Vergleiche
                symbol = item.get('symbol', 'N/A')
                soll_performance = item.get('soll_performance', 0)
                ist_performance = item.get('ist_performance', 0) or 0
                deviation = item.get('deviation', 0) or 0
                accuracy = item.get('accuracy_percentage', 0) or 0
                
                # Farbkodierung für Performance-Werte
                soll_color = 'green' if soll_performance > 0 else 'red'
                ist_color = 'green' if ist_performance > 0 else 'red'
                deviation_color = 'green' if deviation > 0 else 'red'
                accuracy_color = 'green' if accuracy > 80 else 'orange' if accuracy > 60 else 'red'
                
                table_rows += f"""
                <tr>
                    <td><strong>{comparison_date}</strong></td>
                    <td><strong>{symbol}</strong></td>
                    <td><span style="color: {soll_color};">{soll_performance:+.2f}%</span></td>
                    <td><span style="color: {ist_color};">{ist_performance:+.2f}%</span></td>
                    <td><span style="color: {deviation_color};">{deviation:+.2f}%</span></td>
                    <td><span style="color: {accuracy_color};">{accuracy:.1f}%</span></td>
                </tr>
                """
            
            table_html = f"""
            <table class="table table-hover">
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
            # Keine JSON-Daten verfügbar
            table_html = f"""
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Keine Daten verfügbar</strong><br>
                Für den Zeitraum {timeframe_info['display_name']} sind derzeit keine SOLL-IST Vergleichsdaten verfügbar.
            </div>
            """
        
        load_time = (datetime.now() - start_time).total_seconds()
        
        content = f"""
        <h2>⚖️ SOLL-IST Vergleichsanalyse</h2>
        <div class="alert alert-info">
            <p><strong>Zeitraum:</strong> {timeframe_info['display_name']} | <strong>Beschreibung:</strong> {timeframe_info['description']}</p>
            <p><strong>Service:</strong> Vergleichsanalyse CSV-Service Integration</p>
        </div>
        
        <!-- Timeline Navigation für SOLL-IST Vergleich -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #28a745;">
            <button onclick="navigateVergleichsanalyse('previous', '{timeframe}')" 
                    style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px;">
                ⬅️ Zurück ({nav_periods['previous']})
            </button>
            
            <div style="text-align: center;">
                <strong>{nav_periods['nav_info']}</strong><br>
                <span style="color: #28a745; font-size: 16px; font-weight: bold;">{nav_periods['current']}</span>
                {f'<div style="margin-top: 5px;"><small style="color: #28a745;">✅ Navigation erfolgreich</small></div>' if nav_timestamp else ''}
            </div>
            
            <button onclick="navigateVergleichsanalyse('next', '{timeframe}')" 
                    style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px;">
                Vor ({nav_periods['next']}) ➡️
            </button>
        </div>
        
        <!-- Zeitintervall-Auswahl -->
        <h3>🔧 Zeitintervall auswählen</h3>
        <div class="btn-group">
            <button class="btn {'btn-primary' if timeframe == '1W' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('1W')">📊 1 Woche</button>
            <button class="btn {'btn-primary' if timeframe == '1M' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('1M')">📈 1 Monat</button>
            <button class="btn {'btn-primary' if timeframe == '3M' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('3M')">📊 3 Monate</button>
            <button class="btn {'btn-primary' if timeframe == '6M' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('6M')">📊 6 Monate</button>
            <button class="btn {'btn-primary' if timeframe == '12M' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('12M')">📈 12 Monate</button>
        </div>
        
        <!-- SOLL-IST Vergleichstabelle mit Datum -->
        <h3>📊 SOLL-IST Vergleich - {timeframe_info['display_name']} <small>(Ladezeit: {load_time:.2f}s)</small></h3>
        {table_html}
        
        <div class="alert alert-warning">
            <h3>💡 SOLL-IST Vergleich Erklärung</h3>
            <ul>
                <li><strong>SOLL:</strong> Ursprünglich prognostizierte Gewinnwerte</li>
                <li><strong>IST:</strong> Tatsächlich eingetretene Gewinnentwicklung</li>
                <li><strong>Abweichung:</strong> Differenz zwischen Prognose und Realität</li>
                <li><strong>Genauigkeit:</strong> Qualität der ML-Modell Vorhersagen</li>
            </ul>
        </div>
        
        <script>
            function navigateVergleichsanalyse(direction, timeframe) {{
                // Calculate new date based on direction and timeframe
                var timeframeDays = {{
                    '1W': 7,
                    '1M': 30,
                    '3M': 90,
                    '6M': 180,
                    '12M': 365
                }};
                
                var daysToAdd = direction === 'next' ? timeframeDays[timeframe] : -timeframeDays[timeframe];
                var newDate = new Date();
                newDate.setDate(newDate.getDate() + daysToAdd);
                
                // Refresh page with navigation parameters for SOLL-IST Vergleich
                var timestamp = Math.floor(newDate.getTime() / 1000);
                var currentUrl = new URL(window.location);
                currentUrl.searchParams.set('nav_timestamp', timestamp);
                currentUrl.searchParams.set('nav_direction', direction);
                
                window.location.href = currentUrl.toString();
            }}
        </script>
        """
        
    except Exception as e:
        # Berechne Navigation auch im Fehlerfall
        def get_error_navigation_periods(current_timeframe: str, nav_ts: Optional[int] = None, nav_dir: Optional[str] = None):
            from datetime import datetime, timedelta
            timeframe_deltas = {"1W": timedelta(weeks=1), "1M": timedelta(days=30), "3M": timedelta(days=90)}
            
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
                "nav_info": nav_info
            }
        
        error_nav_periods = get_error_navigation_periods(timeframe, nav_timestamp, nav_direction)
        logger.error(f"Error fetching vergleichsanalyse for {timeframe}: {str(e)}")
        
        content = f"""
        <h2>⚖️ SOLL-IST Vergleichsanalyse</h2>
        <div class="alert alert-error">
            <h3>⚠️ Service Temporarily Unavailable</h3>
            <p>Die SOLL-IST Vergleichsdaten können derzeit nicht abgerufen werden.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><strong>Service URL:</strong> {timeframe_info.get('url', 'N/A')}</p>
        </div>
        
        <!-- Timeline Navigation auch im Fehlerfall -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #dc3545;">
            <button onclick="navigateVergleichsanalyse('previous', '{timeframe}')" 
                    style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px;">
                ⬅️ Zurück ({error_nav_periods['previous']})
            </button>
            
            <div style="text-align: center;">
                <strong>{error_nav_periods['nav_info']}</strong><br>
                <span style="color: #dc3545; font-size: 16px; font-weight: bold;">{error_nav_periods['current']}</span>
                {f'<div style="margin-top: 5px;"><small style="color: #dc3545;">⚠️ Service nicht verfügbar</small></div>' if nav_timestamp else '<div style="margin-top: 5px;"><small style="color: #dc3545;">⚠️ Service nicht verfügbar</small></div>'}
            </div>
            
            <button onclick="navigateVergleichsanalyse('next', '{timeframe}')" 
                    style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 14px;">
                Vor ({error_nav_periods['next']}) ➡️
            </button>
        </div>
        
        <!-- Zeitintervall-Auswahl (immer verfügbar) -->
        <h3>🔧 Zeitintervall auswählen</h3>
        <div class="btn-group">
            <button class="btn {'btn-primary' if timeframe == '1W' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('1W')">📊 1 Woche</button>
            <button class="btn {'btn-primary' if timeframe == '1M' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('1M')">📈 1 Monat</button>
            <button class="btn {'btn-primary' if timeframe == '3M' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('3M')">📊 3 Monate</button>
            <button class="btn {'btn-primary' if timeframe == '6M' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('6M')">📊 6 Monate</button>
            <button class="btn {'btn-primary' if timeframe == '12M' else 'btn-outline-primary'}" onclick="loadVergleichsanalyse('12M')">📈 12 Monate</button>
        </div>
        
        <script>
            function navigateVergleichsanalyse(direction, timeframe) {{
                var timeframeDays = {{ '1W': 7, '1M': 30, '3M': 90, '6M': 180, '12M': 365 }};
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
        """
    
    return HTMLTemplateService.generate_base_template("SOLL-IST Vergleichsanalyse", content)


# =============================================================================
# MISSING NAVIGATION ROUTES (FRONTEND-NAV-001 Bug Fix)
# =============================================================================

@app.get("/ki-vorhersage", response_class=HTMLResponse, summary="KI-Vorhersage Route (Redirect zu Prognosen)")
async def ki_vorhersage():
    """KI-Vorhersage Route - Redirect zu /prognosen für Kompatibilität"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/prognosen?timeframe=1M", status_code=301)

@app.get("/dashboard", response_class=HTMLResponse, summary="Dashboard Route (Direct Content)")
async def dashboard_direct() -> str:
    """Dashboard Route - Direct Content (Not Redirect)"""
    content = f"""
        <h2>📈 Dashboard - Aktienanalyse Ökosystem</h2>
        <div class="alert alert-info">
            <h3>📊 System Status</h3>
            <p><span class="status-indicator status-active"></span><strong>Frontend Service:</strong> v{ServiceConfig.VERSION} - Navigation Fix Applied ✅</p>
            <p><span class="status-indicator status-active"></span><strong>FRONTEND-NAV-001:</strong> Behoben ✅</p>
        </div>
        
        <div class="timeframe-grid">
            <div class="timeframe-card" onclick="window.location.href='/prognosen'">
                <div class="icon">📊</div>
                <h3>KI-Prognosen</h3>
                <p>Machine Learning Vorhersagen für verschiedene Zeiträume</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/prediction-averages'">
                <div class="icon">📈</div>
                <h3>Vorhersage-Mittelwerte</h3>
                <p>Mittelwerte über 1W, 1M, 3M und 12M Zeiträume</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/vergleichsanalyse'">
                <div class="icon">⚖️</div>
                <h3>SOLL-IST Vergleich</h3>
                <p>Vergleich zwischen Prognosen und tatsächlichen Ergebnissen</p>
            </div>
            <div class="timeframe-card" onclick="window.location.href='/depot'">
                <div class="icon">💼</div>
                <h3>Depot-Analyse</h3>
                <p>Vollständige Portfolio-Übersicht und Performance</p>
            </div>
        </div>
        
        <div class="alert alert-warning">
            <h3>🚀 FRONTEND-NAV-001 Fix Applied</h3>
            <ul>
                <li><strong>✅ FIXED:</strong> Dashboard Route gibt direkten Content zurück</li>
                <li><strong>✅ FIXED:</strong> Alle 4 Navigation-Routes funktional</li>
                <li><strong>✅ FIXED:</strong> Keine 404 Fehler mehr</li>
            </ul>
        </div>
    """
    
    return HTMLTemplateService.generate_base_template("Dashboard", content)

@app.get("/soll-ist-vergleich", response_class=HTMLResponse, summary="SOLL-IST Vergleich Route (Redirect zu Vergleichsanalyse)")
async def soll_ist_vergleich():
    """SOLL-IST Vergleich Route - Redirect zu /vergleichsanalyse für Kompatibilität"""
    from fastapi.responses import RedirectResponse  
    return RedirectResponse(url="/vergleichsanalyse?timeframe=1M", status_code=301)

@app.get("/depot", response_class=HTMLResponse, summary="Depot-Analyse Interface")
async def depot() -> str:
    """Depot-Analyse Interface Handler"""
    content = """
        <h2>💼 Depot-Analyse - Portfolio-Übersicht</h2>
        <div class="alert alert-info">
            <p><strong>Portfolio-Management:</strong> Vollständige Übersicht Ihrer Aktienpositionen und Performance-Metriken</p>
        </div>
        
        <div class="timeframe-grid">
            <div class="timeframe-card">
                <div class="icon">💼</div>
                <h3>Aktuelle Positionen</h3>
                <p>Übersicht aller gehaltenen Aktien</p>
            </div>
            <div class="timeframe-card">
                <div class="icon">📈</div>
                <h3>Performance</h3>
                <p>Gewinn/Verlust und Rendite-Analyse</p>
            </div>
            <div class="timeframe-card">
                <div class="icon">📊</div>
                <h3>Diversifikation</h3>
                <p>Branchen- und Länder-Verteilung</p>
            </div>
            <div class="timeframe-card">
                <div class="icon">⚖️</div>
                <h3>Risiko-Analyse</h3>
                <p>Volatilität und Risiko-Assessment</p>
            </div>
        </div>
        
        <div class="alert alert-warning">
            <h3>💡 Depot-Funktionen</h3>
            <p>Hier werden zukünftig Ihre Aktienpositionen, Performance-Übersichten und Portfolio-Analysen angezeigt.</p>
        </div>
    """
    
    return HTMLTemplateService.generate_base_template("Depot-Analyse", content)


@app.get("/prediction-averages", response_class=HTMLResponse, summary="Enhanced Prediction Averages Interface")
async def prediction_averages(
    symbol: Optional[str] = Query(None, description="Spezifisches Symbol für Mittelwerte"),
    http_client: IHTTPClient = Depends(get_http_client)
) -> str:
    """Enhanced Prediction Averages Interface Handler"""
    
    try:
        start_time = datetime.now()
        
        # Verfügbare Symbole laden
        symbols_url = f"{ServiceConfig.ENHANCED_PREDICTIONS_AVERAGES_URL}/prediction-averages"
        logger.info(f"Loading available symbols from: {symbols_url}")
        
        symbols_response = await http_client.get(symbols_url)
        logger.info(f"Received symbols response: {symbols_response}")
        
        symbols_list = []
        if symbols_response and "symbols" in symbols_response:
            symbols_list = symbols_response["symbols"]
        
        # Spezifische Symbol-Daten laden wenn Symbol angegeben
        symbol_data = None
        if symbol and symbol.strip():
            symbol = symbol.strip().upper()
            symbol_url = f"{ServiceConfig.ENHANCED_PREDICTIONS_AVERAGES_URL}/prediction-averages/{symbol}"
            logger.info(f"Loading symbol data from: {symbol_url}")
            
            try:
                symbol_data = await http_client.get(symbol_url)
                logger.info(f"Received symbol data: {symbol_data}")
            except Exception as e:
                logger.warning(f"Error loading symbol {symbol}: {str(e)}")
                symbol_data = None
        
        # HTML Content generieren
        if symbol_data and symbol_data.get("averages"):
            # Symbol-spezifische Ansicht
            averages = symbol_data["averages"]
            last_updated = symbol_data.get("last_updated", "N/A")
            
            # Parse last_updated datetime
            try:
                from datetime import datetime
                if isinstance(last_updated, str) and "T" in last_updated:
                    updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    formatted_date = updated_dt.strftime('%d.%m.%Y %H:%M:%S UTC')
                else:
                    formatted_date = str(last_updated)[:19]
            except:
                formatted_date = str(last_updated)
            
            # Einzelsymbol-Tabelle
            symbol_rows = ""
            timeframes = ["1W", "1M", "3M", "12M"]
            
            for tf in timeframes:
                if tf in averages:
                    avg_value = averages[tf]
                    color = 'green' if avg_value > 0 else 'red' if avg_value < 0 else 'gray'
                    symbol_rows += f"""
                    <tr>
                        <td><strong>{tf}</strong></td>
                        <td>{tf.replace('W', ' Woche').replace('M', ' Monat').replace('3 Monat', '3 Monate').replace('12 Monat', '12 Monate')}</td>
                        <td><span style="color: {color}; font-weight: bold;">{avg_value:.2f}</span></td>
                        <td><small>{formatted_date}</small></td>
                    </tr>
                    """
            
            symbol_table = f"""
            <div class="alert alert-info">
                <h3>📈 Vorhersage-Mittelwerte für {symbol}</h3>
                <p><strong>Letztes Update:</strong> {formatted_date}</p>
            </div>
            
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Zeitraum</th>
                        <th>Beschreibung</th>
                        <th>Mittelwert</th>
                        <th>Berechnet</th>
                    </tr>
                </thead>
                <tbody>
                    {symbol_rows}
                </tbody>
            </table>
            
            <div style="margin: 20px 0;">
                <a href="/prediction-averages" class="btn btn-primary">🔙 Zurück zur Übersicht</a>
            </div>
            """
        
        else:
            # Übersichts-Ansicht mit allen verfügbaren Symbolen
            if symbols_list and len(symbols_list) > 0:
                overview_rows = ""
                
                for item in symbols_list:
                    symbol_name = item.get("symbol", "N/A")
                    last_updated = item.get("last_updated", "N/A")
                    
                    # Format last updated
                    try:
                        if isinstance(last_updated, str) and "T" in last_updated:
                            updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            formatted_date = updated_dt.strftime('%d.%m.%Y %H:%M')
                        else:
                            formatted_date = str(last_updated)[:16]
                    except:
                        formatted_date = "N/A"
                    
                    overview_rows += f"""
                    <tr onclick="window.location.href='/prediction-averages?symbol={symbol_name}'" style="cursor: pointer;">
                        <td><strong>{symbol_name}</strong></td>
                        <td><small>{formatted_date}</small></td>
                        <td><span style="color: #007bff;">📈 Ansehen</span></td>
                    </tr>
                    """
                
                symbol_table = f"""
                <div class="alert alert-info">
                    <h3>📊 Verfügbare Vorhersage-Mittelwerte</h3>
                    <p><strong>Anzahl Symbole:</strong> {len(symbols_list)}</p>
                </div>
                
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Letztes Update</th>
                            <th>Aktion</th>
                        </tr>
                    </thead>
                    <tbody>
                        {overview_rows}
                    </tbody>
                </table>
                """
            else:
                symbol_table = """
                <div class="alert alert-warning">
                    <h3>⚠️ Keine Daten verfügbar</h3>
                    <p>Derzeit sind keine Vorhersage-Mittelwerte verfügbar.</p>
                </div>
                """
        
        load_time = (datetime.now() - start_time).total_seconds()
        
        content = f"""
        <h2>📈 Enhanced Predictions Averages - Vorhersage-Mittelwerte</h2>
        <div class="alert alert-info">
            <p><strong>Service:</strong> Enhanced Predictions Averages Service auf Port 8087</p>
            <p><strong>Zeiträume:</strong> 1 Woche, 1 Monat, 3 Monate, 12 Monate</p>
            <p><strong>Ladezeit:</strong> {load_time:.2f}s</p>
        </div>
        
        {symbol_table}
        
        <div class="alert alert-info">
            <h3>💡 Enhanced Predictions Averages Erklärung</h3>
            <ul>
                <li><strong>1W:</strong> Mittelwert der Vorhersagen über 1 Woche</li>
                <li><strong>1M:</strong> Mittelwert der Vorhersagen über 1 Monat</li>
                <li><strong>3M:</strong> Mittelwert der Vorhersagen über 3 Monate</li>
                <li><strong>12M:</strong> Mittelwert der Vorhersagen über 12 Monate</li>
            </ul>
        </div>
        """
        
    except Exception as e:
        logger.error(f"Error loading prediction averages: {str(e)}")
        content = f"""
        <h2>📈 Enhanced Predictions Averages - Vorhersage-Mittelwerte</h2>
        <div class="alert alert-error">
            <h3>⚠️ Service nicht verfügbar</h3>
            <p>Die Enhanced Predictions Averages können derzeit nicht abgerufen werden.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><strong>Service URL:</strong> {ServiceConfig.ENHANCED_PREDICTIONS_AVERAGES_URL}</p>
        </div>
        """
    
    return HTMLTemplateService.generate_base_template("Vorhersage-Mittelwerte", content)


@app.get("/system", response_class=HTMLResponse, summary="System Status & Monitoring")
async def system_status(http_client: IHTTPClient = Depends(get_http_client)) -> str:
    """System Status & Monitoring Handler"""
    services = [
        {"name": "Data Processing", "url": ServiceConfig.DATA_PROCESSING_URL, "port": "8017"},
        {"name": "ML Analytics", "url": ServiceConfig.ML_ANALYTICS_URL, "port": "8021"},
        {"name": "CSV Service", "url": ServiceConfig.CSV_SERVICE_URL, "port": "8030"},
        {"name": "Vergleichsanalyse Service", "url": ServiceConfig.VERGLEICHSANALYSE_SERVICE_URL, "port": "8019"},
        {"name": "Enhanced Predictions Averages", "url": ServiceConfig.ENHANCED_PREDICTIONS_AVERAGES_URL, "port": "8087"},
        {"name": "Event Bus", "url": ServiceConfig.EVENT_BUS_URL, "port": "8014"},
        {"name": "Intelligent Core", "url": ServiceConfig.INTELLIGENT_CORE_URL, "port": "8011"},
        {"name": "Broker Gateway", "url": ServiceConfig.BROKER_GATEWAY_URL, "port": "8020"},
        {"name": "System Monitoring", "url": ServiceConfig.SYSTEM_MONITORING_URL, "port": "8040"},
    ]
    
    service_status_rows = ""
    healthy_count = 0
    
    for service in services:
        try:
            health_url = f"{service['url']}/health"
            await http_client.get(health_url)
            status = "✅ Active"
            status_class = "status-active"
            healthy_count += 1
        except Exception:
            status = "❌ Inactive"
            status_class = "status-inactive"
        
        service_status_rows += f"""
            <tr>
                <td>{service['name']}</td>
                <td><span class="status-indicator {status_class}"></span>{status}</td>
                <td>{service['url']}</td>
                <td>:{service['port']}</td>
            </tr>
        """
    
    system_health = "🟢 Excellent" if healthy_count >= 6 else "🟡 Good" if healthy_count >= 4 else "🔴 Critical"
    
    content = f"""
        <h2>⚙️ System Status & Monitoring</h2>
        <div class="alert alert-info">
            <h3>📊 Overall Health: {system_health}</h3>
            <p><strong>Services Status:</strong> {healthy_count}/{len(services)} Services Online</p>
            <p><strong>Frontend Version:</strong> v{ServiceConfig.VERSION} - Fixed Version mit wiederhergestellten Funktionen</p>
        </div>
        
        <h3>🔧 Service Status</h3>
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Status</th>
                    <th>URL</th>
                    <th>Port</th>
                </tr>
            </thead>
            <tbody>
                {service_status_rows}
            </tbody>
        </table>
        
        <div class="alert alert-warning">
            <h3>🚀 Code Quality Status v8.0.1</h3>
            <ul>
                <li><strong>✅ FIXED:</strong> SOLL-IST Vergleichsanalyse mit CSV-Service Integration</li>
                <li><strong>Frontend Consolidation:</strong> 13 → 1 Version (v8.0.1)</li>
                <li><strong>Clean Architecture:</strong> SOLID Principles implemented</li>
                <li><strong>Configuration:</strong> Environment-based, no hard-coding</li>
            </ul>
        </div>
    """
    
    return HTMLTemplateService.generate_base_template("System Status", content)


# =============================================================================
# API ENDPOINTS (für Legacy-Kompatibilität)
# =============================================================================



@app.get("/api/content/vergleichsanalyse", response_class=HTMLResponse, summary="Vergleichsanalyse-Content API") 
async def get_vergleichsanalyse_content(
    timeframe: str = Query(default="1M", description="Zeitintervall für SOLL-IST Vergleich"),
    http_client: IHTTPClient = Depends(get_http_client)
) -> str:
    """
    Vergleichsanalyse-Content API für Legacy-Kompatibilität
    Wiederhergestellte Funktionalität aus ursprünglichen Versionen
    """
    return await vergleichsanalyse(timeframe=timeframe, http_client=http_client)


@app.get("/health", response_class=JSONResponse, summary="Health Check Endpoint")
async def health_check() -> Dict[str, Any]:
    """Health Check Endpoint für Load Balancers"""
    return {
        "status": "healthy",
        "service": ServiceConfig.SERVICE_NAME,
        "version": ServiceConfig.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "consolidation_status": "13_versions_consolidated_to_1",
        "architecture": "clean_architecture_solid_principles",
        "fixes_applied": "soll_ist_vergleich_restored"
    }


# =============================================================================
# API ENDPOINTS FOR TIMELINE NAVIGATION (KI-PROGNOSEN-NAV-002 Fix)
# =============================================================================

@app.get("/api/timeline/navigation", response_class=JSONResponse, summary="Timeline Navigation API")
async def api_timeline_navigation(
    timeframe: str = Query(default="1M", description="Zeitintervall für Timeline Navigation"),
    nav_timestamp: Optional[int] = Query(None, description="Navigation timestamp"),
    nav_direction: Optional[str] = Query(None, description="Navigation direction (prev, next, previous)"),
    http_client: IHTTPClient = Depends(get_http_client)
) -> Dict[str, Any]:
    """
    API Endpoint für Timeline Navigation
    
    KI-PROGNOSEN-NAV-002 Fix: Frontend unterstützt vollständig nav_timestamp und nav_direction Parameter
    """
    try:
        logger.info(f"Timeline Navigation API called: timeframe={timeframe}, nav_timestamp={nav_timestamp}, nav_direction={nav_direction}")
        
        # Timeline Navigation URL mit allen Parametern
        timeline_url = ServiceConfig.get_timeline_navigation_url(timeframe, nav_timestamp, nav_direction)
        logger.info(f"Forwarding to backend: {timeline_url}")
        
        # Backend-Aufruf
        timeline_response = await http_client.get(timeline_url)
        
        if timeline_response and isinstance(timeline_response, dict):
            # Enhanced response mit Frontend-spezifischen Metadaten
            response_data = {
                **timeline_response,
                "frontend_support": "full_nav_params_forwarding",
                "api_version": "v8.0.1",
                "navigation_parameters_received": {
                    "timeframe": timeframe,
                    "nav_timestamp": nav_timestamp,
                    "nav_direction": nav_direction
                },
                "backend_url": timeline_url,
                "processed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Timeline navigation successful: {len(timeline_response.get('predictions', []))} predictions returned")
            return response_data
        else:
            logger.error(f"Invalid backend response: {timeline_response}")
            raise HTTPException(status_code=502, detail="Invalid backend response")
            
    except Exception as e:
        logger.error(f"Timeline navigation API error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Timeline Navigation API Error",
                "message": str(e),
                "navigation_params": {
                    "timeframe": timeframe,
                    "nav_timestamp": nav_timestamp,
                    "nav_direction": nav_direction
                }
            }
        )


@app.get("/api/prognosen/navigation", response_class=JSONResponse, summary="Prognosen Navigation API")
async def api_prognosen_navigation(
    timeframe: str = Query(default="1M", description="Zeitintervall"),
    nav_timestamp: Optional[int] = Query(None, description="Navigation timestamp"),
    nav_direction: Optional[str] = Query(None, description="Navigation direction"),
    http_client: IHTTPClient = Depends(get_http_client)
) -> Dict[str, Any]:
    """
    API Endpoint für Prognosen mit Navigation Support
    
    Simplere Version für direkte Prognosen-Abfragen mit Navigation
    """
    try:
        # Standard prediction URL mit Navigation Parameters
        prediction_url = ServiceConfig.get_prediction_url(timeframe, nav_timestamp, nav_direction)
        logger.info(f"Prognosen Navigation API: {prediction_url}")
        
        # Backend-Aufruf
        prediction_response = await http_client.get(prediction_url)
        
        if prediction_response and isinstance(prediction_response, dict):
            return {
                **prediction_response,
                "api_type": "prognosen_navigation",
                "navigation_forwarded": nav_timestamp is not None or nav_direction is not None
            }
        else:
            raise HTTPException(status_code=502, detail="Backend response error")
            
    except Exception as e:
        logger.error(f"Prognosen navigation API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")


# =============================================================================
# APPLICATION STARTUP
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Application Startup Event Handler"""
    logger.info(f"🚀 Starting {ServiceConfig.SERVICE_NAME} v{ServiceConfig.VERSION}")
    logger.info(f"📊 Frontend Service Consolidated: 13 → 1 Versions")
    logger.info(f"✅ FIXED: SOLL-IST Vergleichsanalyse wiederhergestellt")
    logger.info(f"🔄 FIXED: KI-PROGNOSEN-NAV-002 Timeline Navigation Support")
    logger.info(f"🏗️ Clean Architecture: SOLID Principles Implemented")
    logger.info(f"⚙️ Configuration: Environment-based URLs")
    logger.info(f"🔧 Server: {ServiceConfig.HOST}:{ServiceConfig.PORT}")
    logger.info("📋 Available Endpoints:")
    logger.info("   📊 /prognosen - KI-Prognosen Interface (nav_timestamp/nav_direction support)")
    logger.info("   📈 /vergleichsanalyse - SOLL-IST Vergleichsanalyse")
    logger.info("   🔄 /api/timeline/navigation - Timeline Navigation API")
    logger.info("   📊 /api/prognosen/navigation - Prognosen Navigation API")
    logger.info("   🏥 /health - Service Status")


@app.on_event("shutdown")
async def shutdown_event():
    """Application Shutdown Event Handler"""
    logger.info(f"🛑 Shutting down {ServiceConfig.SERVICE_NAME} v{ServiceConfig.VERSION}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info(f"🚀 Launching {ServiceConfig.SERVICE_NAME} v{ServiceConfig.VERSION}")
    logger.info("📋 Code Quality Improvements Applied:")
    logger.info("   ✅ Frontend Service Consolidation (13 → 1)")
    logger.info("   ✅ FIXED: SOLL-IST Vergleichsanalyse wiederhergestellt") 
    logger.info("   ✅ SOLID Principles Implementation")
    logger.info("   ✅ Type Safety & Error Handling")
    logger.info("   ✅ Environment-based Configuration")
    logger.info("   ✅ Dependency Injection Pattern")
    logger.info("   ✅ Single Responsibility per Endpoint")
    
    uvicorn.run(
        app, 
        host=ServiceConfig.HOST, 
        port=ServiceConfig.PORT,
        log_level=ServiceConfig.LOG_LEVEL.lower(),
        access_log=True
    )