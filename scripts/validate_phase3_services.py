#!/usr/bin/env python3
"""
Phase 3 Service Validation Script v1.0.0
Validierung aller migrierten Services - Clean Architecture v6.1.x

VALIDATION SCRIPT - PHASE 3 TESTING:
- Clean Architecture Compliance Tests
- PostgreSQL Database Manager Integration Tests
- API Standards Compliance Tests
- Error Handling Framework Tests
- Performance und Load Testing
- Comprehensive Service Health Checks

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add shared modules to path
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from service_validation_framework_v1_0_0_20250825 import (
    ServiceValidationOrchestrator,
    ValidationReportGenerator,
    TestStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================

SERVICES_CONFIG = {
    "prediction-tracking-service": {
        "version": "6.1.0",
        "service_path": "/home/mdoehler/aktienanalyse-ökosystem/services/prediction-tracking-service",
        "service_url": "http://localhost:8015",
        "database_type": "postgresql",
        "api_standards": True,
        "error_framework": True
    },
    "diagnostic-service": {
        "version": "6.1.0", 
        "service_path": "/home/mdoehler/aktienanalyse-ökosystem/services/diagnostic-service",
        "service_url": "http://localhost:8013",
        "database_type": "postgresql",
        "api_standards": True,
        "error_framework": True
    },
    "data-processing-service": {
        "version": "6.1.0",
        "service_path": "/home/mdoehler/aktienanalyse-ökosystem/services/data-processing-service", 
        "service_url": "http://localhost:8012",
        "database_type": "postgresql",
        "api_standards": True,
        "error_framework": True
    },
    "marketcap-service": {
        "version": "6.1.0",
        "service_path": "/home/mdoehler/aktienanalyse-ökosystem/services/marketcap-service",
        "service_url": "http://localhost:8011",
        "database_type": "postgresql", 
        "api_standards": True,
        "error_framework": True
    },
    "ml-analytics-service": {
        "version": "6.1.1",
        "service_path": "/home/mdoehler/aktienanalyse-ökosystem/services/ml-analytics-service",
        "service_url": "http://localhost:8016",
        "database_type": "postgresql",
        "api_standards": True,
        "error_framework": True
    }
}


# =============================================================================
# VALIDATION EXECUTION
# =============================================================================

async def validate_all_phase3_services():
    """Execute comprehensive validation for all Phase 3 services"""
    
    logger.info("Starting Phase 3 Service Validation...")
    logger.info("=" * 80)
    
    # Initialize validation orchestrator
    orchestrator = ServiceValidationOrchestrator()
    
    # Execute validation for all services
    reports = await orchestrator.validate_all_services(SERVICES_CONFIG)
    
    # Generate reports
    console_report = ValidationReportGenerator.generate_console_report(reports)
    json_report = ValidationReportGenerator.generate_json_report(reports)
    
    # Output console report
    print(console_report)
    
    # Save JSON report
    report_file = Path("/home/mdoehler/aktienanalyse-ökosystem/reports/phase3_validation_report.json")
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write(json_report)
    
    logger.info(f"Detailed JSON report saved to: {report_file}")
    
    # Summary statistics
    total_services = len(reports)
    passed_services = sum(1 for r in reports.values() if r.overall_status == TestStatus.PASSED)
    failed_services = sum(1 for r in reports.values() if r.overall_status == TestStatus.FAILED)
    error_services = sum(1 for r in reports.values() if r.overall_status == TestStatus.ERROR)
    
    logger.info("=" * 80)
    logger.info("PHASE 3 VALIDATION SUMMARY:")
    logger.info(f"Total Services: {total_services}")
    logger.info(f"Passed: {passed_services}")
    logger.info(f"Failed: {failed_services}")  
    logger.info(f"Errors: {error_services}")
    logger.info(f"Success Rate: {(passed_services/total_services)*100:.1f}%")
    logger.info("=" * 80)
    
    # Determine validation result
    if passed_services == total_services:
        logger.info("✅ Phase 3 Validation: ALL SERVICES PASSED")
        return True
    else:
        logger.error("❌ Phase 3 Validation: SOME SERVICES FAILED")
        
        # Log critical failures
        for service_name, report in reports.items():
            critical_failures = report.get_critical_failures()
            if critical_failures:
                logger.error(f"Critical failures in {service_name}:")
                for failure in critical_failures:
                    logger.error(f"  - {failure.test_name}: {failure.message}")
        
        return False


async def validate_single_service(service_name: str):
    """Validate a single service"""
    
    if service_name not in SERVICES_CONFIG:
        logger.error(f"Service '{service_name}' not found in configuration")
        logger.info(f"Available services: {', '.join(SERVICES_CONFIG.keys())}")
        return False
    
    logger.info(f"Validating single service: {service_name}")
    
    orchestrator = ServiceValidationOrchestrator()
    service_config = SERVICES_CONFIG[service_name]
    
    report = await orchestrator.validate_service(service_name, service_config)
    
    # Generate and display report
    reports = {service_name: report}
    console_report = ValidationReportGenerator.generate_console_report(reports)
    print(console_report)
    
    return report.overall_status == TestStatus.PASSED


async def run_architecture_compliance_only():
    """Run only Clean Architecture compliance tests"""
    
    logger.info("Running Clean Architecture Compliance Tests Only...")
    
    from service_validation_framework_v1_0_0_20250825 import CleanArchitectureValidator
    
    validator = CleanArchitectureValidator()
    
    for service_name, config in SERVICES_CONFIG.items():
        logger.info(f"Testing {service_name}...")
        
        results = await validator.validate(config)
        
        print(f"\n{service_name} Clean Architecture Results:")
        for result in results:
            status_icon = "✅" if result.status == TestStatus.PASSED else "❌"
            print(f"  {status_icon} {result.test_name}: {result.message}")


async def run_database_tests_only():
    """Run only Database integration tests"""
    
    logger.info("Running Database Integration Tests Only...")
    
    from service_validation_framework_v1_0_0_20250825 import DatabaseValidator
    
    validator = DatabaseValidator()
    
    for service_name, config in SERVICES_CONFIG.items():
        logger.info(f"Testing {service_name}...")
        
        results = await validator.validate(config)
        
        print(f"\n{service_name} Database Integration Results:")
        for result in results:
            status_icon = "✅" if result.status == TestStatus.PASSED else "❌"
            print(f"  {status_icon} {result.test_name}: {result.message}")


async def run_api_standards_tests_only():
    """Run only API Standards compliance tests"""
    
    logger.info("Running API Standards Compliance Tests Only...")
    
    from service_validation_framework_v1_0_0_20250825 import APIStandardsValidator
    
    validator = APIStandardsValidator()
    
    for service_name, config in SERVICES_CONFIG.items():
        logger.info(f"Testing {service_name}...")
        
        results = await validator.validate(config)
        
        print(f"\n{service_name} API Standards Results:")
        for result in results:
            status_icon = "✅" if result.status == TestStatus.PASSED else "❌"
            print(f"  {status_icon} {result.test_name}: {result.message}")


async def run_performance_tests_only():
    """Run only Performance tests"""
    
    logger.info("Running Performance Tests Only...")
    
    from service_validation_framework_v1_0_0_20250825 import PerformanceValidator
    
    validator = PerformanceValidator()
    
    for service_name, config in SERVICES_CONFIG.items():
        logger.info(f"Testing {service_name}...")
        
        results = await validator.validate(config)
        
        print(f"\n{service_name} Performance Results:")
        for result in results:
            status_icon = "✅" if result.status == TestStatus.PASSED else "❌"
            severity_icon = "🔴" if result.severity.value == "critical" else "🟡" if result.severity.value == "high" else "🔵"
            print(f"  {status_icon} {severity_icon} {result.test_name}: {result.message}")
            
            if result.details:
                for key, value in result.details.items():
                    if key.endswith("_ms") or key.endswith("_mb"):
                        print(f"    {key}: {value:.2f}")
                    else:
                        print(f"    {key}: {value}")


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

async def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python validate_phase3_services.py <command> [service_name]")
        print("")
        print("Commands:")
        print("  all                    - Run all validation tests")
        print("  service <name>         - Validate single service")
        print("  architecture           - Run only Clean Architecture tests")
        print("  database              - Run only Database integration tests")
        print("  api-standards         - Run only API Standards tests")
        print("  performance           - Run only Performance tests")
        print("")
        print("Available services:")
        for service_name in SERVICES_CONFIG.keys():
            print(f"  - {service_name}")
        return
    
    command = sys.argv[1].lower()
    
    if command == "all":
        success = await validate_all_phase3_services()
        sys.exit(0 if success else 1)
    
    elif command == "service":
        if len(sys.argv) < 3:
            print("Error: Service name required")
            print(f"Available services: {', '.join(SERVICES_CONFIG.keys())}")
            sys.exit(1)
        
        service_name = sys.argv[2]
        success = await validate_single_service(service_name)
        sys.exit(0 if success else 1)
    
    elif command == "architecture":
        await run_architecture_compliance_only()
    
    elif command == "database":
        await run_database_tests_only()
    
    elif command == "api-standards":
        await run_api_standards_tests_only()
    
    elif command == "performance":
        await run_performance_tests_only()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())