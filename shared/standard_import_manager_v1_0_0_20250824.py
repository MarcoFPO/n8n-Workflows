#!/usr/bin/env python3
"""
Standard Import Manager v1.0.0 - Minimal Implementation
Ersetzt sys.path.append Anti-Patterns für Clean Architecture
Issue #65 Integration-Fix
"""

import os
import sys
from pathlib import Path
from typing import List


class ImportPath:
    """Import Path Konfiguration"""
    
    def __init__(self, path: str, priority: int = 100):
        self.path = path
        self.priority = priority


class StandardImportManager:
    """
    Standard Import Manager - Minimale Implementation
    Verwaltet Python Import Paths für Aktienanalyse-Ökosystem
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or self._detect_project_root())
        self.import_paths: List[ImportPath] = []
        self._setup_standard_paths()
    
    def _detect_project_root(self) -> str:
        """Detektiere Projekt-Root"""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / 'services').exists() and (current / 'shared').exists():
                return str(current)
            current = current.parent
        return "/home/mdoehler/aktienanalyse-ökosystem"
    
    def _setup_standard_paths(self):
        """Setup Standard Import Paths"""
        root = self.project_root
        
        # Core paths
        self.import_paths.extend([
            ImportPath(str(root), 1),
            ImportPath(str(root / 'shared'), 10),
            ImportPath(str(root / 'modules'), 20),
            ImportPath(str(root / 'services'), 30),
        ])
    
    def setup_imports(self):
        """Setup Import Paths"""
        self.setup_project_paths()
    
    def setup_project_paths(self):
        """Setup alle Project Paths"""
        # Sortiere nach Priorität
        sorted_paths = sorted(self.import_paths, key=lambda x: x.priority)
        
        for import_path in sorted_paths:
            if os.path.exists(import_path.path) and import_path.path not in sys.path:
                sys.path.insert(0, import_path.path)


def setup_aktienanalyse_imports():
    """
    Convenience Function für Setup
    Ersetzt alle sys.path.append() Aufrufe
    """
    manager = StandardImportManager()
    manager.setup_imports()
    

# Auto-setup wenn als Modul importiert
if __name__ != "__main__":
    setup_aktienanalyse_imports()