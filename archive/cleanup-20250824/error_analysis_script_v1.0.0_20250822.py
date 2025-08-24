#!/usr/bin/env python3
"""
Umfassende Fehleranalyse für das aktienanalyse-ökosystem
Analysiert Python-Syntax, Imports, Logic-Fehler und Architektur-Probleme
"""

import ast
import os
import sys
import json
import importlib.util
import traceback
from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

class CodeErrorAnalyzer:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.errors = {
            'syntax_errors': [],
            'import_errors': [],
            'logic_errors': [],
            'event_bus_errors': [],
            'database_errors': [],
            'service_errors': [],
            'systemd_errors': []
        }
    
    def analyze_syntax_errors(self, file_path: Path) -> List[Dict]:
        """Analysiert Python-Syntax-Fehler"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # AST-basierte Syntax-Überprüfung
            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append({
                    'file': str(file_path),
                    'line': e.lineno,
                    'column': e.offset,
                    'type': 'SyntaxError',
                    'message': str(e),
                    'impact': 'CRITICAL - Module kann nicht geladen werden'
                })
        except Exception as e:
            errors.append({
                'file': str(file_path),
                'line': 0,
                'type': 'FileReadError',
                'message': f"Kann Datei nicht lesen: {e}",
                'impact': 'CRITICAL - Datei unzugänglich'
            })
        
        return errors
    
    def analyze_import_errors(self, file_path: Path) -> List[Dict]:
        """Analysiert Import-Fehler und zirkuläre Abhängigkeiten"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST für Import-Analyse
            try:
                tree = ast.parse(content)
            except:
                return []  # Syntax-Fehler bereits erfasst
            
            # Sammle alle Imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        for alias in node.names:
                            imports.append(f"{node.module}.{alias.name}")
            
            # Prüfe fehlende Module
            for imp in imports:
                try:
                    # Versuche Standard-Imports
                    if '.' not in imp or imp.startswith('shared.') or imp.startswith('services.'):
                        continue
                    importlib.util.find_spec(imp)
                except (ImportError, ModuleNotFoundError, ValueError):
                    errors.append({
                        'file': str(file_path),
                        'type': 'ImportError',
                        'message': f"Modul '{imp}' nicht gefunden",
                        'impact': 'HIGH - Runtime Error beim Import',
                        'solution': f"Installiere Paket oder prüfe Import-Pfad für '{imp}'"
                    })
        
        except Exception as e:
            errors.append({
                'file': str(file_path),
                'type': 'ImportAnalysisError',
                'message': f"Import-Analyse fehlgeschlagen: {e}",
                'impact': 'MEDIUM - Kann Imports nicht validieren'
            })
        
        return errors
    
    def analyze_logic_errors(self, file_path: Path) -> List[Dict]:
        """Analysiert Logic/Runtime-Fehler"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Prüfe typische Logic-Fehler
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Null/None Pointer Probleme
                if re.search(r'\.(\w+)\(\)(?!\s*is\s+not\s+None)', line) and 'None' in line:
                    errors.append({
                        'file': str(file_path),
                        'line': i,
                        'type': 'PotentialNoneError',
                        'message': 'Potentieller None-Pointer-Zugriff ohne Validierung',
                        'impact': 'MEDIUM - Runtime AttributeError möglich',
                        'solution': 'Füge None-Check hinzu: if obj is not None:'
                    })
                
                # Unbehandelte Exception-Bereiche
                if 'except:' in line and 'pass' in lines[i] if i < len(lines) else False:
                    errors.append({
                        'file': str(file_path),
                        'line': i,
                        'type': 'SilentExceptionHandling',
                        'message': 'Exception wird ohne Logging oder Behandlung ignoriert',
                        'impact': 'HIGH - Fehler werden verschluckt',
                        'solution': 'Füge Logging oder spezifische Behandlung hinzu'
                    })
                
                # Offene Resource Leaks
                if 'open(' in line and 'with' not in line:
                    errors.append({
                        'file': str(file_path),
                        'line': i,
                        'type': 'ResourceLeak',
                        'message': 'Datei ohne context manager geöffnet',
                        'impact': 'MEDIUM - Potentieller Resource Leak',
                        'solution': 'Verwende "with open(...) as f:" Pattern'
                    })
        
        except Exception as e:
            errors.append({
                'file': str(file_path),
                'type': 'LogicAnalysisError',
                'message': f"Logic-Analyse fehlgeschlagen: {e}",
                'impact': 'LOW - Analyse nicht vollständig'
            })
        
        return errors
    
    def analyze_event_bus_errors(self, file_path: Path) -> List[Dict]:
        """Analysiert Event-Bus Architecture Fehler"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Event-Bus spezifische Fehler
            if 'event_bus' in str(file_path).lower() or 'event' in content.lower():
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    # Fehlende Error Handling bei Events
                    if 'publish' in line.lower() and 'try:' not in ''.join(lines[max(0,i-3):i]):
                        errors.append({
                            'file': str(file_path),
                            'line': i,
                            'type': 'EventPublishNoErrorHandling',
                            'message': 'Event-Publishing ohne Error Handling',
                            'impact': 'HIGH - Event-Verlust bei Fehlern',
                            'solution': 'Wrappe Event-Publishing in try-except Block'
                        })
                    
                    # Event Schema Violations
                    if 'event' in line.lower() and '{' in line and 'schema' not in content.lower():
                        errors.append({
                            'file': str(file_path),
                            'line': i,
                            'type': 'MissingEventSchema',
                            'message': 'Event-Erstellung ohne Schema-Validierung',
                            'impact': 'MEDIUM - Inkonsistente Event-Struktur',
                            'solution': 'Implementiere Event-Schema-Validierung'
                        })
        
        except Exception as e:
            errors.append({
                'file': str(file_path),
                'type': 'EventBusAnalysisError',
                'message': f"Event-Bus-Analyse fehlgeschlagen: {e}",
                'impact': 'LOW - Event-Bus-Analyse nicht vollständig'
            })
        
        return errors
    
    def analyze_database_errors(self, file_path: Path) -> List[Dict]:
        """Analysiert Database/Persistence Fehler"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if any(db in content.lower() for db in ['sqlite', 'postgresql', 'execute', 'cursor']):
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    # SQL Injection Potentiale
                    if 'execute' in line and '+' in line and 'format' in line:
                        errors.append({
                            'file': str(file_path),
                            'line': i,
                            'type': 'SQLInjectionRisk',
                            'message': 'Potentielle SQL-Injection durch String-Konkatenation',
                            'impact': 'CRITICAL - Sicherheitsrisiko',
                            'solution': 'Verwende Parameterized Queries'
                        })
                    
                    # Connection ohne Transaction
                    if 'connect(' in line and 'commit' not in content:
                        errors.append({
                            'file': str(file_path),
                            'line': i,
                            'type': 'NoTransactionHandling',
                            'message': 'DB-Connection ohne erkennbare Transaction-Behandlung',
                            'impact': 'MEDIUM - Potentielle Dateninkonsistenz',
                            'solution': 'Implementiere Transaction-Management'
                        })
        
        except Exception as e:
            errors.append({
                'file': str(file_path),
                'type': 'DatabaseAnalysisError',
                'message': f"Database-Analyse fehlgeschlagen: {e}",
                'impact': 'LOW - Database-Analyse nicht vollständig'
            })
        
        return errors
    
    def analyze_service_errors(self, file_path: Path) -> List[Dict]:
        """Analysiert API/Service Integration Fehler"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Port-Konflikte
                if 'port' in line.lower() and any(port in line for port in ['8080', '8000', '5000']):
                    errors.append({
                        'file': str(file_path),
                        'line': i,
                        'type': 'PotentialPortConflict',
                        'message': 'Verwendung häufig genutzter Ports',
                        'impact': 'MEDIUM - Service-Start-Probleme möglich',
                        'solution': 'Verwende eindeutige Port-Konfiguration'
                    })
                
                # Fehlende Health Checks
                if 'flask' in content.lower() and '/health' not in content.lower():
                    errors.append({
                        'file': str(file_path),
                        'line': 0,
                        'type': 'MissingHealthCheck',
                        'message': 'Service ohne Health-Check Endpoint',
                        'impact': 'MEDIUM - Monitoring nicht möglich',
                        'solution': 'Implementiere /health Endpoint'
                    })
        
        except Exception as e:
            errors.append({
                'file': str(file_path),
                'type': 'ServiceAnalysisError',
                'message': f"Service-Analyse fehlgeschlagen: {e}",
                'impact': 'LOW - Service-Analyse nicht vollständig'
            })
        
        return errors
    
    def run_analysis(self):
        """Führt umfassende Analyse durch"""
        print("🔍 Starte umfassende Fehleranalyse...")
        
        # Analysiere Python-Dateien in services/ und shared/
        python_files = []
        for pattern in ['services/**/*.py', 'shared/**/*.py']:
            python_files.extend(self.base_path.glob(pattern))
        
        print(f"📊 Analysiere {len(python_files)} Python-Dateien...")
        
        for file_path in python_files:
            if file_path.is_file():
                # Syntax-Fehler
                self.errors['syntax_errors'].extend(self.analyze_syntax_errors(file_path))
                
                # Import-Fehler
                self.errors['import_errors'].extend(self.analyze_import_errors(file_path))
                
                # Logic-Fehler
                self.errors['logic_errors'].extend(self.analyze_logic_errors(file_path))
                
                # Event-Bus Fehler
                self.errors['event_bus_errors'].extend(self.analyze_event_bus_errors(file_path))
                
                # Database-Fehler
                self.errors['database_errors'].extend(self.analyze_database_errors(file_path))
                
                # Service-Fehler
                self.errors['service_errors'].extend(self.analyze_service_errors(file_path))
        
        return self.errors
    
    def generate_report(self):
        """Generiert detaillierten Fehlerbericht"""
        total_errors = sum(len(errors) for errors in self.errors.values())
        
        print(f"\n🚨 FEHLERANALYSE ABGESCHLOSSEN - {total_errors} Probleme gefunden\n")
        print("=" * 80)
        
        for category, error_list in self.errors.items():
            if error_list:
                print(f"\n📋 {category.upper().replace('_', ' ')} ({len(error_list)} Probleme)")
                print("-" * 60)
                
                for error in error_list[:10]:  # Zeige erste 10 Fehler pro Kategorie
                    print(f"🔸 Datei: {error['file']}")
                    if 'line' in error:
                        print(f"   Zeile: {error['line']}")
                    print(f"   Typ: {error['type']}")
                    print(f"   Nachricht: {error['message']}")
                    print(f"   Auswirkung: {error['impact']}")
                    if 'solution' in error:
                        print(f"   Lösung: {error['solution']}")
                    print()
                
                if len(error_list) > 10:
                    print(f"   ... und {len(error_list) - 10} weitere Fehler in dieser Kategorie")
        
        return self.errors

if __name__ == "__main__":
    base_path = "/home/mdoehler/aktienanalyse-ökosystem"
    analyzer = CodeErrorAnalyzer(base_path)
    
    errors = analyzer.run_analysis()
    report = analyzer.generate_report()
    
    # Speichere detaillierten Bericht
    with open(f"{base_path}/error_analysis_report_20250822.json", 'w') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detaillierter Bericht gespeichert: error_analysis_report_20250822.json")