"""
Data Preprocessing Module für aktienanalyse-ökosystem
Normalisierung, Cleaning und Validation von ML-Daten für optimale Model Performance
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

# Import previous modules
try:
    from .feature_engineering_module import FeatureSet, EngineeringResult
    from .ml_data_collector_module import MLDataPoint, MLDataCollection
except ImportError:
    # PRODUCTION CODE MUST NOT USE MOCK CLASSES
    raise ImportError("Production code requires proper module imports - mock classes are not allowed for production deployment")

# Import production-ready base module pattern
try:
    from shared.single_function_module_base import SingleFunctionModuleBase, ModuleConfig
except ImportError:
    # Production fallback - create simplified local implementation
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
class PreprocessingRule:
    """Defines a preprocessing rule"""
    rule_id: str
    rule_type: str  # 'normalization', 'outlier_removal', 'missing_data', 'transformation'
    target_features: List[str]  # Features to apply rule to
    parameters: Dict[str, Any]
    description: str


@dataclass
class PreprocessedDataset:
    """Preprocessed dataset ready for ML training/inference"""
    dataset_id: str
    original_engineering_result: EngineeringResult
    preprocessing_rules_applied: List[PreprocessingRule]
    processed_feature_sets: List[FeatureSet]
    train_test_splits: Dict[str, List[FeatureSet]]
    normalization_parameters: Dict[str, Dict[str, float]]
    quality_metrics: Dict[str, float]
    created_at: datetime


@dataclass
class ValidationResult:
    """Result of data validation"""
    validation_id: str
    dataset_tested: str
    validation_passed: bool
    validation_score: float
    issues_found: List[Dict[str, Any]]
    recommendations: List[str]


class DataPreprocessingModule(SingleFunctionModuleBase):
    """
    Single Function: Normalisierung, Cleaning und Validation von ML-Daten
    
    Hauptaufgaben:
    - Data Normalization und Scaling
    - Missing Data Handling
    - Outlier Detection und Treatment
    - Data Quality Validation
    - Train/Test/Validation Splits
    """
    
    def __init__(self, config: ModuleConfig = None):
        super().__init__(config or ModuleConfig())
        self.logger = logger.bind(module="data_preprocessing")
        
        # Preprocessing configuration
        self.normalization_methods = {
            'z_score': self._z_score_normalization,
            'min_max': self._min_max_normalization,
            'robust': self._robust_normalization,
            'log_transform': self._log_transform
        }
        
        self.outlier_methods = {
            'z_score': self._z_score_outlier_detection,
            'iqr': self._iqr_outlier_detection,
            'isolation_forest': self._isolation_forest_outliers  # Simplified
        }
        
        self.missing_data_strategies = {
            'drop': self._drop_missing,
            'mean_imputation': self._mean_imputation,
            'median_imputation': self._median_imputation,
            'forward_fill': self._forward_fill,
            'interpolation': self._linear_interpolation
        }
        
        # Quality thresholds
        self.quality_thresholds = {
            'min_data_completeness': 0.80,  # 80% of data must be complete
            'max_outlier_ratio': 0.05,      # Max 5% outliers
            'min_feature_variance': 0.01,   # Minimum variance for features
            'max_correlation': 0.95         # Max correlation between features
        }
        
        # Default preprocessing rules
        self.default_rules = [
            PreprocessingRule(
                rule_id="outlier_removal_z",
                rule_type="outlier_removal",
                target_features=["*"],  # All features
                parameters={'method': 'z_score', 'threshold': 3.0},
                description="Remove outliers using Z-score method (threshold=3.0)"
            ),
            PreprocessingRule(
                rule_id="normalization_robust",
                rule_type="normalization",
                target_features=["*"],
                parameters={'method': 'robust'},
                description="Robust normalization using median and IQR"
            ),
            PreprocessingRule(
                rule_id="missing_data_median",
                rule_type="missing_data",
                target_features=["*"],
                parameters={'strategy': 'median_imputation'},
                description="Impute missing values with median"
            )
        ]
        
        # Preprocessing statistics
        self.preprocessing_stats = {
            'datasets_processed': 0,
            'total_features_processed': 0,
            'outliers_removed': 0,
            'missing_values_imputed': 0,
            'processing_times': deque(maxlen=100),
            'quality_scores': deque(maxlen=100)
        }
        
        # Normalization parameters cache (for inference consistency)
        self.normalization_cache = {}
    
    async def preprocess_ml_data(self, engineering_result: EngineeringResult,
                                preprocessing_rules: List[PreprocessingRule] = None,
                                train_test_split: Tuple[float, float, float] = (0.7, 0.2, 0.1),
                                validation_enabled: bool = True) -> PreprocessedDataset:
        """
        Main function: Preprocesses engineered features for ML training/inference
        
        Args:
            engineering_result: Input feature engineering result
            preprocessing_rules: Custom preprocessing rules (uses defaults if None)
            train_test_split: Split ratios (train, test, validation)
            validation_enabled: Whether to perform data validation
            
        Returns:
            PreprocessedDataset: Comprehensive preprocessed dataset
        """
        start_time = datetime.now()
        dataset_id = f"preprocessed_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        if preprocessing_rules is None:
            preprocessing_rules = self.default_rules.copy()
        
        self.logger.info("Starting data preprocessing",
                        dataset_id=dataset_id,
                        original_features=engineering_result.total_features,
                        rules_count=len(preprocessing_rules),
                        validation_enabled=validation_enabled)
        
        try:
            # Step 1: Data Validation (pre-processing)
            if validation_enabled:
                validation_result = await self._validate_input_data(engineering_result)
                if not validation_result.validation_passed:
                    self.logger.warning("Input data validation failed",
                                      validation_score=validation_result.validation_score,
                                      issues=len(validation_result.issues_found))
            
            # Step 2: Apply preprocessing rules
            processed_feature_sets = []
            normalization_params = {}
            
            for feature_set in engineering_result.feature_sets:
                processed_fs, norm_params = await self._apply_preprocessing_rules(
                    feature_set, preprocessing_rules
                )
                processed_feature_sets.append(processed_fs)
                normalization_params[processed_fs.feature_id] = norm_params
            
            # Step 3: Create train/test/validation splits
            train_test_splits = await self._create_train_test_splits(
                processed_feature_sets, train_test_split
            )
            
            # Step 4: Calculate quality metrics
            quality_metrics = await self._calculate_preprocessing_quality(
                processed_feature_sets, engineering_result.feature_sets
            )
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Create preprocessed dataset
            preprocessed_dataset = PreprocessedDataset(
                dataset_id=dataset_id,
                original_engineering_result=engineering_result,
                preprocessing_rules_applied=preprocessing_rules,
                processed_feature_sets=processed_feature_sets,
                train_test_splits=train_test_splits,
                normalization_parameters=normalization_params,
                quality_metrics=quality_metrics,
                created_at=end_time
            )
            
            # Step 5: Final validation
            if validation_enabled:
                final_validation = await self._validate_preprocessed_data(preprocessed_dataset)
                quality_metrics['final_validation_score'] = final_validation.validation_score
            
            # Update statistics
            self.preprocessing_stats['datasets_processed'] += 1
            self.preprocessing_stats['total_features_processed'] += sum(len(fs.features) for fs in processed_feature_sets)
            self.preprocessing_stats['processing_times'].append(processing_time)
            self.preprocessing_stats['quality_scores'].append(quality_metrics.get('overall_quality', 0))
            
            # Cache normalization parameters for consistency
            self.normalization_cache[dataset_id] = normalization_params
            
            self.logger.info("Data preprocessing completed",
                           dataset_id=dataset_id,
                           processed_features=sum(len(fs.features) for fs in processed_feature_sets),
                           processing_time_seconds=processing_time,
                           quality_score=quality_metrics.get('overall_quality', 0))
            
            return preprocessed_dataset
            
        except Exception as e:
            self.logger.error("Data preprocessing failed", error=str(e))
            raise
    
    async def _validate_input_data(self, engineering_result: EngineeringResult) -> ValidationResult:
        """Validate input engineering result data quality"""
        validation_id = f"input_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        issues = []
        scores = []
        
        # Check feature sets completeness
        if not engineering_result.feature_sets:
            issues.append({
                'type': 'critical',
                'message': 'No feature sets found in engineering result',
                'impact': 'Cannot proceed with preprocessing'
            })
            return ValidationResult(validation_id, engineering_result.result_id, False, 0.0, issues, [])
        
        for feature_set in engineering_result.feature_sets:
            # Check feature completeness
            if not feature_set.features:
                issues.append({
                    'type': 'error',
                    'message': f'Empty feature set: {feature_set.feature_id}',
                    'impact': 'Feature set will be skipped'
                })
                scores.append(0.0)
                continue
            
            # Check for NaN/infinite values
            invalid_features = []
            valid_features = 0
            
            for feature_name, value in feature_set.features.items():
                if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
                    invalid_features.append(feature_name)
                else:
                    valid_features += 1
            
            if invalid_features:
                issues.append({
                    'type': 'warning',
                    'message': f'Invalid values in {feature_set.feature_type} features: {invalid_features[:5]}',
                    'impact': 'Features will need cleaning',
                    'count': len(invalid_features)
                })
            
            # Feature completeness score
            completeness_score = valid_features / len(feature_set.features) if feature_set.features else 0
            scores.append(completeness_score)
        
        # Overall validation score
        validation_score = statistics.mean(scores) if scores else 0.0
        validation_passed = validation_score >= self.quality_thresholds['min_data_completeness']
        
        # Generate recommendations
        recommendations = []
        if validation_score < 0.9:
            recommendations.append("Consider improving data collection quality")
        if len(issues) > 5:
            recommendations.append("Multiple data quality issues detected - review data pipeline")
        
        return ValidationResult(
            validation_id=validation_id,
            dataset_tested=engineering_result.result_id,
            validation_passed=validation_passed,
            validation_score=validation_score,
            issues_found=issues,
            recommendations=recommendations
        )
    
    async def _apply_preprocessing_rules(self, feature_set: FeatureSet, 
                                       rules: List[PreprocessingRule]) -> Tuple[FeatureSet, Dict[str, float]]:
        """Apply preprocessing rules to a feature set"""
        
        processed_features = feature_set.features.copy()
        normalization_params = {}
        
        # Apply each rule in sequence
        for rule in rules:
            # Check if rule applies to this feature set
            if not self._rule_applies_to_features(rule, list(processed_features.keys())):
                continue
            
            if rule.rule_type == 'outlier_removal':
                processed_features = await self._apply_outlier_removal(processed_features, rule)
                
            elif rule.rule_type == 'normalization':
                processed_features, norm_params = await self._apply_normalization(processed_features, rule)
                normalization_params.update(norm_params)
                
            elif rule.rule_type == 'missing_data':
                processed_features = await self._apply_missing_data_handling(processed_features, rule)
                
            elif rule.rule_type == 'transformation':
                processed_features = await self._apply_transformation(processed_features, rule)
        
        # Create processed feature set
        processed_feature_set = FeatureSet(
            feature_id=f"processed_{feature_set.feature_id}",
            source_collection_id=feature_set.source_collection_id,
            feature_type=feature_set.feature_type,
            features=processed_features,
            feature_metadata={
                **feature_set.feature_metadata,
                'preprocessing_applied': [rule.rule_id for rule in rules],
                'original_feature_count': len(feature_set.features),
                'processed_feature_count': len(processed_features)
            },
            created_at=datetime.now(),
            quality_score=self._calculate_processed_quality_score(processed_features)
        )
        
        return processed_feature_set, normalization_params
    
    def _rule_applies_to_features(self, rule: PreprocessingRule, feature_names: List[str]) -> bool:
        """Check if preprocessing rule applies to given features"""
        if "*" in rule.target_features:
            return True
        return any(fname in rule.target_features for fname in feature_names)
    
    async def _apply_outlier_removal(self, features: Dict[str, float], rule: PreprocessingRule) -> Dict[str, float]:
        """Apply outlier removal rule"""
        method = rule.parameters.get('method', 'z_score')
        threshold = rule.parameters.get('threshold', 3.0)
        
        if method not in self.outlier_methods:
            self.logger.warning("Unknown outlier method", method=method)
            return features
        
        # Get feature values for outlier detection
        feature_values = list(features.values())
        if len(feature_values) < 3:
            return features  # Need at least 3 values for meaningful outlier detection
        
        # Detect outliers
        outlier_detector = self.outlier_methods[method]
        outlier_mask = outlier_detector(feature_values, threshold)
        
        # Remove outliers by setting to median (conservative approach)
        cleaned_features = {}
        median_value = statistics.median(feature_values)
        outliers_removed = 0
        
        for i, (feature_name, value) in enumerate(features.items()):
            if i < len(outlier_mask) and outlier_mask[i]:
                cleaned_features[feature_name] = median_value
                outliers_removed += 1
            else:
                cleaned_features[feature_name] = value
        
        self.preprocessing_stats['outliers_removed'] += outliers_removed
        
        return cleaned_features
    
    async def _apply_normalization(self, features: Dict[str, float], rule: PreprocessingRule) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Apply normalization rule"""
        method = rule.parameters.get('method', 'z_score')
        
        if method not in self.normalization_methods:
            self.logger.warning("Unknown normalization method", method=method)
            return features, {}
        
        feature_values = list(features.values())
        if len(feature_values) < 2:
            return features, {}
        
        # Apply normalization
        normalizer = self.normalization_methods[method]
        normalized_values, norm_params = normalizer(feature_values)
        
        # Create normalized features dict
        normalized_features = {}
        for i, (feature_name, _) in enumerate(features.items()):
            if i < len(normalized_values):
                normalized_features[feature_name] = normalized_values[i]
            else:
                normalized_features[feature_name] = 0.0
        
        return normalized_features, norm_params
    
    async def _apply_missing_data_handling(self, features: Dict[str, float], rule: PreprocessingRule) -> Dict[str, float]:
        """Apply missing data handling rule"""
        strategy = rule.parameters.get('strategy', 'median_imputation')
        
        if strategy not in self.missing_data_strategies:
            self.logger.warning("Unknown missing data strategy", strategy=strategy)
            return features
        
        # Find missing values (NaN, None, inf)
        missing_features = []
        valid_values = []
        
        for feature_name, value in features.items():
            if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
                missing_features.append(feature_name)
            else:
                valid_values.append(value)
        
        if not missing_features or not valid_values:
            return features
        
        # Apply missing data strategy
        strategy_func = self.missing_data_strategies[strategy]
        imputed_value = strategy_func(valid_values)
        
        # Impute missing values
        imputed_features = features.copy()
        for feature_name in missing_features:
            imputed_features[feature_name] = imputed_value
        
        self.preprocessing_stats['missing_values_imputed'] += len(missing_features)
        
        return imputed_features
    
    async def _apply_transformation(self, features: Dict[str, float], rule: PreprocessingRule) -> Dict[str, float]:
        """Apply feature transformation rule"""
        transformation = rule.parameters.get('transformation', 'identity')
        
        if transformation == 'log':
            # Log transformation (with small constant to avoid log(0))
            return {name: math.log(max(abs(value), 1e-10)) for name, value in features.items()}
        elif transformation == 'sqrt':
            # Square root transformation  
            return {name: math.sqrt(abs(value)) for name, value in features.items()}
        elif transformation == 'square':
            # Square transformation
            return {name: value ** 2 for name, value in features.items()}
        else:
            return features
    
    # Normalization methods
    def _z_score_normalization(self, values: List[float]) -> Tuple[List[float], Dict[str, float]]:
        """Z-score normalization (mean=0, std=1)"""
        if len(values) < 2:
            return values, {}
        
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)
        
        if std_val == 0:
            return values, {'mean': mean_val, 'std': 1.0}
        
        normalized = [(v - mean_val) / std_val for v in values]
        return normalized, {'mean': mean_val, 'std': std_val}
    
    def _min_max_normalization(self, values: List[float]) -> Tuple[List[float], Dict[str, float]]:
        """Min-max normalization (range 0-1)"""
        if not values:
            return values, {}
        
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val
        
        if range_val == 0:
            return values, {'min': min_val, 'max': max_val}
        
        normalized = [(v - min_val) / range_val for v in values]
        return normalized, {'min': min_val, 'max': max_val}
    
    def _robust_normalization(self, values: List[float]) -> Tuple[List[float], Dict[str, float]]:
        """Robust normalization using median and IQR"""
        if len(values) < 2:
            return values, {}
        
        sorted_values = sorted(values)
        median_val = statistics.median(sorted_values)
        q1 = self._percentile(sorted_values, 0.25)
        q3 = self._percentile(sorted_values, 0.75)
        iqr = q3 - q1
        
        if iqr == 0:
            return values, {'median': median_val, 'iqr': 1.0}
        
        normalized = [(v - median_val) / iqr for v in values]
        return normalized, {'median': median_val, 'iqr': iqr}
    
    def _log_transform(self, values: List[float]) -> Tuple[List[float], Dict[str, float]]:
        """Log transformation"""
        if not values:
            return values, {}
        
        # Add small constant to avoid log(0)
        transformed = [math.log(max(abs(v), 1e-10)) for v in values]
        return transformed, {'transformation': 'log'}
    
    # Outlier detection methods
    def _z_score_outlier_detection(self, values: List[float], threshold: float) -> List[bool]:
        """Z-score based outlier detection"""
        if len(values) < 3:
            return [False] * len(values)
        
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 1.0
        
        if std_val == 0:
            return [False] * len(values)
        
        z_scores = [abs(v - mean_val) / std_val for v in values]
        return [z > threshold for z in z_scores]
    
    def _iqr_outlier_detection(self, values: List[float], threshold: float) -> List[bool]:
        """IQR based outlier detection"""
        if len(values) < 4:
            return [False] * len(values)
        
        sorted_values = sorted(values)
        q1 = self._percentile(sorted_values, 0.25)
        q3 = self._percentile(sorted_values, 0.75)
        iqr = q3 - q1
        
        if iqr == 0:
            return [False] * len(values)
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        return [v < lower_bound or v > upper_bound for v in values]
    
    def _isolation_forest_outliers(self, values: List[float], threshold: float) -> List[bool]:
        """Simplified isolation forest outlier detection"""
        # Simplified implementation - in production would use sklearn
        if len(values) < 5:
            return [False] * len(values)
        
        # Use statistical approximation
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 1.0
        
        # Simplified isolation score based on distance from mean
        isolation_scores = [abs(v - mean_val) / std_val if std_val > 0 else 0 for v in values]
        threshold_score = statistics.mean(isolation_scores) + 2 * statistics.stdev(isolation_scores) if len(isolation_scores) > 1 else threshold
        
        return [score > threshold_score for score in isolation_scores]
    
    # Missing data strategies
    def _drop_missing(self, valid_values: List[float]) -> float:
        """Strategy: drop missing values (return median of valid)"""
        return statistics.median(valid_values) if valid_values else 0.0
    
    def _mean_imputation(self, valid_values: List[float]) -> float:
        """Strategy: mean imputation"""
        return statistics.mean(valid_values) if valid_values else 0.0
    
    def _median_imputation(self, valid_values: List[float]) -> float:
        """Strategy: median imputation"""
        return statistics.median(valid_values) if valid_values else 0.0
    
    def _forward_fill(self, valid_values: List[float]) -> float:
        """Strategy: forward fill (use last valid value)"""
        return valid_values[-1] if valid_values else 0.0
    
    def _linear_interpolation(self, valid_values: List[float]) -> float:
        """Strategy: linear interpolation (simplified to mean)"""
        return statistics.mean(valid_values) if valid_values else 0.0
    
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile of sorted values"""
        if not sorted_values:
            return 0.0
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    async def _create_train_test_splits(self, feature_sets: List[FeatureSet],
                                      split_ratios: Tuple[float, float, float]) -> Dict[str, List[FeatureSet]]:
        """Create train/test/validation splits"""
        train_ratio, test_ratio, val_ratio = split_ratios
        
        # Ensure ratios sum to 1.0
        total_ratio = sum(split_ratios)
        if abs(total_ratio - 1.0) > 0.01:
            self.logger.warning("Split ratios don't sum to 1.0", total=total_ratio)
            train_ratio, test_ratio, val_ratio = [r/total_ratio for r in split_ratios]
        
        n_features_sets = len(feature_sets)
        if n_features_sets < 3:
            # Not enough data for proper splitting
            return {
                'train': feature_sets,
                'test': feature_sets[:1] if feature_sets else [],
                'validation': feature_sets[:1] if feature_sets else []
            }
        
        # Calculate split indices
        train_end = int(n_features_sets * train_ratio)
        test_end = train_end + int(n_features_sets * test_ratio)
        
        splits = {
            'train': feature_sets[:train_end],
            'test': feature_sets[train_end:test_end],
            'validation': feature_sets[test_end:]
        }
        
        return splits
    
    async def _calculate_preprocessing_quality(self, processed_feature_sets: List[FeatureSet],
                                             original_feature_sets: List[FeatureSet]) -> Dict[str, float]:
        """Calculate preprocessing quality metrics"""
        if not processed_feature_sets or not original_feature_sets:
            return {'overall_quality': 0.0}
        
        quality_metrics = {}
        
        # Feature retention rate
        original_features = sum(len(fs.features) for fs in original_feature_sets)
        processed_features = sum(len(fs.features) for fs in processed_feature_sets)
        quality_metrics['feature_retention_rate'] = processed_features / original_features if original_features > 0 else 0
        
        # Data completeness after preprocessing
        all_values = []
        for fs in processed_feature_sets:
            all_values.extend(fs.features.values())
        
        if all_values:
            valid_values = [v for v in all_values if isinstance(v, (int, float)) and math.isfinite(v)]
            quality_metrics['data_completeness'] = len(valid_values) / len(all_values)
            
            # Feature variance (non-zero variance indicates useful features)
            if len(valid_values) > 1:
                variance = statistics.stdev(valid_values) ** 2
                quality_metrics['feature_variance'] = min(1.0, variance)
            else:
                quality_metrics['feature_variance'] = 0.0
        else:
            quality_metrics['data_completeness'] = 0.0
            quality_metrics['feature_variance'] = 0.0
        
        # Processing efficiency (inverse of processing time per feature)
        processing_times = list(self.preprocessing_stats['processing_times'])
        if processing_times:
            avg_time = statistics.mean(processing_times)
            efficiency = 1.0 / max(0.01, avg_time)  # Inverse time, bounded
            quality_metrics['processing_efficiency'] = min(1.0, efficiency / 100)  # Normalized
        
        # Individual feature set quality
        individual_qualities = [fs.quality_score for fs in processed_feature_sets]
        if individual_qualities:
            quality_metrics['average_feature_quality'] = statistics.mean(individual_qualities)
            quality_metrics['min_feature_quality'] = min(individual_qualities)
        
        # Overall quality score (weighted average)
        weights = {
            'feature_retention_rate': 0.2,
            'data_completeness': 0.3,
            'feature_variance': 0.2,
            'processing_efficiency': 0.1,
            'average_feature_quality': 0.2
        }
        
        overall_quality = sum(
            quality_metrics.get(metric, 0) * weight 
            for metric, weight in weights.items()
        )
        
        quality_metrics['overall_quality'] = overall_quality
        
        return quality_metrics
    
    def _calculate_processed_quality_score(self, features: Dict[str, float]) -> float:
        """Calculate quality score for processed features"""
        if not features:
            return 0.0
        
        quality_scores = []
        
        # Completeness (no NaN/inf values)
        valid_values = [v for v in features.values() if isinstance(v, (int, float)) and math.isfinite(v)]
        completeness = len(valid_values) / len(features)
        quality_scores.append(completeness)
        
        # Variance (features should have some variability)
        if len(valid_values) > 1:
            variance = statistics.stdev(valid_values) ** 2
            normalized_variance = min(1.0, variance / 10)  # Normalize variance score
            quality_scores.append(normalized_variance)
        
        # Range (features should span reasonable range)
        if valid_values:
            value_range = max(valid_values) - min(valid_values)
            range_score = min(1.0, value_range / 100)  # Normalize range score
            quality_scores.append(range_score)
        
        return statistics.mean(quality_scores)
    
    async def _validate_preprocessed_data(self, dataset: PreprocessedDataset) -> ValidationResult:
        """Final validation of preprocessed dataset"""
        validation_id = f"final_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        issues = []
        scores = []
        
        # Check train/test/validation splits
        splits = dataset.train_test_splits
        if not splits.get('train'):
            issues.append({
                'type': 'critical',
                'message': 'No training data available',
                'impact': 'Cannot train models'
            })
            scores.append(0.0)
        else:
            scores.append(1.0)
        
        # Check feature quality across all processed feature sets
        for feature_set in dataset.processed_feature_sets:
            if feature_set.quality_score < 0.5:
                issues.append({
                    'type': 'warning',
                    'message': f'Low quality feature set: {feature_set.feature_id}',
                    'impact': 'May affect model performance',
                    'quality_score': feature_set.quality_score
                })
            scores.append(feature_set.quality_score)
        
        # Check normalization parameters
        if not dataset.normalization_parameters:
            issues.append({
                'type': 'info',
                'message': 'No normalization parameters stored',
                'impact': 'Inference might be inconsistent'
            })
        
        validation_score = statistics.mean(scores) if scores else 0.0
        validation_passed = validation_score >= 0.7 and len([i for i in issues if i['type'] == 'critical']) == 0
        
        recommendations = []
        if validation_score < 0.8:
            recommendations.append("Consider improving preprocessing rules")
        if len(issues) > 3:
            recommendations.append("Multiple preprocessing issues detected")
        
        return ValidationResult(
            validation_id=validation_id,
            dataset_tested=dataset.dataset_id,
            validation_passed=validation_passed,
            validation_score=validation_score,
            issues_found=issues,
            recommendations=recommendations
        )
    
    def get_preprocessing_statistics(self) -> Dict[str, Any]:
        """Get preprocessing statistics"""
        avg_processing_time = statistics.mean(self.preprocessing_stats['processing_times']) if self.preprocessing_stats['processing_times'] else 0
        avg_quality = statistics.mean(self.preprocessing_stats['quality_scores']) if self.preprocessing_stats['quality_scores'] else 0
        
        return {
            'datasets_processed': self.preprocessing_stats['datasets_processed'],
            'total_features_processed': self.preprocessing_stats['total_features_processed'],
            'outliers_removed': self.preprocessing_stats['outliers_removed'],
            'missing_values_imputed': self.preprocessing_stats['missing_values_imputed'],
            'average_processing_time_seconds': avg_processing_time,
            'average_quality_score': avg_quality,
            'cached_normalizations': len(self.normalization_cache),
            'supported_methods': {
                'normalization': list(self.normalization_methods.keys()),
                'outlier_detection': list(self.outlier_methods.keys()),
                'missing_data': list(self.missing_data_strategies.keys())
            }
        }


# Module factory function
def create_data_preprocessing_module(config: ModuleConfig = None) -> DataPreprocessingModule:
    """Factory function to create Data Preprocessing Module"""
    return DataPreprocessingModule(config)


# Example usage and testing
async def test_data_preprocessing():
    """Test function for Data Preprocessing Module"""
    print("🧪 Testing Data Preprocessing Module")
    
    # Create mock engineering result with feature sets
    from datetime import datetime
    import statistics
    
    # Mock feature set 1: Performance features
    perf_features = {
        'avg_throughput_eps': 150.5,
        'max_throughput_eps': 200.0,
        'avg_latency_p99_ms': 45.2,
        'max_latency_p99_ms': 80.0,
        'system_health_score': 0.85
    }
    
    # Add some outliers and missing data for testing
    perf_features['outlier_feature'] = 1000.0  # Clear outlier
    perf_features['missing_feature'] = float('nan')  # Missing data
    
    perf_feature_set = FeatureSet(
        feature_id="performance_features",
        source_collection_id="test_collection",
        feature_type="performance",
        features=perf_features,
        feature_metadata={'source': 'test'},
        created_at=datetime.now(),
        quality_score=0.8
    )
    
    # Mock feature set 2: Trading features
    trading_features = {
        'avg_trading_confidence': 0.75,
        'avg_analysis_score': 7.5,
        'price_momentum_1': 0.02,
        'price_volatility_10': 0.15,
        'rsi': 65.0
    }
    
    trading_feature_set = FeatureSet(
        feature_id="trading_features",
        source_collection_id="test_collection",
        feature_type="trading",
        features=trading_features,
        feature_metadata={'source': 'test'},
        created_at=datetime.now(),
        quality_score=0.9
    )
    
    # Mock engineering result
    mock_engineering_result = EngineeringResult(
        result_id="test_engineering_result",
        original_collection=None,
        feature_sets=[perf_feature_set, trading_feature_set],
        total_features=len(perf_features) + len(trading_features),
        processing_time_seconds=2.5,
        quality_metrics={'overall_quality': 0.85}
    )
    
    # Create preprocessing module
    preprocessor = create_data_preprocessing_module()
    
    try:
        print("🔧 Starting data preprocessing test...")
        
        # Test preprocessing
        preprocessed_dataset = await preprocessor.preprocess_ml_data(
            mock_engineering_result,
            preprocessing_rules=None,  # Use default rules
            train_test_split=(0.6, 0.3, 0.1),
            validation_enabled=True
        )
        
        print(f"✅ Data preprocessing completed:")
        print(f"   Dataset ID: {preprocessed_dataset.dataset_id}")
        print(f"   Processed Feature Sets: {len(preprocessed_dataset.processed_feature_sets)}")
        print(f"   Total Features: {sum(len(fs.features) for fs in preprocessed_dataset.processed_feature_sets)}")
        print(f"   Rules Applied: {len(preprocessed_dataset.preprocessing_rules_applied)}")
        print(f"   Quality Score: {preprocessed_dataset.quality_metrics.get('overall_quality', 0):.3f}")
        
        # Show train/test splits
        splits = preprocessed_dataset.train_test_splits
        print(f"\n📊 Data Splits:")
        print(f"   Train: {len(splits.get('train', []))} feature sets")
        print(f"   Test: {len(splits.get('test', []))} feature sets")
        print(f"   Validation: {len(splits.get('validation', []))} feature sets")
        
        # Show some processed features
        if preprocessed_dataset.processed_feature_sets:
            first_fs = preprocessed_dataset.processed_feature_sets[0]
            print(f"\n🔧 Sample Processed Features ({first_fs.feature_type}):")
            for i, (name, value) in enumerate(list(first_fs.features.items())[:5]):
                print(f"     {name}: {value:.3f}")
            
            if len(first_fs.features) > 5:
                print(f"     ... and {len(first_fs.features) - 5} more")
        
        # Show normalization parameters
        norm_params = preprocessed_dataset.normalization_parameters
        if norm_params:
            print(f"\n📏 Normalization Parameters:")
            for fs_id, params in norm_params.items():
                if params:
                    print(f"     {fs_id}: {list(params.keys())}")
        
        # Show statistics
        stats = preprocessor.get_preprocessing_statistics()
        print(f"\n📈 Preprocessing Statistics:")
        print(f"   Datasets Processed: {stats['datasets_processed']}")
        print(f"   Features Processed: {stats['total_features_processed']}")
        print(f"   Outliers Removed: {stats['outliers_removed']}")
        print(f"   Missing Values Imputed: {stats['missing_values_imputed']}")
        print(f"   Average Quality: {stats['average_quality_score']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run module test
    import asyncio
    asyncio.run(test_data_preprocessing())
    print("🎯 Data Preprocessing Module test completed")