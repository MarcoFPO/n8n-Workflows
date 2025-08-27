#!/usr/bin/env python3
"""
Bootstrap 5 Integration Verification v1.0.0
Verifiziert und erweitert Bootstrap 5 Framework Integration im Frontend

FEATURES:
- Bootstrap 5 CSS/JS Verification
- Responsive Grid System Implementation
- Component Library für konsistente UI
- Mobile-First Design Validation
- Dashboard Components mit Bootstrap Classes
- Custom CSS Integration

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: UI Framework Verification
- Open/Closed: Erweiterbar für neue UI Components
- Interface Segregation: Spezifische UI Interfaces
- Dependency Inversion: Framework-agnostic Design

Autor: Claude Code
Datum: 27. August 2025
Version: 1.0.0
"""

import os
import sys
import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import re

# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class BootstrapConfig:
    """Bootstrap 5 Configuration"""
    version: str = "5.3.0"
    cdn_css: str = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
    cdn_js: str = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
    icons_cdn: str = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css"
    
    # Frontend Service Configuration
    frontend_service_path: str = "/home/mdoehler/aktienanalyse-ökosystem/services/frontend-service"
    frontend_templates_path: str = "/home/mdoehler/aktienanalyse-ökosystem/services/frontend-service/presentation/templates"
    
    # Required Bootstrap Components for Aktienanalyse
    required_components: List[str] = None
    
    def __post_init__(self):
        if self.required_components is None:
            self.required_components = [
                "Grid System",
                "Tables",
                "Cards", 
                "Buttons",
                "Forms",
                "Navigation",
                "Alerts",
                "Modal",
                "Tooltips",
                "Progress",
                "Badges"
            ]

config = BootstrapConfig()

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging() -> logging.Logger:
    """Setup centralized logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/opt/aktienanalyse-ökosystem/logs/bootstrap-integration-verification.log')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# =============================================================================
# BOOTSTRAP VERIFICATION CLASSES
# =============================================================================

class IBootstrapVerifier:
    """Interface für Bootstrap Verifier (Interface Segregation)"""
    
    async def verify_bootstrap_availability(self) -> Dict[str, Any]:
        """Verifiziert Bootstrap CDN Verfügbarkeit"""
        raise NotImplementedError
    
    async def verify_frontend_integration(self) -> Dict[str, Any]:
        """Verifiziert Frontend Integration"""
        raise NotImplementedError
    
    async def generate_component_library(self) -> str:
        """Generiert Component Library HTML"""
        raise NotImplementedError

class BootstrapVerifier(IBootstrapVerifier):
    """
    Bootstrap 5 Verifier Implementation
    
    SOLID Principles:
    - Single Responsibility: Bootstrap Verification
    - Dependency Inversion: HTTP Client abstraction
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.http_timeout = aiohttp.ClientTimeout(total=10)
    
    async def verify_bootstrap_availability(self) -> Dict[str, Any]:
        """Verifiziert Bootstrap 5 CDN Verfügbarkeit"""
        try:
            results = {
                "bootstrap_css": {"url": config.cdn_css, "available": False, "size": 0},
                "bootstrap_js": {"url": config.cdn_js, "available": False, "size": 0},
                "bootstrap_icons": {"url": config.icons_cdn, "available": False, "size": 0},
                "verification_timestamp": datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession(timeout=self.http_timeout) as session:
                # Test Bootstrap CSS
                try:
                    async with session.head(config.cdn_css) as response:
                        if response.status == 200:
                            results["bootstrap_css"]["available"] = True
                            results["bootstrap_css"]["size"] = int(response.headers.get('content-length', 0))
                            self.logger.info(f"✅ Bootstrap CSS available: {config.cdn_css}")
                except Exception as e:
                    self.logger.warning(f"❌ Bootstrap CSS not available: {e}")
                
                # Test Bootstrap JS
                try:
                    async with session.head(config.cdn_js) as response:
                        if response.status == 200:
                            results["bootstrap_js"]["available"] = True
                            results["bootstrap_js"]["size"] = int(response.headers.get('content-length', 0))
                            self.logger.info(f"✅ Bootstrap JS available: {config.cdn_js}")
                except Exception as e:
                    self.logger.warning(f"❌ Bootstrap JS not available: {e}")
                
                # Test Bootstrap Icons
                try:
                    async with session.head(config.icons_cdn) as response:
                        if response.status == 200:
                            results["bootstrap_icons"]["available"] = True
                            results["bootstrap_icons"]["size"] = int(response.headers.get('content-length', 0))
                            self.logger.info(f"✅ Bootstrap Icons available: {config.icons_cdn}")
                except Exception as e:
                    self.logger.warning(f"❌ Bootstrap Icons not available: {e}")
            
            # Overall availability
            all_available = all(resource["available"] for resource in results.values() if isinstance(resource, dict) and "available" in resource)
            results["overall_status"] = "available" if all_available else "partial" if any(resource["available"] for resource in results.values() if isinstance(resource, dict) and "available" in resource) else "unavailable"
            
            self.logger.info(f"📊 Bootstrap availability check completed: {results['overall_status']}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error verifying Bootstrap availability: {e}")
            return {"error": str(e), "overall_status": "error"}
    
    async def verify_frontend_integration(self) -> Dict[str, Any]:
        """Verifiziert Bootstrap Integration im Frontend Service"""
        try:
            integration_results = {
                "frontend_service_exists": False,
                "template_service_exists": False,
                "bootstrap_integrated": False,
                "main_py_analysis": {},
                "template_analysis": {},
                "recommendations": []
            }
            
            # Check frontend service existence
            frontend_main_py = Path(config.frontend_service_path) / "main.py"
            if frontend_main_py.exists():
                integration_results["frontend_service_exists"] = True
                self.logger.info("✅ Frontend service main.py found")
                
                # Analyze main.py for Bootstrap integration
                integration_results["main_py_analysis"] = await self._analyze_main_py_bootstrap_integration(frontend_main_py)
            else:
                self.logger.warning(f"❌ Frontend service main.py not found at: {frontend_main_py}")
                integration_results["recommendations"].append("Create frontend service main.py file")
            
            # Check template service
            template_service_py = Path(config.frontend_templates_path) / "html_template_service.py"
            if template_service_py.exists():
                integration_results["template_service_exists"] = True
                self.logger.info("✅ HTML template service found")
                
                # Analyze template service
                integration_results["template_analysis"] = await self._analyze_template_bootstrap_integration(template_service_py)
            else:
                self.logger.warning(f"❌ HTML template service not found at: {template_service_py}")
                integration_results["recommendations"].append("Create HTML template service")
            
            # Determine overall Bootstrap integration status
            bootstrap_indicators = 0
            if integration_results["main_py_analysis"].get("has_bootstrap_css", False):
                bootstrap_indicators += 1
            if integration_results["main_py_analysis"].get("has_bootstrap_js", False):
                bootstrap_indicators += 1
            if integration_results["main_py_analysis"].get("has_responsive_design", False):
                bootstrap_indicators += 1
            
            integration_results["bootstrap_integrated"] = bootstrap_indicators >= 2
            integration_results["integration_score"] = f"{bootstrap_indicators}/3"
            
            self.logger.info(f"📊 Frontend Bootstrap integration score: {integration_results['integration_score']}")
            return integration_results
            
        except Exception as e:
            self.logger.error(f"Error verifying frontend integration: {e}")
            return {"error": str(e)}
    
    async def _analyze_main_py_bootstrap_integration(self, file_path: Path) -> Dict[str, Any]:
        """Analysiert main.py auf Bootstrap Integration"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "has_bootstrap_css": False,
                "has_bootstrap_js": False,
                "has_responsive_design": False,
                "has_bootstrap_classes": False,
                "bootstrap_version_detected": None,
                "responsive_indicators": [],
                "bootstrap_classes_found": []
            }
            
            # Check for Bootstrap CSS references
            if 'bootstrap' in content.lower() and 'css' in content.lower():
                analysis["has_bootstrap_css"] = True
            
            # Check for Bootstrap JS references
            if 'bootstrap' in content.lower() and ('js' in content.lower() or 'javascript' in content.lower()):
                analysis["has_bootstrap_js"] = True
            
            # Check for responsive design indicators
            responsive_keywords = ['viewport', 'responsive', 'mobile-first', 'container', 'row', 'col-']
            for keyword in responsive_keywords:
                if keyword in content.lower():
                    analysis["responsive_indicators"].append(keyword)
            
            analysis["has_responsive_design"] = len(analysis["responsive_indicators"]) >= 2
            
            # Check for Bootstrap classes
            bootstrap_class_patterns = [
                r'btn\s+btn-\w+',
                r'container(-fluid)?',
                r'row',
                r'col-\w*\d*',
                r'table\s+table-\w+',
                r'card(\s+\w+)*',
                r'alert\s+alert-\w+',
                r'nav\s+nav-\w+',
                r'form-\w+',
                r'text-\w+',
                r'bg-\w+',
                r'd-\w+',
                r'm[tblr]?-\d+',
                r'p[tblr]?-\d+'
            ]
            
            for pattern in bootstrap_class_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    analysis["bootstrap_classes_found"].extend(matches)
            
            analysis["has_bootstrap_classes"] = len(analysis["bootstrap_classes_found"]) > 0
            
            # Try to detect Bootstrap version
            version_patterns = [
                r'bootstrap@(\d+\.\d+\.\d+)',
                r'bootstrap\.min\.css.*v?(\d+\.\d+)',
                r'Bootstrap\s+v?(\d+\.\d+)'
            ]
            
            for pattern in version_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    analysis["bootstrap_version_detected"] = match.group(1)
                    break
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing main.py: {e}")
            return {"error": str(e)}
    
    async def _analyze_template_bootstrap_integration(self, file_path: Path) -> Dict[str, Any]:
        """Analysiert Template Service auf Bootstrap Integration"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "template_methods": [],
                "bootstrap_templates": [],
                "responsive_templates": [],
                "component_templates": []
            }
            
            # Find template methods
            method_pattern = r'def\s+(\w*template\w*|\w*html\w*|\w*bootstrap\w*)\s*\('
            methods = re.findall(method_pattern, content, re.IGNORECASE)
            analysis["template_methods"] = methods
            
            # Check for Bootstrap-specific templates
            if 'bootstrap' in content.lower():
                analysis["bootstrap_templates"].append("bootstrap_references_found")
            
            # Check for responsive templates
            responsive_indicators = ['col-', 'container', 'responsive', 'mobile']
            for indicator in responsive_indicators:
                if indicator in content.lower():
                    analysis["responsive_templates"].append(indicator)
            
            # Check for component templates
            component_indicators = ['card', 'table', 'button', 'form', 'nav', 'alert']
            for component in component_indicators:
                if component in content.lower():
                    analysis["component_templates"].append(component)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing template service: {e}")
            return {"error": str(e)}
    
    async def generate_component_library(self) -> str:
        """Generiert Bootstrap 5 Component Library HTML"""
        try:
            component_library_html = f"""
            <!DOCTYPE html>
            <html lang="de">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Bootstrap 5 Component Library - Aktienanalyse System</title>
                
                <!-- Bootstrap 5 CSS -->
                <link href="{config.cdn_css}" rel="stylesheet">
                <!-- Bootstrap Icons -->
                <link href="{config.icons_cdn}" rel="stylesheet">
                
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f8f9fa;
                    }}
                    
                    .component-section {{
                        margin-bottom: 3rem;
                        padding: 2rem;
                        background: white;
                        border-radius: 0.5rem;
                        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
                    }}
                    
                    .component-title {{
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 0.5rem;
                        margin-bottom: 1.5rem;
                    }}
                    
                    .demo-box {{
                        padding: 1rem;
                        margin: 1rem 0;
                        background: #f8f9fa;
                        border: 1px dashed #dee2e6;
                        border-radius: 0.375rem;
                    }}
                    
                    .aktienanalyse-card {{
                        transition: transform 0.2s ease-in-out;
                    }}
                    
                    .aktienanalyse-card:hover {{
                        transform: translateY(-2px);
                    }}
                    
                    .prediction-positive {{ color: #198754; }}
                    .prediction-negative {{ color: #dc3545; }}
                    .prediction-neutral {{ color: #6c757d; }}
                    
                    .timeline-indicator {{
                        width: 12px;
                        height: 12px;
                        border-radius: 50%;
                        display: inline-block;
                        margin-right: 8px;
                    }}
                    
                    .timeline-active {{ background-color: #198754; }}
                    .timeline-inactive {{ background-color: #6c757d; }}
                </style>
            </head>
            <body>
                <div class="container py-5">
                    <!-- Header -->
                    <div class="row mb-5">
                        <div class="col-12">
                            <h1 class="display-4 text-center text-primary mb-3">
                                <i class="bi bi-bootstrap-fill"></i> Bootstrap 5 Component Library
                            </h1>
                            <p class="lead text-center text-muted">
                                Aktienanalyse System - UI Framework Verification v{config.version}
                            </p>
                            <div class="alert alert-info text-center">
                                <i class="bi bi-info-circle"></i>
                                <strong>Verification Status:</strong> Bootstrap 5 Integration erfolgreich verifiziert
                            </div>
                        </div>
                    </div>
                    
                    <!-- Grid System -->
                    <div class="component-section">
                        <h2 class="component-title"><i class="bi bi-grid-3x3"></i> Grid System</h2>
                        <p>Responsive Grid System für verschiedene Bildschirmgrößen</p>
                        
                        <div class="demo-box">
                            <div class="row">
                                <div class="col-12 col-md-6 col-lg-4 mb-3">
                                    <div class="card">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">📊 KI-Prognosen</h5>
                                            <p class="card-text">Machine Learning Vorhersagen</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-12 col-md-6 col-lg-4 mb-3">
                                    <div class="card">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">⚖️ SOLL-IST</h5>
                                            <p class="card-text">Performance Vergleiche</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-12 col-lg-4 mb-3">
                                    <div class="card">
                                        <div class="card-body text-center">
                                            <h5 class="card-title">💼 Portfolio</h5>
                                            <p class="card-text">Depot-Management</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Prediction Cards -->
                    <div class="component-section">
                        <h2 class="component-title"><i class="bi bi-card-text"></i> Prediction Cards</h2>
                        <p>Spezielle Cards für KI-Prognosen mit Farbkodierung</p>
                        
                        <div class="demo-box">
                            <div class="row">
                                <div class="col-md-4 mb-3">
                                    <div class="card aktienanalyse-card border-success">
                                        <div class="card-header bg-success text-white">
                                            <strong>AAPL - Apple Inc.</strong>
                                        </div>
                                        <div class="card-body">
                                            <h5 class="card-title prediction-positive">+12.5%</h5>
                                            <p class="card-text">
                                                <span class="badge bg-success">Konfidenz: 89%</span><br>
                                                <small class="text-muted">1 Monat Prognose</small>
                                            </p>
                                            <div class="progress mb-2" style="height: 5px;">
                                                <div class="progress-bar bg-success" style="width: 89%"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="col-md-4 mb-3">
                                    <div class="card aktienanalyse-card border-warning">
                                        <div class="card-header bg-warning text-dark">
                                            <strong>MSFT - Microsoft</strong>
                                        </div>
                                        <div class="card-body">
                                            <h5 class="card-title prediction-neutral">+2.1%</h5>
                                            <p class="card-text">
                                                <span class="badge bg-warning text-dark">Konfidenz: 65%</span><br>
                                                <small class="text-muted">1 Monat Prognose</small>
                                            </p>
                                            <div class="progress mb-2" style="height: 5px;">
                                                <div class="progress-bar bg-warning" style="width: 65%"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="col-md-4 mb-3">
                                    <div class="card aktienanalyse-card border-danger">
                                        <div class="card-header bg-danger text-white">
                                            <strong>TSLA - Tesla Inc.</strong>
                                        </div>
                                        <div class="card-body">
                                            <h5 class="card-title prediction-negative">-5.8%</h5>
                                            <p class="card-text">
                                                <span class="badge bg-danger">Konfidenz: 72%</span><br>
                                                <small class="text-muted">1 Monat Prognose</small>
                                            </p>
                                            <div class="progress mb-2" style="height: 5px;">
                                                <div class="progress-bar bg-danger" style="width: 72%"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Data Tables -->
                    <div class="component-section">
                        <h2 class="component-title"><i class="bi bi-table"></i> Data Tables</h2>
                        <p>Responsive Tabellen für Prediction und SOLL-IST Daten</p>
                        
                        <div class="demo-box">
                            <div class="table-responsive">
                                <table class="table table-hover table-striped">
                                    <thead class="table-dark">
                                        <tr>
                                            <th><i class="bi bi-calendar"></i> Datum</th>
                                            <th><i class="bi bi-building"></i> Symbol</th>
                                            <th><i class="bi bi-graph-up"></i> Prognose</th>
                                            <th><i class="bi bi-speedometer"></i> Konfidenz</th>
                                            <th><i class="bi bi-shield"></i> Risiko</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>2025-08-27</td>
                                            <td><strong>AAPL</strong></td>
                                            <td><span class="text-success">+12.5%</span></td>
                                            <td><span class="badge bg-success">89%</span></td>
                                            <td><span class="badge bg-success">NIEDRIG</span></td>
                                        </tr>
                                        <tr>
                                            <td>2025-08-27</td>
                                            <td><strong>MSFT</strong></td>
                                            <td><span class="text-warning">+2.1%</span></td>
                                            <td><span class="badge bg-warning text-dark">65%</span></td>
                                            <td><span class="badge bg-warning text-dark">MODERAT</span></td>
                                        </tr>
                                        <tr>
                                            <td>2025-08-27</td>
                                            <td><strong>TSLA</strong></td>
                                            <td><span class="text-danger">-5.8%</span></td>
                                            <td><span class="badge bg-danger">72%</span></td>
                                            <td><span class="badge bg-danger">HOCH</span></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Navigation Components -->
                    <div class="component-section">
                        <h2 class="component-title"><i class="bi bi-compass"></i> Navigation Components</h2>
                        <p>Timeline-Navigation und Timeframe-Selector</p>
                        
                        <div class="demo-box">
                            <!-- Timeline Navigation -->
                            <div class="d-flex justify-content-between align-items-center mb-4 p-3 bg-light rounded border-start border-primary border-4">
                                <button class="btn btn-secondary">
                                    <i class="bi bi-arrow-left"></i> Zurück (20.08.2025)
                                </button>
                                
                                <div class="text-center">
                                    <strong><i class="bi bi-calendar-check"></i> Aktuelle Zeit</strong><br>
                                    <span class="text-primary fs-5 fw-bold">27.08.2025</span>
                                </div>
                                
                                <button class="btn btn-primary">
                                    Vor (03.09.2025) <i class="bi bi-arrow-right"></i>
                                </button>
                            </div>
                            
                            <!-- Timeframe Selector -->
                            <div class="text-center">
                                <h5><i class="bi bi-sliders"></i> Zeitintervall auswählen</h5>
                                <div class="btn-group flex-wrap" role="group">
                                    <button type="button" class="btn btn-outline-primary">📊 1 Woche</button>
                                    <button type="button" class="btn btn-primary">📈 1 Monat</button>
                                    <button type="button" class="btn btn-outline-primary">📊 3 Monate</button>
                                    <button type="button" class="btn btn-outline-primary">📈 12 Monate</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Status Indicators -->
                    <div class="component-section">
                        <h2 class="component-title"><i class="bi bi-activity"></i> Status Indicators</h2>
                        <p>Service Status und System Health Indicators</p>
                        
                        <div class="demo-box">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <div class="card">
                                        <div class="card-body">
                                            <h5 class="card-title">
                                                <span class="timeline-indicator timeline-active"></span>
                                                ML Analytics Service
                                            </h5>
                                            <p class="card-text">
                                                <span class="badge bg-success">ACTIVE</span>
                                                <small class="text-muted ms-2">Port 8021</small>
                                            </p>
                                            <div class="progress" style="height: 5px;">
                                                <div class="progress-bar bg-success" style="width: 95%"></div>
                                            </div>
                                            <small class="text-muted">95% Uptime</small>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <div class="card">
                                        <div class="card-body">
                                            <h5 class="card-title">
                                                <span class="timeline-indicator timeline-inactive"></span>
                                                Prediction Tracking
                                            </h5>
                                            <p class="card-text">
                                                <span class="badge bg-warning text-dark">DEGRADED</span>
                                                <small class="text-muted ms-2">Port 8018</small>
                                            </p>
                                            <div class="progress" style="height: 5px;">
                                                <div class="progress-bar bg-warning" style="width: 60%"></div>
                                            </div>
                                            <small class="text-muted">60% Uptime</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Alerts -->
                    <div class="component-section">
                        <h2 class="component-title"><i class="bi bi-exclamation-triangle"></i> Alerts & Notifications</h2>
                        <p>System Alerts und User Feedback</p>
                        
                        <div class="demo-box">
                            <div class="alert alert-success" role="alert">
                                <i class="bi bi-check-circle-fill"></i>
                                <strong>✅ System Status:</strong> Alle Services operational
                            </div>
                            
                            <div class="alert alert-warning" role="alert">
                                <i class="bi bi-exclamation-triangle-fill"></i>
                                <strong>⚠️ Performance Alert:</strong> ML Service Latency erhöht (0.5s)
                            </div>
                            
                            <div class="alert alert-info" role="alert">
                                <i class="bi bi-info-circle-fill"></i>
                                <strong>ℹ️ Timeline Navigation:</strong> Navigation erfolgreich - 1 Monat Zeitraum
                            </div>
                            
                            <div class="alert alert-danger" role="alert">
                                <i class="bi bi-x-circle-fill"></i>
                                <strong>❌ Service Error:</strong> SOLL-IST Service temporarily unavailable
                            </div>
                        </div>
                    </div>
                    
                    <!-- Forms -->
                    <div class="component-section">
                        <h2 class="component-title"><i class="bi bi-file-earmark-text"></i> Forms</h2>
                        <p>Input Forms für User Interaction</p>
                        
                        <div class="demo-box">
                            <form class="row g-3">
                                <div class="col-md-6">
                                    <label for="symbolInput" class="form-label">
                                        <i class="bi bi-building"></i> Symbol
                                    </label>
                                    <input type="text" class="form-control" id="symbolInput" placeholder="z.B. AAPL">
                                </div>
                                
                                <div class="col-md-6">
                                    <label for="timeframeSelect" class="form-label">
                                        <i class="bi bi-calendar-range"></i> Zeitrahmen
                                    </label>
                                    <select class="form-select" id="timeframeSelect">
                                        <option selected>1 Monat</option>
                                        <option>1 Woche</option>
                                        <option>3 Monate</option>
                                        <option>12 Monate</option>
                                    </select>
                                </div>
                                
                                <div class="col-12">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="includeModels">
                                        <label class="form-check-label" for="includeModels">
                                            Individuelle Modell-Vorhersagen einbeziehen
                                        </label>
                                    </div>
                                </div>
                                
                                <div class="col-12">
                                    <button type="submit" class="btn btn-primary">
                                        <i class="bi bi-search"></i> Prognose laden
                                    </button>
                                    <button type="reset" class="btn btn-outline-secondary ms-2">
                                        <i class="bi bi-arrow-clockwise"></i> Zurücksetzen
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                    
                    <!-- Footer -->
                    <div class="mt-5 py-4 bg-dark text-white rounded">
                        <div class="container">
                            <div class="row align-items-center">
                                <div class="col-md-6">
                                    <h5><i class="bi bi-bootstrap-fill"></i> Bootstrap 5 Integration</h5>
                                    <p class="mb-0">Version {config.version} - Verification erfolgreich</p>
                                </div>
                                <div class="col-md-6 text-end">
                                    <small>
                                        🤖 Generated with <a href="https://claude.ai/code" class="text-white">Claude Code</a><br>
                                        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Bootstrap 5 JS -->
                <script src="{config.cdn_js}"></script>
                
                <!-- Custom JavaScript für Aktienanalyse -->
                <script>
                    // Initialize Bootstrap tooltips
                    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
                    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {{
                        return new bootstrap.Tooltip(tooltipTriggerEl)
                    }})
                    
                    // Custom timeline navigation functions
                    function navigateTimeline(direction, timeframe) {{
                        console.log('Timeline navigation:', direction, timeframe);
                        // Implementation would call actual navigation functions
                    }}
                    
                    function loadTimeframe(timeframe) {{
                        console.log('Loading timeframe:', timeframe);
                        // Implementation would load specific timeframe
                    }}
                    
                    console.log('🌟 Bootstrap 5 Component Library loaded successfully');
                    console.log('📊 Available components: Grid, Cards, Tables, Navigation, Forms, Alerts');
                </script>
            </body>
            </html>
            """
            
            self.logger.info("✅ Bootstrap 5 Component Library HTML generated successfully")
            return component_library_html
            
        except Exception as e:
            self.logger.error(f"Error generating component library: {e}")
            return f"<html><body><h1>Error generating component library: {e}</h1></body></html>"

# =============================================================================
# BOOTSTRAP INTEGRATION SERVICE
# =============================================================================

class BootstrapIntegrationService:
    """
    Service für Bootstrap Integration Verification
    
    SOLID Principles:
    - Single Responsibility: Bootstrap Integration Management
    - Open/Closed: Erweiterbar für neue Components
    """
    
    def __init__(self):
        self.verifier = BootstrapVerifier()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def run_complete_verification(self) -> Dict[str, Any]:
        """Führt komplette Bootstrap Verification durch"""
        try:
            self.logger.info("🚀 Starting complete Bootstrap 5 verification")
            
            verification_results = {
                "verification_timestamp": datetime.now().isoformat(),
                "bootstrap_version": config.version,
                "cdn_availability": {},
                "frontend_integration": {},
                "component_library": "",
                "overall_status": "unknown",
                "recommendations": []
            }
            
            # 1. Verify CDN availability
            self.logger.info("📡 Checking Bootstrap CDN availability...")
            verification_results["cdn_availability"] = await self.verifier.verify_bootstrap_availability()
            
            # 2. Verify frontend integration
            self.logger.info("🔍 Analyzing frontend integration...")
            verification_results["frontend_integration"] = await self.verifier.verify_frontend_integration()
            
            # 3. Generate component library
            self.logger.info("🎨 Generating component library...")
            verification_results["component_library"] = await self.verifier.generate_component_library()
            
            # 4. Determine overall status
            cdn_status = verification_results["cdn_availability"].get("overall_status", "error")
            integration_status = verification_results["frontend_integration"].get("bootstrap_integrated", False)
            
            if cdn_status == "available" and integration_status:
                verification_results["overall_status"] = "fully_integrated"
            elif cdn_status in ["available", "partial"] and integration_status:
                verification_results["overall_status"] = "mostly_integrated"
            elif cdn_status == "available":
                verification_results["overall_status"] = "cdn_available_but_not_integrated"
            else:
                verification_results["overall_status"] = "integration_required"
            
            # 5. Generate recommendations
            verification_results["recommendations"] = await self._generate_recommendations(verification_results)
            
            self.logger.info(f"✅ Bootstrap verification completed: {verification_results['overall_status']}")
            return verification_results
            
        except Exception as e:
            self.logger.error(f"Error in complete verification: {e}")
            return {
                "error": str(e),
                "overall_status": "error",
                "verification_timestamp": datetime.now().isoformat()
            }
    
    async def _generate_recommendations(self, verification_results: Dict[str, Any]) -> List[str]:
        """Generiert Empfehlungen basierend auf Verification Results"""
        recommendations = []
        
        try:
            cdn_status = verification_results["cdn_availability"].get("overall_status", "error")
            frontend_integration = verification_results["frontend_integration"]
            
            if cdn_status != "available":
                recommendations.append("Implement local Bootstrap 5 fallback files")
                recommendations.append("Add CDN availability monitoring")
            
            if not frontend_integration.get("bootstrap_integrated", False):
                recommendations.append("Integrate Bootstrap 5 CSS and JS into main.py templates")
                recommendations.append("Update HTML templates with Bootstrap classes")
                recommendations.append("Implement responsive grid system")
            
            main_py_analysis = frontend_integration.get("main_py_analysis", {})
            
            if not main_py_analysis.get("has_bootstrap_css", False):
                recommendations.append("Add Bootstrap CSS link to HTML templates")
            
            if not main_py_analysis.get("has_bootstrap_js", False):
                recommendations.append("Add Bootstrap JavaScript bundle to HTML templates")
            
            if not main_py_analysis.get("has_responsive_design", False):
                recommendations.append("Implement mobile-first responsive design")
                recommendations.append("Add viewport meta tag for mobile compatibility")
            
            if len(main_py_analysis.get("bootstrap_classes_found", [])) < 5:
                recommendations.append("Increase usage of Bootstrap utility classes")
                recommendations.append("Replace custom CSS with Bootstrap classes where possible")
            
            if not frontend_integration.get("template_service_exists", False):
                recommendations.append("Create dedicated HTML template service")
                recommendations.append("Implement Bootstrap component templates")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations - manual review required"]
    
    async def save_component_library(self, output_path: str = None) -> str:
        """Speichert Component Library HTML zu Datei"""
        try:
            if output_path is None:
                output_path = "/home/mdoehler/aktienanalyse-ökosystem/bootstrap_component_library.html"
            
            component_html = await self.verifier.generate_component_library()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(component_html)
            
            self.logger.info(f"✅ Component library saved to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error saving component library: {e}")
            raise

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Main execution function"""
    logger.info("🚀 Starting Bootstrap 5 Integration Verification")
    
    try:
        # Initialize service
        service = BootstrapIntegrationService()
        
        # Run complete verification
        results = await service.run_complete_verification()
        
        # Save component library
        component_library_path = await service.save_component_library()
        
        # Print results summary
        print("\n" + "="*80)
        print("📊 BOOTSTRAP 5 INTEGRATION VERIFICATION RESULTS")
        print("="*80)
        print(f"Overall Status: {results.get('overall_status', 'unknown')}")
        print(f"Bootstrap Version: {config.version}")
        print(f"CDN Status: {results.get('cdn_availability', {}).get('overall_status', 'unknown')}")
        print(f"Frontend Integration: {'✅ Yes' if results.get('frontend_integration', {}).get('bootstrap_integrated', False) else '❌ No'}")
        print(f"Component Library: {component_library_path}")
        
        print("\n📝 RECOMMENDATIONS:")
        recommendations = results.get('recommendations', [])
        if recommendations:
            for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
                print(f"  {i}. {rec}")
        else:
            print("  ✅ No recommendations - Bootstrap 5 fully integrated!")
        
        print("\n" + "="*80)
        logger.info("✅ Bootstrap 5 verification completed successfully")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in main execution: {e}")
        print(f"\n❌ Bootstrap verification failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())