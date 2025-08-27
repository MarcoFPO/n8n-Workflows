# Structured Logging Configuration - Fixed for Production
import logging
import sys
import os
from datetime import datetime

def setup_structured_logging(service_name: str, log_level: str = "INFO"):
    """Setup structured logging for service - Production Ready"""
    
    # Create logs directory if needed
    log_dir = "/var/log/aktienanalyse"
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/{service_name}-{datetime.now().strftime('%Y%m%d')}.log"
    except (OSError, PermissionError):
        # Fallback to local directory
        log_file = f"/opt/aktienanalyse-ökosystem/{service_name}.log"
    
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Setup logging configuration
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=f'{{"service": "{service_name}", "timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}}',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode='a')
        ],
        force=True  # Override existing configuration
    )
    
    # Suppress noisy external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logger = logging.getLogger(service_name)
    logger.info(f"Structured logging initialized for {service_name}")
    
    return logger
