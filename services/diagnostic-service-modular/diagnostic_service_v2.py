#!/usr/bin/env python3
"""
Modernisierter Diagnostic Service v2 mit GUI-Testing
Integriert Web-GUI Darstellungsanalyse und Qualitätskontrolle
"""

import sys
sys.path.append('/opt/aktienanalyse-ökosystem')

# Shared Libraries Import
from shared import (
    # Basis-Klassen
    ModularService, DatabaseMixin, EventBusMixin,
    # Standard-Imports
    datetime, Dict, Any, Optional, List,
    FastAPI, HTTPException, BackgroundTasks, BaseModel, Field,
    # Security & Logging
    SecurityConfig, setup_logging,
    # Utilities
    get_current_timestamp, safe_get_env
)

# GUI-Testing Modul
from modules.gui_testing_module import GUITestingModule, GUITestSuite, GUITestResult

# Environment laden
from dotenv import load_dotenv
load_dotenv('/opt/aktienanalyse-ökosystem/.env')


class DiagnosticTestRequest(BaseModel):
    """Diagnostic Test Request Model"""
    test_type: str  # gui_quality, system_health, event_bus_test
    target: Optional[str] = None
    parameters: Dict[str, Any] = {}


class DiagnosticService(ModularService, DatabaseMixin, EventBusMixin):
    """
    Modernisierter Diagnostic Service mit GUI-Testing
    Umfassende System- und GUI-Qualitätsanalyse
    """
    
    def __init__(self):
        # Service-Initialisierung über BaseService
        super().__init__(
            service_name="diagnostic",
            version="2.0.0",
            port=SecurityConfig.get_service_port("diagnostic")
        )
        
        # GUI-Testing-Modul initialisieren
        self.gui_testing_module = None
        
        # Diagnostic-spezifische Konfiguration
        self.system_services = {
            "frontend": "http://localhost:8005",
            "intelligent-core": "http://localhost:8011", 
            "broker-gateway": "http://localhost:8012",
            "event-bus": "http://localhost:8014",
            "monitoring": "http://localhost:8015"
        }
        
        # Test-Historie
        self.test_results: List[Dict[str, Any]] = []
    
    async def _setup_service(self):
        """Service-spezifische Initialisierung"""
        # Database Connections
        await self.setup_postgres()
        await self.setup_redis()
        
        # Event-Bus Connection
        await self.setup_event_bus("diagnostic")
        
        # GUI-Testing-Modul initialisieren
        await self._initialize_gui_testing()
        
        # API Routes registrieren
        self._setup_api_routes()
        
        # Background Tasks starten
        self._start_background_diagnostics()
        
        self.logger.info("Diagnostic Service v2 with GUI Testing fully initialized")
    
    async def _initialize_gui_testing(self):
        """GUI-Testing-Modul initialisieren"""
        try:
            gui_config = {
                "frontend_url": "http://localhost:8005",
                "timeout": 10,
                "performance_monitoring": True
            }
            
            self.gui_testing_module = GUITestingModule("gui_testing", gui_config)
            self.register_module("gui_testing", self.gui_testing_module)
            
            self.logger.info("GUI Testing Module initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize GUI Testing Module: {e}")
    
    def _setup_api_routes(self):
        """API Routes registrieren"""
        
        # GUI-Testing Routes
        @self.app.post("/api/v2/diagnostic/gui-quality-check")
        async def run_gui_quality_check(background_tasks: BackgroundTasks):
            """GUI-Qualitätscheck durchführen"""
            if not self.gui_testing_module:
                raise HTTPException(status_code=503, detail="GUI Testing Module not available")
            
            try:
                # GUI-Test im Background ausführen
                background_tasks.add_task(self._run_background_gui_test)
                
                return {
                    "status": "started",
                    "message": "GUI quality check started in background",
                    "check_status_url": "/api/v2/diagnostic/gui-test-status",
                    "timestamp": get_current_timestamp().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"GUI quality check start error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v2/diagnostic/gui-test-status")
        async def get_gui_test_status():
            """GUI-Test-Status abrufen"""
            if not self.gui_testing_module:
                raise HTTPException(status_code=503, detail="GUI Testing Module not available")
            
            try:
                summary = await self.gui_testing_module.get_test_summary()
                return summary
            except Exception as e:
                self.logger.error(f"GUI test status error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v2/diagnostic/gui-test-results")
        async def get_gui_test_results():
            """Detaillierte GUI-Test-Ergebnisse abrufen"""
            if not self.gui_testing_module:
                raise HTTPException(status_code=503, detail="GUI Testing Module not available")
            
            try:
                results = await self.gui_testing_module.get_detailed_test_results()
                if results:
                    return results.dict()
                else:
                    return {"status": "no_results", "message": "No GUI test results available"}
            except Exception as e:
                self.logger.error(f"GUI test results error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # System-Diagnostic Routes
        @self.app.post("/api/v2/diagnostic/system-health")
        async def run_system_health_check():
            """System-Health-Check durchführen"""
            try:
                health_results = await self._run_system_health_check()
                return health_results
            except Exception as e:
                self.logger.error(f"System health check error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v2/diagnostic/event-bus-test")
        async def run_event_bus_test():
            """Event-Bus-Test durchführen"""
            try:
                if not self.event_bus:
                    raise HTTPException(status_code=503, detail="Event Bus not connected")
                
                # Test-Event senden
                test_event = {
                    "test_id": f"diagnostic_test_{int(get_current_timestamp().timestamp())}",
                    "timestamp": get_current_timestamp().isoformat(),
                    "source": "diagnostic-v2"
                }
                
                await self.event_bus.publish_event(
                    event_type="diagnostic_test",
                    data=test_event,
                    source="diagnostic-v2"
                )
                
                return {
                    "status": "success",
                    "message": "Event bus test completed",
                    "test_event": test_event
                }
                
            except Exception as e:
                self.logger.error(f"Event bus test error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Comprehensive Diagnostic Route
        @self.app.post("/api/v2/diagnostic/comprehensive")
        async def run_comprehensive_diagnostic(background_tasks: BackgroundTasks):
            """Umfassende System-Diagnose durchführen"""
            try:
                # Comprehensive Test im Background starten
                background_tasks.add_task(self._run_comprehensive_diagnostic)
                
                return {
                    "status": "started",
                    "message": "Comprehensive diagnostic started",
                    "includes": ["gui_quality", "system_health", "event_bus_test", "performance_check"],
                    "check_status_url": "/api/v2/diagnostic/status",
                    "timestamp": get_current_timestamp().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Comprehensive diagnostic start error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v2/diagnostic/status")
        async def get_diagnostic_status():
            """Diagnostic-Service-Status abrufen"""
            return {
                "service": "diagnostic-v2",
                "status": "active",
                "modules": {
                    "gui_testing": self.gui_testing_module is not None,
                    "event_bus": self.event_bus is not None,
                    "database": self.db_pool is not None
                },
                "test_results_count": len(self.test_results),
                "system_services": self.system_services,
                "timestamp": get_current_timestamp().isoformat()
            }
        
        @self.app.get("/api/v2/diagnostic/history")
        async def get_test_history():
            """Test-Historie abrufen"""
            return {
                "test_history": self.test_results[-10:],  # Letzte 10 Tests
                "total_tests": len(self.test_results),
                "timestamp": get_current_timestamp().isoformat()
            }
    
    def _start_background_diagnostics(self):
        """Background Diagnostic Tasks starten"""
        import asyncio
        
        # Automatische GUI-Tests alle 30 Minuten
        asyncio.create_task(self._periodic_gui_testing())
        
        # System-Health-Checks alle 15 Minuten
        asyncio.create_task(self._periodic_system_health())
    
    async def _periodic_gui_testing(self):
        """Periodische GUI-Tests"""
        while True:
            try:
                await asyncio.sleep(1800)  # 30 Minuten
                if self.gui_testing_module:
                    await self._run_background_gui_test()
            except Exception as e:
                self.logger.error(f"Periodic GUI testing error: {e}")
                await asyncio.sleep(3600)  # 1 Stunde Pause bei Fehlern
    
    async def _periodic_system_health(self):
        """Periodische System-Health-Checks"""
        while True:
            try:
                await asyncio.sleep(900)  # 15 Minuten
                await self._run_system_health_check()
            except Exception as e:
                self.logger.error(f"Periodic system health error: {e}")
                await asyncio.sleep(1800)  # 30 Minuten Pause bei Fehlern
    
    async def _run_background_gui_test(self):
        """GUI-Test im Background ausführen"""
        if not self.gui_testing_module:
            return
        
        try:
            self.logger.info("Running background GUI quality check")
            result = await self.gui_testing_module.run_gui_quality_check()
            
            # Ergebnis in Historie speichern
            test_record = {
                "test_type": "gui_quality",
                "timestamp": result.timestamp.isoformat(),
                "success_rate": result.success_rate,
                "duration_ms": result.total_duration_ms,
                "passed": result.passed_tests,
                "failed": result.failed_tests,
                "warnings": result.warning_tests
            }
            
            self.test_results.append(test_record)
            
            # Event über Event-Bus publishen
            if self.event_bus:
                await self.event_bus.publish_event(
                    event_type="gui_test_completed",
                    data=test_record,
                    source="diagnostic-v2"
                )
            
            self.logger.info(f"Background GUI test completed: {result.success_rate:.1f}% success rate")
            
        except Exception as e:
            self.logger.error(f"Background GUI test error: {e}")
    
    async def _run_system_health_check(self) -> Dict[str, Any]:
        """System-Health-Check durchführen"""
        health_results = {
            "timestamp": get_current_timestamp().isoformat(),
            "services": {},
            "overall_health": "unknown"
        }
        
        healthy_services = 0
        total_services = len(self.system_services)
        
        # Jeden Service prüfen
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            for service_name, service_url in self.system_services.items():
                try:
                    async with session.get(f"{service_url}/health") as response:
                        if response.status == 200:
                            health_data = await response.json()
                            health_results["services"][service_name] = {
                                "status": "healthy",
                                "url": service_url,
                                "response_time_ms": 0,  # Wird in echten Tests gemessen
                                "details": health_data
                            }
                            healthy_services += 1
                        else:
                            health_results["services"][service_name] = {
                                "status": "unhealthy",
                                "url": service_url,
                                "error": f"HTTP {response.status}"
                            }
                except Exception as e:
                    health_results["services"][service_name] = {
                        "status": "unreachable",
                        "url": service_url,
                        "error": str(e)
                    }
        
        # Overall Health bestimmen
        health_percentage = (healthy_services / total_services) * 100
        if health_percentage >= 80:
            health_results["overall_health"] = "healthy"
        elif health_percentage >= 60:
            health_results["overall_health"] = "degraded"
        else:
            health_results["overall_health"] = "unhealthy"
        
        health_results["healthy_services"] = healthy_services
        health_results["total_services"] = total_services
        health_results["health_percentage"] = health_percentage
        
        # In Historie speichern
        test_record = {
            "test_type": "system_health",
            "timestamp": health_results["timestamp"],
            "health_percentage": health_percentage,
            "healthy_services": healthy_services,
            "total_services": total_services
        }
        
        self.test_results.append(test_record)
        
        return health_results
    
    async def _run_comprehensive_diagnostic(self):
        """Umfassende System-Diagnose durchführen"""
        try:
            self.logger.info("Running comprehensive diagnostic")
            
            comprehensive_results = {
                "timestamp": get_current_timestamp().isoformat(),
                "tests": {}
            }
            
            # 1. GUI-Quality-Check
            if self.gui_testing_module:
                gui_result = await self.gui_testing_module.run_gui_quality_check()
                comprehensive_results["tests"]["gui_quality"] = {
                    "success_rate": gui_result.success_rate,
                    "duration_ms": gui_result.total_duration_ms,
                    "status": "passed" if gui_result.success_rate >= 80 else "failed"
                }
            
            # 2. System-Health-Check
            health_result = await self._run_system_health_check()
            comprehensive_results["tests"]["system_health"] = {
                "health_percentage": health_result["health_percentage"],
                "healthy_services": health_result["healthy_services"],
                "status": health_result["overall_health"]
            }
            
            # 3. Event-Bus-Test
            if self.event_bus:
                try:
                    test_event = {"test": "comprehensive_diagnostic"}
                    await self.event_bus.publish_event("diagnostic_test", test_event, "diagnostic-v2")
                    comprehensive_results["tests"]["event_bus"] = {"status": "passed"}
                except Exception as e:
                    comprehensive_results["tests"]["event_bus"] = {"status": "failed", "error": str(e)}
            
            # Comprehensive-Test in Historie speichern
            test_record = {
                "test_type": "comprehensive",
                "timestamp": comprehensive_results["timestamp"],
                "results": comprehensive_results["tests"]
            }
            
            self.test_results.append(test_record)
            
            self.logger.info("Comprehensive diagnostic completed")
            
        except Exception as e:
            self.logger.error(f"Comprehensive diagnostic error: {e}")
    
    async def _get_health_details(self) -> Dict[str, Any]:
        """Erweiterte Health-Details für Diagnostic Service"""
        base_health = await super()._get_health_details()
        
        diagnostic_health = {
            "gui_testing": {
                "available": self.gui_testing_module is not None,
                "last_test": await self.gui_testing_module.get_test_summary() if self.gui_testing_module else None
            },
            "system_monitoring": {
                "services_monitored": len(self.system_services),
                "test_history_count": len(self.test_results)
            },
            "background_tasks": {
                "periodic_gui_testing": True,
                "periodic_system_health": True
            }
        }
        
        return {
            **base_health,
            "diagnostic": diagnostic_health,
            "api_version": "v2",
            "code_quality": "refactored_with_shared_libraries"
        }


# Service-Instanz erstellen
def create_app() -> FastAPI:
    """FastAPI App erstellen"""
    service = DiagnosticService()
    return service.app


async def start_service():
    """Service starten"""
    service = DiagnosticService()
    await service._setup_service()
    
    # Server starten
    service.run(
        host="0.0.0.0",
        debug=SecurityConfig.is_debug_mode()
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(start_service())