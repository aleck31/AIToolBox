# Copyright iX.
# SPDX-License-Identifier: MIT-0
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from pytz import timezone


# Get the root directory of the application
ROOT_DIR = os.path.dirname(os.path.abspath(__name__))
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

def setup_logger(log_level=logging.INFO):
    # Configure unified logging
    logger = logging.getLogger('app_logger')
    logger.setLevel(log_level)

    # Create a FileHandler for app.log
    # This will store INFO, WARNING, ERROR, and CRITICAL level logs
    applog_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, 'app.log'),
        maxBytes=1024*1024,
        backupCount=5
    )
    applog_handler.setLevel(logging.INFO)  # Captures INFO and above (WARNING, ERROR, CRITICAL)

    # Create a separate FileHandler for debug.log
    # This will store DEBUG level logs only
    debug_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, 'debug.log'),
        maxBytes=1024*1024,
        backupCount=5
    )
    debug_handler.setLevel(logging.DEBUG)  
    debug_handler.addFilter(lambda record: record.levelno == logging.DEBUG)  # Only DEBUG messages

    # Create another handler to output to the console
    # This will show WARNING, ERROR, and CRITICAL level logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Shows WARNING and above in console

    # Create a custom formatter with UTC+8 timezone
    class TzFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, tz=timezone('Asia/Shanghai'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')

    # Set the formatter for the handlers
    formatter = TzFormatter('%(asctime)s - %(levelname)s - %(message)s')
    applog_handler.setFormatter(formatter)
    debug_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(applog_handler)
    logger.addHandler(debug_handler)
    logger.addHandler(console_handler)

    return logger


# Create logger instance
logger = setup_logger()
