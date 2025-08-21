#!/usr/bin/env python3
"""
Database Connection v1.0.0
PostgreSQL-Datenbankverbindung für ML-Pipeline

Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool, Connection
from asyncpg.exceptions import PostgresError

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Database Connection für ML-Pipeline
    PostgreSQL mit asyncpg für optimale Performance
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Connection Pool
        self.pool: Optional[Pool] = None
        
        # Connection State
        self.is_connected = False
        
        # Query Statistics
        self.queries_executed = 0
        self.query_times = []
        self.connection_count = 0
        
        # Connection URL
        self.connection_url = self._build_connection_url()
    
    def _build_connection_url(self) -> str:
        """Erstellt PostgreSQL Connection URL"""
        return (
            f"postgresql://{self.config['user']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
            f"?sslmode=disable"
        )
    
    async def connect(self):
        """Erstellt Connection Pool"""
        try:
            self.logger.info("Connecting to PostgreSQL database...")
            
            # Connection Pool erstellen
            self.pool = await asyncpg.create_pool(
                self.connection_url,
                min_size=self.config.get('min_connections', 5),
                max_size=self.config.get('max_connections', 20),
                max_queries=self.config.get('max_queries_per_connection', 50000),
                max_inactive_connection_lifetime=self.config.get('max_inactive_lifetime', 300),
                command_timeout=self.config.get('command_timeout', 60),
                server_settings={
                    'application_name': self.config.get('application_name', 'ml-analytics'),
                    'jit': 'off'  # JIT off für konsistente Performance
                }
            )
            
            # Connection testen
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
                
                # TimescaleDB Extension prüfen
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
                )
                if result:
                    self.logger.info("TimescaleDB extension detected")
            
            self.is_connected = True
            self.logger.info("Database connected successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    async def disconnect(self):
        """Schließt Connection Pool"""
        try:
            if self.pool:
                await self.pool.close()
                self.pool = None
            
            self.is_connected = False
            self.logger.info("Database disconnected")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from database: {str(e)}")
    
    @asynccontextmanager
    async def acquire_connection(self):
        """Context Manager für Database Connection"""
        if not self.is_connected or not self.pool:
            raise RuntimeError("Database not connected")
        
        conn = None
        try:
            conn = await self.pool.acquire()
            self.connection_count += 1
            yield conn
        finally:
            if conn:
                await self.pool.release(conn)
    
    async def execute(self, query: str, params: Optional[List[Any]] = None) -> str:
        """Führt INSERT/UPDATE/DELETE Query aus"""
        start_time = time.time()
        
        try:
            async with self.acquire_connection() as conn:
                if params:
                    result = await conn.execute(query, *params)
                else:
                    result = await conn.execute(query)
                
                # Statistics
                self.queries_executed += 1
                query_time = (time.time() - start_time) * 1000
                self.query_times.append(query_time)
                
                self.logger.debug(f"Query executed in {query_time:.1f}ms")
                return result
                
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            raise
    
    async def fetch_all(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Führt SELECT Query aus und gibt alle Zeilen zurück"""
        start_time = time.time()
        
        try:
            async with self.acquire_connection() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)
                
                # Convert zu Dict-Liste
                result = [dict(row) for row in rows]
                
                # Statistics
                self.queries_executed += 1
                query_time = (time.time() - start_time) * 1000
                self.query_times.append(query_time)
                
                self.logger.debug(f"Fetched {len(result)} rows in {query_time:.1f}ms")
                return result
                
        except Exception as e:
            self.logger.error(f"Query fetch failed: {str(e)}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            raise
    
    async def fetch_one(self, query: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
        """Führt SELECT Query aus und gibt eine Zeile zurück"""
        start_time = time.time()
        
        try:
            async with self.acquire_connection() as conn:
                if params:
                    row = await conn.fetchrow(query, *params)
                else:
                    row = await conn.fetchrow(query)
                
                result = dict(row) if row else None
                
                # Statistics
                self.queries_executed += 1
                query_time = (time.time() - start_time) * 1000
                self.query_times.append(query_time)
                
                self.logger.debug(f"Fetched row in {query_time:.1f}ms")
                return result
                
        except Exception as e:
            self.logger.error(f"Query fetchone failed: {str(e)}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            raise
    
    async def fetch_val(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """Führt SELECT Query aus und gibt einen einzelnen Wert zurück"""
        start_time = time.time()
        
        try:
            async with self.acquire_connection() as conn:
                if params:
                    result = await conn.fetchval(query, *params)
                else:
                    result = await conn.fetchval(query)
                
                # Statistics
                self.queries_executed += 1
                query_time = (time.time() - start_time) * 1000
                self.query_times.append(query_time)
                
                self.logger.debug(f"Fetched value in {query_time:.1f}ms")
                return result
                
        except Exception as e:
            self.logger.error(f"Query fetchval failed: {str(e)}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            raise
    
    async def execute_transaction(self, queries: List[tuple]) -> List[Any]:
        """
        Führt mehrere Queries in einer Transaktion aus
        queries: List von (query, params) Tuples
        """
        start_time = time.time()
        results = []
        
        try:
            async with self.acquire_connection() as conn:
                async with conn.transaction():
                    for query, params in queries:
                        if params:
                            result = await conn.execute(query, *params)
                        else:
                            result = await conn.execute(query)
                        results.append(result)
                
                # Statistics
                self.queries_executed += len(queries)
                transaction_time = (time.time() - start_time) * 1000
                self.query_times.append(transaction_time)
                
                self.logger.debug(f"Transaction with {len(queries)} queries completed in {transaction_time:.1f}ms")
                return results
                
        except Exception as e:
            self.logger.error(f"Transaction failed: {str(e)}")
            raise
    
    async def bulk_insert(self, table: str, columns: List[str], data: List[List[Any]]) -> int:
        """Bulk Insert für große Datenmengen"""
        start_time = time.time()
        
        try:
            async with self.acquire_connection() as conn:
                # COPY-basierter Bulk Insert
                result = await conn.copy_records_to_table(
                    table_name=table,
                    records=data,
                    columns=columns
                )
                
                # Statistics
                self.queries_executed += 1
                insert_time = (time.time() - start_time) * 1000
                self.query_times.append(insert_time)
                
                self.logger.info(f"Bulk inserted {len(data)} records into {table} in {insert_time:.1f}ms")
                return len(data)
                
        except Exception as e:
            self.logger.error(f"Bulk insert failed: {str(e)}")
            raise
    
    async def execute_stored_procedure(self, procedure_name: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Führt Stored Procedure aus"""
        start_time = time.time()
        
        try:
            async with self.acquire_connection() as conn:
                if params:
                    query = f"SELECT * FROM {procedure_name}({','.join(['$' + str(i+1) for i in range(len(params))])})"
                    rows = await conn.fetch(query, *params)
                else:
                    query = f"SELECT * FROM {procedure_name}()"
                    rows = await conn.fetch(query)
                
                result = [dict(row) for row in rows]
                
                # Statistics
                self.queries_executed += 1
                procedure_time = (time.time() - start_time) * 1000
                self.query_times.append(procedure_time)
                
                self.logger.debug(f"Stored procedure {procedure_name} executed in {procedure_time:.1f}ms")
                return result
                
        except Exception as e:
            self.logger.error(f"Stored procedure {procedure_name} failed: {str(e)}")
            raise
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Lädt Tabellen-Informationen"""
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = $1 AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        
        columns = await self.fetch_all(query, [table_name])
        
        # Tabellen-Statistiken
        stats_query = f"""
            SELECT 
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size('{table_name}')) as table_size
        """
        
        try:
            stats = await self.fetch_one(stats_query)
        except:
            stats = {'row_count': 0, 'table_size': '0 bytes'}
        
        return {
            'table_name': table_name,
            'columns': columns,
            'statistics': stats
        }
    
    async def get_database_statistics(self) -> Dict[str, Any]:
        """Lädt Database-Statistiken"""
        try:
            # Connection Pool Statistics
            pool_stats = {
                'size': self.pool.get_size() if self.pool else 0,
                'min_size': self.pool.get_min_size() if self.pool else 0,
                'max_size': self.pool.get_max_size() if self.pool else 0,
                'idle_connections': self.pool.get_idle_size() if self.pool else 0
            }
            
            # Query Performance
            avg_query_time = (
                sum(self.query_times[-100:]) / len(self.query_times[-100:])
                if self.query_times else 0
            )
            
            # Database Info
            db_info = {}
            try:
                async with self.acquire_connection() as conn:
                    # Database Size
                    db_size = await conn.fetchval(
                        "SELECT pg_size_pretty(pg_database_size(current_database()))"
                    )
                    
                    # Active Connections
                    active_conns = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM pg_stat_activity 
                        WHERE state = 'active' AND datname = current_database()
                        """
                    )
                    
                    # ML Tables Count
                    ml_tables = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name LIKE 'ml_%'
                        """
                    )
                    
                    db_info = {
                        'database_size': db_size,
                        'active_connections': active_conns,
                        'ml_tables_count': ml_tables
                    }
                    
            except Exception as e:
                self.logger.warning(f"Failed to get database info: {str(e)}")
                db_info = {'error': str(e)}
            
            return {
                'connection_status': 'connected' if self.is_connected else 'disconnected',
                'pool_statistics': pool_stats,
                'query_statistics': {
                    'queries_executed': self.queries_executed,
                    'connections_acquired': self.connection_count,
                    'avg_query_time_ms': round(avg_query_time, 2)
                },
                'database_info': db_info
            }
            
        except Exception as e:
            return {
                'connection_status': 'error',
                'error': str(e)
            }
    
    async def test_ml_schema(self) -> Dict[str, Any]:
        """Testet ML-Schema-Verfügbarkeit"""
        try:
            # ML-Tabellen prüfen
            ml_tables_query = """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE 'ml_%'
                ORDER BY table_name
            """
            
            ml_tables = await self.fetch_all(ml_tables_query)
            table_names = [row['table_name'] for row in ml_tables]
            
            # ML-Funktionen prüfen
            ml_functions_query = """
                SELECT routine_name FROM information_schema.routines 
                WHERE routine_schema = 'public' AND routine_name LIKE '%ml_%'
                ORDER BY routine_name
            """
            
            ml_functions = await self.fetch_all(ml_functions_query)
            function_names = [row['routine_name'] for row in ml_functions]
            
            # Schema-Version prüfen
            schema_version = None
            try:
                schema_version = await self.fetch_val(
                    "SELECT version FROM ml_schema_version ORDER BY deployed_at DESC LIMIT 1"
                )
            except:
                pass
            
            return {
                'ml_schema_available': len(table_names) > 0,
                'ml_tables': table_names,
                'ml_functions': function_names,
                'schema_version': schema_version,
                'tables_count': len(table_names),
                'functions_count': len(function_names)
            }
            
        except Exception as e:
            return {
                'ml_schema_available': False,
                'error': str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für Database Connection"""
        try:
            if not self.is_connected:
                return {'status': 'disconnected'}
            
            # Connection Test
            ping_start = time.time()
            async with self.acquire_connection() as conn:
                await conn.execute('SELECT 1')
            ping_time = (time.time() - ping_start) * 1000
            
            # Pool Health
            pool_healthy = (
                self.pool.get_size() > 0 and 
                self.pool.get_idle_size() >= 0 and
                ping_time < 1000  # < 1s
            )
            
            return {
                'status': 'healthy' if pool_healthy else 'warning',
                'ping_time_ms': round(ping_time, 2),
                'pool_size': self.pool.get_size(),
                'idle_connections': self.pool.get_idle_size(),
                'connection_stable': ping_time < 100
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error': str(e)
            }