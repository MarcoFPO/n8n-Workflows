from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from ..database.models import User, UserSettings
from ..models.schemas import UserCreate, UserUpdate, UserSettingsCreate, UserSettingsUpdate

class UserService:
    
    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Create new user"""
        db_user = User(
            name=user.name,
            email=user.email,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def update_user(db: Session, user_id: int, user: UserUpdate) -> User:
        """Update user"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            update_data = user.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_user, field, value)
            db_user.updated_at = datetime.now()
            db.commit()
            db.refresh(db_user)
        return db_user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Delete user"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db.delete(db_user)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_user_settings(db: Session, user_id: int) -> Optional[UserSettings]:
        """Get user settings"""
        return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    @staticmethod
    def create_user_settings(db: Session, user_id: int, settings: UserSettingsCreate) -> UserSettings:
        """Create user settings"""
        db_settings = UserSettings(
            user_id=user_id,
            daily_calorie_goal=settings.daily_calorie_goal,
            weight_goal=settings.weight_goal,
            activity_level=settings.activity_level,
            dietary_restrictions=settings.dietary_restrictions,
            updated_at=datetime.now()
        )
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        return db_settings
    
    @staticmethod
    def update_user_settings(db: Session, user_id: int, settings: UserSettingsUpdate) -> UserSettings:
        """Update user settings"""
        db_settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if db_settings:
            update_data = settings.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_settings, field, value)
            db_settings.updated_at = datetime.now()
            db.commit()
            db.refresh(db_settings)
        return db_settings