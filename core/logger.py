import logging
import logging.handlers
import os
from datetime import datetime

def setup_logging(log_level: str = 'INFO', log_file: str = 'logs/app.log'):
    """Setup application logging"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create specialized loggers
    audit_logger = logging.getLogger('audit')
    audit_handler = logging.handlers.RotatingFileHandler(
        'logs/audit.log', maxBytes=10*1024*1024, backupCount=10
    )
    audit_handler.setFormatter(formatter)
    audit_logger.addHandler(audit_handler)
    
    error_logger = logging.getLogger('error')
    error_handler = logging.handlers.RotatingFileHandler(
        'logs/error.log', maxBytes=10*1024*1024, backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_logger.addHandler(error_handler)
    
    return root_logger