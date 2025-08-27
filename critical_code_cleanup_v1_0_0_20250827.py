#!/usr/bin/env python3
"""
Critical Code Cleanup Script v1.0.0
Aktienanalyse Ökosystem - Code Quality & Clean Architecture

BEREINIGT:
- 115+ Service-Duplikate  
- Multiple Versionen (v6.0.0, v6.1.0, v6.2.0)
- Backup-Dateien (.backup, .tar.gz)
- Container-Duplikate
- Legacy Module Collections

CLEAN ARCHITECTURE PRINCIPLES:
- Eine autoritative Version pro Service
- SOLID Principles befolgt
- DRY - Keine Code-Duplikation
- Maintainability über alles

Autor: Claude Code Quality Specialist
Datum: 27. August 2025
Version: 1.0.0 - Critical Cleanup
"""

import os
import shutil
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('critical_cleanup_log_20250827.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CriticalCodeCleaner:
    """
    Critical Code Cleanup für Aktienanalyse Ökosystem
    
    BEREINIGUNGSAUFGABEN:
    1. Service-Duplikate archivieren
    2. Container-Versionen konsolidieren  
    3. Backup-Dateien bereinigen
    4. Legacy Collections archivieren
    5. Autoritative Versionen identifizieren
    """
    
    def __init__(self):
        self.project_root = Path("/home/mdoehler/aktienanalyse-ökosystem")
        self.archive_dir = self.project_root / "archive" / f"critical_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.cleanup_report = {
            'timestamp': datetime.now().isoformat(),
            'files_moved': [],
            'files_deleted': [],
            'services_consolidated': [],
            'errors': []
        }
        
        # Service-spezifische Duplikate (REDUNDANT - LÖSCHEN)
        self.service_duplicates = {
            'frontend-service': [
                'main_clean_v1_0_0.py',
                'main_clean_v1_0_0_fixed.py', 
                'main_clean_v1_0_0_production.py',
                'main_enhanced_gui.py',
                'main_v8_1_0_enhanced_averages.py',
                'main.py.backup_20250826_190147'
            ],
            'ml-analytics-service': [
                'main_v6_0_0.py',
                'main_v6_1_0.py', 
                'main_v6_1_1.py',
                'main_refactored.py',
                'main_backup_original.py',
                'migration_script.py',
                'infrastructure/container_v6_1_0.py',
                'infrastructure/di_container.py'
            ],
            'prediction-tracking-service': [
                'main_v6_0_0.py',
                'main_v6_1_0.py',
                'main_v6_2_0_enhanced_averages.py', 
                'main_ml_predictions_enhanced.py',
                'simple_enhanced_api.py',
                'infrastructure/container_v6_1_0.py'
            ],
            'data-processing-service': [
                'main_v6_0_0.py',
                'main_v6_1_0.py',
                'infrastructure/container_v6_1_0.py'
            ],
            'marketcap-service': [
                'main_v6_0_0.py', 
                'main_v6_1_0.py',
                'infrastructure/container_v6_1_0.py'
            ],
            'diagnostic-service': [
                'infrastructure/container_v6_1_0.py'
            ]
        }
        
        # Archive-Dateien (KOMPLETT LÖSCHEN)
        self.archive_files = [
            'backups/**/*.tar.gz',
            'services/**/*.tar.gz',
            'services/**/clean_architecture.tar.gz',
            'services/**/ml-analytics-refactored.tar.gz'
        ]
        
        # Legacy Collections (ARCHIVIEREN)
        self.legacy_collections = [
            'services/ml-analytics-service/legacy_modules_collection_v1_0_0_20250818.py',
            'services/ml-analytics-service/infrastructure/legacy_adapters/'
        ]

    def create_archive_structure(self):
        """Erstelle Archive-Verzeichnisstruktur"""
        try:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Archive-Verzeichnis erstellt: {self.archive_dir}")
            
            # Unterverzeichnisse für verschiedene Dateitypen
            (self.archive_dir / "service_duplicates").mkdir(exist_ok=True)
            (self.archive_dir / "archive_files").mkdir(exist_ok=True) 
            (self.archive_dir / "legacy_collections").mkdir(exist_ok=True)
            (self.archive_dir / "backup_files").mkdir(exist_ok=True)
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Archive-Verzeichnisses: {e}")
            self.cleanup_report['errors'].append(f"Archive creation error: {e}")

    def move_service_duplicates(self):
        """Verschiebe Service-Duplikate ins Archiv"""
        logger.info("=== SERVICE-DUPLIKATE BEREINIGUNG ===")
        
        for service_name, duplicate_files in self.service_duplicates.items():
            service_path = self.project_root / "services" / service_name
            archive_service_path = self.archive_dir / "service_duplicates" / service_name
            
            if not service_path.exists():
                logger.warning(f"Service-Verzeichnis nicht gefunden: {service_path}")
                continue
                
            archive_service_path.mkdir(parents=True, exist_ok=True)
            
            for duplicate_file in duplicate_files:
                source_file = service_path / duplicate_file
                if source_file.exists():
                    dest_file = archive_service_path / duplicate_file
                    
                    try:
                        # Erstelle Zielverzeichnis falls notwendig
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.move(str(source_file), str(dest_file))
                        logger.info(f"Verschoben: {source_file} -> {dest_file}")
                        self.cleanup_report['files_moved'].append({
                            'source': str(source_file),
                            'destination': str(dest_file),
                            'type': 'service_duplicate'
                        })
                        
                    except Exception as e:
                        logger.error(f"Fehler beim Verschieben {source_file}: {e}")
                        self.cleanup_report['errors'].append(f"Move error {source_file}: {e}")
                        
            self.cleanup_report['services_consolidated'].append({
                'service': service_name,
                'duplicates_moved': len([f for f in duplicate_files if (service_path / f).exists()])
            })

    def remove_archive_files(self):
        """Entferne alle .tar.gz Archive und Backup-Dateien"""
        logger.info("=== ARCHIVE-DATEIEN BEREINIGUNG ===")
        
        # Finde alle .tar.gz Dateien
        for archive_pattern in self.archive_files:
            for archive_file in self.project_root.glob(archive_pattern):
                try:
                    archive_file.unlink()
                    logger.info(f"Archive-Datei gelöscht: {archive_file}")
                    self.cleanup_report['files_deleted'].append({
                        'file': str(archive_file),
                        'type': 'archive_file'
                    })
                except Exception as e:
                    logger.error(f"Fehler beim Löschen {archive_file}: {e}")
                    self.cleanup_report['errors'].append(f"Delete error {archive_file}: {e}")

    def move_legacy_collections(self):
        """Verschiebe Legacy Module Collections ins Archiv"""
        logger.info("=== LEGACY COLLECTIONS BEREINIGUNG ===")
        
        for legacy_item in self.legacy_collections:
            source_path = self.project_root / legacy_item
            if source_path.exists():
                dest_path = self.archive_dir / "legacy_collections" / source_path.name
                
                try:
                    if source_path.is_dir():
                        shutil.copytree(str(source_path), str(dest_path))
                        shutil.rmtree(str(source_path))
                    else:
                        shutil.move(str(source_path), str(dest_path))
                        
                    logger.info(f"Legacy Collection verschoben: {source_path} -> {dest_path}")
                    self.cleanup_report['files_moved'].append({
                        'source': str(source_path),
                        'destination': str(dest_path), 
                        'type': 'legacy_collection'
                    })
                    
                except Exception as e:
                    logger.error(f"Fehler beim Verschieben Legacy Collection {source_path}: {e}")
                    self.cleanup_report['errors'].append(f"Legacy move error {source_path}: {e}")

    def remove_backup_files(self):
        """Entferne alle .backup und temporäre Dateien"""
        logger.info("=== BACKUP-DATEIEN BEREINIGUNG ===")
        
        backup_patterns = [
            "**/*.backup*",
            "**/temp_*.py",
            "**/__pycache__/**",
            "services/**/venv/**"
        ]
        
        for pattern in backup_patterns:
            for backup_file in self.project_root.glob(pattern):
                if backup_file.is_file():
                    try:
                        backup_file.unlink()
                        logger.info(f"Backup-Datei gelöscht: {backup_file}")
                        self.cleanup_report['files_deleted'].append({
                            'file': str(backup_file),
                            'type': 'backup_file'
                        })
                    except Exception as e:
                        logger.error(f"Fehler beim Löschen {backup_file}: {e}")
                        self.cleanup_report['errors'].append(f"Backup delete error {backup_file}: {e}")

    def generate_cleanup_report(self):
        """Generiere detaillierte Bereinigung-Report"""
        report_file = self.project_root / f"CRITICAL_CLEANUP_EXECUTION_REPORT_v1_0_0_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.cleanup_report, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Cleanup-Report erstellt: {report_file}")
            
            # Summary ausgeben
            logger.info("\n=== CLEANUP SUMMARY ===")
            logger.info(f"Dateien verschoben: {len(self.cleanup_report['files_moved'])}")
            logger.info(f"Dateien gelöscht: {len(self.cleanup_report['files_deleted'])}")
            logger.info(f"Services konsolidiert: {len(self.cleanup_report['services_consolidated'])}")
            logger.info(f"Fehler: {len(self.cleanup_report['errors'])}")
            
            # Service-spezifische Summary
            for service_info in self.cleanup_report['services_consolidated']:
                logger.info(f"  - {service_info['service']}: {service_info['duplicates_moved']} Duplikate bereinigt")
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Reports: {e}")

    def run_critical_cleanup(self):
        """Führe komplette kritische Bereinigung durch"""
        logger.info("=== KRITISCHE CODE-BEREINIGUNG GESTARTET ===")
        logger.info(f"Projekt-Root: {self.project_root}")
        logger.info(f"Archive-Verzeichnis: {self.archive_dir}")
        
        try:
            # 1. Archive-Struktur erstellen
            self.create_archive_structure()
            
            # 2. Service-Duplikate verschieben
            self.move_service_duplicates()
            
            # 3. Archive-Dateien löschen  
            self.remove_archive_files()
            
            # 4. Legacy Collections verschieben
            self.move_legacy_collections()
            
            # 5. Backup-Dateien bereinigen
            self.remove_backup_files()
            
            # 6. Report generieren
            self.generate_cleanup_report()
            
            logger.info("=== KRITISCHE CODE-BEREINIGUNG ABGESCHLOSSEN ===")
            
        except Exception as e:
            logger.error(f"Kritischer Fehler in Cleanup: {e}")
            self.cleanup_report['errors'].append(f"Critical cleanup error: {e}")


def main():
    """Main Cleanup Execution"""
    cleaner = CriticalCodeCleaner()
    cleaner.run_critical_cleanup()


if __name__ == "__main__":
    main()