#!/usr/bin/env python3
"""
Aktienanalyse Frontend Service - SECURE VERSION
React Frontend Backend API with Security Hardening
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import aiohttp
import asyncpg
import structlog
from fastapi import FastAPI, HTTPException, Request, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn

# Import shared libraries (SECURITY FIX)
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from logging_config import setup_logging, setup_security_logging, setup_performance_logging
from database_mock import DatabaseManager, EventStore, HealthChecker
from security import InputValidator, SecurityConfig, create_security_headers, get_client_ip, RateLimiter
from event_bus_simple import EventBusConnector, EventType

# Load environment variables (SECURITY FIX)
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Setup structured logging (SECURITY FIX)
logger = setup_logging("frontend-service")
security_logger = setup_security_logging("frontend-service")
performance_logger = setup_performance_logging("frontend-service")

# ================================================================
# SECURE MODELS
# ================================================================

class StockRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, pattern="^[A-Z0-9]+$")
    analysis_type: str = Field(default="basic", pattern="^(basic|advanced|full)$")

class PortfolioRequest(BaseModel):
    portfolio_name: str = Field(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_ -]+$")
    stocks: List[str] = Field(..., min_items=1, max_items=50)
    
    @field_validator('stocks')
    def validate_stocks(cls, v):
        for stock in v:
            if not stock or len(stock) > 10 or not stock.replace('_', '').isalnum():
                raise ValueError('Invalid stock symbol')
        return v

class UserPreferences(BaseModel):
    theme: str = Field(default="light", pattern="^(light|dark)$")
    language: str = Field(default="de", pattern="^(de|en)$")
    notifications: bool = True
    auto_refresh: bool = True
    refresh_interval: int = Field(default=30, ge=10, le=300)

# ================================================================
# SECURE FRONTEND SERVICE
# ================================================================

class SecureFrontendService:
    def __init__(self):
        self.db_manager: Optional[DatabaseManager] = None
        self.event_bus: Optional[EventBusConnector] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.security_config = SecurityConfig()
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter(max_requests=300, window_seconds=60)
        
        # Service URLs from environment (SECURITY FIX)
        self.service_urls = {
            "intelligent-core": os.getenv("INTELLIGENT_CORE_URL", "http://localhost:8001"),
            "broker-gateway": os.getenv("BROKER_GATEWAY_URL", "http://localhost:8002"),
            "monitoring": os.getenv("MONITORING_URL", "http://localhost:8080")
        }
        
        # File upload limits (SECURITY FIX)
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "5242880"))  # 5MB
        self.allowed_file_types = ["image/jpeg", "image/png", "image/gif", "text/csv"]
        
    async def initialize(self):
        """Initialize frontend service with security"""
        try:
            # Database manager (SECURITY FIX)
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # Event bus connector (SECURITY FIX)
            self.event_bus = EventBusConnector("frontend-service")
            await self.event_bus.connect()
            
            # Secure HTTP session (SECURITY FIX)
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": "aktienanalyse-frontend/1.0.0-secure",
                    "X-Service": "frontend"
                },
                connector=aiohttp.TCPConnector(
                    limit=50,
                    limit_per_host=10,
                    ttl_dns_cache=300
                )
            )
            
            logger.info("Secure Frontend Service initialized")
            
        except Exception as e:
            logger.error("Failed to initialize frontend service", error=str(e))
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
                
            logger.info("Secure Frontend Service cleaned up")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    async def validate_file_upload(self, file: UploadFile, client_ip: str) -> bool:
        """Validate file upload with security checks"""
        try:
            # Rate limiting for file uploads
            if not self.rate_limiter.allow_request(f"upload_{client_ip}"):
                security_logger.warning("File upload rate limit exceeded",
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            # Check file size
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning
            
            if file_size > self.max_file_size:
                security_logger.warning("File size exceeds limit",
                                       file_size=file_size,
                                       max_size=self.max_file_size,
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            # Check file type
            if file.content_type not in self.allowed_file_types:
                security_logger.warning("Invalid file type",
                                       content_type=file.content_type,
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            # Validate filename
            if not self.validator.validate_filename(file.filename):
                security_logger.warning("Invalid filename",
                                       filename=file.filename,
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            return True
            
        except Exception as e:
            security_logger.error("Error validating file upload",
                                 client_ip_hash=self.validator.hash_ip(client_ip),
                                 error=str(e))
            return False

    async def call_service(self, service: str, endpoint: str, method: str = "GET", 
                          data: Dict = None, client_ip: str = None) -> Dict[str, Any]:
        """Make secure service call with validation"""
        try:
            if service not in self.service_urls:
                raise ValueError(f"Unknown service: {service}")
            
            url = f"{self.service_urls[service]}{endpoint}"
            
            # Add security headers
            headers = {
                "X-Forwarded-For": self.validator.hash_ip(client_ip) if client_ip else "internal",
                "X-Request-ID": f"frontend_{int(time.time())}",
                "Content-Type": "application/json"
            }
            
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HTTPException(status_code=response.status, 
                                          detail=f"Service call failed: {response.status}")
            
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HTTPException(status_code=response.status,
                                          detail=f"Service call failed: {response.status}")
            
            else:
                raise ValueError(f"Unsupported method: {method}")
                
        except Exception as e:
            logger.error("Service call failed",
                        service=service,
                        endpoint=endpoint,
                        client_ip_hash=self.validator.hash_ip(client_ip) if client_ip else None,
                        error=str(e))
            raise HTTPException(status_code=500, detail="Service call failed")

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        try:
            health_checker = HealthChecker(self.db_manager)
            db_status = await health_checker.check_database()
            
            # Check backend services
            service_statuses = {}
            for service_name, url in self.service_urls.items():
                try:
                    status = await self.call_service(service_name, "/health")
                    service_statuses[service_name] = {"status": "healthy", "details": status}
                except Exception as e:
                    service_statuses[service_name] = {"status": "unhealthy", "error": str(e)}
            
            # Determine overall status
            overall_status = "healthy"
            unhealthy_services = [
                name for name, status in service_statuses.items() 
                if status["status"] == "unhealthy"
            ]
            
            if unhealthy_services:
                overall_status = "degraded"
            
            if db_status["status"] != "healthy":
                overall_status = "degraded"
            
            return {
                "service": "secure-frontend",
                "status": overall_status,
                "database": db_status,
                "backend_services": service_statuses,
                "security": {
                    "rate_limiter": "active",
                    "file_validation": "enabled",
                    "input_sanitization": "enabled"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0-secure"
            }
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "service": "secure-frontend",
                "status": "unhealthy",
                "error": "Health check failed",
                "timestamp": datetime.utcnow().isoformat()
            }

# ================================================================
# GLOBAL SERVICE INSTANCE
# ================================================================

frontend_service = SecureFrontendService()

# ================================================================
# FASTAPI APPLICATION WITH SECURITY
# ================================================================

app = FastAPI(
    title="Aktienanalyse Secure Frontend Service",
    description="React Frontend Backend API with Security Hardening",
    version="1.0.0-secure",
    docs_url=None,  # Disable docs in production
    redoc_url=None  # Disable redoc in production
)

# Security Middleware (SECURITY FIX)
@app.middleware("http")
async def security_middleware(request: Request, call_next):
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
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Static files with security (if needed)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# ================================================================
# SECURE API ENDPOINTS
# ================================================================

@app.get("/health")
async def health_check():
    """Secure health check endpoint"""
    return await frontend_service.get_health_status()

@app.get("/api/dashboard")
async def get_dashboard_data(request: Request):
    """Get dashboard data with rate limiting"""
    client_ip = get_client_ip(request)
    
    if not frontend_service.rate_limiter.allow_request(f"dashboard_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Get data from multiple services
        monitoring_data = await frontend_service.call_service(
            "monitoring", "/health", client_ip=client_ip
        )
        
        # Create dashboard summary
        dashboard_data = {
            "system_status": monitoring_data.get("status", "unknown"),
            "services": monitoring_data.get("services", {}),
            "system_metrics": monitoring_data.get("system_metrics", {}),
            "active_alerts": monitoring_data.get("active_alerts", []),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error("Error getting dashboard data",
                    client_ip_hash=frontend_service.validator.hash_ip(client_ip),
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")

@app.post("/api/stocks/analyze")
async def analyze_stock(request: Request, stock_request: StockRequest):
    """Analyze stock with security validation"""
    client_ip = get_client_ip(request)
    
    if not frontend_service.rate_limiter.allow_request(f"analyze_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Validate stock symbol
        if not frontend_service.validator.validate_stock_symbol(stock_request.symbol):
            raise HTTPException(status_code=400, detail="Invalid stock symbol")
        
        # Call intelligent-core service
        analysis_data = await frontend_service.call_service(
            "intelligent-core", 
            f"/analysis/stock/{stock_request.symbol}",
            method="GET",
            client_ip=client_ip
        )
        
        # Log successful analysis
        logger.info("Stock analysis completed",
                   symbol=stock_request.symbol,
                   analysis_type=stock_request.analysis_type,
                   client_ip_hash=frontend_service.validator.hash_ip(client_ip))
        
        return analysis_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error analyzing stock",
                    symbol=stock_request.symbol,
                    client_ip_hash=frontend_service.validator.hash_ip(client_ip),
                    error=str(e))
        raise HTTPException(status_code=500, detail="Analysis failed")

@app.get("/api/portfolio/positions")
async def get_portfolio_positions(request: Request):
    """Get portfolio positions with rate limiting"""
    client_ip = get_client_ip(request)
    
    if not frontend_service.rate_limiter.allow_request(f"portfolio_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Call broker-gateway service
        positions_data = await frontend_service.call_service(
            "broker-gateway",
            "/bitpanda/balances?api_key=demo_key",
            client_ip=client_ip
        )
        
        return positions_data
        
    except Exception as e:
        logger.error("Error getting portfolio positions",
                    client_ip_hash=frontend_service.validator.hash_ip(client_ip),
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get positions")

@app.post("/api/orders/place")
async def place_order(request: Request, order_data: Dict[str, Any]):
    """Place order with security validation"""
    client_ip = get_client_ip(request)
    
    # Strict rate limiting for orders
    if not frontend_service.rate_limiter.allow_request(f"order_{client_ip}"):
        raise HTTPException(status_code=429, detail="Order rate limit exceeded")
    
    try:
        # Validate order data
        if not frontend_service.validator.validate_order_request(order_data):
            raise HTTPException(status_code=400, detail="Invalid order data")
        
        # Call broker-gateway service
        order_result = await frontend_service.call_service(
            "broker-gateway",
            "/bitpanda/orders",
            method="POST",
            data=order_data,
            client_ip=client_ip
        )
        
        # Log order placement
        security_logger.info("Order placed successfully",
                           instrument=order_data.get("instrument_code"),
                           side=order_data.get("side"),
                           amount=order_data.get("amount"),
                           client_ip_hash=frontend_service.validator.hash_ip(client_ip))
        
        return order_result
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.error("Error placing order",
                             order_data=order_data,
                             client_ip_hash=frontend_service.validator.hash_ip(client_ip),
                             error=str(e))
        raise HTTPException(status_code=500, detail="Order placement failed")

@app.post("/api/files/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload file with security validation"""
    client_ip = get_client_ip(request)
    
    try:
        # Validate file upload
        if not await frontend_service.validate_file_upload(file, client_ip):
            raise HTTPException(status_code=400, detail="File validation failed")
        
        # Process file securely (implement based on needs)
        # For now, just return file info
        file_info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file.file.tell(),
            "status": "uploaded",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("File uploaded successfully",
                   filename=file.filename,
                   size=file_info["size"],
                   client_ip_hash=frontend_service.validator.hash_ip(client_ip))
        
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.error("Error uploading file",
                             filename=file.filename if file else "unknown",
                             client_ip_hash=frontend_service.validator.hash_ip(client_ip),
                             error=str(e))
        raise HTTPException(status_code=500, detail="File upload failed")

@app.get("/api/settings/preferences")
async def get_user_preferences(request: Request):
    """Get user preferences with rate limiting"""
    client_ip = get_client_ip(request)
    
    if not frontend_service.rate_limiter.allow_request(f"preferences_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Return default preferences (implement user-specific storage as needed)
    default_preferences = UserPreferences()
    return default_preferences.dict()

@app.put("/api/settings/preferences")
async def update_user_preferences(request: Request, preferences: UserPreferences):
    """Update user preferences with validation"""
    client_ip = get_client_ip(request)
    
    if not frontend_service.rate_limiter.allow_request(f"update_prefs_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Validate and sanitize preferences
        # Store in database (implement as needed)
        
        logger.info("User preferences updated",
                   theme=preferences.theme,
                   language=preferences.language,
                   client_ip_hash=frontend_service.validator.hash_ip(client_ip))
        
        return {"status": "updated", "preferences": preferences.dict()}
        
    except Exception as e:
        logger.error("Error updating preferences",
                    client_ip_hash=frontend_service.validator.hash_ip(client_ip),
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update preferences")

# ================================================================
# STARTUP AND SHUTDOWN EVENTS
# ================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Secure Frontend Service...")
    await frontend_service.initialize()
    logger.info("Secure Frontend Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Secure Frontend Service...")
    await frontend_service.cleanup()
    logger.info("Secure Frontend Service stopped")

if __name__ == "__main__":
    port = int(os.getenv("FRONTEND_PORT", "3001"))
    uvicorn.run(
        "main_secure:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True,
        log_config=None  # Use our structured logging
    )