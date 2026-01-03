"""
Debug Logging Utilities

Provides conditional logging based on DEBUG environment variable.
"""

import logging
from functools import wraps
from datetime import datetime
from config.settings import settings


_debug_logger = logging.getLogger("debug")
_debug_handler = logging.StreamHandler()
_debug_handler.setFormatter(
    logging.Formatter('[%(asctime)s] [DEBUG] %(message)s', datefmt='%H:%M:%S')
)
_debug_logger.addHandler(_debug_handler)
_debug_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.WARNING)


def log_debug(message: str, *args, prefix: str = "") -> None:
    """
    Log a debug message only if DEBUG is set to True in settings.
    
    Args:
        message: The message to log
        *args: Additional arguments to format into the message
        prefix: Optional prefix for categorizing logs (e.g., "ITINERARY", "YOUTUBE")
    """
    if not settings.DEBUG:
        return
    
    if prefix:
        formatted_message = f"[{prefix}] {message}"
    else:
        formatted_message = message
    
    if args:
        formatted_message = formatted_message % args
    
    _debug_logger.debug(formatted_message)


def log_step(step_name: str, step_number: int = None, total_steps: int = None) -> None:
    """
    Log a process step for tracking progress.
    
    Args:
        step_name: Name/description of the current step
        step_number: Current step number (optional)
        total_steps: Total number of steps (optional)
    """
    if not settings.DEBUG:
        return
    
    if step_number is not None and total_steps is not None:
        progress = f"[{step_number}/{total_steps}]"
    elif step_number is not None:
        progress = f"[Step {step_number}]"
    else:
        progress = "[STEP]"
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {progress} {step_name}")


def log_success(message: str, prefix: str = "") -> None:
    """
    Log a success message with a checkmark.
    
    Args:
        message: The success message
        prefix: Optional prefix for categorizing logs
    """
    if not settings.DEBUG:
        return
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix_str = f"[{prefix}] " if prefix else ""
    print(f"[{timestamp}] {prefix_str}✓ {message}")


def log_error(message: str, prefix: str = "") -> None:
    """
    Log an error message with an X mark.
    
    Args:
        message: The error message
        prefix: Optional prefix for categorizing logs
    """
    if not settings.DEBUG:
        return
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix_str = f"[{prefix}] " if prefix else ""
    print(f"[{timestamp}] {prefix_str}✗ {message}")


def log_progress(current: int, total: int, message: str = "", prefix: str = "") -> None:
    """
    Log a progress indicator.
    
    Args:
        current: Current progress value
        total: Total progress value
        message: Optional message to include
        prefix: Optional prefix for categorizing logs
    """
    if not settings.DEBUG:
        return
    
    percentage = (current / total * 100) if total > 0 else 0
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix_str = f"[{prefix}] " if prefix else ""
    progress_bar = f"[{'=' * int(percentage // 5)}{' ' * (20 - int(percentage // 5))}]"
    msg_str = f" - {message}" if message else ""
    print(f"[{timestamp}] {prefix_str}{progress_bar} {percentage:.0f}%{msg_str}")
