#!/usr/bin/env python3
"""
Profit Calculation Engine
Zentrales Berechnungsmodul für Gewinnvorhersagen mit Multi-Source-Daten
Empfängt Daten von verschiedenen Datenquellen-Modulen über Event-Bus
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import uuid
import json
import sqlite3
import os
from dataclasses import dataclass, asdict
from statistics import mean, median
import math

# Add paths for imports
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')

from backend_base_module import BackendBaseModule
from event_bus import EventBusConnector, EventType
from logging_config import setup_logging
import structlog

logger = setup_logging("profit-calculation-engine")


@dataclass
class ProfitPrediction:
    """Strukturierte Gewinnvorhersage"""
    symbol: str
    company_name: str
    score: float
    profit_forecast: float
    forecast_period_days: int
    recommendation: str
    confidence_level: float
    trend: str
    target_date: str
    created_at: str
    
    # Multi-Source Metadaten
    source_count: int
    source_reliability: float
    calculation_method: str
    risk_assessment: str
    
    # Detaillierte Metriken
    base_metrics: Dict[str, Any]
    source_contributions: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiSourceDataAggregator:
    """Aggregiert Daten von verschiedenen Datenquellen"""
    
    def __init__(self):
        self.data_sources = {}
        self.aggregation_timeout = 10.0  # 10 Sekunden Timeout für Datensammlung
        
    def add_source_data(self, source_name: str, data: Dict[str, Any]):
        """Füge Daten von einer Quelle hinzu"""
        self.data_sources[source_name] = {
            'data': data,
            'timestamp': datetime.now(),
            'reliability': data.get('reliability_score', 0.5),
            'priority': data.get('source_priority', 1)
        }
    
    def get_aggregated_data(self) -> Dict[str, Any]:
        """Aggregiere Daten von allen verfügbaren Quellen"""
        if not self.data_sources:
            raise ValueError("No data sources available for aggregation")
        
        # Sortiere Quellen nach Priorität und Zuverlässigkeit
        sorted_sources = sorted(
            self.data_sources.items(),
            key=lambda x: (x[1]['priority'], x[1]['reliability']),
            reverse=True
        )
        
        # Berechne gewichtete Metriken
        total_weight = sum(source['reliability'] * source['priority'] 
                          for _, source in sorted_sources)
        
        aggregated = {
            'sources_used': list(self.data_sources.keys()),
            'source_count': len(self.data_sources),
            'total_reliability': total_weight / len(self.data_sources) if self.data_sources else 0,
            'primary_source': sorted_sources[0][0] if sorted_sources else None,
            'aggregation_timestamp': datetime.now().isoformat(),
            'source_contributions': {}
        }
        
        # Extrahiere und aggregiere Metriken
        financial_metrics = {}
        analysis_metrics = {}
        prediction_indicators = {}
        
        for source_name, source_info in sorted_sources:
            source_data = source_info['data']
            weight = source_info['reliability'] * source_info['priority']
            
            # Store source contribution
            aggregated['source_contributions'][source_name] = {
                'weight': weight,
                'reliability': source_info['reliability'],
                'priority': source_info['priority'],
                'timestamp': source_info['timestamp'].isoformat()
            }
            
            # Extrahiere Financial Metrics
            if 'financial_metrics' in source_data:
                fm = source_data['financial_metrics']
                for key, value in fm.items():
                    if isinstance(value, (int, float)):
                        if key not in financial_metrics:
                            financial_metrics[key] = []
                        financial_metrics[key].append((value, weight))
            
            # Extrahiere Analysis Metrics
            if 'analysis_metrics' in source_data:
                am = source_data['analysis_metrics']
                for key, value in am.items():
                    if isinstance(value, (int, float)):
                        if key not in analysis_metrics:
                            analysis_metrics[key] = []
                        analysis_metrics[key].append((value, weight))
            
            # Extrahiere Prediction Indicators
            if 'prediction_indicators' in source_data:
                pi = source_data['prediction_indicators']
                for key, value in pi.items():
                    if isinstance(value, (int, float)):
                        if key not in prediction_indicators:
                            prediction_indicators[key] = []
                        prediction_indicators[key].append((value, weight))
        
        # Berechne gewichtete Durchschnitte
        aggregated['financial_metrics'] = self._calculate_weighted_averages(financial_metrics)
        aggregated['analysis_metrics'] = self._calculate_weighted_averages(analysis_metrics)
        aggregated['prediction_indicators'] = self._calculate_weighted_averages(prediction_indicators)
        
        # Füge primäre Company Info hinzu (von der wichtigsten Quelle)
        if sorted_sources and 'company_info' in sorted_sources[0][1]['data']:
            aggregated['company_info'] = sorted_sources[0][1]['data']['company_info']
        
        return aggregated
    
    def _calculate_weighted_averages(self, metrics: Dict[str, List[Tuple[float, float]]]) -> Dict[str, float]:
        """Berechne gewichtete Durchschnitte für Metriken"""
        result = {}
        for key, value_weight_pairs in metrics.items():
            if value_weight_pairs:
                total_weighted_value = sum(value * weight for value, weight in value_weight_pairs)
                total_weight = sum(weight for _, weight in value_weight_pairs)
                if total_weight > 0:
                    result[key] = round(total_weighted_value / total_weight, 4)
                else:
                    result[key] = 0.0
        return result
    
    def is_sufficient_data(self) -> bool:
        """Prüfe ob ausreichend Daten für Berechnung vorhanden sind"""
        return len(self.data_sources) >= 1  # Mindestens eine Datenquelle erforderlich
    
    def clear(self):
        """Lösche alle gesammelten Daten"""
        self.data_sources.clear()


class ProfitCalculationEngine(BackendBaseModule):
    """
    Zentrales Berechnungsmodul für Gewinnvorhersagen
    Empfängt Daten von mehreren Datenquellen über Event-Bus
    """
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("profit_calculation_engine", event_bus)
        
        # Datenbank für Predictions
        self.db_path = "/home/mdoehler/aktienanalyse-ökosystem/data/ki_recommendations.db"
        
        # Multi-Source Data Aggregation
        self.pending_calculations = {}  # request_id -> MultiSourceDataAggregator
        self.calculation_timeout = 30.0  # 30 Sekunden Timeout
        
        # Calculation Configuration
        self.config = {
            'default_forecast_days': 30,
            'min_confidence_threshold': 0.3,
            'max_forecast_period': 365,
            'risk_adjustment_factor': 0.1,
            'multi_source_bonus': 0.15,  # Bonus für mehrere Datenquellen
            'timeframe_adjustments': {
                7: 1.2,    # 1 Woche: +20%
                14: 1.1,   # 2 Wochen: +10%
                30: 1.0,   # 1 Monat: Basis
                90: 0.9,   # 3 Monate: -10%
                180: 0.8,  # 6 Monate: -20%
                365: 0.7   # 1 Jahr: -30%
            }
        }
        
        # Performance Metriken
        self.metrics = {
            'calculations_processed': 0,
            'successful_calculations': 0,
            'multi_source_calculations': 0,
            'average_source_count': 0.0,
            'average_calculation_time': 0.0,
            'last_calculation': None
        }
        
    async def _initialize_module(self) -> bool:
        """Initialize profit calculation engine"""
        try:
            logger.info("Initializing Profit Calculation Engine")
            
            # Initialize database
            await self._initialize_database()
            
            logger.info("Profit Calculation Engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Profit Calculation Engine", error=str(e))
            return False
    
    async def _initialize_database(self):
        """Initialize database with updated schema for multi-source support"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Updated table schema für Multi-Source
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    score REAL NOT NULL,
                    profit_forecast REAL NOT NULL,
                    forecast_period_days INTEGER NOT NULL,
                    recommendation TEXT NOT NULL,
                    confidence_level REAL NOT NULL,
                    trend TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    
                    -- Multi-Source Metadaten
                    source_count INTEGER DEFAULT 1,
                    source_reliability REAL DEFAULT 0.5,
                    calculation_method TEXT DEFAULT 'single_source',
                    risk_assessment TEXT DEFAULT 'medium',
                    
                    -- JSON Felder für detaillierte Daten
                    base_metrics TEXT,  -- JSON
                    source_contributions TEXT  -- JSON
                )
            ''')
            
            # Index für bessere Performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON predictions(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON predictions(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_count ON predictions(source_count)')
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    async def _subscribe_to_events(self):
        """Subscribe to calculation events"""
        # Subscribe to profit calculation requests
        await self.subscribe_to_event(
            EventType.MODULE_REQUEST,
            self._handle_calculation_request
        )
        
        # Subscribe to data source responses
        await self.subscribe_to_event(
            EventType.MODULE_RESPONSE,
            self._handle_data_source_response
        )
        
        # Use same EventType for batch responses
        # await self.subscribe_to_event(
        #     EventType.MARKET_DATA_RESPONSE,
        #     self._handle_batch_data_source_response
        # )
        
        # Subscribe to other data sources (future extensions)
        # Generic data source responses handled via MARKET_DATA_RESPONSE
        # await self.subscribe_to_event(
        #     EventType.MARKET_DATA_RESPONSE,
        #     self._handle_generic_data_source_response
        # )
        
        # Subscribe to calculation status requests
        await self.subscribe_to_event(
            EventType.SYSTEM_HEALTH_REQUEST,
            self._handle_status_request
        )
    
    async def _handle_calculation_request(self, event):
        """Handle profit calculation requests"""
        start_time = datetime.now()
        request_id = None
        
        try:
            # Extract event data
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_id = data.get('request_id', str(uuid.uuid4()))
            symbol = data.get('symbol')
            company_name = data.get('company_name')
            forecast_days = data.get('forecast_days', self.config['default_forecast_days'])
            data_sources = data.get('data_sources', ['marketcap'])  # Welche Quellen anfordern
            
            logger.info("Processing profit calculation request", 
                       request_id=request_id, symbol=symbol, company_name=company_name,
                       forecast_days=forecast_days, data_sources=data_sources)
            
            # Initialize data aggregator for this request
            self.pending_calculations[request_id] = {
                'aggregator': MultiSourceDataAggregator(),
                'symbol': symbol,
                'company_name': company_name,
                'forecast_days': forecast_days,
                'requested_sources': data_sources,
                'start_time': start_time,
                'completed_sources': 0,
                'total_sources': len(data_sources)
            }
            
            # Request data from all specified sources
            for source in data_sources:
                await self._request_data_from_source(request_id, source, symbol, company_name)
            
            # Start timeout monitoring
            asyncio.create_task(self._monitor_calculation_timeout(request_id))
            
        except Exception as e:
            logger.error("Error processing calculation request", 
                        request_id=request_id, error=str(e))
            await self._send_calculation_error(request_id, str(e))
    
    async def _request_data_from_source(self, request_id: str, source: str, symbol: str, company_name: str):
        """Request data from specific data source"""
        try:
            if source == 'marketcap':
                await self.publish_module_event(
                    'data_source.marketcap.request',
                    {
                        'request_id': request_id,
                        'symbol': symbol,
                        'company_name': company_name,
                        'requested_by': 'profit_calculation_engine'
                    }
                )
            
            # Future: Add other data sources
            # elif source == 'financial_api':
            #     await self.publish_module_event('data_source.financial_api.request', ...)
            # elif source == 'news_sentiment':
            #     await self.publish_module_event('data_source.news.request', ...)
            
            else:
                logger.warning(f"Unknown data source requested: {source}", request_id=request_id)
                
        except Exception as e:
            logger.error(f"Error requesting data from {source}", request_id=request_id, error=str(e))
    
    async def _handle_data_source_response(self, event):
        """Handle response from data sources"""
        try:
            # Extract event data
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_id = data.get('request_id')
            success = data.get('success', False)
            source_data = data.get('data', {})
            
            if not request_id or request_id not in self.pending_calculations:
                return
            
            calculation_info = self.pending_calculations[request_id]
            
            if success and source_data:
                # Add source data to aggregator
                source_name = source_data.get('data_source', 'unknown')
                calculation_info['aggregator'].add_source_data(source_name, source_data)
                calculation_info['completed_sources'] += 1
                
                logger.info("Received data source response", 
                           request_id=request_id, source=source_name,
                           completed=calculation_info['completed_sources'],
                           total=calculation_info['total_sources'])
            else:
                logger.warning("Received failed data source response", 
                             request_id=request_id, success=success)
                calculation_info['completed_sources'] += 1
            
            # Check if we have enough data to proceed
            if (calculation_info['completed_sources'] >= calculation_info['total_sources'] or
                calculation_info['aggregator'].is_sufficient_data()):
                
                await self._perform_calculation(request_id)
                
        except Exception as e:
            logger.error("Error handling data source response", error=str(e))
    
    async def _handle_batch_data_source_response(self, event):
        """Handle batch responses from data sources"""
        # For now, delegate to single response handler
        # TODO: Implement batch-specific logic if needed
        await self._handle_data_source_response(event)
    
    async def _handle_generic_data_source_response(self, event):
        """Handle responses from any data source (generic handler)"""
        await self._handle_data_source_response(event)
    
    async def _perform_calculation(self, request_id: str):
        """Perform the actual profit calculation"""
        try:
            if request_id not in self.pending_calculations:
                return
            
            calculation_info = self.pending_calculations[request_id]
            aggregator = calculation_info['aggregator']
            
            # Get aggregated data
            aggregated_data = aggregator.get_aggregated_data()
            
            # Perform calculation
            prediction = await self._calculate_profit_prediction(
                symbol=calculation_info['symbol'],
                company_name=calculation_info['company_name'],
                forecast_days=calculation_info['forecast_days'],
                aggregated_data=aggregated_data
            )
            
            # Save to database
            await self._save_prediction(prediction)
            
            # Send response
            await self._send_calculation_response(request_id, prediction, calculation_info['start_time'])
            
            # Update metrics
            self.metrics['successful_calculations'] += 1
            if aggregated_data['source_count'] > 1:
                self.metrics['multi_source_calculations'] += 1
            
            # Cleanup
            del self.pending_calculations[request_id]
            
        except Exception as e:
            logger.error("Error performing calculation", request_id=request_id, error=str(e))
            await self._send_calculation_error(request_id, str(e))
            if request_id in self.pending_calculations:
                del self.pending_calculations[request_id]
    
    async def _calculate_profit_prediction(self, symbol: str, company_name: str, 
                                         forecast_days: int, aggregated_data: Dict[str, Any]) -> ProfitPrediction:
        """Calculate profit prediction from aggregated data"""
        try:
            # Extract aggregated metrics
            financial_metrics = aggregated_data.get('financial_metrics', {})
            analysis_metrics = aggregated_data.get('analysis_metrics', {})
            prediction_indicators = aggregated_data.get('prediction_indicators', {})
            company_info = aggregated_data.get('company_info', {})
            
            # Base calculation from analysis metrics
            base_score = analysis_metrics.get('analysis_score', 5.0)
            market_cap = financial_metrics.get('market_cap', 0)
            daily_change = financial_metrics.get('daily_change_percent', 0)
            
            # Multi-Source Calculation Enhancement
            source_count = aggregated_data['source_count']
            source_reliability = aggregated_data['total_reliability']
            
            # Multi-Source Bonus
            multi_source_multiplier = 1.0 + (source_count - 1) * self.config['multi_source_bonus']
            
            # Timeframe Adjustment
            timeframe_multiplier = self._get_timeframe_multiplier(forecast_days)
            
            # Risk Assessment basierend auf Multi-Source Daten
            risk_factor = self._calculate_risk_factor(aggregated_data)
            
            # Calculate base profit forecast
            base_profit = self._calculate_base_profit(base_score, market_cap, daily_change)
            
            # Apply adjustments
            adjusted_profit = base_profit * multi_source_multiplier * timeframe_multiplier * (1 - risk_factor * self.config['risk_adjustment_factor'])
            
            # Calculate confidence level
            confidence = self._calculate_confidence_level(
                source_count, source_reliability, risk_factor, aggregated_data
            )
            
            # Determine recommendation
            recommendation = self._determine_recommendation(adjusted_profit, confidence, risk_factor)
            
            # Determine trend
            trend = self._determine_trend(daily_change, prediction_indicators)
            
            # Risk assessment string
            risk_assessment = self._get_risk_assessment_string(risk_factor)
            
            # Target date
            target_date = (datetime.now() + timedelta(days=forecast_days)).isoformat()
            
            # Create prediction object
            prediction = ProfitPrediction(
                symbol=symbol,
                company_name=company_name or company_info.get('name', symbol),
                score=round(base_score * multi_source_multiplier, 2),
                profit_forecast=round(adjusted_profit, 2),
                forecast_period_days=forecast_days,
                recommendation=recommendation,
                confidence_level=round(confidence, 3),
                trend=trend,
                target_date=target_date,
                created_at=datetime.now().isoformat(),
                
                # Multi-Source Metadata
                source_count=source_count,
                source_reliability=round(source_reliability, 3),
                calculation_method='multi_source' if source_count > 1 else 'single_source',
                risk_assessment=risk_assessment,
                
                # Detailed metrics
                base_metrics={
                    'base_score': base_score,
                    'base_profit': base_profit,
                    'multi_source_multiplier': multi_source_multiplier,
                    'timeframe_multiplier': timeframe_multiplier,
                    'risk_factor': risk_factor,
                    'market_cap': market_cap,
                    'daily_change': daily_change
                },
                source_contributions=aggregated_data.get('source_contributions', {})
            )
            
            logger.info("Profit prediction calculated", 
                       symbol=symbol, profit=adjusted_profit, confidence=confidence,
                       sources=source_count, recommendation=recommendation)
            
            return prediction
            
        except Exception as e:
            logger.error("Error calculating profit prediction", error=str(e))
            raise
    
    def _calculate_base_profit(self, base_score: float, market_cap: float, daily_change: float) -> float:
        """Calculate base profit prediction"""
        # Market cap influence (logarithmic scaling for large numbers)
        market_cap_billions = market_cap / 1_000_000_000
        market_cap_factor = math.log10(max(1, market_cap_billions)) * 2
        
        # Daily change momentum
        momentum_factor = max(-10, min(10, daily_change))  # Cap at ±10%
        
        # Base calculation
        base_profit = (base_score * 0.4) + (market_cap_factor * 0.3) + (momentum_factor * 0.3)
        
        return max(0, base_profit)  # No negative base profits
    
    def _get_timeframe_multiplier(self, forecast_days: int) -> float:
        """Get timeframe adjustment multiplier"""
        # Find closest timeframe
        timeframes = sorted(self.config['timeframe_adjustments'].keys())
        closest_timeframe = min(timeframes, key=lambda x: abs(x - forecast_days))
        
        return self.config['timeframe_adjustments'][closest_timeframe]
    
    def _calculate_risk_factor(self, aggregated_data: Dict[str, Any]) -> float:
        """Calculate risk factor from aggregated data"""
        analysis_metrics = aggregated_data.get('analysis_metrics', {})
        financial_metrics = aggregated_data.get('financial_metrics', {})
        
        # Volatility indicators
        daily_change = abs(financial_metrics.get('daily_change_percent', 0))
        volatility_factor = analysis_metrics.get('volatility_factor', 0.5)
        risk_score = analysis_metrics.get('risk_score', 1.0)
        
        # Combine risk factors
        combined_risk = (daily_change * 0.4 + volatility_factor * 0.3 + risk_score * 0.3) / 10
        
        return min(1.0, max(0.0, combined_risk))  # Normalize to 0-1
    
    def _calculate_confidence_level(self, source_count: int, source_reliability: float, 
                                  risk_factor: float, aggregated_data: Dict[str, Any]) -> float:
        """Calculate confidence level for prediction"""
        # Base confidence from source reliability
        base_confidence = source_reliability
        
        # Multi-source bonus
        source_bonus = min(0.3, (source_count - 1) * 0.1)  # Max 30% bonus
        
        # Risk penalty
        risk_penalty = risk_factor * 0.2  # Max 20% penalty
        
        # Data quality bonus
        data_quality = self._assess_data_quality(aggregated_data)
        quality_bonus = data_quality * 0.1
        
        confidence = base_confidence + source_bonus + quality_bonus - risk_penalty
        
        return min(0.95, max(0.1, confidence))  # Keep between 10-95%
    
    def _assess_data_quality(self, aggregated_data: Dict[str, Any]) -> float:
        """Assess quality of aggregated data"""
        quality_score = 0.0
        
        # Check if key metrics are available
        financial_metrics = aggregated_data.get('financial_metrics', {})
        analysis_metrics = aggregated_data.get('analysis_metrics', {})
        
        if financial_metrics.get('market_cap', 0) > 0:
            quality_score += 0.3
        if 'daily_change_percent' in financial_metrics:
            quality_score += 0.2
        if analysis_metrics.get('analysis_score', 0) > 0:
            quality_score += 0.3
        if 'prediction_indicators' in aggregated_data:
            quality_score += 0.2
        
        return quality_score
    
    def _determine_recommendation(self, profit_forecast: float, confidence: float, risk_factor: float) -> str:
        """Determine investment recommendation"""
        if confidence < self.config['min_confidence_threshold']:
            return 'HOLD'
        
        if profit_forecast >= 8 and confidence >= 0.7 and risk_factor <= 0.3:
            return 'STRONG_BUY'
        elif profit_forecast >= 5 and confidence >= 0.6 and risk_factor <= 0.5:
            return 'BUY'
        elif profit_forecast >= 2 and confidence >= 0.5:
            return 'WEAK_BUY'
        elif profit_forecast >= -2:
            return 'HOLD'
        elif profit_forecast >= -5:
            return 'WEAK_SELL'
        else:
            return 'SELL'
    
    def _determine_trend(self, daily_change: float, prediction_indicators: Dict[str, Any]) -> str:
        """Determine trend direction"""
        momentum = prediction_indicators.get('momentum_indicator', 0)
        
        if daily_change > 2 and momentum > 0:
            return 'strong_bullish'
        elif daily_change > 0 and momentum >= 0:
            return 'bullish'
        elif daily_change < -2 and momentum < 0:
            return 'strong_bearish'
        elif daily_change < 0 and momentum <= 0:
            return 'bearish'
        else:
            return 'neutral'
    
    def _get_risk_assessment_string(self, risk_factor: float) -> str:
        """Convert risk factor to string assessment"""
        if risk_factor <= 0.3:
            return 'low'
        elif risk_factor <= 0.6:
            return 'medium'
        else:
            return 'high'
    
    async def _save_prediction(self, prediction: ProfitPrediction):
        """Save prediction to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO predictions (
                    symbol, company_name, score, profit_forecast, forecast_period_days,
                    recommendation, confidence_level, trend, target_date, created_at,
                    source_count, source_reliability, calculation_method, risk_assessment,
                    base_metrics, source_contributions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                prediction.symbol,
                prediction.company_name,
                prediction.score,
                prediction.profit_forecast,
                prediction.forecast_period_days,
                prediction.recommendation,
                prediction.confidence_level,
                prediction.trend,
                prediction.target_date,
                prediction.created_at,
                prediction.source_count,
                prediction.source_reliability,
                prediction.calculation_method,
                prediction.risk_assessment,
                json.dumps(prediction.base_metrics),
                json.dumps(prediction.source_contributions)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("Prediction saved to database", symbol=prediction.symbol)
            
        except Exception as e:
            logger.error("Error saving prediction to database", error=str(e))
            raise
    
    async def _send_calculation_response(self, request_id: str, prediction: ProfitPrediction, start_time: datetime):
        """Send calculation response"""
        calculation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        await self.publish_module_event(
            'profit_calculation.response',
            {
                'request_id': request_id,
                'success': True,
                'prediction': prediction.to_dict(),
                'calculation_time_ms': round(calculation_time, 2),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        logger.info("Sent calculation response", 
                   request_id=request_id, symbol=prediction.symbol,
                   calculation_time_ms=round(calculation_time, 2))
        
        # Update metrics
        self._update_calculation_time_metric(calculation_time)
    
    async def _send_calculation_error(self, request_id: str, error: str):
        """Send calculation error response"""
        await self.publish_module_event(
            'profit_calculation.error',
            {
                'request_id': request_id,
                'success': False,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        logger.error("Sent calculation error response", request_id=request_id, error=error)
    
    async def _monitor_calculation_timeout(self, request_id: str):
        """Monitor calculation timeout"""
        await asyncio.sleep(self.calculation_timeout)
        
        if request_id in self.pending_calculations:
            calculation_info = self.pending_calculations[request_id]
            aggregator = calculation_info['aggregator']
            
            # Check if we have at least some data
            if aggregator.is_sufficient_data():
                logger.warning("Calculation timeout reached, proceeding with available data",
                             request_id=request_id, 
                             completed=calculation_info['completed_sources'],
                             total=calculation_info['total_sources'])
                
                await self._perform_calculation(request_id)
            else:
                logger.error("Calculation timeout with insufficient data",
                           request_id=request_id)
                await self._send_calculation_error(request_id, "Timeout: Insufficient data from sources")
                del self.pending_calculations[request_id]
    
    async def _handle_status_request(self, event):
        """Handle calculation status requests"""
        try:
            if hasattr(event, 'data'):
                data = event.data
            else:
                data = event.get('data', {})
            
            request_id = data.get('request_id', str(uuid.uuid4()))
            
            status = {
                'engine': 'profit_calculation_engine',
                'status': 'healthy',
                'config': self.config,
                'metrics': self.metrics,
                'pending_calculations': len(self.pending_calculations),
                'database_path': self.db_path,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.publish_module_event(
                'profit_calculation.status_response',
                {
                    'request_id': request_id,
                    'status': status
                }
            )
            
        except Exception as e:
            logger.error("Error in status request", error=str(e))
    
    def _update_calculation_time_metric(self, calculation_time_ms: float):
        """Update average calculation time metric"""
        if self.metrics['average_calculation_time'] == 0:
            self.metrics['average_calculation_time'] = calculation_time_ms
        else:
            # Moving average
            self.metrics['average_calculation_time'] = (
                self.metrics['average_calculation_time'] * 0.9 + calculation_time_ms * 0.1
            )
        
        self.metrics['calculations_processed'] += 1
        self.metrics['last_calculation'] = datetime.now().isoformat()
        
        # Update average source count
        if self.metrics['calculations_processed'] > 0:
            total_sources = self.metrics['multi_source_calculations'] * 2 + (
                self.metrics['successful_calculations'] - self.metrics['multi_source_calculations']
            )
            self.metrics['average_source_count'] = total_sources / self.metrics['successful_calculations']
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main business logic processing"""
        try:
            operation = data.get('operation', 'calculate_profit')
            
            if operation == 'calculate_profit':
                # This would be handled via events, but can be used for direct calls
                symbol = data.get('symbol')
                company_name = data.get('company_name')
                forecast_days = data.get('forecast_days', self.config['default_forecast_days'])
                
                # Generate request ID and trigger calculation via events
                request_id = str(uuid.uuid4())
                
                # Simulate event-based calculation
                await self.publish_module_event(
                    'profit_calculation.request',
                    {
                        'request_id': request_id,
                        'symbol': symbol,
                        'company_name': company_name,
                        'forecast_days': forecast_days,
                        'data_sources': ['marketcap']
                    }
                )
                
                return {
                    'success': True,
                    'request_id': request_id,
                    'message': 'Calculation request submitted'
                }
            
            elif operation == 'get_recent_predictions':
                limit = data.get('limit', 10)
                predictions = await self._get_recent_predictions(limit)
                return {
                    'success': True,
                    'predictions': predictions,
                    'count': len(predictions)
                }
            
            else:
                return {'success': False, 'error': f'Unknown operation: {operation}'}
                
        except Exception as e:
            logger.error("Error in business logic processing", error=str(e))
            return {'success': False, 'error': str(e)}
    
    async def _get_recent_predictions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent predictions from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM predictions 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            predictions = []
            
            for row in rows:
                prediction_dict = dict(zip(columns, row))
                
                # Parse JSON fields
                if prediction_dict['base_metrics']:
                    prediction_dict['base_metrics'] = json.loads(prediction_dict['base_metrics'])
                if prediction_dict['source_contributions']:
                    prediction_dict['source_contributions'] = json.loads(prediction_dict['source_contributions'])
                
                predictions.append(prediction_dict)
            
            return predictions
            
        except Exception as e:
            logger.error("Error getting recent predictions", error=str(e))
            return []
    
    async def _cleanup_module(self):
        """Cleanup resources"""
        try:
            # Clear pending calculations
            self.pending_calculations.clear()
            
            await super()._cleanup_module()
            
        except Exception as e:
            logger.warning("Error during cleanup", error=str(e))


# Standalone service implementation
class ProfitCalculationEngineService:
    """Standalone Service für Profit Calculation Engine"""
    
    def __init__(self):
        self.event_bus = EventBusConnector("profit-calculation-engine-service")
        self.calculation_engine = None
        self.is_running = False
        
    async def initialize(self) -> bool:
        """Initialize service"""
        try:
            logger.info("Initializing Profit Calculation Engine Service")
            
            # Connect to event bus
            await self.event_bus.connect()
            
            # Initialize calculation engine
            self.calculation_engine = ProfitCalculationEngine(self.event_bus)
            await self.calculation_engine.initialize()
            
            self.is_running = True
            logger.info("Profit Calculation Engine Service initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Profit Calculation Engine Service", error=str(e))
            return False
    
    async def run(self):
        """Run the service"""
        try:
            logger.info("Starting Profit Calculation Engine Service...")
            
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error("Service error", error=str(e))
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown service"""
        try:
            logger.info("Shutting down Profit Calculation Engine Service")
            self.is_running = False
            
            if self.calculation_engine:
                await self.calculation_engine.shutdown()
            
            if self.event_bus:
                await self.event_bus.disconnect()
                
            logger.info("Profit Calculation Engine Service shutdown complete")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))


async def main():
    """Main entry point"""
    service = ProfitCalculationEngineService()
    
    try:
        success = await service.initialize()
        if not success:
            logger.error("Failed to initialize service")
            return 1
        
        await service.run()
        return 0
        
    except Exception as e:
        logger.error("Service failed", error=str(e))
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Critical service error", error=str(e))
        sys.exit(1)