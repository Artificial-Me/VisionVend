"""
logging_config.py - Comprehensive logging configuration for VisionVend

This module provides a centralized logging configuration with:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- JSON and standard formatters for better log analysis
- Console and rotating file handlers
- Component-specific loggers (server, hardware, vision, payments)
- Performance monitoring and error tracking utilities
"""

import logging
import logging.handlers
import os
import time
import json
import traceback
import socket
import platform
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Dict, Any, Callable, Optional, Union

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Constants
DEFAULT_LOG_LEVEL = logging.INFO
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5
HOST_NAME = socket.gethostname()
PLATFORM_INFO = platform.platform()

# Custom JSON formatter
class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON objects"""
    
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "host": HOST_NAME,
            "platform": PLATFORM_INFO
        }
        
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add extra fields if available
        if hasattr(record, "extra"):
            log_record.update(record.extra)
            
        return json.dumps(log_record)


# Performance monitoring context manager and decorator
class PerformanceMonitor:
    """Context manager and decorator for monitoring execution time"""
    
    def __init__(self, logger, operation_name=None):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_time = time.time() - self.start_time
        if self.operation_name:
            self.logger.info(
                f"Operation '{self.operation_name}' completed in {elapsed_time:.4f} seconds",
                extra={"duration": elapsed_time, "operation": self.operation_name}
            )
        else:
            self.logger.info(
                f"Operation completed in {elapsed_time:.4f} seconds",
                extra={"duration": elapsed_time}
            )
            
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = self.operation_name or func.__name__
            with PerformanceMonitor(self.logger, operation_name):
                return func(*args, **kwargs)
        return wrapper


# Error tracking utility
def log_exception(logger, exc_info=None, extra=None):
    """
    Log an exception with detailed information
    
    Args:
        logger: The logger to use
        exc_info: Exception info tuple (type, value, traceback)
        extra: Additional context to include in the log
    """
    if exc_info is None:
        exc_info = sys.exc_info()
    
    if not extra:
        extra = {}
        
    logger.error(
        f"Exception occurred: {exc_info[1]}",
        exc_info=exc_info,
        extra={"extra": extra}
    )


# Configure handlers
def get_console_handler():
    """Create and return a console handler with colored output"""
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    return console_handler


def get_file_handler(component_name, use_json=False):
    """Create and return a rotating file handler"""
    log_file = LOG_DIR / f"{component_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT
    )
    
    if use_json:
        file_handler.setFormatter(JsonFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
    return file_handler


# Component-specific loggers
def get_logger(component_name, level=DEFAULT_LOG_LEVEL, use_json=True):
    """
    Get a configured logger for a specific component
    
    Args:
        component_name: Name of the component (server, hardware, vision, payments)
        level: Logging level (default: INFO)
        use_json: Whether to use JSON formatting for file logs (default: True)
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(f"visionvend.{component_name}")
    logger.setLevel(level)
    
    # Remove existing handlers if any
    if logger.handlers:
        logger.handlers.clear()
        
    # Add handlers
    logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler(component_name, use_json))
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger


# Pre-configured loggers for main components
server_logger = get_logger("server")
hardware_logger = get_logger("hardware")
vision_logger = get_logger("vision")
payment_logger = get_logger("payment")
inventory_logger = get_logger("inventory")


# Helper function to create a logger with performance monitoring
def get_monitored_logger(component_name, level=DEFAULT_LOG_LEVEL):
    """Get a logger with an attached performance monitor"""
    logger = get_logger(component_name, level)
    logger.performance = PerformanceMonitor(logger)
    return logger


# Function to configure all loggers at once
def configure_logging(log_level=DEFAULT_LOG_LEVEL, log_dir=None):
    """
    Configure all VisionVend loggers at once
    
    Args:
        log_level: Logging level to set for all loggers
        log_dir: Custom directory for log files
    """
    global LOG_DIR
    
    if log_dir:
        LOG_DIR = Path(log_dir)
        LOG_DIR.mkdir(exist_ok=True)
    
    # Set levels for all loggers
    for logger_name in ["server", "hardware", "vision", "payment", "inventory"]:
        logger = logging.getLogger(f"visionvend.{logger_name}")
        logger.setLevel(log_level)


# Import this to ensure exception hooks are set
def setup_exception_hooks():
    """Set up global exception hooks to ensure all unhandled exceptions are logged"""
    import sys
    
    def exception_hook(exc_type, exc_value, exc_traceback):
        # Log the exception
        logger = logging.getLogger("visionvend.uncaught")
        logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        # Call the default exception hook
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Set the exception hook
    sys.excepthook = exception_hook


# Call this function to set up exception hooks
setup_exception_hooks()
