#!/usr/bin/env python3
"""
Business Logic Test Framework v1.0.0 - Clean Architecture
=========================================================

COMPREHENSIVE TESTING FRAMEWORK für alle Service Business Logic Tests:
- Unit Tests für Domain Logic
- Integration Tests für Service Interaction
- End-to-End Tests für Complete Workflows
- Performance Tests für Critical Paths
- Mock Framework für External Dependencies

CLEAN ARCHITECTURE TESTING PRINCIPLES:
✅ Domain Layer: Business Rules, Entities, Value Objects Tests
✅ Application Layer: Use Case Tests, Service Orchestration Tests
✅ Infrastructure Layer: Repository Tests, External API Tests
✅ Presentation Layer: Controller Tests, API Contract Tests

DESIGN PATTERNS:
- Test Factory Pattern: Automatische Test-Suite Generation
- Mock Strategy Pattern: Flexible Dependency Mocking
- Test Builder Pattern: Complex Test Scenario Building
- Test Observer Pattern: Real-time Test Result Monitoring

Code-Qualität: HÖCHSTE PRIORITÄT - Test-Driven Development Support
Autor: Claude Code - Test Framework Specialist
Datum: 25. August 2025
Version: 1.0.0
"""

import asyncio
import inspect
import json
import logging
import os
import sys
import time
import traceback
import unittest
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Callable, Type, Union
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from enum import Enum
import pytest
import aiohttp
import asyncpg

logger = logging.getLogger(__name__)

# =============================================================================
# TEST FRAMEWORK CORE CLASSES
# =============================================================================

class TestResult(Enum):
    """Test Result Status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class TestCategory(Enum):
    """Test Category Classifications"""
    UNIT = "unit"
    INTEGRATION = "integration"
    END_TO_END = "end_to_end"
    PERFORMANCE = "performance"
    SECURITY = "security"
    SMOKE = "smoke"

@dataclass
class TestReport:
    """Individual Test Report"""
    test_name: str
    category: TestCategory
    result: TestResult
    duration_ms: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class TestSuiteReport:
    """Complete Test Suite Report"""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    total_duration_ms: float
    test_reports: List[TestReport]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_tests == 0:
            return 100.0
        return (self.passed / self.total_tests) * 100.0

# =============================================================================
# BUSINESS LOGIC TEST FRAMEWORK BASE CLASSES
# =============================================================================

class BusinessLogicTestCase(ABC):
    """Base Class für Business Logic Tests"""
    
    def __init__(self, name: str, category: TestCategory = TestCategory.UNIT):
        self.name = name
        self.category = category
        self.setup_completed = False
        self.teardown_completed = False
        self.mocks: Dict[str, Mock] = {}
        
    async def setup(self):
        """Setup Test Environment"""
        self.setup_completed = True
        
    async def teardown(self):
        """Cleanup Test Environment"""
        # Clear all mocks
        for mock in self.mocks.values():
            if hasattr(mock, 'reset_mock'):
                mock.reset_mock()
        self.teardown_completed = True
    
    @abstractmethod
    async def execute(self) -> bool:
        """Execute Test Logic - Must be implemented by subclasses"""
        pass
    
    async def run(self) -> TestReport:
        """Run complete test with setup/teardown"""
        start_time = time.time()
        result = TestResult.PASSED
        error_message = None
        stack_trace = None
        
        try:
            await self.setup()
            
            if not self.setup_completed:
                raise RuntimeError("Setup was not completed properly")
            
            test_passed = await self.execute()
            
            if not test_passed:
                result = TestResult.FAILED
                error_message = f"Test {self.name} returned False"
                
        except Exception as e:
            result = TestResult.ERROR
            error_message = str(e)
            stack_trace = traceback.format_exc()
            logger.error(f"Test {self.name} failed with error: {e}")
            
        finally:
            try:
                await self.teardown()
            except Exception as e:
                logger.error(f"Teardown failed for {self.name}: {e}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return TestReport(
            test_name=self.name,
            category=self.category,
            result=result,
            duration_ms=duration_ms,
            error_message=error_message,
            stack_trace=stack_trace
        )
    
    def create_mock(self, name: str, spec: Optional[Type] = None, **kwargs) -> Mock:
        """Create and store a mock object"""
        if spec and asyncio.iscoroutinefunction(getattr(spec, '__call__', None)):
            mock_obj = AsyncMock(spec=spec, **kwargs)
        else:
            mock_obj = Mock(spec=spec, **kwargs)
        
        self.mocks[name] = mock_obj
        return mock_obj
    
    def get_mock(self, name: str) -> Mock:
        """Retrieve stored mock object"""
        if name not in self.mocks:
            raise ValueError(f"Mock '{name}' not found")
        return self.mocks[name]

# =============================================================================
# SPECIALIZED TEST CASE CLASSES
# =============================================================================

class DomainLogicTestCase(BusinessLogicTestCase):
    """Domain Logic Test Cases"""
    
    def __init__(self, name: str):
        super().__init__(name, TestCategory.UNIT)
        
    async def setup(self):
        """Setup for domain logic tests"""
        await super().setup()
        # Domain tests typically don't need external dependencies

class ApplicationLogicTestCase(BusinessLogicTestCase):
    """Application Use Case Test Cases"""
    
    def __init__(self, name: str):
        super().__init__(name, TestCategory.INTEGRATION)
        
    async def setup(self):
        """Setup for application logic tests"""
        await super().setup()
        # Setup mocks for repositories and external services

class InfrastructureTestCase(BusinessLogicTestCase):
    """Infrastructure Layer Test Cases"""
    
    def __init__(self, name: str):
        super().__init__(name, TestCategory.INTEGRATION)
        self.db_connection: Optional[asyncpg.Connection] = None
        
    async def setup(self):
        """Setup for infrastructure tests"""
        await super().setup()
        # Setup test database connection if needed

class EndToEndTestCase(BusinessLogicTestCase):
    """End-to-End Workflow Test Cases"""
    
    def __init__(self, name: str):
        super().__init__(name, TestCategory.END_TO_END)
        self.http_session: Optional[aiohttp.ClientSession] = None
        
    async def setup(self):
        """Setup for E2E tests"""
        await super().setup()
        self.http_session = aiohttp.ClientSession()
        
    async def teardown(self):
        """Cleanup E2E test environment"""
        if self.http_session:
            await self.http_session.close()
        await super().teardown()

class PerformanceTestCase(BusinessLogicTestCase):
    """Performance Test Cases"""
    
    def __init__(self, name: str, max_duration_ms: float = 1000.0):
        super().__init__(name, TestCategory.PERFORMANCE)
        self.max_duration_ms = max_duration_ms
        
    async def run(self) -> TestReport:
        """Run performance test with duration check"""
        report = await super().run()
        
        # Check performance constraint
        if report.result == TestResult.PASSED and report.duration_ms > self.max_duration_ms:
            report.result = TestResult.FAILED
            report.error_message = f"Performance test exceeded {self.max_duration_ms}ms (took {report.duration_ms:.2f}ms)"
            
        return report

# =============================================================================
# TEST SUITE MANAGER
# =============================================================================

class BusinessLogicTestSuite:
    """Test Suite Manager für Business Logic Tests"""
    
    def __init__(self, name: str):
        self.name = name
        self.test_cases: List[BusinessLogicTestCase] = []
        self.setup_hooks: List[Callable] = []
        self.teardown_hooks: List[Callable] = []
        
    def add_test(self, test_case: BusinessLogicTestCase):
        """Add test case to suite"""
        self.test_cases.append(test_case)
        
    def add_tests(self, test_cases: List[BusinessLogicTestCase]):
        """Add multiple test cases"""
        self.test_cases.extend(test_cases)
        
    def add_setup_hook(self, hook: Callable):
        """Add setup hook that runs before all tests"""
        self.setup_hooks.append(hook)
        
    def add_teardown_hook(self, hook: Callable):
        """Add teardown hook that runs after all tests"""
        self.teardown_hooks.append(hook)
        
    async def run_all(self, parallel: bool = False) -> TestSuiteReport:
        """Run all tests in the suite"""
        logger.info(f"Running test suite: {self.name} ({len(self.test_cases)} tests)")
        
        start_time = time.time()
        
        # Run setup hooks
        for hook in self.setup_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook()
            else:
                hook()
        
        try:
            # Run tests
            if parallel:
                test_results = await asyncio.gather(
                    *[test_case.run() for test_case in self.test_cases],
                    return_exceptions=True
                )
                
                # Convert exceptions to error reports
                reports = []
                for i, result in enumerate(test_results):
                    if isinstance(result, Exception):
                        reports.append(TestReport(
                            test_name=self.test_cases[i].name,
                            category=self.test_cases[i].category,
                            result=TestResult.ERROR,
                            duration_ms=0.0,
                            error_message=str(result),
                            stack_trace=traceback.format_exception(type(result), result, result.__traceback__)
                        ))
                    else:
                        reports.append(result)
            else:
                reports = []
                for test_case in self.test_cases:
                    report = await test_case.run()
                    reports.append(report)
                    logger.info(f"Test {report.test_name}: {report.result.value} ({report.duration_ms:.2f}ms)")
                    
        finally:
            # Run teardown hooks
            for hook in self.teardown_hooks:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook()
                    else:
                        hook()
                except Exception as e:
                    logger.error(f"Teardown hook failed: {e}")
        
        # Calculate results
        total_duration_ms = (time.time() - start_time) * 1000
        passed = sum(1 for r in reports if r.result == TestResult.PASSED)
        failed = sum(1 for r in reports if r.result == TestResult.FAILED)
        skipped = sum(1 for r in reports if r.result == TestResult.SKIPPED)
        errors = sum(1 for r in reports if r.result == TestResult.ERROR)
        
        suite_report = TestSuiteReport(
            suite_name=self.name,
            total_tests=len(reports),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            total_duration_ms=total_duration_ms,
            test_reports=reports
        )
        
        logger.info(f"Test suite {self.name} completed: {passed}/{len(reports)} passed ({suite_report.success_rate:.1f}%)")
        
        return suite_report
    
    async def run_category(self, category: TestCategory) -> TestSuiteReport:
        """Run only tests of specific category"""
        filtered_tests = [tc for tc in self.test_cases if tc.category == category]
        if not filtered_tests:
            logger.warning(f"No tests found for category {category.value}")
            return TestSuiteReport(
                suite_name=f"{self.name} ({category.value})",
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                total_duration_ms=0.0,
                test_reports=[]
            )
        
        # Temporarily replace test cases
        original_tests = self.test_cases
        self.test_cases = filtered_tests
        
        try:
            report = await self.run_all()
            report.suite_name = f"{self.name} ({category.value})"
            return report
        finally:
            self.test_cases = original_tests

# =============================================================================
# TEST FACTORY AND UTILITIES
# =============================================================================

class TestFactory:
    """Factory für automatische Test-Generierung"""
    
    @staticmethod
    def create_api_endpoint_test(endpoint_url: str, method: str = "GET", 
                                expected_status: int = 200) -> EndToEndTestCase:
        """Create API endpoint test"""
        class APIEndpointTest(EndToEndTestCase):
            async def execute(self) -> bool:
                try:
                    if method.upper() == "GET":
                        async with self.http_session.get(endpoint_url) as response:
                            return response.status == expected_status
                    elif method.upper() == "POST":
                        async with self.http_session.post(endpoint_url) as response:
                            return response.status == expected_status
                    else:
                        return False
                except Exception:
                    return False
        
        return APIEndpointTest(f"API {method} {endpoint_url}")
    
    @staticmethod
    def create_database_connection_test(connection_string: str) -> InfrastructureTestCase:
        """Create database connection test"""
        class DatabaseConnectionTest(InfrastructureTestCase):
            async def execute(self) -> bool:
                try:
                    conn = await asyncpg.connect(connection_string)
                    result = await conn.fetchval("SELECT 1")
                    await conn.close()
                    return result == 1
                except Exception:
                    return False
        
        return DatabaseConnectionTest("Database Connection Test")
    
    @staticmethod
    def create_performance_test(test_function: Callable, 
                              max_duration_ms: float = 1000.0) -> PerformanceTestCase:
        """Create performance test wrapper"""
        class PerformanceTestWrapper(PerformanceTestCase):
            async def execute(self) -> bool:
                try:
                    if asyncio.iscoroutinefunction(test_function):
                        await test_function()
                    else:
                        test_function()
                    return True
                except Exception:
                    return False
        
        return PerformanceTestWrapper(
            f"Performance test: {test_function.__name__}", 
            max_duration_ms
        )

# =============================================================================
# REPORT GENERATORS
# =============================================================================

class TestReportGenerator:
    """Generate Test Reports in Various Formats"""
    
    @staticmethod
    def generate_json_report(report: TestSuiteReport, file_path: str):
        """Generate JSON test report"""
        report_data = {
            "suite_name": report.suite_name,
            "timestamp": report.timestamp.isoformat(),
            "summary": {
                "total_tests": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "errors": report.errors,
                "success_rate": report.success_rate,
                "total_duration_ms": report.total_duration_ms
            },
            "test_results": [
                {
                    "test_name": tr.test_name,
                    "category": tr.category.value,
                    "result": tr.result.value,
                    "duration_ms": tr.duration_ms,
                    "error_message": tr.error_message,
                    "timestamp": tr.timestamp.isoformat()
                }
                for tr in report.test_reports
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def generate_console_report(report: TestSuiteReport) -> str:
        """Generate console-friendly report"""
        lines = []
        lines.append(f"📊 Test Suite Report: {report.suite_name}")
        lines.append("=" * 60)
        lines.append(f"🕐 Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"⏱️  Total Duration: {report.total_duration_ms:.2f}ms")
        lines.append(f"📈 Success Rate: {report.success_rate:.1f}%")
        lines.append("")
        lines.append("📋 Summary:")
        lines.append(f"  ✅ Passed:  {report.passed}")
        lines.append(f"  ❌ Failed:  {report.failed}")
        lines.append(f"  ⚠️  Errors:  {report.errors}")
        lines.append(f"  ⏭️  Skipped: {report.skipped}")
        lines.append(f"  📊 Total:   {report.total_tests}")
        
        if report.failed > 0 or report.errors > 0:
            lines.append("\n❌ Failed/Error Tests:")
            for tr in report.test_reports:
                if tr.result in [TestResult.FAILED, TestResult.ERROR]:
                    lines.append(f"  - {tr.test_name} ({tr.category.value}): {tr.error_message}")
        
        return "\n".join(lines)

# =============================================================================
# EXAMPLE TEST IMPLEMENTATIONS
# =============================================================================

class ExampleDomainTest(DomainLogicTestCase):
    """Example Domain Logic Test"""
    
    def __init__(self):
        super().__init__("Example Domain Logic Test")
        
    async def execute(self) -> bool:
        # Example: Test business rule validation
        from decimal import Decimal
        
        # Business rule: Stock price must be positive
        price = Decimal("100.50")
        return price > 0

class ExampleApplicationTest(ApplicationLogicTestCase):
    """Example Application Logic Test"""
    
    def __init__(self):
        super().__init__("Example Application Use Case Test")
        
    async def setup(self):
        await super().setup()
        # Mock external repository
        self.mock_repo = self.create_mock("repository", AsyncMock)
        self.mock_repo.get_stock_price.return_value = Decimal("100.50")
        
    async def execute(self) -> bool:
        # Test use case with mocked dependencies
        price = await self.mock_repo.get_stock_price("AAPL")
        return price == Decimal("100.50")

# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def run_example_tests():
    """Run example tests to demonstrate framework"""
    suite = BusinessLogicTestSuite("Example Test Suite")
    
    # Add various test types
    suite.add_test(ExampleDomainTest())
    suite.add_test(ExampleApplicationTest())
    
    # Add factory-generated tests
    suite.add_test(TestFactory.create_api_endpoint_test("http://localhost:8080/health"))
    suite.add_test(TestFactory.create_performance_test(
        lambda: time.sleep(0.1), max_duration_ms=200.0
    ))
    
    # Run tests
    report = await suite.run_all()
    
    # Generate reports
    print(TestReportGenerator.generate_console_report(report))
    TestReportGenerator.generate_json_report(report, "/tmp/test_report.json")
    
    return report

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_example_tests())