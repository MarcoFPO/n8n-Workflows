#!/usr/bin/env python3
"""
MarketCap Service - Presentation Models
Clean Architecture Presentation Layer DTOs

CLEAN ARCHITECTURE - PRESENTATION LAYER:
- Request/Response data transfer objects
- Input validation and serialization
- Presentation layer contracts

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class MarketDataRequest(BaseModel):
    """
    Market Data Request DTO
    
    PRESENTATION MODEL: Input validation for market data requests
    """
    
    symbol: str = Field(..., description="Stock symbol to retrieve", min_length=1, max_length=10)
    use_cache: bool = Field(True, description="Whether to use cached data")
    source: str = Field("marketcap_service", description="Data source identifier")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.upper().strip()
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "use_cache": True,
                "source": "marketcap_service"
            }
        }


class MarketDataResponse(BaseModel):
    """
    Market Data Response DTO
    
    PRESENTATION MODEL: Output format for market data
    """
    
    success: bool = Field(..., description="Request success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Market data payload")
    source: Optional[str] = Field(None, description="Data source used")
    request_info: Optional[Dict[str, Any]] = Field(None, description="Request metadata")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    timestamp: str = Field(..., description="Response timestamp")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "symbol": "AAPL",
                    "company_name": "Apple Inc.",
                    "market_cap": "2800000000000",
                    "stock_price": "175.50",
                    "daily_change_percent": "2.35",
                    "timestamp": "2025-08-25T10:30:00",
                    "cap_classification": "Large Cap",
                    "is_positive_performance": True,
                    "source": "mock_provider_v6.0.0"
                },
                "source": "cache",
                "timestamp": "2025-08-25T10:30:15"
            }
        }


class AllMarketDataRequest(BaseModel):
    """
    All Market Data Request DTO
    
    PRESENTATION MODEL: Input for retrieving all market data
    """
    
    cap_classification: Optional[str] = Field(None, description="Filter by cap size")
    fresh_only: bool = Field(True, description="Only return fresh data")
    
    @validator('cap_classification')
    def validate_cap_classification(cls, v):
        if v is not None:
            valid_caps = ["Large Cap", "Mid Cap", "Small Cap"]
            if v not in valid_caps:
                raise ValueError(f"cap_classification must be one of: {valid_caps}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "cap_classification": "Large Cap",
                "fresh_only": True
            }
        }


class AllMarketDataResponse(BaseModel):
    """
    All Market Data Response DTO
    
    PRESENTATION MODEL: Output format for all market data
    """
    
    success: bool = Field(..., description="Request success status")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="List of market data records")
    count: int = Field(0, description="Number of records returned")
    filter: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    timestamp: str = Field(..., description="Response timestamp")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "symbol": "AAPL",
                        "company_name": "Apple Inc.",
                        "market_cap": "2800000000000",
                        "stock_price": "175.50",
                        "daily_change_percent": "2.35"
                    }
                ],
                "count": 1,
                "filter": {
                    "cap_classification": "Large Cap",
                    "fresh_only": True
                },
                "timestamp": "2025-08-25T10:30:15"
            }
        }


class SymbolsResponse(BaseModel):
    """
    Available Symbols Response DTO
    
    PRESENTATION MODEL: Output format for available symbols
    """
    
    success: bool = Field(..., description="Request success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Symbols data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "symbols": ["AAPL", "GOOGL", "MSFT"],
                    "count": 3
                }
            }
        }


class CapDistributionResponse(BaseModel):
    """
    Cap Distribution Response DTO
    
    PRESENTATION MODEL: Output format for market cap distribution
    """
    
    success: bool = Field(..., description="Request success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Distribution data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "distribution": {
                        "Large Cap": 10,
                        "Mid Cap": 5,
                        "Small Cap": 5
                    },
                    "total_symbols": 20,
                    "positive_performance_count": 12,
                    "positive_performance_percentage": 60.0,
                    "total_market_cap": 15000000000000,
                    "average_market_cap": 750000000000
                }
            }
        }


class HealthResponse(BaseModel):
    """
    Health Check Response DTO
    
    PRESENTATION MODEL: Output format for health checks
    """
    
    success: bool = Field(..., description="Health check success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Health data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "controller": "MarketCapController",
                    "status": "healthy",
                    "version": "6.0.0",
                    "capabilities": [
                        "get_market_data",
                        "get_all_market_data",
                        "get_symbols",
                        "get_cap_distribution",
                        "health_check"
                    ]
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Error Response DTO
    
    PRESENTATION MODEL: Standardized error format
    """
    
    success: bool = Field(False, description="Always False for errors")
    error: Dict[str, Any] = Field(..., description="Error details")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "message": "Symbol not found",
                    "code": "DATA_NOT_FOUND",
                    "timestamp": "2025-08-25T10:30:15"
                }
            }
        }