#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Aktienanalyse Frontend Service mit Menü-Navigation
"""

import os
from datetime import datetime
from pathlib import Path
import aiohttp
import asyncpg
import asyncio
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

# Logging Setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class EnhancedFrontendService:
    def __init__(self):
        self.db_pool = None
        self.session = None
        self.services = {
            "event_bus": "http://10.1.1.174:8081",
            "core": "http://10.1.1.174:8080", 
            "broker": "http://10.1.1.174:8082",
            "monitoring": "http://10.1.1.174:8083"
        }
        self.static_path = Path("/opt/aktienanalyse-ökosystem/services/frontend-service/static")
        
    async def initialize(self):
        try:
            postgres_url = "postgresql://aktienanalyse:secure_password@localhost:5432/aktienanalyse_events?sslmode=disable"
            self.db_pool = await asyncpg.create_pool(postgres_url, min_size=1, max_size=5)
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
            self.static_path.mkdir(exist_ok=True)
            await self.create_enhanced_static_files()
            logger.info("Enhanced Frontend Service initialized")
        except Exception as e:
            logger.error("Failed to initialize", error=str(e))
            raise

    async def cleanup(self):
        if self.session:
            await self.session.close()
        if self.db_pool:
            await self.db_pool.close()

    async def create_enhanced_static_files(self):
        html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aktienanalyse-Ökosystem</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .sidebar {
            min-height: 100vh;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            position: fixed;
            top: 0;
            left: 0;
            width: 250px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        .sidebar-brand {
            padding: 20px 15px;
            color: white;
            font-size: 1.2rem;
            font-weight: bold;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        .sidebar-nav {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .sidebar-nav li {
            margin: 5px 0;
        }
        .sidebar-nav a {
            display: block;
            padding: 15px 20px;
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            transition: all 0.3s ease;
            border-radius: 0 25px 25px 0;
            margin-right: 15px;
        }
        .sidebar-nav a:hover,
        .sidebar-nav a.active {
            background: rgba(255,255,255,0.2);
            color: white;
            transform: translateX(5px);
        }
        .main-content {
            margin-left: 250px;
            min-height: 100vh;
            background: #f8f9fa;
        }
        .content-header {
            background: white;
            padding: 20px 30px;
            border-bottom: 1px solid #dee2e6;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .content-body {
            padding: 30px;
        }
        .status-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 15px;
        }
        .service-card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .service-card:hover {
            transform: translateY(-5px);
        }
        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .api-endpoint {
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }
        @media (max-width: 768px) {
            .sidebar {
                width: 100%;
                height: auto;
                position: relative;
            }
            .main-content {
                margin-left: 0;
            }
        }
    </style>
</head>
<body>
    <!-- Sidebar Navigation -->
    <div class="sidebar">
        <div class="sidebar-brand">
            <i class="fas fa-chart-line me-2"></i>
            Aktienanalyse-Ökosystem
        </div>
        <ul class="sidebar-nav">
            <li>
                <a href="#" onclick="loadContent('dashboard')" class="active" id="nav-dashboard">
                    <i class="fas fa-tachometer-alt me-2"></i>
                    Dashboard
                </a>
            </li>
            <li>
                <a href="#" onclick="loadContent('events')" id="nav-events">
                    <i class="fas fa-broadcast-tower me-2"></i>
                    Event-Bus
                </a>
            </li>
            <li>
                <a href="#" onclick="loadContent('monitoring')" id="nav-monitoring">
                    <i class="fas fa-heartbeat me-2"></i>
                    Monitoring
                </a>
            </li>
            <li>
                <a href="#" onclick="loadContent('api')" id="nav-api">
                    <i class="fas fa-code me-2"></i>
                    API Dokumentation
                </a>
            </li>
            <li>
                <a href="#" onclick="loadContent('predictions')" id="nav-predictions">
                    <i class="fas fa-chart-line me-2"></i>
                    Gewinn-Vorhersage
                </a>
            </li>
            <li>
                <a href="#" onclick="loadContent('admin')" id="nav-admin">
                    <i class="fas fa-cogs me-2"></i>
                    Administration
                </a>
            </li>
        </ul>
    </div>

    <!-- Main Content Area -->
    <div class="main-content">
        <div class="content-header">
            <h1 id="content-title">Dashboard</h1>
            <p class="text-muted mb-0" id="content-subtitle">System-Übersicht und Status</p>
        </div>
        <div class="content-body">
            <div id="main-content">
                <!-- Content wird hier dynamisch geladen -->
                <div class="loading-spinner"></div>
                <span class="ms-2">Lade Inhalt...</span>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentSection = 'dashboard';

        async function loadContent(section) {
            try {
                // Update Navigation
                document.querySelectorAll('.sidebar-nav a').forEach(a => a.classList.remove('active'));
                document.getElementById('nav-' + section).classList.add('active');
                
                // Show loading
                document.getElementById('main-content').innerHTML = 
                    '<div class="loading-spinner"></div><span class="ms-2">Lade Inhalt...</span>';
                
                // Update header
                updateHeader(section);
                
                // Fetch content
                const response = await fetch('/api/content/' + section);
                const content = await response.text();
                
                document.getElementById('main-content').innerHTML = content;
                currentSection = section;
                
                // Initialize section-specific functionality
                if (section === 'dashboard') {
                    initDashboard();
                } else if (section === 'monitoring') {
                    initMonitoring();
                } else if (section === 'predictions') {
                    initPredictions();
                }
                
            } catch (error) {
                console.error('Error loading content:', error);
                document.getElementById('main-content').innerHTML = 
                    '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>Fehler beim Laden des Inhalts</div>';
            }
        }

        function updateHeader(section) {
            const headers = {
                'dashboard': { title: 'Dashboard', subtitle: 'System-Übersicht und Status' },
                'events': { title: 'Event-Bus', subtitle: 'Event-Stream und Nachrichten' },
                'monitoring': { title: 'System Monitoring', subtitle: 'Performance und Metriken' },
                'api': { title: 'API Dokumentation', subtitle: 'Service-Endpunkte und Dokumentation' },
                'predictions': { title: 'Gewinn-Vorhersage', subtitle: 'ML-basierte Aktienanalyse und Performance-Prognosen' },
                'admin': { title: 'Administration', subtitle: 'System-Verwaltung und Konfiguration' }
            };
            
            const header = headers[section] || headers['dashboard'];
            document.getElementById('content-title').textContent = header.title;
            document.getElementById('content-subtitle').textContent = header.subtitle;
        }

        async function initDashboard() {
            try {
                // Load system metrics
                const metricsResponse = await fetch('/api/monitoring/metrics/overview');
                const metrics = await metricsResponse.json();
                
                // Update status cards
                if (metrics && metrics.system) {
                    document.getElementById('cpu-usage').textContent = metrics.system.cpu_percent.toFixed(1) + '%';
                    document.getElementById('memory-usage').textContent = metrics.system.memory_percent.toFixed(1) + '%';
                    document.getElementById('active-services').textContent = 
                        metrics.summary.active_services + '/' + metrics.summary.total_services;
                }
            } catch (error) {
                console.error('Error loading dashboard metrics:', error);
            }
        }

        async function initMonitoring() {
            // Auto-refresh monitoring data every 30 seconds
            setInterval(async () => {
                if (currentSection === 'monitoring') {
                    try {
                        const response = await fetch('/api/content/monitoring');
                        const content = await response.text();
                        document.getElementById('main-content').innerHTML = content;
                    } catch (error) {
                        console.error('Error refreshing monitoring data:', error);
                    }
                }
            }, 30000);
        }

        async function refreshService(serviceName) {
            try {
                const button = document.getElementById('refresh-' + serviceName);
                const originalText = button.innerHTML;
                button.innerHTML = '<div class="loading-spinner"></div>';
                
                const response = await fetch('/api/' + serviceName + '/health');
                const status = await response.json();
                
                // Update service status display
                const statusElement = document.getElementById('status-' + serviceName);
                if (statusElement) {
                    statusElement.innerHTML = status.status === 'healthy' ? 
                        '<span class="badge bg-success">Aktiv</span>' : 
                        '<span class="badge bg-danger">Offline</span>';
                }
                
                button.innerHTML = originalText;
            } catch (error) {
                console.error('Error refreshing service:', error);
                document.getElementById('refresh-' + serviceName).innerHTML = 
                    '<i class="fas fa-exclamation-triangle"></i>';
            }
        }

        async function initPredictions() {
            // Auto-refresh prediction data every 60 seconds
            setInterval(async () => {
                if (currentSection === 'predictions') {
                    try {
                        const response = await fetch('/api/content/predictions');
                        const content = await response.text();
                        document.getElementById('main-content').innerHTML = content;
                        // Re-initialize charts after content refresh
                        initPredictionCharts();
                    } catch (error) {
                        console.error('Error refreshing prediction data:', error);
                    }
                }
            }, 60000);
            
            // Initialize charts immediately
            initPredictionCharts();
        }

        function initPredictionCharts() {
            // Initialize Chart.js charts if elements exist
            if (document.getElementById('performance-chart')) {
                initPerformanceChart();
            }
            if (document.getElementById('risk-chart')) {
                initRiskChart();
            }
        }

        async function refreshPredictions() {
            try {
                const button = document.getElementById('refresh-predictions');
                if (!button) {
                    console.error('Refresh button not found');
                    return;
                }
                
                const originalText = button.innerHTML;
                button.innerHTML = '<div class="loading-spinner"></div> ML-Berechnung läuft...';
                
                console.log('Triggering ML prediction calculation...');
                
                // POST Request für ML-Neuberechnung
                const mlResponse = await fetch('/api/predictions/refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!mlResponse.ok) {
                    throw new Error(`ML-API Error ${mlResponse.status}: ${mlResponse.statusText}`);
                }
                
                const mlResult = await mlResponse.json();
                console.log('ML calculation completed:', mlResult);
                
                button.innerHTML = '<div class="loading-spinner"></div> Lade neue Daten...';
                
                // Jetzt GUI mit neuen Daten aktualisieren
                await updatePredictionsWithLiveData(mlResult.predictions);
                
                button.innerHTML = '<i class="fas fa-check me-2"></i>Erfolgreich aktualisiert';
                
                // Button nach 2 Sekunden zurücksetzen
                setTimeout(() => {
                    button.innerHTML = originalText;
                }, 2000);
                
            } catch (error) {
                console.error('Error refreshing predictions:', error);
                const button = document.getElementById('refresh-predictions');
                if (button) {
                    button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ML-Fehler';
                    // Reset button after 5 seconds
                    setTimeout(() => {
                        button.innerHTML = '<i class="fas fa-sync me-2"></i>Aktualisieren';
                    }, 5000);
                }
            }
        }

        async function updatePredictionsWithLiveData(predictions) {
            try {
                console.log('Updating GUI with live prediction data:', predictions);
                
                // Update KPI Cards mit neuen Daten
                const currentTimeframe = document.getElementById('timeframe-select').value || '3M';
                if (predictions[currentTimeframe]) {
                    const data = predictions[currentTimeframe];
                    
                    // Top Prediction Card aktualisieren
                    const topPrediction = document.getElementById('top-prediction');
                    const topPredictionTimeframe = document.getElementById('top-prediction-timeframe');
                    
                    if (topPrediction) {
                        topPrediction.textContent = data.predicted_return + '%';
                    }
                    if (topPredictionTimeframe) {
                        topPredictionTimeframe.textContent = `${data.best_stock} (${currentTimeframe})`;
                    }
                }
                
                // TODO: Chart-Daten mit neuen Werten aktualisieren
                // TODO: Tabellen-Daten mit ML-Ergebnissen aktualisieren
                // TODO: Timestamp der letzten Berechnung anzeigen
                
                console.log('GUI update completed');
                
            } catch (error) {
                console.error('Error updating GUI with live data:', error);
            }
        }

        // Update Prediction Timeframe Function (Event Handler - Main HTML)
        function updatePredictionTimeframe(timeframe) {
            try {
                console.log(`[MAIN] Zeitraum-Event geändert zu: ${timeframe}`);
                
                // Dispatch custom event to content-specific handlers
                const event = new CustomEvent('timeframeChanged', { 
                    detail: { timeframe: timeframe } 
                });
                document.dispatchEvent(event);
                
            } catch (error) {
                console.error('[MAIN] Error dispatching timeframe event:', error);
            }
        }

        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadContent('dashboard');
        });
    </script>
</body>
</html>"""
        
        with open(self.static_path / "index.html", "w", encoding="utf-8") as f:
            f.write(html)

    async def get_dashboard_content(self):
        """Dashboard content with system overview"""
        try:
            # Get system metrics
            metrics_data = await self.proxy_request("monitoring", "/metrics/overview")
            
            return f"""
            <div class="row">
                <div class="col-md-4 mb-4">
                    <div class="card status-card">
                        <div class="card-body text-center">
                            <i class="fas fa-microchip fa-2x mb-2"></i>
                            <h3 id="cpu-usage">{metrics_data.get('system', {}).get('cpu_percent', 0):.1f}%</h3>
                            <p class="mb-0">CPU Auslastung</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card status-card">
                        <div class="card-body text-center">
                            <i class="fas fa-memory fa-2x mb-2"></i>
                            <h3 id="memory-usage">{metrics_data.get('system', {}).get('memory_percent', 0):.1f}%</h3>
                            <p class="mb-0">Speicher</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card status-card">
                        <div class="card-body text-center">
                            <i class="fas fa-server fa-2x mb-2"></i>
                            <h3 id="active-services">{metrics_data.get('summary', {}).get('active_services', 0)}/{metrics_data.get('summary', {}).get('total_services', 0)}</h3>
                            <p class="mb-0">Services</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <div class="card service-card">
                        <div class="card-header">
                            <h5><i class="fas fa-network-wired me-2"></i>Backend Services</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                        <div>
                                            <strong>Event-Bus Service</strong><br>
                                            <small class="text-muted">Port 8081</small>
                                        </div>
                                        <div>
                                            <span class="badge bg-success" id="status-event_bus">Aktiv</span>
                                            <button class="btn btn-sm btn-outline-primary ms-2" id="refresh-event_bus" onclick="refreshService('event_bus')">
                                                <i class="fas fa-sync"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                        <div>
                                            <strong>Core Service</strong><br>
                                            <small class="text-muted">Port 8080</small>
                                        </div>
                                        <div>
                                            <span class="badge bg-success" id="status-core">Aktiv</span>
                                            <button class="btn btn-sm btn-outline-primary ms-2" id="refresh-core" onclick="refreshService('core')">
                                                <i class="fas fa-sync"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                        <div>
                                            <strong>Broker Service</strong><br>
                                            <small class="text-muted">Port 8082</small>
                                        </div>
                                        <div>
                                            <span class="badge bg-success" id="status-broker">Aktiv</span>
                                            <button class="btn btn-sm btn-outline-primary ms-2" id="refresh-broker" onclick="refreshService('broker')">
                                                <i class="fas fa-sync"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                        <div>
                                            <strong>Monitoring Service</strong><br>
                                            <small class="text-muted">Port 8083</small>
                                        </div>
                                        <div>
                                            <span class="badge bg-success" id="status-monitoring">Aktiv</span>
                                            <button class="btn btn-sm btn-outline-primary ms-2" id="refresh-monitoring" onclick="refreshService('monitoring')">
                                                <i class="fas fa-sync"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
        except Exception as e:
            return f"""
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Fehler beim Laden der System-Metriken: {str(e)}
            </div>
            <div class="card service-card">
                <div class="card-header">
                    <h5><i class="fas fa-network-wired me-2"></i>Backend Services</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                <div>
                                    <strong>Event-Bus Service</strong><br>
                                    <small class="text-muted">Port 8081</small>
                                </div>
                                <a href="http://10.1.1.174:8081/docs" target="_blank" class="btn btn-sm btn-primary">
                                    <i class="fas fa-external-link-alt"></i> Docs
                                </a>
                            </div>
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                <div>
                                    <strong>Core Service</strong><br>
                                    <small class="text-muted">Port 8080</small>
                                </div>
                                <a href="http://10.1.1.174:8080/docs" target="_blank" class="btn btn-sm btn-primary">
                                    <i class="fas fa-external-link-alt"></i> Docs
                                </a>
                            </div>
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                <div>
                                    <strong>Broker Service</strong><br>
                                    <small class="text-muted">Port 8082</small>
                                </div>
                                <a href="http://10.1.1.174:8082/docs" target="_blank" class="btn btn-sm btn-primary">
                                    <i class="fas fa-external-link-alt"></i> Docs
                                </a>
                            </div>
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="d-flex justify-content-between align-items-center p-3 bg-light rounded">
                                <div>
                                    <strong>Monitoring Service</strong><br>
                                    <small class="text-muted">Port 8083</small>
                                </div>
                                <a href="http://10.1.1.174:8083/docs" target="_blank" class="btn btn-sm btn-primary">
                                    <i class="fas fa-external-link-alt"></i> Docs
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """

    async def get_events_content(self):
        """Event-Bus content"""
        return """
        <div class="card service-card">
            <div class="card-header">
                <h5><i class="fas fa-broadcast-tower me-2"></i>Event-Bus Status</h5>
            </div>
            <div class="card-body">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Event-Bus Service läuft auf Port 8081 und verwaltet die Kommunikation zwischen den Services.
                </div>
                
                <div class="api-endpoint">
                    <strong>Service Dokumentation:</strong><br>
                    <a href="http://10.1.1.174:8081/docs" target="_blank" class="btn btn-primary mt-2">
                        <i class="fas fa-external-link-alt me-2"></i>OpenAPI Dokumentation öffnen
                    </a>
                </div>
                
                <div class="mt-4">
                    <h6>Verfügbare Endpunkte:</h6>
                    <ul class="list-group">
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <code>GET /health</code>
                            <span class="badge bg-success">Aktiv</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <code>POST /events</code>
                            <span class="badge bg-primary">Event Publishing</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <code>GET /events/stream</code>
                            <span class="badge bg-info">Event Stream</span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
        """

    async def get_monitoring_content(self):
        """Monitoring content with live data"""
        try:
            metrics_data = await self.proxy_request("monitoring", "/metrics/overview")
            
            return f"""
            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="metric-card">
                        <h6><i class="fas fa-microchip me-2"></i>CPU Auslastung</h6>
                        <div class="progress mb-2">
                            <div class="progress-bar" style="width: {metrics_data.get('system', {}).get('cpu_percent', 0)}%"></div>
                        </div>
                        <small class="text-muted">{metrics_data.get('system', {}).get('cpu_percent', 0):.1f}% von {metrics_data.get('system', {}).get('cpu_count', 'N/A')} Cores</small>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="metric-card">
                        <h6><i class="fas fa-memory me-2"></i>Speicher</h6>
                        <div class="progress mb-2">
                            <div class="progress-bar bg-warning" style="width: {metrics_data.get('system', {}).get('memory_percent', 0)}%"></div>
                        </div>
                        <small class="text-muted">{metrics_data.get('system', {}).get('memory_used_gb', 0):.1f} GB von {metrics_data.get('system', {}).get('memory_total_gb', 0):.1f} GB</small>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="metric-card">
                        <h6><i class="fas fa-hdd me-2"></i>Festplatte</h6>
                        <div class="progress mb-2">
                            <div class="progress-bar bg-info" style="width: {metrics_data.get('system', {}).get('disk_percent', 0)}%"></div>
                        </div>
                        <small class="text-muted">{metrics_data.get('system', {}).get('disk_used_gb', 0):.1f} GB von {metrics_data.get('system', {}).get('disk_total_gb', 0):.1f} GB</small>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="metric-card">
                        <h6><i class="fas fa-server me-2"></i>Services</h6>
                        <h4 class="text-success">{metrics_data.get('summary', {}).get('active_services', 0)}/{metrics_data.get('summary', {}).get('total_services', 0)}</h4>
                        <small class="text-muted">Aktive Services</small>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h5><i class="fas fa-chart-line me-2"></i>Live Monitoring</h5>
                </div>
                <div class="card-body">
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        Alle Services laufen normal. Monitoring läuft kontinuierlich.
                    </div>
                    
                    <a href="http://10.1.1.174:8083/docs" target="_blank" class="btn btn-primary">
                        <i class="fas fa-external-link-alt me-2"></i>Monitoring API Dokumentation
                    </a>
                </div>
            </div>
            """
        except Exception as e:
            return f"""
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Monitoring-Daten können nicht geladen werden: {str(e)}
            </div>
            <div class="card">
                <div class="card-header">
                    <h5><i class="fas fa-chart-line me-2"></i>Monitoring Service</h5>
                </div>
                <div class="card-body">
                    <a href="http://10.1.1.174:8083/docs" target="_blank" class="btn btn-primary">
                        <i class="fas fa-external-link-alt me-2"></i>Monitoring API Dokumentation
                    </a>
                </div>
            </div>
            """

    async def get_api_content(self):
        """API Documentation content"""
        return """
        <div class="row">
            <div class="col-md-6 mb-4">
                <div class="card service-card">
                    <div class="card-header">
                        <h6><i class="fas fa-broadcast-tower me-2"></i>Event-Bus Service</h6>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">Port 8081 - Event Management</p>
                        <a href="http://10.1.1.174:8081/docs" target="_blank" class="btn btn-primary">
                            <i class="fas fa-book me-2"></i>API Docs
                        </a>
                    </div>
                </div>
            </div>
            <div class="col-md-6 mb-4">
                <div class="card service-card">
                    <div class="card-header">
                        <h6><i class="fas fa-brain me-2"></i>Core Service</h6>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">Port 8080 - Intelligente Analyse</p>
                        <a href="http://10.1.1.174:8080/docs" target="_blank" class="btn btn-primary">
                            <i class="fas fa-book me-2"></i>API Docs
                        </a>
                    </div>
                </div>
            </div>
            <div class="col-md-6 mb-4">
                <div class="card service-card">
                    <div class="card-header">
                        <h6><i class="fas fa-exchange-alt me-2"></i>Broker Service</h6>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">Port 8082 - Trading Interface</p>
                        <a href="http://10.1.1.174:8082/docs" target="_blank" class="btn btn-primary">
                            <i class="fas fa-book me-2"></i>API Docs
                        </a>
                    </div>
                </div>
            </div>
            <div class="col-md-6 mb-4">
                <div class="card service-card">
                    <div class="card-header">
                        <h6><i class="fas fa-heartbeat me-2"></i>Monitoring Service</h6>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">Port 8083 - System Überwachung</p>
                        <a href="http://10.1.1.174:8083/docs" target="_blank" class="btn btn-primary">
                            <i class="fas fa-book me-2"></i>API Docs
                        </a>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-code me-2"></i>API Übersicht</h5>
            </div>
            <div class="card-body">
                <div class="api-endpoint">
                    <strong>Frontend API Endpunkte:</strong>
                    <ul class="mt-2">
                        <li><code>GET /health</code> - Service Status</li>
                        <li><code>GET /api/content/{section}</code> - Content für Navigation</li>
                        <li><code>GET /api/monitoring/{path}</code> - Monitoring Proxy</li>
                        <li><code>GET /api/broker/{path}</code> - Broker Proxy</li>
                    </ul>
                </div>
                
                <div class="mt-3">
                    <h6>Externe Service APIs:</h6>
                    <p class="text-muted">
                        Alle Backend-Services stellen OpenAPI (Swagger) Dokumentationen zur Verfügung. 
                        Klicken Sie auf die Links oben, um die detaillierten API-Spezifikationen zu sehen.
                    </p>
                </div>
            </div>
        </div>
        """

    async def get_predictions_content(self):
        """Gewinn-Vorhersage content mit tabellarischen und grafischen Darstellungen"""
        return """
        <!-- Chart.js für Grafiken -->
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        
        <!-- Control Panel -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5><i class="fas fa-chart-line me-2"></i>ML-Ensemble Gewinn-Vorhersage</h5>
                        <div>
                            <button class="btn btn-primary btn-sm" id="refresh-predictions" onclick="refreshPredictions()">
                                <i class="fas fa-sync me-2"></i>Aktualisieren
                            </button>
                            <select class="form-select form-select-sm d-inline-block w-auto ms-2" id="timeframe-select" onchange="updatePredictionTimeframe(this.value)">
                                <option value="7D">7 Tage</option>
                                <option value="1M">1 Monat</option>
                                <option value="3M" selected>3 Monate</option>
                                <option value="6M">6 Monate</option>
                                <option value="1Y">1 Jahr</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Key Performance Indicators -->
        <div class="row mb-4">
            <div class="col-md-3 mb-3">
                <div class="card status-card text-center">
                    <div class="card-body">
                        <i class="fas fa-trophy fa-2x mb-2"></i>
                        <h3 id="top-prediction">18.5%</h3>
                        <p class="mb-0">Top Gewinn-Prognose</p>
                        <small id="top-prediction-timeframe">NVDA (3M)</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card status-card text-center">
                    <div class="card-body">
                        <i class="fas fa-robot fa-2x mb-2"></i>
                        <h3>87.3%</h3>
                        <p class="mb-0">ML-Genauigkeit</p>
                        <small>Ensemble-Modell</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card status-card text-center">
                    <div class="card-body">
                        <i class="fas fa-chart-area fa-2x mb-2"></i>
                        <h3>1.42</h3>
                        <p class="mb-0">Avg. Sharpe Ratio</p>
                        <small>Top 10 Aktien</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card status-card text-center">
                    <div class="card-body">
                        <i class="fas fa-clock fa-2x mb-2"></i>
                        <h3>0.08s</h3>
                        <p class="mb-0">Analyse-Zeit</p>
                        <small>Letzte Vorhersage</small>
                    </div>
                </div>
            </div>
        </div>

        <!-- Top Gewinn-Vorhersagen Tabelle -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card service-card">
                    <div class="card-header">
                        <h5><i class="fas fa-table me-2"></i>Top 15 Gewinn-Vorhersagen</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover" id="predictions-table">
                                <thead class="table-dark">
                                    <tr>
                                        <th>#</th>
                                        <th>Symbol</th>
                                        <th>Unternehmen</th>
                                        <th>Aktueller Kurs</th>
                                        <th id="prediction-header">Vorhersage 3M</th>
                                        <th>Gewinn %</th>
                                        <th>Sharpe Ratio</th>
                                        <th>ML-Score</th>
                                        <th>Risiko</th>
                                        <th>Aktion</th>
                                    </tr>
                                </thead>
                                <tbody id="predictions-tbody">
                                    <tr class="table-success">
                                        <td><span class="badge bg-warning">1</span></td>
                                        <td><strong>NVDA</strong></td>
                                        <td>NVIDIA Corp</td>
                                        <td>$875.32</td>
                                        <td>$1,037.50</td>
                                        <td><span class="badge bg-success">+18.5%</span></td>
                                        <td>1.87</td>
                                        <td><span class="badge bg-primary">92.3</span></td>
                                        <td><span class="badge bg-warning">Mittel</span></td>
                                        <td><button class="btn btn-sm btn-success"><i class="fas fa-plus me-1"></i>Import</button></td>
                                    </tr>
                                    <tr>
                                        <td><span class="badge bg-secondary">2</span></td>
                                        <td><strong>AAPL</strong></td>
                                        <td>Apple Inc</td>
                                        <td>$193.42</td>
                                        <td>$224.80</td>
                                        <td><span class="badge bg-success">+16.2%</span></td>
                                        <td>1.65</td>
                                        <td><span class="badge bg-primary">89.7</span></td>
                                        <td><span class="badge bg-success">Niedrig</span></td>
                                        <td><button class="btn btn-sm btn-success"><i class="fas fa-plus me-1"></i>Import</button></td>
                                    </tr>
                                    <tr>
                                        <td><span class="badge bg-secondary">3</span></td>
                                        <td><strong>MSFT</strong></td>
                                        <td>Microsoft Corp</td>
                                        <td>$421.18</td>
                                        <td>$485.90</td>
                                        <td><span class="badge bg-success">+15.4%</span></td>
                                        <td>1.52</td>
                                        <td><span class="badge bg-primary">88.1</span></td>
                                        <td><span class="badge bg-success">Niedrig</span></td>
                                        <td><button class="btn btn-sm btn-success"><i class="fas fa-plus me-1"></i>Import</button></td>
                                    </tr>
                                    <tr>
                                        <td><span class="badge bg-secondary">4</span></td>
                                        <td><strong>GOOGL</strong></td>
                                        <td>Alphabet Inc</td>
                                        <td>$168.24</td>
                                        <td>$192.10</td>
                                        <td><span class="badge bg-success">+14.2%</span></td>
                                        <td>1.38</td>
                                        <td><span class="badge bg-primary">85.9</span></td>
                                        <td><span class="badge bg-warning">Mittel</span></td>
                                        <td><button class="btn btn-sm btn-success"><i class="fas fa-plus me-1"></i>Import</button></td>
                                    </tr>
                                    <tr>
                                        <td><span class="badge bg-secondary">5</span></td>
                                        <td><strong>TSLA</strong></td>
                                        <td>Tesla Inc</td>
                                        <td>$248.95</td>
                                        <td>$282.70</td>
                                        <td><span class="badge bg-success">+13.5%</span></td>
                                        <td>1.21</td>
                                        <td><span class="badge bg-primary">83.4</span></td>
                                        <td><span class="badge bg-danger">Hoch</span></td>
                                        <td><button class="btn btn-sm btn-warning"><i class="fas fa-exclamation-triangle me-1"></i>Vorsicht</button></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Grafische Darstellungen -->
        <div class="row mb-4">
            <!-- Performance Chart -->
            <div class="col-md-8 mb-3">
                <div class="card service-card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-area me-2"></i>Gewinn-Vorhersage Verlauf</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="performance-chart" height="300"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Risk-Return Scatter -->
            <div class="col-md-4 mb-3">
                <div class="card service-card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-scatter me-2"></i>Risiko-Rendite Matrix</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="risk-chart" height="300"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- ML-Modell Performance -->
        <div class="row mb-4">
            <div class="col-md-6 mb-3">
                <div class="card service-card">
                    <div class="card-header">
                        <h5><i class="fas fa-brain me-2"></i>ML-Modell Performance</h5>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <div class="d-flex justify-content-between">
                                <span><strong>XGBoost</strong></span>
                                <span>89.2%</span>
                            </div>
                            <div class="progress mb-2">
                                <div class="progress-bar bg-success" style="width: 89.2%"></div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between">
                                <span><strong>LSTM</strong></span>
                                <span>85.7%</span>
                            </div>
                            <div class="progress mb-2">
                                <div class="progress-bar bg-info" style="width: 85.7%"></div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between">
                                <span><strong>Transformer</strong></span>
                                <span>87.1%</span>
                            </div>
                            <div class="progress mb-2">
                                <div class="progress-bar bg-warning" style="width: 87.1%"></div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between">
                                <span><strong>Ensemble</strong></span>
                                <span>91.3%</span>
                            </div>
                            <div class="progress">
                                <div class="progress-bar bg-primary" style="width: 91.3%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Technical Analysis Scores -->
            <div class="col-md-6 mb-3">
                <div class="card service-card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-bar me-2"></i>Technical Analysis Scores</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="technical-chart" height="250"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <script>
        // Refresh Predictions Function - lokale Definition für dynamischen Content
        async function refreshPredictions() {
            try {
                const button = document.getElementById('refresh-predictions');
                if (!button) {
                    console.error('Refresh button not found');
                    return;
                }
                
                const originalText = button.innerHTML;
                button.innerHTML = '<div class="loading-spinner"></div> ML-Berechnung läuft...';
                
                console.log('Triggering ML prediction calculation...');
                
                // POST Request für ML-Neuberechnung
                const mlResponse = await fetch('/api/predictions/refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!mlResponse.ok) {
                    throw new Error(`ML-API Error ${mlResponse.status}: ${mlResponse.statusText}`);
                }
                
                const mlResult = await mlResponse.json();
                console.log('ML calculation completed:', mlResult);
                
                button.innerHTML = '<div class="loading-spinner"></div> Lade neue Daten...';
                
                // GUI mit neuen Daten aktualisieren
                await updatePredictionsWithLiveData(mlResult.predictions);
                
                button.innerHTML = '<i class="fas fa-check me-2"></i>Erfolgreich aktualisiert';
                
                // Button nach 2 Sekunden zurücksetzen
                setTimeout(() => {
                    button.innerHTML = originalText;
                }, 2000);
                
            } catch (error) {
                console.error('Error refreshing predictions:', error);
                const button = document.getElementById('refresh-predictions');
                if (button) {
                    button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ML-Fehler';
                    // Reset button after 5 seconds
                    setTimeout(() => {
                        button.innerHTML = '<i class="fas fa-sync me-2"></i>Aktualisieren';
                    }, 5000);
                }
            }
        }

        async function updatePredictionsWithLiveData(predictions) {
            try {
                console.log('Updating GUI with live prediction data:', predictions);
                
                // Update KPI Cards mit neuen Daten
                const currentTimeframe = document.getElementById('timeframe-select').value || '3M';
                if (predictions[currentTimeframe]) {
                    const data = predictions[currentTimeframe];
                    
                    // Top Prediction Card aktualisieren
                    const topPrediction = document.getElementById('top-prediction');
                    const topPredictionTimeframe = document.getElementById('top-prediction-timeframe');
                    
                    if (topPrediction) {
                        topPrediction.textContent = data.predicted_return + '%';
                    }
                    if (topPredictionTimeframe) {
                        topPredictionTimeframe.textContent = `${data.best_stock} (${currentTimeframe})`;
                    }
                }
                
                // Update Top 15 Table mit aktuellen Zeitraum
                updateTop15Table(currentTimeframe);
                
                // Update Charts mit neuen Daten (falls vorhanden)
                if (window.performanceChart) {
                    // TODO: Chart-Daten mit ML-Ergebnissen aktualisieren
                    console.log('Charts würden hier mit neuen ML-Daten aktualisiert');
                }
                
                console.log('GUI update completed');
                
            } catch (error) {
                console.error('Error updating GUI with live data:', error);
            }
        }

        // Performance Chart Initialisierung
        function initPerformanceChart() {
            const ctx = document.getElementById('performance-chart');
            if (!ctx) return;
            
            // Destroy existing chart if it exists
            if (window.performanceChart && typeof window.performanceChart.destroy === 'function') {
                window.performanceChart.destroy();
            }
            
            window.performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun'],
                    datasets: [{
                        label: 'Vorhersage-Genauigkeit',
                        data: [85.2, 87.1, 89.3, 91.2, 88.7, 91.3],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.4
                    }, {
                        label: 'Realisierte Gewinne',
                        data: [12.3, 15.8, 18.2, 16.7, 19.1, 17.9],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // Risk-Return Chart
        function initRiskChart() {
            const ctx = document.getElementById('risk-chart');
            if (!ctx) return;
            
            // Destroy existing chart if it exists
            if (window.riskChart && typeof window.riskChart.destroy === 'function') {
                window.riskChart.destroy();
            }
            
            window.riskChart = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Aktien Portfolio',
                        data: [
                            {x: 12, y: 18.5, r: 10}, // NVDA
                            {x: 8, y: 16.2, r: 8},   // AAPL
                            {x: 9, y: 15.4, r: 7},   // MSFT
                            {x: 11, y: 14.2, r: 6},  // GOOGL
                            {x: 15, y: 13.5, r: 9}   // TSLA
                        ],
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Risiko (%)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Erwartete Rendite (%)'
                            }
                        }
                    }
                }
            });
        }

        // Technical Analysis Chart
        function initTechnicalChart() {
            const ctx = document.getElementById('technical-chart');
            if (!ctx) return;
            
            // Destroy existing chart if it exists
            if (window.technicalChart && typeof window.technicalChart.destroy === 'function') {
                window.technicalChart.destroy();
            }
            
            window.technicalChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['RSI', 'MACD', 'SMA', 'EMA', 'Bollinger', 'Stochastic'],
                    datasets: [{
                        label: 'Signal Stärke',
                        data: [78, 85, 72, 68, 82, 75],
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(255, 205, 86, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(153, 102, 255, 0.8)',
                            'rgba(255, 159, 64, 0.8)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 205, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(153, 102, 255, 1)',
                            'rgba(255, 159, 64, 1)'
                        ],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Score (%)'
                            }
                        }
                    }
                }
            });
        }

        // *** Content-spezifische Event-Handler für Predictions ***
        
        // Zeitraum-spezifische Datenstrukturen (gehören zum Predictions-Content)
        const predictionData = {
            timeframes: {
                '7D': { 
                    label: '7 Tage',
                    kpi: { value: '4.2%', stock: 'AAPL (7T)', color: 'bg-info' },
                    top15: [
                        {rank: 1, symbol: 'AAPL', company: 'Apple Inc', current: '$193.42', prediction: '$201.55', gain: '+4.2%', sharpe: '1.12', score: '85.3', risk: 'Niedrig', action: 'Import'},
                        {rank: 2, symbol: 'MSFT', company: 'Microsoft Corp', current: '$421.18', prediction: '$438.90', gain: '+4.2%', sharpe: '1.08', score: '83.7', risk: 'Niedrig', action: 'Import'},
                        {rank: 3, symbol: 'NVDA', company: 'NVIDIA Corp', current: '$875.32', prediction: '$911.20', gain: '+4.1%', sharpe: '1.15', score: '87.2', risk: 'Mittel', action: 'Import'},
                        {rank: 4, symbol: 'GOOGL', company: 'Alphabet Inc', current: '$168.24', prediction: '$174.80', gain: '+3.9%', sharpe: '1.05', score: '82.1', risk: 'Niedrig', action: 'Import'},
                        {rank: 5, symbol: 'AMZN', company: 'Amazon.com Inc', current: '$145.32', prediction: '$150.85', gain: '+3.8%', sharpe: '1.02', score: '80.5', risk: 'Mittel', action: 'Import'}
                    ]
                },
                '1M': { 
                    label: '1 Monat',
                    kpi: { value: '8.7%', stock: 'MSFT (1M)', color: 'bg-primary' },
                    top15: [
                        {rank: 1, symbol: 'MSFT', company: 'Microsoft Corp', current: '$421.18', prediction: '$457.85', gain: '+8.7%', sharpe: '1.42', score: '89.1', risk: 'Niedrig', action: 'Import'},
                        {rank: 2, symbol: 'AAPL', company: 'Apple Inc', current: '$193.42', prediction: '$209.20', gain: '+8.2%', sharpe: '1.38', score: '87.9', risk: 'Niedrig', action: 'Import'},
                        {rank: 3, symbol: 'NVDA', company: 'NVIDIA Corp', current: '$875.32', prediction: '$943.15', gain: '+7.7%', sharpe: '1.35', score: '86.4', risk: 'Mittel', action: 'Import'},
                        {rank: 4, symbol: 'META', company: 'Meta Platforms', current: '$298.54', prediction: '$319.85', gain: '+7.1%', sharpe: '1.28', score: '84.7', risk: 'Mittel', action: 'Import'},
                        {rank: 5, symbol: 'GOOGL', company: 'Alphabet Inc', current: '$168.24', prediction: '$179.95', gain: '+7.0%', sharpe: '1.25', score: '83.2', risk: 'Niedrig', action: 'Import'}
                    ]
                },
                '3M': { 
                    label: '3 Monate',
                    kpi: { value: '18.5%', stock: 'NVDA (3M)', color: 'bg-success' },
                    top15: [
                        {rank: 1, symbol: 'NVDA', company: 'NVIDIA Corp', current: '$875.32', prediction: '$1,037.50', gain: '+18.5%', sharpe: '1.87', score: '92.3', risk: 'Mittel', action: 'Import'},
                        {rank: 2, symbol: 'AAPL', company: 'Apple Inc', current: '$193.42', prediction: '$224.80', gain: '+16.2%', sharpe: '1.65', score: '89.7', risk: 'Niedrig', action: 'Import'},
                        {rank: 3, symbol: 'MSFT', company: 'Microsoft Corp', current: '$421.18', prediction: '$485.90', gain: '+15.4%', sharpe: '1.52', score: '88.1', risk: 'Niedrig', action: 'Import'},
                        {rank: 4, symbol: 'GOOGL', company: 'Alphabet Inc', current: '$168.24', prediction: '$192.10', gain: '+14.2%', sharpe: '1.38', score: '85.9', risk: 'Mittel', action: 'Import'},
                        {rank: 5, symbol: 'TSLA', company: 'Tesla Inc', current: '$248.95', prediction: '$282.70', gain: '+13.5%', sharpe: '1.21', score: '83.4', risk: 'Hoch', action: 'Vorsicht'}
                    ]
                },
                '6M': { 
                    label: '6 Monate',
                    kpi: { value: '24.1%', stock: 'GOOGL (6M)', color: 'bg-warning' },
                    top15: [
                        {rank: 1, symbol: 'GOOGL', company: 'Alphabet Inc', current: '$168.24', prediction: '$208.75', gain: '+24.1%', sharpe: '1.92', score: '94.2', risk: 'Mittel', action: 'Import'},
                        {rank: 2, symbol: 'NVDA', company: 'NVIDIA Corp', current: '$875.32', prediction: '$1,075.20', gain: '+22.8%', sharpe: '1.89', score: '93.1', risk: 'Mittel', action: 'Import'},
                        {rank: 3, symbol: 'MSFT', company: 'Microsoft Corp', current: '$421.18', prediction: '$515.85', gain: '+22.5%', sharpe: '1.76', score: '91.8', risk: 'Niedrig', action: 'Import'},
                        {rank: 4, symbol: 'META', company: 'Meta Platforms', current: '$298.54', prediction: '$364.20', gain: '+22.0%', sharpe: '1.73', score: '90.4', risk: 'Mittel', action: 'Import'},
                        {rank: 5, symbol: 'AAPL', company: 'Apple Inc', current: '$193.42', prediction: '$235.85', gain: '+21.9%', sharpe: '1.71', score: '90.1', risk: 'Niedrig', action: 'Import'}
                    ]
                },
                '1Y': { 
                    label: '1 Jahr',
                    kpi: { value: '35.3%', stock: 'TSLA (1J)', color: 'bg-danger' },
                    top15: [
                        {rank: 1, symbol: 'TSLA', company: 'Tesla Inc', current: '$248.95', prediction: '$336.90', gain: '+35.3%', sharpe: '2.15', score: '95.8', risk: 'Hoch', action: 'Vorsicht'},
                        {rank: 2, symbol: 'NVDA', company: 'NVIDIA Corp', current: '$875.32', prediction: '$1,175.40', gain: '+34.3%', sharpe: '2.08', score: '94.9', risk: 'Mittel', action: 'Import'},
                        {rank: 3, symbol: 'META', company: 'Meta Platforms', current: '$298.54', prediction: '$395.20', gain: '+32.4%', sharpe: '1.95', score: '93.2', risk: 'Mittel', action: 'Import'},
                        {rank: 4, symbol: 'GOOGL', company: 'Alphabet Inc', current: '$168.24', prediction: '$220.85', gain: '+31.3%', sharpe: '1.89', score: '92.1', risk: 'Mittel', action: 'Import'},
                        {rank: 5, symbol: 'AMZN', company: 'Amazon.com Inc', current: '$145.32', prediction: '$190.45', gain: '+31.1%', sharpe: '1.86', score: '91.7', risk: 'Mittel', action: 'Import'}
                    ]
                }
            }
        };
        
        // Content-spezifische Event-Handler
        function handleTimeframeChange(event) {
            const timeframe = event.detail.timeframe;
            console.log(`[CONTENT] Predictions empfängt Zeitraum-Event: ${timeframe}`);
            
            const data = predictionData.timeframes[timeframe] || predictionData.timeframes['3M'];
            
            // Update KPI Cards
            updateKPICards(data.kpi);
            
            // Update Table Headers  
            updateTableHeaders(timeframe);
            
            // Update Top 15 Table
            updateTop15Table(data.top15, timeframe);
        }
        
        function updateKPICards(kpiData) {
            const topPrediction = document.getElementById('top-prediction');
            const topPredictionTimeframe = document.getElementById('top-prediction-timeframe');
            
            if (topPrediction) {
                topPrediction.textContent = kpiData.value;
            }
            if (topPredictionTimeframe) {
                topPredictionTimeframe.textContent = kpiData.stock;
            }
        }
        
        function updateTableHeaders(timeframe) {
            const predictionHeader = document.getElementById('prediction-header');
            if (predictionHeader) {
                predictionHeader.textContent = `Vorhersage ${timeframe}`;
            }
        }
        
        function updateTop15Table(tableData, timeframe) {
            console.log(`[CONTENT] Updating Top 15 table for timeframe: ${timeframe}`);
            
            const tbody = document.getElementById('predictions-tbody');
            
            if (tbody) {
                console.log(`[CONTENT] Found tbody, updating with ${tableData.length} rows`);
                
                // Tabelle leeren und mit neuen Daten füllen
                tbody.innerHTML = '';
                
                tableData.forEach(stock => {
                    const riskClass = stock.risk === 'Niedrig' ? 'success' : stock.risk === 'Mittel' ? 'warning' : 'danger';
                    const actionClass = stock.action === 'Import' ? 'success' : 'warning';
                    const actionIcon = stock.action === 'Import' ? 'plus' : 'exclamation-triangle';
                    
                    const row = `
                        <tr class="${stock.rank === 1 ? 'table-success' : ''}">
                            <td><span class="badge ${stock.rank === 1 ? 'bg-warning' : 'bg-secondary'}">${stock.rank}</span></td>
                            <td><strong>${stock.symbol}</strong></td>
                            <td>${stock.company}</td>
                            <td>${stock.current}</td>
                            <td>${stock.prediction}</td>
                            <td><span class="badge bg-success">${stock.gain}</span></td>
                            <td>${stock.sharpe}</td>
                            <td><span class="badge bg-primary">${stock.score}</span></td>
                            <td><span class="badge bg-${riskClass}">${stock.risk}</span></td>
                            <td><button class="btn btn-sm btn-${actionClass}"><i class="fas fa-${actionIcon} me-1"></i>${stock.action}</button></td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
                
                console.log(`[CONTENT] Top 15 Tabelle aktualisiert für Zeitraum: ${timeframe}`);
            } else {
                console.error('[CONTENT] Table tbody not found! DOM structure may be incorrect.');
            }
        }
        
        // Event-Listener für Timeframe-Changes registrieren
        document.addEventListener('timeframeChanged', handleTimeframeChange);
        
        // Chart-Initialisierung nach DOM-Load
        setTimeout(() => {
            console.log('[CONTENT] Initialisiere Charts...');
            initPerformanceChart();
            initRiskChart();
            initTechnicalChart();
            console.log('[CONTENT] Alle Charts initialisiert');
        }, 500); // 500ms Delay für DOM-Bereitschaft
        
        console.log('[CONTENT] Predictions Content Event-Handler registriert');
        </script>
        """

    async def get_admin_content(self):
        """Admin content"""
        return """
        <div class="card service-card">
            <div class="card-header">
                <h5><i class="fas fa-cogs me-2"></i>System Administration</h5>
            </div>
            <div class="card-body">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Administrations-Tools für das Aktienanalyse-Ökosystem
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6><i class="fas fa-database me-2"></i>Datenbank</h6>
                                <p class="text-muted">PostgreSQL Management</p>
                                <button class="btn btn-outline-primary" onclick="alert('Datenbank-Tools in Entwicklung')">
                                    <i class="fas fa-tools me-2"></i>Verwalten
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6><i class="fas fa-server me-2"></i>Services</h6>
                                <p class="text-muted">Service Management</p>
                                <button class="btn btn-outline-primary" onclick="alert('Service-Management in Entwicklung')">
                                    <i class="fas fa-play me-2"></i>Verwalten
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6><i class="fas fa-chart-bar me-2"></i>Logs</h6>
                                <p class="text-muted">System Logs anzeigen</p>
                                <button class="btn btn-outline-primary" onclick="alert('Log-Viewer in Entwicklung')">
                                    <i class="fas fa-file-alt me-2"></i>Anzeigen
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h6><i class="fas fa-shield-alt me-2"></i>Sicherheit</h6>
                                <p class="text-muted">Sicherheits-Konfiguration</p>
                                <button class="btn btn-outline-primary" onclick="alert('Sicherheits-Tools in Entwicklung')">
                                    <i class="fas fa-lock me-2"></i>Konfigurieren
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mt-4">
                    <h6>System Information:</h6>
                    <ul class="list-group">
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Container IP:</span>
                            <code>10.1.1.174</code>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Frontend Port:</span>
                            <code>443 (HTTPS)</code>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Database:</span>
                            <code>PostgreSQL</code>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>Message Queue:</span>
                            <code>RabbitMQ</code>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
        """

    async def proxy_request(self, service, path, method="GET", **kwargs):
        try:
            service_url = self.services.get(service)
            if not service_url:
                raise HTTPException(status_code=404, detail="Service not found")
            url = f"{service_url}{path}"
            async with self.session.request(method, url, **kwargs) as response:
                return await response.json()
        except Exception as e:
            logger.error("Proxy error", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

frontend_service = EnhancedFrontendService()

app = FastAPI(
    title="Enhanced Aktienanalyse Frontend Service",
    version="2.0.0",
    docs_url="/api/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    try:
        if frontend_service.db_pool:
            async with frontend_service.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        return {
            "service": "enhanced-frontend",
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/api/content/{section}")
async def get_content(section: str):
    """Dynamic content loading for navigation sections"""
    try:
        if section == "dashboard":
            content = await frontend_service.get_dashboard_content()
        elif section == "events":
            content = await frontend_service.get_events_content()
        elif section == "monitoring":
            content = await frontend_service.get_monitoring_content()
        elif section == "api":
            content = await frontend_service.get_api_content()
        elif section == "predictions":
            content = await frontend_service.get_predictions_content()
        elif section == "admin":
            content = await frontend_service.get_admin_content()
        else:
            content = "<div class='alert alert-warning'>Unbekannter Bereich</div>"
        
        return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"Error loading content for section {section}", error=str(e))
        return HTMLResponse(content=f"<div class='alert alert-danger'>Fehler beim Laden: {str(e)}</div>")

@app.get("/api/monitoring/{path:path}")
async def proxy_monitoring(path: str):
    return await frontend_service.proxy_request("monitoring", f"/{path}")

@app.get("/api/broker/{path:path}")
async def proxy_broker(path: str, request: Request):
    query_params = dict(request.query_params)
    return await frontend_service.proxy_request("broker", f"/{path}", params=query_params)

@app.get("/api/event_bus/{path:path}")
async def proxy_event_bus(path: str):
    return await frontend_service.proxy_request("event_bus", f"/{path}")

@app.get("/api/core/{path:path}")
async def proxy_core(path: str):
    return await frontend_service.proxy_request("core", f"/{path}")

@app.post("/api/predictions/refresh")
async def refresh_predictions():
    """Trigger ML-Pipeline für neue Gewinn-Vorhersagen"""
    try:
        # Simuliere ML-Berechnung (später mit echtem ML-Backend ersetzen)
        import random
        import time
        from datetime import datetime
        
        # Simuliere Berechnungszeit
        await asyncio.sleep(2)
        
        # Generiere neue Vorhersage-Daten (später aus ML-Pipeline)
        timeframes = ['7D', '1M', '3M', '6M', '1Y']
        stocks = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA', 'AMZN', 'META']
        
        predictions = {}
        for timeframe in timeframes:
            predictions[timeframe] = {
                'best_stock': random.choice(stocks),
                'predicted_return': round(random.uniform(2.0, 25.0), 1),
                'confidence': round(random.uniform(75.0, 95.0), 1),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # TODO: Daten in Datenbank speichern
        # await save_predictions_to_db(predictions)
        
        return {
            "status": "success",
            "message": "ML-Vorhersagen erfolgreich aktualisiert",
            "timestamp": datetime.utcnow().isoformat(),
            "predictions": predictions,
            "next_update": "Nächste automatische Aktualisierung in 4 Stunden"
        }
        
    except Exception as e:
        logger.error("Error refreshing predictions", error=str(e))
        raise HTTPException(status_code=500, detail=f"Fehler bei ML-Berechnung: {str(e)}")

@app.get("/api/predictions/latest")
async def get_latest_predictions():
    """Aktuelle Vorhersage-Daten abrufen"""
    try:
        # TODO: Aus Datenbank laden statt statische Daten
        from datetime import datetime, timedelta
        
        # Simuliere Datenbank-Abfrage
        predictions = {
            '7D': {'best_stock': 'AAPL', 'predicted_return': 4.2, 'confidence': 87.3, 'timestamp': datetime.utcnow().isoformat()},
            '1M': {'best_stock': 'MSFT', 'predicted_return': 8.7, 'confidence': 89.1, 'timestamp': datetime.utcnow().isoformat()},
            '3M': {'best_stock': 'NVDA', 'predicted_return': 18.5, 'confidence': 92.3, 'timestamp': datetime.utcnow().isoformat()},
            '6M': {'best_stock': 'GOOGL', 'predicted_return': 24.1, 'confidence': 88.7, 'timestamp': datetime.utcnow().isoformat()},
            '1Y': {'best_stock': 'TSLA', 'predicted_return': 35.3, 'confidence': 85.9, 'timestamp': datetime.utcnow().isoformat()}
        }
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "predictions": predictions,
            "last_calculation": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "ml_model_version": "v2.1-ensemble"
        }
        
    except Exception as e:
        logger.error("Error getting latest predictions", error=str(e))
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden der Vorhersagen: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open(frontend_service.static_path / "index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Enhanced Frontend loading...</h1>"

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Enhanced Frontend Service...")
    await frontend_service.initialize()
    logger.info("Enhanced Frontend Service started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Enhanced Frontend Service...")
    await frontend_service.cleanup()
    logger.info("Enhanced Frontend Service stopped")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8084, reload=False, access_log=True)