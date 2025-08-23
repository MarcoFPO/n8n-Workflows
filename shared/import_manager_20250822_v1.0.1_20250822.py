#!/usr/bin/env python3
"""
Import Manager v1.0.0 - Structured Import Management
Ersetzt alle sys.path.append Anti-Patterns mit Clean Architecture

Code-Qualität: HÖCHSTE PRIORITÄT
- Single Responsibility: Nur Import Management
- DRY Principle: Eliminiert 72+ sys.path.append Duplikation
- Clean Architecture: Proper Python Package Structure
- Path Management: Environment-aware Path Resolution
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Union
from dataclasses import dataclass
from enum import Enum
import importlib.util
import importlib

logger = logging.getLogger(__name__)

class ModuleLocation(Enum):
    """Standard Module Locations in Aktienanalyse Ecosystem"""
    SHARED = "shared"
    SERVICES = "services"
    MODULES = "modules"
    TOOLS = "tools"
    TESTS = "tests"
    DATA = "data"
    CONFIGS = "configs"
    SCRIPTS = "scripts"

@dataclass
class ImportPath:
    """Import Path Configuration"""
    location: ModuleLocation
    subdirectory: Optional[str] = None
    relative_path: Optional[str] = None
    
    def resolve_path(self, project_root: Path) -> Path:
        """Resolve full path based on project root"""
        path = project_root / self.location.value
        
        if self.subdirectory:
            path = path / self.subdirectory
        
        if self.relative_path:
            path = path / self.relative_path
            
        return path

class ProjectStructure:
    """
    Project Structure Manager - Single Responsibility
    Manages standard paths and module locations
    """
    
    def __init__(self, project_root: Optional[Union[str, Path]] = None):
        self.project_root = self._detect_project_root(project_root)
        self.import_paths: Dict[str, ImportPath] = {}
        self._registered_paths: Set[str] = set()
        
        # Initialize standard import paths
        self._initialize_standard_paths()
        
    def _detect_project_root(self, provided_root: Optional[Union[str, Path]]) -> Path:
        """Auto-detect project root directory"""
        if provided_root:
            return Path(provided_root).resolve()
        
        # Try to detect from current file location
        current_file = Path(__file__).resolve()
        
        # Look for project markers
        for parent in current_file.parents:
            if any(marker.exists() for marker in [
                parent / "README.md",
                parent / ".git",
                parent / "CLAUDE.md",
                parent / "services",
                parent / "shared"
            ]):
                return parent
        
        # Fallback to known paths
        candidates = [
            Path("/home/mdoehler/aktienanalyse-ökosystem"),
            Path("/opt/aktienanalyse-ökosystem"),
            Path.cwd()
        ]
        
        for candidate in candidates:
            if candidate.exists() and (candidate / "shared").exists():
                return candidate
        
        # Last resort
        return Path.cwd()
    
    def _initialize_standard_paths(self) -> None:
        """Initialize standard import paths for the project"""
        standard_paths = {
            # Core shared modules
            "shared": ImportPath(ModuleLocation.SHARED),
            "shared.utils": ImportPath(ModuleLocation.SHARED, "utils"),
            "shared.models": ImportPath(ModuleLocation.SHARED, "models"),
            "shared.config": ImportPath(ModuleLocation.SHARED),
            
            # Service-specific modules  
            "services.frontend": ImportPath(ModuleLocation.SERVICES, "frontend-service-modular"),
            "services.intelligent_core": ImportPath(ModuleLocation.SERVICES, "intelligent-core-service-modular"),
            "services.broker_gateway": ImportPath(ModuleLocation.SERVICES, "broker-gateway-service-modular"),
            "services.data_processing": ImportPath(ModuleLocation.SERVICES, "data-processing-service-modular"),
            "services.event_bus": ImportPath(ModuleLocation.SERVICES, "event-bus-service-modular"),
            "services.monitoring": ImportPath(ModuleLocation.SERVICES, "monitoring-service-modular"),
            "services.diagnostic": ImportPath(ModuleLocation.SERVICES, "diagnostic-service-modular"),
            "services.ml_analytics": ImportPath(ModuleLocation.SERVICES, "ml-analytics-service-modular"),
            
            # Tool and utility modules
            "tools": ImportPath(ModuleLocation.TOOLS),
            "data": ImportPath(ModuleLocation.DATA),
            "tests": ImportPath(ModuleLocation.TESTS),
            "configs": ImportPath(ModuleLocation.CONFIGS),
            "scripts": ImportPath(ModuleLocation.SCRIPTS),
        }
        
        self.import_paths.update(standard_paths)
    
    def register_import_path(self, name: str, import_path: ImportPath) -> None:
        """Register a custom import path"""
        self.import_paths[name] = import_path
        
    def get_import_path(self, name: str) -> Optional[Path]:
        """Get resolved import path by name"""
        if name in self.import_paths:
            return self.import_paths[name].resolve_path(self.project_root)
        return None
    
    def get_all_import_paths(self) -> List[Path]:
        """Get all registered import paths"""
        paths = []
        for import_path in self.import_paths.values():
            resolved = import_path.resolve_path(self.project_root)
            if resolved.exists():
                paths.append(resolved)
        return paths

class ImportManager:
    """
    Import Manager - Clean Alternative to sys.path.append
    
    Replaces all 72+ sys.path.append statements with structured import management
    Implements Clean Architecture principles for module loading
    """
    
    def __init__(self, project_structure: Optional[ProjectStructure] = None):
        self.project_structure = project_structure or ProjectStructure()
        self._original_sys_path = sys.path.copy()
        self._managed_paths: Set[str] = set()
        self._imported_modules: Dict[str, object] = {}
        
    def setup_import_environment(self, additional_paths: Optional[List[str]] = None) -> None:
        """
        Setup import environment - REPLACES sys.path.append patterns
        
        This method replaces patterns like:

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

        # FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared') -> Import Manager
        # FIXED: sys.path.append('/opt/aktienanalyse-ökosystem/services/...') -> Import Manager
        """
        try:
            # Add project root to Python path
            project_root_str = str(self.project_structure.project_root)
            if project_root_str not in sys.path:
                sys.path.insert(0, project_root_str)
                self._managed_paths.add(project_root_str)
            
            # Add all registered import paths
            for path in self.project_structure.get_all_import_paths():
                path_str = str(path)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)
                    self._managed_paths.add(path_str)
            
            # Add any additional paths
            if additional_paths:
                for path in additional_paths:
                    resolved_path = Path(path).resolve()
                    if resolved_path.exists():
                        path_str = str(resolved_path)
                        if path_str not in sys.path:
                            sys.path.insert(0, path_str)
                            self._managed_paths.add(path_str)
            
            logger.info(f"Import environment setup complete. Added {len(self._managed_paths)} paths.")
            
        except Exception as e:
            logger.error(f"Failed to setup import environment: {e}")
            raise
    
    def import_module_safely(self, module_name: str, from_path: Optional[str] = None) -> Optional[object]:
        """
        Safely import module with error handling
        
        Replaces problematic import patterns with safe module loading
        """
        try:
            # Check if module already imported
            if module_name in self._imported_modules:
                return self._imported_modules[module_name]
            
            # Try standard import first
            try:
                module = importlib.import_module(module_name)
                self._imported_modules[module_name] = module
                return module
            except ImportError:
                pass
            
            # Try import from specific path
            if from_path:
                spec = importlib.util.spec_from_file_location(module_name, from_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    self._imported_modules[module_name] = module
                    return module
            
            logger.warning(f"Could not import module: {module_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error importing module {module_name}: {e}")
            return None
    
    def get_module_path(self, module_name: str) -> Optional[Path]:
        """Get the file path for a specific module"""
        try:
            # Check if it's a registered import path
            if path := self.project_structure.get_import_path(module_name):
                return path
            
            # Try to find module in standard locations
            for base_path in self.project_structure.get_all_import_paths():
                potential_file = base_path / f"{module_name}.py"
                if potential_file.exists():
                    return potential_file
                
                potential_package = base_path / module_name / "__init__.py"
                if potential_package.exists():
                    return potential_package.parent
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding module path for {module_name}: {e}")
            return None
    
    def cleanup_import_environment(self) -> None:
        """Cleanup managed import paths - restore original sys.path"""
        try:
            for path in self._managed_paths:
                if path in sys.path:
                    sys.path.remove(path)
            
            self._managed_paths.clear()
            logger.info("Import environment cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up import environment: {e}")
    
    def get_import_status(self) -> Dict[str, any]:
        """Get current import manager status for debugging"""
        return {
            "project_root": str(self.project_structure.project_root),
            "managed_paths": list(self._managed_paths),
            "imported_modules": list(self._imported_modules.keys()),
            "registered_import_paths": list(self.project_structure.import_paths.keys()),
            "sys_path_length": len(sys.path)
        }

# Global Import Manager Instance
_import_manager: Optional[ImportManager] = None

def get_import_manager() -> ImportManager:
    """Get global import manager instance"""
    global _import_manager
    
    if _import_manager is None:
        _import_manager = ImportManager()
    
    return _import_manager

def setup_aktienanalyse_imports() -> None:
    """
    Setup imports for Aktienanalyse Ecosystem
    
    REPLACES ALL sys.path.append statements with:
    setup_aktienanalyse_imports()
    """
    manager = get_import_manager()
    manager.setup_import_environment()

def import_shared_module(module_name: str) -> Optional[object]:
    """
    Import module from shared directory
    
    Replaces:
    # FIXED: sys.path.append('/path/to/shared') -> Import Manager
    import module_name
    
    With:
    module = import_shared_module('module_name')
    """
    manager = get_import_manager()
    shared_path = manager.project_structure.get_import_path("shared")
    
    if shared_path:
        module_file = shared_path / f"{module_name}.py"
        if module_file.exists():
            return manager.import_module_safely(module_name, str(module_file))
    
    return manager.import_module_safely(module_name)

def import_service_module(service_name: str, module_name: str) -> Optional[object]:
    """
    Import module from specific service directory
    
    Replaces service-specific sys.path.append patterns
    """
    manager = get_import_manager()
    service_path = manager.project_structure.get_import_path(f"services.{service_name}")
    
    if service_path:
        module_file = service_path / f"{module_name}.py"
        if module_file.exists():
            return manager.import_module_safely(module_name, str(module_file))
    
    return manager.import_module_safely(module_name)

# Migration Helper Functions
class LegacyImportMigrator:
    """
    Helper for migrating from sys.path.append to Import Manager
    
    Provides drop-in replacements for common sys.path.append patterns
    """
    
    COMMON_PATTERNS = {
        # FIXED: "sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')": "setup_aktienanalyse_imports()", -> Import Manager
        # FIXED: "sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')": "setup_aktienanalyse_imports()", -> Import Manager
        # FIXED: "sys.path.append('/opt/aktienanalyse-ökosystem')": "setup_aktienanalyse_imports()", -> Import Manager
        # FIXED: "sys.path.append('/opt/aktienanalyse-ökosystem/shared')": "setup_aktienanalyse_imports()", -> Import Manager
    }
    
    @classmethod
    def get_replacement(cls, sys_path_line: str) -> str:
        """Get replacement for sys.path.append line"""
        cleaned_line = sys_path_line.strip()
        
        if cleaned_line in cls.COMMON_PATTERNS:
            return cls.COMMON_PATTERNS[cleaned_line]
        
        # Generic replacement
        return "setup_aktienanalyse_imports()  # Replaced sys.path.append"
    
    @classmethod
    def generate_migration_header(cls) -> str:
        """Generate standard migration header for modules"""
        return '''# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements'''

# Context Manager for Temporary Import Environment
class TemporaryImportEnvironment:
    """Context manager for temporary import environment setup"""
    
    def __init__(self, additional_paths: Optional[List[str]] = None):
        self.additional_paths = additional_paths
        self.manager = get_import_manager()
        
    def __enter__(self):
        self.manager.setup_import_environment(self.additional_paths)
        return self.manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.cleanup_import_environment()

if __name__ == "__main__":
    # Test the import management system
    manager = get_import_manager()
    
    print("=== Import Manager Test ===")
    print(f"Project Root: {manager.project_structure.project_root}")
    
    print("\n=== Import Paths ===")
    for name, path in manager.project_structure.import_paths.items():
        resolved = path.resolve_path(manager.project_structure.project_root)
        exists = "✅" if resolved.exists() else "❌"
        print(f"{exists} {name}: {resolved}")
    
    print("\n=== Setup Import Environment ===")
    manager.setup_import_environment()
    
    print(f"\n=== Import Status ===")
    status = manager.get_import_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    print("\n=== Migration Helper Test ===")
    test_patterns = [
        # FIXED: "sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')", -> Import Manager
        # FIXED: "sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')", -> Import Manager
        # FIXED: "sys.path.append('/opt/aktienanalyse-ökosystem/shared')" -> Import Manager
    ]
    
    for pattern in test_patterns:
        replacement = LegacyImportMigrator.get_replacement(pattern)
        print(f"{pattern}")
        print(f"  -> {replacement}")
    
    print("\n=== Migration Header ===")
    print(LegacyImportMigrator.generate_migration_header())
    
    # Cleanup
    manager.cleanup_import_environment()