from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database.connection import get_database
from ..database.models import User, UserSettings
from ..models.schemas import (
    User as UserSchema,
    UserCreate,
    UserUpdate,
    UserSettings as UserSettingsSchema,
    UserSettingsCreate,
    UserSettingsUpdate,
    APIResponse
)
from ..services.user_service import UserService

router = APIRouter()

@router.get("/users", response_model=List[UserSchema])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_database)
):
    """Get all users"""
    try:
        users = UserService.get_users(db, skip=skip, limit=limit)
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )

@router.get("/users/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: Session = Depends(get_database)
):
    """Get user by ID"""
    try:
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )

@router.post("/users", response_model=UserSchema)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_database)
):
    """Create new user"""
    try:
        # Check if user with email already exists
        if user.email:
            existing_user = UserService.get_user_by_email(db, user.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
        
        new_user = UserService.create_user(db, user)
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

@router.put("/users/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_database)
):
    """Update user"""
    try:
        existing_user = UserService.get_user_by_id(db, user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        updated_user = UserService.update_user(db, user_id, user)
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

@router.delete("/users/{user_id}", response_model=APIResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_database)
):
    """Delete user"""
    try:
        existing_user = UserService.get_user_by_id(db, user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        UserService.delete_user(db, user_id)
        return APIResponse(
            success=True,
            message="User deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@router.get("/users/{user_id}/settings", response_model=UserSettingsSchema)
async def get_user_settings(
    user_id: int,
    db: Session = Depends(get_database)
):
    """Get user settings"""
    try:
        settings = UserService.get_user_settings(db, user_id)
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )
        return settings
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user settings: {str(e)}"
        )

@router.post("/users/{user_id}/settings", response_model=UserSettingsSchema)
async def create_user_settings(
    user_id: int,
    settings: UserSettingsCreate,
    db: Session = Depends(get_database)
):
    """Create user settings"""
    try:
        # Check if user exists
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if settings already exist
        existing_settings = UserService.get_user_settings(db, user_id)
        if existing_settings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User settings already exist"
            )
        
        new_settings = UserService.create_user_settings(db, user_id, settings)
        return new_settings
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user settings: {str(e)}"
        )

@router.put("/users/{user_id}/settings", response_model=UserSettingsSchema)
async def update_user_settings(
    user_id: int,
    settings: UserSettingsUpdate,
    db: Session = Depends(get_database)
):
    """Update user settings"""
    try:
        existing_settings = UserService.get_user_settings(db, user_id)
        if not existing_settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )
        
        updated_settings = UserService.update_user_settings(db, user_id, settings)
        return updated_settings
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user settings: {str(e)}"
        )