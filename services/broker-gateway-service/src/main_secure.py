#!/usr/bin/env python3
"""
Aktienanalyse Broker-Gateway Service - SECURE VERSION
Unified API Gateway for Bitpanda Pro and other brokers with Security Hardening
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
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# Import shared libraries (SECURITY FIX)
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from logging_config import setup_logging, setup_security_logging, setup_performance_logging
from database_mock import DatabaseManager, EventStore, HealthChecker
from security import InputValidator, SecurityConfig, create_security_headers, get_client_ip, RateLimiter, ParameterizedQuery
from event_bus_simple import EventBusConnector, create_order_event, EventType

# Load environment variables (SECURITY FIX)
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Setup structured logging (SECURITY FIX)
logger = setup_logging("broker-gateway-service")
security_logger = setup_security_logging("broker-gateway-service")
performance_logger = setup_performance_logging("broker-gateway-service")

# Pydantic Models with Validation (SECURITY FIX)
class BitpandaCredentials(BaseModel):
    api_key: str = Field(..., min_length=10, max_length=200, description="API Key for Bitpanda Pro")
    api_secret: str = Field(..., min_length=10, max_length=200, description="API Secret for Bitpanda Pro")
    environment: str = Field(default="sandbox", pattern="^(sandbox|production)$", description="sandbox or production")

class OrderRequest(BaseModel):
    instrument_code: str = Field(..., min_length=3, max_length=20, pattern="^[A-Z_]+$", description="Trading pair e.g. BTC_EUR")
    side: str = Field(..., pattern="^(BUY|SELL)$", description="BUY or SELL")
    type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$", description="MARKET or LIMIT")
    amount: str = Field(..., pattern="^[0-9]+\.?[0-9]*$", description="Amount to trade")
    price: Optional[str] = Field(None, pattern="^[0-9]+\.?[0-9]*$", description="Price for LIMIT orders")
    client_id: Optional[str] = Field(None, max_length=50, description="Client order ID")

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
    currency_code: str = Field(..., pattern="^[A-Z]{3,5}$")
    available: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")
    locked: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")
    total: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")

class MarketData(BaseModel):
    instrument_code: str = Field(..., pattern="^[A-Z_]+$")
    last_price: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")
    best_bid: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")
    best_ask: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")
    price_change: str = Field(..., pattern="^[+-]?[0-9]+\.?[0-9]*$")
    price_change_percentage: str = Field(..., pattern="^[+-]?[0-9]+\.?[0-9]*$")
    high_24h: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")
    low_24h: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")
    volume_24h: str = Field(..., pattern="^[0-9]+\.?[0-9]*$")
    timestamp: datetime

# Secure Broker Gateway Service
class SecureBrokerGatewayService:
    def __init__(self):
        self.db_manager: Optional[DatabaseManager] = None
        self.event_bus: Optional[EventBusConnector] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.security_config = SecurityConfig()
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
        
        # Environment variables (SECURITY FIX)
        self.event_bus_url = os.getenv("EVENT_BUS_URL", "http://localhost:8081")
        self.bitpanda_api_base = {
            "sandbox": os.getenv("BITPANDA_SANDBOX_URL", "https://api.exchange.bitpanda.com"),
            "production": os.getenv("BITPANDA_PRODUCTION_URL", "https://api.exchange.bitpanda.com")
        }
        
    async def initialize(self):
        """Initialize database connection and HTTP session"""
        try:
            # Database manager with secure config (SECURITY FIX)
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # Event bus connector (SECURITY FIX)
            self.event_bus = EventBusConnector("broker-gateway-service")
            await self.event_bus.connect()
            
            # Secure HTTP session (SECURITY FIX)
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": "aktienanalyse-broker-gateway/1.0.0",
                    "X-Service": "broker-gateway"
                },
                connector=aiohttp.TCPConnector(
                    limit=10,
                    limit_per_host=5,
                    ttl_dns_cache=300,
                    use_dns_cache=True
                )
            )
            
            logger.info("Secure Broker-Gateway Service initialized", 
                       database="connected", 
                       event_bus="connected",
                       session="ready")
            
        except Exception as e:
            logger.error("Failed to initialize Secure Broker-Gateway Service", error=str(e))
            raise

    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session:
                await self.session.close()
            if self.event_bus:
                await self.event_bus.disconnect()
            if self.db_manager:
                await self.db_manager.close()
                
            logger.info("Secure Broker-Gateway Service cleaned up")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    async def validate_credentials(self, credentials: BitpandaCredentials, client_ip: str) -> bool:
        """Validate API credentials securely (SECURITY FIX)"""
        try:
            # Rate limiting check
            if not self.rate_limiter.allow_request(client_ip):
                security_logger.warning("Rate limit exceeded for credentials validation", 
                                       client_ip=client_ip)
                return False
            
            # Input validation
            if not self.validator.validate_api_key(credentials.api_key):
                security_logger.warning("Invalid API key format", client_ip=client_ip)
                return False
                
            if not self.validator.validate_api_secret(credentials.api_secret):
                security_logger.warning("Invalid API secret format", client_ip=client_ip)
                return False
            
            # Log successful validation
            security_logger.info("Credentials validated", 
                               client_ip=client_ip,
                               environment=credentials.environment)
            return True
            
        except Exception as e:
            security_logger.error("Error validating credentials", 
                                 client_ip=client_ip, 
                                 error=str(e))
            return False

    async def get_bitpanda_headers(self, credentials: BitpandaCredentials) -> Dict[str, str]:
        """Generate Bitpanda API headers with authentication (SECURITY FIX)"""
        # Sanitize credentials before using
        clean_api_key = self.validator.sanitize_input(credentials.api_key)
        
        return {
            "Authorization": f"Bearer {clean_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-ID": f"broker_{int(time.time())}",
            "X-API-Version": "v1"
        }

    async def get_account_balances(self, credentials: BitpandaCredentials, client_ip: str) -> List[AccountBalance]:
        """Get account balances from Bitpanda Pro (SECURITY FIX)"""
        try:
            # Validate credentials first
            if not await self.validate_credentials(credentials, client_ip):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # For demo purposes, return secure mock data
            # In production, integrate with real Bitpanda API using secure headers
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
            
            # Publish secure event (SECURITY FIX)
            event = {
                "event_type": "account.balances.retrieved",
                "source": "broker-gateway-service",
                "data": {
                    "balances_count": len(mock_balances),
                    "currencies": [b.currency_code for b in mock_balances],
                    "client_ip_hash": self.validator.hash_ip(client_ip)
                }
            }
            await self.event_bus.publish(event)
            
            # Store in event store (SECURITY FIX)
            query = ParameterizedQuery(
                "INSERT INTO events (event_type, aggregate_id, aggregate_type, event_data, created_at) VALUES ($1, $2, $3, $4, $5)",
                ["account.balances.retrieved", "bitpanda_account", "BrokerOperation", json.dumps(event["data"]), datetime.utcnow()]
            )
            await self.db_manager.execute_query(query)
            
            logger.info("Account balances retrieved", 
                       balances_count=len(mock_balances),
                       client_ip_hash=self.validator.hash_ip(client_ip))
            
            return mock_balances
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting account balances", client_ip_hash=self.validator.hash_ip(client_ip), error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get balances")

    async def get_market_data(self, instrument_code: str, client_ip: str) -> MarketData:
        """Get market data for trading pair (SECURITY FIX)"""
        try:
            # Validate instrument code
            if not self.validator.validate_trading_pair(instrument_code):
                raise HTTPException(status_code=400, detail="Invalid instrument code")
            
            # Rate limiting
            if not self.rate_limiter.allow_request(client_ip):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Clean input
            clean_instrument = self.validator.sanitize_input(instrument_code)
            
            # For demo purposes, return secure mock data
            mock_data = MarketData(
                instrument_code=clean_instrument,
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
            
            # Publish secure event
            event = {
                "event_type": "market.data.retrieved",
                "source": "broker-gateway-service", 
                "data": {
                    "instrument": clean_instrument,
                    "price": mock_data.last_price,
                    "volume": mock_data.volume_24h,
                    "client_ip_hash": self.validator.hash_ip(client_ip)
                }
            }
            await self.event_bus.publish(event)
            
            logger.info("Market data retrieved", 
                       instrument=clean_instrument,
                       client_ip_hash=self.validator.hash_ip(client_ip))
            
            return mock_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting market data", 
                        instrument=instrument_code,
                        client_ip_hash=self.validator.hash_ip(client_ip),
                        error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get market data")

    async def place_order(self, order_request: OrderRequest, credentials: BitpandaCredentials, client_ip: str) -> OrderResponse:
        """Place order via Bitpanda Pro API (SECURITY FIX)"""
        try:
            # Validate credentials and order
            if not await self.validate_credentials(credentials, client_ip):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            if not self.validator.validate_order_request(order_request.dict()):
                raise HTTPException(status_code=400, detail="Invalid order request")
            
            # Rate limiting for orders
            if not self.rate_limiter.allow_request(f"order_{client_ip}"):
                raise HTTPException(status_code=429, detail="Order rate limit exceeded")
            
            # For demo purposes, return secure mock response
            # In production, use real Bitpanda API with secure validation
            order_id = f"order_{int(time.time())}_{self.validator.generate_secure_id()}"
            
            mock_response = OrderResponse(
                order_id=order_id,
                status="FILLED",
                instrument_code=order_request.instrument_code,
                side=order_request.side,
                type=order_request.type,
                amount=order_request.amount,
                price=order_request.price,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Create secure order event
            event = create_order_event(
                symbol=order_request.instrument_code,
                action=order_request.side,
                quantity=int(float(order_request.amount) * 100),  # Convert to satoshis/cents
                price=float(order_request.price) if order_request.price else 0.0,
                source="broker-gateway-service"
            )
            event["data"]["client_ip_hash"] = self.validator.hash_ip(client_ip)
            event["data"]["order_id"] = order_id
            
            await self.event_bus.publish(event)
            
            # Store in event store with parameterized query
            query = ParameterizedQuery(
                "INSERT INTO events (event_type, aggregate_id, aggregate_type, event_data, created_at) VALUES ($1, $2, $3, $4, $5)",
                ["order.placed", order_id, "BrokerOperation", json.dumps(event["data"]), datetime.utcnow()]
            )
            await self.db_manager.execute_query(query)
            
            security_logger.info("Order placed successfully",
                                order_id=order_id,
                                instrument=order_request.instrument_code,
                                side=order_request.side,
                                client_ip_hash=self.validator.hash_ip(client_ip))
            
            return mock_response
            
        except HTTPException:
            raise
        except Exception as e:
            security_logger.error("Error placing order", 
                                 order=order_request.dict(),
                                 client_ip_hash=self.validator.hash_ip(client_ip),
                                 error=str(e))
            raise HTTPException(status_code=500, detail="Failed to place order")

    async def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status (SECURITY FIX)"""
        try:
            health_checker = HealthChecker(self.db_manager)
            db_status = await health_checker.check_database()
            
            return {
                "service": "secure-broker-gateway",
                "status": "healthy" if db_status["status"] == "healthy" else "degraded",
                "database": db_status,
                "event_bus": {
                    "status": "connected" if self.event_bus and self.event_bus.connected else "disconnected"
                },
                "session": {
                    "status": "ready" if self.session and not self.session.closed else "not_ready"
                },
                "security": {
                    "rate_limiter": "active",
                    "input_validation": "enabled",
                    "logging": "structured"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0-secure"
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "service": "secure-broker-gateway",
                "status": "unhealthy",
                "error": "Health check failed",
                "timestamp": datetime.utcnow().isoformat()
            }

# Global service instance
broker_service = SecureBrokerGatewayService()

# FastAPI Application with Security Configuration
app = FastAPI(
    title="Aktienanalyse Secure Broker-Gateway Service",
    description="Unified API Gateway for Bitpanda Pro and other brokers with Security Hardening",
    version="1.0.0-secure",
    docs_url=None,  # Disable docs in production
    redoc_url=None  # Disable redoc in production
)

# Security Middleware (SECURITY FIX)
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Add security headers
    response = await call_next(request)
    security_headers = create_security_headers()
    for header, value in security_headers.items():
        response.headers[header] = value
    return response

# CORS Middleware with Hardened Configuration (SECURITY FIX)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://aktienanalyse.local").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # No wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only required methods
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Secure health check endpoint"""
    return await broker_service.get_health_status()

# Secure Bitpanda Pro Endpoints
@app.get("/bitpanda/balances", response_model=List[AccountBalance])
async def get_bitpanda_balances(
    request: Request,
    api_key: str = Field(..., min_length=10, max_length=200),
    environment: str = Field(default="sandbox", pattern="^(sandbox|production)$")
):
    """Get account balances from Bitpanda Pro with security validation"""
    client_ip = get_client_ip(request)
    
    credentials = BitpandaCredentials(
        api_key=api_key,
        api_secret=os.getenv("BITPANDA_API_SECRET", "dummy_secret_for_demo"),
        environment=environment
    )
    return await broker_service.get_account_balances(credentials, client_ip)

@app.get("/bitpanda/market/{instrument_code}", response_model=MarketData)
async def get_bitpanda_market_data(request: Request, instrument_code: str):
    """Get market data for trading pair with security validation"""
    client_ip = get_client_ip(request)
    return await broker_service.get_market_data(instrument_code, client_ip)

@app.post("/bitpanda/orders", response_model=OrderResponse)
async def place_bitpanda_order(
    request: Request,
    order_request: OrderRequest,
    api_key: str = Field(..., min_length=10, max_length=200),
    environment: str = Field(default="sandbox", pattern="^(sandbox|production)$")
):
    """Place order via Bitpanda Pro with security validation"""
    client_ip = get_client_ip(request)
    
    credentials = BitpandaCredentials(
        api_key=api_key,
        api_secret=os.getenv("BITPANDA_API_SECRET", "dummy_secret_for_demo"),
        environment=environment
    )
    return await broker_service.place_order(order_request, credentials, client_ip)

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
                "environments": ["sandbox", "production"],
                "security_features": ["rate_limiting", "input_validation", "secure_logging"]
            }
        ],
        "total_count": 1,
        "security_version": "1.0.0-secure"
    }

@app.get("/orders/history")
async def get_order_history(
    request: Request,
    broker: str = Field(default="bitpanda", pattern="^[a-z_]+$"),
    limit: int = Field(default=50, ge=1, le=100)
):
    """Get order history from database with security validation"""
    client_ip = get_client_ip(request)
    
    try:
        # Rate limiting
        if not broker_service.rate_limiter.allow_request(f"history_{client_ip}"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Parameterized query for security
        query = ParameterizedQuery(
            """SELECT event_data, created_at 
               FROM events 
               WHERE event_type = $1 
               AND aggregate_type = $2
               ORDER BY created_at DESC 
               LIMIT $3""",
            ["order.placed", "BrokerOperation", limit]
        )
        
        rows = await broker_service.db_manager.fetch_all(query)
        
        orders = []
        for row in rows:
            order_data = row['event_data']
            if isinstance(order_data, str):
                order_data = json.loads(order_data)
            order_data['created_at'] = row['created_at'].isoformat()
            # Remove sensitive data
            order_data.pop('client_ip_hash', None)
            orders.append(order_data)
        
        logger.info("Order history retrieved", 
                   count=len(orders),
                   client_ip_hash=broker_service.validator.hash_ip(client_ip))
        
        return {
            "orders": orders,
            "total_count": len(orders),
            "broker": broker,
            "security_filtered": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting order history", 
                    client_ip_hash=broker_service.validator.hash_ip(client_ip),
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get order history")

# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Secure Broker-Gateway Service...")
    await broker_service.initialize()
    logger.info("Secure Broker-Gateway Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Secure Broker-Gateway Service...")
    await broker_service.cleanup()
    logger.info("Secure Broker-Gateway Service stopped")

if __name__ == "__main__":
    port = int(os.getenv("BROKER_GATEWAY_PORT", "8002"))
    uvicorn.run(
        "main_secure:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True,
        log_config=None  # Use our structured logging
    )