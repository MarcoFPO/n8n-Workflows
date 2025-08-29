#!/usr/bin/env python3
"""
Logging Configuration - Minimal Implementation
Issue #65 Integration-Fix
"""

import logging
from typing import Dict, Any


def setup_logging(service_name: str = "service", level: str = "INFO") -> None:
    """Setup Standard Logging"""
    
    # Configure standard logging only (fallback)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=f"%(asctime)s [{service_name}] [%(levelname)s] %(name)s: %(message)s"
    )


class LoggerMixin:
    """Logger Mixin für Service Classes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def log_info(self, message: str, **kwargs):
        """Log Info"""
        self.logger.info(message, **kwargs)
    
    def log_error(self, message: str, error: Exception = None, **kwargs):
        """Log Error"""
        if error:
            kwargs["error"] = str(error)
        self.logger.error(message, **kwargs)
    
    def log_debug(self, message: str, **kwargs):
        """Log Debug"""
        self.logger.debug(message, **kwargs)