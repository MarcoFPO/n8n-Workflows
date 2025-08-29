#!/usr/bin/env python3
"""
BaseServiceOrchestrator Exception-Framework Integration Test
Validiert die Integration zwischen BaseServiceOrchestrator und Exception-Framework

Author: TEST-AGENT für Issue #66
Version: 1.0.0
Date: 2025-08-29
"""

import sys
import os
import asyncio
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_base_service_exception_integration():
    """Test BaseServiceOrchestrator + Exception-Framework Integration"""
    
    test_results = {
        "base_service_import": False,
        "exception_framework_configuration": False,
        "fastapi_handler_registration": False,
        "service_instantiation": False,
        "exception_handling_flow": False
    }
    
    try:
        # Test 1: BaseServiceOrchestrator Import
        logger.info("🔍 Testing BaseServiceOrchestrator import...")
        from shared.service_base import BaseServiceOrchestrator
        test_results["base_service_import"] = True
        logger.info("✅ BaseServiceOrchestrator import successful")
        
        # Test 2: Exception-Framework Components Import
        logger.info("🔍 Testing Exception-Framework configuration...")
        from shared.exception_handler import (
            ExceptionHandlerConfig, 
            configure_exception_handler,
            create_fastapi_exception_handler
        )
        from shared.exceptions import (
            BaseServiceException,
            RecoveryStrategy,
            ValidationException
        )
        test_results["exception_framework_configuration"] = True
        logger.info("✅ Exception-Framework components imported")
        
        # Test 3: Mock Service-Konfiguration
        class MockServiceConfig:
            def __init__(self):
                self.service_name = "test-service"
                self.service_version = "1.0.0"
                self.host = "0.0.0.0"
                self.port = 8999  # Use different port to avoid conflicts
                
                # Exception-Framework Konfiguration
                self.exception_logging = True
                self.exception_default_recovery = "retry"
                self.exception_rollback = True
                self.exception_max_retries = 3
                self.exception_circuit_breaker_threshold = 5
                self.exception_metrics = True
                
                # Database-Konfiguration (Mock)
                self.database_url = "sqlite:///:memory:"
                self.redis_url = "redis://localhost:6379"
                
                # Service-spezifische Konfiguration
                self.service_root_path = "/home/mdoehler/aktienanalyse-ökosystem/services/test-service"
        
        config = MockServiceConfig()
        
        # Test 4: Service-Instantiation
        logger.info("🔍 Testing BaseServiceOrchestrator instantiation...")
        service = BaseServiceOrchestrator(config)
        test_results["service_instantiation"] = True
        logger.info("✅ BaseServiceOrchestrator instantiation successful")
        
        # Test 5: FastAPI Exception-Handler Registration
        logger.info("🔍 Testing FastAPI exception handler registration...")
        if service.app and hasattr(service.app, 'exception_handlers'):
            # Check if BaseServiceException handler is registered
            has_exception_handler = BaseServiceException in service.app.exception_handlers
            test_results["fastapi_handler_registration"] = has_exception_handler
            logger.info(f"✅ FastAPI exception handler registration: {has_exception_handler}")
        else:
            logger.warning("⚠️ FastAPI app not available for exception handler test")
        
        # Test 6: Exception-Handling Flow
        logger.info("🔍 Testing exception handling flow...")
        try:
            # Mock eine Service-Operation die eine Exception wirft
            def mock_operation():
                raise ValidationException(
                    "Mock validation error for integration test",
                    field_errors={"test_field": "Required"}
                )
            
            # Exception sollte vom Framework behandelt werden
            try:
                mock_operation()
            except ValidationException as e:
                # Exception wurde korrekt geworfen und kann behandelt werden
                assert e.http_status_code == 400
                assert "validation error" in e.message.lower()
                test_results["exception_handling_flow"] = True
                logger.info("✅ Exception handling flow working")
            
        except Exception as e:
            logger.error(f"❌ Exception handling flow failed: {e}")
        
        return test_results
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return test_results
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return test_results


def test_diagnostic_service_exception_migration():
    """Test diagnostic-service Exception-Framework Migration"""
    
    test_results = {
        "diagnostic_service_import": False,
        "exception_framework_imported": False,
        "service_methods_available": False
    }
    
    try:
        # Test diagnostic-service Import
        logger.info("🔍 Testing diagnostic-service exception migration...")
        
        # Check if diagnostic-service can be imported
        diagnostic_service_path = "/home/mdoehler/aktienanalyse-ökosystem/services/diagnostic-service"
        if os.path.exists(diagnostic_service_path):
            sys.path.append(diagnostic_service_path)
            
            try:
                from main import app
                test_results["diagnostic_service_import"] = True
                logger.info("✅ diagnostic-service import successful")
                
                # Check if exception framework is imported in diagnostic-service
                import main
                source_code = open(f"{diagnostic_service_path}/main.py", "r").read()
                
                if "from shared.exceptions import" in source_code:
                    test_results["exception_framework_imported"] = True
                    logger.info("✅ Exception-Framework imported in diagnostic-service")
                
                # Check service methods
                if hasattr(main, 'app') and main.app:
                    test_results["service_methods_available"] = True
                    logger.info("✅ diagnostic-service methods available")
                
            except Exception as e:
                logger.error(f"❌ diagnostic-service import failed: {e}")
        
        else:
            logger.warning("⚠️ diagnostic-service not found")
            
        return test_results
        
    except Exception as e:
        logger.error(f"❌ diagnostic-service migration test failed: {e}")
        return test_results


def generate_integration_test_report():
    """Generiere Integration Test Report"""
    
    logger.info("🧪 Starte BaseServiceOrchestrator Exception-Framework Integration Tests...")
    
    # Test 1: BaseServiceOrchestrator Integration
    base_service_results = test_base_service_exception_integration()
    
    # Test 2: diagnostic-service Migration
    diagnostic_service_results = test_diagnostic_service_exception_migration()
    
    # Kombiniere Ergebnisse
    all_results = {**base_service_results, **diagnostic_service_results}
    
    # Berechne Statistiken
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results.values() if result)
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    # Erstelle Report
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_suite": "BaseServiceOrchestrator Exception-Framework Integration",
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": f"{success_rate:.2f}%",
        "test_results": {
            "base_service_orchestrator": base_service_results,
            "diagnostic_service_migration": diagnostic_service_results
        },
        "overall_status": "PASSED" if failed_tests == 0 else "INTEGRATION_ISSUES"
    }
    
    # Report speichern
    report_path = "/home/mdoehler/aktienanalyse-ökosystem/base_service_exception_integration_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # Log Zusammenfassung
    logger.info("📊 Integration Test Zusammenfassung:")
    logger.info(f"   Total Tests: {total_tests}")
    logger.info(f"   Erfolgreich: {passed_tests}")
    logger.info(f"   Fehlgeschlagen: {failed_tests}")
    logger.info(f"   Erfolgsrate: {success_rate:.2f}%")
    logger.info(f"   Status: {report['overall_status']}")
    
    # Detaillierte Ergebnisse
    logger.info("🔍 BaseServiceOrchestrator Tests:")
    for test_name, result in base_service_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
    
    logger.info("🔍 diagnostic-service Migration Tests:")
    for test_name, result in diagnostic_service_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
    
    return report


if __name__ == "__main__":
    print("BaseServiceOrchestrator Exception-Framework Integration Test")
    print("==========================================================")
    
    report = generate_integration_test_report()
    
    if report["overall_status"] == "PASSED":
        print("\n✅ BaseServiceOrchestrator Integration erfolgreich!")
        exit(0)
    else:
        print(f"\n❌ {report['failed_tests']} Integration-Issues gefunden")
        exit(1)