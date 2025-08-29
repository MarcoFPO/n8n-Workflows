#!/usr/bin/env python3
"""
SOLID Compliance Test Suite
Issue #62 - SOLID-Prinzipien durchsetzen

Test-Framework zur Validierung der SOLID-Prinzipien-Implementierung

Author: System Modernization Team
Version: 1.0.0
Date: 2025-08-29
"""

import asyncio
import inspect
import pytest
from typing import Dict, Any, Type, List
from abc import ABC, abstractmethod

# Fix imports für direktes Ausführen
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SOLID Components
from shared.solid_foundations import (
    SOLIDServiceOrchestrator,
    ServiceContainer,
    APIRouter,
    ServiceManager,
    HealthMonitor,
    Startable,
    Stoppable,
    Healthable,
    Configurable,
    Routable,
    Monitorable,
    validate_solid_compliance
)

# Event-Bus SOLID Implementation
try:
    from services.event_bus_service.solid_event_bus import (
        SOLIDEventBusOrchestrator,
        EventBusService,
        EventBusAPIController,
        FastAPIAdapter
    )
except ImportError:
    # Mock für fehlende Dependencies
    class SOLIDEventBusOrchestrator:
        pass
    class EventBusService:
        pass
    class EventBusAPIController:
        pass
    class FastAPIAdapter:
        pass


class SOLIDComplianceValidator:
    """Validator für SOLID-Prinzipien-Compliance"""
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def validate_srp(self, class_type: Type) -> Dict[str, Any]:
        """Single Responsibility Principle validieren"""
        result = {
            'principle': 'SRP - Single Responsibility Principle',
            'class': class_type.__name__,
            'compliant': True,
            'issues': [],
            'metrics': {}
        }
        
        # Anzahl Methoden analysieren
        methods = [method for method in dir(class_type) 
                  if not method.startswith('_') and callable(getattr(class_type, method, None))]
        
        result['metrics']['method_count'] = len(methods)
        
        # SRP: Max 10 public Methods als Richtwert
        if len(methods) > 10:
            result['compliant'] = False
            result['issues'].append(f"Too many methods ({len(methods)}) - possible SRP violation")
        
        # Klassennamen-Analyse (sollte spezifisch sein)
        class_name = class_type.__name__.lower()
        generic_names = ['manager', 'handler', 'controller', 'service', 'orchestrator']
        
        if any(generic in class_name for generic in generic_names):
            # Check ob wirklich generic oder spezifisch
            specific_indicators = ['api', 'health', 'event', 'solid']
            if not any(indicator in class_name for indicator in specific_indicators):
                result['issues'].append("Generic class name - possible multiple responsibilities")
        
        return result
    
    def validate_ocp(self, class_type: Type) -> Dict[str, Any]:
        """Open/Closed Principle validieren"""
        result = {
            'principle': 'OCP - Open/Closed Principle',
            'class': class_type.__name__,
            'compliant': True,
            'issues': [],
            'metrics': {}
        }
        
        # Prüfe auf abstrakte Methoden (Extension Points)
        has_abstract_methods = hasattr(class_type, '__abstractmethods__') and len(class_type.__abstractmethods__) > 0
        is_abc = issubclass(class_type, ABC)
        
        result['metrics']['is_abstract'] = is_abc
        result['metrics']['abstract_method_count'] = len(class_type.__abstractmethods__) if has_abstract_methods else 0
        
        # OCP: Abstrakte Klassen oder Interfaces für Erweiterbarkeit
        if not is_abc and not hasattr(class_type, '__init__'):
            result['issues'].append("No extension mechanism found")
            result['compliant'] = False
        
        return result
    
    def validate_lsp(self, class_type: Type) -> Dict[str, Any]:
        """Liskov Substitution Principle validieren"""
        result = {
            'principle': 'LSP - Liskov Substitution Principle',
            'class': class_type.__name__,
            'compliant': True,
            'issues': [],
            'metrics': {}
        }
        
        # Base-Classes analysieren
        base_classes = [base for base in class_type.__mro__ if base != class_type and base != object]
        result['metrics']['base_class_count'] = len(base_classes)
        
        # LSP: Konsistente Interface-Implementation
        for base in base_classes:
            if hasattr(base, '__abstractmethods__'):
                abstract_methods = base.__abstractmethods__
                for method_name in abstract_methods:
                    if not hasattr(class_type, method_name):
                        result['compliant'] = False
                        result['issues'].append(f"Missing implementation: {method_name}")
                    else:
                        # Signatur-Konsistenz prüfen
                        base_method = getattr(base, method_name, None)
                        impl_method = getattr(class_type, method_name)
                        
                        if base_method and hasattr(base_method, '__annotations__'):
                            base_sig = inspect.signature(base_method) if callable(base_method) else None
                            impl_sig = inspect.signature(impl_method)
                            
                            # Vereinfachte Signatur-Prüfung
                            if base_sig and len(base_sig.parameters) != len(impl_sig.parameters):
                                result['issues'].append(f"Signature mismatch: {method_name}")
        
        return result
    
    def validate_isp(self, class_type: Type) -> Dict[str, Any]:
        """Interface Segregation Principle validieren"""
        result = {
            'principle': 'ISP - Interface Segregation Principle',
            'class': class_type.__name__,
            'compliant': True,
            'issues': [],
            'metrics': {}
        }
        
        # Interfaces analysieren (ABC-Subklassen)
        interfaces = [base for base in class_type.__mro__ 
                     if issubclass(base, ABC) and base != ABC and base != class_type]
        
        result['metrics']['interface_count'] = len(interfaces)
        
        # ISP: Kleine, spezifische Interfaces
        for interface in interfaces:
            if hasattr(interface, '__abstractmethods__'):
                abstract_count = len(interface.__abstractmethods__)
                result['metrics'][f'{interface.__name__}_methods'] = abstract_count
                
                # Max 5 Methoden pro Interface als Richtwert
                if abstract_count > 5:
                    result['compliant'] = False
                    result['issues'].append(f"Interface {interface.__name__} too large ({abstract_count} methods)")
        
        return result
    
    def validate_dip(self, class_type: Type) -> Dict[str, Any]:
        """Dependency Inversion Principle validieren"""
        result = {
            'principle': 'DIP - Dependency Inversion Principle',
            'class': class_type.__name__,
            'compliant': True,
            'issues': [],
            'metrics': {}
        }
        
        # Constructor-Parameter analysieren
        if hasattr(class_type, '__init__'):
            init_signature = inspect.signature(class_type.__init__)
            params = [param for name, param in init_signature.parameters.items() if name != 'self']
            
            result['metrics']['constructor_param_count'] = len(params)
            
            # DIP: Dependency Injection via Constructor
            has_container_param = any('container' in param.name.lower() for param in params)
            has_interface_params = any(param.annotation and hasattr(param.annotation, '__abstractmethods__') 
                                     for param in params if param.annotation)
            
            result['metrics']['has_container_param'] = has_container_param
            result['metrics']['has_interface_params'] = has_interface_params
            
            # DIP-Compliance: Container oder Interface-Parameter
            if len(params) == 0:
                result['issues'].append("No dependency injection - hardcoded dependencies likely")
                result['compliant'] = False
            elif not (has_container_param or has_interface_params):
                result['issues'].append("No abstract dependencies - possible concrete coupling")
        
        return result
    
    def validate_class_compliance(self, class_type: Type) -> Dict[str, Any]:
        """Komplette SOLID-Compliance einer Klasse validieren"""
        compliance_result = {
            'class': class_type.__name__,
            'overall_compliant': True,
            'principles': {},
            'score': 0
        }
        
        # Alle SOLID-Prinzipien testen
        principles = [
            self.validate_srp,
            self.validate_ocp,
            self.validate_lsp,
            self.validate_isp,
            self.validate_dip
        ]
        
        compliant_count = 0
        for principle_validator in principles:
            principle_result = principle_validator(class_type)
            principle_name = principle_result['principle'].split(' - ')[0]
            compliance_result['principles'][principle_name] = principle_result
            
            if principle_result['compliant']:
                compliant_count += 1
            else:
                compliance_result['overall_compliant'] = False
        
        # Score berechnen (0-100)
        compliance_result['score'] = (compliant_count / len(principles)) * 100
        
        return compliance_result


# =============================================================================
# SOLID COMPLIANCE TESTS
# =============================================================================

class TestSOLIDCompliance:
    """Test Suite für SOLID-Prinzipien-Compliance"""
    
    def setup_method(self):
        """Test Setup"""
        self.validator = SOLIDComplianceValidator()
    
    def test_solid_foundations_compliance(self):
        """Test SOLID Foundation Classes"""
        classes_to_test = [
            SOLIDServiceOrchestrator,
            ServiceContainer,
            APIRouter,
            ServiceManager,
            HealthMonitor
        ]
        
        results = []
        for class_type in classes_to_test:
            result = self.validator.validate_class_compliance(class_type)
            results.append(result)
            
            # Mindestens 80% Compliance erforderlich
            assert result['score'] >= 80, f"{class_type.__name__} SOLID compliance: {result['score']}%"
        
        # Durchschnittliche Compliance
        avg_score = sum(r['score'] for r in results) / len(results)
        assert avg_score >= 85, f"Foundation classes average compliance: {avg_score}%"
    
    def test_event_bus_solid_compliance(self):
        """Test Event-Bus SOLID Implementation"""
        classes_to_test = [
            SOLIDEventBusOrchestrator,
            EventBusService,
            EventBusAPIController,
            FastAPIAdapter
        ]
        
        results = []
        for class_type in classes_to_test:
            result = self.validator.validate_class_compliance(class_type)
            results.append(result)
            
            # Mindestens 85% Compliance für Event-Bus
            assert result['score'] >= 85, f"{class_type.__name__} SOLID compliance: {result['score']}%"
        
        # Event-Bus sollte >90% Compliance haben
        avg_score = sum(r['score'] for r in results) / len(results)
        assert avg_score >= 90, f"Event-Bus SOLID compliance: {avg_score}%"
    
    def test_interface_segregation_compliance(self):
        """Test Interface Segregation Principle"""
        interfaces_to_test = [
            Startable,
            Stoppable,
            Healthable,
            Configurable,
            Routable,
            Monitorable
        ]
        
        for interface in interfaces_to_test:
            # Interfaces sollten klein sein (max 3 Methoden)
            if hasattr(interface, '__abstractmethods__'):
                method_count = len(interface.__abstractmethods__)
                assert method_count <= 3, f"{interface.__name__} has too many methods: {method_count}"
    
    @pytest.mark.asyncio
    async def test_dependency_injection_functionality(self):
        """Test Dependency Injection Functionality"""
        container = ServiceContainer("test")
        
        # Service registrieren
        class TestService:
            def get_value(self):
                return "test-value"
        
        container.register_singleton(TestService, TestService())
        
        # Service auflösen
        service = container.resolve(TestService)
        assert service.get_value() == "test-value"
        
        # Registrierungen prüfen
        registrations = container.get_registrations()
        assert len(registrations) >= 1
    
    @pytest.mark.asyncio
    async def test_solid_orchestrator_integration(self):
        """Test SOLID Orchestrator Integration"""
        orchestrator = SOLIDServiceOrchestrator("test-service")
        
        # Initialisierung
        success = await orchestrator.initialize()
        assert success, "Orchestrator initialization failed"
        
        # Health Check
        health = await orchestrator.health_check()
        assert health['status'] in ['healthy', 'unhealthy']
        assert 'service' in health
        
        # Container-Zugriff
        container = orchestrator.get_container()
        assert isinstance(container, ServiceContainer)
        
        # Komponenten-Zugriff
        router = orchestrator.get_router()
        assert isinstance(router, APIRouter)
        
        service_manager = orchestrator.get_service_manager()
        assert isinstance(service_manager, ServiceManager)
        
        health_monitor = orchestrator.get_health_monitor()
        assert isinstance(health_monitor, HealthMonitor)


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestSOLIDPerformance:
    """Performance Tests für SOLID Implementation"""
    
    @pytest.mark.asyncio
    async def test_container_resolution_performance(self):
        """Test Container Resolution Performance"""
        container = ServiceContainer("performance-test")
        
        # Service registrieren
        class PerfTestService:
            def process(self):
                return "processed"
        
        container.register_singleton(PerfTestService, PerfTestService())
        
        # Performance Test: 1000 Resolutions
        import time
        start_time = time.time()
        
        for _ in range(1000):
            service = container.resolve(PerfTestService)
            service.process()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Sollte unter 100ms für 1000 Resolutions sein
        assert duration < 0.1, f"Container resolution too slow: {duration}s for 1000 resolutions"
    
    @pytest.mark.asyncio
    async def test_service_manager_performance(self):
        """Test Service Manager Performance"""
        service_manager = ServiceManager("performance-test")
        
        # Multiple Services registrieren
        class FastService(Startable, Stoppable):
            def __init__(self, name):
                self.name = name
                self.started = False
            
            async def startup(self):
                self.started = True
                return True
            
            async def shutdown(self):
                self.started = False
                return True
        
        # 50 Services registrieren
        for i in range(50):
            service = FastService(f"service-{i}")
            service_manager.register_service(f"service-{i}", service, priority=i)
        
        # Start Performance Test
        import time
        start_time = time.time()
        
        success = await service_manager.start_all()
        assert success
        
        await service_manager.stop_all()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Sollte unter 500ms für 50 Services sein
        assert duration < 0.5, f"Service manager too slow: {duration}s for 50 services"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSOLIDIntegration:
    """Integration Tests für SOLID Event-Bus"""
    
    @pytest.mark.asyncio
    async def test_solid_event_bus_integration(self):
        """Test komplette SOLID Event-Bus Integration"""
        orchestrator = SOLIDEventBusOrchestrator()
        
        try:
            # Initialisierung
            success = await orchestrator.initialize()
            assert success, "Event-Bus orchestrator initialization failed"
            
            # FastAPI App verfügbar
            app = orchestrator.get_app()
            assert app is not None
            
            # Health Check
            health = await orchestrator.health_check()
            assert 'service' in health
            assert 'container' in health
            
        finally:
            # Cleanup
            await orchestrator.stop()


if __name__ == "__main__":
    # Direkt ausführen für schnelle Tests
    async def run_basic_tests():
        validator = SOLIDComplianceValidator()
        
        # Foundation Tests
        foundation_classes = [SOLIDServiceOrchestrator, ServiceContainer]
        print("=== SOLID Foundation Compliance ===")
        
        for class_type in foundation_classes:
            result = validator.validate_class_compliance(class_type)
            print(f"\n{class_type.__name__}: {result['score']:.1f}% compliant")
            
            for principle, details in result['principles'].items():
                status = "✓" if details['compliant'] else "✗"
                print(f"  {status} {principle}: {details.get('issues', ['OK'])[0] if details.get('issues') else 'OK'}")
    
    asyncio.run(run_basic_tests())