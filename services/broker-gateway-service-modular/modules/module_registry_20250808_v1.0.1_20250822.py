"""
Module Registry - Central Registry für Single Function Modules
Implementiert das Module Discovery und Management Pattern
"""

from typing import Dict, Any, List, Optional, Type
import inspect
import importlib
from pathlib import Path
import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

from shared.common_imports import (
    datetime, structlog
)
from event_bus import EventBusConnector, Event, EventType
from .single_function_module_base import SingleFunctionModule


class ModuleRegistryEntry:
    """Registry-Eintrag für ein einzelnes Modul"""
    
    def __init__(self, module_name: str, module_class: Type[SingleFunctionModule], 
                 module_instance: Optional[SingleFunctionModule] = None):
        self.module_name = module_name
        self.module_class = module_class
        self.module_instance = module_instance
        self.registration_time = datetime.now()
        self.is_loaded = module_instance is not None
        self.load_count = 0
        self.last_accessed = None
        self.performance_metrics = {}


class ModuleRegistry:
    """
    Central Registry für alle Single Function Modules
    Implementiert Lazy Loading, Performance Tracking und Event-Bus Integration
    """
    
    def __init__(self, event_bus: EventBusConnector = None):
        self.event_bus = event_bus
        self.logger = structlog.get_logger("module_registry")
        
        # Registry Storage
        self.modules: Dict[str, ModuleRegistryEntry] = {}
        self.module_groups: Dict[str, List[str]] = {}  # Grouping related modules
        
        # Performance Tracking
        self.total_module_calls = 0
        self.failed_module_calls = 0
        self.average_response_time = 0.0
        
        # Auto-Discovery Configuration
        self.auto_discovery_paths = [
            'order_modules',  # Order-related modules
            'account_modules',  # Account-related modules (future)
            'market_modules'    # Market-related modules (future)
        ]
        
    async def initialize(self):
        """Registry initialisieren und Module auto-discovern"""
        self.logger.info("Initializing Module Registry")
        
        # Auto-discover modules
        await self._auto_discover_modules()
        
        # Event-Bus Integration
        if self.event_bus:
            await self._setup_event_subscriptions()
        
        self.logger.info(f"Module Registry initialized with {len(self.modules)} modules")
    
    async def register_module(self, module_name: str, module_class: Type[SingleFunctionModule], 
                            group: str = None, auto_load: bool = False) -> bool:
        """
        Modul im Registry registrieren
        
        Args:
            module_name: Eindeutiger Modulname
            module_class: Modul-Klasse (nicht instanziiert)
            group: Optional - Gruppierung für verwandte Module
            auto_load: Sofort laden oder Lazy Loading
        """
        try:
            if module_name in self.modules:
                self.logger.warning(f"Module {module_name} already registered, skipping")
                return False
            
            # Module-Instanz erstellen falls auto_load
            module_instance = None
            if auto_load:
                module_instance = module_class(self.event_bus)
                await module_instance._initialize_module()
            
            # Registry Entry erstellen
            entry = ModuleRegistryEntry(module_name, module_class, module_instance)
            self.modules[module_name] = entry
            
            # Zu Gruppe hinzufügen
            if group:
                if group not in self.module_groups:
                    self.module_groups[group] = []
                self.module_groups[group].append(module_name)
            
            self.logger.info(f"Module registered: {module_name}", 
                           group=group, auto_loaded=auto_load)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register module {module_name}", error=str(e))
            return False
    
    async def get_module(self, module_name: str) -> Optional[SingleFunctionModule]:
        """
        Modul abrufen (mit Lazy Loading)
        
        Args:
            module_name: Name des Moduls
            
        Returns:
            Modul-Instanz oder None
        """
        if module_name not in self.modules:
            self.logger.error(f"Module {module_name} not found in registry")
            return None
        
        entry = self.modules[module_name]
        
        # Lazy Loading: Modul laden falls noch nicht geladen
        if not entry.is_loaded:
            try:
                entry.module_instance = entry.module_class(self.event_bus)
                await entry.module_instance._initialize_module()
                entry.is_loaded = True
                entry.load_count += 1
                
                self.logger.info(f"Module lazy-loaded: {module_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to lazy-load module {module_name}", error=str(e))
                return None
        
        # Access Tracking
        entry.last_accessed = datetime.now()
        
        return entry.module_instance
    
    async def execute_module_function(self, module_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modulfunktion ausführen mit Performance-Tracking
        
        Args:
            module_name: Name des Moduls
            input_data: Input-Parameter
            
        Returns:
            Execution-Result mit Metadaten
        """
        start_time = datetime.now()
        self.total_module_calls += 1
        
        try:
            # Modul abrufen
            module = await self.get_module(module_name)
            if not module:
                self.failed_module_calls += 1
                return {
                    'success': False,
                    'error': f'Module {module_name} not available',
                    'execution_time': 0.0
                }
            
            # Funktion ausführen
            result = await module.process_business_logic(input_data)
            
            # Performance-Tracking
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(execution_time)
            
            # Event publishen
            if self.event_bus and self.event_bus.connected:
                await self._publish_module_execution_event(module_name, input_data, result, execution_time)
            
            return {
                **result,
                'module_name': module_name,
                'registry_execution_time': execution_time
            }
            
        except Exception as e:
            self.failed_module_calls += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.error(f"Module execution failed: {module_name}", 
                            error=str(e), execution_time=execution_time)
            
            return {
                'success': False,
                'error': str(e),
                'module_name': module_name,
                'execution_time': execution_time
            }
    
    async def get_module_group(self, group_name: str) -> List[SingleFunctionModule]:
        """
        Alle Module einer Gruppe abrufen
        
        Args:
            group_name: Name der Gruppe
            
        Returns:
            Liste der Module in der Gruppe
        """
        if group_name not in self.module_groups:
            return []
        
        modules = []
        for module_name in self.module_groups[group_name]:
            module = await self.get_module(module_name)
            if module:
                modules.append(module)
        
        return modules
    
    async def _auto_discover_modules(self):
        """Automatisches Entdecken von Modulen in konfigurierten Pfaden"""
        base_path = Path(__file__).parent
        
        for discovery_path in self.auto_discovery_paths:
            full_path = base_path / discovery_path
            
            if not full_path.exists():
                continue
            
            # Python-Dateien in Pfad finden
            python_files = list(full_path.glob('*_module.py'))
            
            for py_file in python_files:
                await self._discover_module_in_file(py_file, discovery_path)
    
    async def _discover_module_in_file(self, file_path: Path, group: str):
        """Modul aus einer Python-Datei entdecken und registrieren"""
        try:
            module_name = file_path.stem
            
            # Dynamischen Import durchführen
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # SingleFunctionModule-Klassen finden
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, SingleFunctionModule) and 
                    obj != SingleFunctionModule):
                    
                    # Spezielle Behandlung für OrderModule Single Function Modules
                    if group == 'order_modules':
                        # Spezifische Function Names für alle 18 OrderModule Funktionen
                        order_module_mappings = {
                            'OrderPlacementModule': 'order_placement',
                            'OrderValidationModule': 'order_validation',
                            'OrderExecutionModule': 'order_execution',
                            'OrderCancellationModule': 'order_cancellation',
                            'OrderStatusModule': 'order_status',
                            'OrderHistoryModule': 'order_history',
                            'ActiveOrdersModule': 'active_orders',
                            'OrderModificationModule': 'order_modification',
                            'OrderSimulationModule': 'order_simulation',
                            'OrderRiskAssessmentModule': 'order_risk_assessment',
                            'OrderIntelligenceHandlerModule': 'order_intelligence_handler',
                            'OrderMarketDataHandlerModule': 'order_market_data_handler',
                            'OrderSystemAlertHandlerModule': 'order_system_alert_handler',
                            'OrderConfigHandlerModule': 'order_config_handler',
                            'OrderDailyLimitModule': 'order_daily_limit'
                        }
                        
                        function_name = order_module_mappings.get(name)
                        if function_name:
                            await self.register_module(function_name, obj, group=group, auto_load=False)
                            self.logger.info(f"Auto-discovered OrderModule function: {function_name}", 
                                           file=str(file_path), class=name, group=group)
                        else:
                            # Fallback für neue Module
                            function_name = name.lower().replace('module', '').replace('_', '')
                            if function_name.endswith('_'):
                                function_name = function_name[:-1]
                            await self.register_module(function_name, obj, group=group, auto_load=False)
                            self.logger.info(f"Auto-discovered module with fallback naming: {function_name}", 
                                           file=str(file_path), class=name, group=group)
                    else:
                        # Standard-Behandlung für andere Gruppen
                        function_name = name.lower().replace('module', '').replace('_', '')
                        if function_name.endswith('_'):
                            function_name = function_name[:-1]
                        
                        await self.register_module(function_name, obj, group=group, auto_load=False)
                        self.logger.info(f"Auto-discovered module: {function_name}", 
                                       file=str(file_path), class=name, group=group)
                    
        except Exception as e:
            self.logger.error(f"Failed to discover module in {file_path}", error=str(e))
    
    async def _setup_event_subscriptions(self):
        """Event-Bus Subscriptions für Registry Management"""
        if not self.event_bus or not self.event_bus.connected:
            return
        
        # Module Performance Events
        await self.event_bus.subscribe(
            event_type="module_performance_request",
            handler=self._handle_performance_request
        )
        
        # Module Health Check Events
        await self.event_bus.subscribe(
            event_type="module_health_check",
            handler=self._handle_health_check
        )
    
    async def _publish_module_execution_event(self, module_name: str, input_data: Dict, 
                                            result: Dict, execution_time: float):
        """Module Execution Event publishen"""
        event = Event(
            event_type="module_executed",
            stream_id=f"registry-{module_name}-{int(datetime.now().timestamp())}",
            data={
                'module_name': module_name,
                'success': result.get('success', False),
                'execution_time': execution_time,
                'registry_stats': self.get_registry_statistics()
            },
            source="module_registry"
        )
        
        await self.event_bus.publish(event)
    
    async def _handle_performance_request(self, event):
        """Performance-Request Event Handler"""
        module_name = event.data.get('module_name')
        
        if module_name and module_name in self.modules:
            entry = self.modules[module_name]
            if entry.module_instance:
                performance_data = entry.module_instance.get_performance_metrics()
            else:
                performance_data = {'status': 'not_loaded'}
        else:
            performance_data = self.get_registry_statistics()
        
        # Response Event publishen
        response_event = Event(
            event_type="module_performance_response",
            stream_id=f"registry-perf-{int(datetime.now().timestamp())}",
            data=performance_data,
            source="module_registry"
        )
        
        await self.event_bus.publish(response_event)
    
    async def _handle_health_check(self, event):
        """Health Check Event Handler"""
        health_data = {
            'registry_status': 'healthy',
            'total_modules': len(self.modules),
            'loaded_modules': sum(1 for entry in self.modules.values() if entry.is_loaded),
            'module_groups': {group: len(modules) for group, modules in self.module_groups.items()},
            'performance_summary': self.get_registry_statistics()
        }
        
        # Health Response Event publishen
        response_event = Event(
            event_type="module_health_response",
            stream_id=f"registry-health-{int(datetime.now().timestamp())}",
            data=health_data,
            source="module_registry"
        )
        
        await self.event_bus.publish(response_event)
    
    def _update_performance_metrics(self, execution_time: float):
        """Registry Performance-Metriken aktualisieren"""
        if self.total_module_calls == 1:
            self.average_response_time = execution_time
        else:
            # Exponential Moving Average
            alpha = 0.1
            self.average_response_time = (alpha * execution_time + 
                                        (1 - alpha) * self.average_response_time)
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """Registry-Statistiken abrufen"""
        success_rate = 0.0
        if self.total_module_calls > 0:
            success_rate = (self.total_module_calls - self.failed_module_calls) / self.total_module_calls
        
        return {
            'total_modules': len(self.modules),
            'loaded_modules': sum(1 for entry in self.modules.values() if entry.is_loaded),
            'total_calls': self.total_module_calls,
            'failed_calls': self.failed_module_calls,
            'success_rate': success_rate,
            'average_response_time': self.average_response_time,
            'module_groups': {group: len(modules) for group, modules in self.module_groups.items()}
        }
    
    def get_module_list(self) -> List[Dict[str, Any]]:
        """Liste aller registrierten Module abrufen"""
        modules = []
        
        for module_name, entry in self.modules.items():
            module_info = {
                'name': module_name,
                'class': entry.module_class.__name__,
                'is_loaded': entry.is_loaded,
                'load_count': entry.load_count,
                'registration_time': entry.registration_time.isoformat(),
                'last_accessed': entry.last_accessed.isoformat() if entry.last_accessed else None
            }
            
            # Funktions-Info hinzufügen falls Modul geladen
            if entry.is_loaded and entry.module_instance:
                try:
                    function_info = entry.module_instance.get_function_info()
                    module_info['function_info'] = function_info
                except AttributeError as e:
                    self.logger.debug(f"Module {entry.name} does not have function info: {e}")
                except Exception as e:
                    self.logger.warning(f"Error getting function info for module {entry.name}: {e}")
            
            modules.append(module_info)
        
        return modules