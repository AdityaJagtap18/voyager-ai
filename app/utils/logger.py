"""
Simple logging utility for Voyager
"""
import logging
import sys


def setup_logger(name="voyager"):
    """
    Create and configure a logger
    
    Args:
        name: Logger name (default: "voyager")
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Don't add handlers if already exist (avoid duplicates)
    if logger.handlers:
        return logger
    
    # Create console handler (prints to terminal)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # Create formatter (how logs look)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


# Create a default logger that can be imported
logger = setup_logger()

