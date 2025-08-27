"""
Data Processing Service - Aggregated Prediction DTOs
Timeframe-Specific Aggregation v7.1 - Clean Architecture Application Layer

Data Transfer Objects für API-Layer Communication
SOLID Principles: Single Responsibility, Interface Segregation, Validation
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, date
from pydantic import BaseModel, Field, validator


class TimeframeAggregationRequestDTO(BaseModel):
    """DTO für Timeframe Aggregation Requests"""
    
    timeframe: str = Field(
        ...,
        regex="^(1W|1M|3M|6M|1Y)$",
        description="Zeitintervall: 1W, 1M, 3M, 6M, 1Y"
    )
    force_refresh: bool = Field(
        default=False,
        description="Force refresh bypassing cache"
    )
    include_quality_details: bool = Field(
        default=False,
        description="Include detailed quality metrics in response"
    )
    symbol_filter: Optional[str] = Field(
        default=None,
        regex="^[A-Z]{1,10}$",
        description="Optional symbol filter (e.g., 'AAPL')"
    )
    limit: int = Field(
        default=15,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = {'1W', '1M', '3M', '6M', '1Y'}
        if v not in valid_timeframes:
            raise ValueError(f'Invalid timeframe. Must be one of: {valid_timeframes}')
        return v


class QualityMetricsDTO(BaseModel):
    """DTO für Quality Metrics"""
    
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence score (0.0-1.0)"
    )
    data_completeness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Data completeness score (0.0-1.0)"
    )
    statistical_validity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Statistical validity score (0.0-1.0)"
    )
    outlier_percentage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of outliers detected"
    )
    comprehensive_quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall composite quality score"
    )
    quality_category: str = Field(
        ...,
        regex="^(excellent|good|acceptable|poor|unacceptable)$",
        description="Quality classification"
    )
    production_ready: bool = Field(
        ...,
        description="Whether quality meets production standards"
    )


class DetailedQualityMetricsDTO(QualityMetricsDTO):
    """Extended DTO für detaillierte Quality Metrics"""
    
    temporal_consistency: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Temporal consistency score"
    )
    cross_model_agreement: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cross-model agreement score"
    )
    data_freshness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Data freshness score"
    )
    convergence_stability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Numerical convergence stability"
    )
    quality_issues: Dict[str, str] = Field(
        default_factory=dict,
        description="Identified quality issues"
    )
    improvement_recommendations: Dict[str, str] = Field(
        default_factory=dict,
        description="Quality improvement recommendations"
    )


class AggregatedPredictionDTO(BaseModel):
    """Core DTO für Aggregated Predictions"""
    
    symbol: str = Field(
        ...,
        regex="^[A-Z]{1,10}$",
        description="Stock symbol"
    )
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Company name"
    )
    timeframe: str = Field(
        ...,
        regex="^(1W|1M|3M|6M|1Y)$",
        description="Aggregation timeframe"
    )
    aggregated_prediction_percent: float = Field(
        ...,
        ge=-1000.0,
        le=1000.0,
        description="Aggregated prediction value in percent"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Prediction confidence (0.0-1.0)"
    )
    quality_metrics: QualityMetricsDTO = Field(
        ...,
        description="Quality assessment metrics"
    )
    
    # Statistical Metadata
    source_prediction_count: int = Field(
        ...,
        ge=1,
        description="Number of source predictions aggregated"
    )
    statistical_variance: float = Field(
        ...,
        ge=0.0,
        description="Statistical variance of source predictions"
    )
    outlier_count: int = Field(
        ...,
        ge=0,
        description="Number of outliers detected and excluded"
    )
    
    # Temporal Information
    calculation_timestamp: datetime = Field(
        ...,
        description="When this aggregation was calculated"
    )
    target_prediction_date: date = Field(
        ...,
        description="Target date for this prediction"
    )
    expires_at: datetime = Field(
        ...,
        description="When this aggregation expires"
    )
    
    # Aggregation Metadata
    aggregation_strategy: str = Field(
        ...,
        description="Strategy used for aggregation"
    )
    cache_hit: bool = Field(
        default=False,
        description="Whether this result came from cache"
    )
    
    @validator('expires_at')
    def expires_at_in_future(cls, v):
        if v <= datetime.now():
            raise ValueError('expires_at must be in the future')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class DetailedAggregatedPredictionDTO(AggregatedPredictionDTO):
    """Extended DTO mit detaillierten Informationen"""
    
    quality_metrics: DetailedQualityMetricsDTO = Field(
        ...,
        description="Detailed quality assessment metrics"
    )
    
    # Enhanced Statistical Information
    standard_deviation: float = Field(
        ...,
        ge=0.0,
        description="Standard deviation of source predictions"
    )
    outlier_percentage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of outliers in source data"
    )
    min_source_value: float = Field(
        ...,
        description="Minimum value from source predictions"
    )
    max_source_value: float = Field(
        ...,
        description="Maximum value from source predictions"
    )
    median_source_value: float = Field(
        ...,
        description="Median value from source predictions"
    )
    
    # Processing Information
    processing_duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Processing duration in milliseconds"
    )
    calculation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Technical calculation metadata"
    )
    source_data_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of source data used"
    )


class AggregatedPredictionsResponseDTO(BaseModel):
    """Response DTO für Aggregated Predictions List"""
    
    predictions: List[AggregatedPredictionDTO] = Field(
        ...,
        description="List of aggregated predictions"
    )
    timeframe: str = Field(
        ...,
        description="Requested timeframe"
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of predictions available"
    )
    returned_count: int = Field(
        ...,
        ge=0,
        description="Number of predictions returned in this response"
    )
    calculation_timestamp: datetime = Field(
        ...,
        description="When these aggregations were calculated"
    )
    cache_status: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cache performance information"
    )
    processing_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Processing performance summary"
    )
    
    @validator('returned_count')
    def returned_count_matches_predictions(cls, v, values):
        if 'predictions' in values and len(values['predictions']) != v:
            raise ValueError('returned_count must match length of predictions list')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class AggregationCalculationRequestDTO(BaseModel):
    """DTO für manuelle Aggregation Calculation Requests"""
    
    timeframe: str = Field(
        ...,
        regex="^(1W|1M|3M|6M|1Y)$",
        description="Zeitintervall für Aggregation"
    )
    symbols: Optional[List[str]] = Field(
        default=None,
        description="Optional list of symbols to process (default: all)"
    )
    force_recalculation: bool = Field(
        default=False,
        description="Force recalculation even if cached results exist"
    )
    aggregation_strategy: Optional[str] = Field(
        default=None,
        regex="^(equal_weight|recency_weight|volatility_weight|trend_weight|seasonal_weight|hierarchical_average)$",
        description="Override default aggregation strategy"
    )
    quality_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum quality threshold for results"
    )
    
    @validator('symbols')
    def validate_symbols(cls, v):
        if v is not None:
            for symbol in v:
                if not symbol.isupper() or len(symbol) > 10:
                    raise ValueError(f'Invalid symbol format: {symbol}')
        return v


class AggregationCalculationResponseDTO(BaseModel):
    """Response DTO für Aggregation Calculations"""
    
    request_id: str = Field(
        ...,
        description="Unique request identifier"
    )
    timeframe: str = Field(
        ...,
        description="Processed timeframe"
    )
    status: str = Field(
        ...,
        regex="^(started|processing|completed|failed)$",
        description="Calculation status"
    )
    processed_symbols: List[str] = Field(
        default_factory=list,
        description="Symbols that were processed"
    )
    successful_calculations: int = Field(
        default=0,
        ge=0,
        description="Number of successful calculations"
    )
    failed_calculations: int = Field(
        default=0,
        ge=0,
        description="Number of failed calculations"
    )
    processing_duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total processing duration"
    )
    average_quality_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Average quality score of calculations"
    )
    error_messages: List[str] = Field(
        default_factory=list,
        description="Error messages if any calculations failed"
    )
    started_at: datetime = Field(
        ...,
        description="When calculation was started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When calculation was completed"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QualityReportRequestDTO(BaseModel):
    """DTO für Quality Report Requests"""
    
    symbol: str = Field(
        ...,
        regex="^[A-Z]{1,10}$",
        description="Stock symbol for quality report"
    )
    timeframe: str = Field(
        ...,
        regex="^(1W|1M|3M|6M|1Y)$",
        description="Timeframe for quality assessment"
    )
    include_recommendations: bool = Field(
        default=True,
        description="Include improvement recommendations"
    )
    include_historical_comparison: bool = Field(
        default=False,
        description="Include historical quality comparison"
    )


class QualityReportResponseDTO(BaseModel):
    """Response DTO für Quality Reports"""
    
    symbol: str = Field(..., description="Stock symbol")
    timeframe: str = Field(..., description="Assessed timeframe")
    
    current_quality: DetailedQualityMetricsDTO = Field(
        ...,
        description="Current quality assessment"
    )
    
    quality_trend: Optional[str] = Field(
        default=None,
        regex="^(improving|stable|declining)$",
        description="Quality trend over time"
    )
    
    historical_comparison: Optional[Dict[str, float]] = Field(
        default=None,
        description="Historical quality score comparison"
    )
    
    actionable_insights: List[str] = Field(
        default_factory=list,
        description="Actionable insights for quality improvement"
    )
    
    assessment_timestamp: datetime = Field(
        ...,
        description="When this quality report was generated"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Factory Functions für DTO Creation

def create_aggregated_prediction_dto_from_entity(aggregated_prediction) -> AggregatedPredictionDTO:
    """Factory für AggregatedPredictionDTO aus Domain Entity"""
    
    quality_metrics_dto = QualityMetricsDTO(
        confidence_score=float(aggregated_prediction.quality_metrics.confidence_score),
        data_completeness=float(aggregated_prediction.quality_metrics.data_completeness),
        statistical_validity=float(aggregated_prediction.quality_metrics.statistical_validity),
        outlier_percentage=float(aggregated_prediction.quality_metrics.outlier_percentage),
        comprehensive_quality_score=float(aggregated_prediction.quality_metrics.calculate_composite_quality_score()),
        quality_category=aggregated_prediction.quality_metrics.get_quality_category().value,
        production_ready=aggregated_prediction.quality_metrics.is_production_ready()
    )
    
    return AggregatedPredictionDTO(
        symbol=aggregated_prediction.symbol,
        company_name=aggregated_prediction.company_name,
        timeframe=aggregated_prediction.timeframe,
        aggregated_prediction_percent=float(aggregated_prediction.aggregated_value),
        confidence_score=aggregated_prediction.confidence_score,
        quality_metrics=quality_metrics_dto,
        source_prediction_count=aggregated_prediction.source_prediction_count,
        statistical_variance=float(aggregated_prediction.statistical_variance),
        outlier_count=aggregated_prediction.outlier_count,
        calculation_timestamp=aggregated_prediction.calculation_timestamp,
        target_prediction_date=aggregated_prediction.target_prediction_date,
        expires_at=aggregated_prediction.expires_at,
        aggregation_strategy=aggregated_prediction.aggregation_strategy_used.value,
        cache_hit=aggregated_prediction.cache_hit
    )


def create_detailed_aggregated_prediction_dto_from_entity(aggregated_prediction) -> DetailedAggregatedPredictionDTO:
    """Factory für DetailedAggregatedPredictionDTO aus Domain Entity"""
    
    quality_report = aggregated_prediction.quality_metrics.to_detailed_report()
    
    detailed_quality_metrics_dto = DetailedQualityMetricsDTO(
        confidence_score=float(aggregated_prediction.quality_metrics.confidence_score),
        data_completeness=float(aggregated_prediction.quality_metrics.data_completeness),
        statistical_validity=float(aggregated_prediction.quality_metrics.statistical_validity),
        outlier_percentage=float(aggregated_prediction.quality_metrics.outlier_percentage),
        comprehensive_quality_score=float(aggregated_prediction.quality_metrics.calculate_composite_quality_score()),
        quality_category=aggregated_prediction.quality_metrics.get_quality_category().value,
        production_ready=aggregated_prediction.quality_metrics.is_production_ready(),
        temporal_consistency=float(aggregated_prediction.quality_metrics.temporal_consistency),
        cross_model_agreement=float(aggregated_prediction.quality_metrics.cross_model_agreement),
        data_freshness_score=float(aggregated_prediction.quality_metrics.data_freshness_score),
        convergence_stability=float(aggregated_prediction.quality_metrics.convergence_stability),
        quality_issues=quality_report['quality_issues'],
        improvement_recommendations=quality_report['improvement_recommendations']
    )
    
    # Extract min/max/median from source data summary
    source_summary = aggregated_prediction.source_data_summary
    
    return DetailedAggregatedPredictionDTO(
        symbol=aggregated_prediction.symbol,
        company_name=aggregated_prediction.company_name,
        timeframe=aggregated_prediction.timeframe,
        aggregated_prediction_percent=float(aggregated_prediction.aggregated_value),
        confidence_score=aggregated_prediction.confidence_score,
        quality_metrics=detailed_quality_metrics_dto,
        source_prediction_count=aggregated_prediction.source_prediction_count,
        statistical_variance=float(aggregated_prediction.statistical_variance),
        outlier_count=aggregated_prediction.outlier_count,
        calculation_timestamp=aggregated_prediction.calculation_timestamp,
        target_prediction_date=aggregated_prediction.target_prediction_date,
        expires_at=aggregated_prediction.expires_at,
        aggregation_strategy=aggregated_prediction.aggregation_strategy_used.value,
        cache_hit=aggregated_prediction.cache_hit,
        standard_deviation=float(aggregated_prediction.standard_deviation),
        outlier_percentage=float(aggregated_prediction.outlier_percentage),
        min_source_value=float(source_summary.get('value_range', {}).get('min_cleaned', 0)),
        max_source_value=float(source_summary.get('value_range', {}).get('max_cleaned', 0)),
        median_source_value=float(source_summary.get('median_value', 0)),
        calculation_metadata=aggregated_prediction.calculation_metadata,
        source_data_summary=aggregated_prediction.source_data_summary
    )