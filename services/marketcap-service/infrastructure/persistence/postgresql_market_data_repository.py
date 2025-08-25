#!/usr/bin/env python3
"""
MarketCap Service v6.1.0 - PostgreSQL Market Data Repository
Clean Architecture v6.1.0 - Database Manager Integration

PostgreSQL Implementation für Market Data Repository
- Database Manager für Verbindungsmanagement
- Optimierte Indizierung für Performance
- Async Repository Pattern mit Connection Pooling

Autor: Claude Code
Datum: 25. August 2025
Version: 6.1.0
"""

import structlog
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import sys

# Database Manager Import - Direct Path Import
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import DatabaseConnectionManager

from ...domain.entities.market_data import MarketData
from ...domain.repositories.market_data_repository import IMarketDataRepository

logger = structlog.get_logger(__name__)


class PostgreSQLMarketDataRepository(IMarketDataRepository):
    """
    PostgreSQL-based Market Data Repository Implementation
    
    INFRASTRUCTURE LAYER: Concrete implementation with Database Manager
    CONNECTION POOLING: Managed through central Database Manager
    PERFORMANCE: Optimized with proper indexing and async operations
    """
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operations_count = 0
        self._initialized_at = datetime.now()
    
    async def initialize_schema(self) -> bool:
        """Initialize market data schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create market data table with optimized schema
                await connection.execute('''
                    CREATE TABLE IF NOT EXISTS market_data (
                        symbol VARCHAR(10) PRIMARY KEY,
                        company_name VARCHAR(255) NOT NULL,
                        market_cap DECIMAL(18,2) NOT NULL CHECK (market_cap >= 0),
                        stock_price DECIMAL(12,4) NOT NULL CHECK (stock_price >= 0),
                        daily_change_percent DECIMAL(8,4) NOT NULL CHECK (
                            daily_change_percent >= -100 AND daily_change_percent <= 1000
                        ),
                        timestamp TIMESTAMPTZ NOT NULL,
                        source VARCHAR(100) NOT NULL DEFAULT 'marketcap_service',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                ''')
                
                # Create optimized indices
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_market_data_timestamp 
                    ON market_data(timestamp DESC)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_market_data_market_cap 
                    ON market_data(market_cap DESC)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_market_data_daily_change 
                    ON market_data(daily_change_percent DESC)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_market_data_company_name 
                    ON market_data USING gin(to_tsvector('english', company_name))
                ''')
                
                # Create updated_at trigger
                await connection.execute('''
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = NOW();
                        RETURN NEW;
                    END;
                    $$ language plpgsql;
                ''')
                
                await connection.execute('''
                    DROP TRIGGER IF EXISTS update_market_data_updated_at ON market_data;
                    CREATE TRIGGER update_market_data_updated_at 
                    BEFORE UPDATE ON market_data
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                ''')
                
                logger.info("Market data schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error("Failed to initialize market data schema", error=str(e))
            return False
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Retrieve market data for a symbol
        
        Args:
            symbol: Stock symbol to retrieve data for
            
        Returns:
            MarketData entity or None if not found
        """
        try:
            self._operations_count += 1
            symbol = symbol.upper().strip()
            
            async with self.db_manager.get_connection() as connection:
                row = await connection.fetchrow(
                    '''SELECT symbol, company_name, market_cap, stock_price, 
                              daily_change_percent, timestamp, source
                       FROM market_data 
                       WHERE symbol = $1''',
                    symbol
                )
                
                if row:
                    return MarketData(
                        symbol=row['symbol'],
                        company_name=row['company_name'],
                        market_cap=Decimal(str(row['market_cap'])),
                        stock_price=Decimal(str(row['stock_price'])),
                        daily_change_percent=Decimal(str(row['daily_change_percent'])),
                        timestamp=row['timestamp'],
                        source=row['source']
                    )
                
                logger.debug("Market data not found", symbol=symbol)
                return None
                
        except Exception as e:
            logger.error("Failed to get market data", error=str(e), symbol=symbol)
            return None
    
    async def save_market_data(self, market_data: MarketData) -> bool:
        """
        Save market data with UPSERT functionality
        
        Args:
            market_data: MarketData entity to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                await connection.execute(
                    '''INSERT INTO market_data 
                       (symbol, company_name, market_cap, stock_price, 
                        daily_change_percent, timestamp, source, created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                       ON CONFLICT (symbol) 
                       DO UPDATE SET 
                           company_name = EXCLUDED.company_name,
                           market_cap = EXCLUDED.market_cap,
                           stock_price = EXCLUDED.stock_price,
                           daily_change_percent = EXCLUDED.daily_change_percent,
                           timestamp = EXCLUDED.timestamp,
                           source = EXCLUDED.source,
                           updated_at = NOW()''',
                    market_data.symbol.upper(),
                    market_data.company_name,
                    market_data.market_cap,
                    market_data.stock_price,
                    market_data.daily_change_percent,
                    market_data.timestamp,
                    market_data.source
                )
                
                logger.info("Market data saved successfully", symbol=market_data.symbol)
                return True
                
        except Exception as e:
            logger.error("Failed to save market data", error=str(e), symbol=market_data.symbol)
            return False
    
    async def get_all_symbols(self) -> List[str]:
        """
        Get all available symbols
        
        Returns:
            List of available stock symbols
        """
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    'SELECT symbol FROM market_data ORDER BY symbol'
                )
                
                symbols = [row['symbol'] for row in rows]
                logger.debug("Retrieved symbols from database", count=len(symbols))
                return symbols
                
        except Exception as e:
            logger.error("Failed to get all symbols", error=str(e))
            return []
    
    async def get_market_data_by_cap_size(self, cap_classification: str) -> List[MarketData]:
        """
        Get market data filtered by cap size using PostgreSQL logic
        
        Args:
            cap_classification: "Large Cap", "Mid Cap", or "Small Cap"
            
        Returns:
            List of MarketData entities matching cap classification
        """
        try:
            self._operations_count += 1
            
            # Define cap size ranges (same as business logic in domain)
            if cap_classification == "Large Cap":
                cap_filter = "market_cap >= 10000000000"  # >= 10 billion
            elif cap_classification == "Mid Cap":
                cap_filter = "market_cap >= 2000000000 AND market_cap < 10000000000"  # 2-10 billion
            elif cap_classification == "Small Cap":
                cap_filter = "market_cap < 2000000000"  # < 2 billion
            else:
                logger.warning("Invalid cap classification", classification=cap_classification)
                return []
            
            async with self.db_manager.get_connection() as connection:
                query = f'''
                    SELECT symbol, company_name, market_cap, stock_price, 
                           daily_change_percent, timestamp, source
                    FROM market_data 
                    WHERE {cap_filter}
                    ORDER BY market_cap DESC
                '''
                
                rows = await connection.fetch(query)
                
                market_data_list = []
                for row in rows:
                    market_data_list.append(MarketData(
                        symbol=row['symbol'],
                        company_name=row['company_name'],
                        market_cap=Decimal(str(row['market_cap'])),
                        stock_price=Decimal(str(row['stock_price'])),
                        daily_change_percent=Decimal(str(row['daily_change_percent'])),
                        timestamp=row['timestamp'],
                        source=row['source']
                    ))
                
                logger.debug("Retrieved market data by cap size", 
                           classification=cap_classification, count=len(market_data_list))
                return market_data_list
                
        except Exception as e:
            logger.error("Failed to get market data by cap size", 
                        error=str(e), classification=cap_classification)
            return []
    
    async def get_fresh_market_data(self, max_age_minutes: int = 15) -> List[MarketData]:
        """
        Get fresh market data within age limit
        
        Args:
            max_age_minutes: Maximum age of data in minutes
            
        Returns:
            List of fresh MarketData entities
        """
        try:
            self._operations_count += 1
            cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT symbol, company_name, market_cap, stock_price, 
                              daily_change_percent, timestamp, source
                       FROM market_data 
                       WHERE timestamp >= $1
                       ORDER BY timestamp DESC''',
                    cutoff_time
                )
                
                fresh_data = []
                for row in rows:
                    fresh_data.append(MarketData(
                        symbol=row['symbol'],
                        company_name=row['company_name'],
                        market_cap=Decimal(str(row['market_cap'])),
                        stock_price=Decimal(str(row['stock_price'])),
                        daily_change_percent=Decimal(str(row['daily_change_percent'])),
                        timestamp=row['timestamp'],
                        source=row['source']
                    ))
                
                logger.debug("Retrieved fresh market data", 
                           max_age_minutes=max_age_minutes, count=len(fresh_data))
                return fresh_data
                
        except Exception as e:
            logger.error("Failed to get fresh market data", error=str(e))
            return []
    
    async def delete_stale_data(self, max_age_hours: int = 24) -> int:
        """
        Delete stale market data
        
        Args:
            max_age_hours: Maximum age of data to keep in hours
            
        Returns:
            Number of records deleted
        """
        try:
            self._operations_count += 1
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            async with self.db_manager.get_connection() as connection:
                result = await connection.execute(
                    'DELETE FROM market_data WHERE timestamp < $1',
                    cutoff_time
                )
                
                # Extract number of deleted rows from result
                deleted_count = int(result.split()[-1]) if result else 0
                
                logger.info("Deleted stale market data", 
                          deleted_count=deleted_count, max_age_hours=max_age_hours)
                return deleted_count
                
        except Exception as e:
            logger.error("Failed to delete stale data", error=str(e))
            return 0
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get repository health status
        
        Returns:
            Health status dictionary
        """
        try:
            async with self.db_manager.get_connection() as connection:
                # Get total records count
                total_result = await connection.fetchval(
                    'SELECT COUNT(*) FROM market_data'
                )
                total_records = total_result or 0
                
                # Get fresh records count
                cutoff_time = datetime.now() - timedelta(minutes=15)
                fresh_result = await connection.fetchval(
                    'SELECT COUNT(*) FROM market_data WHERE timestamp >= $1',
                    cutoff_time
                )
                fresh_records = fresh_result or 0
                
                uptime = datetime.now() - self._initialized_at
                
                return {
                    'status': 'healthy',
                    'repository_type': 'postgresql',
                    'total_records': total_records,
                    'fresh_records': fresh_records,
                    'stale_records': total_records - fresh_records,
                    'operations_count': self._operations_count,
                    'uptime_seconds': int(uptime.total_seconds()),
                    'initialized_at': self._initialized_at.isoformat(),
                    'last_check': datetime.now().isoformat(),
                    'database': 'PostgreSQL'
                }
                
        except Exception as e:
            logger.error("Failed to get health status", error=str(e))
            return {
                'status': 'unhealthy',
                'repository_type': 'postgresql',
                'error': str(e),
                'database': 'PostgreSQL'
            }
    
    async def clear_all_data(self) -> int:
        """
        Clear all data (utility method - use with caution)
        
        Returns:
            Number of records cleared
        """
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                result = await connection.execute('DELETE FROM market_data')
                deleted_count = int(result.split()[-1]) if result else 0
                
                logger.warning("Cleared all market data", deleted_count=deleted_count)
                return deleted_count
                
        except Exception as e:
            logger.error("Failed to clear all data", error=str(e))
            return 0
    
    async def get_repository_stats(self) -> Dict[str, Any]:
        """
        Get detailed repository statistics
        
        Returns:
            Repository statistics dictionary
        """
        try:
            async with self.db_manager.get_connection() as connection:
                # Get basic stats
                stats_query = '''
                    SELECT 
                        COUNT(*) as total_symbols,
                        COUNT(CASE WHEN market_cap >= 10000000000 THEN 1 END) as large_cap_count,
                        COUNT(CASE WHEN market_cap >= 2000000000 AND market_cap < 10000000000 THEN 1 END) as mid_cap_count,
                        COUNT(CASE WHEN market_cap < 2000000000 THEN 1 END) as small_cap_count,
                        COUNT(CASE WHEN daily_change_percent > 0 THEN 1 END) as positive_performance_count,
                        AVG(market_cap) as avg_market_cap,
                        AVG(stock_price) as avg_stock_price,
                        AVG(daily_change_percent) as avg_daily_change
                    FROM market_data
                '''
                
                stats_row = await connection.fetchrow(stats_query)
                
                # Get all symbols
                symbols_rows = await connection.fetch('SELECT symbol FROM market_data ORDER BY symbol')
                symbols = [row['symbol'] for row in symbols_rows]
                
                total_symbols = stats_row['total_symbols'] or 0
                
                return {
                    'total_symbols': total_symbols,
                    'symbols': symbols,
                    'cap_distribution': {
                        'Large Cap': stats_row['large_cap_count'] or 0,
                        'Mid Cap': stats_row['mid_cap_count'] or 0,
                        'Small Cap': stats_row['small_cap_count'] or 0
                    },
                    'positive_performance_count': stats_row['positive_performance_count'] or 0,
                    'negative_performance_count': total_symbols - (stats_row['positive_performance_count'] or 0),
                    'operations_count': self._operations_count,
                    'averages': {
                        'market_cap': float(stats_row['avg_market_cap']) if stats_row['avg_market_cap'] else 0.0,
                        'stock_price': float(stats_row['avg_stock_price']) if stats_row['avg_stock_price'] else 0.0,
                        'daily_change_percent': float(stats_row['avg_daily_change']) if stats_row['avg_daily_change'] else 0.0
                    },
                    'database': 'PostgreSQL'
                }
                
        except Exception as e:
            logger.error("Failed to get repository stats", error=str(e))
            return {
                'total_symbols': 0,
                'symbols': [],
                'cap_distribution': {'Large Cap': 0, 'Mid Cap': 0, 'Small Cap': 0},
                'positive_performance_count': 0,
                'negative_performance_count': 0,
                'operations_count': self._operations_count,
                'error': str(e),
                'database': 'PostgreSQL'
            }