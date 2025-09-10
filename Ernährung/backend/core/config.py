import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = "postgresql://ernaehrung_user:secure_password@localhost/ernaehrung_app"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "ernaehrung_app"
    DATABASE_USER: str = "ernaehrung_user"
    DATABASE_PASSWORD: str = "secure_password"
    
    # External API Keys
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_CREDENTIALS: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # File Upload
    UPLOAD_DIR: str = "/opt/ernaehrungs-app/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Feature Flags
    ENABLE_ML: bool = True
    ENABLE_OCR: bool = True
    ENABLE_ANALYTICS: bool = True
    
    # Development
    DEBUG: bool = False
    RELOAD: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/var/log/ernaehrung-app/app.log"
    
    # ML Configuration
    ML_MODEL_PATH: str = "/opt/ernaehrung-app/models"
    ML_UPDATE_INTERVAL_HOURS: int = 24
    ML_MIN_TRAINING_DATA: int = 50
    
    # OCR Configuration
    OCR_CONFIDENCE_THRESHOLD: float = 0.7
    OCR_TEMP_DIR: str = "/tmp/ernaehrung-ocr"
    
    # Nutrition Database
    ALDI_PRODUCTS_UPDATE_INTERVAL_HOURS: int = 168  # Weekly
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()