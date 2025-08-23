#!/usr/bin/env python3
"""
System Monitoring Content Provider v1.0.0
Provider für System-Monitoring Dashboard mit Realtime Kreisdiagrammen
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import aiohttp
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class SystemMonitoringContentProvider:
    """Content Provider für System-Monitoring Dashboard."""
    
    def __init__(self, event_bus, api_gateway):
        self.event_bus = event_bus
        self.api_gateway = api_gateway
        self.logger = logger
        self.dashboard_template_path = Path(__file__).parent / "dashboard-components" / "system_monitoring_dashboard.html"
    
    async def get_content(self, context: Dict[str, Any] = None) -> str:
        """Generiert System-Monitoring Dashboard Content."""
        try:
            # Lade Dashboard Template
            if self.dashboard_template_path.exists():
                with open(self.dashboard_template_path, 'r', encoding='utf-8') as f:
                    dashboard_content = f.read()
            else:
                # Fallback Dashboard wenn Template nicht verfügbar
                dashboard_content = self._get_fallback_dashboard()
            
            # Event Bus Benachrichtigung
            if self.event_bus:
                await self.event_bus.emit("frontend.system_monitoring.loaded", {
                    "status": "success",
                    "context": context or {}
                })
            
            self.logger.info("✅ System Monitoring Dashboard content generated")
            return dashboard_content
            
        except Exception as e:
            self.logger.error(f"❌ Error generating system monitoring content: {e}")
            return self._get_error_content(str(e))
    
    def _get_fallback_dashboard(self) -> str:
        """Fallback Dashboard falls Template nicht verfügbar."""
        return '''
        <div class="container-fluid">
            <div class="row mb-4">
                <div class="col-12">
                    <div class="alert alert-info">
                        <h4><i class="fas fa-desktop me-2"></i>System-Monitoring</h4>
                        <p>Realtime System-Auslastung wird geladen...</p>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-lg-4 mb-4">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h6><i class="fas fa-microchip me-2"></i>CPU Auslastung</h6>
                        </div>
                        <div class="card-body text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2">Lade CPU-Daten...</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-4 mb-4">
                    <div class="card">
                        <div class="card-header bg-success text-white">
                            <h6><i class="fas fa-memory me-2"></i>RAM Auslastung</h6>
                        </div>
                        <div class="card-body text-center">
                            <div class="spinner-border text-success" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2">Lade RAM-Daten...</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-4 mb-4">
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <h6><i class="fas fa-hdd me-2"></i>Disk Auslastung</h6>
                        </div>
                        <div class="card-body text-center">
                            <div class="spinner-border text-info" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2">Lade Disk-Daten...</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>Template nicht gefunden:</strong> 
                        System-Monitoring Dashboard Template wurde nicht gefunden. 
                        Bitte stellen Sie sicher, dass die Datei 
                        <code>dashboard-components/system_monitoring_dashboard.html</code> existiert.
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        // Fallback: Versuche System-Monitoring API direkt zu erreichen
        setTimeout(async () => {
            try {
                const response = await fetch('http://127.0.0.1:8020/health');
                if (response.ok) {
                    const data = await response.json();
                    console.log('✅ System Monitoring API is reachable:', data);
                    
                    // Zeige erfolgreiche Verbindung an
                    document.querySelector('.alert-warning').className = 'alert alert-success';
                    document.querySelector('.alert-success i').className = 'fas fa-check-circle me-2';
                    document.querySelector('.alert-success').innerHTML = `
                        <i class="fas fa-check-circle me-2"></i>
                        <strong>System-Monitoring API Online:</strong> 
                        CPU: ${data.cpu_percent}%, RAM: ${data.ram_percent}%, Disk: ${data.disk_percent}%
                    `;
                }
            } catch (error) {
                console.error('❌ System Monitoring API not reachable:', error);
            }
        }, 1000);
        </script>
        '''
    
    def _get_error_content(self, error_message: str) -> str:
        """Error Content für System-Monitoring."""
        return f'''
        <div class="container-fluid">
            <div class="alert alert-danger">
                <h4><i class="fas fa-exclamation-triangle me-2"></i>System-Monitoring Fehler</h4>
                <p><strong>Fehler beim Laden des System-Monitoring Dashboards:</strong></p>
                <p><code>{error_message}</code></p>
                
                <hr>
                
                <div class="d-flex gap-2">
                    <button class="btn btn-outline-danger btn-sm" onclick="location.reload()">
                        <i class="fas fa-redo me-1"></i> Seite neu laden
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" onclick="loadContent('dashboard')">
                        <i class="fas fa-home me-1"></i> Zurück zum Dashboard
                    </button>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h6><i class="fas fa-tools me-2"></i>Troubleshooting</h6>
                </div>
                <div class="card-body">
                    <h6>Mögliche Lösungen:</h6>
                    <ul>
                        <li>Stellen Sie sicher, dass die System-Monitoring API läuft (Port 8020)</li>
                        <li>Überprüfen Sie, ob das Dashboard-Template verfügbar ist</li>
                        <li>Überprüfen Sie die Netzwerkverbindung zum Monitoring-Service</li>
                        <li>Schauen Sie in die Logs für weitere Details</li>
                    </ul>
                    
                    <div class="mt-3">
                        <small class="text-muted">
                            <strong>Service-URLs:</strong><br>
                            • System Monitoring API: <code>http://127.0.0.1:8020</code><br>
                            • WebSocket: <code>ws://127.0.0.1:8020/ws/system-stats</code>
                        </small>
                    </div>
                </div>
            </div>
        </div>
        '''

class SystemMonitoringContentProviderFactory:
    """Factory für System-Monitoring Content Provider."""
    
    @staticmethod
    def get_provider(provider_type: str, event_bus, api_gateway) -> SystemMonitoringContentProvider:
        """Factory Methode für System-Monitoring Provider."""
        if provider_type == 'monitoring':
            return SystemMonitoringContentProvider(event_bus, api_gateway)
        else:
            raise ValueError(f"Unknown system monitoring provider type: {provider_type}")

# Alias für einfacheren Import
MonitoringContentProvider = SystemMonitoringContentProvider
MonitoringProviderFactory = SystemMonitoringContentProviderFactory