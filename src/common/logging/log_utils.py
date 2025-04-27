"""
Logging utility functions for the Watsonx IPG Testing project.

This module provides functions for setting up and configuring logging throughout the application.
"""

import os
import sys
import logging
import logging.handlers
import yaml
from datetime import datetime
from typing import Dict, Optional, Union, List, Tuple, Any
from pathlib import Path


def setup_logger(
    logger_name: str,
    log_file: Optional[str] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    propagate: bool = False,
    rotation: str = 'size',
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    date_format: str = '%Y-%m-%d %H:%M:%S'
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.
    
    Args:
        logger_name: Name of the logger
        log_file: Path to the log file (None for console-only logging)
        console_level: Logging level for console output
        file_level: Logging level for file output
        propagate: Whether to propagate logs to parent loggers
        rotation: Log rotation strategy ('size' or 'time')
        max_bytes: Maximum size of each log file for size-based rotation
        backup_count: Number of backup files to keep
        log_format: Format string for log messages
        date_format: Format string for timestamps
        
    Returns:
        Configured logger instance
    """
    # Get or create logger
    logger = logging.getLogger(logger_name)
    
    # Set propagation
    logger.propagate = propagate
    
    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Set the level to the lowest level that will be used
    logger.setLevel(min(console_level, file_level if log_file else logging.CRITICAL))
    
    # Create formatter
    formatter = logging.Formatter(log_format, date_format)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Setup file handler if log_file is specified
    if log_file:
        # Ensure the directory exists
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Configure rotation
        if rotation.lower() == 'time':
            # Time-based rotation (at midnight)
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file, when='midnight', interval=1, backupCount=backup_count
            )
        else:
            # Size-based rotation (default)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
        
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_logger_from_config(
    config_file: str,
    logger_name: Optional[str] = None,
    default_level: int = logging.INFO
) -> Union[logging.Logger, Dict[str, logging.Logger]]:
    """
    Set up logging configuration from a YAML config file.
    
    Args:
        config_file: Path to the YAML config file
        logger_name: Specific logger to retrieve (None for all loggers)
        default_level: Default logging level if config file is missing
        
    Returns:
        Single logger if logger_name is specified, otherwise dictionary of loggers
    """
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Configure logging system using dictConfig
            logging.config.dictConfig(config)
            
            # Return the specific logger or all loggers
            if logger_name:
                return logging.getLogger(logger_name)
            else:
                # Create a dictionary of all configured loggers
                loggers = {}
                for name in config.get('loggers', {}).keys():
                    loggers[name] = logging.getLogger(name)
                return loggers
                
        except Exception as e:
            # Fall back to basic configuration if there's an error
            print(f"Error loading logging configuration: {e}")
            logging.basicConfig(level=default_level)
            return logging.getLogger(logger_name) if logger_name else {'root': logging.getLogger()}
    else:
        # Fall back to basic configuration if the file doesn't exist
        logging.basicConfig(level=default_level)
        return logging.getLogger(logger_name) if logger_name else {'root': logging.getLogger()}


def get_log_file_path(
    app_name: str,
    log_dir: Optional[str] = None,
    filename_pattern: str = '{app_name}_{date}.log'
) -> str:
    """
    Generate a log file path with date-based naming.
    
    Args:
        app_name: Name of the application
        log_dir: Directory to store log files (defaults to ./logs)
        filename_pattern: Pattern for log filenames
        
    Returns:
        Full path to the log file
    """
    if log_dir is None:
        # Default to logs directory in current working directory
        log_dir = os.path.join(os.getcwd(), 'logs')
    
    # Ensure the directory exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Generate the filename using the pattern
    date_str = datetime.now().strftime('%Y%m%d')
    filename = filename_pattern.format(app_name=app_name, date=date_str)
    
    return os.path.join(log_dir, filename)


def create_default_config_file(
    output_path: str,
    loggers: List[str] = ['root', 'app', 'integrations', 'execution'],
    default_level: str = 'INFO'
) -> str:
    """
    Create a default logging configuration YAML file.
    
    Args:
        output_path: Path to save the configuration file
        loggers: List of logger names to configure
        default_level: Default logging level
        
    Returns:
        Path to the created configuration file
    """
    # Define default configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': default_level,
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': './logs/app.log',
                'maxBytes': 10485760,  # 10 MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': './logs/error.log',
                'maxBytes': 10485760,  # 10 MB
                'backupCount': 5,
                'encoding': 'utf8'
            }
        },
        'loggers': {},
        'root': {
            'level': default_level,
            'handlers': ['console', 'file', 'error_file'],
        }
    }
    
    # Configure specified loggers
    for logger_name in loggers:
        if logger_name != 'root':
            config['loggers'][logger_name] = {
                'level': default_level,
                'handlers': ['console', 'file'],
                'propagate': False
            }
    
    # Create the directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Write the configuration to file
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return output_path


def add_sensitive_filter(logger: logging.Logger, sensitive_patterns: List[str]) -> logging.Logger:
    """
    Add a filter to mask sensitive information in log messages.
    
    Args:
        logger: Logger instance to add the filter to
        sensitive_patterns: List of patterns to mask (e.g. ['password=', 'api_key='])
        
    Returns:
        Logger instance with the filter added
    """
    class SensitiveInfoFilter(logging.Filter):
        def __init__(self, patterns):
            super().__init__()
            self.patterns = patterns
        
        def filter(self, record):
            if isinstance(record.msg, str):
                msg = record.msg
                for pattern in self.patterns:
                    if pattern in msg:
                        # Find the pattern and replace what follows it until a space or end of string
                        parts = msg.split(pattern)
                        for i in range(1, len(parts)):
                            value_end = parts[i].find(' ')
                            if value_end == -1:  # No space found, mask until end of string
                                parts[i] = '********' + parts[i][len(parts[i]):]
                            else:
                                parts[i] = '********' + parts[i][value_end:]
                        msg = pattern.join(parts)
                record.msg = msg
            return True
    
    # Add the filter to all handlers
    sensitive_filter = SensitiveInfoFilter(sensitive_patterns)
    for handler in logger.handlers:
        handler.addFilter(sensitive_filter)
    
    return logger


def get_all_loggers() -> Dict[str, logging.Logger]:
    """
    Get a dictionary of all existing loggers.
    
    Returns:
        Dictionary mapping logger names to logger instances
    """
    return {name: logging.getLogger(name) for name in logging.root.manager.loggerDict}


def set_log_level_for_all(level: int) -> None:
    """
    Set the log level for all existing loggers.
    
    Args:
        level: Logging level to set (e.g. logging.INFO, logging.DEBUG)
    """
    # Set root logger level
    logging.getLogger().setLevel(level)
    
    # Set level for all other loggers
    for logger in logging.root.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.setLevel(level)


def create_module_logger(module_name: str) -> logging.Logger:
    """
    Create a logger named after the module it's used in.
    
    Args:
        module_name: Name of the module (usually __name__)
        
    Returns:
        Logger instance for the module
    """
    return logging.getLogger(module_name)


def capture_exceptions(logger: logging.Logger) -> callable:
    """
    Decorator to capture and log exceptions.
    
    Args:
        logger: Logger instance to use
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator


class LoggingContext:
    """
    Context manager for temporarily changing log level.
    
    Example:
        with LoggingContext(logger, logging.DEBUG):
            # Log at DEBUG level within this block
            logger.debug("Detailed debug info")
    """
    
    def __init__(self, logger: logging.Logger, level: int):
        """
        Initialize the context manager.
        
        Args:
            logger: Logger instance
            level: Temporary logging level
        """
        self.logger = logger
        self.level = level
        self.old_level = logger.level
    
    def __enter__(self):
        """Set the temporary log level."""
        self.logger.setLevel(self.level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the original log level."""
        self.logger.setLevel(self.old_level)


class LazyLogging:
    """
    Utility class for deferred formatting of log messages.
    
    This helps avoid expensive string operations when the log level would
    filter the message anyway.
    
    Example:
        logger.debug(LazyLogging(lambda: f"Calculated result: {expensive_calculation()}"))
    """
    
    def __init__(self, func):
        """
        Initialize with a function that returns the log message.
        
        Args:
            func: Function that returns the log message string
        """
        self.func = func
    
    def __str__(self):
        """Call the function and return its result when the message is logged."""
        return str(self.func())


# Example usage for this module
if __name__ == "__main__":
    # Example 1: Basic logger setup
    logger = setup_logger(
        logger_name="example",
        log_file="./logs/example.log",
        console_level=logging.INFO,
        file_level=logging.DEBUG
    )
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Example 2: Creating a default config file
    config_path = create_default_config_file("./logs/logging_config.yaml")
    print(f"Created default config file at: {config_path}")
    
    # Example 3: Using sensitive info filter
    filtered_logger = add_sensitive_filter(logger, ["password=", "api_key=", "secret="])
    filtered_logger.info("User authenticated with password=12345 and api_key=abcdef")
    
    # Example 4: Using the context manager
    logger.info("Normal info message")
    with LoggingContext(logger, logging.DEBUG):
        logger.debug("This debug message will be shown")
    logger.debug("This debug message won't be shown if level is INFO")
    
    # Example 5: Using the lazy logging feature
    def expensive_calculation():
        # Simulate an expensive operation
        import time
        time.sleep(1)
        return "Expensive result"
    
    logger.debug(LazyLogging(lambda: f"Result: {expensive_calculation()}"))