#!/usr/bin/env python3
"""
Import Manager - Zentrale Import-Hierarchie für das Aktienanalyse-Ökosystem
Ersetzt alle sys.path.append/insert Anti-Patterns mit strukturierter Lösung

Code-Qualität: HÖCHSTE PRIORITÄT
- Clean Code Architecture
- Single Point of Truth für Imports
- Environment-aware Pfad-Auflösung
- Eliminiert sys.path Chaos
"""

import sys
import os
from pathlib import Path
from typing import List, Optional


class ImportManager:
    """
    Zentrale Import-Verwaltung für alle Services
    Clean Architecture: KEINE hardcoded Pfade mehr
    """
    
    def __init__(self):
        self._project_root = self._detect_project_root()
        self._is_production = self._detect_environment()
        self._paths_configured = False
    
    def _detect_project_root(self) -> Path:
        """Automatische Projektwurzel-Erkennung"""
        current = Path(__file__).resolve()
        
        # Suche nach charakteristischen Projektdateien
        for parent in current.parents:
            if any((parent / marker).exists() for marker in [
                'README.md', 
                '.env', 
                'config/central_config_v1_0_0_20250821.py',
                'shared/__init__.py'
            ]):
                return parent
                
        # Fallback: Parent von shared/
        return current.parent.parent
    
    def _detect_environment(self) -> bool:
        """Erkennung von Produktions- vs Entwicklungsumgebung"""
        return self._project_root.as_posix().startswith('/opt/')
    
    def setup_paths(self) -> None:
        """
        Einmalige Pfad-Konfiguration für alle Services
        Clean Architecture: Strukturierte Hierarchie
        """
        if self._paths_configured:
            return
            
        paths_to_add = self._get_import_paths()
        
        for path in paths_to_add:
            if path.exists() and str(path) not in sys.path:
                sys.path.insert(0, str(path))
        
        self._paths_configured = True
        
    def _get_import_paths(self) -> List[Path]:
        """Definiert strukturierte Import-Hierarchie"""
        base_paths = [
            # 1. Projektwurzel (höchste Priorität)
            self._project_root,
            
            # 2. Shared Libraries
            self._project_root / 'shared',
            
            # 3. Service Directories
            self._project_root / 'services',
            
            # 4. Config Directory
            self._project_root / 'config',
            
            # 5. Service-spezifische Pfade
            self._project_root / 'services' / 'frontend-service-modular',
            self._project_root / 'services' / 'intelligent-core-service-modular',
            self._project_root / 'services' / 'broker-gateway-service-modular',
            self._project_root / 'services' / 'event-bus-service-modular',
            self._project_root / 'services' / 'data-processing-service-modular',
            self._project_root / 'services' / 'monitoring-service-modular',
            self._project_root / 'services' / 'diagnostic-service',
            self._project_root / 'services' / 'prediction-tracking-service-modular'
        ]
        
        return [path for path in base_paths if path.exists()]
    
    def get_project_root(self) -> str:
        """Projektwurzel als String zurückgeben"""
        return str(self._project_root)
    
    def is_production(self) -> bool:
        """Produktionsumgebung erkennen"""
        return self._is_production
    
    def get_service_path(self, service_name: str) -> Optional[str]:
        """Pfad zu spezifischem Service"""
        service_path = self._project_root / 'services' / service_name
        return str(service_path) if service_path.exists() else None
    
    def get_shared_path(self) -> str:
        """Shared Libraries Pfad"""
        return str(self._project_root / 'shared')
    
    def get_config_path(self) -> str:
        """Config Directory Pfad"""
        return str(self._project_root / 'config')


# Globale Import Manager Instanz
import_manager = ImportManager()

def setup_imports():
    """
    Convenience-Funktion für einfache Import-Konfiguration
    Ersetzt alle sys.path.append/insert Statements
    
    Usage:
        from shared.import_manager import setup_imports
        setup_imports()
    """
    import_manager.setup_paths()

def get_project_root() -> str:
    """Convenience-Funktion für Projektwurzel"""
    return import_manager.get_project_root()

def get_shared_path() -> str:
    """Convenience-Funktion für Shared Path"""
    return import_manager.get_shared_path()


# Auto-Setup bei Import (optional)
if __name__ != "__main__":
    # Automatische Pfad-Konfiguration beim Import
    import_manager.setup_paths()


if __name__ == "__main__":
    # Debug/Test-Modus
    print("=== Import Manager Debug ===")
    print(f"Project Root: {import_manager.get_project_root()}")
    print(f"Is Production: {import_manager.is_production()}")
    print(f"Shared Path: {import_manager.get_shared_path()}")
    print(f"Config Path: {import_manager.get_config_path()}")
    
    print("\nConfigured Paths:")
    import_manager.setup_paths()
    for i, path in enumerate(sys.path[:10]):  # Show first 10 paths
        print(f"  {i}: {path}")