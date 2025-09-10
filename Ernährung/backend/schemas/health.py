from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class HealthMetricBase(BaseModel):
    date: date = Field(..., description="Datum der Messung")
    weight: Optional[Decimal] = Field(None, gt=0, le=300, description="Gewicht in kg")
    blood_pressure_systolic: Optional[int] = Field(None, ge=60, le=300, description="Systolischer Blutdruck")
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=200, description="Diastolischer Blutdruck")
    pulse: Optional[int] = Field(None, ge=30, le=220, description="Puls")
    notes: Optional[str] = Field(None, description="Notizen")

class HealthMetricCreate(HealthMetricBase):
    pass

class HealthMetricUpdate(BaseModel):
    weight: Optional[Decimal] = Field(None, gt=0, le=300)
    blood_pressure_systolic: Optional[int] = Field(None, ge=60, le=300)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=200)
    pulse: Optional[int] = Field(None, ge=30, le=220)
    notes: Optional[str] = None

class HealthMetric(HealthMetricBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class HealthTrend(BaseModel):
    period: str = Field(..., description="Zeitraum (week, month, year)")
    weight_trend: List[Dict[str, Any]] = Field(default_factory=list, description="Gewichtsverlauf")
    blood_pressure_trend: List[Dict[str, Any]] = Field(default_factory=list, description="Blutdruckverlauf")
    pulse_trend: List[Dict[str, Any]] = Field(default_factory=list, description="Pulsverlauf")
    
    class Config:
        from_attributes = True