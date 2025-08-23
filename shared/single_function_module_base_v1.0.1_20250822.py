"""
Production-Ready Single Function Module Base - Standard Interface für Ein-Funktion-Module
Implementiert das "Eine Funktion = Ein Modul" Pattern mit Event-Bus Integration
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"ℹ️ {msg} {kwargs}")
        def debug(self, msg, **kwargs): print(f"🐛 {msg} {kwargs}")
        def error(self, msg, **kwargs): print(f"❌ {msg} {kwargs}")
        def warning(self, msg, **kwargs): print(f"⚠️ {msg} {kwargs}")
    logger = MockLogger()


class ModuleConfig:
    """Configuration for Single Function Modules"""
    
    def __init__(self):
        self.max_execution_time = 30.0  # seconds
        self.enable_performance_tracking = True
        self.enable_event_publishing = True
        self.log_level = 'INFO'


class SingleFunctionModuleBase(ABC):
    """
    Production-Ready Base Class für Single-Function-Module
    Jede Implementierung enthält genau eine Hauptfunktion
    """
    
    def __init__(self, config: ModuleConfig = None):
        self.config = config or ModuleConfig()
        self.logger = logger.bind(module=self.__class__.__name__)
        self.execution_count = 0
        self.last_execution_time = None
        self.average_execution_time = 0.0
        self.total_execution_time = 0.0
        self.error_count = 0
        self.success_count = 0
        self.created_at = datetime.now()
        self.is_active = True
        
    @abstractmethod
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion des Moduls - muss von jeder Implementierung überschrieben werden
        
        Args:
            input_data: Input-Parameter für die Funktion
            
        Returns:
            Dict mit Ergebnis und Metadaten
        """
        raise NotImplementedError("Subclasses must implement execute_function()")
    
    @abstractmethod
    def get_function_info(self) -> Dict[str, Any]:
        """
        Metadaten über die Funktion
        
        Returns:
            Dict mit Funktionsinfo (Name, Beschreibung, Parameter, etc.)
        """
        raise NotImplementedError("Subclasses must implement get_function_info()")
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Production-Ready Business Logic Wrapper mit Performance Tracking
        """
        start_time = datetime.now()
        function_name = self.__class__.__name__
        
        try:
            self.logger.debug("Starting function execution", 
                            function=function_name, 
                            input_keys=list(data.keys()) if data else [])
            
            # Hauptfunktion ausführen
            result = await self.execute_function(data)
            
            # Performance tracking
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(execution_time, success=True)
            
            # Success Event publishen (wenn Event Bus verfügbar)
            if hasattr(self, 'event_bus') and self.event_bus:
                await self._publish_success_event(data, result, execution_time)
            
            self.logger.info("Function execution completed", 
                           function=function_name,
                           execution_time=execution_time,
                           success=True)
            
            return {
                'success': True,
                'result': result,
                'execution_time': execution_time,
                'function_name': function_name,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            # Error tracking
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(execution_time, success=False)
            
            # Error Event publishen (wenn Event Bus verfügbar)
            if hasattr(self, 'event_bus') and self.event_bus:
                await self._publish_error_event(data, str(e), execution_time)
            
            self.logger.error("Function execution failed", 
                            function=function_name,
                            error=str(e), 
                            input_data=data,
                            execution_time=execution_time)
            
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'execution_time': execution_time,
                'function_name': function_name,
                'timestamp': datetime.now().isoformat()
            }
    
    def _update_performance_metrics(self, execution_time: float, success: bool = True):
        """Performance-Metriken aktualisieren"""
        self.execution_count += 1
        self.last_execution_time = execution_time
        self.total_execution_time += execution_time
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        # Rolling Average berechnen
        if self.execution_count == 1:
            self.average_execution_time = execution_time
        else:
            # Exponential Moving Average mit Alpha = 0.1
            alpha = 0.1
            self.average_execution_time = (alpha * execution_time + 
                                         (1 - alpha) * self.average_execution_time)
    
    async def _publish_success_event(self, input_data: Dict, result: Dict, execution_time: float):
        """Success Event über Event-Bus publishen"""
        try:
            if hasattr(self.event_bus, 'publish'):
                event_data = {
                    'event_type': f"{self.__class__.__name__}_success",
                    'function_name': self.__class__.__name__,
                    'input_data': input_data,
                    'result': result,
                    'execution_time': execution_time,
                    'execution_count': self.execution_count,
                    'timestamp': datetime.now().isoformat()
                }
                
                await self.event_bus.publish(event_data)
        except Exception as e:
            self.logger.warning("Failed to publish success event", error=str(e))
    
    async def _publish_error_event(self, input_data: Dict, error: str, execution_time: float):
        """Error Event über Event-Bus publishen"""
        try:
            if hasattr(self.event_bus, 'publish'):
                event_data = {
                    'event_type': f"{self.__class__.__name__}_error",
                    'function_name': self.__class__.__name__,
                    'input_data': input_data,
                    'error': error,
                    'execution_time': execution_time,
                    'execution_count': self.execution_count,
                    'error_count': self.error_count,
                    'timestamp': datetime.now().isoformat()
                }
                
                await self.event_bus.publish(event_data)
        except Exception as e:
            self.logger.warning("Failed to publish error event", error=str(e))
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Production-Ready Performance-Metriken abrufen"""
        uptime_seconds = (datetime.now() - self.created_at).total_seconds()
        success_rate = (self.success_count / self.execution_count) if self.execution_count > 0 else 0.0
        error_rate = (self.error_count / self.execution_count) if self.execution_count > 0 else 0.0
        
        return {
            'function_name': self.__class__.__name__,
            'execution_count': self.execution_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': success_rate,
            'error_rate': error_rate,
            'last_execution_time': self.last_execution_time,
            'average_execution_time': self.average_execution_time,
            'total_execution_time': self.total_execution_time,
            'uptime_seconds': uptime_seconds,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Production-Ready Health-Status des Single-Function-Moduls"""
        try:
            metrics = self.get_performance_metrics()
            function_info = self.get_function_info()
            
            # Health Score berechnen (0.0 - 1.0)
            health_score = 1.0
            health_issues = []
            
            # Error Rate Check
            error_rate = metrics.get('error_rate', 0.0)
            if error_rate > 0.1:  # > 10% Error Rate
                health_score -= 0.3
                health_issues.append(f"High error rate: {error_rate:.1%}")
            
            # Performance Check
            avg_time = metrics.get('average_execution_time', 0.0)
            if avg_time > self.config.max_execution_time:
                health_score -= 0.2
                health_issues.append(f"Slow execution: {avg_time:.2f}s > {self.config.max_execution_time}s")
            
            # Activity Check
            if not self.is_active:
                health_score -= 0.5
                health_issues.append("Module is inactive")
            
            # Determine health status
            if health_score >= 0.8:
                health_status = "healthy"
            elif health_score >= 0.5:
                health_status = "degraded"
            else:
                health_status = "unhealthy"
            
            return {
                'health_status': health_status,
                'health_score': max(0.0, health_score),
                'health_issues': health_issues,
                'function_info': function_info,
                'performance_metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get health status", error=str(e))
            return {
                'health_status': 'unknown',
                'health_score': 0.0,
                'health_issues': [f"Health check failed: {str(e)}"],
                'timestamp': datetime.now().isoformat()
            }
    
    def set_active(self, active: bool):
        """Modul aktivieren/deaktivieren"""
        self.is_active = active
        self.logger.info("Module activity changed", active=active)
    
    def reset_metrics(self):
        """Performance-Metriken zurücksetzen"""
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_execution_time = None
        self.average_execution_time = 0.0
        self.total_execution_time = 0.0
        self.created_at = datetime.now()
        self.logger.info("Performance metrics reset")


# Factory function for creating modules with config
def create_module_with_config(module_class, config: ModuleConfig = None):
    """Factory function to create modules with configuration"""
    if config is None:
        config = ModuleConfig()
    return module_class(config)