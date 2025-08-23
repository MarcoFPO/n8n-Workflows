#!/usr/bin/env python3
"""
Database Migration for Multi-Source Support
Erweitert die KI-Recommendations Datenbank für die neue modulare Multi-Source-Architektur
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
import structlog

# Add paths for imports

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_v1_0_0_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared') -> Import Manager
from logging_config import setup_logging

logger = setup_logging("database-migration-multi-source")


class DatabaseMigrationMultiSource:
    """Database Migration für Multi-Source Support"""
    
    def __init__(self, db_path: str = "/home/mdoehler/aktienanalyse-ökosystem/data/ki_recommendations.db"):
        self.db_path = db_path
        self.backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Migration Versionierung
        self.migration_version = "1.0.0"
        self.migration_date = datetime.now().isoformat()
        
    def run_migration(self) -> bool:
        """Führe die komplette Migration durch"""
        try:
            logger.info("Starting database migration for multi-source support")
            
            # 1. Backup erstellen
            self._create_backup()
            
            # 2. Datenbankschema prüfen
            current_schema = self._analyze_current_schema()
            logger.info("Current database schema analyzed", tables=list(current_schema.keys()))
            
            # 3. Migration durchführen
            if self._needs_migration(current_schema):
                logger.info("Migration required - proceeding with schema updates")
                self._perform_migration()
            else:
                logger.info("Database already up to date - no migration needed")
                return True
            
            # 4. Validierung
            if self._validate_migration():
                logger.info("Database migration completed successfully")
                return True
            else:
                logger.error("Migration validation failed - restoring backup")
                self._restore_backup()
                return False
                
        except Exception as e:
            logger.error("Database migration failed", error=str(e))
            try:
                self._restore_backup()
            except Exception as restore_error:
                logger.error("Failed to restore backup", error=str(restore_error))
            return False
    
    def _create_backup(self):
        """Erstelle Backup der aktuellen Datenbank"""
        try:
            if os.path.exists(self.db_path):
                import shutil
                shutil.copy2(self.db_path, self.backup_path)
                logger.info("Database backup created", backup_path=self.backup_path)
            else:
                logger.info("No existing database found - creating new one")
                
        except Exception as e:
            logger.error("Failed to create backup", error=str(e))
            raise
    
    def _analyze_current_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Analysiere das aktuelle Datenbankschema"""
        schema = {}
        
        try:
            # Erstelle Datenbank falls sie nicht existiert
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                schema[table_name] = []
                for col_info in columns:
                    schema[table_name].append({
                        'name': col_info[1],
                        'type': col_info[2],
                        'not_null': col_info[3],
                        'default': col_info[4],
                        'primary_key': col_info[5]
                    })
            
            conn.close()
            return schema
            
        except Exception as e:
            logger.error("Failed to analyze current schema", error=str(e))
            return {}
    
    def _needs_migration(self, current_schema: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Prüfe ob Migration erforderlich ist"""
        try:
            # Prüfe ob predictions Tabelle existiert
            if 'predictions' not in current_schema:
                return True
            
            # Prüfe ob Multi-Source Felder vorhanden sind
            predictions_columns = [col['name'] for col in current_schema['predictions']]
            
            required_multi_source_fields = [
                'source_count',
                'source_reliability', 
                'calculation_method',
                'risk_assessment',
                'base_metrics',
                'source_contributions'
            ]
            
            for field in required_multi_source_fields:
                if field not in predictions_columns:
                    logger.info(f"Missing multi-source field: {field}")
                    return True
            
            # Prüfe ob Migration-Metadata Tabelle existiert
            if 'migration_history' not in current_schema:
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error checking migration necessity", error=str(e))
            return True
    
    def _perform_migration(self):
        """Führe die Migration durch"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. Erstelle neue Predictions Tabelle mit Multi-Source Support
            logger.info("Creating new predictions table with multi-source support")
            self._create_new_predictions_table(cursor)
            
            # 2. Migriere existierende Daten
            logger.info("Migrating existing prediction data")
            self._migrate_existing_predictions(cursor)
            
            # 3. Erstelle Data Sources Tabelle
            logger.info("Creating data sources tracking table")
            self._create_data_sources_table(cursor)
            
            # 4. Erstelle Calculation History Tabelle
            logger.info("Creating calculation history table")
            self._create_calculation_history_table(cursor)
            
            # 5. Erstelle Migration History Tabelle
            logger.info("Creating migration history table")
            self._create_migration_history_table(cursor)
            
            # 6. Erstelle Indizes für bessere Performance
            logger.info("Creating performance indexes")
            self._create_performance_indexes(cursor)
            
            # 7. Log Migration
            self._log_migration(cursor)
            
            conn.commit()
            conn.close()
            
            logger.info("Database migration completed successfully")
            
        except Exception as e:
            logger.error("Error performing migration", error=str(e))
            raise
    
    def _create_new_predictions_table(self, cursor):
        """Erstelle neue Predictions Tabelle mit Multi-Source Support"""
        
        # Prüfe ob alte Tabelle existiert
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'")
        old_table_exists = cursor.fetchone() is not None
        
        if old_table_exists:
            # Rename old table
            cursor.execute("ALTER TABLE predictions RENAME TO predictions_old")
        
        # Erstelle neue Tabelle
        cursor.execute('''
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                company_name TEXT NOT NULL,
                score REAL NOT NULL,
                profit_forecast REAL NOT NULL,
                forecast_period_days INTEGER NOT NULL,
                recommendation TEXT NOT NULL,
                confidence_level REAL NOT NULL,
                trend TEXT NOT NULL,
                target_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                
                -- Multi-Source Support Fields
                source_count INTEGER DEFAULT 1,
                source_reliability REAL DEFAULT 0.5,
                calculation_method TEXT DEFAULT 'single_source',
                risk_assessment TEXT DEFAULT 'medium',
                
                -- JSON Fields für detaillierte Daten
                base_metrics TEXT,  -- JSON mit base_score, multipliers, etc.
                source_contributions TEXT,  -- JSON mit source-spezifischen Beiträgen
                
                -- Enhanced Metadata
                calculation_engine_version TEXT DEFAULT '1.0.0',
                data_freshness_minutes INTEGER DEFAULT 0,
                market_conditions TEXT DEFAULT 'normal',
                
                -- Performance Tracking
                calculation_time_ms REAL DEFAULT 0.0,
                data_source_response_times TEXT,  -- JSON
                
                -- Version Control
                prediction_version INTEGER DEFAULT 1,
                updated_at TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
    
    def _migrate_existing_predictions(self, cursor):
        """Migriere existierende Prediction-Daten"""
        try:
            # Prüfe ob alte Tabelle existiert
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictions_old'")
            old_table_exists = cursor.fetchone() is not None
            
            if not old_table_exists:
                logger.info("No existing predictions to migrate")
                return
            
            # Hole alle Daten aus der alten Tabelle
            cursor.execute("SELECT * FROM predictions_old")
            old_predictions = cursor.fetchall()
            
            # Hole Column-Namen der alten Tabelle
            cursor.execute("PRAGMA table_info(predictions_old)")
            old_columns = [row[1] for row in cursor.fetchall()]
            
            logger.info(f"Migrating {len(old_predictions)} existing predictions")
            
            for prediction in old_predictions:
                # Erstelle Dictionary aus alten Daten
                old_data = dict(zip(old_columns, prediction))
                
                # Erstelle Default-Werte für neue Felder
                base_metrics = {
                    'base_score': old_data.get('score', 0),
                    'legacy_migration': True,
                    'migrated_at': datetime.now().isoformat()
                }
                
                source_contributions = {
                    'legacy_source': {
                        'weight': 1.0,
                        'reliability': 0.5,
                        'priority': 1,
                        'migration_note': 'Migrated from legacy single-source system'
                    }
                }
                
                # Insert in neue Tabelle
                cursor.execute('''
                    INSERT INTO predictions (
                        symbol, company_name, score, profit_forecast, forecast_period_days,
                        recommendation, confidence_level, trend, target_date, created_at,
                        source_count, source_reliability, calculation_method, risk_assessment,
                        base_metrics, source_contributions, calculation_engine_version,
                        prediction_version, updated_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    old_data.get('symbol', ''),
                    old_data.get('company_name', ''),
                    old_data.get('score', 0),
                    old_data.get('profit_forecast', 0),
                    old_data.get('forecast_period_days', 30),
                    old_data.get('recommendation', 'HOLD'),
                    old_data.get('confidence_level', 0.5),
                    old_data.get('trend', 'neutral'),
                    old_data.get('target_date', ''),
                    old_data.get('created_at', datetime.now().isoformat()),
                    1,  # source_count
                    0.5,  # source_reliability
                    'legacy_single_source',  # calculation_method
                    'medium',  # risk_assessment
                    json.dumps(base_metrics),
                    json.dumps(source_contributions),
                    'legacy_v1.0.0',  # calculation_engine_version
                    1,  # prediction_version
                    datetime.now().isoformat(),  # updated_at
                    1   # is_active
                ))
            
            logger.info(f"Successfully migrated {len(old_predictions)} predictions")
            
            # Lösche alte Tabelle
            cursor.execute("DROP TABLE predictions_old")
            
        except Exception as e:
            logger.error("Error migrating existing predictions", error=str(e))
            raise
    
    def _create_data_sources_table(self, cursor):
        """Erstelle Tabelle für Data Source Tracking"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL,
                version TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                reliability_score REAL DEFAULT 0.5,
                is_active BOOLEAN DEFAULT 1,
                last_successful_request TEXT,
                last_failed_request TEXT,
                total_requests INTEGER DEFAULT 0,
                successful_requests INTEGER DEFAULT 0,
                average_response_time_ms REAL DEFAULT 0.0,
                configuration TEXT,  -- JSON
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        
        # Default Data Sources einfügen
        default_sources = [
            {
                'source_name': 'marketcap_data_source',
                'source_type': 'market_data',
                'version': '1.0.0',
                'priority': 1,
                'reliability_score': 0.9,
                'configuration': json.dumps({
                    'update_interval': 3600,
                    'data_types': ['market_cap', 'stock_price', 'daily_change', 'company_info']
                })
            },
            {
                'source_name': 'legacy_companies_marketcap',
                'source_type': 'legacy_adapter',
                'version': '1.0.0',
                'priority': 2,
                'reliability_score': 0.7,
                'configuration': json.dumps({
                    'compatibility_mode': 'legacy',
                    'deprecation_notice': 'Will be phased out in favor of modular sources'
                })
            }
        ]
        
        for source in default_sources:
            cursor.execute('''
                INSERT OR IGNORE INTO data_sources (
                    source_name, source_type, version, priority, reliability_score,
                    configuration, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                source['source_name'],
                source['source_type'],
                source['version'],
                source['priority'],
                source['reliability_score'],
                source['configuration'],
                datetime.now().isoformat()
            ))
    
    def _create_calculation_history_table(self, cursor):
        """Erstelle Tabelle für Calculation History"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calculation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER,
                calculation_request_id TEXT,
                symbol TEXT NOT NULL,
                sources_requested TEXT,  -- JSON array
                sources_received TEXT,   -- JSON array
                calculation_time_ms REAL,
                calculation_method TEXT,
                success BOOLEAN,
                error_message TEXT,
                created_at TEXT NOT NULL,
                
                FOREIGN KEY (prediction_id) REFERENCES predictions (id)
            )
        ''')
    
    def _create_migration_history_table(self, cursor):
        """Erstelle Tabelle für Migration History"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_version TEXT NOT NULL,
                migration_name TEXT NOT NULL,
                migration_description TEXT,
                applied_at TEXT NOT NULL,
                applied_by TEXT DEFAULT 'system',
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                rollback_script TEXT
            )
        ''')
    
    def _create_performance_indexes(self, cursor):
        """Erstelle Performance-Indizes"""
        indexes = [
            # Predictions Indizes
            "CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_source_count ON predictions(source_count)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_active ON predictions(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_recommendation ON predictions(recommendation)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_symbol_active ON predictions(symbol, is_active)",
            
            # Data Sources Indizes
            "CREATE INDEX IF NOT EXISTS idx_data_sources_name ON data_sources(source_name)",
            "CREATE INDEX IF NOT EXISTS idx_data_sources_type ON data_sources(source_type)",
            "CREATE INDEX IF NOT EXISTS idx_data_sources_active ON data_sources(is_active)",
            
            # Calculation History Indizes
            "CREATE INDEX IF NOT EXISTS idx_calc_history_symbol ON calculation_history(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_calc_history_created_at ON calculation_history(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_calc_history_success ON calculation_history(success)",
            
            # Migration History Indizes
            "CREATE INDEX IF NOT EXISTS idx_migration_history_version ON migration_history(migration_version)",
            "CREATE INDEX IF NOT EXISTS idx_migration_history_applied_at ON migration_history(applied_at)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    def _log_migration(self, cursor):
        """Log die Migration in der History"""
        cursor.execute('''
            INSERT INTO migration_history (
                migration_version, migration_name, migration_description,
                applied_at, applied_by, success
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            self.migration_version,
            'Multi-Source Architecture Migration',
            'Added support for multiple data sources in profit prediction calculations',
            self.migration_date,
            'database_migration_multi_source_v1_0_0_20250817.py',
            1
        ))
    
    def _validate_migration(self) -> bool:
        """Validiere dass Migration erfolgreich war"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prüfe ob alle neuen Tabellen existieren
            required_tables = ['predictions', 'data_sources', 'calculation_history', 'migration_history']
            
            for table in required_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    logger.error(f"Migration validation failed: Table {table} not found")
                    return False
            
            # Prüfe ob neue Felder in predictions Tabelle existieren
            cursor.execute("PRAGMA table_info(predictions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_fields = [
                'source_count', 'source_reliability', 'calculation_method', 
                'risk_assessment', 'base_metrics', 'source_contributions'
            ]
            
            for field in required_fields:
                if field not in columns:
                    logger.error(f"Migration validation failed: Field {field} not found in predictions table")
                    return False
            
            # Prüfe ob Migration History Eintrag vorhanden
            cursor.execute("SELECT COUNT(*) FROM migration_history WHERE migration_version = ?", (self.migration_version,))
            if cursor.fetchone()[0] == 0:
                logger.error("Migration validation failed: No migration history entry found")
                return False
            
            conn.close()
            
            logger.info("Migration validation successful")
            return True
            
        except Exception as e:
            logger.error("Migration validation error", error=str(e))
            return False
    
    def _restore_backup(self):
        """Restore Backup bei fehlgeschlagener Migration"""
        try:
            if os.path.exists(self.backup_path):
                import shutil
                shutil.copy2(self.backup_path, self.db_path)
                logger.info("Database backup restored successfully")
            else:
                logger.error("No backup file found to restore")
                
        except Exception as e:
            logger.error("Failed to restore backup", error=str(e))
            raise
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get Migration Status"""
        try:
            if not os.path.exists(self.db_path):
                return {
                    'migration_needed': True,
                    'reason': 'Database does not exist',
                    'current_version': None
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if migration_history table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='migration_history'")
            if not cursor.fetchone():
                return {
                    'migration_needed': True,
                    'reason': 'No migration history found',
                    'current_version': 'legacy'
                }
            
            # Get latest migration
            cursor.execute('''
                SELECT migration_version, applied_at, success 
                FROM migration_history 
                ORDER BY applied_at DESC 
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                version, applied_at, success = result
                return {
                    'migration_needed': False,
                    'current_version': version,
                    'last_migration': applied_at,
                    'migration_successful': bool(success)
                }
            else:
                return {
                    'migration_needed': True,
                    'reason': 'No migrations found in history',
                    'current_version': 'unknown'
                }
                
        except Exception as e:
            logger.error("Error getting migration status", error=str(e))
            return {
                'migration_needed': True,
                'reason': f'Error checking status: {str(e)}',
                'current_version': 'error'
            }


def main():
    """Main function für Migration"""
    try:
        migration = DatabaseMigrationMultiSource()
        
        # Check current status
        status = migration.get_migration_status()
        logger.info("Migration status", status=status)
        
        if status['migration_needed']:
            logger.info("Starting database migration")
            success = migration.run_migration()
            
            if success:
                logger.info("Database migration completed successfully")
                return 0
            else:
                logger.error("Database migration failed")
                return 1
        else:
            logger.info("Database already migrated")
            return 0
            
    except Exception as e:
        logger.error("Migration script error", error=str(e))
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)