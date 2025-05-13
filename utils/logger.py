import logging
import os
import re
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler

import yaml
from pythonjsonlogger import jsonlogger


def load_logger_config():
    """
    Loads logger configuration from default values, a YAML configuration file,
    and then overrides with environment variables. Environment variables take
    precedence over the YAML configuration if provided.

    Supported configuration keys and corresponding environment variables:
      - level: Logging level. Supported string values are:
            "CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET"
         Default is "ERROR".
         Environment variable: LOGGER_LEVEL.
      - format: Log output format. Supported values are "json" and "plain".
         Default is "json". Environment variable: LOGGER_FORMAT.
      - dir: Base directory where log folders and files will be stored.
         Default is "output/logs". Environment variable: LOGGER_DIR.
      - console_enabled: Boolean flag indicating whether console logging is enabled.
         Default is False. Environment variable: LOGGER_CONSOLE_ENABLED.
      - max_bytes: Maximum size in bytes for a log file before rotation.
         Default is 25 MB. Environment variable: LOGGER_MAX_BYTES.
      - backup_count: The number of rotated backup files to retain.
         Default is 5. Environment variable: LOGGER_BACKUP_COUNT.
      - default_file_name: The default name for the log file.
         Default is "application.log". Environment variable: LOGGER_DEFAULT_FILE_NAME.
      - logger_name: The name assigned to the logger.
         Default is "Genpod". Environment variable: LOGGER_NAME.
      - clean_enabled: Enables automatic cleaning of old log directories.
         Default is False. Environment variable: LOGGER_CLEAN_ENABLED.
      - clean_count: Maximum number of log directories to keep.
         Default is 2. Environment variable: LOGGER_CLEAN_COUNT.
      - LOGGER_CONFIG_FILE: Path to a YAML config file. Default is "logger_config.yaml".

    Example YAML configuration (logger_config.yaml):

    logger:
      level: DEBUG
      format: plain
      dir: output/logs
      console_enabled: true
      max_bytes: 26214400  # 25 MB
      backup_count: 5
      default_file_name: my_app.log
      logger_name: MyApplicationLogger
      clean_enabled: true
      clean_count: 2

    Returns:
        dict: Logger configuration settings.
    """
    defaults = {
        "level": "ERROR",
        "format": "json",
        "dir": "output/logs",
        "console_enabled": False,
        "max_bytes": 25 * 1024 * 1024,
        "backup_count": 5,
        "default_file_name": "application.log",
        "logger_name": "Genpod",
        "clean_enabled": False,
        "clean_count": 2
    }
    
    # Start with defaults.
    config = defaults.copy()
    
    # Load YAML configuration if available.
    yaml_config_path = os.environ.get("LOGGER_CONFIG_FILE", "logger_config.yaml")
    if os.path.exists(yaml_config_path):
        with open(yaml_config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
        logger_yaml = yaml_config.get("logger", {})
        for key in defaults:
            if key in logger_yaml:
                config[key] = logger_yaml[key]

    # Now override with environment variables if they exist.
    config["level"] = os.environ.get("LOGGER_LEVEL", config["level"]).upper()
    config["format"] = os.environ.get("LOGGER_FORMAT", config["format"])
    config["dir"] = os.environ.get("LOGGER_DIR", config["dir"])
    config["console_enabled"] = os.environ.get("LOGGER_CONSOLE_ENABLED", str(config["console_enabled"])).lower() in ("true", "1", "yes")
    config["max_bytes"] = int(os.environ.get("LOGGER_MAX_BYTES", config["max_bytes"]))
    config["backup_count"] = int(os.environ.get("LOGGER_BACKUP_COUNT", config["backup_count"]))
    config["default_file_name"] = os.environ.get("LOGGER_DEFAULT_FILE_NAME", config["default_file_name"])
    config["logger_name"] = os.environ.get("LOGGER_NAME", config["logger_name"])
    config["clean_enabled"] = os.environ.get("LOGGER_CLEAN_ENABLED", str(config["clean_enabled"])).lower() in ("true", "1", "yes")
    config["clean_count"] = int(os.environ.get("LOGGER_CLEAN_COUNT", config["clean_count"]))
    
    return config

def clean_old_logs(base_dir, keep_count):
    """
    Removes the oldest log directories in the given base directory if the total
    number of directories exceeds keep_count.

    Args:
        base_dir (str): The base directory where log folders are stored.
        keep_count (int): The maximum number of log directories to keep.
    """
    if not os.path.exists(base_dir):
        return
    
    # List only directories.
    dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if len(dirs) <= keep_count:
        return

    # Sort directories by name (timestamps in "YYYY-MM-DD_HH-MM-SS" format sort correctly).
    dirs.sort()
    # Delete the oldest directories.
    for d in dirs[:-keep_count]:
        full_path = os.path.join(base_dir, d)
        try:
            shutil.rmtree(full_path)
        except Exception as e:
            logging.getLogger().error(f"Failed to delete old log directory {full_path}: {e}")

class Logger:
    """
    A singleton logger class that always writes to a file (with rotation) and optionally
    to the console (if enabled via configuration). When the application is triggered, a new
    timestamped folder is created under the base log directory. All log files (including rotated
    backups) for that run will be stored in this folder.

    Configuration can be provided via environment variables or a YAML configuration file. The
    following settings are supported:

      - LOGGER_LEVEL: Logging level. Supported string values are:
            "CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET"
         Default is "ERROR".

      - LOGGER_FORMAT: Log output format. Supported values are "json" and "plain".
         Default is "json".

      - LOGGER_DIR: Base directory for log storage.
         Default is "output/logs".

      - LOGGER_CONSOLE_ENABLED: Enables console logging if set to "true" (or "1"/"yes").
         Default is False.

      - LOGGER_MAX_BYTES: Maximum file size in bytes before rotation.
         Default is 25 MB.

      - LOGGER_BACKUP_COUNT: Number of rotated backup files to retain.
         Default is 5.

      - LOGGER_DEFAULT_FILE_NAME: Default name for the log file (e.g., "application.log").
         Default is "application.log".

      - LOGGER_NAME: Name of the logger.
         Default is "Genpod".

      - LOGGER_CLEAN_ENABLED: Enables automatic cleaning of old log directories.
         Default is False.

      - LOGGER_CLEAN_COUNT: Maximum number of log directories to keep.
         Default is 2.

      - LOGGER_CONFIG_FILE: Path to a YAML config file.
         Default is "logger_config.yaml".

    Propagation:
      The logger's propagate attribute is set to False by default, meaning that log messages will
      NOT be passed to parent loggers. This helps avoid duplicate log messages if multiple loggers are
      configured in an application.

    Usage:
        logger = Logger.get_instance()
        logger.info("Your log message")
    """
    _instance = None

    @staticmethod
    def get_instance():
        """
        Returns the singleton logger instance. Creates and configures one if needed.
        
        Returns:
            logging.Logger: The configured logger instance.
        """
        if Logger._instance:
            return Logger._instance

        config = load_logger_config()

        # Create and configure the logger with the specified name.
        logger = logging.getLogger(config["logger_name"])
        logger.setLevel(config["level"])
        logger.propagate = False  # Do not pass log messages to parent loggers.
        logger.handlers.clear()

        # Choose formatter based on configuration.
        if config["format"] == "json":
            formatter = SanitizedJsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        # Create a timestamped folder under the base log directory.
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = os.path.join(config["dir"], timestamp)
        os.makedirs(log_dir, exist_ok=True)
        
        # Define the log file path using the default file name.
        log_file = os.path.join(log_dir, config["default_file_name"])

        # File handler with rotation: always enabled.
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=config["max_bytes"],
            backupCount=config["backup_count"]
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler: enabled only if configuration is set.
        if config["console_enabled"]:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Clean old log directories if enabled.
        if config.get("clean_enabled"):
            clean_old_logs(config["dir"], config["clean_count"])

        Logger._instance = logger
        return logger

class SanitizedJsonFormatter(jsonlogger.JsonFormatter):
    """
    A custom JSON formatter that sanitizes log records by redacting sensitive information.
    """
    def process_log_record(self, log_record):
        # Sanitize the log message using enhanced rules.
        log_record['message'] = sanitize_log_message(log_record['message'])
        
        # Sanitize extra fields if they exist.
        if 'extra' in log_record:
            log_record['extra'] = sanitize_dict(log_record['extra'])

        # Remove taskName if present
        log_record.pop('taskName', None)

        return super().process_log_record(log_record)

def sanitize_log_message(message: str) -> str:
    """
    Sanitize sensitive data from a log message using enhanced regex rules.
    
    This function redacts:
      - API keys, access tokens, secret keys, passwords, and authorization tokens.
      - URLs.
    
    Args:
        message (str): The original log message.
    
    Returns:
        str: The sanitized log message.
    """
    substitutions = [
        (r'(api[_-]?key\s*[:=]\s*)["\']?([^\s"\']+)["\']?', r'\1<REDACTED>'),
        (r'(access[_-]?token\s*[:=]\s*)["\']?([^\s"\']+)["\']?', r'\1<REDACTED>'),
        (r'(secret(?:_key)?\s*[:=]\s*)["\']?([^\s"\']+)["\']?', r'\1<REDACTED>'),
        (r'(password\s*[:=]\s*)["\']?([^\s"\']+)["\']?', r'\1<REDACTED>'),
        (r'(authorization\s*[:=]\s*)["\']?([^\s"\']+)["\']?', r'\1<REDACTED>'),
        (r'(auth[_-]?token\s*[:=]\s*)["\']?([^\s"\']+)["\']?', r'\1<REDACTED>'),
        (r'https?://[^\s]+', r'<REDACTED_URL>'),
    ]
    for pattern, replacement in substitutions:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    return message

def sanitize_dict(data: dict) -> dict:
    """
    Recursively sanitize all string values in a dictionary or list.
    
    Args:
        data (dict): The dictionary containing potential sensitive data.
    
    Returns:
        dict: A new dictionary with sanitized string values.
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_log_message(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item) if isinstance(item, dict)
                else sanitize_log_message(item) if isinstance(item, str)
                else item for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized

# Export a global logger instance.
logger = Logger.get_instance()
