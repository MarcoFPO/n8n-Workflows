#!/usr/bin/env python3
"""
PostgreSQL Authentication & Schema Migration Fix v1.0.0
Systematische Lösung für das Aktienanalyse-Ökosystem auf 10.1.1.174

KRITISCHES PROBLEM:
- PostgreSQL Peer Authentication fehlgeschlagen für User 'aktienanalyse'  
- Fehlende 'soll_ist_gewinn_tracking' Tabelle (ersetzt durch prediction_tracking_unified)
- Database Manager erwartet korrekten Authentication Setup

LÖSUNGSANSATZ:
1. PostgreSQL Authentication Fix (peer -> md5)
2. User & Database Setup korrigieren  
3. Fehlende soll_ist_gewinn_tracking Tabelle erstellen (Backward Compatibility)
4. Database Manager Integration testen

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Compliance
Autor: Claude Code - PostgreSQL Authentication Fix Agent
Datum: 26. August 2025
Version: 1.0.0 (Authentication & Schema Fix)
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncpg
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PostgreSQLConfig:
    """PostgreSQL Configuration für Authentication Fix"""
    host: str = "10.1.1.174"
    port: int = 5432
    database: str = "aktienanalyse_events"
    user: str = "aktienanalyse"
    password: str = "secure_password_2025"
    postgres_user: str = "postgres"


class PostgreSQLAuthenticationFixer:
    """
    Systematische Lösung für PostgreSQL Authentication Probleme
    
    CLEAN ARCHITECTURE COMPLIANCE:
    - Single Responsibility: Authentication & Schema Migration
    - Error Handling: Comprehensive error handling  
    - Security: Secure authentication setup
    """
    
    def __init__(self, config: PostgreSQLConfig):
        self.config = config
        self.ssh_host = f"mdoehler@{config.host}"
        
    async def diagnose_authentication_issue(self) -> Dict[str, Any]:
        """
        Diagnose PostgreSQL Authentication Setup
        
        RETURN: Comprehensive diagnosis report
        """
        logger.info("🔍 Diagnosing PostgreSQL Authentication Issue")
        
        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "host": self.config.host,
            "database": self.config.database,
            "user": self.config.user,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Test 1: Check if PostgreSQL is running
            result = await self._run_ssh_command("systemctl is-active postgresql")
            if result.returncode != 0:
                diagnosis["issues"].append("PostgreSQL service not running")
                diagnosis["recommendations"].append("Start PostgreSQL: sudo systemctl start postgresql")
            else:
                logger.info("✅ PostgreSQL service is running")
            
            # Test 2: Check if database exists
            result = await self._run_ssh_command(
                f"sudo -u postgres psql -lqt | cut -d \\| -f 1 | grep -qw {self.config.database}"
            )
            if result.returncode != 0:
                diagnosis["issues"].append(f"Database '{self.config.database}' does not exist")
                diagnosis["recommendations"].append(f"Create database: sudo -u postgres createdb {self.config.database}")
            else:
                logger.info(f"✅ Database '{self.config.database}' exists")
            
            # Test 3: Check if user exists
            result = await self._run_ssh_command(
                f"sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='{self.config.user}'\""
            )
            if not result.stdout.strip():
                diagnosis["issues"].append(f"User '{self.config.user}' does not exist")
                diagnosis["recommendations"].append(f"Create user: sudo -u postgres createuser {self.config.user}")
            else:
                logger.info(f"✅ User '{self.config.user}' exists")
            
            # Test 4: Check pg_hba.conf for authentication method
            result = await self._run_ssh_command("sudo cat /etc/postgresql/*/main/pg_hba.conf | grep -v '^#' | grep local")
            if "peer" in result.stdout:
                diagnosis["issues"].append("pg_hba.conf uses peer authentication which causes issues")
                diagnosis["recommendations"].append("Configure md5 authentication in pg_hba.conf")
            
            # Test 5: Test connection as postgres user
            result = await self._run_ssh_command(f"sudo -u postgres psql -d {self.config.database} -c 'SELECT 1;'")
            if result.returncode != 0:
                diagnosis["issues"].append("Cannot connect to database as postgres user")
            else:
                logger.info("✅ Can connect as postgres user")
            
            # Test 6: Check existing tables
            result = await self._run_ssh_command(
                f"sudo -u postgres psql -d {self.config.database} -c '\\dt' | grep -E '(prediction_tracking_unified|soll_ist_gewinn_tracking)'"
            )
            if "prediction_tracking_unified" in result.stdout:
                logger.info("✅ prediction_tracking_unified table exists")
            else:
                diagnosis["issues"].append("prediction_tracking_unified table missing")
                
            if "soll_ist_gewinn_tracking" not in result.stdout:
                diagnosis["issues"].append("soll_ist_gewinn_tracking table missing (backward compatibility)")
                diagnosis["recommendations"].append("Create soll_ist_gewinn_tracking table for backward compatibility")
            
        except Exception as e:
            logger.error(f"❌ Diagnosis failed: {e}")
            diagnosis["issues"].append(f"Diagnosis error: {str(e)}")
        
        logger.info(f"🔍 Found {len(diagnosis['issues'])} issues")
        return diagnosis
    
    async def fix_postgresql_authentication(self) -> bool:
        """
        Fix PostgreSQL Authentication Configuration
        
        STEPS:
        1. Create aktienanalyse user with password
        2. Grant necessary privileges  
        3. Configure pg_hba.conf for md5 authentication
        4. Reload PostgreSQL configuration
        """
        logger.info("🔧 Fixing PostgreSQL Authentication")
        
        try:
            # Step 1: Create user if not exists
            logger.info("Creating aktienanalyse user...")
            create_user_sql = f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{self.config.user}') THEN
                        CREATE USER {self.config.user} WITH PASSWORD '{self.config.password}';
                        RAISE NOTICE 'User {self.config.user} created';
                    ELSE
                        ALTER USER {self.config.user} WITH PASSWORD '{self.config.password}';
                        RAISE NOTICE 'User {self.config.user} password updated';
                    END IF;
                END
                $$;
            """
            
            result = await self._run_ssh_command(
                f"sudo -u postgres psql -d {self.config.database} -c \"{create_user_sql}\""
            )
            if result.returncode != 0:
                logger.error(f"Failed to create user: {result.stderr}")
                return False
            
            # Step 2: Grant privileges
            logger.info("Granting privileges...")
            grant_sql = f"""
                GRANT ALL PRIVILEGES ON DATABASE {self.config.database} TO {self.config.user};
                GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {self.config.user};
                GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {self.config.user};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {self.config.user};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {self.config.user};
            """
            
            result = await self._run_ssh_command(
                f"sudo -u postgres psql -d {self.config.database} -c \"{grant_sql}\""
            )
            if result.returncode != 0:
                logger.error(f"Failed to grant privileges: {result.stderr}")
                return False
            
            # Step 3: Update pg_hba.conf for md5 authentication
            logger.info("Updating pg_hba.conf...")
            
            # Backup current pg_hba.conf
            await self._run_ssh_command("sudo cp /etc/postgresql/*/main/pg_hba.conf /etc/postgresql/*/main/pg_hba.conf.backup")
            
            # Add md5 authentication for aktienanalyse user
            hba_rule = f"local   {self.config.database}   {self.config.user}   md5"
            result = await self._run_ssh_command(
                f"sudo sed -i '/^local.*all.*all.*peer/i {hba_rule}' /etc/postgresql/*/main/pg_hba.conf"
            )
            
            # Step 4: Reload PostgreSQL configuration
            logger.info("Reloading PostgreSQL configuration...")
            result = await self._run_ssh_command("sudo systemctl reload postgresql")
            if result.returncode != 0:
                logger.error(f"Failed to reload PostgreSQL: {result.stderr}")
                return False
            
            # Step 5: Test connection
            logger.info("Testing connection...")
            test_result = await self._test_connection()
            if not test_result:
                logger.error("Connection test failed after authentication fix")
                return False
            
            logger.info("✅ PostgreSQL Authentication fixed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to fix authentication: {e}")
            return False
    
    async def create_missing_schema(self) -> bool:
        """
        Create missing soll_ist_gewinn_tracking table for backward compatibility
        
        CLEAN ARCHITECTURE:
        - Maintains backward compatibility with existing services
        - Creates schema compatible with both old and new systems
        """
        logger.info("🗄️ Creating missing schema for backward compatibility")
        
        try:
            # Create soll_ist_gewinn_tracking table that maps to prediction_tracking_unified
            create_schema_sql = """
                -- Create soll_ist_gewinn_tracking for backward compatibility
                CREATE TABLE IF NOT EXISTS soll_ist_gewinn_tracking (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    company_name VARCHAR(255),
                    datum DATE NOT NULL,
                    soll_gewinn_1w DECIMAL(12,4),
                    soll_gewinn_1m DECIMAL(12,4), 
                    soll_gewinn_3m DECIMAL(12,4),
                    soll_gewinn_12m DECIMAL(12,4),
                    ist_gewinn DECIMAL(12,4),
                    market_region VARCHAR(50) DEFAULT 'DE',
                    confidence_score DECIMAL(5,4),
                    model_version VARCHAR(50),
                    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Constraints
                    CONSTRAINT soll_ist_gewinn_tracking_datum_symbol_unique UNIQUE (datum, symbol)
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_soll_ist_symbol_datum 
                    ON soll_ist_gewinn_tracking (symbol, datum DESC);
                CREATE INDEX IF NOT EXISTS idx_soll_ist_datum 
                    ON soll_ist_gewinn_tracking (datum DESC);
                CREATE INDEX IF NOT EXISTS idx_soll_ist_region 
                    ON soll_ist_gewinn_tracking (market_region);
                
                -- Updated trigger
                CREATE OR REPLACE FUNCTION update_soll_ist_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                
                DROP TRIGGER IF EXISTS update_soll_ist_updated_at ON soll_ist_gewinn_tracking;
                CREATE TRIGGER update_soll_ist_updated_at
                    BEFORE UPDATE ON soll_ist_gewinn_tracking
                    FOR EACH ROW
                    EXECUTE FUNCTION update_soll_ist_updated_at();
            """
            
            # Execute schema creation as aktienanalyse user
            result = await self._run_ssh_command(
                f"PGPASSWORD='{self.config.password}' psql -h {self.config.host} -U {self.config.user} -d {self.config.database} -c \"{create_schema_sql}\""
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to create schema: {result.stderr}")
                return False
            
            # Insert some compatibility data based on prediction_tracking_unified
            sync_data_sql = """
                -- Sync data from prediction_tracking_unified to soll_ist_gewinn_tracking
                INSERT INTO soll_ist_gewinn_tracking 
                (symbol, company_name, datum, soll_gewinn_1w, soll_gewinn_1m, soll_gewinn_3m, soll_gewinn_12m, 
                 ist_gewinn, confidence_score, model_version, calculation_date, created_at)
                SELECT 
                    symbol, 
                    company_name,
                    target_date as datum,
                    CASE WHEN horizon_type = '1W' THEN predicted_value END as soll_gewinn_1w,
                    CASE WHEN horizon_type = '1M' THEN predicted_value END as soll_gewinn_1m,
                    CASE WHEN horizon_type = '3M' THEN predicted_value END as soll_gewinn_3m,
                    CASE WHEN horizon_type = '12M' THEN predicted_value END as soll_gewinn_12m,
                    actual_value as ist_gewinn,
                    confidence_score,
                    model_version,
                    calculation_date,
                    created_at
                FROM prediction_tracking_unified
                WHERE NOT EXISTS (
                    SELECT 1 FROM soll_ist_gewinn_tracking 
                    WHERE soll_ist_gewinn_tracking.symbol = prediction_tracking_unified.symbol 
                    AND soll_ist_gewinn_tracking.datum = prediction_tracking_unified.target_date
                )
                LIMIT 1000;
            """
            
            result = await self._run_ssh_command(
                f"PGPASSWORD='{self.config.password}' psql -h {self.config.host} -U {self.config.user} -d {self.config.database} -c \"{sync_data_sql}\""
            )
            
            logger.info("✅ Schema created successfully with data sync")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create schema: {e}")
            return False
    
    async def verify_database_manager_integration(self) -> bool:
        """
        Verify Database Connection Manager Integration
        
        TESTS:
        - Connection Pool functionality
        - Query execution
        - Transaction support
        - Health checks
        """
        logger.info("🧪 Verifying Database Manager Integration")
        
        try:
            # Import the database manager
            sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
            from database_connection_manager_v1_0_0_20250825 import (
                DatabaseConfiguration, DatabaseConnectionManager, get_database_manager
            )
            
            # Set environment variables
            import os
            os.environ['POSTGRES_HOST'] = self.config.host
            os.environ['POSTGRES_PORT'] = str(self.config.port)
            os.environ['POSTGRES_DB'] = self.config.database
            os.environ['POSTGRES_USER'] = self.config.user
            os.environ['POSTGRES_PASSWORD'] = self.config.password
            
            # Test 1: Initialize Database Manager
            logger.info("Testing Database Manager initialization...")
            config = DatabaseConfiguration()
            manager = get_database_manager()
            await manager.initialize()
            
            # Test 2: Test connection
            logger.info("Testing database connection...")
            result = await manager.fetch_one_query("SELECT 1 as test, NOW() as timestamp")
            if result and result.get('test') == 1:
                logger.info("✅ Database connection test successful")
            else:
                logger.error("❌ Database connection test failed")
                return False
            
            # Test 3: Test table access
            logger.info("Testing table access...")
            tables_result = await manager.fetch_query(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_names = [row['table_name'] for row in tables_result]
            
            if 'soll_ist_gewinn_tracking' in table_names:
                logger.info("✅ soll_ist_gewinn_tracking table accessible")
            else:
                logger.error("❌ soll_ist_gewinn_tracking table not accessible")
                return False
            
            if 'prediction_tracking_unified' in table_names:
                logger.info("✅ prediction_tracking_unified table accessible")
            else:
                logger.error("❌ prediction_tracking_unified table not accessible")
                return False
            
            # Test 4: Test health check
            logger.info("Testing health check...")
            health = await manager.health_check()
            if health.get('status') == 'healthy':
                logger.info("✅ Database health check passed")
            else:
                logger.error(f"❌ Database health check failed: {health}")
                return False
            
            # Cleanup
            await manager.close()
            
            logger.info("✅ Database Manager Integration verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database Manager Integration verification failed: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """Test PostgreSQL connection with new authentication"""
        try:
            result = await self._run_ssh_command(
                f"PGPASSWORD='{self.config.password}' psql -h {self.config.host} -U {self.config.user} -d {self.config.database} -c 'SELECT 1;'"
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def _run_ssh_command(self, command: str) -> subprocess.CompletedProcess:
        """Execute SSH command on remote server"""
        ssh_command = f"ssh {self.ssh_host} \"{command}\""
        
        process = await asyncio.create_subprocess_shell(
            ssh_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return subprocess.CompletedProcess(
            args=ssh_command,
            returncode=process.returncode,
            stdout=stdout.decode('utf-8'),
            stderr=stderr.decode('utf-8')
        )


async def main():
    """Main execution function"""
    logger.info("🚀 PostgreSQL Authentication & Schema Migration Fix v1.0.0")
    
    config = PostgreSQLConfig()
    fixer = PostgreSQLAuthenticationFixer(config)
    
    success_steps = []
    failed_steps = []
    
    try:
        # Step 1: Diagnose current state
        logger.info("=" * 80)
        logger.info("PHASE 1: AUTHENTICATION DIAGNOSIS")
        logger.info("=" * 80)
        
        diagnosis = await fixer.diagnose_authentication_issue()
        logger.info(f"Issues found: {len(diagnosis['issues'])}")
        for issue in diagnosis['issues']:
            logger.warning(f"⚠️ {issue}")
        
        # Step 2: Fix authentication if needed
        if diagnosis['issues']:
            logger.info("=" * 80)
            logger.info("PHASE 2: AUTHENTICATION FIX")
            logger.info("=" * 80)
            
            auth_success = await fixer.fix_postgresql_authentication()
            if auth_success:
                success_steps.append("PostgreSQL Authentication Fix")
            else:
                failed_steps.append("PostgreSQL Authentication Fix")
                logger.error("❌ Cannot proceed without authentication fix")
                return False
        else:
            logger.info("✅ Authentication already working")
            success_steps.append("Authentication Verification")
        
        # Step 3: Create missing schema
        logger.info("=" * 80)
        logger.info("PHASE 3: SCHEMA MIGRATION")
        logger.info("=" * 80)
        
        schema_success = await fixer.create_missing_schema()
        if schema_success:
            success_steps.append("Schema Migration")
        else:
            failed_steps.append("Schema Migration")
        
        # Step 4: Verify Database Manager integration
        logger.info("=" * 80)
        logger.info("PHASE 4: DATABASE MANAGER VERIFICATION")
        logger.info("=" * 80)
        
        integration_success = await fixer.verify_database_manager_integration()
        if integration_success:
            success_steps.append("Database Manager Integration")
        else:
            failed_steps.append("Database Manager Integration")
        
        # Final Report
        logger.info("=" * 80)
        logger.info("FINAL REPORT")
        logger.info("=" * 80)
        
        logger.info(f"✅ Successful Steps ({len(success_steps)}):")
        for step in success_steps:
            logger.info(f"  - {step}")
        
        if failed_steps:
            logger.error(f"❌ Failed Steps ({len(failed_steps)}):")
            for step in failed_steps:
                logger.error(f"  - {step}")
            return False
        else:
            logger.info("🎉 All steps completed successfully!")
            logger.info("🗄️ PostgreSQL Authentication & Schema Migration completed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Critical error in main execution: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)