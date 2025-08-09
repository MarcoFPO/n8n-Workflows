#!/usr/bin/env python3
"""
GUI-Testing-Modul für WEB-GUI Darstellungsanalyse
Automatisierte Frontend-Validierung und Qualitätskontrolle
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

# Shared Libraries Import
from shared import (
    datetime, Dict, Any, Optional, List,
    BaseModel, Field, HTTPException,
    setup_logging, get_current_timestamp
)

import aiohttp
import asyncio
from typing import Union
import json
import re
from urllib.parse import urljoin
import time
from pathlib import Path


class GUITestResult(BaseModel):
    """GUI-Test-Ergebnis Model"""
    test_name: str
    status: str  # success, failed, warning
    duration_ms: float
    details: Dict[str, Any]
    timestamp: datetime = Field(default_factory=get_current_timestamp)
    error_message: Optional[str] = None


class GUITestSuite(BaseModel):
    """GUI-Test-Suite Model"""
    suite_name: str
    tests: List[GUITestResult]
    total_tests: int
    passed_tests: int
    failed_tests: int
    warning_tests: int
    total_duration_ms: float
    success_rate: float
    timestamp: datetime = Field(default_factory=get_current_timestamp)


class WebGUIQualityChecker:
    """
    Web-GUI Qualitätschecker
    Führt automatisierte Tests der Frontend-Darstellung durch
    """
    
    def __init__(self, base_url: str = "http://localhost:8005"):
        self.base_url = base_url.rstrip('/')
        self.logger = setup_logging("gui-quality-checker")
        self.session = None
        
        # Test-Konfiguration
        self.timeout = 10  # Sekunden
        self.expected_elements = {
            "dashboard": ["portfolio_value", "daily_change", "active_orders"],
            "market_data": ["price_chart", "watchlist", "symbol_search"],
            "trading": ["order_form", "order_history", "active_orders"]
        }
        
        # Performance-Thresholds
        self.performance_thresholds = {
            "page_load_ms": 2000,  # Max 2 Sekunden
            "api_response_ms": 1000,  # Max 1 Sekunde
            "content_size_kb": 500  # Max 500 KB
        }
    
    async def __aenter__(self):
        """Async Context Manager - Einstieg"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async Context Manager - Ausgang"""
        if self.session:
            await self.session.close()
    
    async def run_comprehensive_gui_test(self) -> GUITestSuite:
        """
        Umfassender GUI-Test der Frontend-Anwendung
        """
        self.logger.info("Starting comprehensive GUI quality check")
        start_time = time.time()
        
        test_results = []
        
        # 1. Frontend-Erreichbarkeits-Test
        test_results.append(await self._test_frontend_availability())
        
        # 2. API-Endpoints-Test
        test_results.append(await self._test_api_endpoints())
        
        # 3. HTML-Struktur-Validierung
        test_results.append(await self._test_html_structure())
        
        # 4. Performance-Tests
        test_results.append(await self._test_performance())
        
        # 5. GUI-Elemente-Verfügbarkeit
        test_results.append(await self._test_gui_elements())
        
        # 6. Response-Zeit-Tests
        test_results.append(await self._test_response_times())
        
        # 7. Content-Validierung
        test_results.append(await self._test_content_validation())
        
        # 8. Error-Handling-Test
        test_results.append(await self._test_error_handling())
        
        # Test-Suite zusammenfassen
        total_duration = (time.time() - start_time) * 1000
        
        passed = len([t for t in test_results if t.status == "success"])
        failed = len([t for t in test_results if t.status == "failed"])
        warnings = len([t for t in test_results if t.status == "warning"])
        
        suite = GUITestSuite(
            suite_name="Comprehensive GUI Quality Test",
            tests=test_results,
            total_tests=len(test_results),
            passed_tests=passed,
            failed_tests=failed,
            warning_tests=warnings,
            total_duration_ms=total_duration,
            success_rate=(passed / len(test_results)) * 100
        )
        
        self.logger.info(f"GUI quality check completed: {passed}/{len(test_results)} passed, {suite.success_rate:.1f}% success rate")
        
        return suite
    
    async def _test_frontend_availability(self) -> GUITestResult:
        """Test 1: Frontend-Erreichbarkeit"""
        start_time = time.time()
        
        try:
            async with self.session.get(self.base_url) as response:
                duration = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    content = await response.text()
                    return GUITestResult(
                        test_name="frontend_availability",
                        status="success",
                        duration_ms=duration,
                        details={
                            "status_code": response.status,
                            "content_length": len(content),
                            "content_type": response.headers.get('content-type', 'unknown')
                        }
                    )
                else:
                    return GUITestResult(
                        test_name="frontend_availability",
                        status="failed",
                        duration_ms=duration,
                        details={"status_code": response.status},
                        error_message=f"HTTP {response.status}"
                    )
                    
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return GUITestResult(
                test_name="frontend_availability",
                status="failed",
                duration_ms=duration,
                details={},
                error_message=str(e)
            )
    
    async def _test_api_endpoints(self) -> GUITestResult:
        """Test 2: API-Endpoints-Funktionalität"""
        start_time = time.time()
        
        endpoints_to_test = [
            "/health",
            "/api/v2/dashboard", 
            "/api/v2/market/AAPL",
            "/api/v2/orders",
            "/api/v2/gui/elements",
            "/api/v2/gui/status"
        ]
        
        results = {}
        errors = []
        
        for endpoint in endpoints_to_test:
            try:
                url = urljoin(self.base_url, endpoint)
                async with self.session.get(url) as response:
                    results[endpoint] = {
                        "status_code": response.status,
                        "success": response.status == 200
                    }
                    
                    if response.status != 200:
                        errors.append(f"{endpoint}: HTTP {response.status}")
                        
            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}
                errors.append(f"{endpoint}: {e}")
        
        duration = (time.time() - start_time) * 1000
        successful_endpoints = len([r for r in results.values() if r.get("success", False)])
        
        status = "success" if len(errors) == 0 else ("warning" if successful_endpoints > 0 else "failed")
        
        return GUITestResult(
            test_name="api_endpoints",
            status=status,
            duration_ms=duration,
            details={
                "tested_endpoints": len(endpoints_to_test),
                "successful_endpoints": successful_endpoints,
                "results": results
            },
            error_message="; ".join(errors) if errors else None
        )
    
    async def _test_html_structure(self) -> GUITestResult:
        """Test 3: HTML-Struktur-Validierung"""
        start_time = time.time()
        
        try:
            async with self.session.get(self.base_url) as response:
                content = await response.text()
                
                # HTML-Grundstruktur prüfen
                checks = {
                    "has_doctype": content.strip().startswith("<!DOCTYPE"),
                    "has_html_tag": "<html" in content,
                    "has_head_section": "<head>" in content,
                    "has_body_section": "<body>" in content,
                    "has_title": "<title>" in content,
                    "has_meta_charset": 'charset="UTF-8"' in content or "charset=UTF-8" in content,
                    "has_viewport": "viewport" in content
                }
                
                # CSS und JavaScript prüfen
                checks["has_styles"] = "<style>" in content or 'rel="stylesheet"' in content
                checks["has_scripts"] = "<script>" in content
                
                passed_checks = sum(checks.values())
                duration = (time.time() - start_time) * 1000
                
                status = "success" if passed_checks >= 6 else ("warning" if passed_checks >= 4 else "failed")
                
                return GUITestResult(
                    test_name="html_structure",
                    status=status,
                    duration_ms=duration,
                    details={
                        "checks": checks,
                        "passed_checks": passed_checks,
                        "total_checks": len(checks),
                        "html_size": len(content)
                    }
                )
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return GUITestResult(
                test_name="html_structure",
                status="failed",
                duration_ms=duration,
                details={},
                error_message=str(e)
            )
    
    async def _test_performance(self) -> GUITestResult:
        """Test 4: Performance-Tests"""
        start_time = time.time()
        
        performance_results = {}
        warnings = []
        
        try:
            # Homepage-Performance
            page_start = time.time()
            async with self.session.get(self.base_url) as response:
                page_load_time = (time.time() - page_start) * 1000
                content_size = len(await response.text()) / 1024  # KB
                
                performance_results["page_load_ms"] = page_load_time
                performance_results["content_size_kb"] = content_size
                
                if page_load_time > self.performance_thresholds["page_load_ms"]:
                    warnings.append(f"Page load time too high: {page_load_time:.0f}ms")
                
                if content_size > self.performance_thresholds["content_size_kb"]:
                    warnings.append(f"Content size too large: {content_size:.1f}KB")
            
            # API-Performance
            api_start = time.time()
            async with self.session.get(f"{self.base_url}/api/v2/dashboard") as response:
                api_response_time = (time.time() - api_start) * 1000
                performance_results["api_response_ms"] = api_response_time
                
                if api_response_time > self.performance_thresholds["api_response_ms"]:
                    warnings.append(f"API response time too high: {api_response_time:.0f}ms")
            
            duration = (time.time() - start_time) * 1000
            status = "success" if len(warnings) == 0 else "warning"
            
            return GUITestResult(
                test_name="performance",
                status=status,
                duration_ms=duration,
                details={
                    "metrics": performance_results,
                    "thresholds": self.performance_thresholds
                },
                error_message="; ".join(warnings) if warnings else None
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return GUITestResult(
                test_name="performance",
                status="failed",
                duration_ms=duration,
                details={"metrics": performance_results},
                error_message=str(e)
            )
    
    async def _test_gui_elements(self) -> GUITestResult:
        """Test 5: GUI-Elemente-Verfügbarkeit"""
        start_time = time.time()
        
        try:
            # GUI-Elemente über API abrufen
            async with self.session.get(f"{self.base_url}/api/v2/gui/elements") as response:
                if response.status == 200:
                    gui_data = await response.json()
                    
                    found_elements = gui_data.get("elements", {})
                    found_pages = gui_data.get("pages", [])
                    found_endpoints = gui_data.get("api_endpoints", [])
                    
                    # Elemente-Verfügbarkeit prüfen
                    element_check = {}
                    for module, expected_elements in self.expected_elements.items():
                        module_elements = found_elements.get(module, [])
                        element_check[module] = {
                            "expected": expected_elements,
                            "found": module_elements,
                            "missing": [e for e in expected_elements if e not in module_elements]
                        }
                    
                    duration = (time.time() - start_time) * 1000
                    
                    # Status bestimmen
                    missing_elements = sum(len(check["missing"]) for check in element_check.values())
                    status = "success" if missing_elements == 0 else ("warning" if missing_elements < 3 else "failed")
                    
                    return GUITestResult(
                        test_name="gui_elements",
                        status=status,
                        duration_ms=duration,
                        details={
                            "element_check": element_check,
                            "pages": found_pages,
                            "api_endpoints": found_endpoints,
                            "missing_elements_count": missing_elements
                        }
                    )
                
                else:
                    duration = (time.time() - start_time) * 1000
                    return GUITestResult(
                        test_name="gui_elements",
                        status="failed",
                        duration_ms=duration,
                        details={},
                        error_message=f"GUI elements API returned HTTP {response.status}"
                    )
                    
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return GUITestResult(
                test_name="gui_elements",
                status="failed",
                duration_ms=duration,
                details={},
                error_message=str(e)
            )
    
    async def _test_response_times(self) -> GUITestResult:
        """Test 6: Response-Zeit-Tests für verschiedene Endpoints"""
        start_time = time.time()
        
        endpoints = ["/", "/health", "/api/v2/dashboard", "/api/v2/gui/status"]
        response_times = {}
        slow_endpoints = []
        
        try:
            for endpoint in endpoints:
                endpoint_start = time.time()
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    response_time = (time.time() - endpoint_start) * 1000
                    response_times[endpoint] = {
                        "response_time_ms": response_time,
                        "status_code": response.status
                    }
                    
                    if response_time > 1000:  # > 1 Sekunde
                        slow_endpoints.append(f"{endpoint}: {response_time:.0f}ms")
            
            duration = (time.time() - start_time) * 1000
            avg_response_time = sum(rt["response_time_ms"] for rt in response_times.values()) / len(response_times)
            
            status = "success" if len(slow_endpoints) == 0 else ("warning" if len(slow_endpoints) < 2 else "failed")
            
            return GUITestResult(
                test_name="response_times",
                status=status,
                duration_ms=duration,
                details={
                    "response_times": response_times,
                    "average_response_time_ms": avg_response_time,
                    "slow_endpoints": slow_endpoints
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return GUITestResult(
                test_name="response_times",
                status="failed",
                duration_ms=duration,
                details={"response_times": response_times},
                error_message=str(e)
            )
    
    async def _test_content_validation(self) -> GUITestResult:
        """Test 7: Content-Validierung"""
        start_time = time.time()
        
        try:
            # Hauptseite Content prüfen
            async with self.session.get(self.base_url) as response:
                content = await response.text()
                
                # Erwartete Inhalte prüfen
                content_checks = {
                    "has_title": "Aktienanalyse" in content,
                    "has_dashboard_mention": "Dashboard" in content,
                    "has_version_info": "v2" in content,
                    "has_api_links": "/api/" in content,
                    "has_health_link": "/health" in content,
                    "has_navigation": any(word in content.lower() for word in ["menu", "nav", "link"]),
                    "has_status_info": "status" in content.lower()
                }
                
                # JSON-APIs Content prüfen
                api_checks = {}
                api_endpoints = ["/api/v2/dashboard", "/api/v2/gui/status"]
                
                for endpoint in api_endpoints:
                    try:
                        async with self.session.get(f"{self.base_url}{endpoint}") as api_response:
                            if api_response.status == 200:
                                api_data = await api_response.json()
                                api_checks[endpoint] = {
                                    "is_json": True,
                                    "has_timestamp": "timestamp" in str(api_data),
                                    "has_data": len(api_data) > 0
                                }
                            else:
                                api_checks[endpoint] = {"is_json": False, "status": api_response.status}
                    except:
                        api_checks[endpoint] = {"error": True}
                
                duration = (time.time() - start_time) * 1000
                passed_content_checks = sum(content_checks.values())
                
                status = "success" if passed_content_checks >= 5 else ("warning" if passed_content_checks >= 3 else "failed")
                
                return GUITestResult(
                    test_name="content_validation",
                    status=status,
                    duration_ms=duration,
                    details={
                        "content_checks": content_checks,
                        "api_checks": api_checks,
                        "passed_content_checks": passed_content_checks
                    }
                )
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return GUITestResult(
                test_name="content_validation",
                status="failed",
                duration_ms=duration,
                details={},
                error_message=str(e)
            )
    
    async def _test_error_handling(self) -> GUITestResult:
        """Test 8: Error-Handling-Test"""
        start_time = time.time()
        
        error_endpoints = [
            "/nonexistent-page",
            "/api/v2/nonexistent",
            "/api/v2/market/INVALID_SYMBOL"
        ]
        
        error_handling_results = {}
        proper_errors = 0
        
        try:
            for endpoint in error_endpoints:
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    error_handling_results[endpoint] = {
                        "status_code": response.status,
                        "proper_error": response.status in [404, 400, 422, 500]
                    }
                    
                    if error_handling_results[endpoint]["proper_error"]:
                        proper_errors += 1
            
            duration = (time.time() - start_time) * 1000
            
            # Error-Handling als gut bewerten wenn mindestens 2/3 korrekte Fehler-Status-Codes
            status = "success" if proper_errors >= len(error_endpoints) * 0.66 else "warning"
            
            return GUITestResult(
                test_name="error_handling",
                status=status,
                duration_ms=duration,
                details={
                    "tested_error_endpoints": error_endpoints,
                    "error_handling_results": error_handling_results,
                    "proper_errors": proper_errors,
                    "total_tested": len(error_endpoints)
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return GUITestResult(
                test_name="error_handling",
                status="failed",
                duration_ms=duration,
                details={"error_handling_results": error_handling_results},
                error_message=str(e)
            )


class GUITestingModule:
    """
    GUI-Testing-Modul für Diagnostic Service
    Integriert Web-GUI-Qualitätschecks in das System
    """
    
    def __init__(self, module_id: str = "gui_testing", config: Dict[str, Any] = None):
        self.module_id = module_id
        self.config = config or {}
        self.logger = setup_logging("gui-testing-module")
        
        # GUI-Checker initialisieren
        self.frontend_url = self.config.get("frontend_url", "http://localhost:8005")
        self.quality_checker = WebGUIQualityChecker(self.frontend_url)
        
        # Test-Historie
        self.test_history: List[GUITestSuite] = []
        self.last_test_result: Optional[GUITestSuite] = None
        
        self.logger.info(f"GUI Testing Module initialized for {self.frontend_url}")
    
    async def run_gui_quality_check(self) -> GUITestSuite:
        """
        GUI-Qualitätscheck durchführen
        """
        self.logger.info("Starting GUI quality check")
        
        async with self.quality_checker:
            result = await self.quality_checker.run_comprehensive_gui_test()
        
        # Ergebnis speichern
        self.last_test_result = result
        self.test_history.append(result)
        
        # Historie begrenzen (letzte 10 Tests)
        if len(self.test_history) > 10:
            self.test_history = self.test_history[-10:]
        
        self.logger.info(f"GUI quality check completed: {result.success_rate:.1f}% success rate")
        
        return result
    
    async def get_test_summary(self) -> Dict[str, Any]:
        """
        Test-Zusammenfassung abrufen
        """
        if not self.last_test_result:
            return {"status": "no_tests_run", "message": "No GUI tests have been run yet"}
        
        return {
            "last_test": {
                "timestamp": self.last_test_result.timestamp.isoformat(),
                "success_rate": self.last_test_result.success_rate,
                "total_tests": self.last_test_result.total_tests,
                "passed": self.last_test_result.passed_tests,
                "failed": self.last_test_result.failed_tests,
                "warnings": self.last_test_result.warning_tests,
                "duration_ms": self.last_test_result.total_duration_ms
            },
            "test_history_count": len(self.test_history),
            "module_status": "active",
            "frontend_url": self.frontend_url
        }
    
    async def get_detailed_test_results(self) -> Optional[GUITestSuite]:
        """
        Detaillierte Test-Ergebnisse abrufen
        """
        return self.last_test_result
    
    async def get_health(self) -> Dict[str, Any]:
        """
        Modul-Health-Status
        """
        return {
            "module": self.module_id,
            "status": "active",
            "frontend_url": self.frontend_url,
            "tests_run": len(self.test_history),
            "last_test_success_rate": self.last_test_result.success_rate if self.last_test_result else None,
            "last_test_timestamp": self.last_test_result.timestamp.isoformat() if self.last_test_result else None
        }