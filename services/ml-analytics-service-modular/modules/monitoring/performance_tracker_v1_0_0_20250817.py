#!/usr/bin/env python3
"""
Performance Tracker v1.0.0
Überwacht und trackt ML-Model-Performance

Autor: Claude Code  
Datum: 17. August 2025
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Tracks und überwacht ML-Model-Performance
    """
    
    def __init__(self, database_connection, event_bus):
        self.database_connection = database_connection
        self.event_bus = event_bus
        
        # Performance-Metriken Cache
        self.performance_cache: Dict[str, Dict] = {}
        
    async def record_prediction_performance(self, 
                                          model_id: str,
                                          symbol: str,
                                          prediction_date: datetime,
                                          predicted_values: List[float],
                                          actual_values: List[float],
                                          horizon_days: int):
        """
        Zeichnet Performance einer Vorhersage auf
        """
        try:
            # Performance-Metriken berechnen
            performance_metrics = self._calculate_performance_metrics(
                predicted_values, actual_values
            )
            
            # In Datenbank speichern
            await self._store_performance_record(
                model_id, symbol, prediction_date, 
                predicted_values, actual_values, performance_metrics
            )
            
            # Performance-Event publizieren
            await self.event_bus.publish_event(
                event_type="ml.performance.recorded",
                data={
                    'model_id': model_id,
                    'symbol': symbol,
                    'horizon_days': horizon_days,
                    'mae': performance_metrics['mae'],
                    'directional_accuracy': performance_metrics['directional_accuracy'],
                    'prediction_date': prediction_date.isoformat()
                }
            )
            
            logger.info(f"Performance recorded for {model_id}: MAE={performance_metrics['mae']:.4f}")
            
        except Exception as e:
            logger.error(f"Error recording performance: {str(e)}")
            raise
    
    def _calculate_performance_metrics(self, 
                                     predicted: List[float], 
                                     actual: List[float]) -> Dict[str, float]:
        """
        Berechnet Performance-Metriken
        """
        import numpy as np
        
        predicted = np.array(predicted)
        actual = np.array(actual)
        
        # Mean Absolute Error
        mae = np.mean(np.abs(predicted - actual))
        
        # Mean Squared Error
        mse = np.mean((predicted - actual) ** 2)
        
        # Root Mean Squared Error
        rmse = np.sqrt(mse)
        
        # Directional Accuracy (für Zeitreihen-Vorhersagen)
        if len(predicted) > 1 and len(actual) > 1:
            pred_direction = np.diff(predicted) > 0
            actual_direction = np.diff(actual) > 0
            directional_accuracy = np.mean(pred_direction == actual_direction)
        else:
            directional_accuracy = 0.0
        
        # R² Score
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        r2_score = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        
        return {
            'mae': float(mae),
            'mse': float(mse),
            'rmse': float(rmse),
            'directional_accuracy': float(directional_accuracy),
            'r2_score': float(r2_score)
        }
    
    async def _store_performance_record(self,
                                      model_id: str,
                                      symbol: str,
                                      evaluation_date: datetime,
                                      predicted_values: List[float],
                                      actual_values: List[float],
                                      metrics: Dict[str, float]):
        """
        Speichert Performance-Record in Datenbank
        """
        query = """
        INSERT INTO ml_model_performance 
        (model_id, symbol, evaluation_date, predicted_values, actual_values,
         mae_score, mse_score, directional_accuracy, r2_score)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        await self.database_connection.execute(
            query,
            model_id,
            symbol,
            evaluation_date.date(),
            predicted_values,
            actual_values,
            metrics['mae'],
            metrics['mse'],
            metrics['directional_accuracy'],
            metrics['r2_score']
        )
    
    async def get_model_performance_summary(self, 
                                          model_id: str, 
                                          days_back: int = 30) -> Dict[str, Any]:
        """
        Gibt Performance-Zusammenfassung für Modell zurück
        """
        query = """
        SELECT 
            COUNT(*) as evaluation_count,
            AVG(mae_score) as avg_mae,
            AVG(mse_score) as avg_mse,
            AVG(directional_accuracy) as avg_directional_accuracy,
            AVG(r2_score) as avg_r2,
            MIN(mae_score) as best_mae,
            MAX(mae_score) as worst_mae,
            MAX(created_at) as last_evaluation
        FROM ml_model_performance 
        WHERE model_id = $1 
        AND created_at >= NOW() - INTERVAL '%s days'
        """ % days_back
        
        row = await self.database_connection.fetchrow(query, model_id)
        
        if row and row['evaluation_count'] > 0:
            return {
                'model_id': model_id,
                'evaluation_count': row['evaluation_count'],
                'avg_mae': float(row['avg_mae']),
                'avg_mse': float(row['avg_mse']),
                'avg_directional_accuracy': float(row['avg_directional_accuracy']),
                'avg_r2_score': float(row['avg_r2']),
                'best_mae': float(row['best_mae']),
                'worst_mae': float(row['worst_mae']),
                'last_evaluation': row['last_evaluation'],
                'days_analyzed': days_back
            }
        else:
            return {
                'model_id': model_id,
                'evaluation_count': 0,
                'message': 'No performance data available'
            }
    
    async def get_symbol_performance_ranking(self, 
                                           symbol: str, 
                                           model_type: str = None,
                                           horizon_days: int = None) -> List[Dict]:
        """
        Gibt Performance-Ranking für Symbol zurück
        """
        conditions = ["p.symbol = $1"]
        params = [symbol]
        param_count = 1
        
        if model_type:
            param_count += 1
            conditions.append(f"m.model_type = ${param_count}")
            params.append(model_type)
            
        if horizon_days:
            param_count += 1
            conditions.append(f"m.horizon_days = ${param_count}")
            params.append(horizon_days)
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT 
            m.model_id,
            m.model_type,
            m.horizon_days,
            m.model_version,
            COUNT(p.performance_id) as evaluations,
            AVG(p.mae_score) as avg_mae,
            AVG(p.directional_accuracy) as avg_directional_accuracy,
            AVG(p.r2_score) as avg_r2,
            MAX(p.created_at) as last_evaluation
        FROM ml_model_metadata m
        LEFT JOIN ml_model_performance p ON m.model_id = p.model_id
        WHERE {where_clause}
        AND m.status = 'active'
        AND p.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY m.model_id, m.model_type, m.horizon_days, m.model_version
        HAVING COUNT(p.performance_id) > 0
        ORDER BY avg_mae ASC, avg_directional_accuracy DESC
        """
        
        rows = await self.database_connection.fetch(query, *params)
        
        return [
            {
                'model_id': row['model_id'],
                'model_type': row['model_type'],
                'horizon_days': row['horizon_days'],
                'model_version': row['model_version'],
                'evaluations': row['evaluations'],
                'avg_mae': float(row['avg_mae']),
                'avg_directional_accuracy': float(row['avg_directional_accuracy']),
                'avg_r2_score': float(row['avg_r2']),
                'last_evaluation': row['last_evaluation']
            }
            for row in rows
        ]
    
    async def check_model_degradation(self, 
                                    model_id: str,
                                    threshold_mae_increase: float = 0.1,
                                    days_to_compare: int = 7) -> Dict[str, Any]:
        """
        Prüft auf Model-Performance-Degradation
        """
        query = """
        WITH recent_performance AS (
            SELECT AVG(mae_score) as recent_mae,
                   AVG(directional_accuracy) as recent_accuracy
            FROM ml_model_performance 
            WHERE model_id = $1 
            AND created_at >= NOW() - INTERVAL '%s days'
        ),
        historical_performance AS (
            SELECT AVG(mae_score) as historical_mae,
                   AVG(directional_accuracy) as historical_accuracy
            FROM ml_model_performance 
            WHERE model_id = $1 
            AND created_at >= NOW() - INTERVAL '%s days'
            AND created_at < NOW() - INTERVAL '%s days'
        )
        SELECT 
            r.recent_mae,
            r.recent_accuracy,
            h.historical_mae,
            h.historical_accuracy
        FROM recent_performance r, historical_performance h
        """ % (days_to_compare, days_to_compare * 2, days_to_compare)
        
        row = await self.database_connection.fetchrow(query, model_id)
        
        if not row or not all([row['recent_mae'], row['historical_mae']]):
            return {
                'model_id': model_id,
                'degradation_detected': False,
                'reason': 'Insufficient data for comparison'
            }
        
        recent_mae = float(row['recent_mae'])
        historical_mae = float(row['historical_mae'])
        recent_accuracy = float(row['recent_accuracy'])
        historical_accuracy = float(row['historical_accuracy'])
        
        mae_increase = (recent_mae - historical_mae) / historical_mae
        accuracy_decrease = (historical_accuracy - recent_accuracy) / historical_accuracy
        
        degradation_detected = (
            mae_increase > threshold_mae_increase or 
            accuracy_decrease > threshold_mae_increase
        )
        
        result = {
            'model_id': model_id,
            'degradation_detected': degradation_detected,
            'recent_mae': recent_mae,
            'historical_mae': historical_mae,
            'mae_increase_pct': mae_increase * 100,
            'recent_accuracy': recent_accuracy,
            'historical_accuracy': historical_accuracy,
            'accuracy_decrease_pct': accuracy_decrease * 100,
            'days_compared': days_to_compare
        }
        
        if degradation_detected:
            await self.event_bus.publish_event(
                event_type="ml.performance.degradation_detected",
                data=result
            )
            
            logger.warning(f"Performance degradation detected for model {model_id}")
        
        return result
    
    async def get_service_health_metrics(self) -> Dict[str, Any]:
        """
        Gibt Service-Health-Metriken zurück
        """
        # System-Performance-Metriken
        import psutil
        
        health_metrics = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            },
            'ml_service': await self._get_ml_service_metrics()
        }
        
        # Health-Status in DB speichern
        await self._store_health_metrics(health_metrics)
        
        return health_metrics
    
    async def _get_ml_service_metrics(self) -> Dict[str, Any]:
        """
        Gibt ML-Service-spezifische Metriken zurück
        """
        # Aktive Modelle zählen
        query_active_models = """
        SELECT model_type, COUNT(*) as count
        FROM ml_model_metadata 
        WHERE status = 'active'
        GROUP BY model_type
        """
        
        active_models = await self.database_connection.fetch(query_active_models)
        
        # Letzte Performance-Evaluierungen
        query_recent_evaluations = """
        SELECT COUNT(*) as recent_evaluations
        FROM ml_model_performance 
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        """
        
        recent_eval_row = await self.database_connection.fetchrow(query_recent_evaluations)
        
        # Durchschnittliche Performance
        query_avg_performance = """
        SELECT 
            AVG(mae_score) as avg_mae,
            AVG(directional_accuracy) as avg_accuracy
        FROM ml_model_performance 
        WHERE created_at >= NOW() - INTERVAL '7 days'
        """
        
        avg_perf_row = await self.database_connection.fetchrow(query_avg_performance)
        
        return {
            'active_models': {row['model_type']: row['count'] for row in active_models},
            'recent_evaluations_24h': recent_eval_row['recent_evaluations'] if recent_eval_row else 0,
            'avg_mae_7d': float(avg_perf_row['avg_mae']) if avg_perf_row and avg_perf_row['avg_mae'] else None,
            'avg_accuracy_7d': float(avg_perf_row['avg_accuracy']) if avg_perf_row and avg_perf_row['avg_accuracy'] else None
        }
    
    async def _store_health_metrics(self, metrics: Dict[str, Any]):
        """
        Speichert Health-Metriken in Datenbank
        """
        try:
            query = """
            INSERT INTO ml_service_health 
            (service_name, status, metrics)
            VALUES ($1, $2, $3)
            """
            
            # Status basierend auf Metriken bestimmen
            cpu_percent = metrics['system']['cpu_percent']
            memory_percent = metrics['system']['memory_percent']
            
            if cpu_percent > 90 or memory_percent > 90:
                status = 'critical'
            elif cpu_percent > 70 or memory_percent > 70:
                status = 'warning'
            else:
                status = 'healthy'
            
            await self.database_connection.execute(
                query, 
                'ml-analytics', 
                status, 
                json.dumps(metrics)
            )
            
        except Exception as e:
            logger.error(f"Error storing health metrics: {str(e)}")
    
    async def run_periodic_performance_checks(self):
        """
        Führt periodische Performance-Checks durch
        """
        logger.info("Starting periodic performance checks")
        
        try:
            # Alle aktiven Modelle holen
            query = """
            SELECT model_id, model_type, horizon_days
            FROM ml_model_metadata 
            WHERE status = 'active'
            """
            
            models = await self.database_connection.fetch(query)
            
            for model in models:
                try:
                    # Degradation-Check
                    degradation_result = await self.check_model_degradation(
                        model['model_id']
                    )
                    
                    if degradation_result['degradation_detected']:
                        logger.warning(f"Degradation detected for model {model['model_id']}")
                    
                    # Performance-Summary aktualisieren
                    summary = await self.get_model_performance_summary(
                        model['model_id']
                    )
                    
                    # Cache aktualisieren
                    self.performance_cache[model['model_id']] = {
                        'summary': summary,
                        'last_updated': datetime.now()
                    }
                    
                except Exception as e:
                    logger.error(f"Error checking model {model['model_id']}: {str(e)}")
            
            # Health-Metriken sammeln
            health_metrics = await self.get_service_health_metrics()
            
            logger.info("Periodic performance checks completed")
            
        except Exception as e:
            logger.error(f"Error in periodic performance checks: {str(e)}")
    
    async def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """
        Gibt Dashboard-Daten für Performance-Monitoring zurück
        """
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': await self._get_performance_summary(),
            'top_performing_models': await self._get_top_performing_models(),
            'recent_degradations': await self._get_recent_degradations(),
            'system_health': await self.get_service_health_metrics()
        }
        
        return dashboard_data
    
    async def _get_performance_summary(self) -> Dict[str, Any]:
        """
        Gibt Performance-Gesamtübersicht zurück
        """
        query = """
        SELECT 
            COUNT(DISTINCT m.model_id) as total_active_models,
            COUNT(p.performance_id) as total_evaluations_7d,
            AVG(p.mae_score) as avg_mae_7d,
            AVG(p.directional_accuracy) as avg_accuracy_7d
        FROM ml_model_metadata m
        LEFT JOIN ml_model_performance p ON m.model_id = p.model_id 
        WHERE m.status = 'active'
        AND (p.created_at >= NOW() - INTERVAL '7 days' OR p.created_at IS NULL)
        """
        
        row = await self.database_connection.fetchrow(query)
        
        return {
            'total_active_models': row['total_active_models'] if row else 0,
            'total_evaluations_7d': row['total_evaluations_7d'] if row else 0,
            'avg_mae_7d': float(row['avg_mae_7d']) if row and row['avg_mae_7d'] else None,
            'avg_accuracy_7d': float(row['avg_accuracy_7d']) if row and row['avg_accuracy_7d'] else None
        }
    
    async def _get_top_performing_models(self, limit: int = 5) -> List[Dict]:
        """
        Gibt Top-performende Modelle zurück
        """
        query = """
        SELECT 
            m.model_id,
            m.model_type,
            m.horizon_days,
            AVG(p.mae_score) as avg_mae,
            AVG(p.directional_accuracy) as avg_accuracy,
            COUNT(p.performance_id) as evaluations
        FROM ml_model_metadata m
        JOIN ml_model_performance p ON m.model_id = p.model_id
        WHERE m.status = 'active'
        AND p.created_at >= NOW() - INTERVAL '7 days'
        GROUP BY m.model_id, m.model_type, m.horizon_days
        HAVING COUNT(p.performance_id) >= 3
        ORDER BY avg_accuracy DESC, avg_mae ASC
        LIMIT $1
        """
        
        rows = await self.database_connection.fetch(query, limit)
        
        return [
            {
                'model_id': row['model_id'],
                'model_type': row['model_type'],
                'horizon_days': row['horizon_days'],
                'avg_mae': float(row['avg_mae']),
                'avg_accuracy': float(row['avg_accuracy']),
                'evaluations': row['evaluations']
            }
            for row in rows
        ]
    
    async def _get_recent_degradations(self, days: int = 7) -> List[Dict]:
        """
        Gibt kürzliche Performance-Degradationen zurück
        """
        # Implementierung vereinfacht - in Praxis würde man komplexere Degradation-Detection verwenden
        query = """
        SELECT 
            m.model_id,
            m.model_type,
            m.horizon_days,
            AVG(p.mae_score) as recent_mae
        FROM ml_model_metadata m
        JOIN ml_model_performance p ON m.model_id = p.model_id
        WHERE m.status = 'active'
        AND p.created_at >= NOW() - INTERVAL '%s days'
        GROUP BY m.model_id, m.model_type, m.horizon_days
        HAVING AVG(p.mae_score) > 0.05  -- Threshold für "schlechte" Performance
        ORDER BY recent_mae DESC
        """ % days
        
        rows = await self.database_connection.fetch(query)
        
        return [
            {
                'model_id': row['model_id'],
                'model_type': row['model_type'],
                'horizon_days': row['horizon_days'],
                'recent_mae': float(row['recent_mae'])
            }
            for row in rows
        ]