"""
Core Framework - Frontend-Domain
React-Framework, Design System und Event-Integration
"""

from .content_providers import ContentProviderFactory, BaseContentProvider
from .event_bus_connector import get_event_bus, EventBusConnector
from .api_gateway_connector import get_api_gateway, APIGatewayConnector
from .api_routes import api_router

__all__ = [
    'ContentProviderFactory',
    'BaseContentProvider', 
    'get_event_bus',
    'EventBusConnector',
    'get_api_gateway', 
    'APIGatewayConnector',
    'api_router'
]