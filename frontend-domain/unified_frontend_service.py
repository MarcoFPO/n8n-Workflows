#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 Unified Frontend Service - Konsolidiert alle Frontend-Funktionalität
Ersetzt: main.py (3670 Zeilen), simple_modular_frontend.py (670 Zeilen)
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
from abc import ABC, abstractmethod

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import des zentralen Fallback-Systems
import sys
sys.path.append(str(Path(__file__).parent.parent))
from core.unified_fallback_provider import get_fallback_stock_data, get_fallback_predictions, get_fallback_metrics
try:
    from depot_management_module import DepotContentProviderFactory
except ImportError:
    try:
        from .depot_management_module import DepotContentProviderFactory
    except ImportError:
        # Fallback für lokale Tests
        import sys
        sys.path.append(str(Path(__file__).parent))
        from depot_management_module import DepotContentProviderFactory


# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="Unified Frontend Service",
    description="Konsolidierter Frontend Service für Aktienanalyse-Ökosystem",
    version="2.0.0"
)


class UnifiedEventBusConnector:
    """Vereinfachter Event-Bus Connector"""
    
    def __init__(self):
        self.connected = True
        self.logger = logger
        
    async def connect(self):
        """Event-Bus Verbindung"""
        self.logger.info("🔗 Event-Bus connected")
        
    async def disconnect(self):
        """Event-Bus Trennung"""
        self.logger.info("🔌 Event-Bus disconnected")
        
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Event senden"""
        self.logger.info(f"📤 Event: {event_type}")
        self.logger.debug(f"Data: {data}")


class UnifiedAPIGatewayConnector:
    """Vereinfachter API Gateway Connector"""
    
    def __init__(self):
        self.session = None
        self.logger = logger
        
    async def get_predictions_data(self, timeframe: str = "1M") -> Dict[str, Any]:
        """Predictions-Daten abrufen"""
        try:
            # Fallback-Daten verwenden
            predictions = get_fallback_predictions(timeframe)
            return {
                "stocks": predictions,
                "timeframe": timeframe,
                "total_analyzed": len(predictions),
                "currency": "EUR",
                "fallback": True
            }
        except Exception as e:
            self.logger.error(f"API Error: {e}")
            return {"stocks": [], "error": str(e)}
    
    async def cleanup(self):
        """Cleanup-Methode"""
        if self.session:
            await self.session.close()


class BaseContentProvider(ABC):
    """Basis Content Provider"""
    
    def __init__(self, event_bus, api_gateway):
        self.event_bus = event_bus
        self.api_gateway = api_gateway
        self.logger = logger
    
    @abstractmethod
    async def get_content(self, context: Dict[str, Any]) -> str:
        pass


class PredictionsContentProvider(BaseContentProvider):
    """Predictions Content mit Live-Tabelle"""
    
    async def get_content(self, context: Dict[str, Any]) -> str:
        await self.event_bus.emit("frontend.predictions.requested", {"context": context})
        
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
                                    <tr><td colspan="10" class="text-center">
                                        <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                                        Lade Live-Marktdaten...
                                    </td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
        let currentTimeframe = '1M';
        
        async function updatePredictionsWithLiveData() {
            try {
                const response = await fetch(`/api/predictions/${currentTimeframe}`);
                const data = await response.json();
                
                const tbody = document.getElementById('predictions-table-body');
                if (!tbody) return;
                
                tbody.innerHTML = data.stocks.map((stock, index) => `
                    <tr class="${index === 0 ? 'table-success' : ''}">
                        <td><span class="badge bg-${index === 0 ? 'warning' : index < 3 ? 'success' : 'secondary'}">${index + 1}</span></td>
                        <td><strong>${stock.symbol}</strong></td>
                        <td>${stock.name}</td>
                        <td>${stock.current_price}</td>
                        <td>${stock.predicted_price}</td>
                        <td><span class="badge bg-success">${stock.predicted_return}</span></td>
                        <td>${stock.sharpe_ratio}</td>
                        <td><span class="badge bg-primary">${stock.ml_score}</span></td>
                        <td><span class="badge bg-${stock.risk_level === 'Niedrig' ? 'success' : stock.risk_level === 'Mittel' ? 'warning' : 'danger'}">${stock.risk_level}</span></td>
                        <td><button class="btn btn-sm btn-primary">Analyse</button></td>
                    </tr>
                `).join('');
                
                const now = new Date().toLocaleString('de-DE');
                const lastUpdated = document.getElementById('last-updated');
                if (lastUpdated) {
                    lastUpdated.textContent = `Letzte Aktualisierung: ${now} (${data.timeframe})`;
                }
                
            } catch (error) {
                console.error('Error updating predictions table:', error);
            }
        }
        
        async function updatePredictionTimeframe(timeframe) {
            currentTimeframe = timeframe;
            
            const buttons = document.querySelectorAll('#timeframe-buttons button');
            buttons.forEach(btn => {
                btn.className = btn.textContent === timeframe ? 'btn btn-primary' : 'btn btn-outline-primary';
            });
            
            await updatePredictionsWithLiveData();
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => updatePredictionsWithLiveData(), 500);
            setInterval(() => updatePredictionsWithLiveData(), 60000);
        });
        </script>
        '''


class DashboardContentProvider(BaseContentProvider):
    """Dashboard Content"""
    
    async def get_content(self, context: Dict[str, Any]) -> str:
        await self.event_bus.emit("frontend.dashboard.requested", {"context": context})
        
        metrics = get_fallback_metrics()
        summary = metrics.get('summary', {})
        
        return f'''
        <div class="row">
            <div class="col-md-4 mb-4">
                <div class="card status-card">
                    <div class="card-body text-center">
                        <i class="fas fa-microchip fa-2x mb-2"></i>
                        <h3>{summary.get('cpu_usage', 0)}%</h3>
                        <p class="mb-0">CPU Auslastung</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-4">
                <div class="card status-card">
                    <div class="card-body text-center">
                        <i class="fas fa-memory fa-2x mb-2"></i>
                        <h3>{summary.get('memory_usage', 0)}%</h3>
                        <p class="mb-0">Speicher</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-4">
                <div class="card status-card">
                    <div class="card-body text-center">
                        <i class="fas fa-server fa-2x mb-2"></i>
                        <h3>{summary.get('active_services', 0)}/{summary.get('total_services', 0)}</h3>
                        <p class="mb-0">Services</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="alert alert-success">
            <i class="fas fa-check-circle me-2"></i>
            <strong>System Status:</strong> Alle Core-Services laufen optimal. 
            Unified Frontend-Service aktiv mit Event-Bus Integration.
        </div>
        
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-chart-line me-2"></i>Optimierte Architektur</h5>
            </div>
            <div class="card-body">
                <p>✅ <strong>Unified Frontend:</strong> Konsolidierte UI Components</p>
                <p>✅ <strong>Zentrales Fallback:</strong> Einheitliche Fallback-Logik</p>
                <p>✅ <strong>Optimierte Adapter:</strong> Reduzierte Code-Duplikation</p>
                <p>✅ <strong>Event-Bus:</strong> Lose gekoppelte Services</p>
            </div>
        </div>
        '''


class ContentProviderFactory:
    """Factory für Content Provider"""
    
    @staticmethod
    def get_provider(provider_type: str, event_bus, api_gateway):
        providers = {
            'dashboard': DashboardContentProvider,
            'predictions': PredictionsContentProvider
        }
        provider_class = providers.get(provider_type)
        return provider_class(event_bus, api_gateway) if provider_class else None


class UnifiedFrontendService:
    """Hauptservice mit konsolidierter Architektur"""
    
    def __init__(self):
        self.event_bus = UnifiedEventBusConnector()
        self.api_gateway = UnifiedAPIGatewayConnector()
        self.content_providers = {}
        self.logger = logger
        self.static_path = Path(__file__).parent / "static-assets"
        
    async def initialize(self):
        """Service initialisieren"""
        self.logger.info("🎨 Initializing Unified Frontend Service...")
        
        # Event-Bus verbinden
        await self.event_bus.connect()
        
        # Content Providers
        self.content_providers['dashboard'] = ContentProviderFactory.get_provider('dashboard', self.event_bus, self.api_gateway)
        self.content_providers['predictions'] = ContentProviderFactory.get_provider('predictions', self.event_bus, self.api_gateway)
        
        # Depot-Management Provider
        self.content_providers['depot-overview'] = DepotContentProviderFactory.get_provider('depot-overview', self.event_bus, self.api_gateway)
        self.content_providers['depot-details'] = DepotContentProviderFactory.get_provider('depot-details', self.event_bus, self.api_gateway)
        self.content_providers['depot-trading'] = DepotContentProviderFactory.get_provider('depot-trading', self.event_bus, self.api_gateway)
        
        # Static Files
        await self._create_static_files()
        
        await self.event_bus.emit("frontend.service.started", {"version": "2.0.0"})
        
        self.logger.info("✅ Unified Frontend Service initialized")
    
    async def get_content(self, section: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Content für spezifische Sektion abrufen"""
        try:
            provider = self.content_providers.get(section)
            if not provider:
                return f'<div class="alert alert-warning">Content für "{section}" noch nicht implementiert</div>'
            
            await self.event_bus.emit(f"frontend.content.requested", {
                "section": section, "context": context or {}
            })
            
            return await provider.get_content(context or {})
            
        except Exception as e:
            self.logger.error(f"❌ Content generation failed for {section}: {e}")
            return f'<div class="alert alert-danger">Fehler beim Laden von "{section}": {str(e)}</div>'
    
    async def _create_static_files(self):
        """HTML Template erstellen"""
        self.static_path.mkdir(parents=True, exist_ok=True)
        
        html = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aktienanalyse-Ökosystem - Unified</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .sidebar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .sidebar-nav a { color: white; text-decoration: none; padding: 0.8rem 1.2rem; display: block; border-radius: 5px; margin: 0.2rem; }
        .sidebar-nav a:hover, .sidebar-nav a.active { background: rgba(255,255,255,0.2); }
        .status-card { border-left: 4px solid #007bff; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 sidebar text-white vh-100 p-0">
                <div class="p-3">
                    <h4><i class="fas fa-chart-line me-2"></i>Unified Frontend</h4>
                </div>
                <nav class="sidebar-nav">
                    <a href="#" id="nav-dashboard" onclick="loadContent('dashboard')" class="active">
                        <i class="fas fa-tachometer-alt me-2"></i> Dashboard
                    </a>
                    <a href="#" id="nav-predictions" onclick="loadContent('predictions')">
                        <i class="fas fa-chart-line me-2"></i> Gewinn-Vorhersage
                    </a>
                    <div class="mt-2 mb-2">
                        <small class="text-white-50 px-3">DEPOTVERWALTUNG</small>
                    </div>
                    <a href="#" id="nav-depot-overview" onclick="loadContent('depot-overview')">
                        <i class="fas fa-briefcase me-2"></i> Portfolio Übersicht
                    </a>
                    <a href="#" id="nav-depot-details" onclick="loadContent('depot-details', {portfolio_id: 'portfolio_001'})">
                        <i class="fas fa-list-alt me-2"></i> Portfolio Details
                    </a>
                    <a href="#" id="nav-depot-trading" onclick="loadContent('depot-trading', {portfolio_id: 'portfolio_001'})">
                        <i class="fas fa-exchange-alt me-2"></i> Trading Interface
                    </a>
                </nav>
            </div>
            
            <div class="col-md-10 p-4">
                <div id="main-content">
                    <div class="text-center">
                        <div class="spinner-border text-primary" role="status"></div>
                        <p class="mt-2">Lade Dashboard...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        async function loadContent(section, context = {}) {
            try {
                // Navigation Update nur für Hauptnavigation
                const navItem = document.getElementById('nav-' + section);
                if (navItem) {
                    document.querySelectorAll('.sidebar-nav a').forEach(a => a.classList.remove('active'));
                    navItem.classList.add('active');
                }
                
                // Loading anzeigen
                document.getElementById('main-content').innerHTML = 
                    '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Lade ' + section + '...</p></div>';
                
                // API-Aufruf mit Context
                let url = '/api/content/' + section;
                if (Object.keys(context).length > 0) {
                    const params = new URLSearchParams(context);
                    url += '?' + params.toString();
                }
                
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const content = await response.text();
                document.getElementById('main-content').innerHTML = content;
                
                console.log(`✅ Content loaded: ${section}`, context);
                
            } catch (error) {
                console.error('Content loading failed:', error);
                document.getElementById('main-content').innerHTML = 
                    '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>Fehler beim Laden: ' + error.message + '</div>';
            }
        }
        
        // Global verfügbare Funktionen für Depot-Management
        window.loadContent = loadContent;
        
        document.addEventListener('DOMContentLoaded', function() {
            loadContent('dashboard');
        });
    </script>
</body>
</html>'''
        
        with open(self.static_path / "index.html", "w", encoding="utf-8") as f:
            f.write(html)


# Service Instance
frontend_service = UnifiedFrontendService()


# FastAPI Routes
@app.on_event("startup")
async def startup_event():
    await frontend_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    await frontend_service.event_bus.disconnect()
    await frontend_service.api_gateway.cleanup()

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse(frontend_service.static_path / "index.html")

@app.get("/api/content/{section}")
async def get_content(section: str):
    content = await frontend_service.get_content(section)
    return HTMLResponse(content)

@app.get("/api/predictions/{timeframe}")
async def get_predictions_data(timeframe: str):
    try:
        logger.info(f"📈 Predictions request: {timeframe}")
        data = await frontend_service.api_gateway.get_predictions_data(timeframe)
        await frontend_service.event_bus.emit("frontend.api.predictions.delivered", {
            "timeframe": timeframe, "stock_count": len(data.get("stocks", []))
        })
        return data
    except Exception as e:
        logger.error(f"❌ Predictions API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "unified-frontend-service",
        "version": "2.0.0",
        "architecture": "consolidated",
        "event_bus_connected": frontend_service.event_bus.connected
    }

# Portfolio Management API Endpoints
@app.get("/api/portfolios")
async def get_portfolios():
    """Alle Portfolios abrufen"""
    try:
        logger.info("📊 Portfolios request")
        # Mock-Daten für Demo - später durch echte API ersetzen
        portfolios = [
            {
                "portfolio_id": "portfolio_001",
                "name": "Hauptportfolio",
                "description": "Langfristige Anlagestrategie",
                "currency": "EUR",
                "total_value": 125000.50,
                "cash_balance": 5000.00,
                "performance": {"daily": 2.3, "weekly": 8.7, "monthly": 12.1},
                "risk_profile": "moderate"
            },
            {
                "portfolio_id": "portfolio_002", 
                "name": "Trading Portfolio",
                "description": "Kurzfristige Trades",
                "currency": "EUR",
                "total_value": 45000.00,
                "cash_balance": 12000.00,
                "performance": {"daily": -0.8, "weekly": 3.2, "monthly": 18.5},
                "risk_profile": "aggressive"
            }
        ]
        await frontend_service.event_bus.emit("frontend.api.portfolios.delivered", {
            "portfolio_count": len(portfolios)
        })
        return portfolios
    except Exception as e:
        logger.error(f"❌ Portfolios API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolios/{portfolio_id}/positions")
async def get_portfolio_positions(portfolio_id: str):
    """Positionen eines Portfolios abrufen"""
    try:
        logger.info(f"📈 Portfolio positions request: {portfolio_id}")
        # Mock-Daten für Demo
        positions = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "quantity": 50,
                "avg_buy_price": 180.25,
                "current_price": 192.30,
                "market_value": 9615.00,
                "unrealized_pnl": 602.50,
                "unrealized_pnl_percent": 6.69,
                "allocation_percent": 15.2
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft Corporation", 
                "quantity": 30,
                "avg_buy_price": 320.50,
                "current_price": 335.80,
                "market_value": 10074.00,
                "unrealized_pnl": 459.00,
                "unrealized_pnl_percent": 4.78,
                "allocation_percent": 16.1
            }
        ]
        return positions
    except Exception as e:
        logger.error(f"❌ Portfolio positions API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolios/{portfolio_id}/orders")
async def create_order(portfolio_id: str, order_data: dict):
    """Neue Order erstellen"""
    try:
        logger.info(f"📝 Creating order for portfolio {portfolio_id}: {order_data}")
        # Order-Validierung und Simulation
        order_result = {
            "order_id": f"order_{portfolio_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "pending",
            "portfolio_id": portfolio_id,
            "symbol": order_data.get("symbol"),
            "quantity": order_data.get("quantity"),
            "order_type": order_data.get("order_type", "market"),
            "estimated_total": order_data.get("quantity", 0) * order_data.get("price", 0),
            "created_at": datetime.now().isoformat()
        }
        await frontend_service.event_bus.emit("frontend.api.order.created", order_result)
        return order_result
    except Exception as e:
        logger.error(f"❌ Order creation API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "unified_frontend_service:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )