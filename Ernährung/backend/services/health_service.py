from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from ..database.models import HealthMetrics
from ..models.schemas import HealthMetricsCreate, HealthMetricsUpdate

class HealthService:
    
    @staticmethod
    def get_user_health_metrics(
        db: Session, 
        user_id: int, 
        filters: Dict[str, Any] = None, 
        limit: int = 100
    ) -> List[HealthMetrics]:
        """Get health metrics for a user with optional date filtering"""
        query = db.query(HealthMetrics).filter(HealthMetrics.user_id == user_id)
        
        if filters:
            if 'start_date' in filters:
                query = query.filter(HealthMetrics.date >= filters['start_date'])
            if 'end_date' in filters:
                query = query.filter(HealthMetrics.date <= filters['end_date'])
        
        return query.order_by(HealthMetrics.date.desc()).limit(limit).all()
    
    @staticmethod
    def get_health_metrics_by_date(db: Session, user_id: int, target_date: date) -> Optional[HealthMetrics]:
        """Get health metrics for a specific date"""
        return db.query(HealthMetrics).filter(
            HealthMetrics.user_id == user_id,
            HealthMetrics.date == target_date
        ).first()
    
    @staticmethod
    def create_health_metrics(db: Session, user_id: int, health_data: HealthMetricsCreate) -> HealthMetrics:
        """Create new health metrics entry"""
        # Check if entry already exists for this date
        existing = HealthService.get_health_metrics_by_date(db, user_id, health_data.date)
        if existing:
            # Update existing entry instead
            return HealthService.update_health_metrics(db, user_id, health_data.date, 
                                                     HealthMetricsUpdate(**health_data.dict()))
        
        db_metrics = HealthMetrics(
            user_id=user_id,
            date=health_data.date,
            weight=health_data.weight,
            blood_pressure_systolic=health_data.blood_pressure_systolic,
            blood_pressure_diastolic=health_data.blood_pressure_diastolic,
            pulse=health_data.pulse,
            notes=health_data.notes,
            created_at=datetime.now()
        )
        db.add(db_metrics)
        db.commit()
        db.refresh(db_metrics)
        return db_metrics
    
    @staticmethod
    def update_health_metrics(
        db: Session, 
        user_id: int, 
        target_date: date, 
        health_data: HealthMetricsUpdate
    ) -> HealthMetrics:
        """Update health metrics for a specific date"""
        db_metrics = db.query(HealthMetrics).filter(
            HealthMetrics.user_id == user_id,
            HealthMetrics.date == target_date
        ).first()
        
        if db_metrics:
            update_data = health_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_metrics, field, value)
            db.commit()
            db.refresh(db_metrics)
        
        return db_metrics
    
    @staticmethod
    def get_weight_trend(db: Session, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get weight trend data for the last N days"""
        start_date = date.today().replace(day=1)  # Start of month
        
        weight_data = db.query(HealthMetrics).filter(
            HealthMetrics.user_id == user_id,
            HealthMetrics.date >= start_date,
            HealthMetrics.weight.isnot(None)
        ).order_by(HealthMetrics.date.asc()).all()
        
        return [
            {
                'date': metrics.date,
                'weight': float(metrics.weight) if metrics.weight else None
            }
            for metrics in weight_data
        ]
    
    @staticmethod
    def get_health_summary(db: Session, user_id: int) -> Dict[str, Any]:
        """Get health summary statistics"""
        # Get latest metrics
        latest = db.query(HealthMetrics).filter(
            HealthMetrics.user_id == user_id
        ).order_by(HealthMetrics.date.desc()).first()
        
        # Get weight trend (last 30 days)
        weight_trend = HealthService.get_weight_trend(db, user_id, 30)
        
        summary = {
            'latest_weight': float(latest.weight) if latest and latest.weight else None,
            'latest_date': latest.date if latest else None,
            'weight_trend_30d': weight_trend,
            'total_entries': db.query(HealthMetrics).filter(
                HealthMetrics.user_id == user_id
            ).count()
        }
        
        # Calculate weight change if we have trend data
        if len(weight_trend) >= 2:
            first_weight = next((d['weight'] for d in weight_trend if d['weight']), None)
            last_weight = next((d['weight'] for d in reversed(weight_trend) if d['weight']), None)
            
            if first_weight and last_weight:
                summary['weight_change_30d'] = round(last_weight - first_weight, 2)
        
        return summary