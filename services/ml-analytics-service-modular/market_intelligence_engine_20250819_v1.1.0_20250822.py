#!/usr/bin/env python3
"""
Real-Time Market Intelligence und Event-Driven Analytics Engine - Phase 15
==========================================================================

Umfassendes Real-Time Market Intelligence System:
- Live Market Data Streaming
- Event-Driven Market Analysis
- News Sentiment Real-Time Processing
- Economic Indicator Monitoring
- Central Bank Watch System
- Geopolitical Event Analysis
- Corporate Action Tracking
- Earnings Surprise Detection
- Insider Trading Monitoring
- Market Volatility Alerts
- Cross-Asset Correlation Tracking
- Regime Change Detection

Author: Claude Code & AI Development Team
Version: 1.0.0
Date: 2025-08-19
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncpg
import json
import websockets
from aioredis import Redis
import aiohttp
from collections import deque
import re
from textblob import TextBlob

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventType(Enum):
    """Market event types"""
    EARNINGS_SURPRISE = "earnings_surprise"
    NEWS_SENTIMENT = "news_sentiment"
    ECONOMIC_INDICATOR = "economic_indicator"
    CENTRAL_BANK_ACTION = "central_bank_action"
    GEOPOLITICAL_EVENT = "geopolitical_event"
    CORPORATE_ACTION = "corporate_action"
    INSIDER_TRADING = "insider_trading"
    VOLATILITY_SPIKE = "volatility_spike"
    CORRELATION_BREAK = "correlation_break"
    REGIME_CHANGE = "regime_change"
    TECHNICAL_BREAKOUT = "technical_breakout"
    VOLUME_ANOMALY = "volume_anomaly"

class EventPriority(Enum):
    """Event priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class MarketRegime(Enum):
    """Market regime types"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS_MARKET = "sideways_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    CRISIS_MODE = "crisis_mode"

class DataSource(Enum):
    """Market data sources"""
    MARKET_DATA_API = "market_data_api"
    NEWS_FEED = "news_feed"
    SOCIAL_MEDIA = "social_media"
    EARNINGS_CALENDAR = "earnings_calendar"
    ECONOMIC_CALENDAR = "economic_calendar"
    INSIDER_FILINGS = "insider_filings"
    CENTRAL_BANK_FEEDS = "central_bank_feeds"
    ALTERNATIVE_DATA = "alternative_data"

@dataclass
class MarketEvent:
    """Market event data structure"""
    event_id: str
    event_type: EventType
    priority: EventPriority
    symbol: Optional[str]
    title: str
    description: str
    impact_score: float  # -1.0 to 1.0
    confidence: float    # 0.0 to 1.0
    source: DataSource
    timestamp: datetime
    related_symbols: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed: bool = False
    alert_sent: bool = False

@dataclass
class MarketSentiment:
    """Market sentiment analysis"""
    symbol: str
    sentiment_score: float  # -1.0 to 1.0
    sentiment_label: str    # negative, neutral, positive
    confidence: float
    news_count: int
    social_mentions: int
    sentiment_trend: Dict[str, float]
    key_themes: List[str]
    influencer_sentiment: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class EconomicIndicator:
    """Economic indicator data"""
    indicator_name: str
    country: str
    actual_value: Optional[float]
    forecast_value: Optional[float]
    previous_value: Optional[float]
    surprise_factor: float  # (actual - forecast) / forecast
    importance: str         # low, medium, high
    impact_assessment: Dict[str, float]
    release_time: datetime
    next_release: Optional[datetime]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class VolatilityAlert:
    """Volatility spike alert"""
    symbol: str
    current_volatility: float
    average_volatility: float
    volatility_percentile: float
    spike_magnitude: float
    duration_minutes: int
    trigger_threshold: float
    related_events: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class CorrelationBreak:
    """Correlation breakdown alert"""
    symbol_pair: Tuple[str, str]
    current_correlation: float
    historical_correlation: float
    correlation_change: float
    break_duration: timedelta
    significance_level: float
    potential_causes: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class MarketIntelligenceReport:
    """Comprehensive market intelligence report"""
    report_id: str
    timeframe: str
    market_regime: MarketRegime
    key_events: List[MarketEvent]
    sentiment_overview: Dict[str, MarketSentiment]
    economic_releases: List[EconomicIndicator]
    volatility_alerts: List[VolatilityAlert]
    correlation_breaks: List[CorrelationBreak]
    actionable_insights: List[str]
    risk_alerts: List[str]
    opportunities: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

class MarketIntelligenceEngine:
    """Real-Time Market Intelligence and Event-Driven Analytics Engine"""
    
    def __init__(self, database_pool: asyncpg.Pool, redis_client: Optional[Redis] = None):
        self.database_pool = database_pool
        self.redis_client = redis_client
        
        # Event processing
        self.event_queue = asyncio.Queue()
        self.event_handlers = {}
        self.event_history = deque(maxlen=10000)
        
        # Real-time data streams
        self.price_streams = {}
        self.news_streams = {}
        self.sentiment_cache = {}
        
        # Market regime detection
        self.current_regime = MarketRegime.SIDEWAYS_MARKET
        self.regime_history = []
        
        # Alert thresholds
        self.volatility_threshold = 2.0  # 2 standard deviations
        self.correlation_break_threshold = 0.3
        self.news_sentiment_threshold = 0.7
        
        # Data sources configuration
        self.data_sources = {
            'news_apis': ['alpha_vantage', 'news_api', 'benzinga'],
            'social_media': ['twitter', 'reddit', 'stocktwits'],
            'economic_calendars': ['trading_economics', 'investing_com'],
            'insider_data': ['sec_filings', 'insider_monkey']
        }
        
        # Watchlists
        self.watchlist_symbols = []
        self.economic_indicators = []
        self.central_bank_events = []
        
        logger.info("Market Intelligence Engine initialized")
    
    async def initialize(self):
        """Initialize market intelligence engine"""
        try:
            logger.info("Initializing Market Intelligence Engine...")
            
            # Load configuration
            await self._load_configuration()
            
            # Initialize event handlers
            await self._register_event_handlers()
            
            # Start real-time data streams
            await self._initialize_data_streams()
            
            # Load historical regime data
            await self._load_historical_regimes()
            
            logger.info("Market Intelligence Engine initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Market Intelligence Engine: {str(e)}")
            return False
    
    async def _load_configuration(self):
        """Load engine configuration"""
        # Load watchlist symbols
        self.watchlist_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
            'SPY', 'QQQ', 'IWM', 'VIX', 'DXY', 'GLD', 'TLT', 'HYG'
        ]
        
        # Load economic indicators to monitor
        self.economic_indicators = [
            {'name': 'Non-Farm Payrolls', 'country': 'US', 'importance': 'high'},
            {'name': 'CPI', 'country': 'US', 'importance': 'high'},
            {'name': 'GDP', 'country': 'US', 'importance': 'high'},
            {'name': 'Federal Funds Rate', 'country': 'US', 'importance': 'critical'},
            {'name': 'Unemployment Rate', 'country': 'US', 'importance': 'medium'},
            {'name': 'PMI Manufacturing', 'country': 'US', 'importance': 'medium'},
            {'name': 'Consumer Confidence', 'country': 'US', 'importance': 'medium'}
        ]
        
        # Central bank events
        self.central_bank_events = [
            {'bank': 'Federal Reserve', 'type': 'FOMC Meeting'},
            {'bank': 'European Central Bank', 'type': 'Rate Decision'},
            {'bank': 'Bank of Japan', 'type': 'Policy Meeting'},
            {'bank': 'Bank of England', 'type': 'MPC Meeting'}
        ]
        
        logger.info("Configuration loaded")
    
    async def _register_event_handlers(self):
        """Register event handlers for different event types"""
        self.event_handlers = {
            EventType.EARNINGS_SURPRISE: self._handle_earnings_surprise,
            EventType.NEWS_SENTIMENT: self._handle_news_sentiment,
            EventType.ECONOMIC_INDICATOR: self._handle_economic_indicator,
            EventType.CENTRAL_BANK_ACTION: self._handle_central_bank_action,
            EventType.GEOPOLITICAL_EVENT: self._handle_geopolitical_event,
            EventType.CORPORATE_ACTION: self._handle_corporate_action,
            EventType.INSIDER_TRADING: self._handle_insider_trading,
            EventType.VOLATILITY_SPIKE: self._handle_volatility_spike,
            EventType.CORRELATION_BREAK: self._handle_correlation_break,
            EventType.REGIME_CHANGE: self._handle_regime_change,
            EventType.TECHNICAL_BREAKOUT: self._handle_technical_breakout,
            EventType.VOLUME_ANOMALY: self._handle_volume_anomaly
        }
        
        logger.info("Event handlers registered")
    
    async def _initialize_data_streams(self):
        """Initialize real-time data streams"""
        # In production, this would connect to actual data providers
        # For demo, we'll simulate data streams
        
        logger.info("Data streams initialized (simulated)")
    
    async def _load_historical_regimes(self):
        """Load historical market regime data"""
        # Simulate historical regime data
        regimes = [
            {'regime': MarketRegime.BULL_MARKET, 'start': '2020-03-23', 'end': '2022-01-03'},
            {'regime': MarketRegime.BEAR_MARKET, 'start': '2022-01-04', 'end': '2022-10-12'},
            {'regime': MarketRegime.SIDEWAYS_MARKET, 'start': '2022-10-13', 'end': 'present'}
        ]
        
        self.regime_history = regimes
        logger.info("Historical regime data loaded")
    
    async def process_market_event(self, event: MarketEvent) -> Dict[str, Any]:
        """Process a market event and trigger appropriate actions"""
        try:
            # Add to event queue
            await self.event_queue.put(event)
            
            # Get appropriate handler
            handler = self.event_handlers.get(event.event_type)
            if not handler:
                logger.warning(f"No handler for event type: {event.event_type}")
                return {'status': 'no_handler', 'event_id': event.event_id}
            
            # Process event
            result = await handler(event)
            
            # Update event status
            event.processed = True
            
            # Add to history
            self.event_history.append(event)
            
            # Cache in Redis if available
            if self.redis_client:
                await self.redis_client.setex(
                    f"market_event:{event.event_id}",
                    3600,  # 1 hour
                    json.dumps({
                        'event_type': event.event_type.value,
                        'symbol': event.symbol,
                        'impact_score': event.impact_score,
                        'timestamp': event.timestamp.isoformat()
                    })
                )
            
            return {
                'status': 'processed',
                'event_id': event.event_id,
                'handler_result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process market event {event.event_id}: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    async def _handle_earnings_surprise(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle earnings surprise events"""
        surprise_factor = event.metadata.get('surprise_factor', 0.0)
        
        # Determine impact based on surprise magnitude
        if abs(surprise_factor) > 0.2:  # >20% surprise
            priority = EventPriority.HIGH
            alert_needed = True
        elif abs(surprise_factor) > 0.1:  # >10% surprise
            priority = EventPriority.MEDIUM
            alert_needed = True
        else:
            priority = EventPriority.LOW
            alert_needed = False
        
        return {
            'action': 'earnings_analysis',
            'priority': priority.value,
            'alert_needed': alert_needed,
            'related_analysis': ['price_target_revision', 'sector_impact']
        }
    
    async def _handle_news_sentiment(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle news sentiment events"""
        sentiment_score = event.impact_score
        
        # Analyze sentiment strength
        if abs(sentiment_score) > 0.8:
            significance = 'high'
        elif abs(sentiment_score) > 0.5:
            significance = 'medium'
        else:
            significance = 'low'
        
        return {
            'action': 'sentiment_analysis',
            'significance': significance,
            'sentiment_direction': 'positive' if sentiment_score > 0 else 'negative',
            'related_analysis': ['momentum_analysis', 'option_flow']
        }
    
    async def _handle_economic_indicator(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle economic indicator releases"""
        surprise_factor = event.metadata.get('surprise_factor', 0.0)
        importance = event.metadata.get('importance', 'medium')
        
        market_impact = abs(surprise_factor) * {'high': 1.0, 'medium': 0.7, 'low': 0.4}[importance]
        
        return {
            'action': 'economic_analysis',
            'market_impact': market_impact,
            'sectors_affected': event.metadata.get('affected_sectors', []),
            'fed_policy_implications': market_impact > 0.5
        }
    
    async def _handle_central_bank_action(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle central bank actions"""
        return {
            'action': 'monetary_policy_analysis',
            'priority': EventPriority.CRITICAL.value,
            'broad_market_impact': True,
            'currency_impact': True,
            'bond_market_impact': True
        }
    
    async def _handle_geopolitical_event(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle geopolitical events"""
        severity = event.metadata.get('severity', 'medium')
        
        return {
            'action': 'geopolitical_analysis',
            'severity': severity,
            'safe_haven_impact': severity in ['high', 'critical'],
            'sector_rotation_likely': True
        }
    
    async def _handle_corporate_action(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle corporate actions"""
        action_type = event.metadata.get('action_type', 'unknown')
        
        return {
            'action': 'corporate_action_analysis',
            'action_type': action_type,
            'dividend_impact': action_type in ['dividend', 'special_dividend'],
            'ownership_change': action_type in ['merger', 'acquisition', 'spinoff']
        }
    
    async def _handle_insider_trading(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle insider trading events"""
        trade_type = event.metadata.get('trade_type', 'unknown')
        volume = event.metadata.get('volume', 0)
        
        significance = 'high' if volume > 1000000 else 'medium' if volume > 100000 else 'low'
        
        return {
            'action': 'insider_analysis',
            'trade_type': trade_type,
            'significance': significance,
            'sentiment_signal': 'bullish' if trade_type == 'buy' else 'bearish'
        }
    
    async def _handle_volatility_spike(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle volatility spike events"""
        magnitude = event.metadata.get('spike_magnitude', 1.0)
        
        return {
            'action': 'volatility_analysis',
            'magnitude': magnitude,
            'risk_assessment_needed': magnitude > 2.0,
            'option_flow_analysis': True
        }
    
    async def _handle_correlation_break(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle correlation breakdown events"""
        return {
            'action': 'correlation_analysis',
            'regime_change_indicator': True,
            'portfolio_rebalancing_needed': True,
            'risk_model_update_needed': True
        }
    
    async def _handle_regime_change(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle market regime change events"""
        new_regime = event.metadata.get('new_regime', 'unknown')
        
        return {
            'action': 'regime_change_analysis',
            'new_regime': new_regime,
            'strategy_adjustment_needed': True,
            'risk_parameters_update': True,
            'broad_communication_needed': True
        }
    
    async def _handle_technical_breakout(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle technical breakout events"""
        breakout_type = event.metadata.get('breakout_type', 'resistance')
        
        return {
            'action': 'technical_analysis',
            'breakout_type': breakout_type,
            'momentum_confirmation': True,
            'target_calculation_needed': True
        }
    
    async def _handle_volume_anomaly(self, event: MarketEvent) -> Dict[str, Any]:
        """Handle volume anomaly events"""
        volume_multiple = event.metadata.get('volume_multiple', 1.0)
        
        return {
            'action': 'volume_analysis',
            'volume_multiple': volume_multiple,
            'institutional_activity': volume_multiple > 3.0,
            'news_catalyst_search': True
        }
    
    async def analyze_market_sentiment(self, symbol: str) -> MarketSentiment:
        """Analyze real-time market sentiment for a symbol"""
        try:
            # Simulate sentiment analysis
            np.random.seed(hash(symbol) % 2**32)
            
            # Generate realistic sentiment data
            base_sentiment = np.random.normal(0, 0.3)  # Slightly neutral bias
            sentiment_score = np.clip(base_sentiment, -1.0, 1.0)
            
            # Determine sentiment label
            if sentiment_score > 0.2:
                sentiment_label = 'positive'
            elif sentiment_score < -0.2:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
            
            # Generate supporting metrics
            confidence = np.random.uniform(0.6, 0.95)
            news_count = np.random.randint(5, 50)
            social_mentions = np.random.randint(100, 5000)
            
            # Sentiment trend (last 7 days)
            sentiment_trend = {}
            for i in range(7):
                date = datetime.now() - timedelta(days=i)
                trend_score = sentiment_score + np.random.normal(0, 0.1)
                sentiment_trend[date.strftime('%Y-%m-%d')] = np.clip(trend_score, -1.0, 1.0)
            
            # Key themes
            themes = ['earnings', 'product_launch', 'regulation', 'competition', 'market_conditions']
            key_themes = np.random.choice(themes, size=np.random.randint(1, 4), replace=False).tolist()
            
            # Influencer sentiment
            influencer_sentiment = {
                'analysts': np.random.normal(sentiment_score, 0.2),
                'media': np.random.normal(sentiment_score, 0.15),
                'social_influencers': np.random.normal(sentiment_score, 0.25)
            }
            
            return MarketSentiment(
                symbol=symbol,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                confidence=confidence,
                news_count=news_count,
                social_mentions=social_mentions,
                sentiment_trend=sentiment_trend,
                key_themes=key_themes,
                influencer_sentiment=influencer_sentiment
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze sentiment for {symbol}: {str(e)}")
            raise
    
    async def monitor_economic_indicators(self) -> List[EconomicIndicator]:
        """Monitor and analyze economic indicators"""
        indicators = []
        
        for indicator_config in self.economic_indicators:
            try:
                # Simulate economic indicator data
                np.random.seed(hash(indicator_config['name']) % 2**32)
                
                # Generate realistic economic data
                forecast_value = np.random.uniform(50, 200)  # Base forecast
                actual_value = forecast_value * (1 + np.random.normal(0, 0.05))  # 5% typical deviation
                previous_value = forecast_value * (1 + np.random.normal(0, 0.03))
                
                # Calculate surprise factor
                surprise_factor = (actual_value - forecast_value) / forecast_value if forecast_value != 0 else 0
                
                # Impact assessment
                impact_assessment = {
                    'equity_markets': surprise_factor * 0.5,
                    'bond_markets': -surprise_factor * 0.3,  # Inverse relationship
                    'currency': surprise_factor * 0.4,
                    'commodities': surprise_factor * 0.2
                }
                
                # Next release (monthly for most indicators)
                next_release = datetime.now() + timedelta(days=30)
                
                indicator = EconomicIndicator(
                    indicator_name=indicator_config['name'],
                    country=indicator_config['country'],
                    actual_value=actual_value,
                    forecast_value=forecast_value,
                    previous_value=previous_value,
                    surprise_factor=surprise_factor,
                    importance=indicator_config['importance'],
                    impact_assessment=impact_assessment,
                    release_time=datetime.now(),
                    next_release=next_release
                )
                
                indicators.append(indicator)
                
            except Exception as e:
                logger.warning(f"Failed to process indicator {indicator_config['name']}: {str(e)}")
                continue
        
        return indicators
    
    async def detect_volatility_spikes(self, symbols: List[str]) -> List[VolatilityAlert]:
        """Detect volatility spikes across symbols"""
        alerts = []
        
        for symbol in symbols:
            try:
                # Simulate volatility data
                np.random.seed(hash(symbol) % 2**32)
                
                average_volatility = np.random.uniform(0.15, 0.35)  # 15-35% annual vol
                current_volatility = average_volatility * np.random.uniform(0.5, 3.0)  # Spike simulation
                
                # Calculate percentile
                volatility_percentile = np.random.uniform(0, 100)
                
                # Check if spike exceeds threshold
                spike_magnitude = current_volatility / average_volatility
                
                if spike_magnitude > self.volatility_threshold:
                    # Generate related events
                    possible_events = ['earnings_miss', 'news_release', 'analyst_downgrade', 'sector_rotation']
                    related_events = np.random.choice(possible_events, size=np.random.randint(0, 3), replace=False).tolist()
                    
                    alert = VolatilityAlert(
                        symbol=symbol,
                        current_volatility=current_volatility,
                        average_volatility=average_volatility,
                        volatility_percentile=volatility_percentile,
                        spike_magnitude=spike_magnitude,
                        duration_minutes=np.random.randint(5, 120),
                        trigger_threshold=self.volatility_threshold,
                        related_events=related_events
                    )
                    
                    alerts.append(alert)
                    
            except Exception as e:
                logger.warning(f"Failed to check volatility for {symbol}: {str(e)}")
                continue
        
        return alerts
    
    async def detect_correlation_breaks(self, symbol_pairs: List[Tuple[str, str]]) -> List[CorrelationBreak]:
        """Detect correlation breakdowns between asset pairs"""
        breaks = []
        
        for pair in symbol_pairs:
            try:
                symbol1, symbol2 = pair
                
                # Simulate correlation data
                np.random.seed(hash(f"{symbol1}_{symbol2}") % 2**32)
                
                historical_correlation = np.random.uniform(0.3, 0.9)  # Typically correlated assets
                current_correlation = historical_correlation + np.random.normal(0, 0.3)
                current_correlation = np.clip(current_correlation, -1.0, 1.0)
                
                correlation_change = abs(current_correlation - historical_correlation)
                
                if correlation_change > self.correlation_break_threshold:
                    # Generate potential causes
                    possible_causes = [
                        'divergent_earnings', 'sector_rotation', 'idiosyncratic_news',
                        'regulatory_changes', 'market_structure_changes'
                    ]
                    potential_causes = np.random.choice(possible_causes, size=np.random.randint(1, 3), replace=False).tolist()
                    
                    break_duration = timedelta(hours=np.random.randint(1, 48))
                    significance_level = correlation_change / self.correlation_break_threshold
                    
                    correlation_break = CorrelationBreak(
                        symbol_pair=pair,
                        current_correlation=current_correlation,
                        historical_correlation=historical_correlation,
                        correlation_change=correlation_change,
                        break_duration=break_duration,
                        significance_level=significance_level,
                        potential_causes=potential_causes
                    )
                    
                    breaks.append(correlation_break)
                    
            except Exception as e:
                logger.warning(f"Failed to check correlation for {pair}: {str(e)}")
                continue
        
        return breaks
    
    async def detect_market_regime_change(self) -> Optional[MarketRegime]:
        """Detect market regime changes"""
        try:
            # Simulate regime detection logic
            # In production, this would analyze multiple indicators:
            # - VIX levels, term structure
            # - Cross-asset correlations
            # - Market breadth
            # - Economic indicators
            
            np.random.seed(int(datetime.now().timestamp()) % 2**32)
            
            # Simulate regime indicators
            vix_level = np.random.uniform(12, 45)
            correlation_level = np.random.uniform(0.3, 0.9)
            market_breadth = np.random.uniform(0.2, 0.8)
            
            # Simple regime classification
            if vix_level > 30:
                new_regime = MarketRegime.CRISIS_MODE
            elif vix_level > 25:
                new_regime = MarketRegime.HIGH_VOLATILITY
            elif vix_level < 15:
                new_regime = MarketRegime.LOW_VOLATILITY
            elif market_breadth > 0.6:
                new_regime = MarketRegime.BULL_MARKET
            elif market_breadth < 0.4:
                new_regime = MarketRegime.BEAR_MARKET
            else:
                new_regime = MarketRegime.SIDEWAYS_MARKET
            
            # Check if regime has changed
            if new_regime != self.current_regime:
                logger.info(f"Market regime change detected: {self.current_regime} -> {new_regime}")
                
                # Update current regime
                old_regime = self.current_regime
                self.current_regime = new_regime
                
                # Add to history
                regime_change = {
                    'from_regime': old_regime.value,
                    'to_regime': new_regime.value,
                    'timestamp': datetime.utcnow(),
                    'indicators': {
                        'vix_level': vix_level,
                        'correlation_level': correlation_level,
                        'market_breadth': market_breadth
                    }
                }
                self.regime_history.append(regime_change)
                
                return new_regime
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to detect regime change: {str(e)}")
            return None
    
    async def generate_market_intelligence_report(self, timeframe: str = "daily") -> MarketIntelligenceReport:
        """Generate comprehensive market intelligence report"""
        try:
            report_id = f"market_intel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Collect recent events
            recent_events = list(self.event_history)[-50:]  # Last 50 events
            key_events = [event for event in recent_events if event.priority in [EventPriority.CRITICAL, EventPriority.HIGH]]
            
            # Analyze sentiment for watchlist
            sentiment_overview = {}
            for symbol in self.watchlist_symbols[:5]:  # Top 5 for demo
                try:
                    sentiment = await self.analyze_market_sentiment(symbol)
                    sentiment_overview[symbol] = sentiment
                except Exception as e:
                    logger.warning(f"Failed to get sentiment for {symbol}: {str(e)}")
            
            # Get economic releases
            economic_releases = await self.monitor_economic_indicators()
            
            # Check for volatility alerts
            volatility_alerts = await self.detect_volatility_spikes(self.watchlist_symbols[:8])
            
            # Check for correlation breaks
            symbol_pairs = [('SPY', 'QQQ'), ('GLD', 'TLT'), ('AAPL', 'MSFT'), ('VIX', 'SPY')]
            correlation_breaks = await self.detect_correlation_breaks(symbol_pairs)
            
            # Generate actionable insights
            actionable_insights = await self._generate_actionable_insights(
                key_events, sentiment_overview, economic_releases, volatility_alerts
            )
            
            # Generate risk alerts
            risk_alerts = await self._generate_risk_alerts(volatility_alerts, correlation_breaks)
            
            # Generate opportunities
            opportunities = await self._generate_opportunities(sentiment_overview, economic_releases)
            
            return MarketIntelligenceReport(
                report_id=report_id,
                timeframe=timeframe,
                market_regime=self.current_regime,
                key_events=key_events,
                sentiment_overview=sentiment_overview,
                economic_releases=economic_releases,
                volatility_alerts=volatility_alerts,
                correlation_breaks=correlation_breaks,
                actionable_insights=actionable_insights,
                risk_alerts=risk_alerts,
                opportunities=opportunities
            )
            
        except Exception as e:
            logger.error(f"Failed to generate market intelligence report: {str(e)}")
            raise
    
    async def _generate_actionable_insights(self, events, sentiment, economic, volatility) -> List[str]:
        """Generate actionable insights from market data"""
        insights = []
        
        # Event-based insights
        if any(event.event_type == EventType.EARNINGS_SURPRISE for event in events):
            insights.append("Multiple earnings surprises detected - review sector rotation opportunities")
        
        # Sentiment-based insights
        strong_sentiment_symbols = [
            symbol for symbol, sent in sentiment.items() 
            if abs(sent.sentiment_score) > 0.6
        ]
        if strong_sentiment_symbols:
            insights.append(f"Strong sentiment signals in: {', '.join(strong_sentiment_symbols)}")
        
        # Economic insights
        high_impact_indicators = [
            indicator for indicator in economic 
            if indicator.importance == 'high' and abs(indicator.surprise_factor) > 0.1
        ]
        if high_impact_indicators:
            insights.append("Significant economic surprises may drive market movements")
        
        # Volatility insights
        high_vol_symbols = [alert.symbol for alert in volatility if alert.spike_magnitude > 2.5]
        if high_vol_symbols:
            insights.append(f"Elevated volatility in: {', '.join(high_vol_symbols)}")
        
        return insights
    
    async def _generate_risk_alerts(self, volatility_alerts, correlation_breaks) -> List[str]:
        """Generate risk alerts"""
        alerts = []
        
        if len(volatility_alerts) > 3:
            alerts.append("Widespread volatility spikes detected - increase risk monitoring")
        
        if correlation_breaks:
            alerts.append("Correlation breakdowns may signal regime change - review risk models")
        
        if self.current_regime in [MarketRegime.CRISIS_MODE, MarketRegime.HIGH_VOLATILITY]:
            alerts.append(f"Current regime ({self.current_regime.value}) requires heightened risk management")
        
        return alerts
    
    async def _generate_opportunities(self, sentiment, economic) -> List[str]:
        """Generate opportunity alerts"""
        opportunities = []
        
        # Sentiment-based opportunities
        undervalued_sentiment = [
            symbol for symbol, sent in sentiment.items()
            if sent.sentiment_score < -0.4 and sent.confidence > 0.7
        ]
        if undervalued_sentiment:
            opportunities.append(f"Potential contrarian opportunities: {', '.join(undervalued_sentiment)}")
        
        # Economic opportunities
        positive_surprises = [
            indicator for indicator in economic
            if indicator.surprise_factor > 0.1 and indicator.importance in ['high', 'critical']
        ]
        if positive_surprises:
            opportunities.append("Positive economic surprises may support risk assets")
        
        return opportunities
    
    async def get_market_intelligence_status(self) -> Dict[str, Any]:
        """Get current status of market intelligence engine"""
        return {
            'engine_status': 'operational',
            'current_regime': self.current_regime.value,
            'watchlist_symbols': len(self.watchlist_symbols),
            'economic_indicators_monitored': len(self.economic_indicators),
            'events_in_queue': self.event_queue.qsize(),
            'events_processed_today': len([e for e in self.event_history if e.timestamp.date() == datetime.now().date()]),
            'data_sources': self.data_sources,
            'alert_thresholds': {
                'volatility_threshold': self.volatility_threshold,
                'correlation_break_threshold': self.correlation_break_threshold,
                'news_sentiment_threshold': self.news_sentiment_threshold
            },
            'last_regime_change': self.regime_history[-1] if self.regime_history else None,
            'last_update': datetime.utcnow().isoformat()
        }

# Example usage and testing
async def main():
    """Example usage of Market Intelligence Engine"""
    print("🔍 Real-Time Market Intelligence Engine Demo")
    print("=" * 70)
    
    # Initialize market intelligence engine
    market_intel = MarketIntelligenceEngine(database_pool=None)
    await market_intel.initialize()
    
    # Generate sample market event
    sample_event = MarketEvent(
        event_id="earnings_aapl_20250819",
        event_type=EventType.EARNINGS_SURPRISE,
        priority=EventPriority.HIGH,
        symbol="AAPL",
        title="Apple Q3 Earnings Beat",
        description="Apple reports Q3 EPS of $1.40 vs $1.35 expected",
        impact_score=0.6,
        confidence=0.9,
        source=DataSource.EARNINGS_CALENDAR,
        timestamp=datetime.utcnow(),
        related_symbols=["AAPL", "QQQ", "SPY"],
        metadata={"surprise_factor": 0.04, "revenue_surprise": 0.02}
    )
    
    # Process event
    result = await market_intel.process_market_event(sample_event)
    print(f"📊 Processed event: {result}")
    
    # Analyze sentiment
    sentiment = await market_intel.analyze_market_sentiment("AAPL")
    print(f"💭 AAPL Sentiment: {sentiment.sentiment_label} ({sentiment.sentiment_score:.2f})")
    
    # Generate intelligence report
    report = await market_intel.generate_market_intelligence_report()
    print(f"📈 Intelligence Report: {len(report.key_events)} events, {len(report.actionable_insights)} insights")
    
    print("✅ Market Intelligence Engine demo completed!")

if __name__ == "__main__":
    asyncio.run(main())