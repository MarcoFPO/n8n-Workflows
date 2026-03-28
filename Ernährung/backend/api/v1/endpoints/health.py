from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from database import get_db
from models.database import User as UserModel, HealthMetric as HealthMetricModel
from schemas.health import HealthMetric, HealthMetricCreate, HealthMetricUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/users/{user_id}", response_model=List[HealthMetric])
async def get_user_health_metrics(
    user_id: int,
    start_date: Optional[date] = Query(None, description="Startdatum für Filterung"),
    end_date: Optional[date] = Query(None, description="Enddatum für Filterung"),
    limit: int = Query(30, ge=1, le=365, description="Maximale Anzahl Einträge"),
    db: Session = Depends(get_db)
):
    """Gesundheitsverlauf eines Benutzers abrufen."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        query = db.query(HealthMetricModel).filter(HealthMetricModel.user_id == user_id)
        
        if start_date:
            query = query.filter(HealthMetricModel.date >= start_date)
        if end_date:
            query = query.filter(HealthMetricModel.date <= end_date)
        
        health_metrics = query.order_by(HealthMetricModel.date.desc()).limit(limit).all()
        return health_metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health metrics for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/users/{user_id}", response_model=HealthMetric, status_code=status.HTTP_201_CREATED)
async def create_health_metric(
    user_id: int,
    health_metric: HealthMetricCreate,
    db: Session = Depends(get_db)
):
    """Neue Gesundheitsmessung hinzufügen."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prüfe ob bereits ein Eintrag für dieses Datum existiert
        existing = db.query(HealthMetricModel).filter(
            HealthMetricModel.user_id == user_id,
            HealthMetricModel.date == health_metric.date
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Health metric for date {health_metric.date} already exists"
            )
        
        health_data = health_metric.dict()
        health_data['user_id'] = user_id
        db_health_metric = HealthMetricModel(**health_data)
        
        db.add(db_health_metric)
        db.commit()
        db.refresh(db_health_metric)
        return db_health_metric
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating health metric for user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/users/{user_id}/{metric_date}", response_model=HealthMetric)
async def update_health_metric(
    user_id: int,
    metric_date: date,
    health_metric: HealthMetricUpdate,
    db: Session = Depends(get_db)
):
    """Tageswerte aktualisieren."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_health_metric = db.query(HealthMetricModel).filter(
            HealthMetricModel.user_id == user_id,
            HealthMetricModel.date == metric_date
        ).first()
        
        if not db_health_metric:
            raise HTTPException(status_code=404, detail="Health metric not found")
        
        update_data = health_metric.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_health_metric, field, value)
        
        db.commit()
        db.refresh(db_health_metric)
        return db_health_metric
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating health metric for user {user_id}, date {metric_date}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/users/{user_id}/latest", response_model=HealthMetric)
async def get_latest_health_metric(user_id: int, db: Session = Depends(get_db)):
    """Letzte Gesundheitsmessung abrufen."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        latest_metric = db.query(HealthMetricModel).filter(
            HealthMetricModel.user_id == user_id
        ).order_by(HealthMetricModel.date.desc()).first()
        
        if not latest_metric:
            raise HTTPException(status_code=404, detail="No health metrics found")
        
        return latest_metric
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest health metric for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/users/{user_id}/{metric_date}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_metric(
    user_id: int,
    metric_date: date,
    db: Session = Depends(get_db)
):
    """Gesundheitsmessung löschen."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_health_metric = db.query(HealthMetricModel).filter(
            HealthMetricModel.user_id == user_id,
            HealthMetricModel.date == metric_date
        ).first()
        
        if not db_health_metric:
            raise HTTPException(status_code=404, detail="Health metric not found")
        
        db.delete(db_health_metric)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting health metric for user {user_id}, date {metric_date}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")