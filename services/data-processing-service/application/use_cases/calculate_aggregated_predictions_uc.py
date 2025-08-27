"""
Data Processing Service - Calculate Aggregated Predictions Use Case
Timeframe-Specific Aggregation v7.1 - Clean Architecture Application Layer

Primary Use Case für Timeframe-spezifische Prediction Aggregation
SOLID Principles: Single Responsibility, Dependency Inversion, Open/Closed
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import time
from decimal import Decimal

# Domain Imports
from ...domain.entities.aggregated_prediction import AggregatedPrediction, TimeframeConfiguration, AggregationStrategy
from ...domain.services.timeframe_aggregation_service import TimeframeAggregationService
from ...domain.value_objects.quality_metrics import QualityMetrics

# Application Layer Imports
from ..dtos.aggregated_prediction_dto import (
    AggregatedPredictionDTO, 
    DetailedAggregatedPredictionDTO,
    AggregatedPredictionsResponseDTO,
    create_aggregated_prediction_dto_from_entity,
    create_detailed_aggregated_prediction_dto_from_entity
)

# Infrastructure Interfaces (Dependency Inversion)
from ..interfaces.aggregation_repository_interface import AggregationRepositoryInterface
from ..interfaces.prediction_repository_interface import PredictionRepositoryInterface
from ..interfaces.cache_service_interface import CacheServiceInterface
from ..interfaces.event_publisher_interface import EventPublisherInterface


class CalculateAggregatedPredictionsUseCase:
    """
    Primary Use Case für Timeframe-spezifische Prediction Aggregation
    
    RESPONSIBILITIES:
    - Orchestrate complete aggregation workflow
    - Validate input parameters und business rules
    - Coordinate between Domain Services und Infrastructure
    - Manage caching strategy für Performance
    - Publish domain events für Cross-Service Integration
    - Ensure Quality Thresholds werden eingehalten
    """
    
    def __init__(self,
                 aggregation_service: TimeframeAggregationService,
                 aggregation_repository: AggregationRepositoryInterface,
                 prediction_repository: PredictionRepositoryInterface,
                 cache_service: CacheServiceInterface,
                 event_publisher: EventPublisherInterface):
        """
        Dependency Injection Constructor
        
        SOLID Principle: Dependency Inversion - abhängig von Abstractions, nicht Concretions
        """
        self._aggregation_service = aggregation_service
        self._aggregation_repository = aggregation_repository
        self._prediction_repository = prediction_repository
        self._cache_service = cache_service
        self._event_publisher = event_publisher
        
        # Business Configuration
        self._cache_ttl_seconds = 300  # 5 minutes default TTL
        self._max_concurrent_calculations = 10
        self._quality_threshold = Decimal('0.60')  # Minimum acceptable quality
        self._performance_target_ms = 300  # Target response time
    
    async def execute(self, 
                     timeframe: str,
                     force_refresh: bool = False,
                     symbol_filter: Optional[str] = None,
                     limit: int = 15,
                     include_quality_details: bool = False) -> AggregatedPredictionsResponseDTO:
        """
        Main Execution Method für Aggregated Predictions Calculation
        
        WORKFLOW:
        1. Input Validation
        2. Cache Check (wenn nicht force_refresh)
        3. Fetch Raw Prediction Data
        4. Execute Parallel Aggregation Calculations
        5. Quality Control und Filtering
        6. Cache Results
        7. Publish Events
        8. Return Response DTO
        """
        start_time = time.time()
        
        try:
            # 1. Input Validation
            await self._validate_input_parameters(timeframe, symbol_filter, limit)
            
            # 2. Get Timeframe Configuration
            timeframe_config = self._get_timeframe_configuration(timeframe)
            
            # 3. Cache Check (wenn nicht force refresh)
            if not force_refresh:
                cached_response = await self._check_cache(timeframe, symbol_filter, limit, include_quality_details)
                if cached_response:
                    await self._publish_cache_hit_event(timeframe, len(cached_response.predictions))
                    return cached_response
            
            # 4. Fetch Raw Prediction Data
            raw_predictions = await self._fetch_raw_predictions(timeframe_config, symbol_filter, limit)
            
            if not raw_predictions:
                return self._create_empty_response(timeframe, start_time)
            
            # 5. Group by Symbol for Aggregation
            symbol_groups = self._group_predictions_by_symbol(raw_predictions)
            
            # 6. Execute Parallel Aggregation Calculations
            aggregated_predictions = await self._execute_parallel_aggregations(
                symbol_groups, timeframe_config
            )
            
            # 7. Quality Control und Filtering
            quality_filtered_predictions = self._apply_quality_filtering(aggregated_predictions)
            
            # 8. Sort und Limit Results
            final_predictions = self._sort_and_limit_results(quality_filtered_predictions, limit)
            
            # 9. Cache Results
            await self._cache_results(final_predictions, timeframe, symbol_filter)
            
            # 10. Create Response DTOs
            response_dtos = await self._create_response_dtos(
                final_predictions, include_quality_details
            )
            
            # 11. Build Response
            processing_duration = (time.time() - start_time) * 1000  # Convert to ms
            response = self._build_response(
                response_dtos, timeframe, len(raw_predictions), processing_duration, False
            )
            
            # 12. Publish Success Events
            await self._publish_calculation_completed_event(
                timeframe, len(final_predictions), processing_duration, True
            )
            
            return response
            
        except Exception as e:
            # Error Handling und Event Publishing
            processing_duration = (time.time() - start_time) * 1000
            await self._publish_calculation_failed_event(timeframe, str(e), processing_duration)
            raise
    
    async def _validate_input_parameters(self, 
                                       timeframe: str, 
                                       symbol_filter: Optional[str], 
                                       limit: int) -> None:
        """Validate Input Parameters entsprechend Business Rules"""
        
        valid_timeframes = {'1W', '1M', '3M', '6M', '1Y'}
        if timeframe not in valid_timeframes:
            raise ValueError(f"Invalid timeframe '{timeframe}'. Must be one of: {valid_timeframes}")
        
        if symbol_filter and (not symbol_filter.isupper() or len(symbol_filter) > 10):
            raise ValueError(f"Invalid symbol filter '{symbol_filter}'. Must be uppercase, max 10 chars")
        
        if not (1 <= limit <= 100):
            raise ValueError(f"Invalid limit '{limit}'. Must be between 1 and 100")
    
    def _get_timeframe_configuration(self, timeframe: str) -> TimeframeConfiguration:
        """Get Timeframe Configuration für Business Logic"""
        standard_configs = TimeframeConfiguration.create_standard_configurations()
        config = standard_configs.get(timeframe)
        
        if not config:
            raise ValueError(f"No configuration found for timeframe '{timeframe}'")
        
        return config
    
    async def _check_cache(self,
                          timeframe: str,
                          symbol_filter: Optional[str],
                          limit: int,
                          include_quality_details: bool) -> Optional[AggregatedPredictionsResponseDTO]:
        """Check Cache für existierende Results"""
        
        cache_key = self._build_cache_key(timeframe, symbol_filter, limit)
        
        try:
            cached_data = await self._cache_service.get(cache_key)
            if cached_data:
                # Deserialize und convert zu Response DTO
                cached_predictions = self._deserialize_cached_predictions(cached_data)
                
                # Convert zu Response DTOs mit gewünschtem Detail Level
                response_dtos = []
                for cached_pred in cached_predictions:
                    cached_pred.cache_hit = True  # Mark as cache hit
                    if include_quality_details:
                        dto = create_detailed_aggregated_prediction_dto_from_entity(cached_pred)
                    else:
                        dto = create_aggregated_prediction_dto_from_entity(cached_pred)
                    response_dtos.append(dto)
                
                return self._build_response(response_dtos, timeframe, len(cached_predictions), 0, True)
                
        except Exception as e:
            # Cache Miss oder Error - continue mit fresh calculation
            pass
        
        return None
    
    async def _fetch_raw_predictions(self,
                                   timeframe_config: TimeframeConfiguration,
                                   symbol_filter: Optional[str],
                                   limit: int) -> List[Dict[str, Any]]:
        """Fetch Raw Prediction Data from Repository"""
        
        # Calculate date range basierend auf timeframe configuration
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=timeframe_config.data_collection_period_days)
        
        try:
            raw_predictions = await self._prediction_repository.fetch_predictions_for_timeframe(
                start_date=start_date,
                end_date=end_date,
                symbol_filter=symbol_filter,
                limit=limit * 2  # Fetch more für better aggregation
            )
            
            return raw_predictions
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch raw predictions: {e}")
    
    def _group_predictions_by_symbol(self, raw_predictions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group Raw Predictions by Symbol für Aggregation"""
        
        symbol_groups = {}
        
        for prediction in raw_predictions:
            symbol = prediction.get('symbol', 'UNKNOWN')
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(prediction)
        
        return symbol_groups
    
    async def _execute_parallel_aggregations(self,
                                           symbol_groups: Dict[str, List[Dict[str, Any]]],
                                           timeframe_config: TimeframeConfiguration) -> List[AggregatedPrediction]:
        """Execute Parallel Aggregation Calculations für Performance"""
        
        aggregation_tasks = []
        
        for symbol, predictions in symbol_groups.items():
            if len(predictions) >= timeframe_config.min_data_threshold:
                task = self._calculate_single_aggregation(symbol, predictions, timeframe_config)
                aggregation_tasks.append(task)
        
        # Execute mit Concurrency Limit
        semaphore = asyncio.Semaphore(self._max_concurrent_calculations)
        
        async def limited_aggregation(task):
            async with semaphore:
                return await task
        
        # Execute all tasks parallel
        results = await asyncio.gather(
            *[limited_aggregation(task) for task in aggregation_tasks],
            return_exceptions=True
        )
        
        # Filter successful results
        successful_aggregations = []
        for result in results:
            if isinstance(result, AggregatedPrediction):
                successful_aggregations.append(result)
            elif isinstance(result, Exception):
                # Log error but continue (graceful degradation)
                print(f"Aggregation failed: {result}")
        
        return successful_aggregations
    
    async def _calculate_single_aggregation(self,
                                          symbol: str,
                                          predictions: List[Dict[str, Any]],
                                          timeframe_config: TimeframeConfiguration) -> AggregatedPrediction:
        """Calculate Single Symbol Aggregation"""
        
        try:
            # Extract company name
            company_name = predictions[0].get('company_name', 'Unknown Company')
            
            # Execute Domain Service Calculation
            aggregated_prediction = self._aggregation_service.calculate_hierarchical_average(
                raw_data=predictions,
                timeframe_config=timeframe_config
            )
            
            # Set expiration
            expire_hours = self._get_expiration_hours(timeframe_config.timeframe_type.value)
            aggregated_prediction.expires_at = datetime.now() + timedelta(hours=expire_hours)
            
            return aggregated_prediction
            
        except Exception as e:
            raise RuntimeError(f"Failed to calculate aggregation for {symbol}: {e}")
    
    def _apply_quality_filtering(self, aggregated_predictions: List[AggregatedPrediction]) -> List[AggregatedPrediction]:
        """Apply Quality Filtering entsprechend Business Rules"""
        
        quality_filtered = []
        
        for prediction in aggregated_predictions:
            # Quality Threshold Check
            comprehensive_quality = prediction.quality_metrics.calculate_composite_quality_score()
            
            if comprehensive_quality >= self._quality_threshold:
                quality_filtered.append(prediction)
        
        return quality_filtered
    
    def _sort_and_limit_results(self, 
                               predictions: List[AggregatedPrediction], 
                               limit: int) -> List[AggregatedPrediction]:
        """Sort by Quality und Confidence, dann Limit"""
        
        # Sort by: 1) Comprehensive Quality Score, 2) Confidence Score, 3) Aggregated Value
        sorted_predictions = sorted(
            predictions,
            key=lambda p: (
                p.quality_metrics.calculate_composite_quality_score(),
                p.confidence_score,
                abs(p.aggregated_value)
            ),
            reverse=True
        )
        
        return sorted_predictions[:limit]
    
    async def _cache_results(self,
                           predictions: List[AggregatedPrediction],
                           timeframe: str,
                           symbol_filter: Optional[str]) -> None:
        """Cache Results für Performance"""
        
        if not predictions:
            return
        
        cache_key = self._build_cache_key(timeframe, symbol_filter, len(predictions))
        
        try:
            # Serialize für Cache Storage
            cache_data = self._serialize_predictions_for_cache(predictions)
            
            # Calculate dynamic TTL basierend auf Quality
            avg_quality = sum(p.quality_metrics.calculate_composite_quality_score() for p in predictions) / len(predictions)
            dynamic_ttl = int(self._cache_ttl_seconds * float(avg_quality))  # Higher quality = longer cache
            
            await self._cache_service.set(cache_key, cache_data, ttl_seconds=dynamic_ttl)
            
            await self._publish_cache_updated_event(timeframe, len(predictions), dynamic_ttl)
            
        except Exception as e:
            # Cache Error ist nicht critical - log und continue
            print(f"Cache storage failed: {e}")
    
    async def _create_response_dtos(self,
                                  predictions: List[AggregatedPrediction],
                                  include_quality_details: bool) -> List[AggregatedPredictionDTO]:
        """Create Response DTOs mit gewünschtem Detail Level"""
        
        response_dtos = []
        
        for prediction in predictions:
            if include_quality_details:
                dto = create_detailed_aggregated_prediction_dto_from_entity(prediction)
            else:
                dto = create_aggregated_prediction_dto_from_entity(prediction)
            
            response_dtos.append(dto)
        
        return response_dtos
    
    def _build_response(self,
                       response_dtos: List[AggregatedPredictionDTO],
                       timeframe: str,
                       total_available: int,
                       processing_duration_ms: float,
                       from_cache: bool) -> AggregatedPredictionsResponseDTO:
        """Build Final Response DTO"""
        
        # Calculate Cache Performance Metrics
        cache_hits = sum(1 for dto in response_dtos if dto.cache_hit)
        cache_hit_ratio = cache_hits / len(response_dtos) if response_dtos else 0.0
        
        cache_status = {
            'cache_hits': cache_hits,
            'cache_misses': len(response_dtos) - cache_hits,
            'cache_hit_ratio': cache_hit_ratio,
            'response_from_cache': from_cache
        }
        
        # Calculate Processing Performance
        avg_quality = (sum(dto.quality_metrics.comprehensive_quality_score for dto in response_dtos) / 
                      len(response_dtos) if response_dtos else 0.0)
        
        processing_summary = {
            'processing_duration_ms': processing_duration_ms,
            'average_quality_score': avg_quality,
            'performance_target_ms': self._performance_target_ms,
            'performance_met': processing_duration_ms <= self._performance_target_ms,
            'predictions_per_second': len(response_dtos) / (processing_duration_ms / 1000) if processing_duration_ms > 0 else 0
        }
        
        return AggregatedPredictionsResponseDTO(
            predictions=response_dtos,
            timeframe=timeframe,
            total_count=total_available,
            returned_count=len(response_dtos),
            calculation_timestamp=datetime.now(),
            cache_status=cache_status,
            processing_summary=processing_summary
        )
    
    def _create_empty_response(self, timeframe: str, start_time: float) -> AggregatedPredictionsResponseDTO:
        """Create Empty Response wenn keine Data verfügbar"""
        
        processing_duration = (time.time() - start_time) * 1000
        
        return AggregatedPredictionsResponseDTO(
            predictions=[],
            timeframe=timeframe,
            total_count=0,
            returned_count=0,
            calculation_timestamp=datetime.now(),
            cache_status={'response_from_cache': False, 'cache_hit_ratio': 0.0},
            processing_summary={
                'processing_duration_ms': processing_duration,
                'average_quality_score': 0.0,
                'performance_met': True
            }
        )
    
    # HELPER METHODS
    
    def _build_cache_key(self, timeframe: str, symbol_filter: Optional[str], limit: int) -> str:
        """Build Cache Key für Aggregation Results"""
        key_parts = [f'aggregation', timeframe, str(limit)]
        if symbol_filter:
            key_parts.append(symbol_filter)
        return ':'.join(key_parts)
    
    def _get_expiration_hours(self, timeframe: str) -> int:
        """Get Cache Expiration Hours basierend auf Timeframe"""
        expiration_hours = {
            '1W': 2,   # 2 hours für weekly
            '1M': 6,   # 6 hours für monthly  
            '3M': 12,  # 12 hours für quarterly
            '6M': 24,  # 24 hours für semi-annual
            '1Y': 48   # 48 hours für annual
        }
        return expiration_hours.get(timeframe, 6)  # Default 6 hours
    
    def _serialize_predictions_for_cache(self, predictions: List[AggregatedPrediction]) -> Dict[str, Any]:
        """Serialize Predictions für Cache Storage"""
        return {
            'predictions': [pred.to_audit_dict() for pred in predictions],
            'cached_at': datetime.now().isoformat(),
            'version': 'v7.1'
        }
    
    def _deserialize_cached_predictions(self, cache_data: Dict[str, Any]) -> List[AggregatedPrediction]:
        """Deserialize Predictions from Cache"""
        # Simplified deserialization - würde in real implementation komplexer sein
        cached_predictions = []
        for pred_data in cache_data.get('predictions', []):
            # Create simplified AggregatedPrediction from cache data
            # This is a simplified version - real implementation würde full reconstruction machen
            pass
        return cached_predictions
    
    # EVENT PUBLISHING METHODS
    
    async def _publish_cache_hit_event(self, timeframe: str, prediction_count: int) -> None:
        """Publish Cache Hit Event"""
        await self._event_publisher.publish_event(
            event_type='aggregation.cache.hit',
            event_data={
                'timeframe': timeframe,
                'prediction_count': prediction_count,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    async def _publish_calculation_completed_event(self,
                                                 timeframe: str,
                                                 prediction_count: int,
                                                 processing_duration_ms: float,
                                                 success: bool) -> None:
        """Publish Calculation Completed Event"""
        await self._event_publisher.publish_event(
            event_type='aggregation.calculation.completed',
            event_data={
                'timeframe': timeframe,
                'prediction_count': prediction_count,
                'processing_duration_ms': processing_duration_ms,
                'success': success,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    async def _publish_calculation_failed_event(self,
                                              timeframe: str,
                                              error_message: str,
                                              processing_duration_ms: float) -> None:
        """Publish Calculation Failed Event"""
        await self._event_publisher.publish_event(
            event_type='aggregation.calculation.failed',
            event_data={
                'timeframe': timeframe,
                'error_message': error_message,
                'processing_duration_ms': processing_duration_ms,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    async def _publish_cache_updated_event(self,
                                         timeframe: str,
                                         prediction_count: int,
                                         ttl_seconds: int) -> None:
        """Publish Cache Updated Event"""
        await self._event_publisher.publish_event(
            event_type='aggregation.cache.updated',
            event_data={
                'timeframe': timeframe,
                'prediction_count': prediction_count,
                'ttl_seconds': ttl_seconds,
                'timestamp': datetime.now().isoformat()
            }
        )