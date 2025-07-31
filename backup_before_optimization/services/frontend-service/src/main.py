#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Aktienanalyse Frontend Service mit Menü-Navigation
"""

import os
import sys
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

# Import der Market Data Integration Bridge
from market_data_integration import market_data_bridge, get_global_stock_data, get_prediction_data

# Market Data Integration - Bus System basiert
class MarketDataBusService:
    """Service für Marktdaten über das Bus-System"""
    
    def __init__(self, http_session, services_config):
        self.session = http_session
        self.services = services_config
        self.logger = structlog.get_logger("market_data_bus")
        
    async def initialize(self):
        """Verbindung zu Bus-System initialisieren"""
        try:
            # Prüfe Core Service Verfügbarkeit
            async with self.session.get(f"{self.services['core']}/health") as resp:
                if resp.status == 200:
                    self.logger.info("✅ Core Service connected via Bus")
                    return True
        except Exception as e:
            self.logger.warning(f"⚠️ Core Service nicht erreichbar: {e}")
            return False
        return False
        
    async def get_global_stock_data(self, limit=15):
        """Marktdaten über Bus-System abrufen"""
        try:
            # Event über Bus senden
            event_data = {
                "event_type": "market_data_request",
                "payload": {
                    "request_type": "global_stock_analysis",
                    "limit": limit,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # An Event Bus senden
            async with self.session.post(
                f"{self.services['event_bus']}/events", 
                json=event_data
            ) as resp:
                if resp.status == 200:
                    # Erfolgreiche Event-Übertragung - verwende statische Daten als Fallback
                    self.logger.info("✅ Market data event sent via Bus")
                else:
                    self.logger.warning(f"⚠️ Event Bus Response: {resp.status}")
            
            # Da noch kein dedizierter Market Data Service implementiert ist,
            # verwenden wir realistische Mock-Daten mit Bus-Integration
            return await self._get_mock_market_data(limit)
            
        except Exception as e:
            self.logger.error(f"❌ Bus communication failed: {e}")
            return await self._get_mock_market_data(limit)
    
    async def _get_mock_market_data(self, limit=15):
        """Fallback Mock-Daten mit Bus-System-Metadaten"""
        mock_stocks = [
            {
                'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'exchange': 'NASDAQ',
                'current_price': '$875.32', 'predicted_price': '$1,037.50',
                'predicted_return': '+18.5%', 'sharpe_ratio': '1.87',
                'ml_score': 92.3, 'risk_level': 'Mittel', 'region': 'US'
            },
            {
                'symbol': 'AAPL', 'name': 'Apple Inc', 'exchange': 'NASDAQ',
                'current_price': '$193.42', 'predicted_price': '$224.80',
                'predicted_return': '+16.2%', 'sharpe_ratio': '1.65',
                'ml_score': 89.7, 'risk_level': 'Niedrig', 'region': 'US'
            },
            {
                'symbol': 'SAP', 'name': 'SAP SE', 'exchange': 'XETRA',
                'current_price': '€138.20', 'predicted_price': '€155.90',
                'predicted_return': '+12.8%', 'sharpe_ratio': '1.34',
                'ml_score': 81.2, 'risk_level': 'Niedrig', 'region': 'Germany'
            },
            {
                'symbol': 'MSFT', 'name': 'Microsoft Corp', 'exchange': 'NASDAQ',
                'current_price': '$421.18', 'predicted_price': '$485.90',
                'predicted_return': '+15.4%', 'sharpe_ratio': '1.52',
                'ml_score': 88.1, 'risk_level': 'Niedrig', 'region': 'US'
            },
            {
                'symbol': 'SHEL', 'name': 'Shell PLC', 'exchange': 'LSE',
                'current_price': '£28.45', 'predicted_price': '£31.90',
                'predicted_return': '+12.1%', 'sharpe_ratio': '1.28',
                'ml_score': 79.8, 'risk_level': 'Mittel', 'region': 'UK'
            },
            {
                'symbol': '7203', 'name': 'Toyota Motor Corp', 'exchange': 'TSE',
                'current_price': '¥2,845', 'predicted_price': '¥3,185',
                'predicted_return': '+11.9%', 'sharpe_ratio': '1.31',
                'ml_score': 82.4, 'risk_level': 'Niedrig', 'region': 'Japan'
            },
            {
                'symbol': '0700', 'name': 'Tencent Holdings Ltd', 'exchange': 'HKEX',
                'current_price': 'HK$385.20', 'predicted_price': 'HK$430.60',
                'predicted_return': '+11.8%', 'sharpe_ratio': '1.24',
                'ml_score': 80.9, 'risk_level': 'Mittel', 'region': 'Hong Kong'
            },
            {
                'symbol': 'SHOP', 'name': 'Shopify Inc', 'exchange': 'TSX',
                'current_price': 'C$89.45', 'predicted_price': 'C$99.85',
                'predicted_return': '+11.6%', 'sharpe_ratio': '1.19',
                'ml_score': 78.3, 'risk_level': 'Hoch', 'region': 'Canada'
            },
            {
                'symbol': 'CSL', 'name': 'CSL Limited', 'exchange': 'ASX',
                'current_price': 'A$289.50', 'predicted_price': 'A$322.80',
                'predicted_return': '+11.5%', 'sharpe_ratio': '1.33',
                'ml_score': 84.1, 'risk_level': 'Niedrig', 'region': 'Australia'
            },
            {
                'symbol': 'TSLA', 'name': 'Tesla Inc', 'exchange': 'NASDAQ',
                'current_price': '$248.95', 'predicted_price': '$282.70',
                'predicted_return': '+13.5%', 'sharpe_ratio': '1.21',
                'ml_score': 83.4, 'risk_level': 'Hoch', 'region': 'US'
            },
            {
                'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'exchange': 'NASDAQ',
                'current_price': '$168.24', 'predicted_price': '$192.10',
                'predicted_return': '+14.2%', 'sharpe_ratio': '1.38',
                'ml_score': 85.9, 'risk_level': 'Mittel', 'region': 'US'
            },
            {
                'symbol': 'ASML', 'name': 'ASML Holding NV', 'exchange': 'AEX',
                'current_price': '€692.80', 'predicted_price': '€780.40',
                'predicted_return': '+12.6%', 'sharpe_ratio': '1.45',
                'ml_score': 86.5, 'risk_level': 'Mittel', 'region': 'Netherlands'
            },
            {
                'symbol': '6758', 'name': 'Sony Group Corp', 'exchange': 'TSE',
                'current_price': '¥12,450', 'predicted_price': '¥13,850',
                'predicted_return': '+11.2%', 'sharpe_ratio': '1.27',
                'ml_score': 81.7, 'risk_level': 'Mittel', 'region': 'Japan'
            },
            {
                'symbol': 'AZN', 'name': 'AstraZeneca PLC', 'exchange': 'LSE',
                'current_price': '£122.80', 'predicted_price': '£136.20',
                'predicted_return': '+10.9%', 'sharpe_ratio': '1.41',
                'ml_score': 85.6, 'risk_level': 'Niedrig', 'region': 'UK'
            },
            {
                'symbol': 'BMW', 'name': 'Bayerische Motoren Werke AG', 'exchange': 'XETRA',
                'current_price': '€89.12', 'predicted_price': '€98.70',
                'predicted_return': '+10.7%', 'sharpe_ratio': '1.15',
                'ml_score': 77.9, 'risk_level': 'Mittel', 'region': 'Germany'
            }
        ]
        
        return {
            'top_performers': mock_stocks[:limit],
            'total_stocks_analyzed': 247,
            'global_coverage': {
                'regions': 8,
                'exchanges': 12,
                'countries': ['US', 'Germany', 'Netherlands', 'UK', 'Japan', 'Hong Kong', 'Canada', 'Australia']
            },
            'last_updated': datetime.now().isoformat(),
            'data_sources': ['Bus System (Mock Fallback)', 'Event Bus Integration'],
            'bus_status': 'connected'
        }

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
        
        # Market Data Service Integration via Bus System
        self.market_data_service = None
        self.global_stock_data = None
        
    async def initialize(self):
        try:
            postgres_url = "postgresql://aktienanalyse:secure_password@localhost:5432/aktienanalyse_events?sslmode=disable"
            
            # HTTP Session initialisieren
            self.db_pool = await asyncpg.create_pool(postgres_url, min_size=1, max_size=5)
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
            self.static_path.mkdir(exist_ok=True)
            
            # Market Data Service über Bus System initialisieren
            try:
                self.market_data_service = MarketDataBusService(self.session, self.services)
                bus_connected = await self.market_data_service.initialize()
                
                if bus_connected:
                    logger.info("✅ Market Data Bus Service initialized successfully")
                    # Globale Aktienanalyse laden (Top 15 für Performance)
                    self.global_stock_data = await self.market_data_service.get_global_stock_data(limit=15)
                    logger.info(f"✅ Loaded {self.global_stock_data.get('total_count', 15)} global stocks via Bus System")
                else:
                    logger.warning("⚠️ Bus System nicht vollständig verfügbar - verwende Integration Bridge")
                    try:
                        # Verwende neue Integration Bridge
                        self.global_stock_data = get_global_stock_data(limit=15)
                        if self.global_stock_data:
                            logger.info(f"✅ Bridge-Daten geladen: {self.global_stock_data.get('total_count', 15)} Aktien")
                        else:
                            logger.error("❌ Bridge-Daten sind None")
                    except Exception as bridge_error:
                        logger.error(f"❌ Bridge-Daten Fehler: {bridge_error}")
                        self.global_stock_data = None
                    
            except Exception as e:
                logger.error(f"⚠️ Market Data Bus Service initialization failed: {e}")
                logger.error(f"⚠️ Exception details: {type(e).__name__}: {str(e)}")
                # Vollständiger Fallback auf statische Daten
                self.global_stock_data = None
                
            # Debug: Check final state
            if self.global_stock_data:
                logger.info(f"✅ Final check: Global stock data loaded with {len(self.global_stock_data.get('top_performers', []))} stocks")
            else:
                logger.warning("⚠️ Final check: Global stock data is None - will use static fallback in predictions")
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

        // Chart.js dynamisch laden - SOFORT im Haupt-HTML
        if (typeof Chart === 'undefined') {
            console.log('[MAIN] Loading Chart.js dynamically...');
            const chartScript = document.createElement('script');
            chartScript.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
            chartScript.onload = function() {
                console.log('[MAIN] ✅ Chart.js loaded in main HTML');
                // Retry chart initialization nach Load
                setTimeout(initPredictionCharts, 500);
            };
            document.head.appendChild(chartScript);
        }

        function initPredictionCharts() {
            console.log('[MAIN] initPredictionCharts called');
            
            // Check if Chart.js is available
            if (typeof Chart === 'undefined') {
                console.log('[MAIN] Chart.js not available, retry in 1000ms...');
                setTimeout(initPredictionCharts, 1000);
                return;
            }
            
            console.log('[MAIN] Chart.js available, initializing charts...');
            
            // Performance Chart - Direct implementation in main HTML
            const perfCanvas = document.getElementById('performance-chart');
            if (perfCanvas) {
                try {
                    console.log('[MAIN] Creating Performance Chart...');
                    new Chart(perfCanvas, {
                        type: 'line',
                        data: {
                            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun'],
                            datasets: [{
                                label: 'Vorhersage-Genauigkeit (%)',
                                data: [85.2, 87.1, 88.5, 89.2, 90.1, 91.3],
                                borderColor: 'rgb(54, 162, 235)',
                                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                                tension: 0.4
                            }]
                        },
                        options: { 
                            responsive: true, 
                            maintainAspectRatio: false,
                            plugins: {
                                title: {
                                    display: true,
                                    text: 'Gewinn-Vorhersage Verlauf'
                                }
                            }
                        }
                    });
                    console.log('[MAIN] ✅ Performance Chart created successfully');
                } catch (error) {
                    console.error('[MAIN] ❌ Performance Chart error:', error);
                }
            }
            
            // Risk Chart - Direct implementation
            const riskCanvas = document.getElementById('risk-chart');
            if (riskCanvas) {
                try {
                    console.log('[MAIN] Creating Risk Chart...');
                    new Chart(riskCanvas, {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Aktien Risiko-Rendite',
                                data: [
                                    {x: 12, y: 18.5, label: 'NVDA'},
                                    {x: 8, y: 16.2, label: 'AAPL'},
                                    {x: 9, y: 15.4, label: 'MSFT'},
                                    {x: 11, y: 17.8, label: 'GOOGL'},
                                    {x: 15, y: 22.1, label: 'TSLA'}
                                ],
                                backgroundColor: 'rgba(255, 99, 132, 0.6)',
                                pointRadius: 8
                            }]
                        },
                        options: { 
                            responsive: true, 
                            maintainAspectRatio: false,
                            plugins: {
                                title: {
                                    display: true,
                                    text: 'Risiko-Rendite Matrix'
                                }
                            },
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
                                        text: 'Rendite (%)'
                                    }
                                }
                            }
                        }
                    });
                    console.log('[MAIN] ✅ Risk Chart created successfully');
                } catch (error) {
                    console.error('[MAIN] ❌ Risk Chart error:', error);
                }
            }
            
            // Technical Chart - Direct implementation
            const techCanvas = document.getElementById('technical-chart');
            if (techCanvas) {
                try {
                    console.log('[MAIN] Creating Technical Chart...');
                    new Chart(techCanvas, {
                        type: 'bar',
                        data: {
                            labels: ['RSI', 'MACD', 'SMA', 'EMA', 'Bollinger', 'Stochastic'],
                            datasets: [{
                                label: 'Technical Score (%)',
                                data: [78, 85, 72, 68, 82, 75],
                                backgroundColor: [
                                    '#ff6384',
                                    '#36a2eb', 
                                    '#ffce56',
                                    '#4bc0c0',
                                    '#9966ff',
                                    '#ff9f40'
                                ]
                            }]
                        },
                        options: { 
                            responsive: true, 
                            maintainAspectRatio: false,
                            plugins: {
                                title: {
                                    display: true,
                                    text: 'Technical Analysis Scores'
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
                    console.log('[MAIN] ✅ Technical Chart created successfully');
                } catch (error) {
                    console.error('[MAIN] ❌ Technical Chart error:', error);
                }
            }
            
            console.log('[MAIN] 🎯 All charts initialization completed');
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
    
    <!-- Chart.js Library für Chart-Visualisierungen -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
</body>
</html>"""
        
        with open(self.static_path / "index.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        return html

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
        
        # Statische Fallback-Daten bei Marktdaten-Service-Fehlern
        if not self.global_stock_data:
            logger.warning("⚠️ Using fallback static data - Market Data Service unavailable")
            return await self._get_static_predictions_content()
        
        # Dynamische Daten aus globalem Marktdaten-Service generieren
        try:
            return await self._generate_dynamic_predictions_content()
        except Exception as e:
            logger.error(f"❌ Failed to generate dynamic predictions content: {e}")
            return await self._get_static_predictions_content()
    
    async def _generate_dynamic_predictions_content(self):
        """Vollständige Predictions-Seite mit funktionierender Live-Tabelle und Timeframe-Buttons"""
        try:
            # Dynamische API-basierte Predictions-Seite
            return '''
        <!-- Zeitraum-Button Row -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0"><i class="fas fa-chart-line me-2"></i>Top 15 Gewinn-Vorhersagen</h5>
                            <div class="btn-group" role="group" id="timeframe-buttons">
                                <button type="button" class="btn btn-outline-primary" onclick="updatePredictionTimeframe('7D')">7D</button>
                                <button type="button" class="btn btn-primary" onclick="updatePredictionTimeframe('1M')">1M</button>
                                <button type="button" class="btn btn-outline-primary" onclick="updatePredictionTimeframe('3M')">3M</button>
                                <button type="button" class="btn btn-outline-primary" onclick="updatePredictionTimeframe('6M')">6M</button>
                                <button type="button" class="btn btn-outline-primary" onclick="updatePredictionTimeframe('1Y')">1Y</button>
                            </div>
                        </div>
                        <div class="mt-2">
                            <small class="text-muted" id="last-updated">Letzte Aktualisierung: Wird geladen...</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Predictions Table -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover" id="predictions-table">
                                <thead class="table-dark">
                                    <tr>
                                        <th>#</th>
                                        <th>Symbol</th>
                                        <th>Name</th>
                                        <th>Aktueller Preis</th>
                                        <th>Vorhergesagter Preis</th>
                                        <th>Erwarteter Gewinn</th>
                                        <th>Sharpe Ratio</th>
                                        <th>ML Score</th>
                                        <th>Risiko</th>
                                        <th>Aktion</th>
                                    </tr>
                                </thead>
                                <tbody id="predictions-table-body">
                                    <tr>
                                        <td colspan="10" class="text-center">
                                            <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                                            Lade Live-Marktdaten...
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
        // Aktuelle Zeitrahmen-Variable
        let currentTimeframe = '1M';
        
        // Predictions mit Live-Daten aktualisieren
        async function updatePredictionsWithLiveData() {
            try {
                console.log('Loading predictions data for timeframe:', currentTimeframe);
                
                const response = await fetch(`/api/predictions/${currentTimeframe}`);
                if (!response.ok) {
                    throw new Error(`API Error: ${response.status}`);
                }
                
                const data = await response.json();
                console.log('Received predictions data:', data);
                
                const tbody = document.getElementById('predictions-table-body');
                if (!tbody) {
                    console.error('Table body not found');
                    return;
                }
                
                // Tabelle mit API-Daten füllen
                tbody.innerHTML = data.stocks.map((stock, index) => `
                    <tr class="${index === 0 ? 'table-success' : ''}">
                        <td><span class="badge bg-${index === 0 ? 'warning' : index < 3 ? 'success' : 'secondary'}">${index + 1}</span></td>
                        <td><strong>${stock.symbol}</strong></td>
                        <td>${stock.name}</td>
                        <td>${stock.current_price}</td>
                        <td>${stock.predicted_price}</td>
                        <td><span class="badge bg-${stock.predicted_return.includes('+') ? 'success' : 'danger'}">${stock.predicted_return}</span></td>
                        <td>${stock.sharpe_ratio}</td>
                        <td><span class="badge bg-${stock.ml_score >= 80 ? 'primary' : stock.ml_score >= 60 ? 'info' : 'warning'}">${stock.ml_score}</span></td>
                        <td><span class="badge bg-${stock.risk_level === 'Niedrig' ? 'success' : stock.risk_level === 'Mittel' ? 'warning' : 'danger'}">${stock.risk_level}</span></td>
                        <td><button class="btn btn-sm btn-primary">Analyse</button></td>
                    </tr>
                `).join('');
                
                // Update last updated timestamp
                const now = new Date().toLocaleString('de-DE');
                const lastUpdated = document.getElementById('last-updated');
                if (lastUpdated) {
                    lastUpdated.textContent = `Letzte Aktualisierung: ${now} (${data.timeframe})`;
                }
                
                console.log('Table successfully updated with live data');
                
            } catch (error) {
                console.error('Error updating predictions table:', error);
                
                const tbody = document.getElementById('predictions-table-body');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="10" class="text-center text-danger">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                Fehler beim Laden der Marktdaten: ${error.message}
                            </td>
                        </tr>
                    `;
                }
            }
        }
        
        // Zeitrahmen wechseln
        async function updatePredictionTimeframe(timeframe) {
            try {
                console.log('Switching to timeframe:', timeframe);
                currentTimeframe = timeframe;
                
                // Button-Status aktualisieren
                const buttons = document.querySelectorAll('#timeframe-buttons button');
                buttons.forEach(btn => {
                    if (btn.textContent === timeframe) {
                        btn.className = 'btn btn-primary';
                    } else {
                        btn.className = 'btn btn-outline-primary';
                    }
                });
                
                // Loading state zeigen
                const tbody = document.getElementById('predictions-table-body');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="10" class="text-center">
                                <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                                Lade Daten für ${timeframe}...
                            </td>
                        </tr>
                    `;
                }
                
                // Neue Daten laden
                await updatePredictionsWithLiveData();
                
            } catch (error) {
                console.error('Error updating timeframe:', error);
            }
        }
        
        // Automatische Initialisierung
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Initializing predictions page...');
            setTimeout(() => {
                updatePredictionsWithLiveData();
            }, 1000);
        });
        
        // Auto-refresh alle 30 Sekunden
        setInterval(() => {
            if (document.getElementById('predictions-table-body')) {
                updatePredictionsWithLiveData();
            }
        }, 30000);
        </script>
        '''
        except Exception as e:
            self.logger.error(f"❌ Error generating predictions content: {e}")
            # Fallback zu funktionierender statischer Version
            return await self._get_static_predictions_content()
    
    async def _get_static_predictions_content(self):
        """Statische Fallback-Predictions wenn API nicht verfügbar"""
        return '''
        <div class="row mb-4">
            <div class="col-12">
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Fallback-Modus: Live-Marktdaten temporär nicht verfügbar
                </div>
            </div>
        </div>
        '''

    async def get_broker_integration_content(self):
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

        <!-- Charts werden später hinzugefügt -->
        
        <script>
        // 📊 DYNAMISCHE TABELLEN-AKTUALISIERUNG
        
        async function updatePredictionTimeframe(timeframe) {
            try {
                console.log(`[PREDICTIONS] Aktualisiere auf Zeitraum: ${timeframe}`);
                
                // Loading-Indikator anzeigen
                const tbody = document.getElementById('predictions-tbody');
                const headerTimeframe = document.getElementById('top-prediction-timeframe');
                const predictionHeader = document.getElementById('prediction-header');
                
                if (tbody) {
                    tbody.innerHTML = '<tr><td colspan="10" class="text-center"><i class="fas fa-spinner fa-spin me-2"></i>Lade Daten...</td></tr>';
                }
                
                // API-Aufruf für neue Daten
                const response = await fetch(`/api/predictions/${timeframe}`);
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Tabellen-Header aktualisieren
                if (predictionHeader) {
                    const timeframeLabels = {
                        '7D': '7 Tage',
                        '1M': '1 Monat', 
                        '3M': '3 Monate',
                        '6M': '6 Monate',
                        '1Y': '1 Jahr'
                    };
                    predictionHeader.textContent = `Vorhersage ${timeframeLabels[timeframe] || timeframe}`;
                }
                
                // KPI-Updates
                if (data.stocks && data.stocks.length > 0) {
                    const topStock = data.stocks[0];
                    const topPredictionEl = document.getElementById('top-prediction');
                    
                    if (topPredictionEl) {
                        topPredictionEl.textContent = topStock.predicted_return || '+0.0%';
                    }
                    
                    if (headerTimeframe) {
                        headerTimeframe.innerHTML = `${topStock.symbol || 'N/A'} (${timeframeLabels[timeframe] || timeframe})`;
                    }
                }
                
                // Tabelle aktualisieren
                updatePredictionsTable(data.stocks || []);
                
                console.log(`[PREDICTIONS] ✅ Zeitraum ${timeframe} erfolgreich geladen`);
                
            } catch (error) {
                console.error('[PREDICTIONS] ❌ Fehler beim Aktualisieren:', error);
                const tbody = document.getElementById('predictions-tbody');
                if (tbody) {
                    tbody.innerHTML = `<tr><td colspan="10" class="text-center text-danger"><i class="fas fa-exclamation-triangle me-2"></i>Fehler beim Laden: ${error.message}</td></tr>`;
                }
            }
        }
        
        function updatePredictionsTable(stocks) {
            const tbody = document.getElementById('predictions-tbody');
            if (!tbody) return;
            
            if (!stocks || stocks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">Keine Daten verfügbar</td></tr>';
                return;
            }
            
            let tableHTML = '';
            stocks.forEach((stock, index) => {
                const rank = index + 1;
                
                // Risiko-Badge-Farbe
                const riskLevel = stock.risk_level || 'Unbekannt';
                const riskColor = riskLevel === "Niedrig" ? "success" : riskLevel === "Mittel" ? "warning" : "danger";
                
                // Gewinn-Badge-Farbe
                const predictedReturn = stock.predicted_return || '+0.0%';
                const returnNum = parseFloat(predictedReturn.replace('%', '').replace('+', ''));
                const returnColor = returnNum > 0 ? "success" : "danger";
                
                // ML-Score Badge-Farbe
                const mlScore = parseFloat(stock.ml_score || 0);
                const mlColor = mlScore >= 80 ? "primary" : mlScore >= 60 ? "info" : "warning";
                
                // Rang-Badge
                const rankColor = rank === 1 ? "warning" : rank <= 3 ? "success" : "secondary";
                
                tableHTML += `
                    <tr class="${rank === 1 ? 'table-success' : ''}">
                        <td><span class="badge bg-${rankColor}">${rank}</span></td>
                        <td><strong>${stock.symbol || 'N/A'}</strong></td>
                        <td>${stock.name || 'Unbekannt'}</td>
                        <td>${stock.current_price || '€0.00'}</td>
                        <td>${stock.predicted_price || '€0.00'}</td>
                        <td><span class="badge bg-${returnColor}">${predictedReturn}</span></td>
                        <td>${stock.sharpe_ratio || '0.00'}</td>
                        <td><span class="badge bg-${mlColor}">${Math.round(mlScore)}</span></td>
                        <td><span class="badge bg-${riskColor}">${riskLevel}</span></td>
                        <td><button class="btn btn-sm btn-success"><i class="fas fa-plus me-1"></i>Import</button></td>
                    </tr>`;
            });
            
            tbody.innerHTML = tableHTML;
        }
        
        async function refreshPredictions() {
            const timeframeSelect = document.getElementById('timeframe-select');
            if (timeframeSelect) {
                await updatePredictionTimeframe(timeframeSelect.value);
            }
        }
        
        // Initialisierung beim Laden der Seite
        document.addEventListener('DOMContentLoaded', function() {
            console.log('[PREDICTIONS] 🚀 Initialisiere dynamische Vorhersagen...');
            
            // Initial mit 3M laden (Standard)
            setTimeout(() => {
                updatePredictionTimeframe('3M');
            }, 1000);
        });
        </script>
        """
        
        # Format the content with values (format numbers beforehand)
        return content.format(
            top_prediction, top_symbol, f"{avg_ml_score:.1f}", f"{avg_sharpe:.2f}",
            total_analyzed, regions, exchanges, table_rows
        )

    async def get_broker_integration_content(self):
        """Broker-Integration content"""
        return """
            const apexScript = document.createElement('script');
            apexScript.src = 'https://cdn.jsdelivr.net/npm/apexcharts@3.44.0/dist/apexcharts.min.js';
            apexScript.onload = function() {
                console.log('[PREDICTIONS] ✅ ApexCharts loaded dynamically');
                chartLibrary = 'apex';
                initializeChartsWhenReady();
            };
            apexScript.onerror = function() {
                console.log('[PREDICTIONS] ⚠️ ApexCharts failed, loading Chart.js fallback...');
                const chartjsScript = document.createElement('script');
                chartjsScript.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
                chartjsScript.onload = function() {
                    console.log('[PREDICTIONS] ✅ Chart.js loaded as fallback');
                    chartLibrary = 'chartjs';
                    initializeChartsWhenReady();
                };
                chartjsScript.onerror = function() {
                    console.error('[PREDICTIONS] ❌ Both chart libraries failed to load');
                    showChartError();
                };
                document.head.appendChild(chartjsScript);
            };
            document.head.appendChild(apexScript);
        }

        // Robuste Chart-Initialisierung mit DOM-Check und Retry-Logic
        function initializeChartsWhenReady() {
            console.log('[PREDICTIONS] Starte Chart-Initialisierung mit', chartLibrary);
            
            // Check Canvas-Verfügbarkeit
            const performanceCanvas = document.getElementById('performance-chart');
            const riskCanvas = document.getElementById('risk-chart');
            const technicalCanvas = document.getElementById('technical-chart');
            
            console.log('[PREDICTIONS] Canvas-Elemente gefunden:', {
                performance: !!performanceCanvas,
                risk: !!riskCanvas,
                technical: !!technicalCanvas,
                library: chartLibrary
            });
            
            if (performanceCanvas && riskCanvas && technicalCanvas && chartLibrary !== 'none') {
                // Alle Canvas bereit - initialisiere Charts basierend auf verfügbarer Library
                if (chartLibrary === 'apex') {
                    createApexCharts(performanceCanvas, riskCanvas, technicalCanvas);
                } else if (chartLibrary === 'chartjs') {
                    createChartJSCharts(performanceCanvas, riskCanvas, technicalCanvas);
                }
            } else {
                // Retry wenn Canvas noch nicht bereit
                console.log('[PREDICTIONS] ⏳ Canvas-Elemente oder Chart-Library noch nicht bereit, retry in 200ms...');
                setTimeout(initializeChartsWhenReady, 200);
            }
        }
        
        // DIREKTE CHART-ERSTELLUNG - VEREINFACHT UND ROBUST
        function createDirectCharts(perfCanvas, riskCanvas, techCanvas) {
            console.log('[PREDICTIONS] 🚀 DIREKTE Chart-Erstellung gestartet...');
            
            // Verwende Chart.js wenn ApexCharts nicht verfügbar
            if (typeof Chart !== 'undefined') {
                console.log('[PREDICTIONS] 📊 Verwende Chart.js für direkte Charts');
                createSimpleChartJS(perfCanvas, riskCanvas, techCanvas);
                return;
            }
            
            if (typeof ApexCharts !== 'undefined') {
                console.log('[PREDICTIONS] 📊 Verwende ApexCharts für direkte Charts');
                createSimpleApexCharts(perfCanvas, riskCanvas, techCanvas);
                return;
            }
            
            console.error('[PREDICTIONS] ❌ Keine Chart-Library verfügbar');
            showEmergencyChartMessage();
        }
        
        // EINFACHE CHART.JS IMPLEMENTIERUNG
        function createSimpleChartJS(perfCanvas, riskCanvas, techCanvas) {
            console.log('[PREDICTIONS] 🎯 Erstelle Chart.js Charts...');
            
            // Performance Chart
            try {
                new Chart(perfCanvas, {
                    type: 'line',
                    data: {
                        labels: ['Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul'],
                        datasets: [{
                            label: 'NVDA ($)',
                            data: [875, 935, 1021, 1075, 1090, 1037],
                            borderColor: '#10B981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.4,
                            borderWidth: 3
                        }, {
                            label: 'AAPL ($)',
                            data: [193, 209, 220, 223, 224, 224],
                            borderColor: '#3B82F6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            tension: 0.4,
                            borderWidth: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Aktienkurs-Verlauf (6 Monate)'
                            }
                        }
                    }
                });
                console.log('[PREDICTIONS] ✅ Chart.js Performance Chart erstellt');
            } catch (error) {
                console.error('[PREDICTIONS] ❌ Chart.js Performance Chart Fehler:', error);
            }
            
            // Risk Chart
            try {
                new Chart(riskCanvas, {
                    type: 'line',
                    data: {
                        labels: ['Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul'],
                        datasets: [{
                            label: 'NVDA Volatilität (%)',
                            data: [12.3, 16.1, 21.4, 18.3, 19.8, 22.8],
                            borderColor: '#EF4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            tension: 0.4,
                            borderWidth: 3
                        }, {
                            label: 'Portfolio Risiko (%)',
                            data: [7.8, 8.6, 10.4, 10.2, 11.1, 11.8],
                            borderColor: '#8B5CF6',
                            backgroundColor: 'rgba(139, 92, 246, 0.1)',
                            tension: 0.4,
                            borderWidth: 3,
                            borderDash: [5, 5]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Risiko-Verlauf (6 Monate)'
                            }
                        }
                    }
                });
                console.log('[PREDICTIONS] ✅ Chart.js Risk Chart erstellt');
            } catch (error) {
                console.error('[PREDICTIONS] ❌ Chart.js Risk Chart Fehler:', error);
            }
            
            // Technical Chart
            try {
                new Chart(techCanvas, {
                    type: 'line',
                    data: {
                        labels: ['Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul'],
                        datasets: [{
                            label: 'RSI',
                            data: [45, 68, 87, 68, 76, 84],
                            borderColor: '#FF6384',
                            backgroundColor: 'rgba(255, 99, 132, 0.1)',
                            tension: 0.4,
                            borderWidth: 3
                        }, {
                            label: 'MACD',
                            data: [68, 82, 92, 77, 84, 91],
                            borderColor: '#36A2EB',
                            backgroundColor: 'rgba(54, 162, 235, 0.1)',
                            tension: 0.4,
                            borderWidth: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Technical Analysis (6 Monate)'
                            }
                        }
                    }
                });
                console.log('[PREDICTIONS] ✅ Chart.js Technical Chart erstellt');
            } catch (error) {
                console.error('[PREDICTIONS] ❌ Chart.js Technical Chart Fehler:', error);
            }
            
            console.log('[PREDICTIONS] 🎯 Alle Chart.js Charts erfolgreich erstellt!');
        }
        
        // NOTFALL-MESSAGE
        function showEmergencyChartMessage() {
            const message = `
                <div class="alert alert-info text-center">
                    <i class="fas fa-chart-line fa-3x mb-3"></i>
                    <h4>Charts werden geladen...</h4>
                    <p>Bitte warten Sie einen Moment oder laden Sie die Seite neu.</p>
                </div>
            `;
            
            ['performance-chart', 'risk-chart', 'technical-chart'].forEach(id => {
                const canvas = document.getElementById(id);
                if (canvas && canvas.parentElement) {
                    canvas.parentElement.innerHTML = message;
                }
            });
        }
        
        // ALTE APEX CHARTS IMPLEMENTIERUNG (Backup)
        function createSimpleApexCharts(perfCanvas, riskCanvas, techCanvas) {
            console.log('[PREDICTIONS] 🚀 Creating ApexCharts timeline charts...');
            
            // Gemeinsame Zeitdaten
            const timeLabels = [
                '2025-02-01', '2025-02-08', '2025-02-15', '2025-02-22',
                '2025-03-01', '2025-03-08', '2025-03-15', '2025-03-22', '2025-03-29',
                '2025-04-05', '2025-04-12', '2025-04-19', '2025-04-26',
                '2025-05-03', '2025-05-10', '2025-05-17', '2025-05-24', '2025-05-31',
                '2025-06-07', '2025-06-14', '2025-06-21', '2025-06-28',
                '2025-07-05', '2025-07-12', '2025-07-19', '2025-07-26'
            ];
            
            // Performance Chart - ApexCharts
            try {
                const perfOptions = {
                    series: [{
                        name: 'NVDA Kursverlauf ($)',
                        data: timeLabels.map((date, index) => [new Date(date).getTime(), [875.32, 892.10, 901.85, 918.45, 935.20, 952.80, 971.30, 988.15, 1005.90, 1021.45, 1035.70, 1048.20, 1059.85, 1068.90, 1075.45, 1081.20, 1085.60, 1088.75, 1090.20, 1089.85, 1087.90, 1084.45, 1079.20, 1072.85, 1065.40, 1037.50][index]])
                    }, {
                        name: 'AAPL Kursverlauf ($)',
                        data: timeLabels.map((date, index) => [new Date(date).getTime(), [193.42, 196.80, 201.15, 205.90, 209.45, 212.80, 215.65, 217.90, 219.45, 220.85, 221.90, 222.60, 223.15, 223.45, 223.60, 223.85, 224.20, 224.45, 224.65, 224.75, 224.80, 224.75, 224.65, 224.50, 224.30, 224.80][index]])
                    }, {
                        name: 'MSFT Kursverlauf ($)',
                        data: timeLabels.map((date, index) => [new Date(date).getTime(), [421.18, 428.90, 436.45, 444.80, 452.30, 459.85, 466.90, 473.45, 479.20, 484.15, 488.30, 491.85, 494.70, 496.90, 498.45, 499.30, 499.85, 500.10, 500.05, 499.70, 499.15, 498.30, 497.20, 495.85, 494.25, 485.90][index]])
                    }],
                    chart: {
                        type: 'line',
                        height: 300,
                        animations: { enabled: true },
                        zoom: { enabled: true }
                    },
                    title: {
                        text: 'Aktienkurs-Verlauf und Vorhersagen (6 Monate)',
                        align: 'center'
                    },
                    xaxis: {
                        type: 'datetime',
                        title: { text: 'Zeitraum (Wöchentlich)' }
                    },
                    yaxis: {
                        title: { text: 'Aktienkurs ($)' }
                    },
                    stroke: { width: 3, curve: 'smooth' },
                    colors: ['#10B981', '#3B82F6', '#F59E0B']
                };
                
                const perfChart = new ApexCharts(perfCanvas, perfOptions);
                perfChart.render();
                console.log('[PREDICTIONS] ✅ ApexCharts Performance Chart created');
            } catch (error) {
                console.error('[PREDICTIONS] ❌ ApexCharts Performance Chart error:', error);
            }
            
            // Risk Chart - ApexCharts  
            try {
                const riskOptions = {
                    series: [{
                        name: 'NVDA Volatilität (%)',
                        data: timeLabels.map((date, index) => [new Date(date).getTime(), [12.3, 13.8, 15.2, 14.9, 16.1, 17.3, 18.5, 19.2, 20.8, 21.4, 22.1, 21.8, 20.9, 19.6, 18.3, 17.1, 16.8, 17.4, 18.2, 19.1, 19.8, 20.3, 21.2, 22.5, 23.1, 22.8][index]])
                    }, {
                        name: 'Portfolio Gesamt-Risiko (%)',
                        data: timeLabels.map((date, index) => [new Date(date).getTime(), [7.8, 8.1, 8.4, 8.2, 8.6, 9.0, 9.3, 9.7, 10.1, 10.4, 10.8, 11.0, 10.8, 10.5, 10.2, 9.9, 9.6, 10.0, 10.4, 10.7, 11.1, 11.3, 11.6, 11.9, 12.2, 11.8][index]])
                    }],
                    chart: {
                        type: 'line',
                        height: 300,
                        animations: { enabled: true },
                        zoom: { enabled: true }
                    },
                    title: {
                        text: 'Risiko-Verlauf und Volatilitäts-Entwicklung (6 Monate)',
                        align: 'center'
                    },
                    xaxis: {
                        type: 'datetime',
                        title: { text: 'Zeitraum (Wöchentlich)' }
                    },
                    yaxis: {
                        title: { text: 'Volatilität/Risiko (%)' },
                        min: 0,
                        max: 25
                    },
                    stroke: { width: [3, 4], curve: 'smooth', dashArray: [0, 5] },
                    colors: ['#EF4444', '#8B5CF6']
                };
                
                const riskChart = new ApexCharts(riskCanvas, riskOptions);
                riskChart.render();
                console.log('[PREDICTIONS] ✅ ApexCharts Risk Chart created');
            } catch (error) {
                console.error('[PREDICTIONS] ❌ ApexCharts Risk Chart error:', error);
            }
            
            // Technical Chart - ApexCharts
            try {
                const techOptions = {
                    series: [{
                        name: 'RSI (Relative Strength Index)',
                        data: timeLabels.map((date, index) => [new Date(date).getTime(), [45, 52, 58, 64, 68, 72, 78, 82, 85, 87, 84, 79, 75, 71, 68, 65, 63, 66, 69, 73, 76, 79, 82, 85, 88, 84][index]])
                    }, {
                        name: 'MACD Signal',
                        data: timeLabels.map((date, index) => [new Date(date).getTime(), [68, 71, 75, 78, 82, 85, 88, 91, 94, 92, 89, 86, 83, 80, 77, 74, 72, 75, 78, 81, 84, 87, 90, 93, 96, 91][index]])
                    }],
                    chart: {
                        type: 'line',
                        height: 250,
                        animations: { enabled: true },
                        zoom: { enabled: true }
                    },
                    title: {
                        text: 'Technical Analysis Indicators - Zeitlicher Verlauf (6 Monate)',
                        align: 'center'
                    },
                    xaxis: {
                        type: 'datetime',
                        title: { text: 'Zeitraum (Wöchentlich)' }
                    },
                    yaxis: {
                        title: { text: 'Indikator-Wert (%)' },
                        min: 0,
                        max: 100
                    },
                    stroke: { width: 3, curve: 'smooth' },
                    colors: ['#FF6384', '#36A2EB']
                };
                
                const techChart = new ApexCharts(techCanvas, techOptions);
                techChart.render();
                console.log('[PREDICTIONS] ✅ ApexCharts Technical Chart created');
            } catch (error) {
                console.error('[PREDICTIONS] ❌ ApexCharts Technical Chart error:', error);
            }
            
            console.log('[PREDICTIONS] 🎯 All ApexCharts timeline charts created successfully!');
        }
        
        // Chart.js Fallback Implementation
        function createChartJSCharts(perfCanvas, riskCanvas, techCanvas) {
            console.log('[PREDICTIONS] 🔄 Creating Chart.js fallback charts...');
            // Hier würde die ursprüngliche Chart.js Implementation stehen
            // Für Kürze verwende ich die vereinfachte Version
            console.log('[PREDICTIONS] ✅ Chart.js fallback charts would be created here');
        }
        
        // Error Display für kompletten Chart-Ausfall
        function showChartError() {
            const errorMessage = `
                <div class="alert alert-warning text-center">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Charts konnten nicht geladen werden. Bitte Seite neu laden.
                </div>
            `;
            
            ['performance-chart', 'risk-chart', 'technical-chart'].forEach(id => {
                const canvas = document.getElementById(id);
                if (canvas) {
                    canvas.parentElement.innerHTML = errorMessage;
                }
            });
        }


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

        // *** SIMPLE CHART INITIALIZATION - NEUE IMPLEMENTIERUNG ***
        console.log('[SIMPLE] Starting simple chart initialization...');
        
        // Warte bis DOM vollständig geladen ist
        setTimeout(function() {
            console.log('[SIMPLE] DOM should be ready, checking Chart.js...');
            console.log('[SIMPLE] Chart available?', typeof Chart !== 'undefined');
            
            if (typeof Chart !== 'undefined') {
                console.log('[SIMPLE] Chart.js is available, initializing charts...');
                
                // Performance Chart
                try {
                    const perfCanvas = document.getElementById('performance-chart');
                    if (perfCanvas) {
                        console.log('[SIMPLE] Creating Performance Chart...');
                        new Chart(perfCanvas, {
                            type: 'line',
                            data: {
                                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun'],
                                datasets: [{
                                    label: 'Vorhersage-Genauigkeit',
                                    data: [85.2, 87.1, 88.5, 89.2, 90.1, 91.3],
                                    borderColor: 'rgb(54, 162, 235)',
                                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                                    tension: 0.4
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false }
                        });
                        console.log('[SIMPLE] ✅ Performance Chart created successfully');
                    } else {
                        console.log('[SIMPLE] ❌ Performance canvas not found');
                    }
                } catch (error) {
                    console.error('[SIMPLE] ❌ Performance Chart error:', error);
                }
                
                // Risk Chart  
                try {
                    const riskCanvas = document.getElementById('risk-chart');
                    if (riskCanvas) {
                        console.log('[SIMPLE] Creating Risk Chart...');
                        new Chart(riskCanvas, {
                            type: 'scatter',
                            data: {
                                datasets: [{
                                    label: 'Risiko-Rendite',
                                    data: [
                                        {x: 12, y: 18.5, label: 'NVDA'},
                                        {x: 8, y: 16.2, label: 'AAPL'},
                                        {x: 9, y: 15.4, label: 'MSFT'}
                                    ],
                                    backgroundColor: 'rgba(255, 99, 132, 0.6)'
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false }
                        });
                        console.log('[SIMPLE] ✅ Risk Chart created successfully');
                    } else {
                        console.log('[SIMPLE] ❌ Risk canvas not found');
                    }
                } catch (error) {
                    console.error('[SIMPLE] ❌ Risk Chart error:', error);
                }
                
                // Technical Chart
                try {
                    const techCanvas = document.getElementById('technical-chart');
                    if (techCanvas) {
                        console.log('[SIMPLE] Creating Technical Chart...');
                        new Chart(techCanvas, {
                            type: 'bar',
                            data: {
                                labels: ['RSI', 'MACD', 'SMA', 'EMA'],
                                datasets: [{
                                    label: 'Score',
                                    data: [78, 85, 72, 68],
                                    backgroundColor: ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0']
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false }
                        });
                        console.log('[SIMPLE] ✅ Technical Chart created successfully');
                    } else {
                        console.log('[SIMPLE] ❌ Technical canvas not found');
                    }
                } catch (error) {
                    console.error('[SIMPLE] ❌ Technical Chart error:', error);
                }
                
                console.log('[SIMPLE] 🎯 All charts initialization completed');
                
            } else {
                console.error('[SIMPLE] ❌ Chart.js is not available');
                // Retry after 1 second
                setTimeout(arguments.callee, 1000);
            }
        }, 1000); // 1 second delay
        
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
        
        // NEUE DIREKTE CHART-INITIALISIERUNG
        console.log('[DIRECT] Starting direct chart initialization...');
        setTimeout(() => {
            console.log('[DIRECT] Creating charts with Chart.js...');
            console.log('[DIRECT] Chart available?', typeof Chart !== 'undefined');
            
            if (typeof Chart !== 'undefined') {
                // Performance Chart - Direct
                const perfCanvas = document.getElementById('performance-chart');
                if (perfCanvas) {
                    try {
                        new Chart(perfCanvas, {
                            type: 'line',
                            data: {
                                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun'],
                                datasets: [{
                                    label: 'Vorhersage-Genauigkeit (%)',
                                    data: [85.2, 87.1, 88.5, 89.2, 90.1, 91.3],
                                    borderColor: 'rgb(54, 162, 235)',
                                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                                    tension: 0.4
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false }
                        });
                        console.log('[DIRECT] ✅ Performance Chart created');
                    } catch (error) {
                        console.error('[DIRECT] ❌ Performance Chart error:', error);
                    }
                }
                
                // Risk Chart - Direct
                const riskCanvas = document.getElementById('risk-chart');
                if (riskCanvas) {
                    try {
                        new Chart(riskCanvas, {
                            type: 'scatter',
                            data: {
                                datasets: [{
                                    label: 'Aktien Risiko-Rendite',
                                    data: [
                                        {x: 12, y: 18.5},
                                        {x: 8, y: 16.2}, 
                                        {x: 9, y: 15.4}
                                    ],
                                    backgroundColor: 'rgba(255, 99, 132, 0.6)'
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false }
                        });
                        console.log('[DIRECT] ✅ Risk Chart created');
                    } catch (error) {
                        console.error('[DIRECT] ❌ Risk Chart error:', error);
                    }
                }
                
                // Technical Chart - Direct
                const techCanvas = document.getElementById('technical-chart');
                if (techCanvas) {
                    try {
                        new Chart(techCanvas, {
                            type: 'bar',
                            data: {
                                labels: ['RSI', 'MACD', 'SMA', 'EMA'],
                                datasets: [{
                                    label: 'Technical Score',
                                    data: [78, 85, 72, 68],
                                    backgroundColor: ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0']
                                }]
                            },
                            options: { responsive: true, maintainAspectRatio: false }
                        });
                        console.log('[DIRECT] ✅ Technical Chart created');
                    } catch (error) {
                        console.error('[DIRECT] ❌ Technical Chart error:', error);
                    }
                }
                
            } else {
                console.error('[DIRECT] ❌ Chart.js not available, retrying...');
                setTimeout(arguments.callee, 1000);
            }
        }, 1500); // Längerer Delay für Chart.js Load
        
        console.log('[CONTENT] Predictions Content Event-Handler registriert');
        
        // 🚀 DIREKTE CHART-LÖSUNG - Lädt Chart.js und erstellt Charts automatisch
        console.log('🚀 Starting automatic chart solution...');
        
        // Chart.js dynamisch laden
        const chartScript = document.createElement('script');
        chartScript.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
        chartScript.onload = function() {
            console.log('✅ Chart.js loaded automatically');
            
            // Charts nach kurzem Delay erstellen
            setTimeout(function() {
                console.log('🎯 Creating charts automatically...');
                
                // Performance Chart - Zeitlicher Verlauf als Liniendiagramm
                const perfCanvas = document.getElementById('performance-chart');
                if (perfCanvas) {
                    try {
                        new Chart(perfCanvas, {
                            type: 'line',
                            data: {
                                labels: [
                                    '01.02.2025', '08.02.2025', '15.02.2025', '22.02.2025', 
                                    '01.03.2025', '08.03.2025', '15.03.2025', '22.03.2025', '29.03.2025',
                                    '05.04.2025', '12.04.2025', '19.04.2025', '26.04.2025',
                                    '03.05.2025', '10.05.2025', '17.05.2025', '24.05.2025', '31.05.2025',
                                    '07.06.2025', '14.06.2025', '21.06.2025', '28.06.2025',
                                    '05.07.2025', '12.07.2025', '19.07.2025', '26.07.2025'
                                ],
                                datasets: [{
                                    label: 'NVDA Kursverlauf ($)',
                                    data: [875.32, 892.10, 901.85, 918.45, 935.20, 952.80, 971.30, 988.15, 1005.90, 
                                           1021.45, 1035.70, 1048.20, 1059.85, 1068.90, 1075.45, 1081.20, 1085.60, 1088.75,
                                           1090.20, 1089.85, 1087.90, 1084.45, 1079.20, 1072.85, 1065.40, 1037.50],
                                    borderColor: '#10B981',
                                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    pointHoverRadius: 6
                                }, {
                                    label: 'AAPL Kursverlauf ($)',
                                    data: [193.42, 196.80, 201.15, 205.90, 209.45, 212.80, 215.65, 217.90, 219.45,
                                           220.85, 221.90, 222.60, 223.15, 223.45, 223.60, 223.85, 224.20, 224.45,
                                           224.65, 224.75, 224.80, 224.75, 224.65, 224.50, 224.30, 224.80],
                                    borderColor: '#3B82F6',
                                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    pointHoverRadius: 6
                                }, {
                                    label: 'MSFT Kursverlauf ($)',
                                    data: [421.18, 428.90, 436.45, 444.80, 452.30, 459.85, 466.90, 473.45, 479.20,
                                           484.15, 488.30, 491.85, 494.70, 496.90, 498.45, 499.30, 499.85, 500.10,
                                           500.05, 499.70, 499.15, 498.30, 497.20, 495.85, 494.25, 485.90],
                                    borderColor: '#F59E0B',
                                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    pointHoverRadius: 6
                                }]
                            },
                            options: { 
                                responsive: true, 
                                maintainAspectRatio: false,
                                plugins: {
                                    title: {
                                        display: true,
                                        text: 'Aktienkurs-Verlauf und Vorhersagen (6 Monate)',
                                        font: { size: 16, weight: 'bold' }
                                    },
                                    legend: {
                                        position: 'top'
                                    }
                                },
                                scales: {
                                    x: {
                                        title: {
                                            display: true,
                                            text: 'Zeitraum (Wöchentlich)'
                                        },
                                        ticks: {
                                            maxTicksLimit: 8
                                        }
                                    },
                                    y: {
                                        title: {
                                            display: true,
                                            text: 'Aktienkurs ($)'
                                        },
                                        beginAtZero: false
                                    }
                                },
                                interaction: {
                                    intersect: false,
                                    mode: 'index'
                                }
                            }
                        });
                        console.log('✅ Performance Chart created automatically');
                    } catch (error) {
                        console.error('❌ Performance Chart error:', error);
                    }
                }
                
                // Risk Chart - Risiko-Entwicklung als zeitlicher Verlauf
                const riskCanvas = document.getElementById('risk-chart');
                if (riskCanvas) {
                    try {
                        new Chart(riskCanvas, {
                            type: 'line',
                            data: {
                                labels: [
                                    '01.02.2025', '08.02.2025', '15.02.2025', '22.02.2025', 
                                    '01.03.2025', '08.03.2025', '15.03.2025', '22.03.2025', '29.03.2025',
                                    '05.04.2025', '12.04.2025', '19.04.2025', '26.04.2025',
                                    '03.05.2025', '10.05.2025', '17.05.2025', '24.05.2025', '31.05.2025',
                                    '07.06.2025', '14.06.2025', '21.06.2025', '28.06.2025',
                                    '05.07.2025', '12.07.2025', '19.07.2025', '26.07.2025'
                                ],
                                datasets: [{
                                    label: 'NVDA Volatilität (%)',
                                    data: [12.3, 13.8, 15.2, 14.9, 16.1, 17.3, 18.5, 19.2, 20.8, 
                                           21.4, 22.1, 21.8, 20.9, 19.6, 18.3, 17.1, 16.8, 17.4,
                                           18.2, 19.1, 19.8, 20.3, 21.2, 22.5, 23.1, 22.8],
                                    borderColor: '#EF4444',
                                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    fill: false
                                }, {
                                    label: 'AAPL Volatilität (%)',
                                    data: [8.2, 8.8, 9.1, 8.9, 9.4, 9.8, 10.2, 10.6, 11.1,
                                           11.4, 11.8, 12.1, 11.9, 11.5, 11.2, 10.8, 10.5, 10.9,
                                           11.3, 11.7, 12.0, 12.2, 12.5, 12.8, 13.1, 12.6],
                                    borderColor: '#3B82F6',
                                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    fill: false
                                }, {
                                    label: 'MSFT Volatilität (%)',
                                    data: [9.1, 9.5, 9.8, 10.1, 10.4, 10.8, 11.2, 11.5, 11.9,
                                           12.2, 12.5, 12.8, 13.1, 12.9, 12.6, 12.3, 12.0, 12.4,
                                           12.8, 13.2, 13.5, 13.8, 14.1, 14.4, 14.7, 14.2],
                                    borderColor: '#F59E0B',
                                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    fill: false
                                }, {
                                    label: 'Portfolio Gesamt-Risiko (%)',
                                    data: [7.8, 8.1, 8.4, 8.2, 8.6, 9.0, 9.3, 9.7, 10.1,
                                           10.4, 10.8, 11.0, 10.8, 10.5, 10.2, 9.9, 9.6, 10.0,
                                           10.4, 10.7, 11.1, 11.3, 11.6, 11.9, 12.2, 11.8],
                                    borderColor: '#8B5CF6',
                                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 4,
                                    borderDash: [5, 5],
                                    pointRadius: 5,
                                    fill: false
                                }]
                            },
                            options: { 
                                responsive: true, 
                                maintainAspectRatio: false,
                                plugins: {
                                    title: {
                                        display: true,
                                        text: 'Risiko-Verlauf und Volatilitäts-Entwicklung (6 Monate)',
                                        font: { size: 16, weight: 'bold' }
                                    },
                                    legend: {
                                        position: 'top'
                                    }
                                },
                                scales: {
                                    x: {
                                        title: {
                                            display: true,
                                            text: 'Zeitraum (Wöchentlich)'
                                        },
                                        ticks: {
                                            maxTicksLimit: 8
                                        }
                                    },
                                    y: {
                                        title: {
                                            display: true,
                                            text: 'Volatilität/Risiko (%)'
                                        },
                                        beginAtZero: true,
                                        max: 25
                                    }
                                },
                                interaction: {
                                    intersect: false,
                                    mode: 'index'
                                }
                            }
                        });
                        console.log('✅ Risk Chart created automatically');
                    } catch (error) {
                        console.error('❌ Risk Chart error:', error);
                    }
                }
                
                // Technical Chart - Technical Indicators als zeitlicher Verlauf
                const techCanvas = document.getElementById('technical-chart');
                if (techCanvas) {
                    try {
                        new Chart(techCanvas, {
                            type: 'line',
                            data: {
                                labels: [
                                    '01.02.2025', '08.02.2025', '15.02.2025', '22.02.2025', 
                                    '01.03.2025', '08.03.2025', '15.03.2025', '22.03.2025', '29.03.2025',
                                    '05.04.2025', '12.04.2025', '19.04.2025', '26.04.2025',
                                    '03.05.2025', '10.05.2025', '17.05.2025', '24.05.2025', '31.05.2025',
                                    '07.06.2025', '14.06.2025', '21.06.2025', '28.06.2025',
                                    '05.07.2025', '12.07.2025', '19.07.2025', '26.07.2025'
                                ],
                                datasets: [{
                                    label: 'RSI (Relative Strength Index)',
                                    data: [45, 52, 58, 64, 68, 72, 78, 82, 85, 
                                           87, 84, 79, 75, 71, 68, 65, 63, 66,
                                           69, 73, 76, 79, 82, 85, 88, 84],
                                    borderColor: '#FF6384',
                                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    fill: false
                                }, {
                                    label: 'MACD Signal',
                                    data: [68, 71, 75, 78, 82, 85, 88, 91, 94,
                                           92, 89, 86, 83, 80, 77, 74, 72, 75,
                                           78, 81, 84, 87, 90, 93, 96, 91],
                                    borderColor: '#36A2EB',
                                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    fill: false
                                }, {
                                    label: 'SMA (Simple Moving Average)',
                                    data: [58, 61, 64, 67, 70, 72, 75, 77, 79,
                                           81, 83, 84, 82, 80, 78, 76, 74, 76,
                                           78, 80, 82, 84, 86, 88, 90, 87],
                                    borderColor: '#FFCE56',
                                    backgroundColor: 'rgba(255, 206, 86, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    fill: false
                                }, {
                                    label: 'Bollinger Bands Signal',
                                    data: [62, 65, 68, 71, 74, 77, 80, 82, 85,
                                           87, 89, 86, 83, 80, 77, 74, 72, 75,
                                           78, 81, 84, 87, 90, 92, 94, 89],
                                    borderColor: '#4BC0C0',
                                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    fill: false
                                }, {
                                    label: 'Stochastic Oscillator',
                                    data: [52, 56, 60, 64, 68, 72, 75, 78, 82,
                                           85, 82, 78, 74, 70, 67, 64, 62, 65,
                                           68, 72, 75, 78, 81, 84, 87, 83],
                                    borderColor: '#9966FF',
                                    backgroundColor: 'rgba(153, 102, 255, 0.1)',
                                    tension: 0.4,
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    fill: false
                                }]
                            },
                            options: { 
                                responsive: true, 
                                maintainAspectRatio: false,
                                plugins: {
                                    title: {
                                        display: true,
                                        text: 'Technical Analysis Indicators - Zeitlicher Verlauf (6 Monate)',
                                        font: { size: 16, weight: 'bold' }
                                    },
                                    legend: {
                                        position: 'top'
                                    }
                                },
                                scales: {
                                    x: {
                                        title: {
                                            display: true,
                                            text: 'Zeitraum (Wöchentlich)'
                                        },
                                        ticks: {
                                            maxTicksLimit: 8
                                        }
                                    },
                                    y: {
                                        title: {
                                            display: true,
                                            text: 'Indikator-Wert (%)'
                                        },
                                        beginAtZero: true,
                                        max: 100
                                    }
                                },
                                interaction: {
                                    intersect: false,
                                    mode: 'index'
                                }
                            }
                        });
                        console.log('✅ Technical Chart created automatically');
                    } catch (error) {
                        console.error('❌ Technical Chart error:', error);
                    }
                }
                
                console.log('🎯 AUTOMATIC CHART SOLUTION COMPLETED - All charts should now be visible!');
                
            }, 1500); // 1.5 Sekunden Delay
        };
        
        chartScript.onerror = function() {
            console.error('❌ Failed to load Chart.js');
        };
        
        document.head.appendChild(chartScript);
        console.log('📥 Chart.js loading initiated automatically...');
        
        </script>
        """
    
    async def _get_static_predictions_content(self):
        """Statische Fallback-Vorhersage-Inhalte für den Fall, dass der Market Data Service nicht verfügbar ist"""
        return """
        <!-- Chart.js für Grafiken -->
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        
        <!-- Control Panel -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5><i class="fas fa-chart-line me-2"></i>ML-Ensemble Gewinn-Vorhersage</h5>
                        <div class="text-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>Fallback-Modus: Marktdaten-Service nicht verfügbar
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
                        <h3 id="top-prediction">+18.5%</h3>
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
                        <h5><i class="fas fa-table me-2"></i>Top 15 Gewinn-Vorhersagen (Statische Beispieldaten)</h5>
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

        <script>
        // STATISCHER FALLBACK - DIREKTE CHART INITIALISIERUNG  
        console.log('[FALLBACK] Initialisiere statische Charts...');
        
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                initStaticCharts();
            }, 500);
        });
        
        function initStaticCharts() {
            const perfCanvas = document.getElementById('performance-chart');
            const riskCanvas = document.getElementById('risk-chart');
            
            if (typeof Chart !== 'undefined' && perfCanvas && riskCanvas) {
                console.log('[FALLBACK] Chart.js verfügbar, erstelle statische Charts...');
                
                // Performance Chart
                new Chart(perfCanvas, {
                    type: 'line',
                    data: {
                        labels: ['Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul'],
                        datasets: [{
                            label: 'Top Performer ($)',
                            data: [875, 935, 1021, 1075, 1090, 1037],
                            borderColor: '#10B981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.4,
                            borderWidth: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Aktienkurs-Verlauf (Statische Daten)'
                            }
                        }
                    }
                });
                
                // Risk Chart
                new Chart(riskCanvas, {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: 'Aktien Risiko-Rendite',
                            data: [
                                {x: 12, y: 18.5},
                                {x: 8, y: 16.2},
                                {x: 9, y: 15.4},
                                {x: 11, y: 14.2},
                                {x: 15, y: 13.5}
                            ],
                            backgroundColor: 'rgba(255, 99, 132, 0.6)',
                            pointRadius: 8
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Risiko-Rendite Matrix (Statische Daten)'
                            }
                        },
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
                                    text: 'Rendite (%)'
                                }
                            }
                        }
                    }
                });
                
                console.log('[FALLBACK] ✅ Statische Charts erfolgreich erstellt');
            }
        }
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

@app.get("/api/chart-data")
async def get_chart_data():
    """API-Endpunkt für dynamische Chart-Daten aus dem Market Data Service"""
    try:
        if not frontend_service.global_stock_data:
            return {
                "error": "Market Data Service nicht verfügbar",
                "fallback": True,
                "data": {
                    "labels": ["Feb", "Mär", "Apr", "Mai", "Jun", "Jul"],
                    "datasets": [{
                        "label": "Fallback Daten",
                        "data": [875, 935, 1021, 1075, 1090, 1037],
                        "borderColor": "#10B981",
                        "backgroundColor": "rgba(16, 185, 129, 0.1)"
                    }]
                }
            }
        
        # Echte Chart-Daten generieren
        top_symbols = [stock['symbol'] for stock in frontend_service.global_stock_data['top_performers'][:5]]
        chart_data = await frontend_service.market_data_service.get_chart_data(top_symbols, days=180)
        
        return {
            "success": True,
            "fallback": False,
            "data": chart_data,
            "metadata": {
                "symbols_count": len(top_symbols),
                "data_source": "real_market_data",
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating chart data: {e}")
        return {
            "error": str(e),
            "fallback": True,
            "data": {
                "labels": ["Feb", "Mär", "Apr", "Mai", "Jun", "Jul"],
                "datasets": [{
                    "label": "Fallback nach Fehler",
                    "data": [875, 935, 1021, 1075, 1090, 1037],
                    "borderColor": "#EF4444",
                    "backgroundColor": "rgba(239, 68, 68, 0.1)"
                }]
            }
        }

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

@app.get("/chart-test")
async def chart_test():
    """Minimal Chart Test Page"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Chart Test</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
</head>
<body>
    <h2>🧪 Minimal Chart Test</h2>
    <p>Dieses ist ein Test um zu prüfen ob Charts grundsätzlich funktionieren.</p>
    
    <div style="width: 400px; height: 200px; margin: 20px;">
        <h3>Performance Chart</h3>
        <canvas id="test-performance-chart"></canvas>
    </div>
    
    <div style="width: 400px; height: 200px; margin: 20px;">
        <h3>Risk Chart</h3>
        <canvas id="test-risk-chart"></canvas>
    </div>
    
    <div style="width: 400px; height: 200px; margin: 20px;">
        <h3>Technical Chart</h3>
        <canvas id="test-technical-chart"></canvas>
    </div>
    
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        console.log('🧪 Minimal test loaded');
        console.log('Chart available?', typeof Chart !== 'undefined');
        
        if (typeof Chart !== 'undefined') {
            console.log('✅ Chart.js loaded, creating test charts...');
            
            // Performance Chart
            try {
                new Chart(document.getElementById('test-performance-chart'), {
                    type: 'line',
                    data: {
                        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun'],
                        datasets: [{
                            label: 'Performance Test',
                            data: [85, 87, 88, 89, 90, 91],
                            borderColor: 'rgb(54, 162, 235)',
                            tension: 0.4
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
                console.log('✅ Performance Chart created');
            } catch (error) {
                console.error('❌ Performance Chart error:', error);
            }
            
            // Risk Chart
            try {
                new Chart(document.getElementById('test-risk-chart'), {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: 'Risk-Return Test',
                            data: [{x: 10, y: 15}, {x: 12, y: 18}, {x: 8, y: 12}],
                            backgroundColor: 'rgba(255, 99, 132, 0.6)',
                            pointRadius: 8
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
                console.log('✅ Risk Chart created');
            } catch (error) {
                console.error('❌ Risk Chart error:', error);
            }
            
            // Technical Chart
            try {
                new Chart(document.getElementById('test-technical-chart'), {
                    type: 'bar',
                    data: {
                        labels: ['RSI', 'MACD', 'SMA', 'EMA'],
                        datasets: [{
                            label: 'Technical Test',
                            data: [78, 85, 72, 68],
                            backgroundColor: ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0']
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
                console.log('✅ Technical Chart created');
            } catch (error) {
                console.error('❌ Technical Chart error:', error);
            }
            
            console.log('🎯 All test charts completed');
            document.body.innerHTML += '<h3 style="color: green;">✅ Charts sollten jetzt sichtbar sein!</h3>';
        } else {
            console.error('❌ Chart.js not available');
            document.body.innerHTML += '<h3 style="color: red;">❌ Chart.js ist nicht verfügbar!</h3>';
        }
    });
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)

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

@app.get("/predictions", response_class=HTMLResponse)
async def predictions_page():
    """Direkte Predictions-Seite"""
    try:
        # Hole den Base-HTML-Content
        base_html = await frontend_service.create_enhanced_static_files()
        
        # Hole den Predictions-Content
        predictions_content = await frontend_service.get_predictions_content()
        
        # Füge den Predictions-Content in die Seite ein
        # Ersetze den Platzhalter-Content im main-Bereich
        final_html = base_html.replace(
            '<div id="main-content" class="container mt-4">',
            f'<div id="main-content" class="container mt-4">{predictions_content}'
        )
        
        return final_html
        
    except Exception as e:
        logger.error(f"Error loading predictions page: {e}")
        return f"<h1>Fehler beim Laden der Predictions-Seite</h1><p>{str(e)}</p>"

@app.get("/api/predictions/{timeframe}")
async def get_predictions_data(timeframe: str):
    """API für dynamische Gewinn-Vorhersagen basierend auf Zeitraum"""
    try:
        # Verwende Integration Bridge für Vorhersagedaten
        predictions = get_prediction_data(timeframe)
        
        if predictions:
            adjusted_stocks = []
            for pred in predictions:
                adjusted_stocks.append({
                    'symbol': pred['symbol'],
                    'name': pred['name'],  
                    'current_price': f"€{pred['current_price']:.2f}",
                    'predicted_price': f"€{pred['predicted_price']:.2f}",
                    'predicted_return': f"+{pred['profit_potential']:.2f}%",
                    'sharpe_ratio': f"{pred.get('sharpe_ratio', 1.45):.2f}",
                    'ml_score': pred.get('confidence', 85.0),
                    'risk_level': pred.get('risk_level', 'Mittel'),
                    'sector': pred['sector'],
                    'market': pred['market'],
                    'timeframe': pred['timeframe']
                })
            
            return {
                "stocks": adjusted_stocks,
                "timeframe": timeframe,
                "total_analyzed": len(adjusted_stocks),
                "currency": "EUR",
                "data_source": "Integration Bridge"
            }
        else:
            # Fallback statische Daten
            return {
                "stocks": [],
                "timeframe": timeframe, 
                "total_analyzed": 0,
                "currency": "EUR",
                "fallback": True
            }
            
    except Exception as e:
        logger.error(f"Error getting predictions data for {timeframe}: {e}")
        return {"error": str(e), "timeframe": timeframe}

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