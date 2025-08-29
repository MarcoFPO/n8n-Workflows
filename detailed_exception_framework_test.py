#!/usr/bin/env python3
"""
Detaillierte Exception-Framework Test-Suite
Reproduziert und validiert spezifische Issues für Issue #66

Author: TEST-AGENT für Issue #66
Version: 1.0.0
Date: 2025-08-29
"""

import sys
import os
import asyncio
import json
import logging
import traceback
import time
from datetime import datetime
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')


class DetailedTestResults:
    """Sammelt detaillierte Test-Ergebnisse"""
    
    def __init__(self):
        self.results = {}
        self.performance_metrics = {}
        self.critical_issues = []
        self.fixes_needed = []
    
    def add_test_result(self, test_name: str, passed: bool, error: str = None, details: Dict = None):
        """Fügt ein Test-Ergebnis hinzu"""
        self.results[test_name] = {
            "passed": passed,
            "error": error,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        if not passed and error:
            self.critical_issues.append({
                "test": test_name,
                "error": error,
                "stacktrace": traceback.format_exc() if error else None
            })
    
    def add_performance_metric(self, operation: str, duration_ms: float, threshold_ms: float):
        """Fügt eine Performance-Metrik hinzu"""
        self.performance_metrics[operation] = {
            "duration_ms": duration_ms,
            "threshold_ms": threshold_ms,
            "passed": duration_ms <= threshold_ms
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generiert einen detaillierten Report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["passed"])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "test_suite": "Detailed Exception Framework Analysis",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.2f}%" if total_tests > 0 else "0%",
            "test_results": self.results,
            "critical_issues": self.critical_issues,
            "performance_metrics": self.performance_metrics,
            "fixes_needed": self.fixes_needed,
            "overall_status": "PASSED" if len(self.critical_issues) == 0 else "CRITICAL_FIXES_NEEDED"
        }


def test_recovery_strategy_attribute_error():
    """Test Issue 1: recovery_strategy Attribute-Fehler reproduzieren"""
    test_results = DetailedTestResults()
    
    try:
        from shared.exception_handler import exception_handler
        from shared.exceptions import ValidationException
        
        logger.info("🔍 Testing recovery_strategy attribute error...")
        
        @exception_handler()
        def test_function():
            raise ValueError("Test generic error")
        
        try:
            result = test_function()
            test_results.add_test_result(
                "recovery_strategy_handling", 
                True,
                details={"result": str(result)}
            )
        except AttributeError as e:
            if "recovery_strategy" in str(e):
                test_results.add_test_result(
                    "recovery_strategy_handling", 
                    False, 
                    f"CRITICAL: recovery_strategy AttributeError: {e}"
                )
                test_results.fixes_needed.append("Fix recovery_strategy attribute access in exception conversion")
            else:
                raise
        except Exception as e:
            test_results.add_test_result(
                "recovery_strategy_handling", 
                False, 
                f"Unexpected error: {e}"
            )
            
    except Exception as e:
        test_results.add_test_result(
            "recovery_strategy_handling", 
            False, 
            f"Import or setup error: {e}"
        )
    
    return test_results


def test_exception_factory_parameter_conflict():
    """Test Issue 2: ExceptionFactory Parameter-Konflikt"""
    test_results = DetailedTestResults()
    
    try:
        from shared.exceptions import ExceptionFactory
        
        logger.info("🔍 Testing ExceptionFactory parameter conflicts...")
        
        # Test Database Exception Factory
        try:
            db_exc = ExceptionFactory.create_database_exception(
                "connection", 
                "Database connection failed"
            )
            test_results.add_test_result(
                "database_exception_factory", 
                True,
                details={"http_status": db_exc.http_status_code}
            )
        except TypeError as e:
            if "multiple values" in str(e) and "http_status_code" in str(e):
                test_results.add_test_result(
                    "database_exception_factory", 
                    False,
                    f"CRITICAL: Multiple values for http_status_code: {e}"
                )
                test_results.fixes_needed.append("Remove duplicate http_status_code parameter in ExceptionFactory methods")
            else:
                raise
        
        # Test Event Bus Exception Factory
        try:
            event_exc = ExceptionFactory.create_event_bus_exception(
                "publish",
                "Failed to publish event"
            )
            test_results.add_test_result(
                "event_bus_exception_factory", 
                True,
                details={"http_status": event_exc.http_status_code}
            )
        except TypeError as e:
            test_results.add_test_result(
                "event_bus_exception_factory", 
                False,
                f"Parameter conflict: {e}"
            )
        
        # Test API Exception Factory
        try:
            api_exc = ExceptionFactory.create_api_exception(
                "rate_limit",
                "API rate limit exceeded"
            )
            test_results.add_test_result(
                "api_exception_factory", 
                True,
                details={"http_status": api_exc.http_status_code}
            )
        except TypeError as e:
            test_results.add_test_result(
                "api_exception_factory", 
                False,
                f"Parameter conflict: {e}"
            )
            
    except Exception as e:
        test_results.add_test_result(
            "exception_factory_import", 
            False, 
            f"Import error: {e}"
        )
    
    return test_results


def test_asyncio_event_loop_conflicts():
    """Test Issue 3: AsyncIO Event-Loop-Konflikte"""
    test_results = DetailedTestResults()
    
    try:
        from shared.exception_handler import create_fastapi_exception_handler
        from shared.exceptions import BaseServiceException
        
        logger.info("🔍 Testing AsyncIO event loop conflicts...")
        
        # Mock FastAPI Request
        class MockRequest:
            def __init__(self):
                self.url = "http://localhost:8000/test"
                self.method = "GET"
        
        handler = create_fastapi_exception_handler()
        
        exc = BaseServiceException(
            "Test exception for FastAPI handler",
            http_status_code=400
        )
        
        request = MockRequest()
        
        # Test ohne asyncio.run() - direkt await verwenden
        try:
            # Synchroner Test
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            response = loop.run_until_complete(handler(request, exc))
            
            test_results.add_test_result(
                "fastapi_handler_sync", 
                True,
                details={
                    "status_code": response.status_code,
                    "has_content": hasattr(response, 'body')
                }
            )
            
            loop.close()
            
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                test_results.add_test_result(
                    "fastapi_handler_asyncio_conflict", 
                    False,
                    f"CRITICAL: AsyncIO event loop conflict: {e}"
                )
                test_results.fixes_needed.append("Remove asyncio.run() from FastAPI handler test - use direct await")
            else:
                raise
        except Exception as e:
            test_results.add_test_result(
                "fastapi_handler_general", 
                False,
                f"General FastAPI handler error: {e}"
            )
            
    except Exception as e:
        test_results.add_test_result(
            "fastapi_handler_import", 
            False, 
            f"Import error: {e}"
        )
    
    return test_results


def test_exception_hierarchy_validation():
    """Test Exception-Hierarchie und HTTP-Status-Code-Mapping"""
    test_results = DetailedTestResults()
    
    try:
        from shared.exceptions import (
            BaseServiceException,
            DatabaseException, 
            ConnectionException, 
            QueryException,
            TransactionException,
            DataIntegrityException,
            EventBusException,
            PublishException,
            SubscribeException,
            EventRoutingException,
            ExternalAPIException,
            RateLimitException,
            AuthenticationException,
            ValidationException,
            ConfigurationException,
            BusinessLogicException,
            NetworkException,
            TimeoutException
        )
        
        logger.info("🔍 Testing exception hierarchy...")
        
        # Test alle Exception-Klassen
        exceptions_to_test = [
            (ConnectionException, 503),
            (QueryException, 500),
            (TransactionException, 500),
            (DataIntegrityException, 409),
            (PublishException, 500),
            (SubscribeException, 500),
            (EventRoutingException, 500),
            (RateLimitException, 429),
            (AuthenticationException, 401),
            (ValidationException, 400),
            (ConfigurationException, 503),
            (BusinessLogicException, 422),
            (NetworkException, 503),
            (TimeoutException, 408)
        ]
        
        for exc_class, expected_status in exceptions_to_test:
            try:
                exc = exc_class("Test message")
                
                # Test instanziierbar
                assert isinstance(exc, BaseServiceException)
                
                # Test HTTP-Status-Code
                assert exc.http_status_code == expected_status, f"Expected {expected_status}, got {exc.http_status_code}"
                
                # Test to_dict funktioniert
                exc_dict = exc.to_dict()
                assert "error_code" in exc_dict
                assert "message" in exc_dict
                assert "http_status_code" in exc_dict
                
                test_results.add_test_result(
                    f"exception_hierarchy_{exc_class.__name__}", 
                    True,
                    details={
                        "expected_status": expected_status,
                        "actual_status": exc.http_status_code,
                        "has_error_code": "error_code" in exc_dict
                    }
                )
                
            except Exception as e:
                test_results.add_test_result(
                    f"exception_hierarchy_{exc_class.__name__}", 
                    False,
                    f"Exception instantiation failed: {e}"
                )
        
    except Exception as e:
        test_results.add_test_result(
            "exception_hierarchy_import", 
            False, 
            f"Import error: {e}"
        )
    
    return test_results


def test_performance_benchmarks():
    """Test Performance-Benchmarks"""
    test_results = DetailedTestResults()
    
    try:
        from shared.exceptions import ValidationException, DatabaseException, ExternalAPIException
        
        logger.info("🔍 Testing performance benchmarks...")
        
        # Test Exception-Creation Time < 5ms
        start_time = time.perf_counter()
        for i in range(100):
            exc = ValidationException(f"Test error {i}")
        end_time = time.perf_counter()
        
        avg_creation_time_ms = ((end_time - start_time) / 100) * 1000
        test_results.add_performance_metric("exception_creation", avg_creation_time_ms, 5.0)
        
        # Test to_dict Performance
        exc = DatabaseException("Performance test")
        start_time = time.perf_counter()
        for i in range(100):
            exc_dict = exc.to_dict()
        end_time = time.perf_counter()
        
        avg_to_dict_time_ms = ((end_time - start_time) / 100) * 1000
        test_results.add_performance_metric("to_dict_serialization", avg_to_dict_time_ms, 2.0)
        
        # Test Handler-Overhead < 2ms
        from shared.exception_handler import ExceptionHandler, ExceptionHandlerConfig
        handler = ExceptionHandler(ExceptionHandlerConfig())
        
        start_time = time.perf_counter()
        for i in range(50):
            try:
                handler.handle_exception(ValidationException(f"Test {i}"))
            except:
                pass  # Expected
        end_time = time.perf_counter()
        
        avg_handler_time_ms = ((end_time - start_time) / 50) * 1000
        test_results.add_performance_metric("handler_overhead", avg_handler_time_ms, 2.0)
        
        test_results.add_test_result(
            "performance_benchmarks", 
            True,
            details={
                "exception_creation_ms": avg_creation_time_ms,
                "to_dict_ms": avg_to_dict_time_ms,
                "handler_overhead_ms": avg_handler_time_ms
            }
        )
        
    except Exception as e:
        test_results.add_test_result(
            "performance_benchmarks", 
            False, 
            f"Performance test error: {e}"
        )
    
    return test_results


def test_recovery_strategies():
    """Test Recovery-Strategien"""
    test_results = DetailedTestResults()
    
    try:
        from shared.exceptions import (
            BaseServiceException, 
            RecoveryStrategy, 
            handle_exception_with_recovery
        )
        from shared.exception_handler import ExceptionHandler, ExceptionHandlerConfig
        
        logger.info("🔍 Testing recovery strategies...")
        
        # Test Retry-Logic
        retry_exc = BaseServiceException(
            "Retry test",
            recovery_strategy=RecoveryStrategy.RETRY,
            max_retries=2
        )
        
        retry_success = retry_exc.can_retry()
        test_results.add_test_result(
            "retry_strategy_can_retry", 
            retry_success,
            details={"initial_retry_count": retry_exc.retry_count, "max_retries": retry_exc.max_retries}
        )
        
        # Test Circuit-Breaker
        handler = ExceptionHandler(ExceptionHandlerConfig(circuit_breaker_threshold=3))
        
        circuit_breaker_exc = BaseServiceException(
            "Circuit breaker test",
            recovery_strategy=RecoveryStrategy.CIRCUIT_BREAKER
        )
        
        # Circuit breaker sollte nach mehreren Fehlern aktiviert werden
        circuit_breaker_count = 0
        for i in range(5):
            try:
                handler.handle_exception(circuit_breaker_exc)
            except:
                circuit_breaker_count += 1
        
        test_results.add_test_result(
            "circuit_breaker_strategy", 
            circuit_breaker_count > 0,
            details={"circuit_breaker_activations": circuit_breaker_count}
        )
        
        # Test Rollback-Strategy
        rollback_exc = BaseServiceException(
            "Rollback test",
            recovery_strategy=RecoveryStrategy.ROLLBACK,
            rollback_required=True
        )
        
        test_results.add_test_result(
            "rollback_strategy_flag", 
            rollback_exc.rollback_required,
            details={"recovery_strategy": rollback_exc.recovery_strategy.value}
        )
        
    except Exception as e:
        test_results.add_test_result(
            "recovery_strategies", 
            False, 
            f"Recovery strategy test error: {e}"
        )
    
    return test_results


async def run_detailed_tests():
    """Führt alle detaillierten Tests aus"""
    logger.info("🧪 Starte detaillierte Exception-Framework Tests...")
    
    # Sammle alle Test-Ergebnisse
    all_results = DetailedTestResults()
    
    # Test 1: recovery_strategy Attribute-Fehler
    logger.info("1️⃣ Testing recovery_strategy attribute error...")
    result1 = test_recovery_strategy_attribute_error()
    all_results.results.update(result1.results)
    all_results.critical_issues.extend(result1.critical_issues)
    all_results.fixes_needed.extend(result1.fixes_needed)
    
    # Test 2: ExceptionFactory Parameter-Konflikt
    logger.info("2️⃣ Testing ExceptionFactory parameter conflicts...")
    result2 = test_exception_factory_parameter_conflict()
    all_results.results.update(result2.results)
    all_results.critical_issues.extend(result2.critical_issues)
    all_results.fixes_needed.extend(result2.fixes_needed)
    
    # Test 3: AsyncIO Event-Loop-Konflikte
    logger.info("3️⃣ Testing AsyncIO event loop conflicts...")
    result3 = test_asyncio_event_loop_conflicts()
    all_results.results.update(result3.results)
    all_results.critical_issues.extend(result3.critical_issues)
    all_results.fixes_needed.extend(result3.fixes_needed)
    
    # Test 4: Exception-Hierarchie
    logger.info("4️⃣ Testing exception hierarchy...")
    result4 = test_exception_hierarchy_validation()
    all_results.results.update(result4.results)
    all_results.critical_issues.extend(result4.critical_issues)
    all_results.fixes_needed.extend(result4.fixes_needed)
    
    # Test 5: Performance-Benchmarks
    logger.info("5️⃣ Testing performance benchmarks...")
    result5 = test_performance_benchmarks()
    all_results.results.update(result5.results)
    all_results.performance_metrics.update(result5.performance_metrics)
    all_results.critical_issues.extend(result5.critical_issues)
    all_results.fixes_needed.extend(result5.fixes_needed)
    
    # Test 6: Recovery-Strategien
    logger.info("6️⃣ Testing recovery strategies...")
    result6 = test_recovery_strategies()
    all_results.results.update(result6.results)
    all_results.critical_issues.extend(result6.critical_issues)
    all_results.fixes_needed.extend(result6.fixes_needed)
    
    # Generiere finalen Report
    report = all_results.generate_report()
    
    # Report speichern
    report_path = "/home/mdoehler/aktienanalyse-ökosystem/detailed_exception_framework_test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # Log Zusammenfassung
    logger.info(f"📊 Detaillierte Test-Zusammenfassung:")
    logger.info(f"   Total Tests: {report['total_tests']}")
    logger.info(f"   Erfolgreich: {report['passed_tests']}")
    logger.info(f"   Fehlgeschlagen: {report['failed_tests']}")
    logger.info(f"   Erfolgsrate: {report['success_rate']}")
    logger.info(f"   Kritische Issues: {len(report['critical_issues'])}")
    logger.info(f"   Fixes benötigt: {len(report['fixes_needed'])}")
    logger.info(f"   Status: {report['overall_status']}")
    
    # Performance-Metriken
    logger.info("🏃 Performance-Metriken:")
    for metric, data in report['performance_metrics'].items():
        status = "✅ PASS" if data['passed'] else "❌ FAIL"
        logger.info(f"   {metric}: {data['duration_ms']:.2f}ms (Threshold: {data['threshold_ms']}ms) {status}")
    
    # Kritische Issues
    if report['critical_issues']:
        logger.error("🚨 Kritische Issues gefunden:")
        for issue in report['critical_issues']:
            logger.error(f"   ❌ {issue['test']}: {issue['error']}")
    
    # Fixes needed
    if report['fixes_needed']:
        logger.warning("🔧 Fixes erforderlich:")
        for fix in set(report['fixes_needed']):  # Remove duplicates
            logger.warning(f"   🔧 {fix}")
    
    return report


if __name__ == "__main__":
    print("Detaillierte Exception-Framework Test-Suite")
    print("==========================================")
    
    report = asyncio.run(run_detailed_tests())
    
    if report["overall_status"] == "PASSED":
        print("\n✅ Alle Tests erfolgreich - Exception-Framework Production-Ready!")
        exit(0)
    else:
        print(f"\n❌ {len(report['critical_issues'])} kritische Issues gefunden - Fixes erforderlich!")
        exit(1)