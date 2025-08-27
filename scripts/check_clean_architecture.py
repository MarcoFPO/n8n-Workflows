#!/usr/bin/env python3
"""
Clean Architecture Compliance Checker
Validates that Clean Architecture principles are followed in the codebase.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Clean Architecture Layer Definitions
LAYERS = {
    'domain': {
        'allowed_imports': ['domain', 'typing', 'abc', 'enum', 'dataclasses', 'datetime', 'uuid', 'decimal'],
        'forbidden_imports': ['application', 'infrastructure', 'presentation'],
        'description': 'Domain Layer (Business Logic)'
    },
    'application': {
        'allowed_imports': ['domain', 'application', 'typing', 'abc'],
        'forbidden_imports': ['infrastructure', 'presentation'],
        'description': 'Application Layer (Use Cases)'
    },
    'infrastructure': {
        'allowed_imports': ['domain', 'application', 'infrastructure', 'typing'],
        'forbidden_imports': [],
        'description': 'Infrastructure Layer (External Services)'
    },
    'presentation': {
        'allowed_imports': ['domain', 'application', 'presentation', 'typing'],
        'forbidden_imports': [],
        'description': 'Presentation Layer (API/Controllers)'
    }
}

class ArchitectureViolation:
    def __init__(self, file_path: str, layer: str, violation_type: str, details: str):
        self.file_path = file_path
        self.layer = layer
        self.violation_type = violation_type
        self.details = details
    
    def __str__(self):
        return f"❌ {self.violation_type} in {self.layer} layer: {self.file_path}\n   {self.details}"

class CleanArchitectureChecker:
    def __init__(self, root_path: str = "services"):
        self.root_path = Path(root_path)
        self.violations: List[ArchitectureViolation] = []
        
    def check_all_services(self) -> bool:
        """Check all services for Clean Architecture compliance."""
        print("🏗️  Checking Clean Architecture Compliance...")
        
        if not self.root_path.exists():
            print(f"❌ Services directory not found: {self.root_path}")
            return False
            
        success = True
        service_count = 0
        
        for service_dir in self.root_path.iterdir():
            if service_dir.is_dir() and not service_dir.name.startswith('.'):
                service_count += 1
                print(f"\n📂 Checking service: {service_dir.name}")
                
                if not self.check_service(service_dir):
                    success = False
        
        print(f"\n📊 Checked {service_count} services")
        self.print_summary()
        
        return success and len(self.violations) == 0
    
    def check_service(self, service_path: Path) -> bool:
        """Check a single service for Clean Architecture compliance."""
        success = True
        
        # Check each layer directory
        for layer_name in LAYERS.keys():
            layer_path = service_path / layer_name
            if layer_path.exists():
                if not self.check_layer(layer_path, layer_name):
                    success = False
                    
        return success
    
    def check_layer(self, layer_path: Path, layer_name: str) -> bool:
        """Check a specific layer for compliance."""
        success = True
        
        for python_file in layer_path.rglob("*.py"):
            if python_file.name == "__init__.py":
                continue
                
            if not self.check_file_imports(python_file, layer_name):
                success = False
                
            if not self.check_file_structure(python_file, layer_name):
                success = False
                
        return success
    
    def check_file_imports(self, file_path: Path, layer_name: str) -> bool:
        """Check imports in a Python file for layer compliance."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            success = True
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if not self.validate_import(node, file_path, layer_name):
                        success = False
                        
            return success
            
        except Exception as e:
            self.violations.append(ArchitectureViolation(
                str(file_path), layer_name, "PARSE_ERROR", 
                f"Could not parse file: {e}"
            ))
            return False
    
    def validate_import(self, node: ast.AST, file_path: Path, layer_name: str) -> bool:
        """Validate a specific import statement."""
        layer_config = LAYERS[layer_name]
        module_name = ""
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module if node.module else ""
            
        # Check for forbidden layer imports
        for forbidden in layer_config['forbidden_imports']:
            if forbidden in module_name:
                self.violations.append(ArchitectureViolation(
                    str(file_path), layer_name, "FORBIDDEN_IMPORT",
                    f"Importing from forbidden layer '{forbidden}': {module_name}"
                ))
                return False
                
        return True
    
    def check_file_structure(self, file_path: Path, layer_name: str) -> bool:
        """Check file structure and naming conventions."""
        success = True
        
        # Domain Layer specific checks
        if layer_name == 'domain':
            success &= self.check_domain_layer_structure(file_path)
        elif layer_name == 'application':
            success &= self.check_application_layer_structure(file_path)
        elif layer_name == 'infrastructure':
            success &= self.check_infrastructure_layer_structure(file_path)
        elif layer_name == 'presentation':
            success &= self.check_presentation_layer_structure(file_path)
            
        return success
    
    def check_domain_layer_structure(self, file_path: Path) -> bool:
        """Check Domain layer specific structure."""
        expected_subdirs = ['entities', 'value_objects', 'services', 'repositories']
        parent_dir = file_path.parent.name
        
        if parent_dir not in expected_subdirs and parent_dir != 'domain':
            self.violations.append(ArchitectureViolation(
                str(file_path), 'domain', "STRUCTURE_VIOLATION",
                f"File should be in one of: {expected_subdirs}"
            ))
            return False
            
        return True
    
    def check_application_layer_structure(self, file_path: Path) -> bool:
        """Check Application layer specific structure."""
        expected_subdirs = ['use_cases', 'interfaces', 'dtos']
        parent_dir = file_path.parent.name
        
        if parent_dir not in expected_subdirs and parent_dir != 'application':
            self.violations.append(ArchitectureViolation(
                str(file_path), 'application', "STRUCTURE_VIOLATION", 
                f"File should be in one of: {expected_subdirs}"
            ))
            return False
            
        return True
    
    def check_infrastructure_layer_structure(self, file_path: Path) -> bool:
        """Check Infrastructure layer specific structure."""
        expected_subdirs = ['persistence', 'external_services', 'events', 'container']
        parent_dir = file_path.parent.name
        
        if parent_dir not in expected_subdirs and parent_dir != 'infrastructure':
            self.violations.append(ArchitectureViolation(
                str(file_path), 'infrastructure', "STRUCTURE_VIOLATION",
                f"File should be in one of: {expected_subdirs}"  
            ))
            return False
            
        return True
    
    def check_presentation_layer_structure(self, file_path: Path) -> bool:
        """Check Presentation layer specific structure."""
        expected_subdirs = ['controllers', 'models', 'middleware']
        parent_dir = file_path.parent.name
        
        if parent_dir not in expected_subdirs and parent_dir != 'presentation':
            self.violations.append(ArchitectureViolation(
                str(file_path), 'presentation', "STRUCTURE_VIOLATION",
                f"File should be in one of: {expected_subdirs}"
            ))
            return False
            
        return True
    
    def print_summary(self):
        """Print compliance check summary."""
        if not self.violations:
            print("\n✅ Clean Architecture Compliance: PASSED")
            print("🏗️  All layers follow Clean Architecture principles!")
            return
            
        print(f"\n❌ Clean Architecture Compliance: FAILED")
        print(f"🚨 Found {len(self.violations)} violation(s):")
        
        # Group violations by type
        violation_types = {}
        for violation in self.violations:
            if violation.violation_type not in violation_types:
                violation_types[violation.violation_type] = []
            violation_types[violation.violation_type].append(violation)
            
        for violation_type, violations in violation_types.items():
            print(f"\n{violation_type} ({len(violations)} violations):")
            for violation in violations:
                print(f"  {violation}")
                
        print("\n💡 Clean Architecture Remediation Guide:")
        print("  • Domain layer should only import domain entities and value objects")  
        print("  • Application layer should only import domain and application modules")
        print("  • Infrastructure layer can import domain and application modules")
        print("  • Presentation layer can import domain and application modules")
        print("  • Each layer should have proper subdirectory structure")

def main():
    """Main entry point for Clean Architecture compliance checking."""
    checker = CleanArchitectureChecker()
    
    print("🏗️  Clean Architecture Compliance Checker v1.0.0")
    print("=" * 60)
    
    if checker.check_all_services():
        print("\n🎉 All services comply with Clean Architecture principles!")
        sys.exit(0)
    else:
        print("\n💥 Clean Architecture violations found!")
        print("📋 Please fix the violations above and run the check again.")
        sys.exit(1)

if __name__ == "__main__":
    main()