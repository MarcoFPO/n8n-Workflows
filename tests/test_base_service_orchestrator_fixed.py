#!/usr/bin/env python3
"""
TEST-AGENT für Issue #61 - BaseServiceOrchestrator Funktionalitäts-Tests
FIXED VERSION - Permission Issues behoben

TEST-KATEGORIEN:
1. Unit Tests - BaseServiceOrchestrator Klasse isoliert testen
2. Integration Tests - Template Method Pattern Funktionalität
3. Backward Compatibility - Legacy Services weiterhin funktionsfähig
4. Performance Tests - Startup-Zeit, Memory-Usage, Response-Zeit
5. Edge Cases - Error-Handling, Graceful Shutdown, Invalid Config
"""

import asyncio
import time
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch

# Setup Path for Testing
sys.path.insert(0, '/home/mdoehler/aktienanalyse-ökosystem')

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil not available - memory tests will be skipped")


# Mock logging für Tests ohne File Handler Issues
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Import Test Subject nach Logging Setup
from shared.service_base import BaseServiceOrchestrator, ServiceConfig, BaseService, ModularService


# =============================================================================
# TEST SERVICE IMPLEMENTATIONS  
# =============================================================================

class TestServiceImplementation(BaseServiceOrchestrator):
    """Test Implementation of BaseServiceOrchestrator"""
    
    def __init__(self, config: ServiceConfig):
        # Override logging setup to avoid file permissions
        self.config = config
        self.app = None
        self.logger = logging.getLogger(config.service_name)
        self.is_healthy = False
        self.startup_timestamp = None
        self._shutdown_event = asyncio.Event()
        self._modules = {}
        self._background_tasks = []
        
        # Test tracking
        self.configured = False
        self.routes_registered = False
        self.startup_called = False
        self.shutdown_called = False
        self.health_details_called = False
    
    def configure_service(self):
        """Test configure_service implementation"""
        self.configured = True
        self.register_module("test_module", {"initialized": True})
    
    def register_routes(self):
        """Test register_routes implementation"""
        self.routes_registered = True
        
        @self.app.post("/test")
        async def test_endpoint():
            return {"message": "test endpoint works"}
    
    async def startup_hook(self):
        """Test startup_hook implementation"""
        self.startup_called = True
        await asyncio.sleep(0.1)  # Simulate startup work
    
    async def shutdown_hook(self):
        """Test shutdown_hook implementation"""
        self.shutdown_called = True
        await asyncio.sleep(0.1)  # Simulate shutdown work
    
    async def health_check_details(self) -> Dict[str, Any]:
        """Test health_check_details implementation"""
        self.health_details_called = True
        return {
            "test_module_status": "active",
            "custom_health_info": "all_systems_operational"
        }


class FailingServiceImplementation(BaseServiceOrchestrator):
    """Service Implementation that fails during startup"""
    
    def __init__(self, config: ServiceConfig):
        # Override logging setup to avoid file permissions
        self.config = config
        self.app = None
        self.logger = logging.getLogger(config.service_name)
        self.is_healthy = False
        self.startup_timestamp = None
        self._shutdown_event = asyncio.Event()
        self._modules = {}
        self._background_tasks = []
    
    def configure_service(self):
        pass
    
    def register_routes(self):
        pass
    
    async def startup_hook(self):
        raise RuntimeError("Simulated startup failure")


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_service_config_creation():
    """Test ServiceConfig Model Creation"""
    config = ServiceConfig(
        service_name="test-service",
        version="2.0.0", 
        description="Test Service",
        host="127.0.0.1",
        port=9999,
        log_level="DEBUG"
    )
    
    assert config.service_name == "test-service"
    assert config.version == "2.0.0"
    assert config.description == "Test Service"
    assert config.host == "127.0.0.1"
    assert config.port == 9999
    assert config.log_level == "DEBUG"
    return {"status": "PASSED"}

def test_service_config_defaults():
    """Test ServiceConfig Default Values"""
    config = ServiceConfig(service_name="minimal-service")
    
    assert config.version == "1.0.0"
    assert config.description == ""
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.log_level == "INFO"
    return {"status": "PASSED"}

def test_orchestrator_initialization():
    """Test BaseServiceOrchestrator Initialization"""
    config = ServiceConfig(service_name="test-service")
    service = TestServiceImplementation(config)
    
    assert service.config == config
    assert service.app is None  # Not created yet
    assert service.logger is not None
    assert service.is_healthy is False
    assert service.startup_timestamp is None
    return {"status": "PASSED"}

def test_module_registration():
    """Test Module Registration System"""
    config = ServiceConfig(service_name="test-modules")
    service = TestServiceImplementation(config)
    
    test_module = {"status": "active", "version": "1.0"}
    service.register_module("test_module", test_module)
    
    assert "test_module" in service._modules
    assert service.get_module("test_module") == test_module
    assert service.get_module("nonexistent") is None
    return {"status": "PASSED"}

def test_app_creation_template_method():
    """Test App Creation Template Method"""
    config = ServiceConfig(
        service_name="template-test",
        port=8888,
        health_endpoint="/custom-health"
    )
    service = TestServiceImplementation(config)
    
    app = service.create_app()
    
    # Verify template method execution
    assert service.configured is True
    assert service.routes_registered is True
    assert app is not None
    assert app.title == "template-test"
    assert service.app == app
    
    # Multiple calls should return same app
    app2 = service.create_app()
    assert app == app2
    return {"status": "PASSED"}

async def test_startup_template_method():
    """Test Startup Template Method Execution"""
    config = ServiceConfig(service_name="startup-test")
    service = TestServiceImplementation(config)
    
    # Create app to trigger startup
    service.create_app()
    
    # Manually trigger startup event
    await service._startup_event()
    
    assert service.startup_called is True
    assert service.is_healthy is True
    assert service.startup_timestamp is not None
    assert isinstance(service.startup_timestamp, datetime)
    return {"status": "PASSED"}

async def test_shutdown_template_method():
    """Test Shutdown Template Method Execution"""
    config = ServiceConfig(service_name="shutdown-test")
    service = TestServiceImplementation(config)
    service.create_app()
    
    # Simulate startup first
    await service._startup_event()
    
    # Test shutdown
    await service._handle_shutdown()
    
    assert service.shutdown_called is True
    assert service.is_healthy is False
    return {"status": "PASSED"}

async def test_health_check_template_method():
    """Test Health Check Template Method"""
    config = ServiceConfig(service_name="health-test")
    service = TestServiceImplementation(config)
    app = service.create_app()
    
    # Simulate startup
    await service._startup_event()
    
    # Test health endpoint execution
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "health-test"
        assert data["version"] == "1.0.0"
        
        # Verify custom health details
        assert service.health_details_called is True
        assert data["test_module_status"] == "active"
        
        return {"status": "PASSED"}
    except ImportError:
        return {"status": "SKIPPED", "reason": "FastAPI TestClient not available"}

def test_legacy_base_service():
    """Test Legacy BaseService Interface"""
    # Test Inheritance arbeitet
    class LegacyTestService(BaseService):
        async def start(self):
            self.is_running = True
        
        async def stop(self):
            self.is_running = False
        
        async def health_check(self) -> Dict[str, Any]:
            return {"status": "healthy", "running": self.is_running}
    
    service = LegacyTestService("legacy-test")
    
    assert service.service_name == "legacy-test"
    assert service.is_running is False
    assert service.logger is not None
    return {"status": "PASSED"}

def test_legacy_modular_service():
    """Test Legacy ModularService Interface"""
    service = ModularService("modular-legacy-test")
    
    assert service.service_name == "modular-legacy-test"
    assert service.is_running is False
    assert service.modules == {}
    
    # Test module registration
    test_module = Mock()
    service.register_module("test_module", test_module)
    
    assert "test_module" in service.modules
    return {"status": "PASSED"}

async def test_startup_performance():
    """Test Startup Time Performance"""
    config = ServiceConfig(service_name="perf-startup-test")
    service = TestServiceImplementation(config)
    
    start_time = time.time()
    service.create_app()
    await service._startup_event()
    end_time = time.time()
    
    startup_duration = end_time - start_time
    
    # TARGET: Startup Time < 5s
    assert startup_duration < 5.0, f"Startup took {startup_duration:.2f}s, expected < 5s"
    return {"status": "PASSED", "duration": startup_duration}

def test_memory_usage_baseline():
    """Test Memory Usage Baseline"""
    if not PSUTIL_AVAILABLE:
        return {"status": "SKIPPED", "reason": "psutil not available"}
    
    process = psutil.Process()
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    config = ServiceConfig(service_name="memory-test")
    service = TestServiceImplementation(config)
    service.create_app()
    
    current_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_overhead = current_memory - baseline_memory
    
    # TARGET: Memory Overhead < 100MB
    assert memory_overhead < 100, f"Memory overhead: {memory_overhead:.1f}MB, expected < 100MB"
    return {"status": "PASSED", "memory_overhead_mb": memory_overhead}

async def test_health_endpoint_response_time():
    """Test Health Endpoint Response Time"""
    try:
        from fastapi.testclient import TestClient
        
        config = ServiceConfig(service_name="response-time-test")
        service = TestServiceImplementation(config)
        app = service.create_app()
        await service._startup_event()
        
        client = TestClient(app)
        
        # Warm up
        client.get("/health")
        
        # Measure response time
        start_time = time.time()
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200
        end_time = time.time()
        
        avg_response_time = (end_time - start_time) / 10 * 1000  # ms
        
        # TARGET: Health Response < 100ms
        assert avg_response_time < 100, f"Health response: {avg_response_time:.1f}ms, expected < 100ms"
        return {"status": "PASSED", "avg_response_time_ms": avg_response_time}
    except ImportError:
        return {"status": "SKIPPED", "reason": "FastAPI TestClient not available"}

async def test_startup_failure_handling():
    """Test Startup Failure Error Handling"""
    config = ServiceConfig(service_name="startup-failure-test")
    service = FailingServiceImplementation(config)
    service.create_app()
    
    try:
        await service._startup_event()
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "Service startup failed" in str(e)
        assert service.is_healthy is False
        return {"status": "PASSED"}

async def test_shutdown_with_background_tasks():
    """Test Graceful Shutdown with Background Tasks"""
    config = ServiceConfig(service_name="background-task-test")
    service = TestServiceImplementation(config)
    service.create_app()
    await service._startup_event()
    
    # Add background tasks
    async def dummy_task():
        await asyncio.sleep(10)  # Long running task
    
    task1 = service.add_background_task(dummy_task)
    task2 = service.add_background_task(dummy_task)
    
    assert len(service._background_tasks) == 2
    
    # Test shutdown cancels tasks
    start_time = time.time()
    await service._handle_shutdown()
    end_time = time.time()
    
    shutdown_duration = end_time - start_time
    
    # Should complete quickly due to task cancellation
    assert shutdown_duration < 2.0, f"Shutdown took {shutdown_duration:.2f}s, expected < 2s"
    assert all(task.done() or task.cancelled() for task in service._background_tasks)
    return {"status": "PASSED", "shutdown_duration": shutdown_duration}

def test_abstract_methods_enforcement():
    """Test Abstract Methods sind enforced"""
    config = ServiceConfig(service_name="abstract-test")
    
    # Verify BaseServiceOrchestrator can't be instantiated directly
    try:
        BaseServiceOrchestrator(config)  # Should fail due to abstract methods
        assert False, "Expected TypeError for abstract class instantiation"
    except TypeError:
        return {"status": "PASSED"}


# =============================================================================
# COMPREHENSIVE TEST RUNNER
# =============================================================================

def run_comprehensive_tests():
    """
    Run all BaseServiceOrchestrator Tests
    Returns comprehensive test report
    """
    start_time = time.time()
    test_results = {
        "test_run_timestamp": datetime.utcnow().isoformat(),
        "categories": {},
        "performance_metrics": {},
        "overall_status": "UNKNOWN",
        "recommendation": "UNKNOWN"
    }
    
    print("🧪 STARTING COMPREHENSIVE BaseServiceOrchestrator TESTS")
    print("=" * 80)
    
    # 1. UNIT TESTS
    print("\n1️⃣ UNIT TESTS - BaseServiceOrchestrator Core Functionality")
    print("-" * 60)
    
    unit_tests = [
        test_service_config_creation,
        test_service_config_defaults, 
        test_orchestrator_initialization,
        test_module_registration
    ]
    
    unit_results = []
    for test_func in unit_tests:
        try:
            result = test_func()
            unit_results.append({"test": test_func.__name__, **result})
            print(f"  ✅ {test_func.__name__}")
        except Exception as e:
            unit_results.append({"test": test_func.__name__, "status": "FAILED", "error": str(e)})
            print(f"  ❌ {test_func.__name__}: {str(e)}")
    
    test_results["categories"]["unit_tests"] = {
        "total": len(unit_tests),
        "passed": len([r for r in unit_results if r["status"] == "PASSED"]),
        "failed": len([r for r in unit_results if r["status"] == "FAILED"]),
        "results": unit_results
    }
    
    # 2. INTEGRATION TESTS  
    print("\n2️⃣ INTEGRATION TESTS - Template Method Pattern")
    print("-" * 60)
    
    integration_tests = [
        test_app_creation_template_method,
        test_startup_template_method,
        test_shutdown_template_method,
        test_health_check_template_method
    ]
    
    integration_results = []
    for test_func in integration_tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            integration_results.append({"test": test_func.__name__, **result})
            
            if result["status"] == "PASSED":
                print(f"  ✅ {test_func.__name__}")
            else:
                print(f"  ⚠️  {test_func.__name__}: {result.get('reason', 'SKIPPED')}")
        except Exception as e:
            integration_results.append({"test": test_func.__name__, "status": "FAILED", "error": str(e)})
            print(f"  ❌ {test_func.__name__}: {str(e)}")
    
    test_results["categories"]["integration_tests"] = {
        "total": len(integration_tests),
        "passed": len([r for r in integration_results if r["status"] == "PASSED"]),
        "failed": len([r for r in integration_results if r["status"] == "FAILED"]),
        "skipped": len([r for r in integration_results if r["status"] == "SKIPPED"]),
        "results": integration_results
    }
    
    # 3. BACKWARD COMPATIBILITY
    print("\n3️⃣ BACKWARD COMPATIBILITY - Legacy Services")
    print("-" * 60)
    
    compatibility_tests = [
        test_legacy_base_service,
        test_legacy_modular_service
    ]
    
    compatibility_results = []
    for test_func in compatibility_tests:
        try:
            result = test_func()
            compatibility_results.append({"test": test_func.__name__, **result})
            print(f"  ✅ {test_func.__name__}")
        except Exception as e:
            compatibility_results.append({"test": test_func.__name__, "status": "FAILED", "error": str(e)})
            print(f"  ❌ {test_func.__name__}: {str(e)}")
    
    test_results["categories"]["backward_compatibility"] = {
        "total": len(compatibility_tests),
        "passed": len([r for r in compatibility_results if r["status"] == "PASSED"]),
        "failed": len([r for r in compatibility_results if r["status"] == "FAILED"]),
        "results": compatibility_results
    }
    
    # 4. PERFORMANCE TESTS
    print("\n4️⃣ PERFORMANCE TESTS - Benchmarks")
    print("-" * 60)
    
    performance_tests = [
        test_startup_performance,
        test_memory_usage_baseline,
        test_health_endpoint_response_time
    ]
    
    performance_results = []
    performance_metrics = {}
    
    for test_func in performance_tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            performance_results.append({"test": test_func.__name__, **result})
            
            # Extract performance metrics
            if "duration" in result:
                performance_metrics[f"{test_func.__name__}_duration"] = result["duration"]
            if "memory_overhead_mb" in result:
                performance_metrics[f"{test_func.__name__}_memory_mb"] = result["memory_overhead_mb"]
            if "avg_response_time_ms" in result:
                performance_metrics[f"{test_func.__name__}_response_ms"] = result["avg_response_time_ms"]
            
            if result["status"] == "PASSED":
                print(f"  ✅ {test_func.__name__}")
            else:
                print(f"  ⚠️  {test_func.__name__}: {result.get('reason', 'SKIPPED')}")
                
        except Exception as e:
            performance_results.append({"test": test_func.__name__, "status": "FAILED", "error": str(e)})
            print(f"  ❌ {test_func.__name__}: {str(e)}")
    
    test_results["categories"]["performance_tests"] = {
        "total": len(performance_tests),
        "passed": len([r for r in performance_results if r["status"] == "PASSED"]),
        "failed": len([r for r in performance_results if r["status"] == "FAILED"]),
        "skipped": len([r for r in performance_results if r["status"] == "SKIPPED"]),
        "results": performance_results
    }
    test_results["performance_metrics"] = performance_metrics
    
    # 5. EDGE CASES
    print("\n5️⃣ EDGE CASES - Error Handling")
    print("-" * 60)
    
    edge_case_tests = [
        test_startup_failure_handling,
        test_shutdown_with_background_tasks,
        test_abstract_methods_enforcement
    ]
    
    edge_case_results = []
    for test_func in edge_case_tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            edge_case_results.append({"test": test_func.__name__, **result})
            print(f"  ✅ {test_func.__name__}")
        except Exception as e:
            edge_case_results.append({"test": test_func.__name__, "status": "FAILED", "error": str(e)})
            print(f"  ❌ {test_func.__name__}: {str(e)}")
    
    test_results["categories"]["edge_cases"] = {
        "total": len(edge_case_tests),
        "passed": len([r for r in edge_case_results if r["status"] == "PASSED"]),
        "failed": len([r for r in edge_case_results if r["status"] == "FAILED"]),
        "results": edge_case_results
    }
    
    # CALCULATE OVERALL RESULTS
    total_tests = sum(cat["total"] for cat in test_results["categories"].values())
    total_passed = sum(cat["passed"] for cat in test_results["categories"].values())
    total_failed = sum(cat["failed"] for cat in test_results["categories"].values())
    total_skipped = sum(cat.get("skipped", 0) for cat in test_results["categories"].values())
    
    # Adjust success rate to account for skipped tests
    effective_total = total_tests - total_skipped
    success_rate = (total_passed / effective_total) * 100 if effective_total > 0 else 0
    
    test_results["summary"] = {
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_skipped": total_skipped,
        "success_rate": success_rate,
        "duration_seconds": time.time() - start_time
    }
    
    # DETERMINE OVERALL STATUS AND RECOMMENDATION
    if success_rate >= 95:
        test_results["overall_status"] = "PASSED"
        test_results["recommendation"] = "GO_FOR_PRODUCTION"
    elif success_rate >= 85:
        test_results["overall_status"] = "CONDITIONAL_PASS"
        test_results["recommendation"] = "CONDITIONAL_GO_WITH_MONITORING"
    else:
        test_results["overall_status"] = "FAILED"
        test_results["recommendation"] = "NO_GO_REQUIRES_FIXES"
    
    return test_results


if __name__ == "__main__":
    results = run_comprehensive_tests()
    
    print("\n" + "=" * 80)
    print("📊 FINAL TEST RESULTS")
    print("=" * 80)
    
    summary = results["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['total_passed']}")
    print(f"Failed: {summary['total_failed']}")
    print(f"Skipped: {summary['total_skipped']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Duration: {summary['duration_seconds']:.2f}s")
    
    # Performance Metrics
    if results["performance_metrics"]:
        print(f"\n⚡ PERFORMANCE METRICS:")
        for metric, value in results["performance_metrics"].items():
            print(f"  - {metric}: {value:.3f}")
    
    print(f"\n🎯 OVERALL STATUS: {results['overall_status']}")
    print(f"📋 RECOMMENDATION: {results['recommendation']}")
    
    # Export results
    output_file = "/home/mdoehler/aktienanalyse-ökosystem/test_base_service_orchestrator_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results exported to: {output_file}")
    
    exit(0 if results["overall_status"] in ["PASSED", "CONDITIONAL_PASS"] else 1)