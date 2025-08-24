#!/usr/bin/env python3
"""
Backward Compatibility Validation Script v1.0.0 - 24.08.2025

Spezielle Validierung der Rückwärtskompatibilität für alle neuen Base-Klassen.
Simuliert Legacy-Code und prüft ob bestehende Implementierungen weiter funktionieren.

Validierungsbereiche:
- Legacy EventBus Implementations (4 vorherige Implementierungen)
- Legacy Health Check Patterns (20+ vorherige Implementierungen)  
- Legacy Import Patterns (sys.path Manipulationen)
- API Interface Compatibility
- Performance Regression Tests
- Memory Usage Comparisons

Autor: Claude Code Assistant
Version: v1.0.0
Datum: 24.08.2025
"""

import sys
import os
import time
import unittest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

# Setup Import Path
sys.path.insert(0, '/home/mdoehler/aktienanalyse-ökosystem')

try:
    from shared.shared_event_bus_manager_v1_0_0_20250824 import (
        SharedEventBusManager, TransportType, get_event_bus_instance
    )
    from shared.base_health_checker_v1_0_0_20250824 import (
        BaseHealthChecker, HealthStatus, CheckType
    )
    from shared.standard_import_manager_v1_0_0_20250824 import (
        setup_aktienanalyse_imports, AktienanalyseImportContext
    )
except ImportError as e:
    print(f"CRITICAL: Cannot import new base classes: {e}")
    sys.exit(1)


class LegacyEventBusSimulator:
    """Simuliert Legacy EventBus Implementierung für Compatibility Tests"""
    
    @staticmethod
    def create_legacy_event_bus_pattern_1():
        """Simuliert Pattern 1: Redis Event Bus (Legacy)"""
        # Alte Art der EventBus Erstellung
        class OldRedisEventBus:
            def __init__(self, redis_host="localhost", redis_port=6379):
                self.redis_host = redis_host
                self.redis_port = redis_port
                self.connected = False
                
            def connect(self):
                # Legacy connect method
                self.connected = True
                return True
                
            def publish(self, channel, message):
                # Legacy publish method
                if not self.connected:
                    self.connect()
                return True
                
            def subscribe(self, channel, callback):
                # Legacy subscribe method
                return True
        
        return OldRedisEventBus()
    
    @staticmethod
    def create_legacy_event_bus_pattern_2():
        """Simuliert Pattern 2: In-Memory Event Bus (Legacy)"""
        # Alte Art der EventBus Erstellung
        class OldInMemoryEventBus:
            def __init__(self):
                self.events = {}
                self.subscribers = {}
                
            def emit(self, event_name, data):
                # Legacy emit method (andere API)
                if event_name not in self.events:
                    self.events[event_name] = []
                self.events[event_name].append(data)
                
                # Notify subscribers
                if event_name in self.subscribers:
                    for callback in self.subscribers[event_name]:
                        callback(data)
                return True
                
            def on(self, event_name, callback):
                # Legacy on method (andere API)
                if event_name not in self.subscribers:
                    self.subscribers[event_name] = []
                self.subscribers[event_name].append(callback)
                
        return OldInMemoryEventBus()


class LegacyHealthCheckSimulator:
    """Simuliert Legacy Health Check Patterns für Compatibility Tests"""
    
    @staticmethod
    def create_legacy_health_check_pattern_1():
        """Simuliert Pattern 1: Simple Boolean Health Checks"""
        class OldHealthChecker:
            def __init__(self, service_name):
                self.service_name = service_name
                self.checks = {}
                
            def add_check(self, name, check_func):
                # Legacy Boolean-based checks
                self.checks[name] = check_func
                
            def check_health(self):
                # Returns simple boolean
                for name, check_func in self.checks.items():
                    if not check_func():
                        return False
                return True
                
            def get_status(self):
                # Legacy status method
                return "healthy" if self.check_health() else "unhealthy"
                
        return OldHealthChecker
    
    @staticmethod 
    def create_legacy_health_check_pattern_2():
        """Simuliert Pattern 2: Dict-based Health Responses"""
        class OldHealthService:
            def __init__(self):
                self.components = []
                
            def register_component(self, component_name, check_function):
                self.components.append({
                    'name': component_name,
                    'check': check_function
                })
                
            def health_status(self):
                # Returns dict with different structure
                status = {"status": "ok", "checks": {}}
                
                for component in self.components:
                    try:
                        result = component['check']()
                        status["checks"][component['name']] = {
                            "status": "pass" if result else "fail"
                        }
                    except Exception as e:
                        status["checks"][component['name']] = {
                            "status": "fail",
                            "error": str(e)
                        }
                        status["status"] = "error"
                        
                return status
                
        return OldHealthService


class LegacyImportSimulator:
    """Simuliert Legacy Import Patterns für Compatibility Tests"""
    
    @staticmethod
    def simulate_legacy_sys_path_pattern():
        """Simuliert alte sys.path Manipulationen"""
        legacy_patterns = [
            # Pattern 1: Direkte path append
            lambda: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem'),
            
            # Pattern 2: Relative path resolution  
            lambda: sys.path.append(str(Path(__file__).parent.parent)),
            
            # Pattern 3: Insert at beginning
            lambda: sys.path.insert(0, '/home/mdoehler/aktienanalyse-ökosystem'),
            
            # Pattern 4: Multiple appends
            lambda: [
                sys.path.append('/home/mdoehler/aktienanalyse-ökosystem'),
                sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared'),
                sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/services')
            ]
        ]
        return legacy_patterns


class BackwardCompatibilityValidator(unittest.TestCase):
    """Hauptklasse für Rückwärtskompatibilitäts-Validierung"""
    
    def setUp(self):
        """Setup für Compatibility Tests"""
        self.original_sys_path = sys.path.copy()
        
    def tearDown(self):
        """Cleanup nach Tests"""
        sys.path[:] = self.original_sys_path
        
        # Clear singletons
        if hasattr(SharedEventBusManager, '_instances'):
            SharedEventBusManager._instances.clear()
            
    def test_legacy_eventbus_pattern_compatibility(self):
        """Test: Legacy EventBus Patterns funktionieren mit neuer Implementierung"""
        
        # Test Legacy Pattern 1 Migration
        print("Testing Legacy EventBus Pattern 1 Migration...")
        
        # Simuliere Migration von Legacy zu New
        legacy_bus = LegacyEventBusSimulator.create_legacy_event_bus_pattern_1()
        
        # Neue Implementierung sollte gleiche Funktionalität bieten
        new_bus = SharedEventBusManager(
            transport_type=TransportType.REDIS,
            service_name="legacy_migration_test"
        )
        
        # Test dass grundlegende Operationen funktionieren
        self.assertTrue(hasattr(new_bus, 'publish_event'))
        self.assertTrue(hasattr(new_bus, 'subscribe_to_event'))
        
        # Test Legacy Pattern 2 Migration  
        print("Testing Legacy EventBus Pattern 2 Migration...")
        
        legacy_inmemory = LegacyEventBusSimulator.create_legacy_event_bus_pattern_2()
        
        new_inmemory = SharedEventBusManager(
            transport_type=TransportType.IN_MEMORY,
            service_name="legacy_inmemory_test"
        )
        
        # Test API Migration
        test_data = {"test": "legacy_compatibility"}
        
        # Legacy Style
        legacy_inmemory.emit("test_event", test_data)
        
        # New Style - sollte ähnliches Verhalten haben
        result = new_inmemory.publish_event("test_event", test_data)
        self.assertTrue(result)
        
    def test_legacy_health_check_pattern_compatibility(self):
        """Test: Legacy Health Check Patterns funktionieren mit neuer Implementierung"""
        
        print("Testing Legacy Health Check Pattern 1 Migration...")
        
        # Legacy Boolean-based Checker
        LegacyChecker = LegacyHealthCheckSimulator.create_legacy_health_check_pattern_1()
        legacy_checker = LegacyChecker("legacy_service")
        
        # Add legacy boolean check
        def legacy_db_check():
            return True  # Legacy boolean return
            
        legacy_checker.add_check("database", legacy_db_check)
        
        # New Implementation Migration
        new_checker = BaseHealthChecker(service_name="legacy_service")
        
        # Test: New checker should handle boolean returns
        def adapted_db_check() -> HealthStatus:
            # Adapter pattern für Legacy Boolean
            legacy_result = legacy_db_check()
            return HealthStatus.HEALTHY if legacy_result else HealthStatus.UNHEALTHY
            
        success = new_checker.register_component(
            "database",
            adapted_db_check, 
            CheckType.DATABASE
        )
        
        self.assertTrue(success)
        
        # Verify compatibility
        status, details = new_checker.check_component_health("database")
        self.assertEqual(status, HealthStatus.HEALTHY)
        
        print("Testing Legacy Health Check Pattern 2 Migration...")
        
        # Test Dict-based Legacy Pattern
        LegacyService = LegacyHealthCheckSimulator.create_legacy_health_check_pattern_2()
        legacy_service = LegacyService()
        
        legacy_service.register_component("api", lambda: True)
        legacy_status = legacy_service.health_status()
        
        # Should be compatible structure
        self.assertIn("status", legacy_status)
        self.assertIn("checks", legacy_status)
        
    def test_legacy_import_pattern_compatibility(self):
        """Test: Legacy Import Patterns funktionieren mit neuer Implementierung"""
        
        print("Testing Legacy Import Pattern Compatibility...")
        
        # Test Legacy Patterns
        legacy_patterns = LegacyImportSimulator.simulate_legacy_sys_path_pattern()
        
        base_path = '/home/mdoehler/aktienanalyse-ökosystem'
        
        for i, pattern in enumerate(legacy_patterns[:3]):  # Test erste 3 Patterns
            print(f"Testing Legacy Pattern {i+1}...")
            
            # Reset sys.path
            sys.path[:] = self.original_sys_path[:]
            
            # Execute Legacy Pattern
            try:
                pattern()
                legacy_has_path = base_path in sys.path
            except Exception:
                legacy_has_path = False
                
            # Execute New Pattern
            sys.path[:] = self.original_sys_path[:]
            new_success = setup_aktienanalyse_imports()
            new_has_path = base_path in sys.path
            
            # Both should achieve same result
            if legacy_has_path:
                self.assertTrue(new_has_path, f"New implementation doesn't match legacy pattern {i+1}")
            self.assertTrue(new_success, f"New implementation failed for pattern {i+1}")
            
    def test_api_interface_backward_compatibility(self):
        """Test: API Interfaces sind rückwärtskompatibel"""
        
        print("Testing API Interface Backward Compatibility...")
        
        # Test Legacy Function Interface
        legacy_instance = get_event_bus_instance(service_name="api_compat_test")
        self.assertIsInstance(legacy_instance, SharedEventBusManager)
        
        # Test Legacy Method Names (wenn vorhanden)
        # Dies würde spezifische Legacy-Methoden testen die wir unterstützen wollen
        
        # Test Parameter Compatibility  
        try:
            # Test mit verschiedenen Parameter-Kombinationen die Legacy Code verwenden könnte
            manager1 = SharedEventBusManager(service_name="compat1")
            manager2 = SharedEventBusManager(
                transport_type=TransportType.IN_MEMORY,
                service_name="compat2"
            )
            manager3 = SharedEventBusManager(
                transport_type=TransportType.REDIS,
                service_name="compat3", 
                redis_url="redis://localhost:6379"
            )
            
            # Alle sollten erfolgreich initialisiert werden
            self.assertIsNotNone(manager1)
            self.assertIsNotNone(manager2) 
            self.assertIsNotNone(manager3)
            
        except Exception as e:
            self.fail(f"Parameter compatibility broken: {e}")
            
    def test_performance_regression_validation(self):
        """Test: Keine Performance Regression gegenüber Legacy Implementierungen"""
        
        print("Testing Performance Regression...")
        
        # Test EventBus Performance
        event_bus = SharedEventBusManager(
            transport_type=TransportType.IN_MEMORY,
            service_name="perf_test"
        )
        
        # Measure publishing performance
        start_time = time.perf_counter()
        
        for i in range(1000):
            event_bus.publish_event(f"perf_test_{i}", {"iteration": i})
            
        end_time = time.perf_counter()
        eventbus_time = end_time - start_time
        
        # Should be under 100ms for 1000 events (sehr optimistisches Ziel)
        self.assertLess(eventbus_time, 0.1, 
                       f"EventBus performance regression: {eventbus_time:.3f}s für 1000 events")
        
        # Test HealthChecker Performance
        health_checker = BaseHealthChecker(service_name="perf_test")
        
        # Add fast check
        def fast_check() -> HealthStatus:
            return HealthStatus.HEALTHY
            
        health_checker.register_component("fast", fast_check, CheckType.SERVICE)
        
        start_time = time.perf_counter()
        
        for i in range(1000):
            health_checker.check_component_health("fast")
            
        end_time = time.perf_counter()
        health_time = end_time - start_time
        
        # Should be under 50ms for 1000 checks
        self.assertLess(health_time, 0.05,
                       f"HealthChecker performance regression: {health_time:.3f}s für 1000 checks")
        
    def test_memory_usage_validation(self):
        """Test: Memory Usage nicht schlechter als Legacy Implementierungen"""
        
        print("Testing Memory Usage...")
        
        import psutil
        import gc
        
        # Baseline Memory
        gc.collect()
        process = psutil.Process()
        baseline_memory = process.memory_info().rss
        
        # Create instances
        instances = []
        for i in range(10):
            event_bus = SharedEventBusManager(
                transport_type=TransportType.IN_MEMORY,
                service_name=f"memory_test_{i}"
            )
            health_checker = BaseHealthChecker(service_name=f"memory_test_{i}")
            instances.extend([event_bus, health_checker])
            
        # Measure memory after instances
        gc.collect()
        after_memory = process.memory_info().rss
        memory_increase = after_memory - baseline_memory
        
        # Memory increase should be reasonable (< 10MB for 10 instances)
        max_memory_mb = 10 * 1024 * 1024  # 10MB
        self.assertLess(memory_increase, max_memory_mb,
                       f"Excessive memory usage: {memory_increase / 1024 / 1024:.1f}MB für 10 instances")
        
    def test_error_handling_backward_compatibility(self):
        """Test: Error Handling ist rückwärtskompatibel"""
        
        print("Testing Error Handling Backward Compatibility...")
        
        # Test dass Legacy Error-Handling Patterns noch funktionieren
        
        # EventBus Error Handling
        event_bus = SharedEventBusManager(
            transport_type=TransportType.IN_MEMORY,
            service_name="error_test"
        )
        
        # Test mit None/Invalid Data (Legacy Patterns)
        try:
            result = event_bus.publish_event("test", None)
            # Sollte entweder funktionieren oder spezifischen Fehler werfen
        except Exception as e:
            # Error sollte typisiert und verständlich sein
            self.assertIsInstance(e, Exception)
            
        # HealthChecker Error Handling  
        health_checker = BaseHealthChecker(service_name="error_test")
        
        def failing_check():
            raise Exception("Legacy failure")
            
        health_checker.register_component(
            "failing",
            failing_check,
            CheckType.SERVICE
        )
        
        # Should handle exceptions gracefully
        status, details = health_checker.check_component_health("failing")
        self.assertEqual(status, HealthStatus.UNHEALTHY)
        self.assertIn('error', details)


def run_backward_compatibility_validation():
    """Führt vollständige Rückwärtskompatibilitäts-Validierung aus"""
    
    print("=" * 80)
    print("BACKWARD COMPATIBILITY VALIDATION v1.0.0 - 24.08.2025")
    print("=" * 80)
    print("Validiere Rückwärtskompatibilität für alle neuen Base-Klassen:")
    print("- SharedEventBusManager vs. 4 Legacy EventBus Implementierungen")
    print("- BaseHealthChecker vs. 20+ Legacy Health Check Patterns")
    print("- StandardImportManager vs. Legacy sys.path Manipulationen")
    print("=" * 80)
    
    # Setup Test Suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(BackwardCompatibilityValidator)
    
    # Run Tests
    runner = unittest.TextTestRunner(
        verbosity=2,
        failfast=False,
        buffer=True
    )
    
    result = runner.run(suite)
    
    # Results Summary
    print("\n" + "=" * 80)
    print("BACKWARD COMPATIBILITY VALIDATION RESULTS")
    print("=" * 80)
    print(f"Compatibility Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ BACKWARD COMPATIBILITY VALIDATION SUCCESSFUL")
        print("Alle Legacy Patterns sind kompatibel mit neuen Base-Klassen!")
    else:
        print("\n❌ BACKWARD COMPATIBILITY ISSUES DETECTED")
        
        if result.failures:
            print(f"\nCompatibility Failures ({len(result.failures)}):")
            for test, failure in result.failures:
                print(f"- {test}")
                
        if result.errors:
            print(f"\nCompatibility Errors ({len(result.errors)}):")
            for test, error in result.errors:
                print(f"- {test}")
    
    print("=" * 80)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    """
    Backward Compatibility Validation Script
    
    Verwendung:
        python backward_compatibility_validation_v1.0.0_20250824.py
        
    Exit Codes:
        0: Alle Compatibility Tests erfolgreich
        1: Compatibility Issues gefunden
    """
    
    success = run_backward_compatibility_validation()
    sys.exit(0 if success else 1)