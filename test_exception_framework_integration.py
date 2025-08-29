#!/usr/bin/env python3
"""
Exception-Framework Integration Test
Test Script für Issue #66 - Exception Framework Implementation

Testet die Exception-Framework-Integration im diagnostic-service
und validiert die strukturierte Fehlerbehandlung.

Author: System Modernization Team
Version: 1.0.0
Date: 2025-08-29
"""

import sys
import os
import asyncio
import json
import logging
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

def test_exception_framework_imports():
    """Test dass alle Exception-Framework-Komponenten importiert werden können"""
    try:
        from shared.exceptions import (
            BaseServiceException, 
            DatabaseException, 
            EventBusException,
            ExternalAPIException,
            ValidationException,
            ConfigurationException,
            BusinessLogicException,
            NetworkException,
            ErrorSeverity,
            ErrorCategory,
            RecoveryStrategy,
            get_error_response
        )
        
        from shared.exception_handler import (
            ExceptionHandler,
            ExceptionHandlerConfig,
            exception_handler,
            database_exception_handler,
            event_bus_exception_handler,
            api_exception_handler,
            create_fastapi_exception_handler
        )
        
        logger.info("✅ Alle Exception-Framework-Komponenten erfolgreich importiert")
        return True
    except ImportError as e:
        logger.error(f"❌ Import-Fehler: {e}")
        return False

def test_exception_creation_and_properties():
    """Test Exception-Erstellung und -Eigenschaften"""
    try:
        from shared.exceptions import ValidationException, ErrorSeverity, ErrorCategory, RecoveryStrategy
        
        # Test ValidationException
        exc = ValidationException(
            "Test validation error",
            field_errors={"username": "Required field"},
            context={"test": "data"}
        )
        
        # Test Properties
        assert exc.message == "Test validation error"
        assert exc.user_message == "Eingabedaten sind ungültig. Bitte prüfen Sie Ihre Eingabe."
        assert exc.severity == ErrorSeverity.LOW
        assert exc.category == ErrorCategory.VALIDATION
        assert exc.recovery_strategy == RecoveryStrategy.NONE
        assert exc.http_status_code == 400
        assert "test" in exc.context
        assert "field_errors" in exc.context
        
        # Test to_dict
        error_dict = exc.to_dict()
        assert "error_code" in error_dict
        assert "message" in error_dict
        assert "user_message" in error_dict
        assert "severity" in error_dict
        assert "category" in error_dict
        
        logger.info("✅ Exception-Erstellung und -Eigenschaften korrekt")
        return True
    except Exception as e:
        logger.error(f"❌ Exception-Test fehlgeschlagen: {e}")
        return False

def test_exception_handler_decorator():
    """Test Exception-Handler-Decorator"""
    try:
        from shared.exception_handler import exception_handler
        from shared.exceptions import ValidationException, BusinessLogicException
        
        @exception_handler()
        def test_function_with_validation_error():
            raise ValidationException("Test error")
        
        @exception_handler()
        def test_function_with_generic_error():
            raise ValueError("Generic error")
        
        # Test ValidationException-Handling
        try:
            test_function_with_validation_error()
        except ValidationException:
            logger.info("✅ ValidationException korrekt behandelt")
        
        # Test generische Exception-Konvertierung
        try:
            test_function_with_generic_error()
        except BusinessLogicException:
            logger.info("✅ Generische Exception zu BusinessLogicException konvertiert")
        
        return True
    except Exception as e:
        logger.error(f"❌ Exception-Handler-Decorator-Test fehlgeschlagen: {e}")
        return False

def test_fastapi_exception_handler():
    """Test FastAPI Exception-Handler-Integration"""
    try:
        from shared.exception_handler import create_fastapi_exception_handler
        from shared.exceptions import BaseServiceException, get_error_response
        
        # Mock FastAPI Request
        class MockRequest:
            def __init__(self):
                self.url = "http://localhost:8000/test"
                self.method = "GET"
        
        handler = create_fastapi_exception_handler()
        
        # Test Exception
        exc = BaseServiceException(
            "Test exception for FastAPI handler",
            http_status_code=400
        )
        
        # Handler sollte eine JSONResponse zurückgeben
        request = MockRequest()
        response = asyncio.run(handler(request, exc))
        
        assert hasattr(response, 'status_code')
        assert response.status_code == 400
        
        logger.info("✅ FastAPI Exception-Handler korrekt erstellt")
        return True
    except Exception as e:
        logger.error(f"❌ FastAPI Exception-Handler-Test fehlgeschlagen: {e}")
        return False

def test_exception_factory():
    """Test Exception-Factory"""
    try:
        from shared.exceptions import ExceptionFactory, DatabaseException, EventBusException, ExternalAPIException
        
        # Test Database Exception Factory
        db_exc = ExceptionFactory.create_database_exception(
            "connection", 
            "Database connection failed"
        )
        assert isinstance(db_exc, DatabaseException)
        
        # Test Event Bus Exception Factory
        event_exc = ExceptionFactory.create_event_bus_exception(
            "publish",
            "Failed to publish event"
        )
        assert isinstance(event_exc, EventBusException)
        
        # Test API Exception Factory
        api_exc = ExceptionFactory.create_api_exception(
            "rate_limit",
            "API rate limit exceeded"
        )
        assert isinstance(api_exc, ExternalAPIException)
        
        logger.info("✅ Exception-Factory korrekt funktionsfähig")
        return True
    except Exception as e:
        logger.error(f"❌ Exception-Factory-Test fehlgeschlagen: {e}")
        return False

def test_error_response_generation():
    """Test Error-Response-Generierung"""
    try:
        from shared.exceptions import ValidationException, get_error_response
        
        exc = ValidationException(
            "Invalid input data",
            field_errors={"email": "Invalid format"}
        )
        
        response = get_error_response(exc)
        
        assert response["success"] is False
        assert "error" in response
        assert "timestamp" in response
        assert response["error"]["message"] == "Invalid input data"
        assert response["error"]["http_status_code"] == 400
        
        logger.info("✅ Error-Response-Generierung korrekt")
        return True
    except Exception as e:
        logger.error(f"❌ Error-Response-Test fehlgeschlagen: {e}")
        return False

async def run_integration_tests():
    """Führt alle Integration-Tests aus"""
    logger.info("🧪 Starte Exception-Framework Integration Tests...")
    
    test_results = {
        "imports": test_exception_framework_imports(),
        "exception_creation": test_exception_creation_and_properties(),
        "decorator": test_exception_handler_decorator(),
        "fastapi_handler": test_fastapi_exception_handler(),
        "factory": test_exception_factory(),
        "error_response": test_error_response_generation()
    }
    
    # Erstelle Test-Report
    timestamp = datetime.now().isoformat()
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    failed_tests = total_tests - passed_tests
    
    report = {
        "timestamp": timestamp,
        "test_suite": "Exception Framework Integration",
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": f"{(passed_tests/total_tests)*100:.2f}%",
        "test_results": test_results,
        "overall_status": "PASSED" if failed_tests == 0 else "FAILED"
    }
    
    # Report speichern
    report_path = "/home/mdoehler/aktienanalyse-ökosystem/exception_framework_test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # Log Zusammenfassung
    logger.info(f"📊 Test-Zusammenfassung:")
    logger.info(f"   Total Tests: {total_tests}")
    logger.info(f"   Erfolgreich: {passed_tests}")
    logger.info(f"   Fehlgeschlagen: {failed_tests}")
    logger.info(f"   Erfolgsrate: {report['success_rate']}")
    logger.info(f"   Status: {report['overall_status']}")
    
    if failed_tests == 0:
        logger.info("🎉 Alle Exception-Framework Tests erfolgreich!")
    else:
        logger.warning("⚠️ Einige Tests fehlgeschlagen - Details im Report")
    
    return report

if __name__ == "__main__":
    print("Exception-Framework Integration Test")
    print("===================================")
    
    report = asyncio.run(run_integration_tests())
    
    if report["overall_status"] == "PASSED":
        print("\n✅ Exception-Framework ready für Production Rollout!")
        exit(0)
    else:
        print("\n❌ Exception-Framework benötigt weitere Fixes")
        exit(1)