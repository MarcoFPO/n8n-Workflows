"""
Content Provider Module - Frontend-Domain
Generiert strukturierte Inhalte für verschiedene UI-Bereiche
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from .api_gateway_connector import get_api_gateway

logger = logging.getLogger(__name__)


class BaseContentProvider(ABC):
    """Basis-Klasse für alle Content Provider"""
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.api_gateway = get_api_gateway()
        self.logger = logger
    
    @abstractmethod
    async def get_content(self, context: Dict[str, Any]) -> str:
        """Generiert HTML-Content basierend auf Kontext"""
        pass
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Sendet Event über Bus"""
        if self.event_bus:
            await self.event_bus.emit(event_type, data)


class DashboardContentProvider(BaseContentProvider):
    """Dashboard-Content mit System-Übersicht"""
    
    async def get_content(self, context: Dict[str, Any]) -> str:
        """Dashboard-HTML mit System-Metriken"""
        try:
            # Event: Dashboard-Content angefordert
            await self.emit_event("frontend.dashboard.requested", {
                "timestamp": datetime.now().isoformat(),
                "context": context
            })
            
            return '''
            <div class="row">
                <div class="col-md-4 mb-4">
                    <div class="card status-card">
                        <div class="card-body text-center">
                            <i class="fas fa-microchip fa-2x mb-2"></i>
                            <h3 id="cpu-usage">Loading...</h3>
                            <p class="mb-0">CPU Auslastung</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card status-card">
                        <div class="card-body text-center">
                            <i class="fas fa-memory fa-2x mb-2"></i>
                            <h3 id="memory-usage">Loading...</h3>
                            <p class="mb-0">Speicher</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card status-card">
                        <div class="card-body text-center">
                            <i class="fas fa-server fa-2x mb-2"></i>
                            <h3 id="active-services">Loading...</h3>
                            <p class="mb-0">Services</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
            // Dashboard initialisiert Event senden
            document.addEventListener('DOMContentLoaded', function() {
                if (typeof updateDashboardMetrics === 'function') {
                    updateDashboardMetrics();
                }
            });
            </script>
            '''
            
        except Exception as e:
            self.logger.error(f"Dashboard content error: {e}")
            return f'<div class="alert alert-danger">Dashboard-Fehler: {e}</div>'


class PredictionsContentProvider(BaseContentProvider):
    """Predictions-Content mit Live-Tabelle und Timeframe-Buttons"""
    
    async def get_content(self, context: Dict[str, Any]) -> str:
        """Vollständige Predictions-Seite"""
        try:
            await self.emit_event("frontend.predictions.requested", {
                "timestamp": datetime.now().isoformat(),
                "context": context
            })
            
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
            // Predictions-spezifische Funktionen
            let currentTimeframe = '1M';
            
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
                    
                    // Update timestamp
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
                    
                    // Loading state
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
            
            // Auto-Initialisierung
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
            self.logger.error(f"Predictions content error: {e}")
            return f'<div class="alert alert-danger">Predictions-Fehler: {e}</div>'


class MonitoringContentProvider(BaseContentProvider):
    """Monitoring-Content mit Live-Metriken"""
    
    async def get_content(self, context: Dict[str, Any]) -> str:
        try:
            await self.emit_event("frontend.monitoring.requested", {
                "timestamp": datetime.now().isoformat()
            })
            
            return '''
            <div class="card">
                <div class="card-header">
                    <h5><i class="fas fa-chart-line me-2"></i>Live Monitoring</h5>
                </div>
                <div class="card-body">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        System-Monitoring läuft kontinuierlich. Alle Services sind operational.
                    </div>
                    
                    <div id="monitoring-metrics" class="row">
                        <div class="col-md-6 mb-3">
                            <div class="metric-card">
                                <h6><i class="fas fa-microchip me-2"></i>CPU Auslastung</h6>
                                <div class="progress mb-2">
                                    <div class="progress-bar" id="cpu-progress" style="width: 0%"></div>
                                </div>
                                <small class="text-muted" id="cpu-details">Lade...</small>
                            </div>
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="metric-card">
                                <h6><i class="fas fa-memory me-2"></i>Speicher</h6>
                                <div class="progress mb-2">
                                    <div class="progress-bar bg-warning" id="memory-progress" style="width: 0%"></div>
                                </div>
                                <small class="text-muted" id="memory-details">Lade...</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
            async function updateMonitoringMetrics() {
                try {
                    const response = await fetch('/api/monitoring/metrics');
                    const data = await response.json();
                    
                    // CPU Update
                    const cpuProgress = document.getElementById('cpu-progress');
                    const cpuDetails = document.getElementById('cpu-details');
                    if (cpuProgress && data.system) {
                        cpuProgress.style.width = `${data.system.cpu_percent}%`;
                        cpuDetails.textContent = `${data.system.cpu_percent.toFixed(1)}% von ${data.system.cpu_count} Cores`;
                    }
                    
                    // Memory Update  
                    const memoryProgress = document.getElementById('memory-progress');
                    const memoryDetails = document.getElementById('memory-details');
                    if (memoryProgress && data.system) {
                        memoryProgress.style.width = `${data.system.memory_percent}%`;
                        memoryDetails.textContent = `${data.system.memory_used_gb.toFixed(1)} GB von ${data.system.memory_total_gb.toFixed(1)} GB`;
                    }
                    
                } catch (error) {
                    console.error('Monitoring metrics error:', error);
                }
            }
            
            // Auto-Update alle 5 Sekunden
            setInterval(updateMonitoringMetrics, 5000);
            updateMonitoringMetrics(); // Initial load
            </script>
            '''
            
        except Exception as e:
            self.logger.error(f"Monitoring content error: {e}")
            return f'<div class="alert alert-danger">Monitoring-Fehler: {e}</div>'


# Content Provider Factory
class ContentProviderFactory:
    """Factory für Content Provider"""
    
    _providers = {
        'dashboard': DashboardContentProvider,
        'predictions': PredictionsContentProvider,
        'monitoring': MonitoringContentProvider,
    }
    
    @classmethod
    def get_provider(cls, content_type: str, event_bus=None) -> Optional[BaseContentProvider]:
        """Gibt entsprechenden Content Provider zurück"""
        provider_class = cls._providers.get(content_type)
        if provider_class:
            return provider_class(event_bus)
        return None
    
    @classmethod
    def register_provider(cls, content_type: str, provider_class):
        """Registriert neuen Content Provider"""
        cls._providers[content_type] = provider_class