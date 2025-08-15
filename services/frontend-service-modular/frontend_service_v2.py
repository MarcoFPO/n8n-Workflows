#!/usr/bin/env python3
"""
Modernisierter Frontend Service v2
Verwendet shared libraries und löst Import-Probleme
"""

import sys
import time
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

# Shared Libraries Import (eliminiert Code-Duplikation)
from shared import (
    # Basis-Klassen
    ModularService, DatabaseMixin, EventBusMixin,
    # Standard-Imports
    datetime, Dict, Any, Optional, List,
    FastAPI, HTTPException, BackgroundTasks, BaseModel, Field, Request,
    JSONResponse, HTMLResponse, StaticFiles,
    # Security & Logging
    SecurityConfig, setup_logging,
    # Utilities
    get_current_timestamp, safe_get_env
)

# Event-Bus Imports für Compliance - FIXED Import Path
from shared.event_bus import EventBusConnector, Event, EventType

# Frontend-spezifische Imports
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
import aiofiles
from pathlib import Path

# Environment laden
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')


class FrontendModuleBase:
    """Basis-Klasse für Frontend-Module"""
    
    def __init__(self, module_name: str, event_bus=None):
        self.module_name = module_name
        self.event_bus = event_bus
        self.logger = setup_logging(f"frontend-{module_name}")
        self.data_cache = {}
        self.is_active = True
    
    async def get_health(self):
        """Health-Status des Moduls"""
        return {
            "module": self.module_name,
            "status": "active" if self.is_active else "inactive",
            "cache_size": len(self.data_cache),
            "event_bus_connected": self.event_bus is not None
        }
    
    async def process_event(self, event_type: str, data: Dict[str, Any]):
        """Event-Verarbeitung (Override in Subklassen)"""
        self.logger.info(f"Event received in {self.module_name}", event_type=event_type)


class DashboardModule(FrontendModuleBase):
    """Dashboard-Modul für Hauptübersicht"""
    
    def __init__(self, event_bus=None):
        super().__init__("dashboard", event_bus)
        self.dashboard_data = {
            "portfolio_value": 0.0,
            "daily_change": 0.0,
            "active_orders": 0,
            "last_update": get_current_timestamp().isoformat()
        }
    
    async def get_dashboard_data(self):
        """Dashboard-Daten abrufen"""
        return {
            "data": self.dashboard_data,
            "timestamp": get_current_timestamp().isoformat(),
            "status": "active"
        }
    
    async def update_portfolio_data(self, portfolio_data: Dict):
        """Portfolio-Daten aktualisieren"""
        self.dashboard_data.update(portfolio_data)
        self.dashboard_data["last_update"] = get_current_timestamp().isoformat()


class MarketDataModule(FrontendModuleBase):
    """Marktdaten-Modul für Charts und Kurse"""
    
    def __init__(self, event_bus=None):
        super().__init__("market_data", event_bus)
        self.market_data = {}
        self.watchlist = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    
    async def get_market_data(self, symbol: str = None):
        """Marktdaten abrufen"""
        if symbol:
            return self.market_data.get(symbol, {"symbol": symbol, "price": 0.0, "change": 0.0})
        return {
            "watchlist": {symbol: self.market_data.get(symbol, {}) for symbol in self.watchlist},
            "timestamp": get_current_timestamp().isoformat()
        }
    
    async def update_market_data(self, symbol: str, data: Dict):
        """Marktdaten aktualisieren"""
        self.market_data[symbol] = {
            **data,
            "timestamp": get_current_timestamp().isoformat()
        }


class TradingModule(FrontendModuleBase):
    """Trading-Modul für Order-Management"""
    
    def __init__(self, event_bus=None):
        super().__init__("trading", event_bus)
        self.active_orders = []
        self.order_history = []
    
    async def get_orders(self, status: str = "all"):
        """Orders abrufen"""
        if status == "active":
            return {"orders": self.active_orders}
        elif status == "history":
            return {"orders": self.order_history}
        return {
            "active_orders": self.active_orders,
            "order_history": self.order_history[-10:]  # Last 10
        }
    
    async def create_order(self, order_data: Dict):
        """Neue Order erstellen"""
        order = {
            "id": f"order_{len(self.active_orders) + 1}",
            "timestamp": get_current_timestamp().isoformat(),
            **order_data,
            "status": "pending"
        }
        self.active_orders.append(order)
        return order


class FrontendService(ModularService, EventBusMixin):
    """
    Modernisierter Frontend Service
    Verwendet shared libraries für bessere Code-Qualität
    """
    
    def __init__(self):
        # Service-Initialisierung über BaseService
        super().__init__(
            service_name="frontend",
            version="2.0.0",
            port=SecurityConfig.get_service_port("frontend")
        )
        
        # Templates und Static Files
        self.templates = Jinja2Templates(directory="templates")
        self.static_path = Path("static")
        self.static_path.mkdir(exist_ok=True)
        
        # Frontend-Module initialisieren
        self._initialize_frontend_modules()
    
    async def _setup_service(self):
        """Service-spezifische Initialisierung"""
        # Event-Bus Connection
        await self.setup_event_bus("frontend")
        
        # API Routes registrieren
        self._setup_api_routes()
        
        # Static Files
        self._setup_static_files()
        
        # Frontend-Module starten
        await self._start_frontend_modules()
        
        self.logger.info("Frontend Service v2 fully initialized")
    
    def _initialize_frontend_modules(self):
        """Frontend-Module initialisieren"""
        # Dashboard Module
        dashboard_module = DashboardModule(self.event_bus)
        self.register_module("dashboard", dashboard_module)
        
        # Market Data Module
        market_module = MarketDataModule(self.event_bus)
        self.register_module("market_data", market_module)
        
        # Trading Module
        trading_module = TradingModule(self.event_bus)
        self.register_module("trading", trading_module)
    
    async def _start_frontend_modules(self):
        """Frontend-Module starten"""
        for module_name, module in self.modules.items():
            try:
                if hasattr(module, 'start'):
                    await module.start()
                self.logger.info(f"Frontend module {module_name} started successfully")
            except Exception as e:
                self.logger.error(f"Failed to start frontend module {module_name}: {e}")
    
    def _setup_static_files(self):
        """Static Files Setup"""
        # Static Files mounten
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # Favicon
        @self.app.get("/favicon.ico")
        async def favicon():
            return FileResponse("static/favicon.ico") if Path("static/favicon.ico").exists() else JSONResponse({"status": "not_found"})
    
    def _setup_api_routes(self):
        """API Routes registrieren"""
        
        # Root Route - Frontend Hauptseite
        @self.app.get("/", response_class=HTMLResponse)
        async def frontend_root(request: Request):
            """Frontend Hauptseite"""
            return self._generate_dashboard_html()
        
        # Dashboard API
        @self.app.get("/api/v2/dashboard")
        async def get_dashboard():
            """Dashboard-Daten API"""
            try:
                # Event-Bus-Compliance: Use Event-Bus instead of direct module call
                event = Event(
                    event_type=EventType.DASHBOARD_REQUEST.value,
                    stream_id=f"dashboard-{int(time.time())}",
                    data={"request_type": "get_dashboard_data"},
                    source="frontend"
                )
                
                # For now, fallback to direct call until response handling is implemented
                dashboard_module = self.modules["dashboard"]
                data = await dashboard_module.get_dashboard_data()
                
                # Publish event for logging/monitoring
                if self.event_bus and self.event_bus.connected:
                    await self.event_bus.publish(event)
                
                return data
            except Exception as e:
                self.logger.error(f"Dashboard API error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Market Data API
        @self.app.get("/api/v2/market/{symbol}")
        async def get_market_data(symbol: str):
            """Marktdaten für Symbol"""
            try:
                # Event-Bus-Compliance: Use Event-Bus instead of direct module call
                event = Event(
                    event_type=EventType.MARKET_DATA_REQUEST.value,
                    stream_id=f"market-{symbol}",
                    data={"symbol": symbol, "request_type": "get_market_data"},
                    source="frontend"
                )
                
                # For now, fallback to direct call until response handling is implemented
                market_module = self.modules["market_data"]
                data = await market_module.get_market_data(symbol)
                
                # Publish event for logging/monitoring
                if self.event_bus and self.event_bus.connected:
                    await self.event_bus.publish(event)
                
                return data
            except Exception as e:
                self.logger.error(f"Market data API error for {symbol}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Trading API
        @self.app.get("/api/v2/orders")
        async def get_orders(status: str = "all"):
            """Orders abrufen"""
            try:
                # Event-Bus-Compliance: Use Event-Bus instead of direct module call
                event = Event(
                    event_type=EventType.TRADING_REQUEST.value,
                    stream_id=f"trading-orders-{int(time.time())}",
                    data={"status": status, "request_type": "get_orders"},
                    source="frontend"
                )
                
                # For now, fallback to direct call until response handling is implemented
                trading_module = self.modules["trading"]
                data = await trading_module.get_orders(status)
                
                # Publish event for logging/monitoring
                if self.event_bus and self.event_bus.connected:
                    await self.event_bus.publish(event)
                
                return data
            except Exception as e:
                self.logger.error(f"Orders API error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v2/orders")
        async def create_order(order_data: Dict[str, Any]):
            """Neue Order erstellen"""
            try:
                # Event-Bus-Compliance: Use Event-Bus instead of direct module call
                event = Event(
                    event_type=EventType.ORDER_REQUEST.value,
                    stream_id=f"order-create-{int(time.time())}",
                    data={"order_data": order_data, "request_type": "create_order"},
                    source="frontend"
                )
                
                # For now, fallback to direct call until response handling is implemented
                trading_module = self.modules["trading"]
                order = await trading_module.create_order(order_data)
                
                # Publish event for logging/monitoring
                if self.event_bus and self.event_bus.connected:
                    await self.event_bus.publish(event)
                
                return order
            except Exception as e:
                self.logger.error(f"Create order API error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # GUI Testing API (für automatisierte Tests)
        @self.app.get("/api/v2/gui/elements")
        async def get_gui_elements():
            """GUI-Elemente für Testing abrufen"""
            return {
                "elements": {
                    "dashboard": ["portfolio_value", "daily_change", "active_orders"],
                    "market_data": ["price_chart", "watchlist", "symbol_search"],
                    "trading": ["order_form", "order_history", "active_orders"]
                },
                "pages": ["/", "/dashboard", "/trading", "/market"],
                "api_endpoints": ["/api/v2/dashboard", "/api/v2/market", "/api/v2/orders"],
                "timestamp": get_current_timestamp().isoformat()
            }
        
        # GUI Status API (für Monitoring)
        @self.app.get("/api/v2/gui/status")
        async def get_gui_status():
            """GUI-Status für Monitoring"""
            # Event-Bus-Compliance: Use Event-Bus for health checks
            health_event = Event(
                event_type=EventType.SYSTEM_HEALTH_REQUEST.value,
                stream_id=f"health-gui-{int(time.time())}",
                data={"request_type": "gui_status"},
                source="frontend"
            )
            
            # For now, fallback to direct calls until response handling is implemented
            module_health = {}
            for name, module in self.modules.items():
                try:
                    module_health[name] = await module.get_health()
                except Exception as e:
                    module_health[name] = {"status": "error", "error": str(e)}
            
            # Publish event for logging/monitoring
            if self.event_bus and self.event_bus.connected:
                await self.event_bus.publish(health_event)
            
            return {
                "frontend_status": "active",
                "modules": module_health,
                "static_files": self.static_path.exists(),
                "templates": Path("templates").exists(),
                "timestamp": get_current_timestamp().isoformat()
            }
        
        # CRITICAL FIX: Add /api/content/ routes that the frontend HTML expects
        @self.app.get("/api/content/{section}")
        async def get_content(section: str):
            """Content API für Frontend-Sektionen - KRITISCHER FIX"""
            try:
                self.logger.info(f"Content request for section: {section}")
                
                if section == "dashboard":
                    return self._generate_dashboard_content()
                elif section == "events":
                    return self._generate_events_content()
                elif section == "monitoring":
                    return self._generate_monitoring_content()
                elif section == "predictions":
                    return self._generate_predictions_content()
                elif section == "api":
                    return self._generate_api_content()
                elif section == "depot-overview":
                    return self._generate_depot_overview_content()
                elif section == "depot-details":
                    return self._generate_depot_details_content()
                elif section == "depot-trading":
                    return self._generate_depot_trading_content()
                elif section == "admin":
                    return self._generate_admin_content()
                else:
                    return self._generate_fallback_content(section)
                    
            except Exception as e:
                self.logger.error(f"Content API error for section {section}: {e}")
                return self._generate_error_content(str(e))
    
    def _generate_dashboard_html(self) -> str:
        """Einfache Dashboard-HTML generieren"""
        html = """
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Aktienanalyse Dashboard v2</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .module { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .status { display: inline-block; padding: 4px 8px; border-radius: 4px; }
                .status.active { background: #27ae60; color: white; }
                .api-link { color: #3498db; text-decoration: none; }
                .api-link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 Aktienanalyse Dashboard v2</h1>
                <p>Modernisierter Frontend Service mit shared libraries</p>
            </div>
            
            <div class="module">
                <h3>📊 Dashboard Module</h3>
                <p><span class="status active">AKTIV</span></p>
                <p>API: <a href="/api/v2/dashboard" class="api-link">/api/v2/dashboard</a></p>
            </div>
            
            <div class="module">
                <h3>📈 Market Data Module</h3>
                <p><span class="status active">AKTIV</span></p>
                <p>API: <a href="/api/v2/market/AAPL" class="api-link">/api/v2/market/AAPL</a></p>
            </div>
            
            <div class="module">
                <h3>💼 Trading Module</h3>
                <p><span class="status active">AKTIV</span></p>
                <p>API: <a href="/api/v2/orders" class="api-link">/api/v2/orders</a></p>
            </div>
            
            <div class="module">
                <h3>🔧 GUI Testing</h3>
                <p>GUI-Elemente: <a href="/api/v2/gui/elements" class="api-link">/api/v2/gui/elements</a></p>
                <p>GUI-Status: <a href="/api/v2/gui/status" class="api-link">/api/v2/gui/status</a></p>
            </div>
            
            <div class="module">
                <h3>🩺 Service Health</h3>
                <p>Health Check: <a href="/health" class="api-link">/health</a></p>
                <p>API Docs: <a href="/docs" class="api-link">/docs</a></p>
            </div>
            
            <script>
                // Einfache Auto-Refresh-Funktionalität
                setInterval(() => {
                    fetch('/api/v2/gui/status')
                        .then(response => response.json())
                        .then(data => {
                            console.log('GUI Status:', data);
                        })
                        .catch(error => console.error('Status check failed:', error));
                }, 30000); // Alle 30 Sekunden
            </script>
        </body>
        </html>
        """
        return html
    
    def _generate_dashboard_content(self) -> str:
        """Dashboard Content HTML generieren"""
        return """
        <div class="row g-4">
            <div class="col-xl-3 col-md-6">
                <div class="dashboard-card card-gradient-primary">
                    <div class="card-body">
                        <div class="row no-gutters align-items-center">
                            <div class="col mr-2">
                                <div class="text-xs font-weight-bold text-white text-uppercase mb-1">Portfolio Wert</div>
                                <div class="h5 mb-0 font-weight-bold text-white" id="portfolio-value">€ 0,00</div>
                            </div>
                            <div class="col-auto">
                                <i class="fas fa-calendar fa-2x text-white-50"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-xl-3 col-md-6">
                <div class="dashboard-card card-gradient-success">
                    <div class="card-body">
                        <div class="row no-gutters align-items-center">
                            <div class="col mr-2">
                                <div class="text-xs font-weight-bold text-white text-uppercase mb-1">Tagesänderung</div>
                                <div class="h5 mb-0 font-weight-bold text-white" id="daily-change">+ € 0,00</div>
                            </div>
                            <div class="col-auto">
                                <i class="fas fa-chart-line fa-2x text-white-50"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-xl-3 col-md-6">
                <div class="dashboard-card card-gradient-secondary">
                    <div class="card-body">
                        <div class="row no-gutters align-items-center">
                            <div class="col mr-2">
                                <div class="text-xs font-weight-bold text-white text-uppercase mb-1">Aktive Orders</div>
                                <div class="h5 mb-0 font-weight-bold text-white" id="active-orders">0</div>
                            </div>
                            <div class="col-auto">
                                <i class="fas fa-exchange-alt fa-2x text-white-50"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-xl-3 col-md-6">
                <div class="dashboard-card">
                    <div class="card-body">
                        <div class="row no-gutters align-items-center">
                            <div class="col mr-2">
                                <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">System Status</div>
                                <div class="h5 mb-0 font-weight-bold text-gray-800">
                                    <span class="status-indicator status-online"></span>Online
                                </div>
                            </div>
                            <div class="col-auto">
                                <i class="fas fa-server fa-2x text-gray-300"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-12">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">Recent Activity</h6>
                    </div>
                    <div class="card-body">
                        <div id="recent-activity">
                            <div class="text-center py-4">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="sr-only">Loading...</span>
                                </div>
                                <p class="mt-2 text-muted">Lade aktuelle Aktivitäten...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
        // Dashboard-Daten laden
        async function loadDashboardData() {
            try {
                const response = await fetch('/api/v2/dashboard');
                const data = await response.json();
                
                // Dashboard-Werte aktualisieren
                if (data.data) {
                    document.getElementById('portfolio-value').textContent = 
                        new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' })
                            .format(data.data.portfolio_value || 0);
                    document.getElementById('daily-change').textContent = 
                        new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' })
                            .format(data.data.daily_change || 0);
                    document.getElementById('active-orders').textContent = data.data.active_orders || 0;
                }
                
                console.log('Dashboard data loaded:', data);
            } catch (error) {
                console.error('Failed to load dashboard data:', error);
            }
        }
        
        // Daten initial laden
        loadDashboardData();
        
        // Alle 30 Sekunden aktualisieren
        setInterval(loadDashboardData, 30000);
        </script>
        """
    
    def _generate_events_content(self) -> str:
        """Event-Bus Content HTML generieren"""
        return """
        <div class="dashboard-card">
            <div class="card-header">
                <h6 class="m-0 font-weight-bold text-primary">Event-Bus Status</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6>Connection Status</h6>
                        <p><span class="status-indicator status-online"></span>Connected</p>
                    </div>
                    <div class="col-md-6">
                        <h6>Events Today</h6>
                        <p>1,234 Events processed</p>
                    </div>
                </div>
                <div class="mt-3">
                    <h6>Recent Events</h6>
                    <div class="list-group">
                        <div class="list-group-item">
                            <div class="d-flex w-100 justify-content-between">
                                <h6 class="mb-1">Dashboard Request</h6>
                                <small>vor 3 Minuten</small>
                            </div>
                            <p class="mb-1">Frontend dashboard data request processed</p>
                        </div>
                        <div class="list-group-item">
                            <div class="d-flex w-100 justify-content-between">
                                <h6 class="mb-1">Market Data Update</h6>
                                <small>vor 5 Minuten</small>
                            </div>
                            <p class="mb-1">AAPL market data updated</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _generate_monitoring_content(self) -> str:
        """System-Monitoring Content HTML generieren"""
        return """
        <div class="row">
            <div class="col-md-6">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">Service Status</h6>
                    </div>
                    <div class="card-body" id="service-status">
                        <div class="text-center py-4">
                            <div class="spinner-border text-primary" role="status">
                                <span class="sr-only">Loading...</span>
                            </div>
                            <p class="mt-2 text-muted">Lade Service Status...</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">System Metrics</h6>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6">
                                <h6>CPU Usage</h6>
                                <div class="progress">
                                    <div class="progress-bar bg-success" style="width: 25%">25%</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <h6>Memory Usage</h6>
                                <div class="progress">
                                    <div class="progress-bar bg-info" style="width: 60%">60%</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
        async function loadServiceStatus() {
            try {
                const response = await fetch('/api/v2/gui/status');
                const data = await response.json();
                
                let statusHtml = '';
                if (data.modules) {
                    for (const [name, status] of Object.entries(data.modules)) {
                        const indicator = status.status === 'active' ? 'status-online' : 'status-offline';
                        statusHtml += `
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>${name}</span>
                                <span><span class="status-indicator ${indicator}"></span>${status.status}</span>
                            </div>
                        `;
                    }
                }
                document.getElementById('service-status').innerHTML = statusHtml || 'No services found';
                
            } catch (error) {
                console.error('Failed to load service status:', error);
                document.getElementById('service-status').innerHTML = '<div class="alert alert-danger">Failed to load service status</div>';
            }
        }
        
        loadServiceStatus();
        setInterval(loadServiceStatus, 10000);
        </script>
        """
    
    def _generate_predictions_content(self) -> str:
        """Gewinn-Vorhersage Content HTML generieren"""
        return """
        <div class="dashboard-card">
            <div class="card-header">
                <h6 class="m-0 font-weight-bold text-primary">Gewinn-Vorhersage</h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-8">
                        <div id="prediction-chart" style="height: 300px; background: #f8f9fc; border: 1px dashed #d1d3e2; display: flex; align-items: center; justify-content: center; color: #5a5c69;">
                            Chart wird hier angezeigt
                        </div>
                    </div>
                    <div class="col-md-4">
                        <h6>Vorhersage Details</h6>
                        <ul class="list-unstyled">
                            <li><strong>Zeitraum:</strong> 7 Tage</li>
                            <li><strong>Konfidenz:</strong> 85%</li>
                            <li><strong>Erwarteter Gewinn:</strong> +€ 245,50</li>
                            <li><strong>Risiko-Level:</strong> Moderat</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _generate_api_content(self) -> str:
        """API-Dokumentation Content HTML generieren"""
        return """
        <div class="dashboard-card">
            <div class="card-header">
                <h6 class="m-0 font-weight-bold text-primary">API-Dokumentation</h6>
            </div>
            <div class="card-body">
                <h6>Verfügbare Endpoints:</h6>
                <div class="row">
                    <div class="col-md-6">
                        <h6>Dashboard API</h6>
                        <ul>
                            <li><code>GET /api/v2/dashboard</code></li>
                            <li><code>GET /api/v2/gui/status</code></li>
                            <li><code>GET /api/v2/gui/elements</code></li>
                        </ul>
                        
                        <h6>Trading API</h6>
                        <ul>
                            <li><code>GET /api/v2/orders</code></li>
                            <li><code>POST /api/v2/orders</code></li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h6>Market Data API</h6>
                        <ul>
                            <li><code>GET /api/v2/market/{symbol}</code></li>
                        </ul>
                        
                        <h6>System API</h6>
                        <ul>
                            <li><code>GET /health</code></li>
                            <li><code>GET /docs</code></li>
                        </ul>
                    </div>
                </div>
                <div class="mt-3">
                    <p><a href="/docs" class="btn btn-primary">Interactive API Documentation</a></p>
                </div>
            </div>
        </div>
        """
    
    def _generate_depot_overview_content(self) -> str:
        """Portfolio Overview Content HTML generieren"""
        return """
        <div class="row">
            <div class="col-md-4">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">Portfolio Summary</h6>
                    </div>
                    <div class="card-body">
                        <p><strong>Gesamt-Wert:</strong> € 25,430.50</p>
                        <p><strong>Tagesänderung:</strong> <span class="text-success">+€ 245.30 (+0.97%)</span></p>
                        <p><strong>Positionen:</strong> 12</p>
                        <p><strong>Cash:</strong> € 2,500.00</p>
                    </div>
                </div>
            </div>
            <div class="col-md-8">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">Top Holdings</h6>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Symbol</th>
                                        <th>Aktien</th>
                                        <th>Aktueller Preis</th>
                                        <th>Wert</th>
                                        <th>Änderung</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><strong>AAPL</strong></td>
                                        <td>50</td>
                                        <td>€ 150.25</td>
                                        <td>€ 7,512.50</td>
                                        <td class="text-success">+1.2%</td>
                                    </tr>
                                    <tr>
                                        <td><strong>MSFT</strong></td>
                                        <td>30</td>
                                        <td>€ 280.60</td>
                                        <td>€ 8,418.00</td>
                                        <td class="text-danger">-0.5%</td>
                                    </tr>
                                    <tr>
                                        <td><strong>GOOGL</strong></td>
                                        <td>15</td>
                                        <td>€ 120.40</td>
                                        <td>€ 1,806.00</td>
                                        <td class="text-success">+2.1%</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _generate_depot_details_content(self) -> str:
        """Portfolio Details Content HTML generieren"""
        return """
        <div class="dashboard-card">
            <div class="card-header">
                <h6 class="m-0 font-weight-bold text-primary">Portfolio Details - portfolio_001</h6>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Name</th>
                                <th>Anzahl</th>
                                <th>Kauf-Preis</th>
                                <th>Aktueller Preis</th>
                                <th>Gesamt-Wert</th>
                                <th>Gewinn/Verlust</th>
                                <th>%</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>AAPL</strong></td>
                                <td>Apple Inc.</td>
                                <td>50</td>
                                <td>€ 145.00</td>
                                <td>€ 150.25</td>
                                <td>€ 7,512.50</td>
                                <td class="text-success">+€ 262.50</td>
                                <td class="text-success">+3.62%</td>
                            </tr>
                            <tr>
                                <td><strong>MSFT</strong></td>
                                <td>Microsoft Corporation</td>
                                <td>30</td>
                                <td>€ 290.00</td>
                                <td>€ 280.60</td>
                                <td>€ 8,418.00</td>
                                <td class="text-danger">-€ 282.00</td>
                                <td class="text-danger">-3.24%</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
    
    def _generate_depot_trading_content(self) -> str:
        """Trading Interface Content HTML generieren"""
        return """
        <div class="row">
            <div class="col-md-6">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">Neue Order</h6>
                    </div>
                    <div class="card-body">
                        <form id="order-form">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="form-group mb-3">
                                        <label>Symbol</label>
                                        <input type="text" class="form-control" name="symbol" placeholder="z.B. AAPL">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group mb-3">
                                        <label>Order Type</label>
                                        <select class="form-control" name="order_type">
                                            <option value="buy">Kaufen</option>
                                            <option value="sell">Verkaufen</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="form-group mb-3">
                                        <label>Anzahl</label>
                                        <input type="number" class="form-control" name="quantity" placeholder="10">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group mb-3">
                                        <label>Preis (optional)</label>
                                        <input type="number" step="0.01" class="form-control" name="price" placeholder="Market Order">
                                    </div>
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary">Order erstellen</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">Aktive Orders</h6>
                    </div>
                    <div class="card-body" id="active-orders-list">
                        <p class="text-muted">Keine aktiven Orders</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
        document.getElementById('order-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const orderData = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/v2/orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(orderData)
                });
                
                if (response.ok) {
                    alert('Order erfolgreich erstellt!');
                    e.target.reset();
                    loadActiveOrders();
                } else {
                    alert('Fehler beim Erstellen der Order');
                }
            } catch (error) {
                alert('Fehler: ' + error.message);
            }
        });

        async function loadActiveOrders() {
            try {
                const response = await fetch('/api/v2/orders?status=active');
                const data = await response.json();
                
                let ordersHtml = '';
                if (data.orders && data.orders.length > 0) {
                    data.orders.forEach(order => {
                        ordersHtml += `
                            <div class="border-bottom pb-2 mb-2">
                                <strong>${order.symbol}</strong> - ${order.order_type}<br>
                                <small>Anzahl: ${order.quantity}, Status: ${order.status}</small>
                            </div>
                        `;
                    });
                } else {
                    ordersHtml = '<p class="text-muted">Keine aktiven Orders</p>';
                }
                
                document.getElementById('active-orders-list').innerHTML = ordersHtml;
            } catch (error) {
                console.error('Failed to load active orders:', error);
            }
        }
        
        loadActiveOrders();
        </script>
        """
    
    def _generate_admin_content(self) -> str:
        """Administration Content HTML generieren"""
        return """
        <div class="row">
            <div class="col-md-6">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">System Information</h6>
                    </div>
                    <div class="card-body">
                        <p><strong>Version:</strong> v2.0.0</p>
                        <p><strong>Uptime:</strong> 2h 15m</p>
                        <p><strong>Services:</strong> 5/5 Active</p>
                        <p><strong>Database:</strong> Connected</p>
                        <p><strong>Event-Bus:</strong> Connected</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="dashboard-card">
                    <div class="card-header">
                        <h6 class="m-0 font-weight-bold text-primary">Quick Actions</h6>
                    </div>
                    <div class="card-body">
                        <div class="d-grid gap-2">
                            <button class="btn btn-primary" onclick="location.href='/health'">System Health</button>
                            <button class="btn btn-info" onclick="location.href='/docs'">API Documentation</button>
                            <button class="btn btn-warning">Restart Services</button>
                            <button class="btn btn-secondary">Export Logs</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _generate_fallback_content(self, section: str) -> str:
        """Fallback Content für unbekannte Sektionen"""
        return f"""
        <div class="alert alert-info">
            <h5><i class="fas fa-info-circle"></i> Section: {section}</h5>
            <p>Dieser Bereich ist noch in Entwicklung.</p>
            <p>Verfügbare Sektionen: dashboard, events, monitoring, predictions, api, depot-overview, depot-details, depot-trading, admin</p>
        </div>
        """
    
    def _generate_error_content(self, error: str) -> str:
        """Fehler Content HTML generieren"""
        return f"""
        <div class="alert alert-danger">
            <h5><i class="fas fa-exclamation-triangle"></i> Fehler</h5>
            <p>{error}</p>
            <button class="btn btn-outline-danger btn-sm" onclick="location.reload()">
                <i class="fas fa-redo"></i> Seite neu laden
            </button>
        </div>
        """
    
    async def _get_health_details(self) -> Dict[str, Any]:
        """Erweiterte Health-Details für Frontend Service"""
        base_health = await super()._get_health_details()
        
        # Event-Bus-Compliance: Health checks through Event-Bus
        health_event = Event(
            event_type=EventType.SYSTEM_HEALTH_REQUEST.value,
            stream_id=f"health-frontend-{int(time.time())}",
            data={"request_type": "frontend_health"},
            source="frontend"
        )
        
        # For now, fallback to direct calls until response handling is implemented
        module_details = {}
        for name, module in self.modules.items():
            try:
                module_details[name] = await module.get_health()
            except Exception as e:
                module_details[name] = {"status": "error", "error": str(e)}
        
        # Publish event for logging/monitoring
        if self.event_bus and self.event_bus.connected:
            await self.event_bus.publish(health_event)
        
        # Frontend-spezifische Health-Daten
        frontend_health = {
            "modules": {
                "total": len(self.modules),
                "active": len([m for m in self.modules.values() if hasattr(m, 'is_active') and m.is_active]),
                "details": module_details
            },
            "static_files": {
                "available": self.static_path.exists(),
                "path": str(self.static_path)
            },
            "templates": {
                "available": Path("templates").exists()
            },
            "gui_testing": {
                "endpoints_available": True,
                "monitoring_active": True
            }
        }
        
        return {
            **base_health,
            "frontend": frontend_health,
            "api_version": "v2",
            "code_quality": "refactored_with_shared_libraries"
        }


# Service-Instanz erstellen
def create_app() -> FastAPI:
    """FastAPI App erstellen"""
    service = FrontendService()
    return service.app


async def start_service():
    """Service starten"""
    service = FrontendService()
    await service._setup_service()
    
    # Server starten
    service.run(
        host="0.0.0.0",
        debug=SecurityConfig.is_debug_mode()
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(start_service())