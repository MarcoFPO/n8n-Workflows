#!/usr/bin/env python3
"""
Quality Assurance Agent - Unabhängige Qualitätskontrolle
Separater Agent für objektive Validierung ohne Development-Bias

KRITISCHER GRUNDSATZ:
"Ein Agent darf niemals seine eigene Arbeit als erfolgreich bewerten!"

Dieser QA-Agent ist vollständig unabhängig und führt kritische Validierung durch:
- E2E User Experience Testing
- Objective Success/Failure Assessment  
- Independent Quality Gates
- Critical Issue Detection

Autor: Claude Code - Quality Assurance Specialist
Datum: 27. August 2025
Version: 1.0.0 - Independent QA Agent
"""

import asyncio
import aiohttp
import ssl
import json
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Setup independent logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - QA-AGENT - %(levelname)s - %(message)s')
logger = logging.getLogger("QA_AGENT")

@dataclass
class QATestCase:
    """QA Test Case Definition"""
    test_id: str
    test_name: str
    test_type: str  # "functional", "performance", "user_experience", "integration"
    url: str
    expected_status: int
    expected_content: Optional[List[str]] = None
    expected_redirect: Optional[str] = None
    max_response_time_ms: float = 2000.0
    critical: bool = True  # Is this test critical for success?
    description: str = ""

@dataclass 
class QATestResult:
    """QA Test Result Container"""
    test_id: str
    test_name: str
    passed: bool
    critical_failure: bool
    actual_status: int
    expected_status: int
    response_time_ms: float
    error_details: Optional[str] = None
    performance_rating: str = "UNKNOWN"  # "EXCELLENT", "GOOD", "POOR", "CRITICAL"
    user_experience_rating: str = "UNKNOWN"

class IndependentQualityAssuranceAgent:
    """
    Independent Quality Assurance Agent
    
    SOLID Principles:
    - Single Responsibility: Nur Quality Assurance, kein Development
    - Open/Closed: Erweiterbar für neue QA Tests
    - Interface Segregation: Getrennte QA-Methoden
    - Dependency Inversion: Unabhängig von Development-Code
    
    CRITICAL DESIGN PRINCIPLE:
    Dieser Agent ist vollständig unabhängig und darf NIEMALS:
    - Development-Code modifizieren
    - Fixes implementieren
    - Success ohne objektive Validierung melden
    """
    
    def __init__(self, system_base_url: str = "https://10.1.1.174", agent_id: str = "QA-001"):
        self.system_base_url = system_base_url.rstrip('/')
        self.agent_id = agent_id
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        self.qa_test_results: List[QATestResult] = []
        self.qa_start_time = datetime.now()
        
        # SSL context for self-signed certificates
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # QA Agent Identity
        logger.info(f"🔍 Independent QA Agent {self.agent_id} initialized")
        logger.info(f"🎯 Mission: Objective quality validation without development bias")
        logger.info(f"🚫 Restrictions: NO development, NO fixes, NO biased success reports")
    
    def define_critical_qa_test_suite(self) -> List[QATestCase]:
        """Define Critical QA Test Suite for Frontend Navigation"""
        
        critical_tests = [
            # CRITICAL USER EXPERIENCE TESTS
            QATestCase(
                test_id="UX-001",
                test_name="Homepage User Experience",
                test_type="user_experience", 
                url=f"{self.system_base_url}/",
                expected_status=200,
                expected_content=["🏠 Dashboard", "Aktienanalyse Ökosystem", 'class="nav-menu"'],
                max_response_time_ms=1000.0,
                critical=True,
                description="Homepage must load with navigation menu for users"
            ),
            
            QATestCase(
                test_id="UX-002", 
                test_name="Navigation Menu Presence",
                test_type="user_experience",
                url=f"{self.system_base_url}/",
                expected_status=200,
                expected_content=[
                    'href="/dashboard"', 'href="/ki-vorhersage"', 
                    'href="/soll-ist-vergleich"', 'href="/depot"'
                ],
                max_response_time_ms=1000.0,
                critical=True,
                description="All 4 navigation links must be present in HTML"
            ),
            
            # CRITICAL FUNCTIONAL TESTS
            QATestCase(
                test_id="FUNC-001",
                test_name="Dashboard Navigation Functionality", 
                test_type="functional",
                url=f"{self.system_base_url}/dashboard",
                expected_status=301,
                expected_redirect="/",
                max_response_time_ms=500.0,
                critical=True,
                description="Dashboard link must redirect to homepage"
            ),
            
            QATestCase(
                test_id="FUNC-002",
                test_name="KI-Vorhersage Navigation Functionality",
                test_type="functional", 
                url=f"{self.system_base_url}/ki-vorhersage",
                expected_status=301,
                expected_redirect="/prognosen?timeframe=1M",
                max_response_time_ms=500.0,
                critical=True,
                description="KI-Vorhersage link must redirect to prognosen"
            ),
            
            QATestCase(
                test_id="FUNC-003",
                test_name="SOLL-IST Vergleich Navigation Functionality",
                test_type="functional",
                url=f"{self.system_base_url}/soll-ist-vergleich", 
                expected_status=301,
                expected_redirect="/vergleichsanalyse?timeframe=1M",
                max_response_time_ms=500.0,
                critical=True,
                description="SOLL-IST link must redirect to vergleichsanalyse"
            ),
            
            QATestCase(
                test_id="FUNC-004",
                test_name="Depot Navigation Functionality",
                test_type="functional",
                url=f"{self.system_base_url}/depot",
                expected_status=200,
                expected_content=["💼 Depot-Analyse", "Portfolio-Übersicht"],
                max_response_time_ms=1000.0,
                critical=True,
                description="Depot link must load depot analysis page"
            ),
            
            # CRITICAL END-TO-END USER JOURNEY TESTS
            QATestCase(
                test_id="E2E-001",
                test_name="Dashboard Complete User Journey",
                test_type="integration",
                url=f"{self.system_base_url}/dashboard",
                expected_status=200,  # After redirect
                expected_content=["🏠 Dashboard", "Aktienanalyse Ökosystem"],
                max_response_time_ms=1500.0,
                critical=True,
                description="User clicking Dashboard must see functional dashboard page"
            ),
            
            QATestCase(
                test_id="E2E-002", 
                test_name="KI-Vorhersage Complete User Journey",
                test_type="integration",
                url=f"{self.system_base_url}/ki-vorhersage",
                expected_status=200,  # After redirect
                expected_content=["📊 KI-Prognosen", "Machine Learning"],
                max_response_time_ms=2000.0,
                critical=True,
                description="User clicking KI-Vorhersage must see functional prognosen page"
            ),
            
            QATestCase(
                test_id="E2E-003",
                test_name="SOLL-IST Complete User Journey", 
                test_type="integration",
                url=f"{self.system_base_url}/soll-ist-vergleich",
                expected_status=200,  # After redirect
                expected_content=["⚖️ SOLL-IST Vergleichsanalyse"],
                max_response_time_ms=2000.0,
                critical=True,
                description="User clicking SOLL-IST must see functional vergleichsanalyse page"
            )
        ]
        
        logger.info(f"🧪 Defined {len(critical_tests)} critical QA test cases")
        return critical_tests
    
    async def execute_qa_test_case(self, test_case: QATestCase) -> QATestResult:
        """Execute Individual QA Test Case with Objective Assessment"""
        
        logger.info(f"🔍 Executing QA Test: {test_case.test_id} - {test_case.test_name}")
        test_start_time = datetime.now()
        
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(timeout=self.session_timeout, connector=connector) as session:
                # Determine redirect behavior based on test type
                follow_redirects = test_case.test_type in ["integration", "user_experience"]
                
                async with session.get(test_case.url, allow_redirects=follow_redirects) as response:
                    response_time_ms = (datetime.now() - test_start_time).total_seconds() * 1000
                    
                    # Status Code Assessment
                    status_passed = response.status == test_case.expected_status
                    
                    # Content Assessment
                    content_passed = True
                    content_details = ""
                    if test_case.expected_content:
                        content = await response.text()
                        missing_content = [item for item in test_case.expected_content if item not in content]
                        content_passed = len(missing_content) == 0
                        if not content_passed:
                            content_details = f"Missing content: {missing_content}"
                    
                    # Redirect Assessment  
                    redirect_passed = True
                    redirect_details = ""
                    if test_case.expected_redirect and not follow_redirects:
                        location = response.headers.get('location', '')
                        redirect_passed = test_case.expected_redirect in location
                        if not redirect_passed:
                            redirect_details = f"Expected redirect: {test_case.expected_redirect}, Got: {location}"
                    
                    # Performance Assessment
                    performance_rating = self._assess_performance(response_time_ms, test_case.max_response_time_ms)
                    
                    # Overall Assessment
                    test_passed = status_passed and content_passed and redirect_passed
                    critical_failure = test_case.critical and not test_passed
                    
                    # Error Details
                    error_details = None
                    if not test_passed:
                        error_parts = []
                        if not status_passed:
                            error_parts.append(f"Status: {response.status} != {test_case.expected_status}")
                        if content_details:
                            error_parts.append(content_details)
                        if redirect_details:
                            error_parts.append(redirect_details)
                        error_details = "; ".join(error_parts)
                    
                    # User Experience Rating
                    ux_rating = self._assess_user_experience(test_passed, response_time_ms, test_case.test_type)
                    
                    result = QATestResult(
                        test_id=test_case.test_id,
                        test_name=test_case.test_name,
                        passed=test_passed,
                        critical_failure=critical_failure,
                        actual_status=response.status,
                        expected_status=test_case.expected_status,
                        response_time_ms=response_time_ms,
                        error_details=error_details,
                        performance_rating=performance_rating,
                        user_experience_rating=ux_rating
                    )
                    
                    if test_passed:
                        logger.info(f"✅ QA Test {test_case.test_id} PASSED - {response_time_ms:.1f}ms")
                    else:
                        logger.error(f"❌ QA Test {test_case.test_id} FAILED - {error_details}")
                    
                    return result
                    
        except Exception as e:
            response_time_ms = (datetime.now() - test_start_time).total_seconds() * 1000
            logger.error(f"💥 QA Test {test_case.test_id} EXCEPTION: {str(e)}")
            
            return QATestResult(
                test_id=test_case.test_id,
                test_name=test_case.test_name,
                passed=False,
                critical_failure=test_case.critical,
                actual_status=0,
                expected_status=test_case.expected_status,
                response_time_ms=response_time_ms,
                error_details=f"Network/HTTP Error: {str(e)}",
                performance_rating="CRITICAL",
                user_experience_rating="CRITICAL"
            )
    
    def _assess_performance(self, response_time_ms: float, max_allowed_ms: float) -> str:
        """Assess Performance Rating"""
        if response_time_ms <= max_allowed_ms * 0.5:
            return "EXCELLENT"
        elif response_time_ms <= max_allowed_ms * 0.8:
            return "GOOD"
        elif response_time_ms <= max_allowed_ms:
            return "ACCEPTABLE"
        else:
            return "CRITICAL"
    
    def _assess_user_experience(self, test_passed: bool, response_time_ms: float, test_type: str) -> str:
        """Assess User Experience Rating"""
        if not test_passed:
            return "CRITICAL"
        
        if test_type == "user_experience":
            if response_time_ms <= 500:
                return "EXCELLENT"
            elif response_time_ms <= 1000:
                return "GOOD"
            elif response_time_ms <= 2000:
                return "ACCEPTABLE"
            else:
                return "POOR"
        else:
            return "GOOD" if test_passed else "CRITICAL"
    
    async def execute_complete_qa_audit(self) -> Dict[str, Any]:
        """Execute Complete Independent QA Audit"""
        
        logger.info("🔍 Starting Independent QA Audit - FRONTEND-NAV-001 Bug Validation")
        logger.info(f"🎯 QA Agent: {self.agent_id} | System: {self.system_base_url}")
        
        # Define and execute test suite
        test_cases = self.define_critical_qa_test_suite()
        
        for test_case in test_cases:
            result = await self.execute_qa_test_case(test_case)
            self.qa_test_results.append(result)
        
        # Analyze results
        total_tests = len(self.qa_test_results)
        passed_tests = sum(1 for result in self.qa_test_results if result.passed)
        failed_tests = total_tests - passed_tests
        critical_failures = sum(1 for result in self.qa_test_results if result.critical_failure)
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # QA Assessment Categories
        qa_categories = {
            "user_experience": [r for r in self.qa_test_results if r.test_name.startswith(("Homepage", "Navigation Menu"))],
            "functional": [r for r in self.qa_test_results if "Navigation Functionality" in r.test_name],
            "integration": [r for r in self.qa_test_results if "Complete User Journey" in r.test_name]
        }
        
        # Calculate category success rates
        category_scores = {}
        for category, results in qa_categories.items():
            if results:
                category_passed = sum(1 for r in results if r.passed)
                category_scores[category] = (category_passed / len(results)) * 100
            else:
                category_scores[category] = 0
        
        # INDEPENDENT QA VERDICT (CRITICAL)
        qa_verdict = self._determine_independent_qa_verdict(success_rate, critical_failures, category_scores)
        
        total_qa_time = (datetime.now() - self.qa_start_time).total_seconds()
        
        # Performance Analysis
        avg_response_time = sum(r.response_time_ms for r in self.qa_test_results) / len(self.qa_test_results)
        performance_violations = sum(1 for r in self.qa_test_results if r.performance_rating in ["CRITICAL", "POOR"])
        
        qa_audit_report = {
            "qa_audit_summary": {
                "qa_agent_id": self.agent_id,
                "audit_timestamp": datetime.now().isoformat(),
                "total_tests_executed": total_tests,
                "tests_passed": passed_tests,
                "tests_failed": failed_tests,
                "critical_failures": critical_failures,
                "overall_success_rate": f"{success_rate:.1f}%",
                "audit_duration_seconds": total_qa_time,
                "independent_qa_verdict": qa_verdict
            },
            
            "qa_category_analysis": {
                "user_experience_score": f"{category_scores.get('user_experience', 0):.1f}%",
                "functional_score": f"{category_scores.get('functional', 0):.1f}%", 
                "integration_score": f"{category_scores.get('integration', 0):.1f}%"
            },
            
            "performance_analysis": {
                "average_response_time_ms": avg_response_time,
                "performance_violations": performance_violations,
                "sla_compliance": "<0.12s requirement" if avg_response_time < 120 else "SLA VIOLATION"
            },
            
            "detailed_qa_results": [
                {
                    "test_id": result.test_id,
                    "test_name": result.test_name, 
                    "passed": result.passed,
                    "critical_failure": result.critical_failure,
                    "status_code": result.actual_status,
                    "response_time_ms": result.response_time_ms,
                    "performance_rating": result.performance_rating,
                    "user_experience_rating": result.user_experience_rating,
                    "error_details": result.error_details
                }
                for result in self.qa_test_results
            ],
            
            "qa_recommendations": self._generate_qa_recommendations(success_rate, critical_failures, category_scores),
            
            "frontend_nav_001_bug_status": self._assess_bug_status(success_rate, critical_failures)
        }
        
        return qa_audit_report
    
    def _determine_independent_qa_verdict(self, success_rate: float, critical_failures: int, category_scores: Dict[str, float]) -> str:
        """Independent QA Verdict - Objective Assessment"""
        
        if success_rate == 100.0 and critical_failures == 0:
            return "✅ QA APPROVED - All critical tests passed"
        elif success_rate >= 90.0 and critical_failures == 0:
            return "⚠️ QA CONDITIONAL APPROVAL - Minor issues detected"
        elif success_rate >= 75.0 and critical_failures <= 1:
            return "🔄 QA REQUIRES FIXES - Major issues need resolution"
        elif success_rate >= 50.0:
            return "❌ QA REJECTED - Critical functionality broken" 
        else:
            return "🚨 QA CRITICAL FAILURE - System not functional for users"
    
    def _generate_qa_recommendations(self, success_rate: float, critical_failures: int, category_scores: Dict[str, float]) -> List[str]:
        """Generate QA Recommendations"""
        recommendations = []
        
        if success_rate < 100:
            recommendations.append("🔧 Fix all failing test cases before deployment")
        
        if critical_failures > 0:
            recommendations.append(f"🚨 Address {critical_failures} critical failures immediately")
        
        if category_scores.get('user_experience', 0) < 100:
            recommendations.append("👤 Improve user experience - navigation must be intuitive")
        
        if category_scores.get('functional', 0) < 100:
            recommendations.append("⚙️ Fix functional issues - all navigation links must work")
        
        if category_scores.get('integration', 0) < 100:
            recommendations.append("🔗 Resolve integration issues - end-to-end user journeys must work")
        
        recommendations.append("🧪 Implement continuous QA monitoring")
        recommendations.append("📊 Set up automated QA dashboards") 
        
        return recommendations
    
    def _assess_bug_status(self, success_rate: float, critical_failures: int) -> str:
        """Assess FRONTEND-NAV-001 Bug Status"""
        if success_rate == 100.0 and critical_failures == 0:
            return "🎉 FRONTEND-NAV-001 BUG RESOLVED - All navigation working"
        elif success_rate >= 75.0:
            return "🔄 FRONTEND-NAV-001 PARTIALLY RESOLVED - Some navigation issues remain"
        else:
            return "🚨 FRONTEND-NAV-001 BUG STILL PRESENT - Critical navigation failures"
    
    def print_independent_qa_report(self, qa_report: Dict[str, Any]) -> None:
        """Print Independent QA Report"""
        
        print("\n" + "="*100)
        print(f"🔍 INDEPENDENT QUALITY ASSURANCE AUDIT REPORT - QA AGENT {self.agent_id}")
        print("="*100)
        
        # QA Summary
        summary = qa_report["qa_audit_summary"]
        print(f"\n📊 QA AUDIT SUMMARY:")
        print(f"   QA Agent: {summary['qa_agent_id']}")
        print(f"   Audit Time: {summary['audit_timestamp']}")
        print(f"   Total Tests: {summary['total_tests_executed']}")
        print(f"   ✅ Passed: {summary['tests_passed']}")
        print(f"   ❌ Failed: {summary['tests_failed']}")
        print(f"   🚨 Critical Failures: {summary['critical_failures']}")
        print(f"   Success Rate: {summary['overall_success_rate']}")
        print(f"   Audit Duration: {summary['audit_duration_seconds']:.2f}s")
        print(f"\n🎯 INDEPENDENT QA VERDICT: {summary['independent_qa_verdict']}")
        
        # Category Analysis
        categories = qa_report["qa_category_analysis"]
        print(f"\n📋 QA CATEGORY ANALYSIS:")
        print(f"   👤 User Experience: {categories['user_experience_score']}")
        print(f"   ⚙️ Functional: {categories['functional_score']}")
        print(f"   🔗 Integration: {categories['integration_score']}")
        
        # Performance Analysis
        perf = qa_report["performance_analysis"]
        print(f"\n⚡ PERFORMANCE ANALYSIS:")
        print(f"   Average Response Time: {perf['average_response_time_ms']:.1f}ms")
        print(f"   Performance Violations: {perf['performance_violations']}")
        print(f"   SLA Compliance: {perf['sla_compliance']}")
        
        # Bug Status
        bug_status = qa_report["frontend_nav_001_bug_status"]
        print(f"\n🐛 FRONTEND-NAV-001 BUG STATUS: {bug_status}")
        
        # Recommendations
        recommendations = qa_report["qa_recommendations"]
        print(f"\n💡 QA RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"   {rec}")
        
        # Detailed Results
        print(f"\n📋 DETAILED QA TEST RESULTS:")
        for result in qa_report["detailed_qa_results"]:
            status_icon = "✅" if result["passed"] else "❌"
            critical_icon = "🚨" if result["critical_failure"] else ""
            print(f"   {status_icon}{critical_icon} {result['test_id']}: {result['test_name']}")
            print(f"      Status: {result['status_code']} | Time: {result['response_time_ms']:.1f}ms")
            print(f"      Performance: {result['performance_rating']} | UX: {result['user_experience_rating']}")
            if result["error_details"]:
                print(f"      Error: {result['error_details']}")
        
        print("\n" + "="*100)
        print("🔍 Independent QA Agent - Objective Quality Validation")
        print("🤖 Generated with [Claude Code](https://claude.ai/code)")
        print("="*100 + "\n")

async def main():
    """Main QA Agent Execution"""
    
    qa_agent = IndependentQualityAssuranceAgent()
    
    try:
        # Execute independent QA audit
        qa_report = await qa_agent.execute_complete_qa_audit()
        
        # Print comprehensive report
        qa_agent.print_independent_qa_report(qa_report)
        
        # Save QA report to file
        qa_report_file = f"independent_qa_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(qa_report_file, 'w', encoding='utf-8') as f:
            json.dump(qa_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Independent QA report saved to: {qa_report_file}")
        
        # Return QA exit code
        success_rate = float(qa_report["qa_audit_summary"]["overall_success_rate"].replace('%', ''))
        critical_failures = qa_report["qa_audit_summary"]["critical_failures"]
        
        if success_rate == 100 and critical_failures == 0:
            logger.info("🎉 QA APPROVED - System ready for production")
            return 0
        elif success_rate >= 90 and critical_failures == 0:
            logger.warning("⚠️ QA CONDITIONAL APPROVAL - Minor fixes required")
            return 1
        elif success_rate >= 75:
            logger.error("🔄 QA REQUIRES MAJOR FIXES - Critical issues present")
            return 2
        else:
            logger.error("🚨 QA CRITICAL FAILURE - System not ready for users")
            return 3
            
    except Exception as e:
        logger.error(f"💥 QA Agent execution failed: {str(e)}")
        return 4

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)