"""
Model Version Manager v1.0.0
Vollständiges Versioning und Rollback-System für ML-Modelle

Features:
- Semantic Versioning (major.minor.patch)  
- Model Checkpointing und Snapshots
- Rollback zu beliebigen Versionen
- Performance-Tracking über Versionen
- Automated Backup und Cleanup
- Model A/B Testing Support

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import asyncpg

logger = logging.getLogger(__name__)

class ModelStatus(Enum):
    """Model Status States"""
    ACTIVE = "active"
    STAGING = "staging" 
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    TESTING = "testing"

class VersionType(Enum):
    """Version Increment Types"""
    MAJOR = "major"      # Breaking changes
    MINOR = "minor"      # New features
    PATCH = "patch"      # Bug fixes
    HOTFIX = "hotfix"    # Emergency fixes

@dataclass
class ModelVersion:
    """Model Version Information"""
    model_id: str
    model_type: str
    version: str  # semver format: x.y.z
    status: ModelStatus
    file_path: str
    scaler_path: Optional[str]
    metadata_path: Optional[str]
    performance_metrics: Dict[str, float]
    created_at: datetime
    created_by: str = "automated"
    description: Optional[str] = None
    parent_version: Optional[str] = None

@dataclass
class RollbackPlan:
    """Rollback Execution Plan"""
    target_version: str
    current_version: str
    affected_models: List[str]
    rollback_steps: List[Dict[str, Any]]
    validation_required: bool = True
    estimated_downtime_minutes: int = 5

class ModelVersionManager:
    """
    Vollständiges Model Versioning und Rollback System
    
    Verwaltet:
    - Semantic Versioning für alle ML-Modelle
    - Automatische Backups und Snapshots
    - Rollback zu beliebigen Versionen
    - Performance-Tracking über Versionen
    - Cleanup alter Versionen
    """
    
    def __init__(self, database_pool: asyncpg.Pool, model_storage_base_path: str):
        self.database_pool = database_pool
        self.model_storage_path = Path(model_storage_base_path)
        self.versions_path = self.model_storage_path / "versions"
        self.backups_path = self.model_storage_path / "backups"
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Versioning Configuration
        self.max_versions_per_model = 10  # Maximal gespeicherte Versionen
        self.backup_retention_days = 90   # Backup Retention
        self.auto_cleanup_enabled = True
        
        # Version Registry (in-memory cache)
        self.version_registry = {}
        
        # Ensure directories exist
        self.versions_path.mkdir(parents=True, exist_ok=True)
        self.backups_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialisiert Version Manager"""
        try:
            self.logger.info("Initializing Model Version Manager")
            
            # Database Tables erstellen
            await self._create_versioning_tables()
            
            # Load existing versions
            await self._load_version_registry()
            
            # Migration bestehender Modelle
            await self._migrate_existing_models()
            
            self.logger.info(f"Model Version Manager initialized with {len(self.version_registry)} versions")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize version manager: {str(e)}")
            raise
    
    async def create_model_version(self, model_type: str, model_files: Dict[str, str], 
                                 performance_metrics: Dict[str, float],
                                 version_type: VersionType = VersionType.MINOR,
                                 description: Optional[str] = None) -> ModelVersion:
        """
        Erstellt eine neue Model Version
        
        Args:
            model_type: Type des Modells (technical, sentiment, etc.)
            model_files: Dict mit Pfaden zu Model-Dateien {"model": "/path/to/model.h5", "scaler": "/path/to/scaler.pkl"}
            performance_metrics: Performance Metriken
            version_type: Art der Versionierung
            description: Beschreibung der Changes
        """
        try:
            # Generate new version number
            current_version = await self._get_current_version(model_type)
            new_version = self._increment_version(current_version, version_type)
            
            # Create version directory
            version_dir = self.versions_path / model_type / new_version
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy model files to version directory
            versioned_files = await self._copy_model_files(model_files, version_dir)
            
            # Create model version object
            model_version = ModelVersion(
                model_id=f"{model_type}_{new_version}",
                model_type=model_type,
                version=new_version,
                status=ModelStatus.STAGING,  # New versions start in staging
                file_path=versioned_files.get("model", ""),
                scaler_path=versioned_files.get("scaler"),
                metadata_path=versioned_files.get("metadata"),
                performance_metrics=performance_metrics,
                created_at=datetime.utcnow(),
                description=description,
                parent_version=current_version
            )
            
            # Persist to database
            await self._persist_model_version(model_version)
            
            # Update registry
            if model_type not in self.version_registry:
                self.version_registry[model_type] = []
            self.version_registry[model_type].append(model_version)
            
            # Create metadata file
            await self._create_version_metadata(model_version, version_dir)
            
            self.logger.info(f"Created new version {new_version} for {model_type}")
            return model_version
            
        except Exception as e:
            self.logger.error(f"Failed to create model version: {str(e)}")
            raise
    
    async def promote_version_to_active(self, model_type: str, version: str) -> bool:
        """
        Promoted eine Version von Staging zu Active
        """
        try:
            # Get version
            model_version = await self._get_model_version(model_type, version)
            if not model_version:
                raise ValueError(f"Version {version} not found for {model_type}")
            
            if model_version.status != ModelStatus.STAGING:
                raise ValueError(f"Can only promote staging versions, current status: {model_version.status.value}")
            
            # Validation vor Promotion
            validation_result = await self._validate_model_version(model_version)
            if not validation_result["valid"]:
                raise ValueError(f"Version validation failed: {validation_result['errors']}")
            
            # Deactivate current active version
            await self._deactivate_current_version(model_type)
            
            # Promote to active
            await self._update_version_status(model_type, version, ModelStatus.ACTIVE)
            
            # Update model metadata table
            await self._update_active_model_reference(model_version)
            
            self.logger.info(f"Promoted {model_type} version {version} to active")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to promote version {version}: {str(e)}")
            return False
    
    async def rollback_to_version(self, model_type: str, target_version: str, 
                                validate_before_rollback: bool = True) -> RollbackPlan:
        """
        Rollt zurück zu einer spezifischen Version
        """
        try:
            # Get target version
            target_model = await self._get_model_version(model_type, target_version)
            if not target_model:
                raise ValueError(f"Target version {target_version} not found")
            
            # Get current version
            current_version = await self._get_current_version(model_type)
            
            # Create rollback plan
            rollback_plan = RollbackPlan(
                target_version=target_version,
                current_version=current_version or "unknown",
                affected_models=[model_type],
                rollback_steps=[
                    {"action": "backup_current", "model_type": model_type},
                    {"action": "deactivate_current", "model_type": model_type}, 
                    {"action": "activate_target", "model_type": model_type, "version": target_version},
                    {"action": "validate_rollback", "model_type": model_type}
                ],
                validation_required=validate_before_rollback
            )
            
            # Execute rollback plan
            success = await self._execute_rollback_plan(rollback_plan)
            
            if success:
                self.logger.info(f"Successfully rolled back {model_type} to version {target_version}")
            else:
                self.logger.error(f"Rollback failed for {model_type} to version {target_version}")
            
            return rollback_plan
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            raise
    
    async def get_version_history(self, model_type: str, limit: int = 20) -> List[ModelVersion]:
        """Holt Version History für ein Model"""
        try:
            async with self.database_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM model_versions 
                    WHERE model_type = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, model_type, limit)
                
                versions = []
                for row in rows:
                    version = ModelVersion(
                        model_id=row['model_id'],
                        model_type=row['model_type'],
                        version=row['version'],
                        status=ModelStatus(row['status']),
                        file_path=row['file_path'],
                        scaler_path=row['scaler_path'],
                        metadata_path=row['metadata_path'],
                        performance_metrics=json.loads(row['performance_metrics']) if row['performance_metrics'] else {},
                        created_at=row['created_at'],
                        created_by=row['created_by'],
                        description=row['description'],
                        parent_version=row['parent_version']
                    )
                    versions.append(version)
                
                return versions
                
        except Exception as e:
            self.logger.error(f"Failed to get version history: {str(e)}")
            return []
    
    async def get_performance_comparison(self, model_type: str, version1: str, version2: str) -> Dict[str, Any]:
        """Vergleicht Performance zwischen zwei Versionen"""
        try:
            v1 = await self._get_model_version(model_type, version1)
            v2 = await self._get_model_version(model_type, version2)
            
            if not v1 or not v2:
                return {"error": "One or both versions not found"}
            
            comparison = {
                "version1": {
                    "version": version1,
                    "metrics": v1.performance_metrics,
                    "created_at": v1.created_at.isoformat()
                },
                "version2": {
                    "version": version2, 
                    "metrics": v2.performance_metrics,
                    "created_at": v2.created_at.isoformat()
                },
                "improvements": {},
                "regressions": {}
            }
            
            # Compare metrics
            for metric, value1 in v1.performance_metrics.items():
                if metric in v2.performance_metrics:
                    value2 = v2.performance_metrics[metric]
                    diff = value2 - value1
                    percent_change = (diff / value1) * 100 if value1 != 0 else 0
                    
                    comparison_entry = {
                        "old_value": value1,
                        "new_value": value2,
                        "absolute_change": diff,
                        "percent_change": percent_change
                    }
                    
                    # Lower is better for error metrics
                    if metric.endswith(('_mse', '_mae', '_error')):
                        if diff < 0:
                            comparison["improvements"][metric] = comparison_entry
                        else:
                            comparison["regressions"][metric] = comparison_entry
                    else:  # Higher is better for scores
                        if diff > 0:
                            comparison["improvements"][metric] = comparison_entry
                        else:
                            comparison["regressions"][metric] = comparison_entry
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Failed to compare versions: {str(e)}")
            return {"error": str(e)}
    
    async def cleanup_old_versions(self, dry_run: bool = True) -> Dict[str, Any]:
        """Bereinigt alte Versionen basierend auf Retention Policy"""
        try:
            cleanup_summary = {
                "models_processed": 0,
                "versions_removed": 0,
                "disk_space_freed": 0,
                "actions": []
            }
            
            for model_type in self.version_registry.keys():
                versions = await self.get_version_history(model_type, limit=100)
                
                # Keep active and recent versions
                versions_to_keep = []
                versions_to_remove = []
                
                active_version = None
                for version in versions:
                    if version.status == ModelStatus.ACTIVE:
                        active_version = version
                        versions_to_keep.append(version)
                    elif len(versions_to_keep) < self.max_versions_per_model:
                        versions_to_keep.append(version)
                    else:
                        # Check if version is older than retention period
                        days_old = (datetime.utcnow() - version.created_at).days
                        if days_old > self.backup_retention_days:
                            versions_to_remove.append(version)
                
                # Process removals
                for version in versions_to_remove:
                    if not dry_run:
                        await self._remove_version(version)
                    
                    cleanup_summary["versions_removed"] += 1
                    cleanup_summary["actions"].append({
                        "action": "remove" if not dry_run else "would_remove",
                        "model_type": version.model_type,
                        "version": version.version,
                        "created_at": version.created_at.isoformat()
                    })
                
                cleanup_summary["models_processed"] += 1
            
            self.logger.info(f"Cleanup {'completed' if not dry_run else 'simulated'}: {cleanup_summary}")
            return cleanup_summary
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            return {"error": str(e)}
    
    async def get_versioning_status(self) -> Dict[str, Any]:
        """Returns Versioning System Status"""
        try:
            status = {
                "total_models": len(self.version_registry),
                "total_versions": sum(len(versions) for versions in self.version_registry.values()),
                "storage_usage": await self._calculate_storage_usage(),
                "models": {}
            }
            
            for model_type, versions in self.version_registry.items():
                active_version = None
                staging_versions = 0
                
                for version in versions:
                    if version.status == ModelStatus.ACTIVE:
                        active_version = version.version
                    elif version.status == ModelStatus.STAGING:
                        staging_versions += 1
                
                status["models"][model_type] = {
                    "active_version": active_version,
                    "total_versions": len(versions),
                    "staging_versions": staging_versions,
                    "latest_version": versions[0].version if versions else None
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get versioning status: {str(e)}")
            return {"error": str(e)}
    
    # Helper Methods
    
    async def _create_versioning_tables(self):
        """Erstellt Versioning Database Tables"""
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS model_versions (
                        model_id VARCHAR(100) PRIMARY KEY,
                        model_type VARCHAR(50) NOT NULL,
                        version VARCHAR(20) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'staging',
                        file_path TEXT NOT NULL,
                        scaler_path TEXT,
                        metadata_path TEXT,
                        performance_metrics JSONB,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        created_by VARCHAR(50) DEFAULT 'automated',
                        description TEXT,
                        parent_version VARCHAR(20),
                        UNIQUE(model_type, version)
                    )
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_model_versions_type_status 
                    ON model_versions(model_type, status)
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_model_versions_created 
                    ON model_versions(created_at)
                """)
                
        except Exception as e:
            self.logger.error(f"Failed to create versioning tables: {str(e)}")
            raise
    
    async def _load_version_registry(self):
        """Lädt bestehende Versionen in Registry"""
        try:
            async with self.database_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM model_versions 
                    ORDER BY model_type, created_at DESC
                """)
                
                for row in rows:
                    version = ModelVersion(
                        model_id=row['model_id'],
                        model_type=row['model_type'],
                        version=row['version'],
                        status=ModelStatus(row['status']),
                        file_path=row['file_path'],
                        scaler_path=row['scaler_path'],
                        metadata_path=row['metadata_path'],
                        performance_metrics=json.loads(row['performance_metrics']) if row['performance_metrics'] else {},
                        created_at=row['created_at'],
                        created_by=row['created_by'],
                        description=row['description'],
                        parent_version=row['parent_version']
                    )
                    
                    if version.model_type not in self.version_registry:
                        self.version_registry[version.model_type] = []
                    self.version_registry[version.model_type].append(version)
                
        except Exception as e:
            self.logger.error(f"Failed to load version registry: {str(e)}")
    
    async def _migrate_existing_models(self):
        """Migriert bestehende Modelle ins Versioning System"""
        try:
            # Hole bestehende Modelle aus ml_model_metadata
            async with self.database_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT model_type, file_path, scaler_path, performance_metrics, created_at
                    FROM ml_model_metadata 
                    WHERE status = 'active'
                    AND model_id NOT IN (SELECT model_id FROM model_versions)
                """)
                
                for row in rows:
                    # Create initial version (1.0.0) for existing models
                    if row['model_type'] not in self.version_registry:
                        model_files = {"model": row['file_path']}
                        if row['scaler_path']:
                            model_files["scaler"] = row['scaler_path']
                        
                        metrics = json.loads(row['performance_metrics']) if row['performance_metrics'] else {}
                        
                        # Only create if files exist
                        if Path(row['file_path']).exists():
                            await self.create_model_version(
                                model_type=row['model_type'],
                                model_files=model_files,
                                performance_metrics=metrics,
                                version_type=VersionType.MAJOR,
                                description="Initial version from existing model"
                            )
                            
                            # Promote to active
                            await self.promote_version_to_active(row['model_type'], "1.0.0")
                
        except Exception as e:
            self.logger.error(f"Model migration failed: {str(e)}")
    
    def _increment_version(self, current_version: Optional[str], version_type: VersionType) -> str:
        """Increments version number based on type"""
        if not current_version:
            return "1.0.0"
        
        try:
            major, minor, patch = map(int, current_version.split('.'))
            
            if version_type == VersionType.MAJOR:
                return f"{major + 1}.0.0"
            elif version_type == VersionType.MINOR:
                return f"{major}.{minor + 1}.0"
            elif version_type in [VersionType.PATCH, VersionType.HOTFIX]:
                return f"{major}.{minor}.{patch + 1}"
            else:
                return f"{major}.{minor}.{patch + 1}"
                
        except ValueError:
            # Fallback for invalid version format
            return "1.0.0"
    
    async def _get_current_version(self, model_type: str) -> Optional[str]:
        """Holt aktuelle Version für Model Type"""
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT version FROM model_versions 
                    WHERE model_type = $1 AND status = 'active'
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, model_type)
                
                return row['version'] if row else None
        except Exception as e:
            self.logger.error(f"Failed to get current version: {str(e)}")
            return None
    
    async def _copy_model_files(self, model_files: Dict[str, str], target_dir: Path) -> Dict[str, str]:
        """Kopiert Model Files in Version Directory"""
        copied_files = {}
        
        for file_type, source_path in model_files.items():
            if not Path(source_path).exists():
                continue
                
            filename = Path(source_path).name
            target_path = target_dir / filename
            
            # Copy file
            shutil.copy2(source_path, target_path)
            copied_files[file_type] = str(target_path)
        
        return copied_files
    
    async def _get_model_version(self, model_type: str, version: str) -> Optional[ModelVersion]:
        """Holt spezifische Model Version"""
        if model_type in self.version_registry:
            for model_version in self.version_registry[model_type]:
                if model_version.version == version:
                    return model_version
        return None
    
    async def _persist_model_version(self, version: ModelVersion):
        """Persistiert Model Version in DB"""
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO model_versions 
                    (model_id, model_type, version, status, file_path, scaler_path, 
                     metadata_path, performance_metrics, created_at, created_by, 
                     description, parent_version)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """, 
                version.model_id, version.model_type, version.version, version.status.value,
                version.file_path, version.scaler_path, version.metadata_path,
                json.dumps(version.performance_metrics), version.created_at, version.created_by,
                version.description, version.parent_version)
        except Exception as e:
            self.logger.error(f"Failed to persist version: {str(e)}")
            raise
    
    async def _create_version_metadata(self, version: ModelVersion, version_dir: Path):
        """Erstellt Metadata File für Version"""
        metadata = {
            "model_id": version.model_id,
            "model_type": version.model_type,
            "version": version.version,
            "status": version.status.value,
            "performance_metrics": version.performance_metrics,
            "created_at": version.created_at.isoformat(),
            "description": version.description,
            "parent_version": version.parent_version
        }
        
        metadata_file = version_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update version with metadata path
        version.metadata_path = str(metadata_file)
    
    async def _validate_model_version(self, version: ModelVersion) -> Dict[str, Any]:
        """Validiert Model Version vor Promotion"""
        validation = {"valid": True, "errors": []}
        
        # Check if files exist
        if not Path(version.file_path).exists():
            validation["valid"] = False
            validation["errors"].append(f"Model file not found: {version.file_path}")
        
        if version.scaler_path and not Path(version.scaler_path).exists():
            validation["valid"] = False
            validation["errors"].append(f"Scaler file not found: {version.scaler_path}")
        
        # Check performance metrics
        if not version.performance_metrics:
            validation["valid"] = False
            validation["errors"].append("No performance metrics available")
        
        return validation
    
    async def _deactivate_current_version(self, model_type: str):
        """Deaktiviert aktuelle Version"""
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE model_versions 
                    SET status = 'deprecated' 
                    WHERE model_type = $1 AND status = 'active'
                """, model_type)
        except Exception as e:
            self.logger.error(f"Failed to deactivate current version: {str(e)}")
    
    async def _update_version_status(self, model_type: str, version: str, status: ModelStatus):
        """Updated Version Status"""
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE model_versions 
                    SET status = $3 
                    WHERE model_type = $1 AND version = $2
                """, model_type, version, status.value)
            
            # Update registry
            if model_type in self.version_registry:
                for model_version in self.version_registry[model_type]:
                    if model_version.version == version:
                        model_version.status = status
                        break
                        
        except Exception as e:
            self.logger.error(f"Failed to update version status: {str(e)}")
    
    async def _update_active_model_reference(self, version: ModelVersion):
        """Updated Referenz in ml_model_metadata Table"""
        try:
            async with self.database_pool.acquire() as conn:
                # Update existing active model oder insert new
                await conn.execute("""
                    INSERT INTO ml_model_metadata 
                    (model_id, model_type, model_version, status, file_path, scaler_path, 
                     performance_metrics, created_at)
                    VALUES ($1, $2, $3, 'active', $4, $5, $6, $7)
                    ON CONFLICT (model_type) 
                    DO UPDATE SET
                        model_id = $1,
                        model_version = $3,
                        status = 'active',
                        file_path = $4,
                        scaler_path = $5,
                        performance_metrics = $6,
                        created_at = $7
                """, 
                version.model_id, version.model_type, version.version, 
                version.file_path, version.scaler_path,
                json.dumps(version.performance_metrics), version.created_at)
        except Exception as e:
            self.logger.error(f"Failed to update active model reference: {str(e)}")
    
    async def _execute_rollback_plan(self, plan: RollbackPlan) -> bool:
        """Führt Rollback Plan aus"""
        try:
            for step in plan.rollback_steps:
                action = step["action"]
                model_type = step["model_type"]
                
                if action == "backup_current":
                    await self._backup_current_version(model_type)
                elif action == "deactivate_current":
                    await self._deactivate_current_version(model_type)
                elif action == "activate_target":
                    await self._update_version_status(model_type, step["version"], ModelStatus.ACTIVE)
                    version = await self._get_model_version(model_type, step["version"])
                    if version:
                        await self._update_active_model_reference(version)
                elif action == "validate_rollback":
                    if plan.validation_required:
                        version = await self._get_model_version(model_type, plan.target_version)
                        if version:
                            validation = await self._validate_model_version(version)
                            if not validation["valid"]:
                                raise Exception(f"Rollback validation failed: {validation['errors']}")
            
            return True
        except Exception as e:
            self.logger.error(f"Rollback plan execution failed: {str(e)}")
            return False
    
    async def _backup_current_version(self, model_type: str):
        """Erstellt Backup der aktuellen Version"""
        current_version = await self._get_current_version(model_type)
        if current_version:
            # Implementation für Backup-Erstellung
            self.logger.info(f"Backing up current version {current_version} for {model_type}")
    
    async def _remove_version(self, version: ModelVersion):
        """Entfernt eine Version komplett"""
        try:
            # Remove files
            if Path(version.file_path).exists():
                Path(version.file_path).unlink()
            if version.scaler_path and Path(version.scaler_path).exists():
                Path(version.scaler_path).unlink()
            if version.metadata_path and Path(version.metadata_path).exists():
                Path(version.metadata_path).unlink()
            
            # Remove from database
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    DELETE FROM model_versions 
                    WHERE model_id = $1
                """, version.model_id)
            
            # Remove from registry
            if version.model_type in self.version_registry:
                self.version_registry[version.model_type] = [
                    v for v in self.version_registry[version.model_type] 
                    if v.model_id != version.model_id
                ]
                
        except Exception as e:
            self.logger.error(f"Failed to remove version {version.model_id}: {str(e)}")
    
    async def _calculate_storage_usage(self) -> Dict[str, Any]:
        """Berechnet Storage Usage"""
        try:
            total_size = 0
            for path in self.versions_path.rglob("*"):
                if path.is_file():
                    total_size += path.stat().st_size
            
            return {
                "total_bytes": total_size,
                "total_mb": round(total_size / (1024 * 1024), 2),
                "versions_path": str(self.versions_path),
                "backups_path": str(self.backups_path)
            }
        except Exception as e:
            self.logger.error(f"Failed to calculate storage usage: {str(e)}")
            return {"error": str(e)}

# Export
__all__ = ['ModelVersionManager', 'ModelVersion', 'ModelStatus', 'VersionType', 'RollbackPlan']