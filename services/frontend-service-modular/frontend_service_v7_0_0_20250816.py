#!/usr/bin/env python3
"""
Frontend Service v7.0.0 - Clean Architecture Implementation
Vollständige GUI mit allen Endpunkten nach Projektvorgaben

Code-Qualität: HÖCHSTE PRIORITÄT
- Clean Code Principles
- SOLID Architecture
- Single Responsibility per Endpoint
- Error Handling & Resilience
- Type Safety & Documentation
"""

import uvicorn
import aiohttp
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application Configuration
class ServiceConfig:
    """Service Configuration Constants"""
    VERSION = "7.0.0"
    SERVICE_NAME = "Aktienanalyse Frontend Service"
    PORT = 8080
    HOST = "0.0.0.0"
    
    # Backend Service URLs
    DATA_PROCESSING_URL = "http://localhost:8017"
    CSV_SERVICE_URL = "http://localhost:8019"
    PREDICTION_TRACKING_URL = "http://localhost:8018"
    
    # Timeframe Configuration
    TIMEFRAMES = {
        "1W": {"display_name": "1 Woche", "days": 7, "icon": "📊"},
        "1M": {"display_name": "1 Monat", "days": 30, "icon": "📈"},
        "3M": {"display_name": "3 Monate", "days": 90, "icon": "📊"},
        "6M": {"display_name": "6 Monate", "days": 180, "icon": "📉"},
        "1Y": {"display_name": "1 Jahr", "days": 365, "icon": "📊"}
    }

# FastAPI Application Setup
app = FastAPI(
    title=ServiceConfig.SERVICE_NAME,
    version=ServiceConfig.VERSION,
    description="Enhanced Frontend mit Sidebar-Navigation und CSV-Integration"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Private environment - relaxed CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DataService:
    """Service für Backend-API Calls mit Error Handling"""
    
    @staticmethod
    async def fetch_csv_data(url: str, timeout: int = 10) -> Optional[str]:
        """Fetch CSV data from backend service with error handling"""
        try:
            logger.info(f"Fetching CSV data from URL: {url}")
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.text()
                        logger.info(f"Received data from {url}: {len(data)} characters")
                        # Handle JSON-wrapped CSV
                        if data.startswith('"') and data.endswith('"'):
                            data = data[1:-1].replace('\\n', '\n')
                        # Log first line for debugging
                        first_line = data.split('\n')[0] if data else "No data"
                        logger.info(f"First line of CSV data: {first_line}")
                        return data
                    else:
                        logger.warning(f"Backend service returned status {response.status} for {url}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching data from {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching data from {url}: {e}")
            return None
    
    @staticmethod
    async def check_service_health(url: str) -> Dict[str, Any]:
        """Check backend service health"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"status": "healthy", "data": data}
                    else:
                        return {"status": "unhealthy", "code": response.status}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class HTMLRenderer:
    """HTML Rendering mit Bootstrap 5 und FontAwesome"""
    
    @staticmethod
    def render_base_layout(content: str, title: str = "Dashboard") -> str:
        """Base HTML Layout mit Sidebar Navigation"""
        return f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - Aktienanalyse System</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
            <style>
                .sidebar {{
                    min-height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .content-area {{
                    min-height: 100vh;
                    background-color: #f8f9fa;
                }}
                .nav-link {{
                    color: rgba(255,255,255,0.8) !important;
                    transition: all 0.3s ease;
                }}
                .nav-link:hover, .nav-link.active {{
                    color: white !important;
                    background-color: rgba(255,255,255,0.1);
                    border-radius: 8px;
                }}
                .card {{
                    border: none;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    transition: transform 0.2s ease;
                }}
                .card:hover {{
                    transform: translateY(-2px);
                }}
                .status-card {{
                    border-left: 4px solid;
                }}
                .status-healthy {{ border-left-color: #28a745; }}
                .status-warning {{ border-left-color: #ffc107; }}
                .status-error {{ border-left-color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <div class="row">
                    <!-- Sidebar Navigation -->
                    <div class="col-md-3 col-lg-2 px-0">
                        <div class="sidebar p-3">
                            <h4 class="text-white mb-4">
                                <i class="fas fa-chart-line"></i> 
                                Aktienanalyse
                            </h4>
                            <nav class="nav flex-column">
                                <a class="nav-link active" href="#" onclick="loadSection('dashboard')">
                                    <i class="fas fa-tachometer-alt"></i> Dashboard
                                </a>
                                <a class="nav-link" href="#" onclick="loadSection('analysis')">
                                    <i class="fas fa-chart-bar"></i> Analyse
                                </a>
                                <a class="nav-link" href="#" onclick="loadSection('vergleichsanalyse')">
                                    <i class="fas fa-balance-scale"></i> Soll-Ist Vergleich
                                </a>
                                <a class="nav-link" href="#" onclick="loadSection('events')">
                                    <i class="fas fa-broadcast-tower"></i> Event Bus
                                </a>
                                <a class="nav-link" href="#" onclick="loadSection('monitoring')">
                                    <i class="fas fa-heartbeat"></i> Monitoring
                                </a>
                                <a class="nav-link" href="#" onclick="loadSection('api')">
                                    <i class="fas fa-code"></i> API Docs
                                </a>
                            </nav>
                        </div>
                    </div>
                    
                    <!-- Main Content Area -->
                    <div class="col-md-9 col-lg-10">
                        <div class="content-area p-4">
                            <div id="main-content">
                                {content}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                async function loadSection(section) {{
                    try {{
                        // Update active navigation
                        document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
                        event.target.classList.add('active');
                        
                        // Load content
                        const response = await fetch(`/api/content/${{section}}`);
                        const content = await response.text();
                        document.getElementById('main-content').innerHTML = content;
                    }} catch (error) {{
                        console.error('Error loading section:', error);
                        document.getElementById('main-content').innerHTML = 
                            '<div class="alert alert-danger">Fehler beim Laden des Inhalts</div>';
                    }}
                }}
                
                // Auto-refresh für Dashboard
                if (window.location.hash === '#dashboard' || window.location.hash === '') {{
                    setInterval(() => {{
                        if (document.querySelector('.nav-link.active')?.textContent.includes('Dashboard')) {{
                            loadSection('dashboard');
                        }}
                    }}, 30000); // 30 Sekunden
                }}
            </script>
        </body>
        </html>
        """
    
    @staticmethod
    def render_csv_table(csv_data: str, title: str) -> str:
        """Render CSV data as HTML table"""
        if not csv_data:
            return """
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Keine Daten verfügbar</strong>
            </div>
            """
        
        lines = csv_data.strip().split('\n')
        if len(lines) <= 1:
            return """
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i>
                <strong>Keine Datensätze gefunden</strong>
            </div>
            """
        
        # Parse CSV
        headers = lines[0].split(',')
        rows = [line.split(',') for line in lines[1:] if line.strip()]
        
        table_html = f"""
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-table"></i> {title}
                </h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead class="table-dark">
                            <tr>
        """
        
        for header in headers:
            table_html += f"<th>{header.strip()}</th>"
        
        table_html += "</tr></thead><tbody>"
        
        for row in rows:
            table_html += "<tr>"
            for cell in row:
                # Style positive/negative values
                cell_content = cell.strip()
                if cell_content.startswith('+'):
                    table_html += f'<td><span class="text-success">{cell_content}</span></td>'
                elif cell_content.startswith('-'):
                    table_html += f'<td><span class="text-danger">{cell_content}</span></td>'
                else:
                    table_html += f'<td>{cell_content}</td>'
            table_html += "</tr>"
        
        table_html += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
        
        return table_html

# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - Hauptseite mit Dashboard"""
    dashboard_content = await get_dashboard_content()
    return HTMLRenderer.render_base_layout(dashboard_content, "Dashboard")

@app.get("/api/content/dashboard", response_class=HTMLResponse)
async def get_dashboard_content():
    """Dashboard Content mit Live System-Metriken"""
    
    # Check all backend services
    services = {
        "Data Processing": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL
    }
    
    service_status = {}
    for name, url in services.items():
        health = await DataService.check_service_health(url)
        service_status[name] = health
    
    # Service status cards
    status_cards = ""
    for service_name, status in service_status.items():
        if status["status"] == "healthy":
            card_class = "status-healthy"
            icon = "fas fa-check-circle text-success"
            status_text = "Online"
        elif status["status"] == "unhealthy":
            card_class = "status-warning"
            icon = "fas fa-exclamation-triangle text-warning"
            status_text = f"HTTP {status.get('code', 'Error')}"
        else:
            card_class = "status-error"
            icon = "fas fa-times-circle text-danger"
            status_text = "Offline"
        
        status_cards += f"""
        <div class="col-md-4 mb-3">
            <div class="card status-card {card_class}">
                <div class="card-body">
                    <h6 class="card-title">
                        <i class="{icon}"></i> {service_name}
                    </h6>
                    <p class="card-text">Status: <strong>{status_text}</strong></p>
                    <small class="text-muted">Letzter Check: {datetime.now().strftime('%H:%M:%S')}</small>
                </div>
            </div>
        </div>
        """
    
    return f"""
    <div class="container-fluid">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="mb-3">
                    <i class="fas fa-tachometer-alt text-primary"></i> 
                    System Dashboard
                </h1>
                <p class="text-muted">Live-Status aller Backend-Services und System-Metriken</p>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-12">
                <h3>Service Status</h3>
            </div>
            {status_cards}
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-info-circle"></i> System Information</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Frontend Version:</strong> {ServiceConfig.VERSION}</p>
                        <p><strong>Aktive Services:</strong> {len([s for s in service_status.values() if s["status"] == "healthy"])}/{len(service_status)}</p>
                        <p><strong>Letztes Update:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-external-link-alt"></i> Quick Actions</h5>
                    </div>
                    <div class="card-body">
                        <button class="btn btn-primary me-2" onclick="loadSection('vergleichsanalyse')">
                            <i class="fas fa-balance-scale"></i> Soll-Ist Vergleich
                        </button>
                        <button class="btn btn-info me-2" onclick="loadSection('analysis')">
                            <i class="fas fa-chart-bar"></i> Analyse
                        </button>
                        <button class="btn btn-success" onclick="window.location.reload()">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

@app.get("/api/content/vergleichsanalyse", response_class=HTMLResponse)
async def get_vergleichsanalyse_content(timeframe: str = Query(default="1M")):
    """SOLL-IST Vergleichsanalyse mit Zeitraum-Auswahl"""
    
    if timeframe not in ServiceConfig.TIMEFRAMES:
        timeframe = "1M"
    
    timeframe_info = ServiceConfig.TIMEFRAMES[timeframe]
    
    # Fetch CSV data
    csv_url = f"{ServiceConfig.CSV_SERVICE_URL}/api/v1/vergleichsanalyse/csv?timeframe={timeframe}"
    csv_data = await DataService.fetch_csv_data(csv_url)
    
    # Timeframe buttons
    timeframe_buttons = ""
    for tf, info in ServiceConfig.TIMEFRAMES.items():
        active_class = "btn-primary" if tf == timeframe else "btn-outline-primary"
        timeframe_buttons += f"""
        <button type="button" class="btn {active_class} me-2" 
                onclick="loadSection('vergleichsanalyse?timeframe={tf}')">
            {info['icon']} {info['display_name']}
        </button>
        """
    
    # Render table
    if csv_data:
        table_html = HTMLRenderer.render_csv_table(csv_data, f"SOLL-IST Vergleich - {timeframe_info['display_name']}")
    else:
        table_html = """
        <div class="alert alert-danger">
            <i class="fas fa-exclamation-circle"></i>
            <strong>Fehler beim Laden der Daten</strong><br>
            Der CSV-Service ist nicht erreichbar oder liefert keine Daten.
        </div>
        """
    
    return f"""
    <div class="container-fluid">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="mb-3">
                    <i class="fas fa-balance-scale text-primary"></i> 
                    SOLL-IST Vergleichsanalyse
                </h1>
                <p class="text-muted">Vergleich zwischen vorhergesagten und tatsächlichen Gewinnen</p>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-cog"></i> Zeitintervall auswählen</h5>
                    </div>
                    <div class="card-body">
                        {timeframe_buttons}
                        <div class="mt-3">
                            <small class="text-muted">
                                <i class="fas fa-info-circle"></i> 
                                Aktuell: {timeframe_info['display_name']} ({timeframe_info['days']} Tage)
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                {table_html}
            </div>
        </div>
    </div>
    """

@app.get("/api/content/analysis", response_class=HTMLResponse)
async def get_analysis_content(timeframe: str = Query(default="1M")):
    """Analyse Content mit Top15 Predictions"""
    
    if timeframe not in ServiceConfig.TIMEFRAMES:
        timeframe = "1M"
    
    timeframe_info = ServiceConfig.TIMEFRAMES[timeframe]
    
    # Fetch Top15 Predictions mit korrektem Endpoint
    predictions_url = f"{ServiceConfig.DATA_PROCESSING_URL}/api/v1/data/predictions?timeframe={timeframe}"
    predictions_data = await DataService.fetch_csv_data(predictions_url)
    
    # Timeframe buttons
    timeframe_buttons = ""
    for tf, info in ServiceConfig.TIMEFRAMES.items():
        active_class = "btn-primary" if tf == timeframe else "btn-outline-primary"
        timeframe_buttons += f"""
        <button type="button" class="btn {active_class} me-2" 
                onclick="loadSection('analysis?timeframe={tf}')">
            {info['icon']} {info['display_name']}
        </button>
        """
    
    # Render predictions table
    if predictions_data:
        table_html = HTMLRenderer.render_csv_table(predictions_data, f"Top 15 Aktien-Vorhersagen - {timeframe_info['display_name']}")
    else:
        table_html = """
        <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Keine Vorhersagedaten verfügbar</strong><br>
            Der Data Processing Service ist nicht erreichbar.
        </div>
        """
    
    return f"""
    <div class="container-fluid">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="mb-3">
                    <i class="fas fa-chart-bar text-primary"></i> 
                    Aktien-Analyse
                </h1>
                <p class="text-muted">Top 15 Aktien-Vorhersagen mit KI-basierten Empfehlungen</p>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-calendar-alt"></i> Analysezeitraum</h5>
                    </div>
                    <div class="card-body">
                        {timeframe_buttons}
                        <div class="mt-3">
                            <small class="text-muted">
                                <i class="fas fa-info-circle"></i> 
                                Zeitraum: {timeframe_info['display_name']} ({timeframe_info['days']} Tage)
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                {table_html}
            </div>
        </div>
    </div>
    """

@app.get("/api/content/events", response_class=HTMLResponse)
async def get_events_content():
    """Event Bus Status und Dokumentation"""
    return """
    <div class="container-fluid">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="mb-3">
                    <i class="fas fa-broadcast-tower text-primary"></i> 
                    Event Bus System
                </h1>
                <p class="text-muted">Zentrale Event-Kommunikation zwischen allen Services</p>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-info-circle"></i> Event Bus Status</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Typ:</strong> Redis-basierter Event Bus</p>
                        <p><strong>Status:</strong> <span class="badge bg-success">Aktiv</span></p>
                        <p><strong>Event-Typen:</strong> 8 Core Event-Types</p>
                        <p><strong>Services verbunden:</strong> 6 aktive Services</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-list"></i> Event-Kategorien</h5>
                    </div>
                    <div class="card-body">
                        <ul class="list-unstyled">
                            <li><i class="fas fa-chart-line"></i> analysis.state.changed</li>
                            <li><i class="fas fa-briefcase"></i> portfolio.state.changed</li>
                            <li><i class="fas fa-exchange-alt"></i> trading.state.changed</li>
                            <li><i class="fas fa-brain"></i> intelligence.triggered</li>
                            <li><i class="fas fa-sync"></i> data.synchronized</li>
                            <li><i class="fas fa-exclamation-triangle"></i> system.alert.raised</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

@app.get("/api/content/monitoring", response_class=HTMLResponse)
async def get_monitoring_content():
    """System Monitoring und Health Checks"""
    
    # Service health checks
    services = {
        "Data Processing Service": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL
    }
    
    service_rows = ""
    for service_name, url in services.items():
        health = await DataService.check_service_health(url)
        
        if health["status"] == "healthy":
            status_badge = '<span class="badge bg-success">Healthy</span>'
            last_check = "Gerade eben"
        elif health["status"] == "unhealthy":
            status_badge = f'<span class="badge bg-warning">HTTP {health.get("code", "Error")}</span>'
            last_check = "Fehler"
        else:
            status_badge = '<span class="badge bg-danger">Offline</span>'
            last_check = "Nicht erreichbar"
        
        service_rows += f"""
        <tr>
            <td><i class="fas fa-server"></i> {service_name}</td>
            <td>{status_badge}</td>
            <td>{url}</td>
            <td>{last_check}</td>
        </tr>
        """
    
    return f"""
    <div class="container-fluid">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="mb-3">
                    <i class="fas fa-heartbeat text-primary"></i> 
                    System Monitoring
                </h1>
                <p class="text-muted">Live-Überwachung aller System-Komponenten</p>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-list-alt"></i> Service Health Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Service</th>
                                        <th>Status</th>
                                        <th>URL</th>
                                        <th>Letzter Check</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {service_rows}
                                </tbody>
                            </table>
                        </div>
                        <div class="mt-3">
                            <button class="btn btn-primary" onclick="loadSection('monitoring')">
                                <i class="fas fa-sync-alt"></i> Aktualisieren
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

@app.get("/api/content/api", response_class=HTMLResponse)
async def get_api_content():
    """API Dokumentation"""
    return """
    <div class="container-fluid">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="mb-3">
                    <i class="fas fa-code text-primary"></i> 
                    API Dokumentation
                </h1>
                <p class="text-muted">Verfügbare REST-APIs und Endpunkte</p>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line"></i> Data Processing API</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Base URL:</strong> http://localhost:8017</p>
                        <h6>Endpoints:</h6>
                        <ul>
                            <li><code>/api/v1/data/top15-predictions</code></li>
                            <li><code>/api/v1/data/status</code></li>
                            <li><code>/health</code></li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-table"></i> CSV Service API</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Base URL:</strong> http://localhost:8019</p>
                        <h6>Endpoints:</h6>
                        <ul>
                            <li><code>/api/v1/vergleichsanalyse/csv</code></li>
                            <li><code>/health</code></li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-info-circle"></i> Verwendung</h5>
                    </div>
                    <div class="card-body">
                        <p>Alle APIs unterstützen folgende Parameter:</p>
                        <ul>
                            <li><strong>timeframe:</strong> 1W, 1M, 3M, 6M, 1Y</li>
                            <li><strong>format:</strong> json, csv (Standard: csv)</li>
                        </ul>
                        <p>Beispiel: <code>/api/v1/data/top15-predictions?timeframe=1M</code></p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

@app.get("/health")
async def health_check():
    """Service Health Check"""
    return {
        "status": "healthy",
        "service": "frontend",
        "version": ServiceConfig.VERSION,
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 Handler"""
    return JSONResponse(
        status_code=404,
        content={"detail": f"Endpoint not found: {request.url.path}"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 Handler"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    logger.info(f"Starting {ServiceConfig.SERVICE_NAME} v{ServiceConfig.VERSION}")
    uvicorn.run(
        app, 
        host=ServiceConfig.HOST, 
        port=ServiceConfig.PORT, 
        log_level="info"
    )