"""
Order Market Data Handler Module - Single Function Module
Verantwortlich ausschließlich für Market Data Event Handling Logic
"""

import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderStatus


class MarketDataUpdate(BaseModel):
    instrument_code: str
    timestamp: datetime
    bid_price: Optional[str] = None
    ask_price: Optional[str] = None
    last_price: Optional[str] = None
    volume_24h: Optional[str] = None
    price_change_24h: Optional[str] = None
    volatility: Optional[float] = None
    spread: Optional[str] = None
    metadata: Dict[str, Any] = {}


class OrderImpactAnalysis(BaseModel):
    order_id: str
    instrument_code: str
    impact_type: str  # 'price_favorable', 'price_unfavorable', 'volatility_spike', 'spread_widening'
    impact_severity: str  # 'low', 'medium', 'high'
    current_price: str
    order_price: Optional[str]
    price_deviation_percent: Optional[float]
    recommendation: str
    analysis_timestamp: datetime


class OrderMarketDataHandlerModule(SingleFunctionModule):
    """
    Single Function Module: Order Market Data Handler
    Verantwortlichkeit: Ausschließlich Market-Data-Event-Handling-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_market_data_handler", event_bus)
        
        # Market Data Cache
        self.latest_market_data = {}
        self.market_data_history = {}
        self.market_data_updates_count = 0
        
        # Order Impact Analysis
        self.order_impact_analyses = {}
        self.impact_analysis_counter = 0
        
        # Market Data Thresholds
        self.price_deviation_thresholds = {
            'minor': 0.01,    # 1%
            'moderate': 0.03, # 3%
            'significant': 0.05, # 5%
            'major': 0.10     # 10%
        }
        
        self.volatility_thresholds = {
            'low': 0.01,      # 1%
            'normal': 0.03,   # 3%
            'high': 0.05,     # 5%
            'extreme': 0.10   # 10%
        }
        
        self.spread_thresholds = {
            'tight': 0.001,   # 0.1%
            'normal': 0.005,  # 0.5%
            'wide': 0.01,     # 1%
            'very_wide': 0.02 # 2%
        }
        
        # Order Monitoring (simuliert - normalerweise über andere Services)
        self.monitored_orders = {}
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Market Data Event Handling
        
        Args:
            input_data: {
                'event': market data event,
                'monitored_orders': optional list of orders to analyze,
                'analysis_scope': 'price_impact', 'volatility_analysis', 'spread_analysis', 'all'
            }
            
        Returns:
            Dict mit Market-Data-Analysis-Result
        """
        event_data = input_data.get('event')
        monitored_orders = input_data.get('monitored_orders', [])
        analysis_scope = input_data.get('analysis_scope', 'all')
        
        if not event_data:
            raise ValueError('No market data event provided')
        
        # Market Data Update extrahieren
        market_data_update = await self._extract_market_data_update(event_data)
        
        # Market Data verarbeiten
        analysis_results = await self._process_market_data_update(
            market_data_update, monitored_orders, analysis_scope
        )
        
        return {
            'instrument_code': market_data_update.instrument_code,
            'timestamp': market_data_update.timestamp.isoformat(),
            'market_data': self._serialize_market_data(market_data_update),
            'impact_analyses': [self._serialize_impact_analysis(analysis) for analysis in analysis_results],
            'analysis_summary': self._generate_analysis_summary(analysis_results),
            'processing_timestamp': datetime.now().isoformat()
        }
    
    async def _extract_market_data_update(self, event_data: Dict[str, Any]) -> MarketDataUpdate:
        """Extrahiert Market Data Update aus Event Data"""
        self.market_data_updates_count += 1
        
        # Event Data parsen
        data = event_data.get('data', {})
        
        market_data_update = MarketDataUpdate(
            instrument_code=data.get('instrument_code', 'UNKNOWN'),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            bid_price=data.get('bid_price'),
            ask_price=data.get('ask_price'),
            last_price=data.get('last_price'),
            volume_24h=data.get('volume_24h'),
            price_change_24h=data.get('price_change_24h'),
            volatility=data.get('volatility'),
            spread=data.get('spread'),
            metadata=data.get('metadata', {})
        )
        
        # Market Data in Cache aktualisieren
        self.latest_market_data[market_data_update.instrument_code] = market_data_update
        
        # Market Data History (letzte 100 Updates pro Instrument)
        instrument = market_data_update.instrument_code
        if instrument not in self.market_data_history:
            self.market_data_history[instrument] = []
        
        self.market_data_history[instrument].append(market_data_update)
        if len(self.market_data_history[instrument]) > 100:
            self.market_data_history[instrument].pop(0)
        
        return market_data_update
    
    async def _process_market_data_update(self, market_data_update: MarketDataUpdate,
                                        monitored_orders: List[Dict],
                                        analysis_scope: str) -> List[OrderImpactAnalysis]:
        """Verarbeitet Market Data Update und analysiert Order Impact"""
        
        analysis_results = []
        instrument = market_data_update.instrument_code
        
        # Relevante Orders für dieses Instrument finden
        relevant_orders = [
            order for order in monitored_orders 
            if order.get('instrument_code') == instrument and
               order.get('status') in ['OPEN', 'PARTIALLY_FILLED']
        ]
        
        # Order Impact Analyses durchführen
        for order in relevant_orders:
            impact_analyses = await self._analyze_order_impact(
                order, market_data_update, analysis_scope
            )
            analysis_results.extend(impact_analyses)
        
        # Event-Bus Notifications für kritische Impacts
        await self._check_and_publish_critical_impacts(analysis_results)
        
        self.logger.info(f"Market data processed",
                       instrument=instrument,
                       orders_analyzed=len(relevant_orders),
                       impacts_found=len(analysis_results))
        
        return analysis_results
    
    async def _analyze_order_impact(self, order: Dict[str, Any], 
                                  market_data_update: MarketDataUpdate,
                                  analysis_scope: str) -> List[OrderImpactAnalysis]:
        """Analysiert Impact von Market Data auf einzelne Order"""
        
        analyses = []
        order_id = order.get('order_id', 'UNKNOWN')
        
        # Price Impact Analysis
        if analysis_scope in ['price_impact', 'all']:
            price_analysis = await self._analyze_price_impact(order, market_data_update)
            if price_analysis:
                analyses.append(price_analysis)
        
        # Volatility Impact Analysis
        if analysis_scope in ['volatility_analysis', 'all']:
            volatility_analysis = await self._analyze_volatility_impact(order, market_data_update)
            if volatility_analysis:
                analyses.append(volatility_analysis)
        
        # Spread Impact Analysis
        if analysis_scope in ['spread_analysis', 'all']:
            spread_analysis = await self._analyze_spread_impact(order, market_data_update)
            if spread_analysis:
                analyses.append(spread_analysis)
        
        # Speichere Analyses
        for analysis in analyses:
            self.order_impact_analyses[analysis.order_id + "_" + str(self.impact_analysis_counter)] = analysis
            self.impact_analysis_counter += 1
        
        return analyses
    
    async def _analyze_price_impact(self, order: Dict[str, Any], 
                                  market_data_update: MarketDataUpdate) -> Optional[OrderImpactAnalysis]:
        """Analysiert Price Impact auf Order"""
        
        order_id = order.get('order_id')
        order_side = order.get('side')
        order_type = order.get('type')
        order_price = order.get('price')
        
        # Nur für LIMIT Orders mit Price
        if order_type != 'LIMIT' or not order_price:
            return None
        
        current_price = None
        if order_side == 'BUY':
            current_price = market_data_update.ask_price or market_data_update.last_price
        else:  # SELL
            current_price = market_data_update.bid_price or market_data_update.last_price
        
        if not current_price:
            return None
        
        # Price Deviation berechnen
        order_price_decimal = Decimal(order_price)
        current_price_decimal = Decimal(current_price)
        
        if order_side == 'BUY':
            # Für Buy Orders: günstiger wenn Market Price unter Order Price
            price_deviation = float((current_price_decimal - order_price_decimal) / order_price_decimal)
        else:  # SELL
            # Für Sell Orders: günstiger wenn Market Price über Order Price
            price_deviation = float((order_price_decimal - current_price_decimal) / order_price_decimal)
        
        # Impact Type und Severity bestimmen
        if abs(price_deviation) < self.price_deviation_thresholds['minor']:
            return None  # Keine signifikante Deviation
        
        impact_type = 'price_favorable' if price_deviation < 0 else 'price_unfavorable'
        
        abs_deviation = abs(price_deviation)
        if abs_deviation >= self.price_deviation_thresholds['major']:
            severity = 'high'
        elif abs_deviation >= self.price_deviation_thresholds['significant']:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Recommendation generieren
        if impact_type == 'price_favorable':
            if severity == 'high':
                recommendation = f"Highly favorable price movement - order likely to fill soon"
            else:
                recommendation = f"Favorable price movement - order getting closer to execution"
        else:
            if severity == 'high':
                recommendation = f"Significant unfavorable price movement - consider order review or cancellation"
            elif severity == 'medium':
                recommendation = f"Moderate unfavorable price movement - monitor closely"
            else:
                recommendation = f"Minor unfavorable price movement - continue monitoring"
        
        return OrderImpactAnalysis(
            order_id=order_id,
            instrument_code=market_data_update.instrument_code,
            impact_type=impact_type,
            impact_severity=severity,
            current_price=current_price,
            order_price=order_price,
            price_deviation_percent=price_deviation * 100,
            recommendation=recommendation,
            analysis_timestamp=datetime.now()
        )
    
    async def _analyze_volatility_impact(self, order: Dict[str, Any], 
                                       market_data_update: MarketDataUpdate) -> Optional[OrderImpactAnalysis]:
        """Analysiert Volatility Impact auf Order"""
        
        if not market_data_update.volatility:
            return None
        
        order_id = order.get('order_id')
        order_type = order.get('type')
        volatility = market_data_update.volatility
        
        # Volatility Level bestimmen
        if volatility >= self.volatility_thresholds['extreme']:
            severity = 'high'
            impact_description = 'extreme'
        elif volatility >= self.volatility_thresholds['high']:
            severity = 'medium'
            impact_description = 'high'
        elif volatility >= self.volatility_thresholds['normal']:
            severity = 'low'
            impact_description = 'elevated'
        else:
            return None  # Normale Volatilität
        
        # Recommendation basierend auf Order Type
        if order_type == 'MARKET':
            recommendation = f"High volatility detected - market order may experience slippage"
        elif order_type == 'LIMIT':
            recommendation = f"High volatility may increase fill probability but with price uncertainty"
        else:
            recommendation = f"High volatility detected - monitor order execution carefully"
        
        return OrderImpactAnalysis(
            order_id=order_id,
            instrument_code=market_data_update.instrument_code,
            impact_type='volatility_spike',
            impact_severity=severity,
            current_price=market_data_update.last_price or 'N/A',
            order_price=order.get('price'),
            price_deviation_percent=None,
            recommendation=recommendation,
            analysis_timestamp=datetime.now()
        )
    
    async def _analyze_spread_impact(self, order: Dict[str, Any], 
                                   market_data_update: MarketDataUpdate) -> Optional[OrderImpactAnalysis]:
        """Analysiert Spread Impact auf Order"""
        
        if not market_data_update.bid_price or not market_data_update.ask_price:
            return None
        
        order_id = order.get('order_id')
        
        # Spread berechnen
        bid_price = Decimal(market_data_update.bid_price)
        ask_price = Decimal(market_data_update.ask_price)
        mid_price = (bid_price + ask_price) / 2
        spread_percent = float((ask_price - bid_price) / mid_price)
        
        # Spread Level bestimmen
        if spread_percent >= self.spread_thresholds['very_wide']:
            severity = 'high'
            impact_description = 'very wide'
        elif spread_percent >= self.spread_thresholds['wide']:
            severity = 'medium'
            impact_description = 'wide'
        elif spread_percent >= self.spread_thresholds['normal']:
            severity = 'low'
            impact_description = 'elevated'
        else:
            return None  # Normaler Spread
        
        recommendation = f"Spread is {impact_description} ({spread_percent:.2%}) - consider impact on execution cost"
        
        return OrderImpactAnalysis(
            order_id=order_id,
            instrument_code=market_data_update.instrument_code,
            impact_type='spread_widening',
            impact_severity=severity,
            current_price=str(mid_price),
            order_price=order.get('price'),
            price_deviation_percent=spread_percent * 100,
            recommendation=recommendation,
            analysis_timestamp=datetime.now()
        )
    
    async def _check_and_publish_critical_impacts(self, analysis_results: List[OrderImpactAnalysis]):
        """Prüft und publisht kritische Impacts über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        critical_impacts = [
            analysis for analysis in analysis_results 
            if analysis.impact_severity == 'high'
        ]
        
        for impact in critical_impacts:
            await self._publish_critical_impact_event(impact)
    
    async def _publish_critical_impact_event(self, impact: OrderImpactAnalysis):
        """Publisht Critical Impact Event über Event-Bus"""
        from event_bus import Event
        
        event = Event(
            event_type="order_critical_market_impact",
            stream_id=f"market-impact-{impact.order_id}-{int(impact.analysis_timestamp.timestamp())}",
            data={
                'order_id': impact.order_id,
                'instrument_code': impact.instrument_code,
                'impact_type': impact.impact_type,
                'impact_severity': impact.impact_severity,
                'current_price': impact.current_price,
                'order_price': impact.order_price,
                'price_deviation_percent': impact.price_deviation_percent,
                'recommendation': impact.recommendation,
                'analysis_timestamp': impact.analysis_timestamp.isoformat()
            },
            source="order_market_data_handler"
        )
        
        await self.event_bus.publish(event)
    
    def _serialize_market_data(self, market_data: MarketDataUpdate) -> Dict[str, Any]:
        """Serialisiert Market Data Update"""
        return {
            'instrument_code': market_data.instrument_code,
            'timestamp': market_data.timestamp.isoformat(),
            'bid_price': market_data.bid_price,
            'ask_price': market_data.ask_price,
            'last_price': market_data.last_price,
            'volume_24h': market_data.volume_24h,
            'price_change_24h': market_data.price_change_24h,
            'volatility': market_data.volatility,
            'spread': market_data.spread,
            'metadata': market_data.metadata
        }
    
    def _serialize_impact_analysis(self, analysis: OrderImpactAnalysis) -> Dict[str, Any]:
        """Serialisiert Impact Analysis"""
        return {
            'order_id': analysis.order_id,
            'instrument_code': analysis.instrument_code,
            'impact_type': analysis.impact_type,
            'impact_severity': analysis.impact_severity,
            'current_price': analysis.current_price,
            'order_price': analysis.order_price,
            'price_deviation_percent': analysis.price_deviation_percent,
            'recommendation': analysis.recommendation,
            'analysis_timestamp': analysis.analysis_timestamp.isoformat()
        }
    
    def _generate_analysis_summary(self, analysis_results: List[OrderImpactAnalysis]) -> Dict[str, Any]:
        """Generiert Analysis Summary"""
        if not analysis_results:
            return {
                'total_impacts': 0,
                'severity_distribution': {},
                'impact_type_distribution': {},
                'critical_impacts': 0
            }
        
        severity_counts = {}
        impact_type_counts = {}
        critical_count = 0
        
        for analysis in analysis_results:
            # Severity Distribution
            severity_counts[analysis.impact_severity] = severity_counts.get(analysis.impact_severity, 0) + 1
            
            # Impact Type Distribution
            impact_type_counts[analysis.impact_type] = impact_type_counts.get(analysis.impact_type, 0) + 1
            
            # Critical Count
            if analysis.impact_severity == 'high':
                critical_count += 1
        
        return {
            'total_impacts': len(analysis_results),
            'severity_distribution': severity_counts,
            'impact_type_distribution': impact_type_counts,
            'critical_impacts': critical_count
        }
    
    def get_latest_market_data(self, instrument_code: str) -> Optional[MarketDataUpdate]:
        """Gibt neueste Market Data für Instrument zurück"""
        return self.latest_market_data.get(instrument_code)
    
    def get_market_data_history(self, instrument_code: str, limit: int = 50) -> List[MarketDataUpdate]:
        """Gibt Market Data History für Instrument zurück"""
        history = self.market_data_history.get(instrument_code, [])
        return history[-limit:] if len(history) > limit else history
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_market_data_handler',
            'description': 'Processes market data events and analyzes impact on orders',
            'responsibility': 'Market data event handling and order impact analysis only',
            'input_parameters': {
                'event': 'Market data event with price, volume, volatility information',
                'monitored_orders': 'Optional list of orders to analyze for impact',
                'analysis_scope': 'Scope of analysis (price_impact, volatility_analysis, spread_analysis, all)'
            },
            'output_format': {
                'instrument_code': 'Instrument that was updated',
                'timestamp': 'Market data timestamp',
                'market_data': 'Processed market data update',
                'impact_analyses': 'List of order impact analyses',
                'analysis_summary': 'Summary of impact analysis results',
                'processing_timestamp': 'Processing completion timestamp'
            },
            'analysis_types': ['price_impact', 'volatility_analysis', 'spread_analysis'],
            'thresholds': {
                'price_deviation': self.price_deviation_thresholds,
                'volatility': self.volatility_thresholds,
                'spread': self.spread_thresholds
            },
            'impact_types': ['price_favorable', 'price_unfavorable', 'volatility_spike', 'spread_widening'],
            'severity_levels': ['low', 'medium', 'high'],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_market_data_statistics(self) -> Dict[str, Any]:
        """Market Data Processing Statistiken abrufen"""
        total_updates = self.market_data_updates_count
        total_analyses = len(self.order_impact_analyses)
        instruments_tracked = len(self.latest_market_data)
        
        # Impact Analysis Distribution
        if total_analyses > 0:
            impacts = list(self.order_impact_analyses.values())
            severity_dist = {}
            impact_type_dist = {}
            
            for impact in impacts:
                severity_dist[impact.impact_severity] = severity_dist.get(impact.impact_severity, 0) + 1
                impact_type_dist[impact.impact_type] = impact_type_dist.get(impact.impact_type, 0) + 1
        else:
            severity_dist = {}
            impact_type_dist = {}
        
        return {
            'total_market_data_updates': total_updates,
            'total_impact_analyses': total_analyses,
            'instruments_tracked': instruments_tracked,
            'severity_distribution': severity_dist,
            'impact_type_distribution': impact_type_dist,
            'average_processing_time': self.average_execution_time,
            'thresholds_configured': {
                'price_deviation_levels': len(self.price_deviation_thresholds),
                'volatility_levels': len(self.volatility_thresholds),
                'spread_levels': len(self.spread_thresholds)
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