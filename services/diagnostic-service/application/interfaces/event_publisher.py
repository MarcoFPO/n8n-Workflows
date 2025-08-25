#!/usr/bin/env python3
"""
Diagnostic Service - Event Publisher Interface
CLEAN ARCHITECTURE - APPLICATION LAYER

Interface für Event Publishing (Domain Events)
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class IEventPublisher(ABC):
    """
    Event Publisher Interface
    APPLICATION LAYER: Interface für domain event publishing
    """
    
    @abstractmethod
    async def publish_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Publish domain event
        
        Args:
            event_data: Event data containing type, data, metadata
            
        Returns:
            bool: True if published successfully
        """
        pass
    
    @abstractmethod
    async def publish_batch_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Publish multiple events in batch
        
        Args:
            events: List of event data dictionaries
            
        Returns:
            Dict with success status and results
        """
        pass
    
    @abstractmethod
    async def get_publisher_health(self) -> Dict[str, Any]:
        """
        Get event publisher health status
        
        Returns:
            Health status information
        """
        pass
    
    @abstractmethod
    async def get_published_events_count(self) -> int:
        """
        Get total number of events published
        
        Returns:
            Total events published count
        """
        pass


class IDiagnosticNotificationService(ABC):
    """
    Diagnostic Notification Service Interface
    APPLICATION LAYER: Interface für notifications and alerts
    """
    
    @abstractmethod
    async def send_health_alert(
        self, 
        alert_level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send health alert notification
        
        Args:
            alert_level: Alert severity (info, warning, error, critical)
            message: Alert message
            details: Additional alert details
            
        Returns:
            bool: True if sent successfully
        """
        pass
    
    @abstractmethod
    async def send_test_failure_notification(
        self,
        test_id: str,
        test_name: str,
        target_module: str,
        error_details: str
    ) -> bool:
        """
        Send test failure notification
        
        Args:
            test_id: Failed test ID
            test_name: Test name
            target_module: Target module that failed
            error_details: Error details
            
        Returns:
            bool: True if sent successfully
        """
        pass
    
    @abstractmethod
    async def send_performance_alert(
        self,
        performance_metric: str,
        current_value: float,
        threshold: float,
        details: Dict[str, Any]
    ) -> bool:
        """
        Send performance alert
        
        Args:
            performance_metric: Metric name (response_time, error_rate, etc.)
            current_value: Current metric value
            threshold: Threshold that was exceeded
            details: Additional performance details
            
        Returns:
            bool: True if sent successfully
        """
        pass
    
    @abstractmethod
    async def get_notification_history(
        self, 
        limit: int = 50,
        alert_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get notification history
        
        Args:
            limit: Maximum number of notifications to return
            alert_level: Filter by alert level
            
        Returns:
            List of notification records
        """
        pass


class IDiagnosticReportingService(ABC):
    """
    Diagnostic Reporting Service Interface
    APPLICATION LAYER: Interface für reporting and analytics
    """
    
    @abstractmethod
    async def generate_health_report(
        self, 
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate comprehensive health report
        
        Args:
            timeframe_hours: Report timeframe in hours
            
        Returns:
            Health report data
        """
        pass
    
    @abstractmethod
    async def generate_performance_report(
        self,
        modules: Optional[List[str]] = None,
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate module performance report
        
        Args:
            modules: Specific modules to report on (None for all)
            timeframe_hours: Report timeframe in hours
            
        Returns:
            Performance report data
        """
        pass
    
    @abstractmethod
    async def generate_error_analysis_report(
        self,
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate error analysis report
        
        Args:
            timeframe_hours: Analysis timeframe in hours
            
        Returns:
            Error analysis report
        """
        pass
    
    @abstractmethod
    async def export_diagnostic_data(
        self,
        export_format: str = "json",
        timeframe_hours: int = 24,
        include_events: bool = True,
        include_tests: bool = True,
        include_health: bool = True
    ) -> Dict[str, Any]:
        """
        Export diagnostic data
        
        Args:
            export_format: Export format (json, csv, xml)
            timeframe_hours: Data timeframe in hours
            include_events: Include captured events
            include_tests: Include diagnostic tests
            include_health: Include health snapshots
            
        Returns:
            Exported data or download information
        """
        pass
    
    @abstractmethod
    async def schedule_report(
        self,
        report_type: str,
        schedule_cron: str,
        recipients: List[str],
        report_config: Dict[str, Any]
    ) -> str:
        """
        Schedule recurring report
        
        Args:
            report_type: Type of report to schedule
            schedule_cron: Cron expression for scheduling
            recipients: List of report recipients
            report_config: Report configuration
            
        Returns:
            Scheduled report ID
        """
        pass