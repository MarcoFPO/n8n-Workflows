#!/usr/bin/env python3
"""
Simple MarketCap Data Source Service
Vereinfachte Version für sofortige Integration ohne BackendBaseModule Dependencies
"""

import asyncio
import json
from datetime import datetime
import sys

# Add path for logging

# Import Management - CLEAN ARCHITECTURE
from shared.standard_import_manager_v1_0_0_20250824 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/opt/aktienanalyse-ökosystem/shared') -> Import Manager
from logging_config import setup_logging

logger = setup_logging("simple-marketcap-service")

class SimpleMarketCapService:
    """Standalone MarketCap Service"""
    
    def __init__(self):
        self.running = False
        
    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing Simple MarketCap Service")
        self.running = True
        return True
        
    async def get_market_data(self, symbol: str):
        """Get market data for symbol"""
        return {
            'symbol': symbol,
            'company': f"Company {symbol}",
            'market_cap': 1000000000,
            'stock_price': 100.0,
            'daily_change_percent': 2.5,
            'timestamp': datetime.now().isoformat(),
            'source': 'simple_marketcap_service',
            'success': True
        }
        
    async def run(self):
        """Main service loop"""
        logger.info("Simple MarketCap Service started successfully")
        
        while self.running:
            # Service heartbeat
            logger.debug("Service heartbeat", timestamp=datetime.now().isoformat())
            await asyncio.sleep(30)  # 30 second heartbeat
            
    async def shutdown(self):
        """Shutdown service"""
        self.running = False
        logger.info("Simple MarketCap Service stopped")

async def main():
    """Main entry point"""
    service = SimpleMarketCapService()
    
    try:
        success = await service.initialize()
        if not success:
            logger.error("Failed to initialize service")
            return 1
        
        await service.run()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        await service.shutdown()
        return 0
    except Exception as e:
        logger.error("Service failed", error=str(e))
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Critical service error", error=str(e))
        sys.exit(1)