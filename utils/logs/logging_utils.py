"""Logging utility function to use throughout the agents"""
import logging
import os

from pythonjsonlogger import jsonlogger

from utils.logs.log_sanitization import sanitize_dict, sanitize_log_message


class SanitizedJsonFormatter(jsonlogger.JsonFormatter):
    def process_log_record(self, log_record):
        # Sanitize the log message
        log_record['message'] = sanitize_log_message(log_record['message'])

        # Sanitize extra fields
        if 'extra' in log_record:
            log_record['extra'] = sanitize_dict(log_record['extra'])

        # Remove taskName if present
        log_record.pop('taskName', None)

        return super().process_log_record(log_record)

def setup_logger():
    """
    Set up and configure the logger.

    This function sets up a logger with a specific format and log level.
    The log level is determined by the LOG_LEVEL environment variable,
    defaulting to INFO if not set.

    Logging Levels:
    - DEBUG: Detailed information, typically of interest only when diagnosing problems.
    - INFO: Confirmation that things are working as expected.
    - WARNING: An indication that something unexpected happened, or indicative of some problem in the near future.
    - ERROR: Due to a more serious problem, the software has not been able to perform some function.
    - CRITICAL: A serious error, indicating that the program itself may be unable to continue running.

    Returns:
        logging.Logger: Configured logger object.
    """
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()

    # Set root logger to WARNING
    logging.basicConfig(level=logging.ERROR)

    logger = logging.getLogger('Genpod')
    logger.setLevel(log_level)

    handler = logging.StreamHandler()
    formatter = SanitizedJsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Set specific loggers for external libraries to a higher level
    logging.getLogger('langchain').setLevel(logging.ERROR)
    logging.getLogger('openai').setLevel(logging.ERROR)

    logger.propagate = False

    return logger

# Create a logger instance
logger = setup_logger()

# # Usage examples with comments about different logging levels:

# # DEBUG: Detailed information, typically of interest only when diagnosing problems.
# logger.debug("This is a debug message with sensitive data: api_key=ABC123")

# # INFO: Confirmation that things are working as expected.
# logger.info("Task completed successfully")

# # WARNING: An indication that something unexpected happened, or indicative of some problem in the near future.
# logger.warning("Resource usage is high, consider optimizing")

# # ERROR: Due to a more serious problem, the software has not been able to perform some function.
# logger.error("Failed to connect to database")

# # CRITICAL: A serious error, indicating that the program itself may be unable to continue running.
# logger.critical("System is shutting down due to critical failure")