"""
ML Data Collector Module für aktienanalyse-ökosystem
Sammelt Performance-, Trading- und System-Daten für ML-Training und Inference
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import statistics

# Import base module pattern
try:
    from shared.single_function_module_base import SingleFunctionModuleBase, ModuleConfig
except ImportError:
    class SingleFunctionModuleBase:
        def __init__(self, config): self.config = config
        async def process_event(self, event): pass
    class ModuleConfig: pass

# Import Event-Bus components
try:
    from shared.redis_event_bus import Event, EventPriority
    from shared.redis_event_system_integration import aktienanalyse_event_bus
except ImportError:
    # Mock classes for development
    class Event:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)
    class EventPriority:
        HIGH = "high"
        NORMAL = "normal"
    
    class MockEventBus:
        async def publish_system_health_event(self, *args): return True
        async def publish_analysis_complete(self, *args): return True
    
    aktienanalyse_event_bus = MockEventBus()

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
class MLDataPoint:
    """Represents a single data point for ML training/inference"""
    timestamp: datetime
    data_type: str  # 'performance', 'trading', 'system', 'market'
    source_service: str
    data_payload: Dict[str, Any]
    labels: Dict[str, Any] = None  # For supervised learning
    metadata: Dict[str, Any] = None


@dataclass
class MLDataCollection:
    """Collection of ML data points with aggregation info"""
    collection_id: str
    collection_type: str
    start_time: datetime
    end_time: datetime
    data_points: List[MLDataPoint]
    aggregated_features: Dict[str, float]
    quality_score: float


class MLDataCollectorModule(SingleFunctionModuleBase):
    """
    Single Function: Sammelt und strukturiert Daten für ML-Training und Inference
    
    Hauptaufgaben:
    - Event-Bus Integration für Real-time Data Collection
    - Historical Data Aggregation 
    - Multi-Source Data Integration
    - Data Quality Assessment
    - ML-Ready Data Formatting
    """
    
    def __init__(self, config: ModuleConfig = None):
        super().__init__(config or ModuleConfig())
        self.logger = logger.bind(module="ml_data_collector")
        
        # Data collection buffers (ring buffers for memory efficiency)
        self.buffer_size = 10000  # Adjust based on memory constraints
        self.performance_data = deque(maxlen=self.buffer_size)
        self.trading_data = deque(maxlen=self.buffer_size)
        self.system_data = deque(maxlen=self.buffer_size)
        self.market_data = deque(maxlen=self.buffer_size)
        
        # Collection statistics
        self.collection_stats = {
            'total_collected': 0,
            'by_type': defaultdict(int),
            'by_source': defaultdict(int),
            'quality_scores': deque(maxlen=100),
            'collection_rate_per_hour': deque(maxlen=24)
        }
        
        # Data quality thresholds
        self.quality_thresholds = {
            'completeness': 0.95,  # 95% of expected fields present
            'timeliness': 300,     # Data not older than 5 minutes
            'consistency': 0.90,   # 90% consistency with historical patterns
            'accuracy': 0.85       # 85% accuracy based on validation rules
        }
        
        # Active collection targets
        self.collection_targets = {
            'performance': ['throughput_eps', 'latency_p99_ms', 'error_rate', 'memory_usage_mb'],
            'trading': ['symbol', 'price', 'volume', 'recommendation', 'confidence'],
            'system': ['service_health', 'cpu_usage', 'memory_usage', 'active_connections'],
            'market': ['price_movement', 'volatility', 'market_indicators', 'trend_direction']
        }
        
        self.is_collecting = False
        self.collection_task = None
        
    async def collect_ml_data(self, data_types: List[str] = None, 
                             duration_minutes: int = 60,
                             quality_threshold: float = 0.8) -> MLDataCollection:
        """
        Main function: Sammelt ML-Daten für Training/Inference
        
        Args:
            data_types: List of data types to collect ['performance', 'trading', 'system', 'market']
            duration_minutes: How long to collect data
            quality_threshold: Minimum quality score for collected data
            
        Returns:
            MLDataCollection: Structured ML data collection
        """
        collection_id = f"ml_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        if data_types is None:
            data_types = ['performance', 'trading', 'system', 'market']
        
        self.logger.info("Starting ML data collection", 
                        collection_id=collection_id,
                        data_types=data_types,
                        duration_minutes=duration_minutes)
        
        try:
            # Start active data collection
            await self._start_active_collection(data_types)
            
            # Collect for specified duration
            await asyncio.sleep(duration_minutes * 60)
            
            # Stop collection and process data
            await self._stop_active_collection()
            
            # Aggregate collected data points
            collected_points = await self._aggregate_collected_data(data_types)
            
            # Calculate aggregated features
            aggregated_features = await self._calculate_aggregated_features(collected_points)
            
            # Assess data quality
            quality_score = await self._assess_data_quality(collected_points)
            
            end_time = datetime.now()
            
            # Create ML data collection
            ml_collection = MLDataCollection(
                collection_id=collection_id,
                collection_type="training_batch",
                start_time=start_time,
                end_time=end_time,
                data_points=collected_points,
                aggregated_features=aggregated_features,
                quality_score=quality_score
            )
            
            # Validate quality threshold
            if quality_score < quality_threshold:
                self.logger.warning("Data quality below threshold",
                                  quality_score=quality_score,
                                  threshold=quality_threshold)
            
            # Publish collection complete event
            await self._publish_collection_complete_event(ml_collection)
            
            self.logger.info("ML data collection completed",
                           collection_id=collection_id,
                           data_points=len(collected_points),
                           quality_score=quality_score)
            
            return ml_collection
            
        except Exception as e:
            self.logger.error("ML data collection failed", error=str(e))
            await self._stop_active_collection()
            raise
    
    async def _start_active_collection(self, data_types: List[str]):
        """Start active data collection from Event-Bus"""
        self.is_collecting = True
        self.collection_task = asyncio.create_task(
            self._collection_loop(data_types)
        )
        
    async def _stop_active_collection(self):
        """Stop active data collection"""
        self.is_collecting = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
    
    async def _collection_loop(self, data_types: List[str]):
        """Main collection loop - simulates Event-Bus data collection"""
        try:
            while self.is_collecting:
                # Simulate collecting different types of data
                for data_type in data_types:
                    await self._collect_single_data_type(data_type)
                
                await asyncio.sleep(5)  # Collect every 5 seconds
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error("Collection loop error", error=str(e))
    
    async def _collect_single_data_type(self, data_type: str):
        """Collect data for a single data type"""
        try:
            # Simulate data collection based on type
            if data_type == 'performance':
                data_point = await self._collect_performance_data()
                self.performance_data.append(data_point)
            elif data_type == 'trading':
                data_point = await self._collect_trading_data()
                self.trading_data.append(data_point)
            elif data_type == 'system':
                data_point = await self._collect_system_data()
                self.system_data.append(data_point)
            elif data_type == 'market':
                data_point = await self._collect_market_data()
                self.market_data.append(data_point)
            
            # Update collection statistics
            self.collection_stats['total_collected'] += 1
            self.collection_stats['by_type'][data_type] += 1
            
        except Exception as e:
            self.logger.warning(f"Failed to collect {data_type} data", error=str(e))
    
    async def _collect_performance_data(self) -> MLDataPoint:
        """Collect performance data"""
        # Simulate performance data collection
        data_payload = {
            'throughput_eps': 150.5 + (statistics.random() - 0.5) * 50,
            'latency_p99_ms': 45.2 + (statistics.random() - 0.5) * 20,
            'error_rate': 0.001 + statistics.random() * 0.01,
            'memory_usage_mb': 384 + (statistics.random() - 0.5) * 100,
            'cpu_usage_percent': 35.0 + (statistics.random() - 0.5) * 30
        }
        
        return MLDataPoint(
            timestamp=datetime.now(),
            data_type='performance',
            source_service='system_monitor',
            data_payload=data_payload,
            metadata={'collection_method': 'event_bus_stream'}
        )
    
    async def _collect_trading_data(self) -> MLDataPoint:
        """Collect trading data"""
        symbols = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL']
        symbol = symbols[int(statistics.random() * len(symbols))]
        
        data_payload = {
            'symbol': symbol,
            'price': 150.0 + (statistics.random() - 0.5) * 100,
            'volume': int(1000000 * (1 + statistics.random())),
            'recommendation': ['BUY', 'SELL', 'HOLD'][int(statistics.random() * 3)],
            'confidence': 0.5 + statistics.random() * 0.5,
            'analysis_score': 5.0 + statistics.random() * 5.0
        }
        
        return MLDataPoint(
            timestamp=datetime.now(),
            data_type='trading',
            source_service='intelligent_core_service',
            data_payload=data_payload,
            labels={'price_direction': 1 if statistics.random() > 0.5 else -1}
        )
    
    async def _collect_system_data(self) -> MLDataPoint:
        """Collect system data"""
        services = ['account-service', 'order-service', 'data-analysis-service', 
                   'intelligent-core-service', 'market-data-service', 'frontend-service']
        service = services[int(statistics.random() * len(services))]
        
        data_payload = {
            'service_name': service,
            'service_health': ['healthy', 'degraded', 'critical'][int(statistics.random() * 3)],
            'response_time_ms': 50 + statistics.random() * 200,
            'active_connections': int(10 + statistics.random() * 100),
            'queue_depth': int(statistics.random() * 1000)
        }
        
        return MLDataPoint(
            timestamp=datetime.now(),
            data_type='system',
            source_service=service,
            data_payload=data_payload,
            metadata={'health_score': statistics.random()}
        )
    
    async def _collect_market_data(self) -> MLDataPoint:
        """Collect market data"""
        data_payload = {
            'market_trend': ['bullish', 'bearish', 'sideways'][int(statistics.random() * 3)],
            'volatility_index': 15.0 + statistics.random() * 20,
            'volume_trend': statistics.random() - 0.5,
            'sentiment_score': statistics.random(),
            'technical_indicators': {
                'rsi': 30 + statistics.random() * 40,
                'macd': (statistics.random() - 0.5) * 2,
                'moving_avg_20': 150 + (statistics.random() - 0.5) * 50
            }
        }
        
        return MLDataPoint(
            timestamp=datetime.now(),
            data_type='market',
            source_service='market_data_service',
            data_payload=data_payload,
            metadata={'market_session': 'regular_hours'}
        )
    
    async def _aggregate_collected_data(self, data_types: List[str]) -> List[MLDataPoint]:
        """Aggregate all collected data points"""
        all_data_points = []
        
        for data_type in data_types:
            if data_type == 'performance':
                all_data_points.extend(list(self.performance_data))
            elif data_type == 'trading':
                all_data_points.extend(list(self.trading_data))
            elif data_type == 'system':
                all_data_points.extend(list(self.system_data))
            elif data_type == 'market':
                all_data_points.extend(list(self.market_data))
        
        # Sort by timestamp
        all_data_points.sort(key=lambda dp: dp.timestamp)
        
        return all_data_points
    
    async def _calculate_aggregated_features(self, data_points: List[MLDataPoint]) -> Dict[str, float]:
        """Calculate aggregated features from collected data points"""
        if not data_points:
            return {}
        
        # Group by data type
        by_type = defaultdict(list)
        for dp in data_points:
            by_type[dp.data_type].append(dp)
        
        aggregated = {}
        
        # Performance aggregations
        if 'performance' in by_type:
            perf_data = by_type['performance']
            throughputs = [dp.data_payload.get('throughput_eps', 0) for dp in perf_data]
            latencies = [dp.data_payload.get('latency_p99_ms', 0) for dp in perf_data]
            
            if throughputs:
                aggregated['avg_throughput_eps'] = statistics.mean(throughputs)
                aggregated['max_throughput_eps'] = max(throughputs)
            if latencies:
                aggregated['avg_latency_p99_ms'] = statistics.mean(latencies)
                aggregated['max_latency_p99_ms'] = max(latencies)
        
        # Trading aggregations
        if 'trading' in by_type:
            trading_data = by_type['trading']
            confidences = [dp.data_payload.get('confidence', 0) for dp in trading_data]
            scores = [dp.data_payload.get('analysis_score', 0) for dp in trading_data]
            
            if confidences:
                aggregated['avg_trading_confidence'] = statistics.mean(confidences)
            if scores:
                aggregated['avg_analysis_score'] = statistics.mean(scores)
        
        # System aggregations
        if 'system' in by_type:
            system_data = by_type['system']
            response_times = [dp.data_payload.get('response_time_ms', 0) for dp in system_data]
            
            if response_times:
                aggregated['avg_response_time_ms'] = statistics.mean(response_times)
                aggregated['system_health_score'] = 1.0 - (statistics.mean(response_times) / 1000)
        
        # Market aggregations
        if 'market' in by_type:
            market_data = by_type['market']
            volatilities = [dp.data_payload.get('volatility_index', 0) for dp in market_data]
            sentiments = [dp.data_payload.get('sentiment_score', 0) for dp in market_data]
            
            if volatilities:
                aggregated['avg_volatility'] = statistics.mean(volatilities)
            if sentiments:
                aggregated['avg_market_sentiment'] = statistics.mean(sentiments)
        
        # Cross-type features
        aggregated['total_data_points'] = len(data_points)
        aggregated['collection_duration_minutes'] = (
            (max(dp.timestamp for dp in data_points) - min(dp.timestamp for dp in data_points)).total_seconds() / 60
        ) if len(data_points) > 1 else 0
        
        return aggregated
    
    async def _assess_data_quality(self, data_points: List[MLDataPoint]) -> float:
        """Assess the quality of collected data"""
        if not data_points:
            return 0.0
        
        quality_scores = []
        
        # Completeness check
        complete_points = sum(1 for dp in data_points if self._is_data_complete(dp))
        completeness_score = complete_points / len(data_points)
        quality_scores.append(completeness_score)
        
        # Timeliness check
        now = datetime.now()
        timely_points = sum(1 for dp in data_points 
                           if (now - dp.timestamp).total_seconds() < self.quality_thresholds['timeliness'])
        timeliness_score = timely_points / len(data_points)
        quality_scores.append(timeliness_score)
        
        # Consistency check (simplified)
        consistency_score = self._check_data_consistency(data_points)
        quality_scores.append(consistency_score)
        
        # Overall quality score
        overall_quality = statistics.mean(quality_scores)
        
        # Update quality statistics
        self.collection_stats['quality_scores'].append(overall_quality)
        
        return overall_quality
    
    def _is_data_complete(self, data_point: MLDataPoint) -> bool:
        """Check if a data point has all required fields"""
        required_fields = self.collection_targets.get(data_point.data_type, [])
        if not required_fields:
            return True  # No specific requirements
        
        present_fields = sum(1 for field in required_fields 
                           if field in data_point.data_payload)
        completeness = present_fields / len(required_fields)
        
        return completeness >= self.quality_thresholds['completeness']
    
    def _check_data_consistency(self, data_points: List[MLDataPoint]) -> float:
        """Check data consistency (simplified implementation)"""
        if len(data_points) < 2:
            return 1.0
        
        # Simple consistency check: variance in similar data types
        consistency_scores = []
        
        by_type = defaultdict(list)
        for dp in data_points:
            by_type[dp.data_type].append(dp)
        
        for data_type, points in by_type.items():
            if len(points) < 2:
                continue
            
            # Check consistency within numeric fields
            for field in self.collection_targets.get(data_type, []):
                values = [dp.data_payload.get(field, 0) for dp in points 
                         if isinstance(dp.data_payload.get(field), (int, float))]
                
                if len(values) > 1:
                    # Use coefficient of variation as consistency measure
                    mean_val = statistics.mean(values)
                    if mean_val != 0:
                        cv = statistics.stdev(values) / abs(mean_val)
                        consistency_scores.append(max(0, 1 - cv))  # Lower CV = higher consistency
        
        return statistics.mean(consistency_scores) if consistency_scores else 0.8
    
    async def _publish_collection_complete_event(self, ml_collection: MLDataCollection):
        """Publish ML data collection complete event to Event-Bus"""
        try:
            event_data = {
                'collection_id': ml_collection.collection_id,
                'collection_type': ml_collection.collection_type,
                'data_points_count': len(ml_collection.data_points),
                'quality_score': ml_collection.quality_score,
                'aggregated_features_count': len(ml_collection.aggregated_features),
                'collection_duration_minutes': (ml_collection.end_time - ml_collection.start_time).total_seconds() / 60,
                'timestamp': ml_collection.end_time.isoformat()
            }
            
            success = await aktienanalyse_event_bus.publish_analysis_complete(
                symbol="SYSTEM",
                analysis_type="ml_data_collection",
                results=event_data,
                confidence=ml_collection.quality_score
            )
            
            if success:
                self.logger.info("ML data collection event published", 
                               collection_id=ml_collection.collection_id)
            else:
                self.logger.warning("Failed to publish ML data collection event")
                
        except Exception as e:
            self.logger.error("Error publishing ML data collection event", error=str(e))
    
    def get_collection_statistics(self) -> Dict[str, Any]:
        """Get current collection statistics"""
        avg_quality = statistics.mean(self.collection_stats['quality_scores']) if self.collection_stats['quality_scores'] else 0
        
        return {
            'total_collected': self.collection_stats['total_collected'],
            'by_type': dict(self.collection_stats['by_type']),
            'by_source': dict(self.collection_stats['by_source']),
            'average_quality_score': avg_quality,
            'is_actively_collecting': self.is_collecting,
            'buffer_utilization': {
                'performance': len(self.performance_data),
                'trading': len(self.trading_data),
                'system': len(self.system_data),
                'market': len(self.market_data)
            }
        }


# Module factory function
def create_ml_data_collector_module(config: ModuleConfig = None) -> MLDataCollectorModule:
    """Factory function to create ML Data Collector Module"""
    return MLDataCollectorModule(config)


# Example usage and testing
async def test_ml_data_collector():
    """Test function for ML Data Collector Module"""
    print("🧪 Testing ML Data Collector Module")
    
    # Create module
    collector = create_ml_data_collector_module()
    
    # Test data collection
    print("📊 Starting data collection test...")
    
    try:
        # Collect data for 30 seconds (for testing)
        ml_collection = await collector.collect_ml_data(
            data_types=['performance', 'trading', 'system'],
            duration_minutes=0.5,  # 30 seconds for testing
            quality_threshold=0.7
        )
        
        print(f"✅ Data collection completed:")
        print(f"   Collection ID: {ml_collection.collection_id}")
        print(f"   Data Points: {len(ml_collection.data_points)}")
        print(f"   Quality Score: {ml_collection.quality_score:.3f}")
        print(f"   Features: {len(ml_collection.aggregated_features)}")
        
        # Show statistics
        stats = collector.get_collection_statistics()
        print(f"\n📈 Collection Statistics:")
        print(f"   Total Collected: {stats['total_collected']}")
        print(f"   Average Quality: {stats['average_quality_score']:.3f}")
        print(f"   By Type: {stats['by_type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run module test
    import asyncio
    asyncio.run(test_ml_data_collector())
    print("🎯 ML Data Collector Module test completed")