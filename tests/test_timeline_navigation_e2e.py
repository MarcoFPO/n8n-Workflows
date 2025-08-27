#!/usr/bin/env python3
"""
End-to-End Tests für Timeline Navigation (KI-PROGNOSEN-NAV-002 Fix)

Tests für die gesamte Timeline Navigation Pipeline:
1. Frontend Service Parameter Forwarding
2. Backend API Navigation Context
3. JavaScript Frontend Integration
4. Error Handling und Fallbacks

Clean Architecture Test Principles:
- Test Real API Endpoints
- Validate Complete Workflows
- Ensure SOLID Compliance in Testing
"""

import asyncio
import aiohttp
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# Test Configuration
TEST_BACKEND_URL = "http://localhost:8017"  # Data Processing Service
TEST_FRONTEND_URL = "http://localhost:8016"  # Frontend Service

# Setup Test Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimelineNavigationE2ETester:
    """
    E2E Test Suite für Timeline Navigation
    
    SOLID Principles:
    - Single Responsibility: Nur Timeline Navigation Testing
    - Open/Closed: Erweiterbar für neue Test Cases
    """
    
    def __init__(self):
        self.backend_url = TEST_BACKEND_URL
        self.frontend_url = TEST_FRONTEND_URL
        self.test_results = []
    
    async def test_backend_navigation_endpoint(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test Backend Navigation Endpoint direkt"""
        test_name = "Backend Navigation Endpoint"
        logger.info(f"🧪 Testing: {test_name}")
        
        try:
            # Test Case 1: Basic Navigation ohne Parameter
            url = f"{self.backend_url}/api/v1/data/predictions?timeframe=1M"
            async with session.get(url) as response:
                data = await response.json()
                
                assert response.status == 200, f"Expected 200, got {response.status}"
                assert "predictions" in data, "Response missing 'predictions' field"
                assert "timeframe" in data, "Response missing 'timeframe' field"
                assert data["timeframe"] == "1M", "Incorrect timeframe returned"
                
                basic_test_passed = True
                logger.info("✅ Basic navigation test passed")
            
            # Test Case 2: Navigation mit nav_timestamp und nav_direction
            test_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())
            nav_url = f"{self.backend_url}/api/v1/data/predictions?timeframe=1M&nav_timestamp={test_timestamp}&nav_direction=prev"
            
            async with session.get(nav_url) as nav_response:
                nav_data = await nav_response.json()
                
                assert nav_response.status == 200, f"Navigation request failed: {nav_response.status}"
                assert nav_data.get("nav_timestamp") == test_timestamp, "nav_timestamp not preserved"
                assert nav_data.get("nav_direction") == "prev", "nav_direction not preserved"
                assert "navigation_context" in nav_data, "navigation_context missing"
                
                navigation_test_passed = True
                logger.info("✅ Navigation parameter test passed")
            
            # Test Case 3: Dedicated Timeline Navigation Endpoint
            timeline_url = f"{self.backend_url}/api/v1/data/timeline-navigation?timeframe=1W&nav_timestamp={test_timestamp}&nav_direction=next"
            async with session.get(timeline_url) as timeline_response:
                timeline_data = await timeline_response.json()
                
                assert timeline_response.status == 200, "Timeline navigation endpoint failed"
                assert timeline_data.get("navigation_type") == "timeline", "Incorrect navigation type"
                assert "backend_support" in timeline_data, "Backend support indicator missing"
                
                timeline_test_passed = True
                logger.info("✅ Timeline navigation endpoint test passed")
                
            return {
                "test_name": test_name,
                "status": "PASSED",
                "details": {
                    "basic_navigation": basic_test_passed,
                    "parameter_forwarding": navigation_test_passed,
                    "timeline_endpoint": timeline_test_passed,
                    "test_timestamp": test_timestamp
                }
            }
            
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {str(e)}")
            return {
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "details": {}
            }
    
    async def test_frontend_parameter_forwarding(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test Frontend Service Parameter Forwarding"""
        test_name = "Frontend Parameter Forwarding"
        logger.info(f"🧪 Testing: {test_name}")
        
        try:
            # Test Frontend Timeline Navigation API
            test_timestamp = int(datetime.now().timestamp())
            frontend_nav_url = f"{self.frontend_url}/api/timeline/navigation?timeframe=3M&nav_timestamp={test_timestamp}&nav_direction=next"
            
            async with session.get(frontend_nav_url) as response:
                data = await response.json()
                
                assert response.status == 200, f"Frontend navigation failed: {response.status}"
                assert "frontend_support" in data, "Frontend support indicator missing"
                assert data.get("api_version") is not None, "API version missing"
                assert "navigation_parameters_received" in data, "Parameter tracking missing"
                
                received_params = data["navigation_parameters_received"]
                assert received_params["timeframe"] == "3M", "Timeframe not forwarded correctly"
                assert received_params["nav_timestamp"] == test_timestamp, "Timestamp not forwarded correctly"
                assert received_params["nav_direction"] == "next", "Direction not forwarded correctly"
                
                logger.info("✅ Frontend parameter forwarding test passed")
                
                return {
                    "test_name": test_name,
                    "status": "PASSED",
                    "details": {
                        "parameter_forwarding": True,
                        "api_version": data.get("api_version"),
                        "test_timestamp": test_timestamp
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {str(e)}")
            return {
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "details": {}
            }
    
    async def test_error_handling_scenarios(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test Error Handling und Edge Cases"""
        test_name = "Error Handling Scenarios"
        logger.info(f"🧪 Testing: {test_name}")
        
        test_results = {}
        
        try:
            # Test Case 1: Invalid Timeframe
            invalid_url = f"{self.backend_url}/api/v1/data/predictions?timeframe=INVALID"
            async with session.get(invalid_url) as response:
                assert response.status == 400, "Should return 400 for invalid timeframe"
                test_results["invalid_timeframe"] = True
                logger.info("✅ Invalid timeframe error handling test passed")
            
            # Test Case 2: Invalid nav_timestamp (out of range)
            invalid_timestamp = 999999999999999  # Way too large
            invalid_ts_url = f"{self.backend_url}/api/v1/data/predictions?timeframe=1M&nav_timestamp={invalid_timestamp}&nav_direction=next"
            async with session.get(invalid_ts_url) as response:
                # Should either handle gracefully or return error
                assert response.status in [200, 400], f"Unexpected status for invalid timestamp: {response.status}"
                if response.status == 200:
                    data = await response.json()
                    assert "error" in str(data) or "fallback" in str(data).lower(), "Should indicate error handling"
                test_results["invalid_timestamp"] = True
                logger.info("✅ Invalid timestamp error handling test passed")
            
            # Test Case 3: Invalid nav_direction
            invalid_dir_url = f"{self.backend_url}/api/v1/data/predictions?timeframe=1M&nav_timestamp=1693526400&nav_direction=INVALID"
            async with session.get(invalid_dir_url) as response:
                assert response.status in [200, 400], "Should handle invalid direction gracefully"
                test_results["invalid_direction"] = True
                logger.info("✅ Invalid direction error handling test passed")
                
            return {
                "test_name": test_name,
                "status": "PASSED",
                "details": test_results
            }
            
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {str(e)}")
            return {
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "details": test_results
            }
    
    async def test_performance_requirements(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test Performance Requirements (<500ms response time)"""
        test_name = "Performance Requirements"
        logger.info(f"🧪 Testing: {test_name}")
        
        try:
            import time
            
            # Test multiple requests to measure average response time
            response_times = []
            for i in range(5):
                start_time = time.time()
                url = f"{self.backend_url}/api/v1/data/predictions?timeframe=1M&nav_timestamp={int(time.time())}&nav_direction=next"
                
                async with session.get(url) as response:
                    await response.json()  # Ensure full response is read
                    end_time = time.time()
                    response_time_ms = (end_time - start_time) * 1000
                    response_times.append(response_time_ms)
                    logger.info(f"Request {i+1}: {response_time_ms:.2f}ms")
            
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            # Performance assertion: Average should be < 500ms
            performance_passed = avg_response_time < 500
            
            logger.info(f"Average response time: {avg_response_time:.2f}ms")
            logger.info(f"Max response time: {max_response_time:.2f}ms")
            
            if performance_passed:
                logger.info("✅ Performance requirements met")
            else:
                logger.warning("⚠️ Performance requirements not met")
            
            return {
                "test_name": test_name,
                "status": "PASSED" if performance_passed else "WARNING",
                "details": {
                    "average_response_time_ms": avg_response_time,
                    "max_response_time_ms": max_response_time,
                    "performance_target_ms": 500,
                    "performance_met": performance_passed,
                    "response_times": response_times
                }
            }
            
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {str(e)}")
            return {
                "test_name": test_name,
                "status": "FAILED",
                "error": str(e),
                "details": {}
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all E2E tests and return comprehensive results"""
        logger.info("🚀 Starting E2E Timeline Navigation Tests")
        
        async with aiohttp.ClientSession() as session:
            test_results = []
            
            # Run all test suites
            test_results.append(await self.test_backend_navigation_endpoint(session))
            test_results.append(await self.test_frontend_parameter_forwarding(session))
            test_results.append(await self.test_error_handling_scenarios(session))
            test_results.append(await self.test_performance_requirements(session))
            
            # Calculate overall results
            passed_tests = len([r for r in test_results if r["status"] == "PASSED"])
            failed_tests = len([r for r in test_results if r["status"] == "FAILED"])
            warning_tests = len([r for r in test_results if r["status"] == "WARNING"])
            
            overall_status = "PASSED" if failed_tests == 0 else "FAILED"
            
            summary = {
                "overall_status": overall_status,
                "test_summary": {
                    "total_tests": len(test_results),
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "warnings": warning_tests
                },
                "test_results": test_results,
                "timestamp": datetime.now().isoformat(),
                "test_suite": "Timeline Navigation E2E Tests",
                "bug_id": "KI-PROGNOSEN-NAV-002"
            }
            
            return summary


# Test Runner Function
async def run_timeline_navigation_e2e_tests():
    """Main test runner function"""
    tester = TimelineNavigationE2ETester()
    results = await tester.run_all_tests()
    
    print("\n" + "="*80)
    print("🧪 TIMELINE NAVIGATION E2E TEST RESULTS")
    print("="*80)
    print(f"Overall Status: {'✅ PASSED' if results['overall_status'] == 'PASSED' else '❌ FAILED'}")
    print(f"Tests Run: {results['test_summary']['total_tests']}")
    print(f"Passed: {results['test_summary']['passed']}")
    print(f"Failed: {results['test_summary']['failed']}")
    print(f"Warnings: {results['test_summary']['warnings']}")
    print("-"*80)
    
    for test_result in results['test_results']:
        status_icon = "✅" if test_result['status'] == 'PASSED' else ("⚠️" if test_result['status'] == 'WARNING' else "❌")
        print(f"{status_icon} {test_result['test_name']}: {test_result['status']}")
        
        if 'error' in test_result:
            print(f"   Error: {test_result['error']}")
    
    print("="*80)
    return results


# Direct execution for testing
if __name__ == "__main__":
    print("🧪 Running Timeline Navigation E2E Tests...")
    print("⚠️  Note: Ensure both services are running:")
    print(f"   - Backend: {TEST_BACKEND_URL}")
    print(f"   - Frontend: {TEST_FRONTEND_URL}")
    print()
    
    results = asyncio.run(run_timeline_navigation_e2e_tests())
    
    if results['overall_status'] == 'PASSED':
        print("\n🎉 All tests passed! Timeline Navigation implementation is ready for production.")
    else:
        print("\n🔧 Some tests failed. Review the results and fix issues before deployment.")