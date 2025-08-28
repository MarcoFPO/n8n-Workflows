#!/usr/bin/env python3
"""
Template Service Interface - Application Layer
Frontend Service Clean Architecture v1.0.0

APPLICATION LAYER - INTERFACES:
- Template Rendering Service Interface
- UI Template Generation Contract
- HTML Template Management Interface

CLEAN ARCHITECTURE PRINCIPLES:
- Interface Segregation: Template-specific operations only
- Single Responsibility: Only template rendering contract
- Dependency Inversion: Abstract template implementation

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class TemplateType(Enum):
    """Template Type Enumeration"""
    BASE = "base"
    DASHBOARD = "dashboard"
    PROGNOSEN = "prognosen"
    VERGLEICHSANALYSE = "vergleichsanalyse"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"


class TemplateTheme(Enum):
    """Template Theme Enumeration"""
    DEFAULT = "default"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"


class ITemplateService(ABC):
    """
    Template Service Interface
    
    INTERFACE SEGREGATION PRINCIPLE:
    - Only essential template operations
    - Clean contract for template rendering
    - No implementation details exposed
    """
    
    @abstractmethod
    async def render_base_template(self, 
                                 title: str, 
                                 content: str,
                                 theme: TemplateTheme = TemplateTheme.DEFAULT,
                                 meta_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Render base HTML template
        
        Args:
            title: Page title
            content: Page content HTML
            theme: Template theme
            meta_data: Additional metadata for template
            
        Returns:
            Complete HTML page as string
        """
        pass
    
    @abstractmethod
    async def render_dashboard_template(self,
                                      dashboard_data: Dict[str, Any],
                                      theme: TemplateTheme = TemplateTheme.DEFAULT) -> str:
        """
        Render dashboard template with data
        
        Args:
            dashboard_data: Dashboard data for rendering
            theme: Template theme
            
        Returns:
            Dashboard HTML page
        """
        pass
    
    @abstractmethod
    async def render_data_table(self,
                               headers: List[str],
                               rows: List[List[Any]], 
                               table_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Render data table HTML
        
        Args:
            headers: Table column headers
            rows: Table data rows
            table_config: Table configuration (styling, sorting, etc.)
            
        Returns:
            HTML table as string
        """
        pass
    
    @abstractmethod
    async def render_timeframe_selector(self,
                                      current_timeframe: str,
                                      available_timeframes: List[Dict[str, Any]],
                                      endpoint: str) -> str:
        """
        Render timeframe selector UI component
        
        Args:
            current_timeframe: Currently selected timeframe
            available_timeframes: List of available timeframes
            endpoint: Target endpoint for timeframe changes
            
        Returns:
            Timeframe selector HTML
        """
        pass
    
    @abstractmethod
    async def render_navigation_controls(self,
                                       navigation_data: Dict[str, Any],
                                       endpoint: str) -> str:
        """
        Render navigation controls (previous/next)
        
        Args:
            navigation_data: Navigation period data
            endpoint: Target endpoint for navigation
            
        Returns:
            Navigation controls HTML
        """
        pass
    
    @abstractmethod
    async def render_service_status_card(self,
                                       service_data: Dict[str, Any]) -> str:
        """
        Render service status card
        
        Args:
            service_data: Service status information
            
        Returns:
            Service status card HTML
        """
        pass
    
    @abstractmethod
    async def render_alert_message(self,
                                 message: str,
                                 alert_type: str = "info",
                                 dismissible: bool = True) -> str:
        """
        Render alert message component
        
        Args:
            message: Alert message text
            alert_type: Type of alert (info, warning, error, success)
            dismissible: Whether alert can be dismissed
            
        Returns:
            Alert message HTML
        """
        pass


class ITemplateComponentService(ABC):
    """
    Template Component Service Interface
    
    For reusable UI components
    """
    
    @abstractmethod
    async def render_loading_spinner(self, message: Optional[str] = None) -> str:
        """Render loading spinner component"""
        pass
    
    @abstractmethod
    async def render_error_message(self, error: str, details: Optional[str] = None) -> str:
        """Render error message component"""
        pass
    
    @abstractmethod
    async def render_metric_card(self, title: str, value: str, 
                               icon: str, color: str = "blue") -> str:
        """Render metric display card"""
        pass
    
    @abstractmethod 
    async def render_progress_bar(self, percentage: float, 
                                label: Optional[str] = None) -> str:
        """Render progress bar component"""
        pass


class ITemplateCache(ABC):
    """
    Template Cache Interface
    
    For template caching and performance optimization
    """
    
    @abstractmethod
    async def get_cached_template(self, template_key: str) -> Optional[str]:
        """Get cached template by key"""
        pass
    
    @abstractmethod
    async def cache_template(self, template_key: str, content: str, ttl_seconds: int = 3600) -> None:
        """Cache template content"""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, template_key: Optional[str] = None) -> None:
        """Invalidate template cache"""
        pass


class TemplateRenderError(Exception):
    """Template rendering error"""
    
    def __init__(self, message: str, template_type: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.template_type = template_type
        self.data = data
        self.timestamp = datetime.now()


class TemplateNotFoundError(TemplateRenderError):
    """Template not found error"""
    pass


class TemplateDataValidationError(TemplateRenderError):
    """Template data validation error"""
    pass