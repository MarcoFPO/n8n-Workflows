#!/usr/bin/env python3
"""
Unified Import System Migration Test Suite - Issue #57
======================================================

Validiert die Migration zu Standard Import Manager:
1. Import Resolution funktioniert
2. Keine sys.path.insert() Anti-Patterns
3. StandardImportManager ordnungsgemäß initialisiert

Coverage Target: >=80%
"""

import unittest
import sys
import os
from pathlib import Path
import importlib.util

class UnifiedImportSystemTest(unittest.TestCase):
    """Test Suite für Unified Import System Migration"""
    
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
        self.services_dir = self.project_root / "services"
        
    def test_no_sys_path_insert_patterns(self):
        """Validiere dass keine sys.path.insert() Anti-Patterns vorhanden sind"""
        violations = []
        
        if self.services_dir.exists():
            for service_dir in self.services_dir.iterdir():
                if service_dir.is_dir():
                    for py_file in service_dir.rglob("*.py"):
                        try:
                            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # Skip venv files and focus on actual service files
                                if 'sys.path.insert' in content and '/venv/' not in str(py_file):
                                    violations.append(str(py_file.relative_to(self.project_root)))
                        except (OSError, IOError):
                            pass  # Skip files that can't be read
        
        self.assertEqual([], violations, 
                        f"Found sys.path.insert() anti-patterns in: {violations}")
    
    def test_standard_import_manager_usage(self):
        """Validiere StandardImportManager Verwendung in Services"""
        target_services = [
            "broker-gateway-service/main.py",
            "intelligent-core-service/main.py", 
            "ml-analytics-service/main.py",
            "event-bus-service/event_bus_daemon_v6_2_robust.py"
        ]
        
        for service_file in target_services:
            full_path = self.services_dir / service_file
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                self.assertIn('StandardImportManager', content,
                            f"{service_file} should use StandardImportManager")
                self.assertIn('setup_imports()', content,
                            f"{service_file} should call setup_imports()")
    
    def test_import_resolution_functionality(self):
        """Teste dass Import Resolution nach Migration funktioniert"""
        # Test Standard Import Manager kann geladen werden
        shared_path = self.project_root / "shared" / "standard_import_manager_v1_0_0_20250824.py"
        if not shared_path.exists():
            self.skipTest(f"StandardImportManager file not found at {shared_path}")
            
        spec = importlib.util.spec_from_file_location(
            "standard_import_manager",
            shared_path
        )
        self.assertIsNotNone(spec, "StandardImportManager module should be loadable")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test StandardImportManager Klasse existiert
        self.assertTrue(hasattr(module, 'StandardImportManager'),
                       "StandardImportManager class should exist")
        
        # Test Instanziierung funktioniert
        manager = module.StandardImportManager()
        self.assertIsNotNone(manager, "StandardImportManager should be instantiable")

if __name__ == '__main__':
    unittest.main()
