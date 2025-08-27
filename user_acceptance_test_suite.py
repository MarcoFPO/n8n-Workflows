#!/usr/bin/env python3
"""
User Acceptance Test Suite für Aktienanalyse-Ökosystem v6.0.0
Clean Architecture - Event-Driven Trading Intelligence System

Author: Claude Code Assistant
Date: 2025-08-27
Version: 1.0.0

TESTING SCOPE:
- Frontend GUI Testing (Port 8080/8081)
- API Performance Testing (alle 11 Services)
- Business Workflow Testing (KI-Prognosen + SOLL-IST Vergleich)
- Real-time Dashboard Testing
- Error Handling & Edge Cases
"""

import requests
import json
import time
import csv
import io
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import subprocess
import os

class UserAcceptanceTestSuite:
    """Comprehensive User Acceptance Testing für Aktienanalyse-Ökosystem"""
    
    def __init__(self):
        self.base_url = "http://10.1.1.174"
        self.frontend_ports = [8080, 8081]
        self.backend_port = 8017
        self.test_results = {
            "test_run_timestamp": datetime.now().isoformat(),
            "system_info": {
                "server": "10.1.1.174",
                "architecture": "Clean Architecture v6.0.0",
                "services_count": 11
            },
            "phase_results": {}
        }
        self.performance_threshold = 0.12  # 0.12s Response Time Requirement
        
    def log_test(self, phase: str, test_name: str, result: Dict[str, Any]):
        """Test-Ergebnis protokollieren"""
        if phase not in self.test_results["phase_results"]:
            self.test_results["phase_results"][phase] = {}
        self.test_results["phase_results"][phase][test_name] = result
        
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
        print(f"[{phase}] {test_name}: {status}")
        if not result.get("success", False) and result.get("error"):
            print(f"    Error: {result['error']}")
    
    def measure_response_time(self, url: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Response Time messen und validieren"""
        start_time = time.time()
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response_time,
                "meets_threshold": response_time < self.performance_threshold,
                "content_length": len(response.text),
                "response_preview": response.text[:200] if response.text else None
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    # =================== PHASE 1: FRONTEND ACCESSIBILITY & NAVIGATION ===================
    
    def test_frontend_accessibility(self) -> None:
        """Teste Frontend-Erreichbarkeit auf beiden Ports"""
        print("\n=== PHASE 1: FRONTEND ACCESSIBILITY & NAVIGATION ===")
        
        for port in self.frontend_ports:
            url = f"{self.base_url}:{port}"
            result = self.measure_response_time(url)
            
            # UI-spezifische Tests
            if result["success"]:
                # Bootstrap 5 Detection
                has_bootstrap = "bootstrap" in result.get("response_preview", "").lower()
                result["has_bootstrap"] = has_bootstrap
                
                # Navigation Links Detection
                has_navigation = any(keyword in result.get("response_preview", "").lower() 
                                   for keyword in ["nav", "menu", "timeline", "prognosen"])
                result["has_navigation"] = has_navigation
            
            self.log_test("PHASE_1_FRONTEND", f"frontend_port_{port}", result)
    
    def test_timeline_navigation(self) -> None:
        """Teste Timeline Navigation für alle Zeitrahmen"""
        timeframes = ["1W", "1M", "3M", "1Y"]
        
        for timeframe in timeframes:
            # Test Navigation URLs
            nav_url = f"{self.base_url}:8080/predictions?timeframe={timeframe}"
            result = self.measure_response_time(nav_url)
            
            if result["success"]:
                # Prüfe Timeline-Parameter
                result["timeframe_detected"] = timeframe in result.get("response_preview", "")
            
            self.log_test("PHASE_1_FRONTEND", f"timeline_navigation_{timeframe}", result)
    
    # =================== PHASE 2: DATEN-INTEGRATION & API-TESTING ===================
    
    def test_csv_to_json_integration(self) -> None:
        """Teste CSV-zu-JSON Integration mit 5-Spalten Format"""
        print("\n=== PHASE 2: DATEN-INTEGRATION & API-TESTING ===")
        
        # Test CSV-Daten (Datum, Symbol, Company, Gewinn%, Risiko)
        test_csv = """Datum,Symbol,Company,Gewinn%,Risiko
2025-08-27,AAPL,Apple Inc,8.5,85
2025-08-27,TSLA,Tesla Inc,12.3,75
2025-08-27,MSFT,Microsoft,6.8,90"""
        
        csv_url = f"{self.base_url}:{self.backend_port}/process-csv"
        
        try:
            response = requests.post(
                csv_url, 
                files={'csv_file': ('test.csv', io.StringIO(test_csv), 'text/csv')},
                timeout=10
            )
            
            result = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "meets_threshold": response.elapsed.total_seconds() < self.performance_threshold
            }
            
            if result["success"]:
                try:
                    json_response = response.json()
                    result["json_parsed"] = True
                    result["records_count"] = len(json_response.get("data", []))
                    result["has_risk_colors"] = any("risk_color" in str(record) for record in json_response.get("data", []))
                except:
                    result["json_parsed"] = False
            
        except requests.RequestException as e:
            result = {"success": False, "error": str(e)}
        
        self.log_test("PHASE_2_DATA", "csv_to_json_processing", result)
    
    def test_api_endpoints_performance(self) -> None:
        """Teste alle 11 Services und ihre API-Endpoints"""
        # Service Discovery - prüfe verfügbare Services
        services_to_test = [
            {"name": "data-processing", "port": 8017, "endpoint": "/health"},
            {"name": "ml-analytics", "port": 8021, "endpoint": "/health"},
            {"name": "event-bus", "port": 8014, "endpoint": "/health"},
            {"name": "yahoo-finance-api", "port": 8018, "endpoint": "/health"},
            {"name": "portfolio-performance", "port": 8019, "endpoint": "/health"},
            {"name": "notification-service", "port": 8020, "endpoint": "/health"},
            {"name": "dashboard-aggregator", "port": 8022, "endpoint": "/health"},
            {"name": "config-service", "port": 8023, "endpoint": "/health"},
            {"name": "system-monitor", "port": 8024, "endpoint": "/health"},
            {"name": "database-service", "port": 8025, "endpoint": "/health"},
            {"name": "auth-service", "port": 8026, "endpoint": "/health"}
        ]
        
        healthy_services = 0
        for service in services_to_test:
            url = f"{self.base_url}:{service['port']}{service['endpoint']}"
            result = self.measure_response_time(url)
            
            if result["success"]:
                healthy_services += 1
            
            self.log_test("PHASE_2_DATA", f"service_{service['name']}", result)
        
        # Summary Result
        self.log_test("PHASE_2_DATA", "services_overview", {
            "success": healthy_services >= 8,  # Mindestens 8 von 11 Services sollten laufen
            "healthy_services": healthy_services,
            "total_services": len(services_to_test),
            "health_percentage": (healthy_services / len(services_to_test)) * 100
        })
    
    # =================== PHASE 3: BUSINESS WORKFLOW TESTING ===================
    
    def test_ki_prognosen_workflow(self) -> None:
        """Teste KI-Prognosen Business Workflow"""
        print("\n=== PHASE 3: BUSINESS WORKFLOW TESTING ===")
        
        # Test Aktien-Symbol Eingabe
        test_symbol = "AAPL"
        prediction_url = f"{self.base_url}:{self.backend_port}/predictions/{test_symbol}"
        
        result = self.measure_response_time(prediction_url)
        
        if result["success"]:
            try:
                # Prüfe auf Prognose-spezifische Felder
                content = result.get("response_preview", "")
                result["has_confidence_score"] = "confidence" in content.lower()
                result["has_timeframe_data"] = any(tf in content for tf in ["1W", "1M", "3M", "1Y"])
                result["has_prediction_value"] = any(keyword in content.lower() 
                                                   for keyword in ["gewinn", "profit", "prediction"])
            except:
                pass
        
        self.log_test("PHASE_3_BUSINESS", "ki_prognosen_workflow", result)
    
    def test_soll_ist_vergleich_workflow(self) -> None:
        """Teste SOLL-IST Vergleich Business Workflow"""
        test_symbol = "AAPL"
        comparison_url = f"{self.base_url}:{self.backend_port}/comparison/{test_symbol}"
        
        result = self.measure_response_time(comparison_url)
        
        if result["success"]:
            content = result.get("response_preview", "")
            result["has_soll_data"] = "soll" in content.lower()
            result["has_ist_data"] = "ist" in content.lower()
            result["has_performance_diff"] = "performance" in content.lower() or "diff" in content.lower()
            result["has_color_coding"] = any(color in content.lower() for color in ["green", "red", "grün", "rot"])
        
        self.log_test("PHASE_3_BUSINESS", "soll_ist_vergleich_workflow", result)
    
    # =================== PHASE 4: REAL-TIME & EVENT-TESTING ===================
    
    def test_event_driven_architecture(self) -> None:
        """Teste Event-Driven Architecture"""
        print("\n=== PHASE 4: REAL-TIME & EVENT-TESTING ===")
        
        # Event Bus Communication Test
        event_bus_url = f"{self.base_url}:8014/events"
        result = self.measure_response_time(event_bus_url)
        
        self.log_test("PHASE_4_REALTIME", "event_bus_communication", result)
        
        # Test Event Publishing (falls möglich)
        test_event = {
            "event_type": "user_acceptance_test",
            "timestamp": datetime.now().isoformat(),
            "data": {"test": "event_publishing"}
        }
        
        publish_result = self.measure_response_time(
            f"{self.base_url}:8014/publish", 
            method="POST", 
            data=test_event
        )
        
        self.log_test("PHASE_4_REALTIME", "event_publishing", publish_result)
    
    def test_realtime_dashboard(self) -> None:
        """Teste Real-time Dashboard Updates"""
        # Dashboard Aggregator Service
        dashboard_url = f"{self.base_url}:8022/dashboard"
        result = self.measure_response_time(dashboard_url)
        
        if result["success"]:
            content = result.get("response_preview", "")
            result["has_realtime_data"] = "timestamp" in content.lower() or "time" in content.lower()
            result["has_portfolio_data"] = "portfolio" in content.lower()
            result["has_performance_metrics"] = "performance" in content.lower()
        
        self.log_test("PHASE_4_REALTIME", "realtime_dashboard", result)
    
    # =================== PHASE 5: PERFORMANCE & ERROR HANDLING ===================
    
    def test_performance_under_load(self) -> None:
        """Teste Performance unter Last"""
        print("\n=== PHASE 5: PERFORMANCE & ERROR HANDLING ===")
        
        # Concurrent Requests Test
        urls = [
            f"{self.base_url}:8080",
            f"{self.base_url}:{self.backend_port}/health",
            f"{self.base_url}:8021/health"
        ]
        
        response_times = []
        successful_requests = 0
        
        for i in range(10):  # 10 concurrent-ähnliche Requests
            for url in urls:
                result = self.measure_response_time(url)
                if result["success"]:
                    successful_requests += 1
                    response_times.append(result["response_time"])
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        performance_result = {
            "success": avg_response_time < self.performance_threshold,
            "average_response_time": avg_response_time,
            "successful_requests": successful_requests,
            "total_requests": 30,
            "success_rate": (successful_requests / 30) * 100,
            "meets_threshold": avg_response_time < self.performance_threshold
        }
        
        self.log_test("PHASE_5_PERFORMANCE", "performance_under_load", performance_result)
    
    def test_error_handling(self) -> None:
        """Teste Error Handling und Edge Cases"""
        error_tests = [
            {
                "name": "invalid_stock_symbol",
                "url": f"{self.base_url}:{self.backend_port}/predictions/INVALID123",
                "expected_status": [400, 404]
            },
            {
                "name": "malformed_csv",
                "url": f"{self.base_url}:{self.backend_port}/process-csv",
                "method": "POST",
                "data": "invalid,csv,data",
                "expected_status": [400]
            },
            {
                "name": "nonexistent_endpoint",
                "url": f"{self.base_url}:{self.backend_port}/nonexistent",
                "expected_status": [404]
            }
        ]
        
        for test in error_tests:
            try:
                if test.get("method") == "POST":
                    response = requests.post(test["url"], data=test.get("data"), timeout=5)
                else:
                    response = requests.get(test["url"], timeout=5)
                
                result = {
                    "success": response.status_code in test["expected_status"],
                    "status_code": response.status_code,
                    "expected_status": test["expected_status"],
                    "has_error_message": len(response.text) > 0
                }
                
            except requests.RequestException as e:
                result = {
                    "success": False,
                    "error": str(e)
                }
            
            self.log_test("PHASE_5_PERFORMANCE", test["name"], result)
    
    # =================== MAIN TEST EXECUTION ===================
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Führe alle User Acceptance Tests durch"""
        print("🚀 Starting User Acceptance Test Suite - Aktienanalyse-Ökosystem v6.0.0")
        print("="*80)
        
        # PHASE 1: Frontend Accessibility & Navigation
        self.test_frontend_accessibility()
        self.test_timeline_navigation()
        
        # PHASE 2: Data Integration & API Testing
        self.test_csv_to_json_integration()
        self.test_api_endpoints_performance()
        
        # PHASE 3: Business Workflow Testing
        self.test_ki_prognosen_workflow()
        self.test_soll_ist_vergleich_workflow()
        
        # PHASE 4: Real-time & Event Testing
        self.test_event_driven_architecture()
        self.test_realtime_dashboard()
        
        # PHASE 5: Performance & Error Handling
        self.test_performance_under_load()
        self.test_error_handling()
        
        print("\n" + "="*80)
        print("✅ User Acceptance Test Suite completed")
        
        return self.test_results
    
    def save_results(self) -> str:
        """Speichere Test-Ergebnisse als JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Test results saved to: {filename}")
        return filename

def main():
    """Hauptfunktion - User Acceptance Test Suite ausführen"""
    test_suite = UserAcceptanceTestSuite()
    
    try:
        results = test_suite.run_comprehensive_tests()
        results_file = test_suite.save_results()
        
        # Summary
        total_tests = sum(len(phase) for phase in results["phase_results"].values())
        passed_tests = sum(
            1 for phase in results["phase_results"].values()
            for test in phase.values()
            if test.get("success", False)
        )
        
        print(f"\n📈 TEST SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {total_tests - passed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        return 0 if passed_tests == total_tests else 1
        
    except Exception as e:
        print(f"❌ Test Suite Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())