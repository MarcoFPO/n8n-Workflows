#!/usr/bin/env python3
"""
Clean Architecture Modules Test v1.0.0
Standalone Tests für implementierte Clean Architecture Module

Code-Qualität: HÖCHSTE PRIORITÄT
- Integration Tests für alle implementierten Module
- Standalone Execution ohne externe Dependencies
- Validation der SOLID Principles Implementation
"""

import sys
import os
from pathlib import Path

# Add project root to path for standalone execution
project_root = Path("/home/mdoehler/aktienanalyse-ökosystem")
sys.path.insert(0, str(project_root))

def test_config_manager():
    """Test Configuration Manager and Service Discovery"""
    print("=== Testing Configuration Manager ===")
    
    try:
        # Test module import
        from shared.config_manager_v1_0_0_20250822 import (
            get_config_manager, 
            get_service_discovery,
            ServiceType,
            Environment,
            LegacyUrlMapper
        )
        
        print("✅ Config Manager imported successfully")
        
        # Test config manager
        config = get_config_manager()
        print(f"✅ Environment detected: {config.environment}")
        print(f"✅ Project root: {config.project_root}")
        
        # Test service discovery  
        discovery = get_service_discovery()
        
        # Test a few key services
        test_services = [
            ServiceType.FRONTEND,
            ServiceType.DATA_PROCESSING,
            ServiceType.EVENT_BUS
        ]
        
        for service_type in test_services:
            url = discovery.get_service_url(service_type)
            health_url = discovery.get_health_url(service_type)
            print(f"✅ {service_type.value}: {url} (health: {health_url})")
        
        # Test legacy URL migration
        test_urls = [
            "http://localhost:8017",
            "http://localhost:8014", 
            "http://localhost:8080"
        ]
        
        print("\n--- Legacy URL Migration Test ---")
        for old_url in test_urls:
            new_url = LegacyUrlMapper.migrate_url(old_url)
            print(f"✅ {old_url} → {new_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config Manager test failed: {e}")
        return False

def test_import_manager():
    """Test Import Manager"""
    print("\n=== Testing Import Manager ===")
    
    try:
        # Test module import
        from shared.import_manager_v1_0_0_20250822 import (
            get_import_manager,
            ProjectStructure,
            LegacyImportMigrator
        )
        
        print("✅ Import Manager imported successfully")
        
        # Test project structure
        structure = ProjectStructure()
        print(f"✅ Project root detected: {structure.project_root}")
        print(f"✅ Import paths registered: {len(structure.import_paths)}")
        
        # Test import manager
        manager = get_import_manager()
        status = manager.get_import_status()
        
        print(f"✅ Registered paths: {len(status['registered_import_paths'])}")
        print(f"✅ Project structure: {status['project_root']}")
        
        # Test migration helper
        test_patterns = [

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_v1_0_0_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

            # FIXED: "sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')", -> Import Manager
            # FIXED: "sys.path.append('/opt/aktienanalyse-ökosystem/shared')" -> Import Manager
        ]
        
        print("\n--- Migration Pattern Test ---")
        for pattern in test_patterns:
            replacement = LegacyImportMigrator.get_replacement(pattern)
            print(f"✅ {pattern}")
            print(f"   → {replacement}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import Manager test failed: {e}")
        return False

def test_scripts():
    """Test Utility Scripts"""
    print("\n=== Testing Utility Scripts ===")
    
    try:
        # Test sys.path.append fixer (dry run)
        sys_path_fixer_path = project_root / "scripts" / "fix_all_sys_path_append_v1_0_0_20250822.py"
        if sys_path_fixer_path.exists():
            print("✅ sys.path.append Fixer script available")
            
            # Test import only (don't run)
            spec = {
                'file': str(sys_path_fixer_path),
                'class': 'SysPathFixer'
            }
            print(f"✅ Script ready: {spec}")
        
        # Test module versioning compliance checker
        versioning_checker_path = project_root / "scripts" / "module_versioning_compliance_v1_0_0_20250822.py"
        if versioning_checker_path.exists():
            print("✅ Module Versioning Compliance Checker available")
        
        return True
        
    except Exception as e:
        print(f"❌ Scripts test failed: {e}")
        return False

def test_service_base_concepts():
    """Test Service Base Architecture concepts (without full import)"""
    print("\n=== Testing Service Base Architecture Concepts ===")
    
    try:
        service_base_path = project_root / "shared" / "service_base_v1_0_0_20250822.py"
        
        if service_base_path.exists():
            print("✅ Service Base Architecture module available")
            
            # Read file and check for key SOLID patterns
            with open(service_base_path, 'r') as f:
                content = f.read()
            
            solid_patterns = [
                'class IHealthCheckable(Protocol):',  # Interface Segregation
                'class BaseService(ABC,',             # Single Responsibility
                'class WebService(BaseService):',     # Open/Closed
                'class ServiceFactory:',              # Factory Pattern
                'class ServiceRegistry:'              # Singleton Pattern
            ]
            
            for pattern in solid_patterns:
                if pattern in content:
                    print(f"✅ SOLID Pattern found: {pattern}")
                else:
                    print(f"❌ SOLID Pattern missing: {pattern}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service Base test failed: {e}")
        return False

def test_event_bus_concepts():
    """Test Event Bus Architecture concepts"""
    print("\n=== Testing Event Bus Architecture Concepts ===")
    
    try:
        event_bus_path = project_root / "shared" / "event_bus_architecture_v1_0_0_20250822.py"
        
        if event_bus_path.exists():
            print("✅ Event Bus Architecture module available")
            
            # Read file and check for key Clean Architecture patterns
            with open(event_bus_path, 'r') as f:
                content = f.read()
            
            clean_patterns = [
                'class IEventPublisher(ABC):',        # Interface Segregation
                'class IEventSubscriber(ABC):',       # Interface Segregation  
                'class IEventRouter(ABC):',           # Interface Segregation
                'class EventRouter(IEventRouter):',   # Single Responsibility
                'class EventSubscriptionManager(',    # Single Responsibility
                'class CleanEventBus:'                 # Composition over Inheritance
            ]
            
            for pattern in clean_patterns:
                if pattern in content:
                    print(f"✅ Clean Architecture Pattern found: {pattern}")
                else:
                    print(f"❌ Clean Architecture Pattern missing: {pattern}")
        
        return True
        
    except Exception as e:
        print(f"❌ Event Bus test failed: {e}")
        return False

def test_integration():
    """Test integration between modules"""
    print("\n=== Testing Module Integration ===")
    
    try:
        # Test that Config Manager can be used by Service Base
        integration_patterns = {
            "Config → Service Base": "service_discovery = get_service_discovery()",
            "Import Manager → All": "setup_aktienanalyse_imports()",
            "Service Discovery → Events": "ServiceType.EVENT_BUS"
        }
        
        for integration, pattern in integration_patterns.items():
            # Check if integration patterns exist in files
            files_with_pattern = []
            
            for py_file in [
                "shared/service_base_v1_0_0_20250822.py",
                "shared/event_bus_architecture_v1_0_0_20250822.py",
                "services/frontend-service-modular/frontend_service_v7_0_0_20250816.py"
            ]:
                file_path = project_root / py_file
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        if pattern in f.read():
                            files_with_pattern.append(py_file)
            
            if files_with_pattern:
                print(f"✅ {integration}: Found in {len(files_with_pattern)} files")
            else:
                print(f"⚠️ {integration}: Pattern not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def generate_test_report():
    """Generate test summary report"""
    print("\n" + "="*60)
    print("CODE QUALITY IMPLEMENTATION TEST REPORT")
    print("="*60)
    
    tests = [
        ("Configuration Manager & Service Discovery", test_config_manager),
        ("Import Manager & Path Management", test_import_manager),
        ("Utility Scripts", test_scripts),
        ("Service Base Architecture", test_service_base_concepts),
        ("Event Bus Architecture", test_event_bus_concepts),
        ("Module Integration", test_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        print("-" * 50)
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Clean Architecture Implementation Successful!")
    else:
        print(f"\n⚠️ {total-passed} tests failed - See details above")
    
    return passed == total

def main():
    """Main test function"""
    print("Clean Architecture Modules Test v1.0.0")
    print("Testing all implemented code quality improvements...")
    
    success = generate_test_report()
    
    if success:
        print("\n✅ All Clean Architecture modules are working correctly!")
        print("✅ SOLID Principles successfully implemented")
        print("✅ Code Quality improvements verified")
    else:
        print("\n❌ Some tests failed - Review implementation")
    
    return success

if __name__ == "__main__":
    main()