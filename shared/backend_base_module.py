"""
Backend Base Module Pattern für Aktienanalyse-Ökosystem
Shared Base Class für alle Backend-Module mit Event-Bus Integration
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
from event_bus import EventBusConnector, Event, EventType


class BackendBaseModule(ABC):
    """Base class für alle Backend-Module mit Event-Bus Integration"""
    
    def __init__(self, module_name: str, event_bus: EventBusConnector):
        self.module_name = module_name
        self.event_bus = event_bus
        self.logger = structlog.get_logger(f"backend.{module_name}")
        self.is_initialized = False
        self.subscribed_events: List[EventType] = []
        self.module_data_cache: Dict[str, Any] = {}
        self.last_cache_update = None
        
    async def initialize(self) -> bool:
        """Initialize module with event subscriptions"""
        try:
            # Module-specific initialization
            init_result = await self._initialize_module()
            if not init_result:
                self.logger.error("Module-specific initialization failed")
                return False
            
            # Subscribe to events
            await self._subscribe_to_events()
            
            self.is_initialized = True
            self.logger.info("Backend module initialized successfully", 
                           module=self.module_name,
                           subscribed_events=len(self.subscribed_events))
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize backend module", 
                            module=self.module_name, error=str(e))
            return False
    
    async def shutdown(self):
        """Shutdown module gracefully"""
        try:
            await self._cleanup_module()
            self.is_initialized = False
            self.logger.info("Backend module shutdown complete", module=self.module_name)
        except Exception as e:
            self.logger.error("Error during module shutdown", 
                            module=self.module_name, error=str(e))
    
    @abstractmethod
    async def _initialize_module(self) -> bool:
        """
        Module-specific initialization logic.
        Must be implemented by subclasses.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        raise NotImplementedError(f"Module {self.module_name} must implement _initialize_module()")
    
    @abstractmethod
    async def _subscribe_to_events(self):
        """
        Subscribe to relevant events for this module.
        Must be implemented by subclasses.
        
        Example:
            await self.subscribe_to_event(EventType.ANALYSIS_STATE_CHANGED, self._handle_analysis_event)
        """
        raise NotImplementedError(f"Module {self.module_name} must implement _subscribe_to_events()")
    
    @abstractmethod
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main business logic processing for this module.
        Must be implemented by subclasses.
        
        Args:
            data: Input data for processing
            
        Returns:
            Dict[str, Any]: Processed result data
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(f"Module {self.module_name} must implement process_business_logic()")
    
    async def _cleanup_module(self):
        """
        Module-specific cleanup (override if needed).
        Default implementation clears cache and resets state.
        """
        try:
            self.module_data_cache.clear()
            self.subscribed_events.clear()
            self.last_cache_update = None
            self.logger.info("Module cleanup completed", module=self.module_name)
        except Exception as e:
            self.logger.warning("Error during module cleanup", 
                              module=self.module_name, error=str(e))
    
    async def subscribe_to_event(self, event_type: EventType, handler):
        """Subscribe to a specific event type"""
        try:
            await self.event_bus.subscribe(event_type.value, handler)
            self.subscribed_events.append(event_type)
            self.logger.debug("Subscribed to event", 
                            module=self.module_name, 
                            event_type=event_type.value)
        except Exception as e:
            self.logger.error("Failed to subscribe to event", 
                            module=self.module_name,
                            event_type=event_type.value, 
                            error=str(e))
    
    async def publish_module_event(self, event_type: EventType, data: Dict[str, Any], 
                                 stream_id: str = None) -> bool:
        """Publish event from this module"""
        try:
            if stream_id is None:
                stream_id = f"{self.module_name}-{int(time.time())}"
            
            event = Event(
                event_type=event_type.value,
                stream_id=stream_id,
                data=data,
                source=self.module_name,
                metadata={"module_type": "backend", "timestamp": datetime.now().isoformat()}
            )
            
            success = await self.event_bus.publish(event)
            if success:
                self.logger.debug("Event published successfully", 
                                module=self.module_name,
                                event_type=event_type.value,
                                stream_id=stream_id)
            return success
            
        except Exception as e:
            self.logger.error("Failed to publish event", 
                            module=self.module_name,
                            event_type=event_type.value, 
                            error=str(e))
            return False
    
    def update_module_cache(self, key: str, data: Any):
        """Update module's internal cache"""
        self.module_data_cache[key] = data
        self.last_cache_update = datetime.now()
        self.logger.debug("Module cache updated", 
                        module=self.module_name, 
                        cache_key=key)
    
    def get_module_cache(self, key: str, default=None):
        """Get data from module's cache"""
        return self.module_data_cache.get(key, default)
    
    def clear_module_cache(self):
        """Clear module's cache"""
        self.module_data_cache.clear()
        self.last_cache_update = None
        self.logger.debug("Module cache cleared", module=self.module_name)
    
    def get_module_status(self) -> Dict[str, Any]:
        """Get module health and status information"""
        return {
            "module_name": self.module_name,
            "is_initialized": self.is_initialized,
            "subscribed_events_count": len(self.subscribed_events),
            "cache_size": len(self.module_data_cache),
            "last_cache_update": self.last_cache_update.isoformat() if self.last_cache_update else None,
            "event_bus_connected": self.event_bus.connected if self.event_bus else False
        }


class BackendModuleRegistry:
    """Registry für alle Backend-Module eines Services"""
    
    def __init__(self, service_name: str, event_bus: EventBusConnector):
        self.service_name = service_name
        self.event_bus = event_bus
        self.modules: Dict[str, BackendBaseModule] = {}
        self.logger = structlog.get_logger(f"backend.{service_name}.registry")
    
    def register_module(self, module: BackendBaseModule):
        """Register a new module"""
        self.modules[module.module_name] = module
        self.logger.info("Module registered", 
                       service=self.service_name,
                       module=module.module_name)
    
    async def initialize_all_modules(self) -> Dict[str, bool]:
        """Initialize all registered modules"""
        results = {}
        for name, module in self.modules.items():
            try:
                results[name] = await module.initialize()
                self.logger.info("Module initialization result", 
                               service=self.service_name,
                               module=name, 
                               success=results[name])
            except Exception as e:
                results[name] = False
                self.logger.error("Module initialization failed", 
                                service=self.service_name,
                                module=name, 
                                error=str(e))
        return results
    
    async def shutdown_all_modules(self):
        """Shutdown all modules gracefully"""
        for name, module in self.modules.items():
            try:
                await module.shutdown()
                self.logger.info("Module shutdown complete", 
                               service=self.service_name,
                               module=name)
            except Exception as e:
                self.logger.error("Module shutdown error", 
                                service=self.service_name,
                                module=name, 
                                error=str(e))
    
    def get_module(self, module_name: str) -> Optional[BackendBaseModule]:
        """Get specific module by name"""
        return self.modules.get(module_name)
    
    def get_all_module_status(self) -> Dict[str, Any]:
        """Get status of all modules"""
        return {
            "service_name": self.service_name,
            "total_modules": len(self.modules),
            "modules": {name: module.get_module_status() 
                       for name, module in self.modules.items()}
        }