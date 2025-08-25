#!/usr/bin/env python3
"""
Diagnostic Service - Domain Repository Interfaces
CLEAN ARCHITECTURE - DOMAIN LAYER

Repository interfaces for diagnostic data persistence
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025  
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..entities.diagnostic_event import (
    CapturedEvent, DiagnosticTest, SystemHealthSnapshot, 
    ModuleCommunicationTest, TestResultStatus
)


class IDiagnosticEventRepository(ABC):
    """
    Repository interface für captured events
    DOMAIN LAYER: Pure interface without implementation details
    """
    
    @abstractmethod
    async def save_event(self, event: CapturedEvent) -> bool:
        """Save a captured event"""
        pass
    
    @abstractmethod
    async def get_events(
        self, 
        limit: int = 100, 
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[CapturedEvent]:
        """Get captured events with filtering"""
        pass
    
    @abstractmethod
    async def get_event_by_id(self, capture_id: str) -> Optional[CapturedEvent]:
        """Get event by capture ID"""
        pass
    
    @abstractmethod
    async def get_events_by_source(self, source: str, limit: int = 100) -> List[CapturedEvent]:
        """Get events from specific source"""
        pass
    
    @abstractmethod
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[CapturedEvent]:
        """Get events of specific type"""
        pass
    
    @abstractmethod
    async def get_error_events(self, limit: int = 50) -> List[CapturedEvent]:
        """Get error events only"""
        pass
    
    @abstractmethod
    async def cleanup_old_events(self, older_than_days: int = 7) -> int:
        """Clean up old events, return count of removed events"""
        pass
    
    @abstractmethod
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event statistics summary"""
        pass


class IDiagnosticTestRepository(ABC):
    """
    Repository interface für diagnostic tests
    DOMAIN LAYER: Test management and persistence
    """
    
    @abstractmethod
    async def save_test(self, test: DiagnosticTest) -> bool:
        """Save a diagnostic test"""
        pass
    
    @abstractmethod
    async def update_test_status(
        self, 
        test_id: str, 
        status: TestResultStatus,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update test execution status"""
        pass
    
    @abstractmethod
    async def get_test_by_id(self, test_id: str) -> Optional[DiagnosticTest]:
        """Get test by ID"""
        pass
    
    @abstractmethod
    async def get_tests(
        self, 
        limit: int = 100, 
        status_filter: Optional[TestResultStatus] = None
    ) -> List[DiagnosticTest]:
        """Get diagnostic tests with optional status filtering"""
        pass
    
    @abstractmethod
    async def get_tests_by_module(self, target_module: str) -> List[DiagnosticTest]:
        """Get tests for specific module"""
        pass
    
    @abstractmethod
    async def get_pending_tests(self) -> List[DiagnosticTest]:
        """Get all pending tests"""
        pass
    
    @abstractmethod
    async def cleanup_completed_tests(self, older_than_hours: int = 24) -> int:
        """Clean up old completed tests"""
        pass


class ISystemHealthRepository(ABC):
    """
    Repository interface für system health snapshots
    DOMAIN LAYER: Health monitoring persistence
    """
    
    @abstractmethod
    async def save_health_snapshot(self, snapshot: SystemHealthSnapshot) -> bool:
        """Save system health snapshot"""
        pass
    
    @abstractmethod
    async def get_latest_snapshot(self) -> Optional[SystemHealthSnapshot]:
        """Get most recent health snapshot"""
        pass
    
    @abstractmethod
    async def get_snapshots(
        self, 
        limit: int = 100,
        from_time: Optional[datetime] = None
    ) -> List[SystemHealthSnapshot]:
        """Get health snapshots with time filtering"""
        pass
    
    @abstractmethod
    async def get_health_trend(self, hours: int = 24) -> List[SystemHealthSnapshot]:
        """Get health trend over specified hours"""
        pass
    
    @abstractmethod
    async def cleanup_old_snapshots(self, older_than_days: int = 30) -> int:
        """Clean up old health snapshots"""
        pass


class IModuleCommunicationRepository(ABC):
    """
    Repository interface für module communication tests
    DOMAIN LAYER: Communication test persistence
    """
    
    @abstractmethod
    async def save_communication_test(self, test: ModuleCommunicationTest) -> bool:
        """Save module communication test"""
        pass
    
    @abstractmethod
    async def update_test_response(
        self, 
        test_id: str,
        response_data: Dict[str, Any],
        success: bool,
        error_details: Optional[str] = None
    ) -> bool:
        """Update communication test with response"""
        pass
    
    @abstractmethod
    async def get_communication_test(self, test_id: str) -> Optional[ModuleCommunicationTest]:
        """Get communication test by ID"""
        pass
    
    @abstractmethod
    async def get_communication_tests(
        self, 
        source_module: Optional[str] = None,
        target_module: Optional[str] = None,
        limit: int = 100
    ) -> List[ModuleCommunicationTest]:
        """Get communication tests with filtering"""
        pass
    
    @abstractmethod
    async def get_module_connectivity_stats(self, module_name: str) -> Dict[str, Any]:
        """Get connectivity statistics for a module"""
        pass


class IDiagnosticEventBusProvider(ABC):
    """
    Provider interface für Event Bus integration
    DOMAIN LAYER: External system interface
    """
    
    @abstractmethod
    async def publish_diagnostic_event(self, event_data: Dict[str, Any]) -> bool:
        """Publish diagnostic event to event bus"""
        pass
    
    @abstractmethod
    async def subscribe_to_events(self, event_types: List[str]) -> bool:
        """Subscribe to specific event types for monitoring"""
        pass
    
    @abstractmethod
    async def send_test_message(
        self, 
        target_module: str, 
        message_data: Dict[str, Any]
    ) -> str:
        """Send test message and return test correlation ID"""
        pass
    
    @abstractmethod
    async def ping_module(self, module_name: str) -> bool:
        """Ping specific module to test connectivity"""
        pass
    
    @abstractmethod
    async def is_event_bus_healthy(self) -> bool:
        """Check if event bus is healthy and responsive"""
        pass
    
    @abstractmethod
    async def get_connected_modules(self) -> List[str]:
        """Get list of modules connected to event bus"""
        pass