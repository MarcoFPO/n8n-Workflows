"""
Feature Engineering Module für aktienanalyse-ökosystem
Bereitet gesammelte Daten für ML-Modelle auf durch Feature Extraction und Engineering
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

import asyncio
import json
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics

# Import ML Data Point from Data Collector
try:
    from .ml_data_collector_module import MLDataPoint, MLDataCollection
except ImportError:
    # PRODUCTION CODE MUST NOT USE MOCK CLASSES
    raise ImportError("Production code requires proper module imports - mock classes are not allowed for production deployment")

# Import production-ready base module pattern
try:
    from shared.single_function_module_base import SingleFunctionModuleBase, ModuleConfig
except ImportError:
    # Production fallback - import from shared location
    import sys
    sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')
    from shared.single_function_module_base import SingleFunctionModuleBase, ModuleConfig

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


@dataclass
class FeatureSet:
    """Represents a set of engineered features"""
    feature_id: str
    source_collection_id: str
    feature_type: str  # 'technical', 'statistical', 'temporal', 'cross_system'
    features: Dict[str, float]
    feature_metadata: Dict[str, Any]
    created_at: datetime
    quality_score: float


@dataclass
class EngineeringResult:
    """Result of feature engineering process"""
    result_id: str
    original_collection: MLDataCollection
    feature_sets: List[FeatureSet]
    total_features: int
    processing_time_seconds: float
    quality_metrics: Dict[str, float]


class FeatureEngineeringModule(SingleFunctionModuleBase):
    """
    Single Function: Bereitet gesammelte ML-Daten für Modelle auf durch Feature Engineering
    
    Hauptaufgaben:
    - Technical Indicator Feature Extraction
    - Statistical Feature Engineering  
    - Time-Series Feature Creation
    - Cross-System Feature Correlation
    - Feature Quality Assessment
    """
    
    def __init__(self, config: ModuleConfig = None):
        super().__init__(config or ModuleConfig())
        self.logger = logger.bind(module="feature_engineering")
        
        # Feature engineering configurations
        self.technical_indicators = {
            'sma_periods': [5, 10, 20, 50],
            'ema_periods': [12, 26],
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bollinger_period': 20,
            'bollinger_std': 2
        }
        
        self.statistical_windows = {
            'short_term': 5,   # 5 data points
            'medium_term': 20, # 20 data points
            'long_term': 50    # 50 data points
        }
        
        # Feature cache for incremental updates
        self.feature_cache = {}
        
        # Feature importance tracking
        self.feature_importance = defaultdict(float)
        
        # Engineering statistics
        self.engineering_stats = {
            'total_engineered': 0,
            'by_type': defaultdict(int),
            'processing_times': deque(maxlen=100),
            'quality_scores': deque(maxlen=100)
        }
    
    async def engineer_features(self, ml_collection: MLDataCollection,
                               feature_types: List[str] = None,
                               include_cross_system: bool = True) -> EngineeringResult:
        """
        Main function: Engineers features from ML data collection
        
        Args:
            ml_collection: Input ML data collection
            feature_types: Types of features to engineer ['technical', 'statistical', 'temporal', 'cross_system']
            include_cross_system: Whether to include cross-system correlation features
            
        Returns:
            EngineeringResult: Comprehensive feature engineering results
        """
        start_time = datetime.now()
        result_id = f"feature_eng_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        if feature_types is None:
            feature_types = ['technical', 'statistical', 'temporal']
            if include_cross_system:
                feature_types.append('cross_system')
        
        self.logger.info("Starting feature engineering",
                        result_id=result_id,
                        collection_id=ml_collection.collection_id,
                        data_points=len(ml_collection.data_points),
                        feature_types=feature_types)
        
        try:
            feature_sets = []
            
            # Technical Indicator Features
            if 'technical' in feature_types:
                technical_features = await self._engineer_technical_features(ml_collection)
                if technical_features:
                    feature_sets.append(technical_features)
            
            # Statistical Features
            if 'statistical' in feature_types:
                statistical_features = await self._engineer_statistical_features(ml_collection)
                if statistical_features:
                    feature_sets.append(statistical_features)
            
            # Temporal Features
            if 'temporal' in feature_types:
                temporal_features = await self._engineer_temporal_features(ml_collection)
                if temporal_features:
                    feature_sets.append(temporal_features)
            
            # Cross-System Correlation Features
            if 'cross_system' in feature_types:
                cross_system_features = await self._engineer_cross_system_features(ml_collection)
                if cross_system_features:
                    feature_sets.append(cross_system_features)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Calculate total features and quality metrics
            total_features = sum(len(fs.features) for fs in feature_sets)
            quality_metrics = await self._calculate_feature_quality(feature_sets)
            
            # Create engineering result
            result = EngineeringResult(
                result_id=result_id,
                original_collection=ml_collection,
                feature_sets=feature_sets,
                total_features=total_features,
                processing_time_seconds=processing_time,
                quality_metrics=quality_metrics
            )
            
            # Update statistics
            self.engineering_stats['total_engineered'] += total_features
            self.engineering_stats['processing_times'].append(processing_time)
            self.engineering_stats['quality_scores'].append(quality_metrics.get('overall_quality', 0))
            
            for fs in feature_sets:
                self.engineering_stats['by_type'][fs.feature_type] += len(fs.features)
            
            self.logger.info("Feature engineering completed",
                           result_id=result_id,
                           total_features=total_features,
                           processing_time_seconds=processing_time,
                           quality_score=quality_metrics.get('overall_quality', 0))
            
            return result
            
        except Exception as e:
            self.logger.error("Feature engineering failed", error=str(e))
            raise
    
    async def _engineer_technical_features(self, ml_collection: MLDataCollection) -> Optional[FeatureSet]:
        """Engineer technical indicator features from trading/market data"""
        
        # Extract trading and market data
        trading_data = [dp for dp in ml_collection.data_points if dp.data_type == 'trading']
        market_data = [dp for dp in ml_collection.data_points if dp.data_type == 'market']
        
        if not (trading_data or market_data):
            return None
        
        features = {}
        
        # Price-based features from trading data
        if trading_data:
            prices = [dp.data_payload.get('price', 0) for dp in trading_data if 'price' in dp.data_payload]
            volumes = [dp.data_payload.get('volume', 0) for dp in trading_data if 'volume' in dp.data_payload]
            confidences = [dp.data_payload.get('confidence', 0) for dp in trading_data if 'confidence' in dp.data_payload]
            
            if prices:
                # Moving averages
                for period in self.technical_indicators['sma_periods']:
                    if len(prices) >= period:
                        sma = statistics.mean(prices[-period:])
                        features[f'sma_{period}'] = sma
                        features[f'price_sma_{period}_ratio'] = prices[-1] / sma if sma != 0 else 1.0
                
                # Price momentum
                if len(prices) >= 2:
                    features['price_momentum_1'] = (prices[-1] - prices[-2]) / prices[-2] if prices[-2] != 0 else 0
                
                if len(prices) >= 5:
                    features['price_momentum_5'] = (prices[-1] - prices[-5]) / prices[-5] if prices[-5] != 0 else 0
                
                # Price volatility (rolling standard deviation)
                if len(prices) >= 10:
                    recent_prices = prices[-10:]
                    features['price_volatility_10'] = statistics.stdev(recent_prices) if len(recent_prices) > 1 else 0
                
                # RSI approximation
                if len(prices) >= self.technical_indicators['rsi_period']:
                    rsi = self._calculate_rsi(prices, self.technical_indicators['rsi_period'])
                    features['rsi'] = rsi
                
                # MACD approximation
                if len(prices) >= max(self.technical_indicators['macd_fast'], self.technical_indicators['macd_slow']):
                    macd, signal = self._calculate_macd(prices)
                    features['macd'] = macd
                    features['macd_signal'] = signal
                    features['macd_histogram'] = macd - signal
            
            # Volume-based features
            if volumes:
                features['avg_volume'] = statistics.mean(volumes)
                if len(volumes) > 1:
                    features['volume_volatility'] = statistics.stdev(volumes)
                    features['volume_trend'] = (volumes[-1] - volumes[0]) / volumes[0] if volumes[0] != 0 else 0
            
            # Confidence-based features
            if confidences:
                features['avg_confidence'] = statistics.mean(confidences)
                features['confidence_trend'] = (confidences[-1] - confidences[0]) if len(confidences) > 1 else 0
        
        # Market indicator features
        if market_data:
            volatility_indices = [dp.data_payload.get('volatility_index', 0) for dp in market_data]
            sentiment_scores = [dp.data_payload.get('sentiment_score', 0) for dp in market_data]
            
            if volatility_indices:
                features['avg_market_volatility'] = statistics.mean(volatility_indices)
                features['market_volatility_trend'] = (volatility_indices[-1] - volatility_indices[0]) if len(volatility_indices) > 1 else 0
            
            if sentiment_scores:
                features['avg_market_sentiment'] = statistics.mean(sentiment_scores)
                features['sentiment_momentum'] = (sentiment_scores[-1] - sentiment_scores[0]) if len(sentiment_scores) > 1 else 0
        
        if not features:
            return None
        
        return FeatureSet(
            feature_id=f"technical_{ml_collection.collection_id}",
            source_collection_id=ml_collection.collection_id,
            feature_type='technical',
            features=features,
            feature_metadata={
                'trading_data_points': len(trading_data),
                'market_data_points': len(market_data),
                'indicators_used': list(self.technical_indicators.keys())
            },
            created_at=datetime.now(),
            quality_score=self._assess_feature_quality(features, 'technical')
        )
    
    async def _engineer_statistical_features(self, ml_collection: MLDataCollection) -> Optional[FeatureSet]:
        """Engineer statistical features from all data types"""
        
        if not ml_collection.data_points:
            return None
        
        features = {}
        
        # Group data by type
        by_type = defaultdict(list)
        for dp in ml_collection.data_points:
            by_type[dp.data_type].append(dp)
        
        # Statistical features for each data type
        for data_type, data_points in by_type.items():
            
            # Extract numeric values from data payloads
            numeric_fields = self._extract_numeric_fields(data_points)
            
            for field_name, values in numeric_fields.items():
                if len(values) < 2:
                    continue
                
                prefix = f"{data_type}_{field_name}"
                
                # Basic statistics
                features[f"{prefix}_mean"] = statistics.mean(values)
                features[f"{prefix}_median"] = statistics.median(values)
                features[f"{prefix}_std"] = statistics.stdev(values) if len(values) > 1 else 0
                features[f"{prefix}_min"] = min(values)
                features[f"{prefix}_max"] = max(values)
                features[f"{prefix}_range"] = max(values) - min(values)
                
                # Percentiles
                sorted_values = sorted(values)
                features[f"{prefix}_p25"] = self._percentile(sorted_values, 0.25)
                features[f"{prefix}_p75"] = self._percentile(sorted_values, 0.75)
                features[f"{prefix}_iqr"] = features[f"{prefix}_p75"] - features[f"{prefix}_p25"]
                
                # Distribution shape
                features[f"{prefix}_skewness"] = self._calculate_skewness(values)
                features[f"{prefix}_kurtosis"] = self._calculate_kurtosis(values)
                
                # Trend analysis for time-ordered data
                if len(values) >= 3:
                    features[f"{prefix}_trend_slope"] = self._calculate_trend_slope(values)
                    features[f"{prefix}_trend_r2"] = self._calculate_trend_r2(values)
        
        # Cross-type statistical relationships
        if len(by_type) > 1:
            features.update(self._calculate_cross_type_statistics(by_type))
        
        if not features:
            return None
        
        return FeatureSet(
            feature_id=f"statistical_{ml_collection.collection_id}",
            source_collection_id=ml_collection.collection_id,
            feature_type='statistical',
            features=features,
            feature_metadata={
                'data_types_analyzed': list(by_type.keys()),
                'total_data_points': len(ml_collection.data_points),
                'statistical_windows': self.statistical_windows
            },
            created_at=datetime.now(),
            quality_score=self._assess_feature_quality(features, 'statistical')
        )
    
    async def _engineer_temporal_features(self, ml_collection: MLDataCollection) -> Optional[FeatureSet]:
        """Engineer time-based features from data timestamps"""
        
        if not ml_collection.data_points:
            return None
        
        features = {}
        
        # Sort data points by timestamp
        sorted_data = sorted(ml_collection.data_points, key=lambda dp: dp.timestamp)
        
        # Collection timespan features
        start_time = sorted_data[0].timestamp
        end_time = sorted_data[-1].timestamp
        duration_seconds = (end_time - start_time).total_seconds()
        
        features['collection_duration_seconds'] = duration_seconds
        features['collection_duration_minutes'] = duration_seconds / 60
        features['data_points_per_minute'] = len(sorted_data) / max(1, duration_seconds / 60)
        
        # Time distribution features
        timestamps = [dp.timestamp for dp in sorted_data]
        time_deltas = [(timestamps[i] - timestamps[i-1]).total_seconds() 
                      for i in range(1, len(timestamps))]
        
        if time_deltas:
            features['avg_time_delta_seconds'] = statistics.mean(time_deltas)
            features['time_delta_std'] = statistics.stdev(time_deltas) if len(time_deltas) > 1 else 0
            features['time_consistency_score'] = 1.0 / (1.0 + features['time_delta_std'])
        
        # Time-of-day features (for trading systems)
        hours = [dp.timestamp.hour for dp in sorted_data]
        features['avg_hour_of_day'] = statistics.mean(hours)
        features['trading_hours_ratio'] = sum(1 for h in hours if 9 <= h <= 16) / len(hours)
        features['after_hours_ratio'] = 1 - features['trading_hours_ratio']
        
        # Day-of-week features
        weekdays = [dp.timestamp.weekday() for dp in sorted_data]  # 0=Monday, 6=Sunday
        features['avg_day_of_week'] = statistics.mean(weekdays)
        features['weekday_ratio'] = sum(1 for d in weekdays if d < 5) / len(weekdays)
        features['weekend_ratio'] = 1 - features['weekday_ratio']
        
        # Data freshness features
        now = datetime.now()
        data_ages = [(now - dp.timestamp).total_seconds() for dp in sorted_data]
        features['newest_data_age_seconds'] = min(data_ages)
        features['oldest_data_age_seconds'] = max(data_ages)
        features['avg_data_age_seconds'] = statistics.mean(data_ages)
        
        # Temporal patterns in data values (example with performance data)
        performance_data = [dp for dp in sorted_data if dp.data_type == 'performance']
        if performance_data:
            throughputs = [dp.data_payload.get('throughput_eps', 0) for dp in performance_data]
            if len(throughputs) >= 3:
                # Time-based performance trends
                features['performance_time_correlation'] = self._calculate_time_correlation(
                    [dp.timestamp for dp in performance_data], throughputs
                )
        
        return FeatureSet(
            feature_id=f"temporal_{ml_collection.collection_id}",
            source_collection_id=ml_collection.collection_id,
            feature_type='temporal',
            features=features,
            feature_metadata={
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'total_timespan_minutes': duration_seconds / 60
            },
            created_at=datetime.now(),
            quality_score=self._assess_feature_quality(features, 'temporal')
        )
    
    async def _engineer_cross_system_features(self, ml_collection: MLDataCollection) -> Optional[FeatureSet]:
        """Engineer cross-system correlation features"""
        
        # Group data by system/service
        by_service = defaultdict(list)
        for dp in ml_collection.data_points:
            by_service[dp.source_service].append(dp)
        
        if len(by_service) < 2:
            return None  # Need at least 2 services for cross-system features
        
        features = {}
        
        # Service interaction features
        features['unique_services_count'] = len(by_service)
        features['max_service_data_points'] = max(len(points) for points in by_service.values())
        features['min_service_data_points'] = min(len(points) for points in by_service.values())
        features['service_data_balance'] = features['min_service_data_points'] / features['max_service_data_points']
        
        # Cross-service correlations (simplified)
        service_metrics = {}
        for service_name, data_points in by_service.items():
            # Extract representative metrics for each service
            service_metrics[service_name] = self._extract_service_metrics(data_points)
        
        # Calculate correlations between services
        correlation_features = self._calculate_service_correlations(service_metrics)
        features.update(correlation_features)
        
        # System health aggregations
        system_health_scores = []
        for service_name, data_points in by_service.items():
            for dp in data_points:
                if dp.data_type == 'system':
                    health_score = self._extract_health_score(dp)
                    if health_score is not None:
                        system_health_scores.append(health_score)
        
        if system_health_scores:
            features['overall_system_health'] = statistics.mean(system_health_scores)
            features['system_health_variance'] = statistics.stdev(system_health_scores) if len(system_health_scores) > 1 else 0
            features['unhealthy_services_ratio'] = sum(1 for score in system_health_scores if score < 0.7) / len(system_health_scores)
        
        # Performance vs Trading correlation
        performance_metrics = []
        trading_metrics = []
        
        for dp in ml_collection.data_points:
            if dp.data_type == 'performance':
                perf_score = dp.data_payload.get('throughput_eps', 0)
                performance_metrics.append(perf_score)
            elif dp.data_type == 'trading':
                trading_score = dp.data_payload.get('confidence', 0) * dp.data_payload.get('analysis_score', 0)
                trading_metrics.append(trading_score)
        
        if performance_metrics and trading_metrics:
            # Align lengths for correlation
            min_len = min(len(performance_metrics), len(trading_metrics))
            perf_aligned = performance_metrics[:min_len]
            trading_aligned = trading_metrics[:min_len]
            
            if min_len >= 3:
                correlation = self._calculate_correlation(perf_aligned, trading_aligned)
                features['performance_trading_correlation'] = correlation
        
        return FeatureSet(
            feature_id=f"cross_system_{ml_collection.collection_id}",
            source_collection_id=ml_collection.collection_id,
            feature_type='cross_system',
            features=features,
            feature_metadata={
                'services_analyzed': list(by_service.keys()),
                'cross_correlations_calculated': len(correlation_features),
                'system_health_points': len(system_health_scores)
            },
            created_at=datetime.now(),
            quality_score=self._assess_feature_quality(features, 'cross_system')
        )
    
    # Helper methods for calculations
    
    def _extract_numeric_fields(self, data_points: List[MLDataPoint]) -> Dict[str, List[float]]:
        """Extract numeric fields from data points"""
        numeric_fields = defaultdict(list)
        
        for dp in data_points:
            for field_name, value in dp.data_payload.items():
                if isinstance(value, (int, float)) and not math.isnan(value):
                    numeric_fields[field_name].append(float(value))
        
        return numeric_fields
    
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile of sorted values"""
        if not sorted_values:
            return 0.0
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _calculate_skewness(self, values: List[float]) -> float:
        """Calculate skewness (simplified)"""
        if len(values) < 3:
            return 0.0
        
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 1.0
        
        if std_val == 0:
            return 0.0
        
        skewness = sum(((x - mean_val) / std_val) ** 3 for x in values) / len(values)
        return skewness
    
    def _calculate_kurtosis(self, values: List[float]) -> float:
        """Calculate kurtosis (simplified)"""
        if len(values) < 4:
            return 0.0
        
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 1.0
        
        if std_val == 0:
            return 0.0
        
        kurtosis = sum(((x - mean_val) / std_val) ** 4 for x in values) / len(values) - 3
        return kurtosis
    
    def _calculate_trend_slope(self, values: List[float]) -> float:
        """Calculate trend slope using simple linear regression"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_vals = list(range(n))
        
        # Simple linear regression
        x_mean = statistics.mean(x_vals)
        y_mean = statistics.mean(values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, values))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _calculate_trend_r2(self, values: List[float]) -> float:
        """Calculate R-squared for trend fit"""
        if len(values) < 2:
            return 0.0
        
        slope = self._calculate_trend_slope(values)
        n = len(values)
        x_vals = list(range(n))
        y_mean = statistics.mean(values)
        
        # Predicted values
        y_pred = [slope * x + (y_mean - slope * statistics.mean(x_vals)) for x in x_vals]
        
        # R-squared calculation
        ss_res = sum((y - y_pred) ** 2 for y, y_pred in zip(values, y_pred))
        ss_tot = sum((y - y_mean) ** 2 for y in values)
        
        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
    
    def _calculate_cross_type_statistics(self, by_type: Dict[str, List[MLDataPoint]]) -> Dict[str, float]:
        """Calculate statistical relationships between different data types"""
        features = {}
        
        # Data type distribution
        total_points = sum(len(points) for points in by_type.values())
        for data_type, points in by_type.items():
            features[f"{data_type}_ratio"] = len(points) / total_points
        
        # Entropy of data type distribution
        ratios = [len(points) / total_points for points in by_type.values()]
        entropy = -sum(r * math.log2(r) for r in ratios if r > 0)
        features['data_type_entropy'] = entropy
        
        return features
    
    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        """Calculate RSI (simplified)"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = statistics.mean(gains[-period:])
        avg_loss = statistics.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> Tuple[float, float]:
        """Calculate MACD and signal line (simplified)"""
        fast_period = self.technical_indicators['macd_fast']
        slow_period = self.technical_indicators['macd_slow']
        signal_period = self.technical_indicators['macd_signal']
        
        if len(prices) < slow_period:
            return 0.0, 0.0
        
        # Simplified moving averages for MACD
        fast_ma = statistics.mean(prices[-fast_period:])
        slow_ma = statistics.mean(prices[-slow_period:])
        
        macd = fast_ma - slow_ma
        
        # Simplified signal line (should be EMA of MACD)
        signal = macd * 0.8  # Simplified approximation
        
        return macd, signal
    
    def _extract_service_metrics(self, data_points: List[MLDataPoint]) -> List[float]:
        """Extract representative metrics from service data points"""
        metrics = []
        
        for dp in data_points:
            # Extract a composite metric based on data type
            if dp.data_type == 'performance':
                metric = dp.data_payload.get('throughput_eps', 0) / max(1, dp.data_payload.get('latency_p99_ms', 1))
            elif dp.data_type == 'trading':
                metric = dp.data_payload.get('confidence', 0) * dp.data_payload.get('analysis_score', 0)
            elif dp.data_type == 'system':
                metric = 1.0 / max(1, dp.data_payload.get('response_time_ms', 1))
            else:
                metric = 1.0
            
            metrics.append(metric)
        
        return metrics
    
    def _calculate_service_correlations(self, service_metrics: Dict[str, List[float]]) -> Dict[str, float]:
        """Calculate correlations between services"""
        correlations = {}
        
        service_names = list(service_metrics.keys())
        
        for i, service1 in enumerate(service_names):
            for service2 in service_names[i+1:]:
                metrics1 = service_metrics[service1]
                metrics2 = service_metrics[service2]
                
                if len(metrics1) >= 3 and len(metrics2) >= 3:
                    # Align lengths
                    min_len = min(len(metrics1), len(metrics2))
                    aligned1 = metrics1[:min_len]
                    aligned2 = metrics2[:min_len]
                    
                    correlation = self._calculate_correlation(aligned1, aligned2)
                    correlations[f"correlation_{service1}_{service2}"] = correlation
        
        return correlations
    
    def _calculate_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        x_var = sum((x - x_mean) ** 2 for x in x_values)
        y_var = sum((y - y_mean) ** 2 for y in y_values)
        
        denominator = math.sqrt(x_var * y_var)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _calculate_time_correlation(self, timestamps: List[datetime], values: List[float]) -> float:
        """Calculate correlation between time and values"""
        if len(timestamps) != len(values) or len(timestamps) < 3:
            return 0.0
        
        # Convert timestamps to numeric values (seconds since start)
        start_time = min(timestamps)
        time_values = [(ts - start_time).total_seconds() for ts in timestamps]
        
        return self._calculate_correlation(time_values, values)
    
    def _extract_health_score(self, system_dp: MLDataPoint) -> Optional[float]:
        """Extract health score from system data point"""
        health_status = system_dp.data_payload.get('service_health', 'unknown')
        
        health_mapping = {
            'healthy': 1.0,
            'degraded': 0.6,
            'critical': 0.2,
            'unknown': 0.5
        }
        
        return health_mapping.get(health_status)
    
    def _assess_feature_quality(self, features: Dict[str, float], feature_type: str) -> float:
        """Assess quality of engineered features"""
        if not features:
            return 0.0
        
        quality_scores = []
        
        # Feature completeness
        expected_features = {
            'technical': 15,
            'statistical': 30,
            'temporal': 10,
            'cross_system': 8
        }
        
        completeness = min(1.0, len(features) / expected_features.get(feature_type, 10))
        quality_scores.append(completeness)
        
        # Feature validity (no NaN/inf values)
        valid_features = sum(1 for value in features.values() 
                           if isinstance(value, (int, float)) and math.isfinite(value))
        validity = valid_features / len(features) if features else 0
        quality_scores.append(validity)
        
        # Feature diversity (range of values)
        if len(features) > 1:
            feature_values = [v for v in features.values() if isinstance(v, (int, float)) and math.isfinite(v)]
            if feature_values:
                value_range = max(feature_values) - min(feature_values)
                diversity = min(1.0, value_range / 100)  # Normalized diversity score
                quality_scores.append(diversity)
        
        return statistics.mean(quality_scores)
    
    async def _calculate_feature_quality(self, feature_sets: List[FeatureSet]) -> Dict[str, float]:
        """Calculate overall feature quality metrics"""
        if not feature_sets:
            return {'overall_quality': 0.0}
        
        individual_qualities = [fs.quality_score for fs in feature_sets]
        total_features = sum(len(fs.features) for fs in feature_sets)
        
        return {
            'overall_quality': statistics.mean(individual_qualities),
            'min_quality': min(individual_qualities),
            'max_quality': max(individual_qualities),
            'quality_variance': statistics.stdev(individual_qualities) if len(individual_qualities) > 1 else 0,
            'total_features': total_features,
            'feature_sets_count': len(feature_sets)
        }
    
    def get_engineering_statistics(self) -> Dict[str, Any]:
        """Get feature engineering statistics"""
        avg_processing_time = statistics.mean(self.engineering_stats['processing_times']) if self.engineering_stats['processing_times'] else 0
        avg_quality = statistics.mean(self.engineering_stats['quality_scores']) if self.engineering_stats['quality_scores'] else 0
        
        return {
            'total_features_engineered': self.engineering_stats['total_engineered'],
            'by_type': dict(self.engineering_stats['by_type']),
            'average_processing_time_seconds': avg_processing_time,
            'average_quality_score': avg_quality,
            'cache_size': len(self.feature_cache),
            'supported_feature_types': ['technical', 'statistical', 'temporal', 'cross_system']
        }


# Module factory function
def create_feature_engineering_module(config: ModuleConfig = None) -> FeatureEngineeringModule:
    """Factory function to create Feature Engineering Module"""
    return FeatureEngineeringModule(config)


# Example usage and testing
async def test_feature_engineering():
    """Test function for Feature Engineering Module"""
    print("🧪 Testing Feature Engineering Module")
    
    # Create mock ML data collection
    mock_data_points = []
    
    # Add performance data points
    for i in range(10):
        dp = MLDataPoint(
            timestamp=datetime.now() - timedelta(minutes=i*5),
            data_type='performance',
            source_service='system_monitor',
            data_payload={
                'throughput_eps': 150.0 + (statistics.random() - 0.5) * 30,
                'latency_p99_ms': 45.0 + statistics.random() * 20,
                'memory_usage_mb': 400 + (statistics.random() - 0.5) * 50
            }
        )
        mock_data_points.append(dp)
    
    # Add trading data points
    for i in range(8):
        dp = MLDataPoint(
            timestamp=datetime.now() - timedelta(minutes=i*6),
            data_type='trading',
            source_service='intelligent_core_service',
            data_payload={
                'price': 150.0 + (statistics.random() - 0.5) * 20,
                'volume': int(1000000 * (1 + statistics.random())),
                'confidence': 0.7 + statistics.random() * 0.3,
                'analysis_score': 7.0 + statistics.random() * 2
            }
        )
        mock_data_points.append(dp)
    
    mock_collection = MLDataCollection(
        collection_id="test_collection_123",
        collection_type="test",
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now(),
        data_points=mock_data_points,
        aggregated_features={},
        quality_score=0.85
    )
    
    # Create module and test feature engineering
    engineer = create_feature_engineering_module()
    
    try:
        print("🔧 Starting feature engineering test...")
        
        result = await engineer.engineer_features(
            mock_collection,
            feature_types=['technical', 'statistical', 'temporal'],
            include_cross_system=True
        )
        
        print(f"✅ Feature engineering completed:")
        print(f"   Result ID: {result.result_id}")
        print(f"   Feature Sets: {len(result.feature_sets)}")
        print(f"   Total Features: {result.total_features}")
        print(f"   Processing Time: {result.processing_time_seconds:.2f}s")
        print(f"   Quality Score: {result.quality_metrics.get('overall_quality', 0):.3f}")
        
        # Show feature sets
        for fs in result.feature_sets:
            print(f"\n📊 {fs.feature_type.title()} Features ({len(fs.features)} features):")
            feature_names = list(fs.features.keys())[:5]  # Show first 5
            for name in feature_names:
                print(f"     {name}: {fs.features[name]:.3f}")
            if len(fs.features) > 5:
                print(f"     ... and {len(fs.features) - 5} more")
        
        # Show statistics
        stats = engineer.get_engineering_statistics()
        print(f"\n📈 Engineering Statistics:")
        print(f"   Total Features: {stats['total_features_engineered']}")
        print(f"   Average Processing Time: {stats['average_processing_time_seconds']:.2f}s")
        print(f"   Average Quality: {stats['average_quality_score']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run module test
    import asyncio
    asyncio.run(test_feature_engineering())
    print("🎯 Feature Engineering Module test completed")