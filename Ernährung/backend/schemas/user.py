from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name des Benutzers")

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name des Benutzers")

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserSettingBase(BaseModel):
    daily_calorie_goal: int = Field(..., gt=0, le=5000, description="Tägliches Kalorienziel")
    weight_goal: Optional[Decimal] = Field(None, gt=0, le=300, description="Gewichtsziel in kg")
    activity_level: str = Field("moderate", description="Aktivitätslevel")
    dietary_restrictions: List[str] = Field(default_factory=list, description="Ernährungseinschränkungen")

class UserSettingCreate(UserSettingBase):
    pass

class UserSettingUpdate(BaseModel):
    daily_calorie_goal: Optional[int] = Field(None, gt=0, le=5000)
    weight_goal: Optional[Decimal] = Field(None, gt=0, le=300)
    activity_level: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None

class UserSetting(UserSettingBase):
    user_id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True