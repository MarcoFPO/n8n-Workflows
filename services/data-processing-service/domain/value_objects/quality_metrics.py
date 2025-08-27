"""
Data Processing Service - Quality Metrics Value Object
Timeframe-Specific Aggregation v7.1 - Clean Architecture Domain Layer

Immutable Value Object für umfassende Qualitätsbewertung von Aggregationen
SOLID Principles: Single Responsibility, Immutability, Mathematical Validation
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Any, Optional
from enum import Enum


class QualityCategory(Enum):
    """Qualitäts-Kategorien für Aggregation Assessment"""
    EXCELLENT = "excellent"    # 0.90 - 1.00
    GOOD = "good"             # 0.75 - 0.89  
    ACCEPTABLE = "acceptable" # 0.60 - 0.74
    POOR = "poor"             # 0.40 - 0.59
    UNACCEPTABLE = "unacceptable"  # 0.00 - 0.39


@dataclass(frozen=True)
class QualityMetrics:
    """
    Immutable Value Object für Multi-Dimensionale Qualitätsbewertung
    
    DOMAIN RESPONSIBILITIES:
    - Confidence Score Calculation und Validation
    - Data Completeness Assessment
    - Statistical Validity Measurement
    - Outlier Impact Analysis
    - Overall Quality Classification
    """
    
    # Core Quality Dimensions (0.0 - 1.0)
    confidence_score: Decimal = Decimal('0.0')      # Model-basierte Confidence
    data_completeness: Decimal = Decimal('0.0')     # Vollständigkeit der Quelldaten
    statistical_validity: Decimal = Decimal('0.0')   # Statistische Signifikanz
    outlier_percentage: Decimal = Decimal('0.0')     # Anteil statistischer Outliers
    
    # Advanced Quality Metrics
    temporal_consistency: Decimal = Decimal('0.0')   # Zeitliche Konsistenz
    cross_model_agreement: Decimal = Decimal('0.0')  # Übereinstimmung zwischen Modellen
    data_freshness_score: Decimal = Decimal('0.0')   # Aktualität der Daten
    convergence_stability: Decimal = Decimal('0.0')  # Numerische Stabilität
    
    # Metadata
    quality_calculation_version: str = "v7.1"
    assessment_timestamp: Optional[str] = None
    
    def __post_init__(self):
        """Domain Validation für Quality Metrics"""
        self._validate_percentage_range(self.confidence_score, "confidence_score")
        self._validate_percentage_range(self.data_completeness, "data_completeness") 
        self._validate_percentage_range(self.statistical_validity, "statistical_validity")
        self._validate_percentage_range(self.outlier_percentage, "outlier_percentage")
        self._validate_percentage_range(self.temporal_consistency, "temporal_consistency")
        self._validate_percentage_range(self.cross_model_agreement, "cross_model_agreement")
        self._validate_percentage_range(self.data_freshness_score, "data_freshness_score")
        self._validate_percentage_range(self.convergence_stability, "convergence_stability")
    
    def _validate_percentage_range(self, value: Decimal, field_name: str) -> None:
        """Validiere dass Wert in 0.0 - 1.0 Range ist"""
        if not (Decimal('0.0') <= value <= Decimal('1.0')):
            raise ValueError(f"{field_name} must be between 0.0 and 1.0, got {value}")
    
    # DOMAIN BEHAVIOR METHODS
    
    def calculate_composite_quality_score(self) -> Decimal:
        """
        Berechne gewichteten Composite Quality Score
        
        Gewichtung basierend auf Business Impact:
        - Data Completeness: 25% (kritisch für Verlässlichkeit)
        - Statistical Validity: 20% (mathematische Fundierung)
        - Confidence Score: 20% (Model-Performance)
        - Outlier Impact: 15% (Robustheit)
        - Cross-Model Agreement: 10% (Konsensus)
        - Temporal Consistency: 5% (Stabilität)
        - Data Freshness: 3% (Aktualität)
        - Convergence Stability: 2% (numerische Qualität)
        """
        weights = {
            'data_completeness': Decimal('0.25'),
            'statistical_validity': Decimal('0.20'),
            'confidence_score': Decimal('0.20'),
            'outlier_impact': Decimal('0.15'),  # (1 - outlier_percentage)
            'cross_model_agreement': Decimal('0.10'),
            'temporal_consistency': Decimal('0.05'),
            'data_freshness_score': Decimal('0.03'),
            'convergence_stability': Decimal('0.02')
        }
        
        # Berechne gewichteten Score
        outlier_impact_score = Decimal('1.0') - self.outlier_percentage
        
        composite_score = (
            self.data_completeness * weights['data_completeness'] +
            self.statistical_validity * weights['statistical_validity'] +
            self.confidence_score * weights['confidence_score'] +
            outlier_impact_score * weights['outlier_impact'] +
            self.cross_model_agreement * weights['cross_model_agreement'] +
            self.temporal_consistency * weights['temporal_consistency'] +
            self.data_freshness_score * weights['data_freshness_score'] +
            self.convergence_stability * weights['convergence_stability']
        )
        
        return min(Decimal('1.0'), max(Decimal('0.0'), composite_score))
    
    def get_quality_category(self) -> QualityCategory:
        """Klassifiziere Qualität basierend auf Composite Score"""
        composite_score = self.calculate_composite_quality_score()
        
        if composite_score >= Decimal('0.90'):
            return QualityCategory.EXCELLENT
        elif composite_score >= Decimal('0.75'):
            return QualityCategory.GOOD
        elif composite_score >= Decimal('0.60'):
            return QualityCategory.ACCEPTABLE
        elif composite_score >= Decimal('0.40'):
            return QualityCategory.POOR
        else:
            return QualityCategory.UNACCEPTABLE
    
    def is_production_ready(self) -> bool:
        """Prüfe ob Qualität für Produktions-Einsatz ausreichend ist"""
        composite_score = self.calculate_composite_quality_score()
        
        # Minimum-Kriterien für Production Ready
        minimum_criteria = (
            composite_score >= Decimal('0.70') and
            self.data_completeness >= Decimal('0.80') and
            self.statistical_validity >= Decimal('0.70') and
            self.outlier_percentage <= Decimal('0.20') and
            self.confidence_score >= Decimal('0.60')
        )
        
        return minimum_criteria
    
    def identify_quality_issues(self) -> Dict[str, str]:
        """Identifiziere spezifische Qualitätsprobleme"""
        issues = {}
        
        if self.data_completeness < Decimal('0.70'):
            issues['data_completeness'] = f"Insufficient data completeness: {float(self.data_completeness):.1%}"
        
        if self.statistical_validity < Decimal('0.60'):
            issues['statistical_validity'] = f"Low statistical validity: {float(self.statistical_validity):.1%}"
        
        if self.confidence_score < Decimal('0.50'):
            issues['confidence_score'] = f"Low confidence score: {float(self.confidence_score):.1%}"
        
        if self.outlier_percentage > Decimal('0.25'):
            issues['outlier_percentage'] = f"High outlier percentage: {float(self.outlier_percentage):.1%}"
        
        if self.cross_model_agreement < Decimal('0.40'):
            issues['cross_model_agreement'] = f"Poor cross-model agreement: {float(self.cross_model_agreement):.1%}"
        
        if self.data_freshness_score < Decimal('0.30'):
            issues['data_freshness'] = f"Stale data detected: {float(self.data_freshness_score):.1%}"
        
        if self.temporal_consistency < Decimal('0.40'):
            issues['temporal_consistency'] = f"Temporal inconsistency: {float(self.temporal_consistency):.1%}"
        
        if self.convergence_stability < Decimal('0.30'):
            issues['convergence_stability'] = f"Numerical instability: {float(self.convergence_stability):.1%}"
        
        return issues
    
    def get_quality_improvement_recommendations(self) -> Dict[str, str]:
        """Generiere Verbesserungsempfehlungen basierend auf Quality Issues"""
        issues = self.identify_quality_issues()
        recommendations = {}
        
        if 'data_completeness' in issues:
            recommendations['increase_data_sources'] = "Add more data sources or extend collection period"
        
        if 'statistical_validity' in issues:
            recommendations['improve_sample_size'] = "Increase sample size or improve data preprocessing"
        
        if 'confidence_score' in issues:
            recommendations['model_tuning'] = "Retrain models or adjust hyperparameters"
        
        if 'outlier_percentage' in issues:
            recommendations['outlier_handling'] = "Improve outlier detection and handling strategies"
        
        if 'cross_model_agreement' in issues:
            recommendations['ensemble_optimization'] = "Optimize ensemble weights or model selection"
        
        if 'data_freshness' in issues:
            recommendations['increase_update_frequency'] = "Increase data collection and processing frequency"
        
        if 'temporal_consistency' in issues:
            recommendations['temporal_smoothing'] = "Apply temporal smoothing or trend analysis"
        
        if 'convergence_stability' in issues:
            recommendations['numerical_optimization'] = "Improve numerical stability and precision"
        
        return recommendations
    
    def to_detailed_report(self) -> Dict[str, Any]:
        """Generiere detaillierten Quality Report"""
        composite_score = self.calculate_composite_quality_score()
        quality_category = self.get_quality_category()
        issues = self.identify_quality_issues()
        recommendations = self.get_quality_improvement_recommendations()
        
        return {
            "overall_assessment": {
                "composite_quality_score": float(composite_score),
                "quality_category": quality_category.value,
                "production_ready": self.is_production_ready()
            },
            "dimension_scores": {
                "confidence_score": float(self.confidence_score),
                "data_completeness": float(self.data_completeness),
                "statistical_validity": float(self.statistical_validity),
                "outlier_percentage": float(self.outlier_percentage),
                "temporal_consistency": float(self.temporal_consistency),
                "cross_model_agreement": float(self.cross_model_agreement),
                "data_freshness_score": float(self.data_freshness_score),
                "convergence_stability": float(self.convergence_stability)
            },
            "quality_issues": issues,
            "improvement_recommendations": recommendations,
            "metadata": {
                "quality_calculation_version": self.quality_calculation_version,
                "assessment_timestamp": self.assessment_timestamp
            }
        }
    
    @classmethod
    def create_default(cls) -> 'QualityMetrics':
        """Factory für Default Quality Metrics"""
        return cls(
            confidence_score=Decimal('0.5'),
            data_completeness=Decimal('0.7'),
            statistical_validity=Decimal('0.6'),
            outlier_percentage=Decimal('0.1'),
            temporal_consistency=Decimal('0.7'),
            cross_model_agreement=Decimal('0.6'),
            data_freshness_score=Decimal('0.8'),
            convergence_stability=Decimal('0.9')
        )
    
    @classmethod
    def create_from_statistics(cls,
                              prediction_count: int,
                              outlier_count: int,
                              variance: Decimal,
                              confidence: float,
                              data_age_hours: float = 1.0) -> 'QualityMetrics':
        """Factory aus statistischen Werten"""
        
        # Data Completeness basierend auf Prediction Count
        data_completeness = min(Decimal('1.0'), Decimal(str(prediction_count)) / Decimal('20'))  # 20+ ist "complete"
        
        # Statistical Validity basierend auf Sample Size und Variance
        statistical_validity = min(Decimal('1.0'), 
                                 Decimal(str(prediction_count)) / Decimal('10') * 
                                 (Decimal('1.0') - min(Decimal('1.0'), variance / Decimal('10'))))
        
        # Outlier Percentage
        outlier_percentage = Decimal(str(outlier_count)) / max(Decimal('1'), Decimal(str(prediction_count)))
        
        # Data Freshness Score (je frischer, desto besser)
        data_freshness_score = max(Decimal('0.0'), 
                                  Decimal('1.0') - Decimal(str(data_age_hours)) / Decimal('24'))
        
        # Confidence Score
        confidence_score = Decimal(str(max(0.0, min(1.0, confidence))))
        
        return cls(
            confidence_score=confidence_score,
            data_completeness=data_completeness,
            statistical_validity=statistical_validity,
            outlier_percentage=outlier_percentage,
            temporal_consistency=Decimal('0.75'),  # Standard-Annahme
            cross_model_agreement=confidence_score,  # Vereinfachung
            data_freshness_score=data_freshness_score,
            convergence_stability=Decimal('0.85')  # Standard-Annahme
        )
    
    @classmethod
    def create_excellent(cls) -> 'QualityMetrics':
        """Factory für exzellente Quality Metrics (Testing/Demo)"""
        return cls(
            confidence_score=Decimal('0.92'),
            data_completeness=Decimal('0.95'),
            statistical_validity=Decimal('0.88'),
            outlier_percentage=Decimal('0.05'),
            temporal_consistency=Decimal('0.90'),
            cross_model_agreement=Decimal('0.87'),
            data_freshness_score=Decimal('0.95'),
            convergence_stability=Decimal('0.93')
        )