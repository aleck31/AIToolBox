# Copyright iX.
# SPDX-License-Identifier: MIT-0
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from pytz import timezone


# Get the root directory of the application
ROOT_DIR = os.path.dirname(os.path.abspath(__name__))

def setup_logger(log_level=logging.INFO):
    # Configure unified logging
    logger = logging.getLogger('app_logger')
    logger.setLevel(log_level)

    # Create a FileHandler for app.log
    # file_handler = logging.FileHandler(os.path.join(ROOT_DIR, 'app.log'))
    file_handler = RotatingFileHandler(
        os.path.join(ROOT_DIR, 'app.log'),
        maxBytes=1024*1024,
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)  # Set the file log handler level to DEBUG

    # Create another handler to output to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Set the console log handler level to WARNING

    # Create a custom formatter with UTC+8 timezone
    class TzFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, tz=timezone('Asia/Shanghai'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')

    # Set the formatter for the handler
    formatter = TzFormatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Create logger instance
logger = setup_logger()
    