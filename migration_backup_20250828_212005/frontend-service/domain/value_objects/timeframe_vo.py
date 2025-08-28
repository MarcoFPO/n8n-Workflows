#!/usr/bin/env python3
"""
Timeframe Value Objects - Domain Layer  
Frontend Service Clean Architecture v1.0.0

DOMAIN LAYER - VALUE OBJECTS:
- Timeframe Specifications
- Navigation Period Logic
- Business Rules für Zeitraum-Berechnungen

CLEAN ARCHITECTURE PRINCIPLES:
- Immutable Value Objects
- No Side Effects
- Pure Business Logic

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025  
Version: 1.0.0
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum


class TimeframeType(Enum):
    """Timeframe Type Enumeration"""
    WEEK = "1W"
    MONTH = "1M" 
    QUARTER = "3M"
    HALF_YEAR = "6M"
    YEAR = "12M"
    

class NavigationDirection(Enum):
    """Navigation Direction Enumeration"""
    PREVIOUS = "previous"
    NEXT = "next"
    CURRENT = "current"


@dataclass(frozen=True)
class TimeframeMeta:
    """Timeframe Metadata Value Object"""
    code: str
    display_name: str
    description: str
    days: int
    icon: str
    css_class: str
    
    @property
    def timedelta(self) -> timedelta:
        """Get timedelta for this timeframe"""
        return timedelta(days=self.days)
    
    def is_valid_code(self) -> bool:
        """Validate timeframe code"""
        return self.code in ["1W", "1M", "3M", "6M", "12M"]


@dataclass(frozen=True)
class NavigationPeriod:
    """Navigation Period Value Object"""
    previous_date: datetime
    current_date: datetime
    next_date: datetime
    timeframe_code: str
    navigation_info: str
    timestamp: int
    
    @property
    def previous_formatted(self) -> str:
        """Get formatted previous date"""
        return self.previous_date.strftime('%d.%m.%Y')
    
    @property
    def current_formatted(self) -> str:
        """Get formatted current date"""
        return self.current_date.strftime('%d.%m.%Y')
    
    @property
    def next_formatted(self) -> str:
        """Get formatted next date"""
        return self.next_date.strftime('%d.%m.%Y')
    
    @property
    def current_datetime_formatted(self) -> str:
        """Get formatted current datetime"""
        return self.current_date.strftime('%d.%m.%Y %H:%M')


class TimeframeValueObject:
    """
    Timeframe Value Object - Core Domain Concept
    
    BUSINESS RULES:
    - Immutable timeframe specifications
    - Navigation period calculations
    - Timeframe validation logic
    
    DESIGN PATTERNS:
    - Value Object Pattern: Immutable, equality by value
    - Factory Pattern: Create timeframes from codes
    - Strategy Pattern: Different calculation strategies
    """
    
    # Timeframe Definitions - Business Rules
    _TIMEFRAME_DEFINITIONS: Dict[str, TimeframeMeta] = {
        "1W": TimeframeMeta(
            code="1W",
            display_name="1 Woche",
            description="Wöchentliche Analyse",
            days=7,
            icon="📊",
            css_class="timeframe-week"
        ),
        "1M": TimeframeMeta(
            code="1M", 
            display_name="1 Monat",
            description="Monatliche Analyse",
            days=30,
            icon="📈", 
            css_class="timeframe-month"
        ),
        "3M": TimeframeMeta(
            code="3M",
            display_name="3 Monate", 
            description="Quartalsweise Analyse",
            days=90,
            icon="📊",
            css_class="timeframe-quarter"
        ),
        "6M": TimeframeMeta(
            code="6M",
            display_name="6 Monate",
            description="Halbjährliche Analyse", 
            days=180,
            icon="📊",
            css_class="timeframe-half-year"
        ),
        "12M": TimeframeMeta(
            code="12M",
            display_name="12 Monate",
            description="Jährliche Analyse",
            days=365,
            icon="📈",
            css_class="timeframe-year"
        )
    }
    
    def __init__(self, timeframe_code: str):
        """
        Initialize timeframe
        
        Args:
            timeframe_code: Timeframe code (1W, 1M, 3M, 6M, 12M)
            
        Raises:
            ValueError: If timeframe_code is invalid
        """
        if timeframe_code not in self._TIMEFRAME_DEFINITIONS:
            raise ValueError(f"Invalid timeframe code: {timeframe_code}")
        
        self._timeframe_code = timeframe_code
        self._meta = self._TIMEFRAME_DEFINITIONS[timeframe_code]
    
    @property
    def code(self) -> str:
        """Get timeframe code"""
        return self._timeframe_code
    
    @property
    def display_name(self) -> str:
        """Get display name"""
        return self._meta.display_name
    
    @property
    def description(self) -> str:
        """Get description"""
        return self._meta.description
    
    @property
    def days(self) -> int:
        """Get number of days"""
        return self._meta.days
    
    @property
    def icon(self) -> str:
        """Get icon"""
        return self._meta.icon
    
    @property
    def css_class(self) -> str:
        """Get CSS class"""
        return self._meta.css_class
    
    @property
    def timedelta(self) -> timedelta:
        """Get timedelta"""
        return self._meta.timedelta
    
    def calculate_navigation_periods(self, 
                                   nav_timestamp: Optional[int] = None,
                                   nav_direction: Optional[str] = None) -> NavigationPeriod:
        """
        Calculate navigation periods for this timeframe
        
        BUSINESS RULE: Navigation periods based on timeframe duration
        
        Args:
            nav_timestamp: Navigation timestamp (optional)
            nav_direction: Navigation direction (optional)
            
        Returns:
            NavigationPeriod with calculated dates
        """
        # Determine current date
        if nav_timestamp and nav_direction:
            current_date = datetime.fromtimestamp(nav_timestamp)
            nav_info = f"📍 Navigation: {nav_direction.title()} - {current_date.strftime('%d.%m.%Y %H:%M')}"
        else:
            current_date = datetime.now()
            nav_info = "📅 Aktuelle Zeit"
        
        # Calculate previous and next dates
        delta = self.timedelta
        previous_date = current_date - delta
        next_date = current_date + delta
        
        return NavigationPeriod(
            previous_date=previous_date,
            current_date=current_date,
            next_date=next_date,
            timeframe_code=self._timeframe_code,
            navigation_info=nav_info,
            timestamp=int(current_date.timestamp())
        )
    
    def get_prediction_offset_days(self) -> int:
        """
        Get prediction offset days for this timeframe
        
        BUSINESS RULE: Prediction offset equals timeframe duration
        """
        return self._meta.days
    
    def is_short_term(self) -> bool:
        """Check if this is a short-term timeframe (≤1 month)"""
        return self._meta.days <= 30
    
    def is_medium_term(self) -> bool:
        """Check if this is a medium-term timeframe (1-6 months)"""
        return 30 < self._meta.days <= 180
    
    def is_long_term(self) -> bool:
        """Check if this is a long-term timeframe (>6 months)"""
        return self._meta.days > 180
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "code": self._timeframe_code,
            "display_name": self._meta.display_name,
            "description": self._meta.description,
            "days": self._meta.days,
            "icon": self._meta.icon,
            "css_class": self._meta.css_class
        }
    
    @classmethod
    def get_all_timeframes(cls) -> List['TimeframeValueObject']:
        """Get all available timeframes"""
        return [cls(code) for code in cls._TIMEFRAME_DEFINITIONS.keys()]
    
    @classmethod
    def get_timeframe_meta(cls, timeframe_code: str) -> Optional[TimeframeMeta]:
        """Get timeframe metadata by code"""
        return cls._TIMEFRAME_DEFINITIONS.get(timeframe_code)
    
    @classmethod
    def is_valid_timeframe(cls, timeframe_code: str) -> bool:
        """Check if timeframe code is valid"""
        return timeframe_code in cls._TIMEFRAME_DEFINITIONS
    
    @classmethod
    def get_default_timeframe(cls) -> 'TimeframeValueObject':
        """Get default timeframe (1 Month)"""
        return cls("1M")
    
    def __eq__(self, other) -> bool:
        """Equality comparison"""
        if not isinstance(other, TimeframeValueObject):
            return False
        return self._timeframe_code == other._timeframe_code
    
    def __hash__(self) -> int:
        """Hash for use in sets/dicts"""
        return hash(self._timeframe_code)
    
    def __str__(self) -> str:
        """String representation"""
        return f"Timeframe({self._timeframe_code}: {self._meta.display_name})"
    
    def __repr__(self) -> str:
        """Developer representation"""
        return f"TimeframeValueObject(code='{self._timeframe_code}', days={self._meta.days})"


@dataclass(frozen=True)
class TimeframeURL:
    """Timeframe URL Configuration Value Object"""
    timeframe_code: str
    base_url: str
    days_back: int
    
    @property 
    def full_url(self) -> str:
        """Get full URL with parameters"""
        return f"{self.base_url}?days_back={self.days_back}"
    
    def with_additional_params(self, params: Dict[str, Any]) -> str:
        """Add additional parameters to URL"""
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.full_url}&{param_string}" if param_string else self.full_url


class TimeframeURLFactory:
    """
    Factory for creating timeframe URLs
    
    DESIGN PATTERN: Factory Pattern
    Creates timeframe-specific URLs for different services
    """
    
    @staticmethod
    def create_soll_ist_url(timeframe: TimeframeValueObject, base_url: str) -> TimeframeURL:
        """Create SOLL-IST comparison URL"""
        return TimeframeURL(
            timeframe_code=timeframe.code,
            base_url=f"{base_url}/api/v1/soll-ist-comparison",
            days_back=timeframe.days
        )
    
    @staticmethod
    def create_prediction_url(timeframe: TimeframeValueObject, base_url: str) -> TimeframeURL:
        """Create prediction URL"""
        return TimeframeURL(
            timeframe_code=timeframe.code,
            base_url=f"{base_url}/api/v1/data/predictions",
            days_back=timeframe.days
        )