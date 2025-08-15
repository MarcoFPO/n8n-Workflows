"""
Single Function Module Base - Standard Interface für Ein-Funktion-Module
Implementiert das "Eine Funktion = Ein Modul" Pattern
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, structlog, BaseModel
)
from backend_base_module import BackendBaseModule
from event_bus import EventType


class SingleFunctionModule(BackendBaseModule, ABC):
    """
    Abstract Base Class für Single-Function-Module
    Jede Implementierung enthält genau eine Hauptfunktion
    """
    
    def __init__(self, function_name: str, event_bus=None):
        super().__init__(function_name, event_bus)
        self.function_name = function_name
        self.execution_count = 0
        self.last_execution_time = None
        self.average_execution_time = 0.0
        
    @abstractmethod
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion des Moduls - muss von jeder Implementierung überschrieben werden
        
        Args:
            input_data: Input-Parameter für die Funktion
            
        Returns:
            Dict mit Ergebnis und Metadaten
        """
        pass
    
    @abstractmethod
    def get_function_info(self) -> Dict[str, Any]:
        """
        Metadaten über die Funktion
        
        Returns:
            Dict mit Funktionsinfo (Name, Beschreibung, Parameter, etc.)
        """
        pass
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standard Business Logic Wrapper - trackt Performance
        """
        start_time = datetime.now()
        
        try:
            # Hauptfunktion ausführen
            result = await self.execute_function(data)
            
            # Performance tracking
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(execution_time)
            
            # Success Event publishen
            if self.event_bus and self.event_bus.connected:
                await self._publish_success_event(data, result, execution_time)
            
            return {
                'success': True,
                'result': result,
                'execution_time': execution_time,
                'function_name': self.function_name
            }
            
        except Exception as e:
            # Error Event publishen
            execution_time = (datetime.now() - start_time).total_seconds()
            if self.event_bus and self.event_bus.connected:
                await self._publish_error_event(data, str(e), execution_time)
            
            self.logger.error(f"Error in {self.function_name}", 
                            error=str(e), 
                            input_data=data,
                            execution_time=execution_time)
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'function_name': self.function_name
            }
    
    def _update_performance_metrics(self, execution_time: float):
        """Performance-Metriken aktualisieren"""
        self.execution_count += 1
        self.last_execution_time = execution_time
        
        # Rolling Average berechnen
        if self.execution_count == 1:
            self.average_execution_time = execution_time
        else:
            # Exponential Moving Average
            alpha = 0.1
            self.average_execution_time = (alpha * execution_time + 
                                         (1 - alpha) * self.average_execution_time)
    
    async def _publish_success_event(self, input_data: Dict, result: Dict, execution_time: float):
        """Success Event über Event-Bus publishen"""
        from event_bus import Event
        
        event = Event(
            event_type=f"{self.function_name}_success",
            stream_id=f"{self.function_name}-{int(datetime.now().timestamp())}",
            data={
                'function_name': self.function_name,
                'input_data': input_data,
                'result': result,
                'execution_time': execution_time,
                'execution_count': self.execution_count
            },
            source=f"module-{self.function_name}"
        )
        
        await self.event_bus.publish(event)
    
    async def _publish_error_event(self, input_data: Dict, error: str, execution_time: float):
        """Error Event über Event-Bus publishen"""
        from event_bus import Event
        
        event = Event(
            event_type=f"{self.function_name}_error",
            stream_id=f"{self.function_name}-error-{int(datetime.now().timestamp())}",
            data={
                'function_name': self.function_name,
                'input_data': input_data,
                'error': error,
                'execution_time': execution_time,
                'execution_count': self.execution_count
            },
            source=f"module-{self.function_name}"
        )
        
        await self.event_bus.publish(event)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Performance-Metriken abrufen"""
        return {
            'function_name': self.function_name,
            'execution_count': self.execution_count,
            'last_execution_time': self.last_execution_time,
            'average_execution_time': self.average_execution_time,
            'is_active': self.is_active
        }
    
    async def get_health(self) -> Dict[str, Any]:
        """Health-Status des Single-Function-Moduls"""
        base_health = await super().get_health()
        
        return {
            **base_health,
            'function_info': self.get_function_info(),
            'performance_metrics': self.get_performance_metrics()
        }