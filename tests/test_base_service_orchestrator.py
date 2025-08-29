#!/usr/bin/env python3
"""
TEST-AGENT für Issue #61 - BaseServiceOrchestrator Funktionalitäts-Tests

TEST-KATEGORIEN:
1. Unit Tests - BaseServiceOrchestrator Klasse isoliert testen
2. Integration Tests - Template Method Pattern Funktionalität
3. Backward Compatibility - Legacy Services weiterhin funktionsfähig
4. Performance Tests - Startup-Zeit, Memory-Usage, Response-Zeit
5. Edge Cases - Error-Handling, Graceful Shutdown, Invalid Config
"""

import asyncio
import pytest
import time
import psutil
import os
import sys
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Setup Path for Testing
sys.path.insert(0, '/home/mdoehler/aktienanalyse-ökosystem')

# Import Test Subject
from shared.service_base import BaseServiceOrchestrator, ServiceConfig, BaseService, ModularService


# =============================================================================
# TEST SERVICE IMPLEMENTATIONS
# =============================================================================

class TestServiceImplementation(BaseServiceOrchestrator):
    """Test Implementation of BaseServiceOrchestrator"""
    
    def __init__(self, config: ServiceConfig):
        super().__init__(config)
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
    
    def configure_service(self):
        pass
    
    def register_routes(self):
        pass
    
    async def startup_hook(self):
        raise RuntimeError("Simulated startup failure")


# =============================================================================
# UNIT TESTS - BaseServiceOrchestrator Klasse isoliert testen
# =============================================================================

class TestBaseServiceOrchestratorUnitTests:
    """Unit Tests für BaseServiceOrchestrator"""
    
    def test_service_config_creation(self):
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
        assert config.cors_origins == ["*"]
        assert config.health_endpoint == "/health"
    
    def test_service_config_defaults(self):
        """Test ServiceConfig Default Values"""
        config = ServiceConfig(service_name="minimal-service")
        
        assert config.version == "1.0.0"
        assert config.description == ""
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.log_level == "INFO"
        assert config.cors_credentials is True
        assert config.include_root_endpoint is True
    
    def test_orchestrator_initialization(self):
        """Test BaseServiceOrchestrator Initialization"""
        config = ServiceConfig(service_name="test-service")
        service = TestServiceImplementation(config)
        
        assert service.config == config
        assert service.app is None  # Not created yet
        assert service.logger is not None
        assert service.is_healthy is False
        assert service.startup_timestamp is None
        assert len(service._modules) == 0
        assert len(service._background_tasks) == 0
    
    def test_logging_setup(self):
        """Test Logging Configuration"""
        config = ServiceConfig(service_name="test-logging", log_level="ERROR")
        service = TestServiceImplementation(config)
        
        assert service.logger.name == "test-logging"
        # Note: Level checking might vary based on system configuration
    
    def test_module_registration(self):
        """Test Module Registration System"""
        config = ServiceConfig(service_name="test-modules")
        service = TestServiceImplementation(config)
        
        test_module = {"status": "active", "version": "1.0"}
        service.register_module("test_module", test_module)
        
        assert "test_module" in service._modules
        assert service.get_module("test_module") == test_module
        assert service.get_module("nonexistent") is None


# =============================================================================
# INTEGRATION TESTS - Template Method Pattern Funktionalität
# =============================================================================

class TestTemplateMethodPatternIntegration:
    """Integration Tests für Template Method Pattern"""
    
    def test_app_creation_template_method(self):
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
    
    @pytest.mark.asyncio
    async def test_startup_template_method(self):
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
    
    @pytest.mark.asyncio
    async def test_shutdown_template_method(self):
        """Test Shutdown Template Method Execution"""
        config = ServiceConfig(service_name="shutdown-test")
        service = TestServiceImplementation(config)
        service.create_app()
        
        # Simulate startup first
        await service._startup_event()
        
        # Test shutdown
        await service._shutdown_event()
        
        assert service.shutdown_called is True
        assert service.is_healthy is False
    
    @pytest.mark.asyncio
    async def test_health_check_template_method(self):
        """Test Health Check Template Method"""
        config = ServiceConfig(service_name="health-test")
        service = TestServiceImplementation(config)
        app = service.create_app()
        
        # Simulate startup
        await service._startup_event()
        
        # Extract health endpoint
        health_route = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == "/health":
                health_route = route
                break
        
        assert health_route is not None
        
        # Test health endpoint execution (mock request)
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "health-test"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        
        # Verify custom health details
        assert service.health_details_called is True
        assert data["test_module_status"] == "active"
        assert data["custom_health_info"] == "all_systems_operational"


# =============================================================================
# BACKWARD COMPATIBILITY TESTS - Legacy Services weiterhin funktionsfähig
# =============================================================================

class TestBackwardCompatibility:
    """Backward Compatibility Tests für Legacy Services"""
    
    def test_base_service_legacy_interface(self):
        """Test Legacy BaseService Interface"""
        # Verify BaseService still exists and works
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
    
    def test_modular_service_legacy_interface(self):
        """Test Legacy ModularService Interface"""
        service = ModularService("modular-legacy-test")
        
        assert service.service_name == "modular-legacy-test"
        assert service.is_running is False
        assert service.modules == {}
        assert service.app is not None
        assert service.app.title == "modular-legacy-test"
        
        # Test module registration
        test_module = Mock()
        service.register_module("test_module", test_module)
        
        assert "test_module" in service.modules
        assert service.modules["test_module"] == test_module
    
    @pytest.mark.asyncio
    async def test_modular_service_lifecycle(self):
        """Test Legacy ModularService Lifecycle"""
        service = ModularService("lifecycle-test")
        
        # Mock module with lifecycle methods
        mock_module = Mock()
        mock_module.start = AsyncMock()
        mock_module.stop = AsyncMock()
        mock_module.health_check = AsyncMock(return_value={"status": "healthy"})
        
        service.register_module("mock_module", mock_module)
        
        # Test start
        await service.start()
        assert service.is_running is True
        mock_module.start.assert_called_once()
        
        # Test health check
        health = await service.health_check()
        assert health["service"] == "lifecycle-test"
        assert health["status"] == "healthy"
        assert health["running"] is True
        mock_module.health_check.assert_called_once()
        
        # Test stop
        await service.stop()
        assert service.is_running is False
        mock_module.stop.assert_called_once()


# =============================================================================
# PERFORMANCE TESTS - Startup-Zeit, Memory-Usage, Response-Zeit
# =============================================================================

class TestPerformanceMetrics:
    """Performance Tests für BaseServiceOrchestrator"""
    
    @pytest.mark.asyncio
    async def test_startup_performance(self):
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
        print(f"✅ Startup Performance: {startup_duration:.3f}s (Target: < 5s)")
    
    def test_memory_usage_baseline(self):
        """Test Memory Usage Baseline"""
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        config = ServiceConfig(service_name="memory-test")
        service = TestServiceImplementation(config)
        service.create_app()
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_overhead = current_memory - baseline_memory
        
        # TARGET: Memory Overhead < 100MB
        assert memory_overhead < 100, f"Memory overhead: {memory_overhead:.1f}MB, expected < 100MB"
        print(f"✅ Memory Overhead: {memory_overhead:.1f}MB (Target: < 100MB)")
    
    @pytest.mark.asyncio
    async def test_health_endpoint_response_time(self):
        """Test Health Endpoint Response Time"""
        config = ServiceConfig(service_name="response-time-test")
        service = TestServiceImplementation(config)
        app = service.create_app()
        await service._startup_event()
        
        from fastapi.testclient import TestClient
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
        print(f"✅ Health Response Time: {avg_response_time:.1f}ms (Target: < 100ms)")


# =============================================================================
# EDGE CASES TESTS - Error-Handling, Graceful Shutdown, Invalid Config
# =============================================================================

class TestEdgeCasesAndErrorHandling:
    """Edge Cases und Error Handling Tests"""
    
    @pytest.mark.asyncio
    async def test_startup_failure_handling(self):
        """Test Startup Failure Error Handling"""
        config = ServiceConfig(service_name="startup-failure-test")
        service = FailingServiceImplementation(config)
        service.create_app()
        
        with pytest.raises(RuntimeError, match="Service startup failed"):
            await service._startup_event()
        
        assert service.is_healthy is False
    
    @pytest.mark.asyncio
    async def test_shutdown_with_background_tasks(self):
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
        await service._shutdown_event()
        end_time = time.time()
        
        shutdown_duration = end_time - start_time
        
        # Should complete quickly due to task cancellation
        assert shutdown_duration < 2.0, f"Shutdown took {shutdown_duration:.2f}s, expected < 2s"
        assert all(task.done() or task.cancelled() for task in service._background_tasks)
        print(f"✅ Graceful Shutdown: {shutdown_duration:.3f}s (Background tasks handled)")
    
    def test_invalid_config_validation(self):
        """Test Invalid Configuration Handling"""
        # Test invalid log level
        with pytest.raises(Exception):  # Pydantic validation error
            ServiceConfig(service_name="", port=-1)  # Invalid values
    
    @pytest.mark.asyncio
    async def test_health_check_when_unhealthy(self):
        """Test Health Check when Service is Unhealthy"""
        config = ServiceConfig(service_name="unhealthy-test")
        service = TestServiceImplementation(config)
        app = service.create_app()
        
        # Don't call startup, service should be unhealthy
        assert service.is_healthy is False
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert data["status"] == "unhealthy"
    
    def test_abstract_methods_enforcement(self):
        """Test Abstract Methods sind enforced"""
        config = ServiceConfig(service_name="abstract-test")
        
        # Verify BaseServiceOrchestrator can't be instantiated directly
        with pytest.raises(TypeError):
            BaseServiceOrchestrator(config)  # Should fail due to abstract methods


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
    
    try:
        # 1. UNIT TESTS
        print("\n1️⃣ UNIT TESTS - BaseServiceOrchestrator Core Functionality")
        print("-" * 60)
        
        unit_test_suite = TestBaseServiceOrchestratorUnitTests()
        unit_results = []
        
        unit_tests = [
            "test_service_config_creation",
            "test_service_config_defaults", 
            "test_orchestrator_initialization",
            "test_logging_setup",
            "test_module_registration"
        ]
        
        for test_name in unit_tests:
            try:
                test_method = getattr(unit_test_suite, test_name)
                test_method()
                unit_results.append({"test": test_name, "status": "PASSED"})
                print(f"  ✅ {test_name}")
            except Exception as e:
                unit_results.append({"test": test_name, "status": "FAILED", "error": str(e)})
                print(f"  ❌ {test_name}: {str(e)}")
        
        test_results["categories"]["unit_tests"] = {
            "total": len(unit_tests),
            "passed": len([r for r in unit_results if r["status"] == "PASSED"]),
            "failed": len([r for r in unit_results if r["status"] == "FAILED"]),
            "results": unit_results
        }
        
        # 2. INTEGRATION TESTS  
        print("\n2️⃣ INTEGRATION TESTS - Template Method Pattern")
        print("-" * 60)
        
        integration_test_suite = TestTemplateMethodPatternIntegration()
        integration_results = []
        
        integration_tests = [
            ("test_app_creation_template_method", False),
            ("test_startup_template_method", True),
            ("test_shutdown_template_method", True),
            ("test_health_check_template_method", True)
        ]
        
        for test_name, is_async in integration_tests:
            try:
                test_method = getattr(integration_test_suite, test_name)
                if is_async:
                    asyncio.run(test_method())
                else:
                    test_method()
                integration_results.append({"test": test_name, "status": "PASSED"})
                print(f"  ✅ {test_name}")
            except Exception as e:
                integration_results.append({"test": test_name, "status": "FAILED", "error": str(e)})
                print(f"  ❌ {test_name}: {str(e)}")
        
        test_results["categories"]["integration_tests"] = {
            "total": len(integration_tests),
            "passed": len([r for r in integration_results if r["status"] == "PASSED"]),
            "failed": len([r for r in integration_results if r["status"] == "FAILED"]),
            "results": integration_results
        }
        
        # 3. BACKWARD COMPATIBILITY
        print("\n3️⃣ BACKWARD COMPATIBILITY - Legacy Services")
        print("-" * 60)
        
        compatibility_test_suite = TestBackwardCompatibility()
        compatibility_results = []
        
        compatibility_tests = [
            ("test_base_service_legacy_interface", False),
            ("test_modular_service_legacy_interface", False),
            ("test_modular_service_lifecycle", True)
        ]
        
        for test_name, is_async in compatibility_tests:
            try:
                test_method = getattr(compatibility_test_suite, test_name)
                if is_async:
                    asyncio.run(test_method())
                else:
                    test_method()
                compatibility_results.append({"test": test_name, "status": "PASSED"})
                print(f"  ✅ {test_name}")
            except Exception as e:
                compatibility_results.append({"test": test_name, "status": "FAILED", "error": str(e)})
                print(f"  ❌ {test_name}: {str(e)}")
        
        test_results["categories"]["backward_compatibility"] = {
            "total": len(compatibility_tests),
            "passed": len([r for r in compatibility_results if r["status"] == "PASSED"]),
            "failed": len([r for r in compatibility_results if r["status"] == "FAILED"]),
            "results": compatibility_results
        }
        
        # 4. PERFORMANCE TESTS
        print("\n4️⃣ PERFORMANCE TESTS - Benchmarks")
        print("-" * 60)
        
        performance_test_suite = TestPerformanceMetrics()
        performance_results = []
        perf_metrics = {}
        
        performance_tests = [
            ("test_startup_performance", True),
            ("test_memory_usage_baseline", False),
            ("test_health_endpoint_response_time", True)
        ]
        
        for test_name, is_async in performance_tests:
            try:
                test_method = getattr(performance_test_suite, test_name)
                if is_async:
                    asyncio.run(test_method())
                else:
                    test_method()
                performance_results.append({"test": test_name, "status": "PASSED"})
            except Exception as e:
                performance_results.append({"test": test_name, "status": "FAILED", "error": str(e)})
                print(f"  ❌ {test_name}: {str(e)}")
        
        test_results["categories"]["performance_tests"] = {
            "total": len(performance_tests),
            "passed": len([r for r in performance_results if r["status"] == "PASSED"]),
            "failed": len([r for r in performance_results if r["status"] == "FAILED"]),
            "results": performance_results
        }
        
        # 5. EDGE CASES
        print("\n5️⃣ EDGE CASES - Error Handling")
        print("-" * 60)
        
        edge_cases_test_suite = TestEdgeCasesAndErrorHandling()
        edge_case_results = []
        
        edge_case_tests = [
            ("test_startup_failure_handling", True),
            ("test_shutdown_with_background_tasks", True),
            ("test_invalid_config_validation", False),
            ("test_health_check_when_unhealthy", True),
            ("test_abstract_methods_enforcement", False)
        ]
        
        for test_name, is_async in edge_case_tests:
            try:
                test_method = getattr(edge_cases_test_suite, test_name)
                if is_async:
                    asyncio.run(test_method())
                else:
                    test_method()
                edge_case_results.append({"test": test_name, "status": "PASSED"})
                print(f"  ✅ {test_name}")
            except Exception as e:
                edge_case_results.append({"test": test_name, "status": "FAILED", "error": str(e)})
                print(f"  ❌ {test_name}: {str(e)}")
        
        test_results["categories"]["edge_cases"] = {
            "total": len(edge_case_tests),
            "passed": len([r for r in edge_case_results if r["status"] == "PASSED"]),
            "failed": len([r for r in edge_case_results if r["status"] == "FAILED"]),
            "results": edge_case_results
        }
        
    except Exception as e:
        print(f"❌ CRITICAL TEST FAILURE: {str(e)}")
        test_results["overall_status"] = "CRITICAL_FAILURE"
        test_results["recommendation"] = "DO_NOT_DEPLOY"
        return test_results
    
    # CALCULATE OVERALL RESULTS
    total_tests = sum(cat["total"] for cat in test_results["categories"].values())
    total_passed = sum(cat["passed"] for cat in test_results["categories"].values())
    total_failed = sum(cat["failed"] for cat in test_results["categories"].values())
    
    success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
    
    test_results["summary"] = {
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
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
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Duration: {summary['duration_seconds']:.2f}s")
    
    print(f"\n🎯 OVERALL STATUS: {results['overall_status']}")
    print(f"📋 RECOMMENDATION: {results['recommendation']}")
    
    # Export results
    import json
    with open("/home/mdoehler/aktienanalyse-ökosystem/test_base_service_orchestrator_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results exported to: test_base_service_orchestrator_results.json")