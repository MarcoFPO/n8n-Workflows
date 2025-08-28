"""
Event Validator Service - Domain service for event validation
Validates events according to business rules

Code-Qualität: HÖCHSTE PRIORITÄT
Version: 7.0.0
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any
from domain.entities.event import Event


@dataclass
class ValidationResult:
    """Result of event validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class EventValidatorService:
    """
    Domain service for validating events according to business rules
    """
    
    # Allowed event types based on HLD.md
    ALLOWED_EVENT_TYPES = {
        "analysis.state.changed",
        "analysis.prediction.generated", 
        "portfolio.state.changed",
        "profit.calculation.completed",
        "trading.state.changed",
        "intelligence.triggered",
        "data.synchronized",
        "market.data.synchronized",
        "system.alert.raised",
        "user.interaction.logged",
        "config.updated"
    }
    
    # Required fields for specific event types
    EVENT_TYPE_REQUIREMENTS = {
        "analysis.prediction.generated": ["symbol", "predictions"],
        "profit.calculation.completed": ["symbol", "ist_gewinn"],
        "portfolio.state.changed": ["total_value", "performance_pct"],
        "market.data.synchronized": ["source", "symbols_count"],
        "trading.state.changed": ["action", "symbol", "amount"]
    }
    
    def __init__(self):
        """Initialize event validator service"""
        self.max_event_data_size = 1024 * 1024  # 1MB limit
        self.max_metadata_size = 64 * 1024      # 64KB limit
    
    async def validate(self, event: Event) -> ValidationResult:
        """
        Validate event according to business rules
        
        Args:
            event: Event to validate
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []
        
        # Basic field validation
        errors.extend(self._validate_basic_fields(event))
        
        # Event type validation
        errors.extend(self._validate_event_type(event))
        
        # Event data validation
        errors.extend(self._validate_event_data(event))
        
        # Size validation
        errors.extend(self._validate_size_limits(event))
        
        # Business rule validation
        errors.extend(self._validate_business_rules(event))
        
        # Add warnings for potential issues
        warnings.extend(self._check_warnings(event))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_basic_fields(self, event: Event) -> List[str]:
        """Validate basic required fields"""
        errors = []
        
        if not event.event_id:
            errors.append("event_id is required")
        elif not self._is_valid_uuid(event.event_id):
            errors.append("event_id must be a valid UUID")
        
        if not event.event_type:
            errors.append("event_type is required")
        
        if event.event_data is None:
            errors.append("event_data cannot be None")
        elif not isinstance(event.event_data, dict):
            errors.append("event_data must be a dictionary")
        
        if event.created_at is None:
            errors.append("created_at is required")
        
        if event.correlation_id and not self._is_valid_uuid(event.correlation_id):
            errors.append("correlation_id must be a valid UUID if provided")
        
        return errors
    
    def _validate_event_type(self, event: Event) -> List[str]:
        """Validate event type"""
        errors = []
        
        if event.event_type not in self.ALLOWED_EVENT_TYPES:
            errors.append(f"Unknown event type: {event.event_type}")
        
        return errors
    
    def _validate_event_data(self, event: Event) -> List[str]:
        """Validate event data structure and content"""
        errors = []
        
        if not event.event_data:
            return errors
        
        # Check for required fields based on event type
        required_fields = self.EVENT_TYPE_REQUIREMENTS.get(event.event_type, [])
        for field in required_fields:
            if field not in event.event_data:
                errors.append(f"Required field '{field}' missing for event type {event.event_type}")
        
        # Validate specific event types
        if event.event_type == "analysis.prediction.generated":
            errors.extend(self._validate_prediction_event(event.event_data))
        elif event.event_type == "profit.calculation.completed":
            errors.extend(self._validate_profit_event(event.event_data))
        elif event.event_type == "portfolio.state.changed":
            errors.extend(self._validate_portfolio_event(event.event_data))
        
        return errors
    
    def _validate_prediction_event(self, event_data: Dict[str, Any]) -> List[str]:
        """Validate prediction event data"""
        errors = []
        
        if "symbol" in event_data:
            symbol = event_data["symbol"]
            if not isinstance(symbol, str) or not re.match(r'^[A-Z]{1,5}$', symbol):
                errors.append("symbol must be 1-5 uppercase letters")
        
        if "predictions" in event_data:
            predictions = event_data["predictions"]
            if not isinstance(predictions, dict):
                errors.append("predictions must be a dictionary")
            else:
                # Validate horizon keys
                valid_horizons = {"1W", "1M", "3M", "12M"}
                for horizon in predictions.keys():
                    if horizon not in valid_horizons:
                        errors.append(f"Invalid prediction horizon: {horizon}")
        
        return errors
    
    def _validate_profit_event(self, event_data: Dict[str, Any]) -> List[str]:
        """Validate profit calculation event data"""
        errors = []
        
        if "ist_gewinn" in event_data:
            try:
                float(event_data["ist_gewinn"])
            except (ValueError, TypeError):
                errors.append("ist_gewinn must be a numeric value")
        
        return errors
    
    def _validate_portfolio_event(self, event_data: Dict[str, Any]) -> List[str]:
        """Validate portfolio event data"""
        errors = []
        
        if "total_value" in event_data:
            try:
                value = float(event_data["total_value"])
                if value < 0:
                    errors.append("total_value cannot be negative")
            except (ValueError, TypeError):
                errors.append("total_value must be a numeric value")
        
        if "performance_pct" in event_data:
            try:
                float(event_data["performance_pct"])
            except (ValueError, TypeError):
                errors.append("performance_pct must be a numeric value")
        
        return errors
    
    def _validate_size_limits(self, event: Event) -> List[str]:
        """Validate size limits"""
        errors = []
        
        import json
        
        # Check event data size
        event_data_size = len(json.dumps(event.event_data).encode('utf-8'))
        if event_data_size > self.max_event_data_size:
            errors.append(f"event_data exceeds size limit: {event_data_size} > {self.max_event_data_size}")
        
        # Check metadata size
        if event.metadata:
            metadata_size = len(json.dumps(event.metadata).encode('utf-8'))
            if metadata_size > self.max_metadata_size:
                errors.append(f"metadata exceeds size limit: {metadata_size} > {self.max_metadata_size}")
        
        return errors
    
    def _validate_business_rules(self, event: Event) -> List[str]:
        """Validate business-specific rules"""
        errors = []
        
        # Rule: Future-dated events are not allowed
        from datetime import datetime
        if event.created_at > datetime.utcnow():
            errors.append("created_at cannot be in the future")
        
        # Rule: Processed events should have processed_at timestamp
        if event.is_processed() and event.processed_at is None:
            errors.append("processed events must have processed_at timestamp")
        
        return errors
    
    def _check_warnings(self, event: Event) -> List[str]:
        """Check for potential issues that don't invalidate the event"""
        warnings = []
        
        # Large event data warning
        import json
        event_data_size = len(json.dumps(event.event_data).encode('utf-8'))
        if event_data_size > 100 * 1024:  # 100KB
            warnings.append(f"Large event data: {event_data_size} bytes")
        
        # Old event warning
        from datetime import datetime, timedelta
        if event.created_at < datetime.utcnow() - timedelta(days=1):
            warnings.append("Event is older than 1 day")
        
        return warnings
    
    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Check if string is a valid UUID"""
        import uuid
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False