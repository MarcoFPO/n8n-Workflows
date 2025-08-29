#!/usr/bin/env python3
"""
PILOT SERVICE MIGRATION TEST - Event-Bus Service

Test der Migration vom Legacy Event-Bus Service zum BaseServiceOrchestrator
Issue #61 - Validierung der Pilot-Migration
"""

import asyncio
import pytest
import sys
import time
import requests
from typing import Dict, Any
from unittest.mock import Mock, patch

# Setup Path for Testing
sys.path.insert(0, '/home/mdoehler/aktienanalyse-ökosystem')

from shared.service_base import BaseServiceOrchestrator, ServiceConfig


class EventBusServiceTest:
    """Test Suite für Event-Bus Service Migration"""
    
    def __init__(self):
        self.service_url = "http://10.1.1.174:8014"  # Event-Bus Service URL
        self.test_results = {
            "service_startup": False,
            "health_endpoint": False,
            "api_routes": False,
            "cors_functionality": False,
            "event_publishing": False,
            "event_querying": False,
            "routing_rules": False,
            "statistics": False,
            "error_handling": False,
            "shutdown_graceful": False
        }
    
    def test_service_accessibility(self) -> Dict[str, Any]:
        """Test ob Service erreichbar ist"""
        try:
            response = requests.get(f"{self.service_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.test_results["service_startup"] = True
                return {
                    "status": "SUCCESS",
                    "service_info": data,
                    "accessible": True
                }
            else:
                return {
                    "status": "FAILED",
                    "error": f"HTTP {response.status_code}",
                    "accessible": False
                }
        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED", 
                "error": str(e),
                "accessible": False
            }
    
    def test_health_endpoint(self) -> Dict[str, Any]:
        """Test Health Endpoint Funktionalität"""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.test_results["health_endpoint"] = True
                
                # Validate health response structure
                required_fields = ["status", "service"]
                missing_fields = [field for field in required_fields if field not in data]
                
                return {
                    "status": "SUCCESS",
                    "health_data": data,
                    "valid_structure": len(missing_fields) == 0,
                    "missing_fields": missing_fields
                }
            else:
                return {
                    "status": "FAILED",
                    "error": f"HTTP {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_api_routes(self) -> Dict[str, Any]:
        """Test API Routes Verfügbarkeit"""
        routes_to_test = [
            ("/", "GET"),
            ("/health", "GET"), 
            ("/events/query", "GET"),
            ("/routing/rules", "GET"),
            ("/statistics", "GET")
        ]
        
        route_results = {}
        
        for route, method in routes_to_test:
            try:
                if method == "GET":
                    response = requests.get(f"{self.service_url}{route}", timeout=5)
                else:
                    response = requests.post(f"{self.service_url}{route}", timeout=5)
                
                route_results[route] = {
                    "accessible": response.status_code in [200, 201, 202, 204],
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
                
            except requests.exceptions.RequestException as e:
                route_results[route] = {
                    "accessible": False,
                    "error": str(e),
                    "response_time_ms": None
                }
        
        successful_routes = len([r for r in route_results.values() if r["accessible"]])
        self.test_results["api_routes"] = successful_routes == len(routes_to_test)
        
        return {
            "status": "SUCCESS" if self.test_results["api_routes"] else "PARTIAL",
            "route_results": route_results,
            "successful_routes": successful_routes,
            "total_routes": len(routes_to_test)
        }
    
    def test_cors_functionality(self) -> Dict[str, Any]:
        """Test CORS Headers"""
        try:
            # OPTIONS request to test CORS preflight
            response = requests.options(
                f"{self.service_url}/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type"
                },
                timeout=5
            )
            
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
                "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials")
            }
            
            self.test_results["cors_functionality"] = response.status_code == 200
            
            return {
                "status": "SUCCESS" if self.test_results["cors_functionality"] else "FAILED",
                "status_code": response.status_code,
                "cors_headers": cors_headers,
                "cors_enabled": any(cors_headers.values())
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_event_publishing(self) -> Dict[str, Any]:
        """Test Event Publishing Endpoint"""
        try:
            test_event = {
                "event_type": "test.event.created",
                "source": "test-suite",
                "data": {
                    "test_id": "test_001",
                    "message": "Test event from migration test suite"
                },
                "metadata": {
                    "test_timestamp": time.time()
                }
            }
            
            response = requests.post(
                f"{self.service_url}/events/publish",
                json=test_event,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                data = response.json()
                self.test_results["event_publishing"] = True
                return {
                    "status": "SUCCESS",
                    "response_data": data,
                    "event_accepted": True
                }
            else:
                return {
                    "status": "FAILED",
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_event_querying(self) -> Dict[str, Any]:
        """Test Event Querying"""
        try:
            # Query recent events
            response = requests.get(
                f"{self.service_url}/events/query",
                params={"limit": 10},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_results["event_querying"] = True
                return {
                    "status": "SUCCESS",
                    "query_response": data,
                    "events_returned": len(data.get("events", [])) if isinstance(data, dict) else 0
                }
            else:
                return {
                    "status": "FAILED", 
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_routing_rules(self) -> Dict[str, Any]:
        """Test Routing Rules Endpoint"""
        try:
            response = requests.get(f"{self.service_url}/routing/rules", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.test_results["routing_rules"] = True
                return {
                    "status": "SUCCESS",
                    "routing_rules": data,
                    "rules_count": len(data.get("routing_rules", {})) if isinstance(data, dict) else 0
                }
            else:
                return {
                    "status": "FAILED",
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_statistics_endpoint(self) -> Dict[str, Any]:
        """Test Statistics Endpoint"""
        try:
            response = requests.get(f"{self.service_url}/statistics", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.test_results["statistics"] = True
                return {
                    "status": "SUCCESS",
                    "statistics": data,
                    "has_metrics": len(data) > 0 if isinstance(data, dict) else False
                }
            else:
                return {
                    "status": "FAILED",
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test Error Handling"""
        try:
            # Test invalid event publishing
            invalid_event = {
                "invalid_field": "test"
                # Missing required fields intentionally
            }
            
            response = requests.post(
                f"{self.service_url}/events/publish",
                json=invalid_event,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            # Should return error (4xx status)
            if 400 <= response.status_code < 500:
                self.test_results["error_handling"] = True
                return {
                    "status": "SUCCESS",
                    "error_response": response.text,
                    "proper_error_handling": True,
                    "status_code": response.status_code
                }
            else:
                return {
                    "status": "FAILED",
                    "error": f"Expected 4xx error, got {response.status_code}",
                    "proper_error_handling": False
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }
    
    def run_comprehensive_migration_test(self) -> Dict[str, Any]:
        """Run all migration tests"""
        print("🧪 STARTING EVENT-BUS SERVICE MIGRATION TESTS")
        print("=" * 70)
        
        test_functions = [
            ("Service Accessibility", self.test_service_accessibility),
            ("Health Endpoint", self.test_health_endpoint),
            ("API Routes", self.test_api_routes),
            ("CORS Functionality", self.test_cors_functionality),
            ("Event Publishing", self.test_event_publishing),
            ("Event Querying", self.test_event_querying),
            ("Routing Rules", self.test_routing_rules),
            ("Statistics Endpoint", self.test_statistics_endpoint),
            ("Error Handling", self.test_error_handling)
        ]
        
        test_results = {}
        
        for test_name, test_func in test_functions:
            print(f"\n🔍 Testing: {test_name}")
            print("-" * 40)
            
            try:
                result = test_func()
                test_results[test_name] = result
                
                if result["status"] == "SUCCESS":
                    print(f"  ✅ {test_name}: PASSED")
                elif result["status"] == "PARTIAL":
                    print(f"  ⚠️  {test_name}: PARTIAL SUCCESS")
                else:
                    print(f"  ❌ {test_name}: FAILED")
                    if "error" in result:
                        print(f"     Error: {result['error']}")
                        
            except Exception as e:
                test_results[test_name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"  💥 {test_name}: ERROR - {str(e)}")
        
        # Calculate overall results
        successful_tests = len([r for r in test_results.values() if r["status"] == "SUCCESS"])
        partial_tests = len([r for r in test_results.values() if r["status"] == "PARTIAL"])
        failed_tests = len([r for r in test_results.values() if r["status"] in ["FAILED", "ERROR"]])
        total_tests = len(test_functions)
        
        success_rate = (successful_tests + partial_tests * 0.5) / total_tests * 100
        
        # Determine migration status
        if success_rate >= 90:
            migration_status = "MIGRATION_SUCCESS"
            recommendation = "READY_FOR_PRODUCTION"
        elif success_rate >= 75:
            migration_status = "MIGRATION_PARTIAL"
            recommendation = "NEEDS_MONITORING"
        else:
            migration_status = "MIGRATION_FAILED"
            recommendation = "REQUIRES_FIXES"
        
        final_result = {
            "migration_test_timestamp": time.time(),
            "service_url": self.service_url,
            "test_results": test_results,
            "summary": {
                "total_tests": total_tests,
                "successful": successful_tests,
                "partial": partial_tests,
                "failed": failed_tests,
                "success_rate": success_rate
            },
            "migration_status": migration_status,
            "recommendation": recommendation,
            "detailed_test_results": self.test_results
        }
        
        return final_result


def main():
    """Run Event-Bus Migration Tests"""
    test_suite = EventBusServiceTest()
    results = test_suite.run_comprehensive_migration_test()
    
    print("\n" + "=" * 70)
    print("📊 EVENT-BUS SERVICE MIGRATION TEST RESULTS")
    print("=" * 70)
    
    summary = results["summary"]
    print(f"Service URL: {results['service_url']}")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Successful: {summary['successful']}")
    print(f"Partial Success: {summary['partial']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    
    print(f"\n🎯 MIGRATION STATUS: {results['migration_status']}")
    print(f"📋 RECOMMENDATION: {results['recommendation']}")
    
    # Export results
    import json
    output_file = "/home/mdoehler/aktienanalyse-ökosystem/event_bus_migration_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results exported to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()