"""
Logging configuration with rotating file handlers and separate debug logs
"""
import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .config import app_config

def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger with console and rotating file handlers.
    Debug logs are stored separately from regular application logs.
    """
    logger = logging.getLogger(name)
    
    # Determine log level from DEBUG setting
    debug_mode = app_config.server_config['debug']
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler (shows all logs)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    logger.addHandler(console_handler)
    
    # Regular application log file (INFO and above)
    app_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)
    logger.addHandler(app_handler)
    
    # Debug log file (DEBUG level only)
    if debug_mode:
        debug_handler = RotatingFileHandler(
            log_dir / 'debug.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)
        # Only write DEBUG level messages to debug.log
        debug_handler.addFilter(lambda record: record.levelno == logging.DEBUG)
        logger.addHandler(debug_handler)
    
    return logger

# Create logger instance
logger = setup_logger('aibox')
