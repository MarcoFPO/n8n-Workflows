"""
Security utilities for Aktienanalyse-Ökosystem
Provides input validation, sanitization, and security helpers
"""

import re
import html
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator
from fastapi import HTTPException
import bleach


class SecurityConfig(BaseModel):
    """Security configuration"""
    max_string_length: int = 1000
    allowed_symbols_pattern: str = r'^[A-Z]{1,5}$'
    allowed_domains: List[str] = ['10.1.1.174', 'aktienanalyse.local']
    rate_limit_per_minute: int = 100


class InputValidator:
    """Input validation and sanitization"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        
    def validate_stock_symbol(self, symbol: str) -> str:
        """Validate and sanitize stock symbol"""
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol cannot be empty")
            
        # Remove whitespace and convert to uppercase
        symbol = symbol.strip().upper()
        
        # Check pattern
        if not re.match(self.config.allowed_symbols_pattern, symbol):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid symbol format. Must match pattern: {self.config.allowed_symbols_pattern}"
            )
            
        return symbol
    
    def sanitize_string(self, value: str, max_length: int = None) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail="Value must be string")
            
        max_len = max_length or self.config.max_string_length
        
        # Truncate if too long
        if len(value) > max_len:
            value = value[:max_len]
            
        # HTML escape
        value = html.escape(value)
        
        # Remove potentially dangerous characters
        value = bleach.clean(value, tags=[], strip=True)
        
        return value.strip()
    
    def validate_numeric(self, value: Union[int, float], min_val: float = None, max_val: float = None) -> Union[int, float]:
        """Validate numeric input"""
        if not isinstance(value, (int, float)):
            raise HTTPException(status_code=400, detail="Value must be numeric")
            
        if min_val is not None and value < min_val:
            raise HTTPException(status_code=400, detail=f"Value must be >= {min_val}")
            
        if max_val is not None and value > max_val:
            raise HTTPException(status_code=400, detail=f"Value must be <= {max_val}")
            
        return value
    
    def validate_origin(self, origin: str) -> bool:
        """Validate CORS origin"""
        if not origin:
            return False
            
        # Extract domain from origin
        domain = origin.replace('https://', '').replace('http://', '').split(':')[0]
        
        return domain in self.config.allowed_domains


class ParameterizedQuery:
    """Safe database query builder"""
    
    @staticmethod
    def build_insert_events_query() -> str:
        """Build parameterized INSERT query for events table"""
        return """
        INSERT INTO events (stream_id, event_type, event_version, aggregate_id, 
                           aggregate_type, event_data, metadata, created_at) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """
    
    @staticmethod
    def build_select_events_query() -> str:
        """Build parameterized SELECT query for events"""
        return """
        SELECT stream_id, event_type, event_version, aggregate_id, 
               aggregate_type, event_data, metadata, created_at
        FROM events 
        WHERE aggregate_id = $1 
        AND event_type = $2
        ORDER BY created_at DESC 
        LIMIT $3
        """
    
    @staticmethod
    def build_update_analysis_query() -> str:
        """Build parameterized UPDATE query for analysis results"""
        return """
        UPDATE stock_analysis 
        SET score = $1, recommendation = $2, confidence = $3, updated_at = NOW()
        WHERE symbol = $4
        """


class TokenGenerator:
    """Secure token generation"""
    
    @staticmethod
    def generate_api_token(length: int = 32) -> str:
        """Generate secure API token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_session_id(length: int = 32) -> str:
        """Generate secure session ID"""
        return secrets.token_hex(length)
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
            
        # Use SHA-256 with salt
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    def validate_service_name(self, service_name: str) -> bool:
        """Validate service name"""
        if not service_name or len(service_name) > 50:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', service_name))
    
    def validate_trading_pair(self, pair: str) -> bool:
        """Validate trading pair"""
        if not pair or len(pair) > 20:
            return False
        return bool(re.match(r'^[A-Z_]+$', pair))
    
    def validate_filename(self, filename: str) -> bool:
        """Validate filename for security"""
        if not filename or len(filename) > 255:
            return False
        # Check for dangerous patterns
        dangerous_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        return not any(pattern in filename for pattern in dangerous_patterns)
    
    def validate_websocket_message(self, message: dict) -> bool:
        """Validate WebSocket message"""
        if not isinstance(message, dict):
            return False
        # Basic validation - can be extended
        import json
        return len(json.dumps(message)) < 1000  # 1KB limit
    
    def generate_secure_id(self, length: int = 16) -> str:
        """Generate secure random ID"""
        return secrets.token_hex(length)


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {client_id: [timestamp, ...]}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        import time
        
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id] 
                if req_time > window_start
            ]
        else:
            self.requests[client_id] = []
        
        # Check limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True


# Pydantic models for request validation
class StockAnalysisRequest(BaseModel):
    """Validated stock analysis request"""
    symbol: str
    timeframe: str = "1D"
    period: str = "1D"  # Alias for timeframe for backwards compatibility
    indicators: List[str] = ["RSI", "MACD", "SMA"]
    
    @validator('symbol')
    def validate_symbol(cls, v):
        validator = InputValidator()
        return validator.validate_stock_symbol(v)
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        allowed_timeframes = ["1D", "1W", "1M", "3M", "6M", "1Y"]
        if v not in allowed_timeframes:
            raise ValueError(f"Timeframe must be one of: {allowed_timeframes}")
        return v
    
    @validator('period')
    def validate_and_sync_period(cls, v, values):
        # Sync period with timeframe for backwards compatibility
        timeframe = values.get('timeframe', '1D')
        return timeframe


class OrderRequest(BaseModel):
    """Validated trading order request"""
    symbol: str
    side: str  # "BUY" or "SELL"
    order_type: str  # "MARKET", "LIMIT", "STOP"
    quantity: float
    price: Optional[float] = None
    
    @validator('symbol')
    def validate_symbol(cls, v):
        validator = InputValidator()
        return validator.validate_stock_symbol(v)
    
    @validator('side')
    def validate_side(cls, v):
        if v.upper() not in ["BUY", "SELL"]:
            raise ValueError("Side must be BUY or SELL")
        return v.upper()
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


# Security middleware helpers
def create_security_headers() -> Dict[str, str]:
    """Create security headers for HTTP responses"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    }


def get_client_ip(request) -> str:
    """Extract client IP from request"""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client
    return request.client.host if request.client else "unknown"


# Additional validation methods for InputValidator
def validate_service_name(service_name: str) -> bool:
    """Validate service name"""
    if not service_name or len(service_name) > 50:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', service_name))

def validate_trading_pair(pair: str) -> bool:
    """Validate trading pair"""
    if not pair or len(pair) > 20:
        return False
    return bool(re.match(r'^[A-Z_]+$', pair))

def validate_filename(filename: str) -> bool:
    """Validate filename for security"""
    if not filename or len(filename) > 255:
        return False
    # Check for dangerous patterns
    dangerous_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    return not any(pattern in filename for pattern in dangerous_patterns)

def validate_websocket_message(message: dict) -> bool:
    """Validate WebSocket message"""
    if not isinstance(message, dict):
        return False
    # Basic validation - can be extended
    import json
    return len(json.dumps(message)) < 1000  # 1KB limit