#!/usr/bin/env python3
"""
Backend Base Module - Minimal Implementation
Base Classes für modulare Backend Services
Issue #65 Integration-Fix
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

# Fallback logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackendBaseModule(ABC):
    """
    Base Class für alle Backend Module
    Bietet gemeinsame Funktionalität und Interfaces
    """
    
    def __init__(self, module_name: str, event_bus=None):
        self.module_name = module_name
        self.event_bus = event_bus
        self.logger = logging.getLogger(module_name)
        self.is_initialized = False
        self.is_running = False
        self.health_status = "unknown"
        self.last_heartbeat = None
    
    async def initialize(self) -> bool:
        """Initialize Module"""
        try:
            await self._initialize_impl()
            self.is_initialized = True
            self.health_status = "healthy"
            self.logger.info(f"Module initialized: {self.module_name}")
            return True
        except Exception as e:
            self.health_status = "unhealthy" 
            self.logger.error(f"Module initialization failed: {self.module_name} - {str(e)}")
            return False
    
    @abstractmethod
    async def _initialize_impl(self):
        """Implementation-specific initialization"""
        pass
    
    async def start(self) -> bool:
        """Start Module"""
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            await self._start_impl()
            self.is_running = True
            self.last_heartbeat = datetime.utcnow()
            self.logger.info("Module started", module=self.module_name)
            return True
        except Exception as e:
            self.logger.error("Module start failed", 
                            module=self.module_name, 
                            error=str(e))
            return False
    
    @abstractmethod
    async def _start_impl(self):
        """Implementation-specific start logic"""
        pass
    
    async def stop(self):
        """Stop Module"""
        try:
            await self._stop_impl()
            self.is_running = False
            self.logger.info("Module stopped", module=self.module_name)
        except Exception as e:
            self.logger.error("Module stop failed", 
                            module=self.module_name, 
                            error=str(e))
    
    @abstractmethod
    async def _stop_impl(self):
        """Implementation-specific stop logic"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für Module"""
        self.last_heartbeat = datetime.utcnow()
        
        return {
            "module": self.module_name,
            "status": self.health_status,
            "initialized": self.is_initialized,
            "running": self.is_running,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }


class BackendModuleRegistry:
    """
    Registry für Backend Module
    Verwaltet Lebenszyklus und Health Checks
    """
    
    def __init__(self, service_name: str, event_bus=None):
        self.service_name = service_name
        self.event_bus = event_bus
        self.modules: Dict[str, BackendBaseModule] = {}
        self.logger = structlog.get_logger(f"registry.{service_name}")
    
    def register_module(self, module: BackendBaseModule):
        """Register Module"""
        self.modules[module.module_name] = module
        self.logger.info("Module registered", 
                        service=self.service_name,
                        module=module.module_name)
    
    async def start_all(self) -> bool:
        """Start alle Module"""
        success_count = 0
        
        for module_name, module in self.modules.items():
            if await module.start():
                success_count += 1
            else:
                self.logger.error("Failed to start module", 
                                service=self.service_name,
                                module=module_name)
        
        all_started = success_count == len(self.modules)
        
        if all_started:
            self.logger.info("All modules started successfully", 
                           service=self.service_name,
                           count=success_count)
        else:
            self.logger.warning("Some modules failed to start", 
                              service=self.service_name,
                              successful=success_count,
                              total=len(self.modules))
        
        return all_started
    
    async def stop_all(self):
        """Stop alle Module"""
        for module_name, module in self.modules.items():
            try:
                await module.stop()
            except Exception as e:
                self.logger.error("Error stopping module", 
                                service=self.service_name,
                                module=module_name,
                                error=str(e))
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Health Check für alle Module"""
        module_healths = {}
        overall_healthy = True
        
        for module_name, module in self.modules.items():
            try:
                health = await module.health_check()
                module_healths[module_name] = health
                
                if health.get("status") != "healthy":
                    overall_healthy = False
            except Exception as e:
                module_healths[module_name] = {
                    "status": "error",
                    "error": str(e)
                }
                overall_healthy = False
        
        return {
            "service": self.service_name,
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "modules": module_healths,
            "timestamp": datetime.utcnow().isoformat()
        }