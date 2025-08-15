#!/usr/bin/env python3
"""
CompaniesMarketCap Service
Eigenständiger Service für MarketCap-Datenabfragen
"""

import asyncio
import sys
from datetime import datetime

# Add paths for imports
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')

from event_bus import EventBusConnector
from logging_config import setup_logging
from modules.companies_marketcap_connector_v1_2_0_20250814 import CompaniesMarketCapConnector

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Logging setup
logger = setup_logging("companies-marketcap-service")


class CompaniesMarketCapService:
    """Standalone Service für CompaniesMarketCap Integration"""
    
    def __init__(self):
        self.event_bus = EventBusConnector("companies-marketcap-service")
        self.marketcap_connector = None
        self.is_running = False
        
    async def initialize(self) -> bool:
        """Initialize service and connector"""
        try:
            logger.info("Initializing CompaniesMarketCap Service")
            
            # Connect to event bus
            await self.event_bus.connect()
            
            # Initialize MarketCap connector
            self.marketcap_connector = CompaniesMarketCapConnector(self.event_bus)
            await self.marketcap_connector.initialize()
            
            self.is_running = True
            logger.info("CompaniesMarketCap Service initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize CompaniesMarketCap Service", error=str(e))
            return False
    
    async def run(self):
        """Run the service"""
        try:
            logger.info("Starting CompaniesMarketCap Service...")
            
            # Keep service running
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error("Service error", error=str(e))
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown service"""
        try:
            logger.info("Shutting down CompaniesMarketCap Service")
            self.is_running = False
            
            if self.marketcap_connector:
                await self.marketcap_connector.shutdown()
            
            if self.event_bus:
                await self.event_bus.disconnect()
                
            logger.info("CompaniesMarketCap Service shutdown complete")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


async def main():
    """Main entry point"""
    service = CompaniesMarketCapService()
    
    try:
        success = await service.initialize()
        if not success:
            logger.error("Failed to initialize service")
            return 1
        
        await service.run()
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