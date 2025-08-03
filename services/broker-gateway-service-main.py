#!/usr/bin/env python3
"""
Aktienanalyse Broker-Gateway Service
Unified API Gateway for Bitpanda Pro and other brokers
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import aiohttp
import asyncpg
import structlog
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# Logging Setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Pydantic Models
class BitpandaCredentials(BaseModel):
    api_key: str
    api_secret: str = Field(..., description="API Secret for Bitpanda Pro")
    environment: str = Field(default="sandbox", description="sandbox or production")

class OrderRequest(BaseModel):
    instrument_code: str = Field(..., description="Trading pair e.g. BTC_EUR")
    side: str = Field(..., description="BUY or SELL")
    type: str = Field(default="MARKET", description="MARKET or LIMIT")
    amount: str = Field(..., description="Amount to trade")
    price: Optional[str] = Field(None, description="Price for LIMIT orders")
    client_id: Optional[str] = Field(None, description="Client order ID")

class OrderResponse(BaseModel):
    order_id: str
    status: str
    instrument_code: str
    side: str
    type: str
    amount: str
    price: Optional[str]
    created_at: datetime
    updated_at: datetime

class AccountBalance(BaseModel):
    currency_code: str
    available: str
    locked: str
    total: str

class MarketData(BaseModel):
    instrument_code: str
    last_price: str
    best_bid: str
    best_ask: str
    price_change: str
    price_change_percentage: str
    high_24h: str
    low_24h: str
    volume_24h: str
    timestamp: datetime

# Broker Gateway Service
class BrokerGatewayService:
    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.event_bus_url = os.getenv("EVENT_BUS_URL", "http://localhost:8081")
        self.bitpanda_api_base = {
            "sandbox": "https://api.exchange.bitpanda.com",
            "production": "https://api.exchange.bitpanda.com"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize database connection and HTTP session"""
        try:
            # Database connection
            postgres_url = os.getenv("POSTGRES_URL", "postgresql://aktienanalyse:secure_password@localhost:5432/aktienanalyse_events?sslmode=disable")
            self.db_pool = await asyncpg.create_pool(postgres_url, min_size=2, max_size=10)
            
            # HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "aktienanalyse-broker-gateway/1.0"}
            )
            
            logger.info("Broker-Gateway Service initialized", database="connected", session="ready")
            
        except Exception as e:
            logger.error("Failed to initialize Broker-Gateway Service", error=str(e))
            raise

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        if self.db_pool:
            await self.db_pool.close()

    async def publish_event(self, event_type: str, aggregate_id: str, event_data: Dict[str, Any]):
        """Publish event to Event-Bus"""
        try:
            if not self.session:
                return False
                
            event = {
                "stream_id": f"broker-gateway-{int(time.time())}",
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "aggregate_type": "BrokerOperation",
                "event_data": event_data,
                "metadata": {
                    "source": "broker-gateway-service",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            async with self.session.post(
                f"{self.event_bus_url}/events/publish",
                json=event,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    logger.info("Event published", event_type=event_type, aggregate_id=aggregate_id)
                    return True
                else:
                    logger.error("Failed to publish event", status=response.status)
                    return False
                    
        except Exception as e:
            logger.error("Error publishing event", event_type=event_type, error=str(e))
            return False

    async def get_bitpanda_headers(self, credentials: BitpandaCredentials) -> Dict[str, str]:
        """Generate Bitpanda API headers with authentication"""
        return {
            "Authorization": f"Bearer {credentials.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_account_balances(self, credentials: BitpandaCredentials) -> List[AccountBalance]:
        """Get account balances from Bitpanda Pro"""
        try:
            # For demo purposes, return mock data
            # In production, integrate with real Bitpanda API
            mock_balances = [
                AccountBalance(
                    currency_code="EUR",
                    available="1000.00",
                    locked="0.00",
                    total="1000.00"
                ),
                AccountBalance(
                    currency_code="BTC",
                    available="0.025",
                    locked="0.0",
                    total="0.025"
                )
            ]
            
            await self.publish_event(
                "account.balances.retrieved",
                "bitpanda_account",
                {"balances_count": len(mock_balances), "currencies": [b.currency_code for b in mock_balances]}
            )
            
            return mock_balances
                    
        except Exception as e:
            logger.error("Error getting account balances", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get balances: {str(e)}")

    async def get_market_data(self, instrument_code: str) -> MarketData:
        """Get market data for trading pair"""
        try:
            # For demo purposes, return mock data
            # In production, integrate with real Bitpanda API
            mock_data = MarketData(
                instrument_code=instrument_code,
                last_price="45000.00",
                best_bid="44950.00", 
                best_ask="45050.00",
                price_change="500.00",
                price_change_percentage="1.12",
                high_24h="45500.00",
                low_24h="44200.00",
                volume_24h="125.5",
                timestamp=datetime.utcnow()
            )
            
            await self.publish_event(
                "market.data.retrieved", 
                instrument_code,
                {
                    "instrument": instrument_code,
                    "price": mock_data.last_price,
                    "volume": mock_data.volume_24h
                }
            )
            
            return mock_data
            
        except Exception as e:
            logger.error("Error getting market data", instrument=instrument_code, error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get market data: {str(e)}")

    async def place_order(self, order_request: OrderRequest, credentials: BitpandaCredentials) -> OrderResponse:
        """Place order via Bitpanda Pro API"""
        try:
            # For demo purposes, return mock response
            # In production, use real Bitpanda API
            mock_response = OrderResponse(
                order_id=f"order_{int(time.time())}",
                status="FILLED",
                instrument_code=order_request.instrument_code,
                side=order_request.side,
                type=order_request.type,
                amount=order_request.amount,
                price=order_request.price,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await self.publish_event(
                "order.placed",
                mock_response.order_id,
                {
                    "order_id": mock_response.order_id,
                    "instrument": order_request.instrument_code,
                    "side": order_request.side,
                    "amount": order_request.amount,
                    "status": mock_response.status
                }
            )
            
            return mock_response
            
        except Exception as e:
            logger.error("Error placing order", order=order_request.dict(), error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")

# Global service instance
broker_service = BrokerGatewayService()

# FastAPI Application
app = FastAPI(
    title="Aktienanalyse Broker-Gateway Service",
    description="Unified API Gateway for Bitpanda Pro and other brokers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        if broker_service.db_pool:
            async with broker_service.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        
        return {
            "service": "broker-gateway",
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# Bitpanda Pro Endpoints
@app.get("/bitpanda/balances", response_model=List[AccountBalance])
async def get_bitpanda_balances(
    api_key: str,
    environment: str = "sandbox"
):
    """Get account balances from Bitpanda Pro"""
    credentials = BitpandaCredentials(
        api_key=api_key,
        api_secret="dummy_secret",  # For demo
        environment=environment
    )
    return await broker_service.get_account_balances(credentials)

@app.get("/bitpanda/market/{instrument_code}", response_model=MarketData)
async def get_bitpanda_market_data(instrument_code: str):
    """Get market data for trading pair"""
    return await broker_service.get_market_data(instrument_code)

@app.post("/bitpanda/orders", response_model=OrderResponse)
async def place_bitpanda_order(
    order_request: OrderRequest,
    api_key: str,
    environment: str = "sandbox"
):
    """Place order via Bitpanda Pro"""
    credentials = BitpandaCredentials(
        api_key=api_key,
        api_secret="dummy_secret",  # For demo
        environment=environment
    )
    return await broker_service.place_order(order_request, credentials)

# Generic Broker Endpoints
@app.get("/brokers/supported")
async def get_supported_brokers():
    """Get list of supported brokers"""
    return {
        "supported_brokers": [
            {
                "name": "Bitpanda Pro",
                "code": "bitpanda",
                "features": ["spot_trading", "market_data", "account_info"],
                "environments": ["sandbox", "production"]
            }
        ],
        "total_count": 1
    }

@app.get("/orders/history")
async def get_order_history(
    broker: str = "bitpanda",
    limit: int = 50
):
    """Get order history from database"""
    try:
        async with broker_service.db_pool.acquire() as conn:
            # Query order history from events table
            rows = await conn.fetch("""
                SELECT event_data, created_at 
                FROM events 
                WHERE event_type = 'order.placed' 
                AND aggregate_type = 'BrokerOperation'
                ORDER BY created_at DESC 
                LIMIT $1
            """, limit)
            
            orders = []
            for row in rows:
                order_data = row['event_data']
                order_data['created_at'] = row['created_at'].isoformat()
                orders.append(order_data)
            
            return {
                "orders": orders,
                "total_count": len(orders),
                "broker": broker
            }
    except Exception as e:
        logger.error("Error getting order history", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get order history: {str(e)}")

# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Broker-Gateway Service...")
    await broker_service.initialize()
    logger.info("Broker-Gateway Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Broker-Gateway Service...")
    await broker_service.cleanup()
    logger.info("Broker-Gateway Service stopped")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        access_log=True
    )