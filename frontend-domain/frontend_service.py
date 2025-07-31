"""
🎨 Modular Frontend Service - Frontend-Domain
Event-Driven, Bus-Connected Frontend Service mit modularer Architektur
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Frontend-Domain Imports
import sys
sys.path.append(str(Path(__file__).parent))

from core_framework.content_providers import ContentProviderFactory
from core_framework.event_bus_connector import get_event_bus
from core_framework.api_routes import api_router
from core_framework.api_gateway_connector import get_api_gateway

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="Frontend-Domain Service",
    description="Modular UI Service mit Event-Bus Integration",
    version="1.0.0"
)

# Global Services
event_bus = get_event_bus()
api_gateway = get_api_gateway()
static_path = Path(__file__).parent / "static-assets"

# Include API Router
app.include_router(api_router)


class FrontendDomainService:
    """Hauptservice der Frontend-Domain"""
    
    def __init__(self):
        self.logger = logger
        self.event_bus = event_bus
        self.static_path = static_path
        self.content_providers = {}
        
    async def initialize(self):
        """Service initialisieren"""
        try:
            self.logger.info("🎨 Initializing Frontend-Domain Service...")
            
            # Event-Bus verbinden
            await self.event_bus.connect()
            
            # Content Providers initialisieren
            self._initialize_content_providers()
            
            # Static Files Setup
            await self._create_static_files()
            
            # Event: Service gestartet
            await self.event_bus.emit("frontend.service.started", {
                "service": "frontend-domain",
                "version": "1.0.0"
            })
            
            self.logger.info("✅ Frontend-Domain Service initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Frontend-Domain initialization failed: {e}")
            raise
    
    def _initialize_content_providers(self):
        """Content Providers registrieren"""
        providers = ['dashboard', 'predictions', 'monitoring', 'events', 'api']
        
        for provider_type in providers:
            provider = ContentProviderFactory.get_provider(provider_type, self.event_bus)
            if provider:
                self.content_providers[provider_type] = provider
                self.logger.info(f"📋 Content Provider registered: {provider_type}")
    
    async def get_content(self, section: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Content für spezifische Sektion abrufen"""
        try:
            provider = self.content_providers.get(section)
            if not provider:
                # Fallback für unbekannte Sektionen
                return f'''
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Content für "{section}" noch nicht implementiert
                </div>
                '''
            
            # Event: Content angefordert
            await self.event_bus.emit(f"frontend.content.requested", {
                "section": section,
                "context": context or {}
            })
            
            return await provider.get_content(context or {})
            
        except Exception as e:
            self.logger.error(f"❌ Content generation failed for {section}: {e}")
            return f'''
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Fehler beim Laden von "{section}": {str(e)}
            </div>
            '''
    
    async def _create_static_files(self):
        """Statische HTML-Dateien erstellen"""
        try:
            # Static-Verzeichnis erstellen
            self.static_path.mkdir(parents=True, exist_ok=True)
            
            # Haupt-HTML-Template
            html_content = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aktienanalyse-Ökosystem</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .sidebar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .sidebar-nav a { color: white; text-decoration: none; padding: 0.8rem 1.2rem; display: block; border-radius: 5px; margin: 0.2rem; }
        .sidebar-nav a:hover, .sidebar-nav a.active { background: rgba(255,255,255,0.2); }
        .status-card { border-left: 4px solid #007bff; }
        .metric-card { background: #f8f9fa; padding: 1rem; border-radius: 5px; }
        .loading-spinner { width: 1rem; height: 1rem; border: 2px solid #f3f4f6; border-top: 2px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-2 sidebar text-white vh-100 p-0">
                <div class="p-3">
                    <h4><i class="fas fa-chart-line me-2"></i>Aktienanalyse</h4>
                </div>
                <nav class="sidebar-nav">
                    <a href="#" id="nav-dashboard" onclick="loadContent('dashboard')" class="active">
                        <i class="fas fa-tachometer-alt me-2"></i> Dashboard
                    </a>
                    <a href="#" id="nav-predictions" onclick="loadContent('predictions')">
                        <i class="fas fa-chart-line me-2"></i> Gewinn-Vorhersage
                    </a>
                    <a href="#" id="nav-monitoring" onclick="loadContent('monitoring')">
                        <i class="fas fa-server me-2"></i> Monitoring
                    </a>
                    <a href="#" id="nav-events" onclick="loadContent('events')">
                        <i class="fas fa-broadcast-tower me-2"></i> Event-Bus
                    </a>
                    <a href="#" id="nav-api" onclick="loadContent('api')">
                        <i class="fas fa-code me-2"></i> API Dokumentation
                    </a>
                </nav>
            </div>
            
            <!-- Main Content -->
            <div class="col-md-10 p-4">
                <div id="main-content">
                    <div class="text-center">
                        <div class="loading-spinner mx-auto"></div>
                        <p class="mt-2">Lade Dashboard...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        let currentSection = 'dashboard';
        
        // Content laden
        async function loadContent(section) {
            try {
                // Navigation Update
                document.querySelectorAll('.sidebar-nav a').forEach(a => a.classList.remove('active'));
                document.getElementById('nav-' + section).classList.add('active');
                
                // Loading anzeigen
                document.getElementById('main-content').innerHTML = 
                    '<div class="text-center"><div class="loading-spinner mx-auto"></div><p class="mt-2">Lade ' + section + '...</p></div>';
                
                // Event: Navigation geändert
                if (typeof emitNavigationEvent === 'function') {
                    emitNavigationEvent(section, currentSection);
                }
                
                // Content laden
                const response = await fetch('/api/content/' + section);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const content = await response.text();
                document.getElementById('main-content').innerHTML = content;
                currentSection = section;
                
                console.log(`✅ Content loaded: ${section}`);
                
            } catch (error) {
                console.error('❌ Content loading failed:', error);
                document.getElementById('main-content').innerHTML = 
                    `<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>Fehler beim Laden: ${error.message}</div>`;
            }
        }
        
        // Event-Bus Integration (falls verfügbar)
        function emitNavigationEvent(newSection, oldSection) {
            // Hier würde Event an Bus gesendet werden
            console.log(`📍 Navigation: ${oldSection} → ${newSection}`);
        }
        
        // Page Load
        document.addEventListener('DOMContentLoaded', function() {
            loadContent('dashboard');
        });
    </script>
</body>
</html>'''
            
            # HTML-Datei schreiben
            with open(self.static_path / "index.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            
            self.logger.info("📄 Static HTML files created")
            
        except Exception as e:
            self.logger.error(f"❌ Static files creation failed: {e}")


# Service Instance
frontend_service = FrontendDomainService()


# FastAPI Routes
@app.on_event("startup")
async def startup_event():
    """Service starten"""
    await frontend_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Service beenden"""
    await event_bus.disconnect()
    await api_gateway.cleanup()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Hauptseite"""
    return FileResponse(frontend_service.static_path / "index.html")

@app.get("/predictions", response_class=HTMLResponse)
async def predictions_page():
    """Direkte Predictions-Seite"""
    return FileResponse(frontend_service.static_path / "index.html")

@app.get("/api/content/{section}")
async def get_content(section: str):
    """Content für spezifische Sektion"""
    content = await frontend_service.get_content(section)
    return HTMLResponse(content)

@app.get("/health")
async def health_check():
    """Health Check"""
    return {
        "status": "healthy",
        "service": "frontend-domain",
        "timestamp": datetime.now().isoformat(),
        "event_bus_connected": event_bus.connected
    }


# Development Server
if __name__ == "__main__":
    uvicorn.run(
        "frontend_service:app",
        host="0.0.0.0", 
        port=8084,
        reload=True,
        log_level="info"
    )