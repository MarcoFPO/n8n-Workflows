#!/usr/bin/env python3
"""
E2E Navigation Test Suite - Frontend Navigation Quality Gate
Löst FRONTEND-NAV-001 Bug durch systematische End-to-End Validierung

Diese Test-Suite implementiert den fehlenden Quality Gate für:
1. HTML Navigation Menu Presence Check
2. User Experience Navigation Flow Tests  
3. Backend Service Endpoint Validation
4. Complete E2E User Journey Testing

Autor: Claude Code
Datum: 27. August 2025
Version: 1.0.0 - E2E Quality Gate Implementation
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NavigationTest:
    """Navigation Test Case Definition"""
    name: str
    url: str
    expected_status: int
    expected_redirect: Optional[str] = None
    should_contain: Optional[List[str]] = None
    description: str = ""

@dataclass
class TestResult:
    """Test Result Container"""
    test_name: str
    passed: bool
    actual_status: int
    expected_status: int
    response_time_ms: float
    error_message: Optional[str] = None
    html_content_length: int = 0
    navigation_links_found: int = 0

class FrontendNavigationE2ETester:
    """
    E2E Frontend Navigation Test Suite
    
    SOLID Principles:
    - Single Responsibility: Nur Navigation Testing
    - Open/Closed: Erweiterbar für neue Tests
    - Interface Segregation: Getrennte Test-Methoden
    """
    
    def __init__(self, base_url: str = "http://10.1.1.174:8080"):
        self.base_url = base_url.rstrip('/')
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        self.test_results: List[TestResult] = []
        
    async def test_navigation_menu_html(self) -> TestResult:
        """Test 1: HTML Navigation Menu Presence"""
        test_name = "HTML Navigation Menu Presence"
        start_time = datetime.now()
        
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(f"{self.base_url}/") as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    html_content = await response.text()
                    
                    # Check for navigation menu HTML
                    nav_menu_present = 'class="nav-menu"' in html_content
                    required_nav_links = [
                        'href="/dashboard"',
                        'href="/ki-vorhersage"', 
                        'href="/soll-ist-vergleich"',
                        'href="/depot"'
                    ]
                    
                    nav_links_found = sum(1 for link in required_nav_links if link in html_content)
                    
                    passed = nav_menu_present and nav_links_found == 4
                    error_msg = None if passed else f"Navigation menu missing. Links found: {nav_links_found}/4"
                    
                    return TestResult(
                        test_name=test_name,
                        passed=passed,
                        actual_status=response.status,
                        expected_status=200,
                        response_time_ms=response_time,
                        error_message=error_msg,
                        html_content_length=len(html_content),
                        navigation_links_found=nav_links_found
                    )
                    
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return TestResult(
                test_name=test_name,
                passed=False,
                actual_status=0,
                expected_status=200,
                response_time_ms=response_time,
                error_message=f"HTTP Error: {str(e)}"
            )
    
    async def test_navigation_endpoints(self) -> List[TestResult]:
        """Test 2-5: Individual Navigation Endpoint Tests"""
        navigation_tests = [
            NavigationTest(
                name="Dashboard Navigation",
                url=f"{self.base_url}/dashboard",
                expected_status=301,
                expected_redirect="/",
                description="Dashboard should redirect to homepage"
            ),
            NavigationTest(
                name="KI-Vorhersage Navigation",
                url=f"{self.base_url}/ki-vorhersage", 
                expected_status=301,
                expected_redirect="/prognosen?timeframe=1M",
                description="KI-Vorhersage should redirect to prognosen"
            ),
            NavigationTest(
                name="SOLL-IST Vergleich Navigation",
                url=f"{self.base_url}/soll-ist-vergleich",
                expected_status=301, 
                expected_redirect="/vergleichsanalyse?timeframe=1M",
                description="SOLL-IST should redirect to vergleichsanalyse"
            ),
            NavigationTest(
                name="Depot Navigation",
                url=f"{self.base_url}/depot",
                expected_status=200,
                should_contain=["💼 Depot-Analyse"],
                description="Depot should load direct content"
            )
        ]
        
        results = []
        
        for test in navigation_tests:
            start_time = datetime.now()
            
            try:
                async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                    async with session.get(test.url, allow_redirects=False) as response:
                        response_time = (datetime.now() - start_time).total_seconds() * 1000
                        
                        status_check = response.status == test.expected_status
                        
                        # Check redirect location if expected
                        redirect_check = True
                        if test.expected_redirect:
                            location_header = response.headers.get('location', '')
                            redirect_check = test.expected_redirect in location_header
                        
                        # Check content if required (for non-redirect responses)
                        content_check = True
                        if test.should_contain and response.status == 200:
                            content = await response.text()
                            content_check = all(phrase in content for phrase in test.should_contain)
                        
                        passed = status_check and redirect_check and content_check
                        error_msg = None
                        if not passed:
                            error_parts = []
                            if not status_check:
                                error_parts.append(f"Status: {response.status} != {test.expected_status}")
                            if not redirect_check:
                                error_parts.append(f"Redirect: {response.headers.get('location', 'None')} != {test.expected_redirect}")
                            if not content_check:
                                error_parts.append("Content check failed")
                            error_msg = "; ".join(error_parts)
                        
                        results.append(TestResult(
                            test_name=test.name,
                            passed=passed,
                            actual_status=response.status,
                            expected_status=test.expected_status,
                            response_time_ms=response_time,
                            error_message=error_msg
                        ))
                        
            except Exception as e:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                results.append(TestResult(
                    test_name=test.name,
                    passed=False,
                    actual_status=0,
                    expected_status=test.expected_status,
                    response_time_ms=response_time,
                    error_message=f"HTTP Error: {str(e)}"
                ))
        
        return results
    
    async def test_redirect_destinations(self) -> List[TestResult]:
        """Test 6-8: Redirect Destination Validation"""
        redirect_tests = [
            NavigationTest(
                name="Dashboard Redirect Destination",
                url=f"{self.base_url}/dashboard",
                expected_status=200,
                should_contain=["🏠 Dashboard", "Aktienanalyse Ökosystem"],
                description="Dashboard redirect should lead to functional homepage"
            ),
            NavigationTest(
                name="KI-Vorhersage Redirect Destination", 
                url=f"{self.base_url}/ki-vorhersage",
                expected_status=200,
                should_contain=["📊 KI-Prognosen", "Machine Learning"],
                description="KI-Vorhersage redirect should lead to functional prognosen page"
            ),
            NavigationTest(
                name="SOLL-IST Redirect Destination",
                url=f"{self.base_url}/soll-ist-vergleich", 
                expected_status=200,
                should_contain=["⚖️ SOLL-IST Vergleichsanalyse"],
                description="SOLL-IST redirect should lead to functional vergleichsanalyse page"
            )
        ]
        
        results = []
        
        for test in redirect_tests:
            start_time = datetime.now()
            
            try:
                async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                    async with session.get(test.url, allow_redirects=True) as response:
                        response_time = (datetime.now() - start_time).total_seconds() * 1000
                        content = await response.text()
                        
                        status_check = response.status == test.expected_status
                        content_check = all(phrase in content for phrase in test.should_contain or [])
                        
                        passed = status_check and content_check
                        error_msg = None
                        if not passed:
                            error_parts = []
                            if not status_check:
                                error_parts.append(f"Status: {response.status} != {test.expected_status}")
                            if not content_check:
                                missing_content = [phrase for phrase in (test.should_contain or []) if phrase not in content]
                                error_parts.append(f"Missing content: {missing_content}")
                            error_msg = "; ".join(error_parts)
                        
                        results.append(TestResult(
                            test_name=test.name,
                            passed=passed,
                            actual_status=response.status,
                            expected_status=test.expected_status,
                            response_time_ms=response_time,
                            error_message=error_msg,
                            html_content_length=len(content)
                        ))
                        
            except Exception as e:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                results.append(TestResult(
                    test_name=test.name,
                    passed=False,
                    actual_status=0,
                    expected_status=test.expected_status,
                    response_time_ms=response_time,
                    error_message=f"HTTP Error: {str(e)}"
                ))
        
        return results
    
    async def run_complete_e2e_test_suite(self) -> Dict[str, Any]:
        """Run Complete E2E Test Suite"""
        logger.info("🧪 Starting Complete E2E Frontend Navigation Test Suite")
        test_start_time = datetime.now()
        
        # Test 1: HTML Navigation Menu
        logger.info("Test 1: HTML Navigation Menu Presence...")
        nav_menu_result = await self.test_navigation_menu_html()
        self.test_results.append(nav_menu_result)
        
        # Tests 2-5: Navigation Endpoints
        logger.info("Tests 2-5: Navigation Endpoint Validation...")
        endpoint_results = await self.test_navigation_endpoints()
        self.test_results.extend(endpoint_results)
        
        # Tests 6-8: Redirect Destinations
        logger.info("Tests 6-8: Redirect Destination Validation...")
        redirect_results = await self.test_redirect_destinations()
        self.test_results.extend(redirect_results)
        
        # Calculate results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.passed)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        total_test_time = (datetime.now() - test_start_time).total_seconds()
        
        # Determine overall status
        if success_rate == 100:
            overall_status = "✅ PASS - All navigation tests successful"
            bug_status = "🎉 FRONTEND-NAV-001 BUG RESOLVED"
        elif success_rate >= 75:
            overall_status = "⚠️  PARTIAL - Most navigation tests passed"
            bug_status = "🔄 FRONTEND-NAV-001 BUG PARTIALLY FIXED"
        else:
            overall_status = "❌ FAIL - Critical navigation failures"
            bug_status = "🚨 FRONTEND-NAV-001 BUG STILL PRESENT"
        
        return {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests, 
                "failed_tests": failed_tests,
                "success_rate": f"{success_rate:.1f}%",
                "total_test_time_seconds": total_test_time,
                "overall_status": overall_status,
                "bug_status": bug_status
            },
            "detailed_results": [
                {
                    "test_name": result.test_name,
                    "passed": result.passed,
                    "status_code": result.actual_status,
                    "response_time_ms": result.response_time_ms,
                    "error_message": result.error_message,
                    "navigation_links_found": result.navigation_links_found,
                    "content_length": result.html_content_length
                }
                for result in self.test_results
            ],
            "navigation_analysis": {
                "html_navigation_menu": nav_menu_result.passed,
                "navigation_links_count": nav_menu_result.navigation_links_found,
                "all_endpoints_working": all(result.passed for result in endpoint_results),
                "all_redirects_working": all(result.passed for result in redirect_results)
            },
            "performance_metrics": {
                "average_response_time_ms": sum(result.response_time_ms for result in self.test_results) / len(self.test_results),
                "fastest_response_ms": min(result.response_time_ms for result in self.test_results),
                "slowest_response_ms": max(result.response_time_ms for result in self.test_results)
            },
            "timestamp": datetime.now().isoformat(),
            "frontend_url": self.base_url
        }
    
    def print_test_report(self, results: Dict[str, Any]) -> None:
        """Print Human-Readable Test Report"""
        print("\n" + "="*80)
        print("🧪 E2E FRONTEND NAVIGATION TEST REPORT - FRONTEND-NAV-001 BUG VALIDATION")
        print("="*80)
        
        # Summary
        summary = results["test_summary"]
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   ✅ Passed: {summary['passed_tests']}")
        print(f"   ❌ Failed: {summary['failed_tests']}")
        print(f"   Success Rate: {summary['success_rate']}")
        print(f"   Total Time: {summary['total_test_time_seconds']:.2f}s")
        print(f"\n🎯 OVERALL STATUS: {summary['overall_status']}")
        print(f"🚨 BUG STATUS: {summary['bug_status']}")
        
        # Navigation Analysis
        nav_analysis = results["navigation_analysis"]
        print(f"\n🧭 NAVIGATION ANALYSIS:")
        print(f"   HTML Menu Present: {'✅' if nav_analysis['html_navigation_menu'] else '❌'}")
        print(f"   Navigation Links Found: {nav_analysis['navigation_links_count']}/4")
        print(f"   All Endpoints Working: {'✅' if nav_analysis['all_endpoints_working'] else '❌'}")
        print(f"   All Redirects Working: {'✅' if nav_analysis['all_redirects_working'] else '❌'}")
        
        # Performance
        perf = results["performance_metrics"] 
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"   Average Response Time: {perf['average_response_time_ms']:.1f}ms")
        print(f"   Fastest Response: {perf['fastest_response_ms']:.1f}ms")
        print(f"   Slowest Response: {perf['slowest_response_ms']:.1f}ms")
        
        # Detailed Results
        print(f"\n📋 DETAILED TEST RESULTS:")
        for result in results["detailed_results"]:
            status_icon = "✅" if result["passed"] else "❌"
            print(f"   {status_icon} {result['test_name']}")
            print(f"      Status: {result['status_code']} | Time: {result['response_time_ms']:.1f}ms")
            if result["error_message"]:
                print(f"      Error: {result['error_message']}")
            if result["navigation_links_found"] > 0:
                print(f"      Navigation Links: {result['navigation_links_found']}/4")
        
        print("\n" + "="*80)
        print("🤖 Generated with [Claude Code](https://claude.ai/code) - E2E Quality Gate")
        print("="*80 + "\n")

async def main():
    """Main Test Runner"""
    tester = FrontendNavigationE2ETester()
    
    try:
        # Run complete test suite
        results = await tester.run_complete_e2e_test_suite()
        
        # Print report
        tester.print_test_report(results)
        
        # Save results to JSON
        results_file = f"e2e_navigation_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Test results saved to: {results_file}")
        
        # Return exit code based on test results
        success_rate = float(results["test_summary"]["success_rate"].replace('%', ''))
        if success_rate == 100:
            logger.info("🎉 All tests passed - FRONTEND-NAV-001 bug resolved!")
            return 0
        elif success_rate >= 75:
            logger.warning("⚠️ Partial success - some navigation issues remain")
            return 1
        else:
            logger.error("❌ Critical failures - FRONTEND-NAV-001 bug not resolved")
            return 2
            
    except Exception as e:
        logger.error(f"💥 Test suite failed: {str(e)}")
        return 3

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)