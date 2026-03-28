from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from ..database.connection import get_database
from ..models.schemas import (
    HealthMetrics as HealthMetricsSchema,
    HealthMetricsCreate,
    HealthMetricsUpdate,
    APIResponse
)
from ..services.health_service import HealthService

router = APIRouter()

@router.get("/users/{user_id}/health", response_model=List[HealthMetricsSchema])
async def get_health_history(
    user_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_database)
):
    """Get health metrics history for user"""
    try:
        filters = {}
        if start_date:
            filters['start_date'] = date.fromisoformat(start_date)
        if end_date:
            filters['end_date'] = date.fromisoformat(end_date)
        
        health_data = HealthService.get_user_health_metrics(db, user_id, filters, limit)
        return health_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching health data: {str(e)}"
        )

@router.post("/users/{user_id}/health", response_model=HealthMetricsSchema)
async def add_health_metrics(
    user_id: int,
    health_data: HealthMetricsCreate,
    db: Session = Depends(get_database)
):
    """Add new health measurement"""
    try:
        # Check if user exists
        from ..services.user_service import UserService
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        new_metrics = HealthService.create_health_metrics(db, user_id, health_data)
        return new_metrics
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding health metrics: {str(e)}"
        )

@router.put("/users/{user_id}/health/{measurement_date}", response_model=HealthMetricsSchema)
async def update_health_metrics(
    user_id: int,
    measurement_date: str,
    health_data: HealthMetricsUpdate,
    db: Session = Depends(get_database)
):
    """Update health metrics for a specific date"""
    try:
        target_date = date.fromisoformat(measurement_date)
        
        existing_metrics = HealthService.get_health_metrics_by_date(db, user_id, target_date)
        if not existing_metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Health metrics not found for this date"
            )
        
        updated_metrics = HealthService.update_health_metrics(db, user_id, target_date, health_data)
        return updated_metrics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating health metrics: {str(e)}"
        )