"""
Order Intelligence Handler Module - Single Function Module
Verantwortlich ausschließlich für Intelligence Event Handling Logic
"""

import asyncio
from typing import Dict, Any, List, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderSide, OrderType


class IntelligenceSignal(BaseModel):
    signal_id: str
    signal_type: str  # 'buy', 'sell', 'hold', 'risk_alert'
    instrument_code: str
    confidence_score: float  # 0.0 to 1.0
    signal_strength: str  # 'weak', 'moderate', 'strong'
    recommendation: Dict[str, Any]
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = {}


class IntelligenceResponse(BaseModel):
    signal_id: str
    action_taken: str  # 'order_created', 'order_modified', 'order_cancelled', 'no_action', 'risk_escalation'
    order_id: Optional[str] = None
    reasoning: str
    confidence_used: float
    processing_time: float
    response_timestamp: datetime


class OrderIntelligenceHandlerModule(SingleFunctionModule):
    """
    Single Function Module: Order Intelligence Handler
    Verantwortlichkeit: Ausschließlich Intelligence-Event-Handling-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_intelligence_handler", event_bus)
        
        # Intelligence Processing History
        self.processed_signals = {}
        self.intelligence_responses = {}
        self.signal_counter = 0
        
        # Intelligence Processing Rules
        self.confidence_thresholds = {
            'min_action_confidence': 0.6,    # Minimum confidence for any action
            'auto_order_confidence': 0.8,    # Auto order creation threshold
            'risk_alert_confidence': 0.5,    # Risk alert threshold
            'strong_signal_confidence': 0.9  # Strong signal threshold
        }
        
        # Signal Type Handlers
        self.signal_handlers = {
            'buy_signal': self._handle_buy_signal,
            'sell_signal': self._handle_sell_signal,
            'hold_signal': self._handle_hold_signal,
            'risk_alert': self._handle_risk_alert,
            'trend_change': self._handle_trend_change,
            'volatility_spike': self._handle_volatility_spike,
            'liquidity_warning': self._handle_liquidity_warning
        }
        
        # Auto-Trading Settings (für Demo - normalerweise konfigurierbar)
        self.auto_trading_enabled = False
        self.max_auto_order_value = 1000.0  # Max €1k per auto order
        self.daily_auto_limit = 5000.0      # Max €5k daily auto trading
        self.current_daily_auto_total = 0.0
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Intelligence Event Handling
        
        Args:
            input_data: {
                'event': intelligence event data,
                'current_orders': optional current order information,
                'account_settings': optional account configuration
            }
            
        Returns:
            Dict mit Intelligence-Response
        """
        event_data = input_data.get('event')
        current_orders = input_data.get('current_orders', [])
        account_settings = input_data.get('account_settings', {})
        
        if not event_data:
            raise ValueError('No intelligence event provided')
        
        # Intelligence Signal aus Event extrahieren
        intelligence_signal = await self._extract_intelligence_signal(event_data)
        
        # Signal verarbeiten
        intelligence_response = await self._process_intelligence_signal(
            intelligence_signal, current_orders, account_settings
        )
        
        # Response in History speichern
        self.intelligence_responses[intelligence_response.signal_id] = intelligence_response
        
        return {
            'signal_id': intelligence_response.signal_id,
            'action_taken': intelligence_response.action_taken,
            'order_id': intelligence_response.order_id,
            'reasoning': intelligence_response.reasoning,
            'confidence_used': intelligence_response.confidence_used,
            'processing_time': intelligence_response.processing_time,
            'response_timestamp': intelligence_response.response_timestamp.isoformat()
        }
    
    async def _extract_intelligence_signal(self, event_data: Dict[str, Any]) -> IntelligenceSignal:
        """Extrahiert Intelligence Signal aus Event Data"""
        self.signal_counter += 1
        
        # Event Data parsen
        signal_data = event_data.get('data', {})
        
        # Signal ID generieren falls nicht vorhanden
        signal_id = signal_data.get('signal_id', f"INTEL-{int(datetime.now().timestamp())}-{self.signal_counter:04d}")
        
        intelligence_signal = IntelligenceSignal(
            signal_id=signal_id,
            signal_type=signal_data.get('signal_type', 'unknown'),
            instrument_code=signal_data.get('instrument_code', 'UNKNOWN'),
            confidence_score=float(signal_data.get('confidence_score', 0.5)),
            signal_strength=signal_data.get('signal_strength', 'moderate'),
            recommendation=signal_data.get('recommendation', {}),
            timestamp=datetime.fromisoformat(signal_data.get('timestamp', datetime.now().isoformat())),
            source=signal_data.get('source', 'intelligence_service'),
            metadata=signal_data.get('metadata', {})
        )
        
        # Signal in Processing History speichern
        self.processed_signals[signal_id] = intelligence_signal
        
        return intelligence_signal
    
    async def _process_intelligence_signal(self, intelligence_signal: IntelligenceSignal,
                                         current_orders: List[Dict],
                                         account_settings: Dict[str, Any]) -> IntelligenceResponse:
        """Verarbeitet Intelligence Signal und bestimmt Action"""
        start_time = datetime.now()
        signal_id = intelligence_signal.signal_id
        
        # Confidence Check
        if intelligence_signal.confidence_score < self.confidence_thresholds['min_action_confidence']:
            return IntelligenceResponse(
                signal_id=signal_id,
                action_taken="no_action",
                reasoning=f"Confidence too low: {intelligence_signal.confidence_score:.2f} < {self.confidence_thresholds['min_action_confidence']}",
                confidence_used=intelligence_signal.confidence_score,
                processing_time=(datetime.now() - start_time).total_seconds(),
                response_timestamp=datetime.now()
            )
        
        # Signal Type Handler auswählen
        handler = self.signal_handlers.get(intelligence_signal.signal_type, self._handle_unknown_signal)
        
        # Signal verarbeiten
        try:
            response = await handler(intelligence_signal, current_orders, account_settings)
            response.processing_time = (datetime.now() - start_time).total_seconds()
            response.response_timestamp = datetime.now()
            
            self.logger.info(f"Intelligence signal processed",
                           signal_id=signal_id,
                           signal_type=intelligence_signal.signal_type,
                           action_taken=response.action_taken,
                           confidence=intelligence_signal.confidence_score)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing intelligence signal",
                            signal_id=signal_id,
                            error=str(e))
            
            return IntelligenceResponse(
                signal_id=signal_id,
                action_taken="error",
                reasoning=f"Processing error: {str(e)}",
                confidence_used=intelligence_signal.confidence_score,
                processing_time=(datetime.now() - start_time).total_seconds(),
                response_timestamp=datetime.now()
            )
    
    async def _handle_buy_signal(self, signal: IntelligenceSignal, current_orders: List,
                               account_settings: Dict) -> IntelligenceResponse:
        """Behandelt Buy Signal"""
        
        # Prüfe ob bereits offene Buy Order für dieses Instrument existiert
        existing_buy_orders = [
            order for order in current_orders 
            if (order.get('instrument_code') == signal.instrument_code and 
                order.get('side') == 'BUY' and
                order.get('status') in ['OPEN', 'PARTIALLY_FILLED'])
        ]
        
        if existing_buy_orders:
            return IntelligenceResponse(
                signal_id=signal.signal_id,
                action_taken="no_action",
                reasoning=f"Buy order already exists for {signal.instrument_code}",
                confidence_used=signal.confidence_score
            )
        
        # Auto-Trading Check
        if (self.auto_trading_enabled and 
            signal.confidence_score >= self.confidence_thresholds['auto_order_confidence']):
            
            # Auto Order Parameter bestimmen
            order_value = min(
                signal.recommendation.get('order_value', 500.0),
                self.max_auto_order_value
            )
            
            # Daily Limit Check
            if self.current_daily_auto_total + order_value > self.daily_auto_limit:
                return IntelligenceResponse(
                    signal_id=signal.signal_id,
                    action_taken="no_action",
                    reasoning="Daily auto-trading limit reached",
                    confidence_used=signal.confidence_score
                )
            
            # Simuliere Order Creation (in Produktion: echter Order Creation Call)
            order_id = await self._simulate_order_creation({
                'instrument_code': signal.instrument_code,
                'side': 'BUY',
                'type': 'MARKET',
                'amount': str(order_value / 45000),  # Beispiel für BTC
                'reason': f"Auto-buy based on intelligence signal {signal.signal_id}"
            })
            
            self.current_daily_auto_total += order_value
            
            return IntelligenceResponse(
                signal_id=signal.signal_id,
                action_taken="order_created",
                order_id=order_id,
                reasoning=f"Auto buy order created based on high confidence signal ({signal.confidence_score:.2f})",
                confidence_used=signal.confidence_score
            )
        
        # Manual Action Recommendation
        return IntelligenceResponse(
            signal_id=signal.signal_id,
            action_taken="no_action",
            reasoning=f"Buy signal detected - manual review recommended (confidence: {signal.confidence_score:.2f})",
            confidence_used=signal.confidence_score
        )
    
    async def _handle_sell_signal(self, signal: IntelligenceSignal, current_orders: List,
                                account_settings: Dict) -> IntelligenceResponse:
        """Behandelt Sell Signal"""
        
        # Prüfe bestehende Buy Orders zum Schutz
        existing_buy_orders = [
            order for order in current_orders 
            if (order.get('instrument_code') == signal.instrument_code and 
                order.get('side') == 'BUY' and
                order.get('status') in ['OPEN', 'PARTIALLY_FILLED'])
        ]
        
        # High Confidence Sell Signal -> Cancel Buy Orders
        if (existing_buy_orders and 
            signal.confidence_score >= self.confidence_thresholds['strong_signal_confidence']):
            
            # Simuliere Order Cancellation
            cancelled_orders = []
            for order in existing_buy_orders:
                cancel_result = await self._simulate_order_cancellation(order['order_id'])
                cancelled_orders.append(order['order_id'])
            
            return IntelligenceResponse(
                signal_id=signal.signal_id,
                action_taken="order_cancelled",
                reasoning=f"Cancelled {len(cancelled_orders)} buy orders due to strong sell signal",
                confidence_used=signal.confidence_score
            )
        
        # Regular Sell Signal Processing
        return IntelligenceResponse(
            signal_id=signal.signal_id,
            action_taken="no_action",
            reasoning=f"Sell signal detected - position review recommended (confidence: {signal.confidence_score:.2f})",
            confidence_used=signal.confidence_score
        )
    
    async def _handle_hold_signal(self, signal: IntelligenceSignal, current_orders: List,
                                account_settings: Dict) -> IntelligenceResponse:
        """Behandelt Hold Signal"""
        
        return IntelligenceResponse(
            signal_id=signal.signal_id,
            action_taken="no_action",
            reasoning=f"Hold signal - maintain current positions (confidence: {signal.confidence_score:.2f})",
            confidence_used=signal.confidence_score
        )
    
    async def _handle_risk_alert(self, signal: IntelligenceSignal, current_orders: List,
                               account_settings: Dict) -> IntelligenceResponse:
        """Behandelt Risk Alert"""
        
        if signal.confidence_score >= self.confidence_thresholds['risk_alert_confidence']:
            # Risk Escalation - alle Orders für dieses Instrument prüfen
            risky_orders = [
                order for order in current_orders 
                if order.get('instrument_code') == signal.instrument_code
            ]
            
            if risky_orders:
                # Risk Event über Event-Bus publishen
                if self.event_bus and self.event_bus.connected:
                    await self._publish_risk_alert_event(signal, risky_orders)
                
                return IntelligenceResponse(
                    signal_id=signal.signal_id,
                    action_taken="risk_escalation",
                    reasoning=f"Risk alert escalated for {len(risky_orders)} orders in {signal.instrument_code}",
                    confidence_used=signal.confidence_score
                )
        
        return IntelligenceResponse(
            signal_id=signal.signal_id,
            action_taken="no_action",
            reasoning=f"Risk alert noted - monitoring increased (confidence: {signal.confidence_score:.2f})",
            confidence_used=signal.confidence_score
        )
    
    async def _handle_trend_change(self, signal: IntelligenceSignal, current_orders: List,
                                 account_settings: Dict) -> IntelligenceResponse:
        """Behandelt Trend Change Signal"""
        
        trend_direction = signal.metadata.get('trend_direction', 'unknown')
        
        # Starker Trend Change -> Order Review
        if signal.confidence_score >= 0.8:
            affected_orders = [
                order for order in current_orders 
                if order.get('instrument_code') == signal.instrument_code
            ]
            
            return IntelligenceResponse(
                signal_id=signal.signal_id,
                action_taken="no_action",
                reasoning=f"Strong trend change to {trend_direction} - review {len(affected_orders)} orders",
                confidence_used=signal.confidence_score
            )
        
        return IntelligenceResponse(
            signal_id=signal.signal_id,
            action_taken="no_action",
            reasoning=f"Trend change to {trend_direction} noted (confidence: {signal.confidence_score:.2f})",
            confidence_used=signal.confidence_score
        )
    
    async def _handle_volatility_spike(self, signal: IntelligenceSignal, current_orders: List,
                                     account_settings: Dict) -> IntelligenceResponse:
        """Behandelt Volatility Spike"""
        
        volatility_level = signal.metadata.get('volatility_level', 'unknown')
        
        if signal.confidence_score >= 0.7:
            # Hohe Volatilität -> Market Orders vermeiden
            market_orders = [
                order for order in current_orders 
                if (order.get('instrument_code') == signal.instrument_code and
                    order.get('type') == 'MARKET' and
                    order.get('status') == 'OPEN')
            ]
            
            if market_orders:
                return IntelligenceResponse(
                    signal_id=signal.signal_id,
                    action_taken="no_action",
                    reasoning=f"High volatility detected - review {len(market_orders)} market orders",
                    confidence_used=signal.confidence_score
                )
        
        return IntelligenceResponse(
            signal_id=signal.signal_id,
            action_taken="no_action",
            reasoning=f"Volatility spike ({volatility_level}) noted (confidence: {signal.confidence_score:.2f})",
            confidence_used=signal.confidence_score
        )
    
    async def _handle_liquidity_warning(self, signal: IntelligenceSignal, current_orders: List,
                                      account_settings: Dict) -> IntelligenceResponse:
        """Behandelt Liquidity Warning"""
        
        liquidity_level = signal.metadata.get('liquidity_level', 'unknown')
        
        # Liquiditäts-Problem -> Große Orders überprüfen
        large_orders = [
            order for order in current_orders 
            if (order.get('instrument_code') == signal.instrument_code and
                float(order.get('amount', '0')) * 45000 > 10000)  # > €10k orders
        ]
        
        if large_orders:
            return IntelligenceResponse(
                signal_id=signal.signal_id,
                action_taken="no_action",
                reasoning=f"Low liquidity warning - review {len(large_orders)} large orders",
                confidence_used=signal.confidence_score
            )
        
        return IntelligenceResponse(
            signal_id=signal.signal_id,
            action_taken="no_action",
            reasoning=f"Liquidity warning ({liquidity_level}) noted (confidence: {signal.confidence_score:.2f})",
            confidence_used=signal.confidence_score
        )
    
    async def _handle_unknown_signal(self, signal: IntelligenceSignal, current_orders: List,
                                   account_settings: Dict) -> IntelligenceResponse:
        """Behandelt Unknown Signal Type"""
        
        return IntelligenceResponse(
            signal_id=signal.signal_id,
            action_taken="no_action",
            reasoning=f"Unknown signal type '{signal.signal_type}' - logged for review",
            confidence_used=signal.confidence_score
        )
    
    async def _simulate_order_creation(self, order_params: Dict[str, Any]) -> str:
        """Simuliert Order Creation (in Produktion: echter API Call)"""
        import time
        order_id = f"AUTO-{int(time.time())}-{len(self.intelligence_responses):04d}"
        
        self.logger.info(f"Simulated auto order creation",
                       order_id=order_id,
                       params=order_params)
        
        return order_id
    
    async def _simulate_order_cancellation(self, order_id: str) -> bool:
        """Simuliert Order Cancellation"""
        self.logger.info(f"Simulated order cancellation", order_id=order_id)
        return True
    
    async def _publish_risk_alert_event(self, signal: IntelligenceSignal, affected_orders: List):
        """Publisht Risk Alert Event über Event-Bus"""
        from event_bus import Event
        
        event = Event(
            event_type="order_risk_alert",
            stream_id=f"risk-alert-{signal.signal_id}",
            data={
                'signal_id': signal.signal_id,
                'instrument_code': signal.instrument_code,
                'confidence_score': signal.confidence_score,
                'affected_orders_count': len(affected_orders),
                'affected_order_ids': [order.get('order_id') for order in affected_orders],
                'risk_details': signal.metadata,
                'timestamp': datetime.now().isoformat()
            },
            source="order_intelligence_handler"
        )
        
        await self.event_bus.publish(event)
    
    def configure_auto_trading(self, enabled: bool, max_order_value: float = None,
                             daily_limit: float = None):
        """Konfiguriert Auto-Trading Settings"""
        self.auto_trading_enabled = enabled
        if max_order_value is not None:
            self.max_auto_order_value = max_order_value
        if daily_limit is not None:
            self.daily_auto_limit = daily_limit
        
        self.logger.info(f"Auto-trading configured",
                       enabled=enabled,
                       max_order_value=self.max_auto_order_value,
                       daily_limit=self.daily_auto_limit)
    
    def reset_daily_auto_total(self):
        """Setzt Daily Auto Total zurück (normalerweise täglich um Mitternacht)"""
        self.current_daily_auto_total = 0.0
        self.logger.info("Daily auto-trading total reset")
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_intelligence_handler',
            'description': 'Processes intelligence signals and takes appropriate order actions',
            'responsibility': 'Intelligence event handling and order decision logic only',
            'input_parameters': {
                'event': 'Intelligence event with signal data',
                'current_orders': 'Optional list of current orders',
                'account_settings': 'Optional account configuration'
            },
            'output_format': {
                'signal_id': 'Processed signal identifier',
                'action_taken': 'Action taken based on signal',
                'order_id': 'Order ID if order was created/modified',
                'reasoning': 'Explanation of decision logic',
                'confidence_used': 'Confidence score that influenced decision',
                'processing_time': 'Signal processing time',
                'response_timestamp': 'Response generation timestamp'
            },
            'supported_signal_types': list(self.signal_handlers.keys()),
            'confidence_thresholds': self.confidence_thresholds,
            'auto_trading_settings': {
                'enabled': self.auto_trading_enabled,
                'max_auto_order_value': self.max_auto_order_value,
                'daily_auto_limit': self.daily_auto_limit,
                'current_daily_total': self.current_daily_auto_total
            },
            'actions': ['order_created', 'order_modified', 'order_cancelled', 'no_action', 'risk_escalation', 'error'],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_intelligence_statistics(self) -> Dict[str, Any]:
        """Intelligence Processing Statistiken abrufen"""
        total_signals = len(self.processed_signals)
        total_responses = len(self.intelligence_responses)
        
        if total_responses == 0:
            return {
                'total_signals_processed': total_signals,
                'total_responses_generated': 0,
                'action_distribution': {},
                'average_confidence': 0.0,
                'auto_trading_stats': {
                    'enabled': self.auto_trading_enabled,
                    'daily_total': self.current_daily_auto_total,
                    'daily_limit': self.daily_auto_limit
                }
            }
        
        # Action Distribution
        actions = [r.action_taken for r in self.intelligence_responses.values()]
        action_dist = {action: actions.count(action) for action in set(actions)}
        
        # Average Confidence
        confidences = [r.confidence_used for r in self.intelligence_responses.values()]
        avg_confidence = sum(confidences) / len(confidences)
        
        return {
            'total_signals_processed': total_signals,
            'total_responses_generated': total_responses,
            'action_distribution': action_dist,
            'average_confidence': round(avg_confidence, 3),
            'average_processing_time': self.average_execution_time,
            'auto_trading_stats': {
                'enabled': self.auto_trading_enabled,
                'daily_total': self.current_daily_auto_total,
                'daily_limit': self.daily_auto_limit,
                'remaining_daily_limit': self.daily_auto_limit - self.current_daily_auto_total
            },
            'confidence_thresholds': self.confidence_thresholds

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