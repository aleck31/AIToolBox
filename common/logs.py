# decorators.py
import logging
import os
from datetime import datetime
from pytz import timezone


# Get the root directory of the application
ROOT_DIR = os.path.dirname(os.path.abspath(__name__))


# Configure unified logging
logger = logging.getLogger('app_logger')
logger.setLevel(logging.INFO)
# Create a FileHandler for app.log
log_handler = logging.FileHandler(os.path.join(ROOT_DIR, 'app.log'))

# Create a custom formatter with UTC+8 timezone
class TzFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone('Asia/Shanghai'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')

# Set the formatter for the handler
log_handler.setFormatter(TzFormatter('%(asctime)s - %(levelname)s - %(message)s'))
# Add the handler to the logger
logger.addHandler(log_handler)


def log_info(msg):
    """Log specified information to run.log"""
    print(msg)
    logger.info(msg)


def log_error(msg):
    """Log error with timestamp to erro.log"""
    # print(msg)
    logger.error(msg)
    