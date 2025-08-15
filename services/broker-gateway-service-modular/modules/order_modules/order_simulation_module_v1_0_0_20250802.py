"""
Order Simulation Module - Single Function Module
Verantwortlich ausschließlich für Order Update Simulation Logic
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from decimal import Decimal
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderStatus, OrderSide, OrderType


class SimulationConfig(BaseModel):
    order_id: str
    simulation_duration_seconds: int = 300  # 5 minutes default
    update_interval_seconds: int = 30       # 30 seconds between updates
    fill_probability: float = 0.7           # 70% chance of eventual fill
    partial_fill_probability: float = 0.3   # 30% chance of partial fills
    price_volatility: float = 0.02          # 2% price volatility


class SimulationUpdate(BaseModel):
    order_id: str
    timestamp: datetime
    status: OrderStatus
    filled_amount: str
    remaining_amount: str
    average_price: Optional[str] = None
    last_fill_amount: Optional[str] = None
    last_fill_price: Optional[str] = None
    simulation_progress: float  # 0.0 to 1.0


class OrderSimulationModule(SingleFunctionModule):
    """
    Single Function Module: Order Simulation
    Verantwortlichkeit: Ausschließlich Order-Update-Simulation-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_simulation", event_bus)
        
        # Active Simulations Tracking
        self.active_simulations = {}
        self.simulation_tasks = {}
        self.simulation_history = {}
        self.simulation_counter = 0
        
        # Market Price Simulation
        self.market_prices = {
            'BTC_EUR': Decimal('45000'),
            'ETH_EUR': Decimal('2500'),
            'ADA_EUR': Decimal('0.50'),
            'DOT_EUR': Decimal('25.00')
        }
        
        # Simulation Parameters
        self.min_fill_amount = Decimal('0.001')
        self.max_fill_percentage_per_update = 0.3  # Max 30% fill per update
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order Simulation
        
        Args:
            input_data: {
                'simulation_config': SimulationConfig dict,
                'order_data': current order information,
                'action': 'start', 'stop', 'get_status', 'get_updates'
            }
            
        Returns:
            Dict mit Simulation-Result
        """
        action = input_data.get('action', 'start')
        
        if action == 'start':
            return await self._start_order_simulation(input_data)
        elif action == 'stop':
            return await self._stop_order_simulation(input_data)
        elif action == 'get_status':
            return await self._get_simulation_status(input_data)
        elif action == 'get_updates':
            return await self._get_simulation_updates(input_data)
        else:
            raise ValueError(f'Unknown simulation action: {action}')
    
    async def _start_order_simulation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Startet Order-Update-Simulation"""
        simulation_config_data = input_data.get('simulation_config')
        order_data = input_data.get('order_data')
        
        if not simulation_config_data:
            raise ValueError('No simulation config provided')
        
        if not order_data:
            raise ValueError('No order data provided')
        
        # SimulationConfig parsieren
        try:
            simulation_config = SimulationConfig(**simulation_config_data)
        except Exception as e:
            raise ValueError(f'Invalid simulation config format: {str(e)}')
        
        order_id = simulation_config.order_id
        
        # Prüfen ob bereits Simulation läuft
        if order_id in self.active_simulations:
            return {
                'success': False,
                'error': f'Simulation for order {order_id} is already running',
                'existing_simulation_id': self.active_simulations[order_id]['simulation_id']
            }
        
        # Simulation starten
        simulation_id = await self._initialize_simulation(simulation_config, order_data)
        
        return {
            'success': True,
            'simulation_id': simulation_id,
            'order_id': order_id,
            'duration_seconds': simulation_config.simulation_duration_seconds,
            'update_interval_seconds': simulation_config.update_interval_seconds,
            'started_at': datetime.now().isoformat()
        }
    
    async def _initialize_simulation(self, simulation_config: SimulationConfig, 
                                   order_data: Dict[str, Any]) -> str:
        """Initialisiert neue Order Simulation"""
        self.simulation_counter += 1
        simulation_id = f"SIM-{int(time.time())}-{self.simulation_counter:04d}"
        order_id = simulation_config.order_id
        
        # Simulation State erstellen
        simulation_state = {
            'simulation_id': simulation_id,
            'config': simulation_config,
            'order_data': order_data,
            'started_at': datetime.now(),
            'updates': [],
            'current_status': OrderStatus(order_data['status']),
            'current_filled_amount': Decimal(order_data.get('filled_amount', '0')),
            'total_amount': Decimal(order_data['original_amount']),
            'is_active': True,
            'completion_progress': 0.0
        }
        
        # Registrieren
        self.active_simulations[order_id] = simulation_state
        
        # Simulation Task starten
        task = asyncio.create_task(self._run_simulation_loop(simulation_state))
        self.simulation_tasks[simulation_id] = task
        
        self.logger.info(f"Started order simulation",
                       simulation_id=simulation_id,
                       order_id=order_id,
                       duration_seconds=simulation_config.simulation_duration_seconds)
        
        return simulation_id
    
    async def _run_simulation_loop(self, simulation_state: Dict[str, Any]):
        """Hauptloop für Order Simulation"""
        config = simulation_state['config']
        start_time = simulation_state['started_at']
        order_id = config.order_id
        
        try:
            while simulation_state['is_active']:
                # Zeit-Check
                elapsed_seconds = (datetime.now() - start_time).total_seconds()
                if elapsed_seconds >= config.simulation_duration_seconds:
                    await self._finalize_simulation(simulation_state, 'timeout')
                    break
                
                # Progress berechnen
                progress = min(elapsed_seconds / config.simulation_duration_seconds, 1.0)
                simulation_state['completion_progress'] = progress
                
                # Order Update simulieren
                update = await self._generate_simulation_update(simulation_state, progress)
                
                if update:
                    simulation_state['updates'].append(update)
                    simulation_state['current_status'] = update.status
                    simulation_state['current_filled_amount'] = Decimal(update.filled_amount)
                    
                    # Event publishen falls Event-Bus verfügbar
                    if self.event_bus and self.event_bus.connected:
                        await self._publish_simulation_update_event(update)
                    
                    # Check ob Order komplett gefüllt
                    if update.status == OrderStatus.FILLED:
                        await self._finalize_simulation(simulation_state, 'filled')
                        break
                
                # Warten bis nächstes Update
                await asyncio.sleep(config.update_interval_seconds)
                
        except asyncio.CancelledError:
            self.logger.info(f"Simulation cancelled for order {order_id}")
            await self._finalize_simulation(simulation_state, 'cancelled')
        except Exception as e:
            self.logger.error(f"Simulation error for order {order_id}", error=str(e))
            await self._finalize_simulation(simulation_state, 'error')
    
    async def _generate_simulation_update(self, simulation_state: Dict[str, Any], 
                                        progress: float) -> Optional[SimulationUpdate]:
        """Generiert realistisches Order Update"""
        import random
        
        config = simulation_state['config']
        order_data = simulation_state['order_data']
        current_filled = simulation_state['current_filled_amount']
        total_amount = simulation_state['total_amount']
        remaining_amount = total_amount - current_filled
        
        # Keine Updates wenn Order bereits gefüllt
        if current_filled >= total_amount:
            return None
        
        # Fill-Wahrscheinlichkeit basierend auf Progress und Config
        base_fill_probability = config.fill_probability * progress
        
        # Random Fill-Entscheidung
        if random.random() > base_fill_probability * 2:  # *2 für häufigere Updates
            return None  # Kein Update dieses Mal
        
        # Fill Amount berechnen
        max_fill_this_update = remaining_amount * Decimal(str(self.max_fill_percentage_per_update))
        min_fill = min(self.min_fill_amount, remaining_amount)
        
        # Random Fill Amount
        fill_amount_float = random.uniform(float(min_fill), float(max_fill_this_update))
        fill_amount = Decimal(str(fill_amount_float)).quantize(Decimal('0.00000001'))
        
        # Nicht über Remaining hinaus füllen
        fill_amount = min(fill_amount, remaining_amount)
        
        new_filled_amount = current_filled + fill_amount
        new_remaining = total_amount - new_filled_amount
        
        # Status bestimmen
        if new_filled_amount >= total_amount:
            new_status = OrderStatus.FILLED
            new_remaining = Decimal('0')
        elif new_filled_amount > current_filled:
            new_status = OrderStatus.PARTIALLY_FILLED
        else:
            new_status = simulation_state['current_status']
        
        # Fill Price simulieren
        fill_price = await self._simulate_fill_price(order_data, fill_amount)
        
        # Average Price aktualisieren
        average_price = await self._calculate_new_average_price(
            simulation_state, fill_amount, fill_price
        )
        
        update = SimulationUpdate(
            order_id=config.order_id,
            timestamp=datetime.now(),
            status=new_status,
            filled_amount=str(new_filled_amount),
            remaining_amount=str(new_remaining),
            average_price=str(average_price),
            last_fill_amount=str(fill_amount),
            last_fill_price=str(fill_price),
            simulation_progress=progress
        )
        
        return update
    
    async def _simulate_fill_price(self, order_data: Dict[str, Any], fill_amount: Decimal) -> Decimal:
        """Simuliert realistischen Fill-Preis"""
        import random
        
        instrument = order_data['instrument_code']
        order_type = OrderType(order_data['type'])
        side = OrderSide(order_data['side'])
        
        # Base Market Price
        base_price = self.market_prices.get(instrument, Decimal('1000'))
        
        # Market Order: Slippage simulieren
        if order_type == OrderType.MARKET:
            # Slippage basierend auf Fill-Größe
            slippage_factor = min(float(fill_amount) / 10.0, 0.002)  # Max 0.2% slippage
            
            if side == OrderSide.BUY:
                fill_price = base_price * (Decimal('1.0') + Decimal(str(slippage_factor)))
            else:
                fill_price = base_price * (Decimal('1.0') - Decimal(str(slippage_factor)))
        
        # Limit Order: Order Price oder besser
        elif order_type == OrderType.LIMIT:
            order_price = Decimal(order_data['price'])
            
            # 80% Chance auf exakt Order Price, 20% auf besseren Preis
            if random.random() < 0.8:
                fill_price = order_price
            else:
                # Besserer Preis (0.1-0.5% improvement)
                improvement_factor = random.uniform(0.001, 0.005)
                if side == OrderSide.BUY:
                    fill_price = order_price * (Decimal('1.0') - Decimal(str(improvement_factor)))
                else:
                    fill_price = order_price * (Decimal('1.0') + Decimal(str(improvement_factor)))
        
        # Other order types
        else:
            fill_price = base_price
        
        return fill_price.quantize(Decimal('0.01'))
    
    async def _calculate_new_average_price(self, simulation_state: Dict[str, Any], 
                                         fill_amount: Decimal, fill_price: Decimal) -> Decimal:
        """Berechnet neuen Average Price nach Fill"""
        updates = simulation_state['updates']
        current_filled = simulation_state['current_filled_amount']
        
        if not updates or current_filled == Decimal('0'):
            return fill_price
        
        # Bisherigen Average Price und Total Value berechnen
        total_value = Decimal('0')
        total_filled = Decimal('0')
        
        for update in updates:
            if update.last_fill_amount and update.last_fill_price:
                fill_amt = Decimal(update.last_fill_amount)
                fill_prc = Decimal(update.last_fill_price)
                total_value += fill_amt * fill_prc
                total_filled += fill_amt
        
        # Neuen Fill hinzufügen
        total_value += fill_amount * fill_price
        total_filled += fill_amount
        
        if total_filled > Decimal('0'):
            new_average = total_value / total_filled
            return new_average.quantize(Decimal('0.01'))
        
        return fill_price
    
    async def _finalize_simulation(self, simulation_state: Dict[str, Any], reason: str):
        """Finalisiert Simulation"""
        simulation_id = simulation_state['simulation_id']
        order_id = simulation_state['config'].order_id
        
        simulation_state['is_active'] = False
        simulation_state['completed_at'] = datetime.now()
        simulation_state['completion_reason'] = reason
        
        # Aus active_simulations entfernen
        if order_id in self.active_simulations:
            del self.active_simulations[order_id]
        
        # Task cleanup
        if simulation_id in self.simulation_tasks:
            del self.simulation_tasks[simulation_id]
        
        # In History verschieben
        self.simulation_history[simulation_id] = simulation_state
        
        self.logger.info(f"Simulation finalized",
                       simulation_id=simulation_id,
                       order_id=order_id,
                       reason=reason,
                       updates_generated=len(simulation_state['updates']))
    
    async def _stop_order_simulation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Stoppt laufende Order Simulation"""
        order_id = input_data.get('order_id')
        
        if not order_id:
            raise ValueError('No order_id provided for simulation stop')
        
        if order_id not in self.active_simulations:
            return {
                'success': False,
                'error': f'No active simulation found for order {order_id}'
            }
        
        simulation_state = self.active_simulations[order_id]
        simulation_id = simulation_state['simulation_id']
        
        # Task cancellen
        if simulation_id in self.simulation_tasks:
            self.simulation_tasks[simulation_id].cancel()
        
        return {
            'success': True,
            'simulation_id': simulation_id,
            'order_id': order_id,
            'stopped_at': datetime.now().isoformat(),
            'updates_generated': len(simulation_state['updates'])
        }
    
    async def _get_simulation_status(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gibt Simulation Status zurück"""
        order_id = input_data.get('order_id')
        
        if not order_id:
            raise ValueError('No order_id provided for status check')
        
        if order_id in self.active_simulations:
            simulation_state = self.active_simulations[order_id]
            return {
                'order_id': order_id,
                'simulation_id': simulation_state['simulation_id'],
                'is_active': True,
                'started_at': simulation_state['started_at'].isoformat(),
                'completion_progress': simulation_state['completion_progress'],
                'current_status': simulation_state['current_status'].value,
                'updates_count': len(simulation_state['updates']),
                'current_filled_amount': str(simulation_state['current_filled_amount'])
            }
        
        # Suche in History
        for sim_state in self.simulation_history.values():
            if sim_state['config'].order_id == order_id:
                return {
                    'order_id': order_id,
                    'simulation_id': sim_state['simulation_id'],
                    'is_active': False,
                    'started_at': sim_state['started_at'].isoformat(),
                    'completed_at': sim_state.get('completed_at', datetime.now()).isoformat(),
                    'completion_reason': sim_state.get('completion_reason', 'unknown'),
                    'updates_count': len(sim_state['updates']),
                    'final_filled_amount': str(sim_state['current_filled_amount'])
                }
        
        return {
            'success': False,
            'error': f'No simulation found for order {order_id}'
        }
    
    async def _get_simulation_updates(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gibt Simulation Updates zurück"""
        order_id = input_data.get('order_id')
        limit = input_data.get('limit', 50)
        
        if not order_id:
            raise ValueError('No order_id provided for updates retrieval')
        
        updates = []
        
        # Active Simulation Check
        if order_id in self.active_simulations:
            simulation_state = self.active_simulations[order_id]
            updates = simulation_state['updates']
        else:
            # History Check
            for sim_state in self.simulation_history.values():
                if sim_state['config'].order_id == order_id:
                    updates = sim_state['updates']
                    break
        
        # Serialize Updates
        serialized_updates = []
        for update in updates[-limit:]:  # Last N updates
            serialized_updates.append({
                'order_id': update.order_id,
                'timestamp': update.timestamp.isoformat(),
                'status': update.status.value,
                'filled_amount': update.filled_amount,
                'remaining_amount': update.remaining_amount,
                'average_price': update.average_price,
                'last_fill_amount': update.last_fill_amount,
                'last_fill_price': update.last_fill_price,
                'simulation_progress': update.simulation_progress
            })
        
        return {
            'order_id': order_id,
            'updates': serialized_updates,
            'total_updates': len(updates),
            'returned_count': len(serialized_updates)
        }
    
    async def _publish_simulation_update_event(self, update: SimulationUpdate):
        """Publisht Simulation Update Event über Event-Bus"""
        from event_bus import Event
        
        event = Event(
            event_type="order_simulation_update",
            stream_id=f"order-sim-{update.order_id}-{int(update.timestamp.timestamp())}",
            data={
                'order_id': update.order_id,
                'status': update.status.value,
                'filled_amount': update.filled_amount,
                'remaining_amount': update.remaining_amount,
                'average_price': update.average_price,
                'last_fill_amount': update.last_fill_amount,
                'last_fill_price': update.last_fill_price,
                'simulation_progress': update.simulation_progress,
                'timestamp': update.timestamp.isoformat()
            },
            source="order_simulation_module"
        )
        
        await self.event_bus.publish(event)
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_simulation',
            'description': 'Simulates realistic order updates and fills over time',
            'responsibility': 'Order update simulation logic only',
            'input_parameters': {
                'simulation_config': 'SimulationConfig object with simulation parameters',
                'order_data': 'Current order information to simulate',
                'action': 'Action to perform (start, stop, get_status, get_updates)'
            },
            'output_format': {
                'simulation_id': 'Unique simulation identifier',
                'order_id': 'Order being simulated',
                'updates': 'List of generated order updates',
                'status': 'Current simulation status'
            },
            'actions': ['start', 'stop', 'get_status', 'get_updates'],
            'simulation_parameters': {
                'duration_seconds': 'How long to run simulation',
                'update_interval_seconds': 'Time between updates',
                'fill_probability': 'Probability of order filling',
                'partial_fill_probability': 'Probability of partial fills',
                'price_volatility': 'Market price volatility factor'
            },
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_simulation_statistics(self) -> Dict[str, Any]:
        """Simulation Statistiken abrufen"""
        active_count = len(self.active_simulations)
        history_count = len(self.simulation_history)
        total_simulations = self.simulation_counter
        
        return {
            'total_simulations_started': total_simulations,
            'active_simulations': active_count,
            'completed_simulations': history_count,
            'average_response_time': self.average_execution_time,
            'simulation_parameters': {
                'min_fill_amount': str(self.min_fill_amount),
                'max_fill_percentage_per_update': self.max_fill_percentage_per_update
            }

    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions for Order Module"""
        try:
            # Subscribe to system health requests
            await self.event_bus.subscribe('system.health.request', self.process_event)
            
            # Subscribe to module-specific order events
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('order.status.request', self.process_event)
            await self.event_bus.subscribe('order.update', self.process_event)
            
            self.logger.info("Event subscriptions setup completed",
                           module=self.module_name)
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions",
                            error=str(e), module=self.module_name)

    async def process_event(self, event):
        """Process incoming events"""
        try:
            event_type = event.get('event_type', '')
            
            if event_type == 'system.health.request':
                # Health check response
                health_response = {
                    'event_type': 'system.health.response',
                    'stream_id': 'health-check',
                    'data': {
                        'module_name': self.module_name,
                        'status': 'healthy',
                        'execution_count': len(self.execution_history),
                        'average_execution_time_ms': self.average_execution_time,
                        'orders_processed': getattr(self, 'orders_processed', 0),
                        'health_check_timestamp': datetime.now().isoformat()
                    },
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(health_response)
                
            elif event_type == f'{self.module_name}.request':
                # Module-specific request
                event_data = event.get('data', {})
                result = await self.execute_function(event_data)
                
                response_event = {
                    'event_type': f'{self.module_name}.response',
                    'stream_id': event.get('stream_id', f'{self.module_name}-request'),
                    'data': result,
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(response_event)
            
            elif event_type == 'order.status.request':
                # Order status request
                order_id = event.get('data', {}).get('order_id')
                if order_id and hasattr(self, 'get_order_status'):
                    status = self.get_order_status(order_id)
                    status_response = {
                        'event_type': 'order.status.response',
                        'stream_id': event.get('stream_id', 'order-status'),
                        'data': {
                            'order_id': order_id,
                            'status': status,
                            'module': self.module_name
                        },
                        'source': self.module_name,
                        'correlation_id': event.get('correlation_id')
                    }
                    await self.event_bus.publish(status_response)
            
            else:
                self.logger.debug("Unhandled event type",
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)

    async def publish_order_event(self, event_type: str, order_data: dict):
        """Publish order-related events"""
        if not self.event_bus:
            return
            
        try:
            order_event = {
                'event_type': event_type,
                'stream_id': f'order-{order_data.get("order_id", "unknown")}',
                'data': {
                    **order_data,
                    'timestamp': datetime.now().isoformat(),
                    'processing_module': self.module_name
                },
                'source': self.module_name
            }
            await self.event_bus.publish(order_event)
            
        except Exception as e:
            self.logger.error("Failed to publish order event",
                            error=str(e), event_type=event_type)
        }