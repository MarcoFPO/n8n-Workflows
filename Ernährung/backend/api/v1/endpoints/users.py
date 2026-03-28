from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.database import User as UserModel, UserSetting as UserSettingModel
from schemas.user import User, UserCreate, UserUpdate, UserSetting, UserSettingCreate, UserSettingUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[User])
async def get_users(db: Session = Depends(get_db)):
    """Liste aller Benutzer abrufen."""
    try:
        users = db.query(UserModel).all()
        return users
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Benutzerdetails abrufen."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Neuen Benutzer erstellen."""
    try:
        db_user = UserModel(**user.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{user_id}", response_model=User)
async def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    """Benutzer aktualisieren."""
    try:
        db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        update_data = user.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{user_id}/settings", response_model=UserSetting)
async def get_user_settings(user_id: int, db: Session = Depends(get_db)):
    """Benutzereinstellungen abrufen."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        settings = db.query(UserSettingModel).filter(UserSettingModel.user_id == user_id).first()
        if not settings:
            raise HTTPException(status_code=404, detail="User settings not found")
        
        return settings
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user settings for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{user_id}/settings", response_model=UserSetting)
async def update_user_settings(user_id: int, settings: UserSettingUpdate, db: Session = Depends(get_db)):
    """Benutzereinstellungen aktualisieren."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_settings = db.query(UserSettingModel).filter(UserSettingModel.user_id == user_id).first()
        if not db_settings:
            # Erstelle neue Einstellungen falls nicht vorhanden
            settings_data = settings.dict(exclude_unset=True)
            settings_data['user_id'] = user_id
            db_settings = UserSettingModel(**settings_data)
            db.add(db_settings)
        else:
            # Aktualisiere existierende Einstellungen
            update_data = settings.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_settings, field, value)
        
        db.commit()
        db.refresh(db_settings)
        return db_settings
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user settings for {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{user_id}/settings", response_model=UserSetting, status_code=status.HTTP_201_CREATED)
async def create_user_settings(user_id: int, settings: UserSettingCreate, db: Session = Depends(get_db)):
    """Benutzereinstellungen erstellen."""
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        existing_settings = db.query(UserSettingModel).filter(UserSettingModel.user_id == user_id).first()
        if existing_settings:
            raise HTTPException(status_code=400, detail="User settings already exist")
        
        settings_data = settings.dict()
        settings_data['user_id'] = user_id
        db_settings = UserSettingModel(**settings_data)
        
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        return db_settings
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user settings for {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")