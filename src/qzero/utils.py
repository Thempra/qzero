"""
QZero Utilities Module

Common utilities used across QZero.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
import time


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for QZero.

    Args:
        verbose: Enable debug mode
    """
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def setup_file_logging(log_file: Path, verbose: bool = False) -> None:
    """
    Configure logging with file output.

    Args:
        log_file: Path to log file
        verbose: Enable debug mode
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """
    Format timestamp for display.

    Args:
        timestamp: Datetime object, defaults to now

    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now()

    return timestamp.strftime('%Y-%m-%d %H:%M:%S')


def format_iso_timestamp(timestamp: Optional[datetime] = None) -> str:
    """
    Format timestamp in ISO format.

    Args:
        timestamp: Datetime object, defaults to now

    Returns:
        ISO format timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now()

    return timestamp.isoformat()


def create_timestamped_filename(prefix: str, extension: str = "json") -> str:
    """
    Create a timestamped filename.

    Args:
        prefix: Filename prefix
        extension: File extension (without dot)

    Returns:
        Formatted filename
    """
    timestamp = format_timestamp().replace(" ", "_").replace(":", "-")
    return f"{prefix}_{timestamp}.{extension}"


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, create if not.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(data: Any, file_path: Path, indent: int = 2) -> None:
    """
    Save data to JSON file.

    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation
    """
    ensure_directory(file_path.parent)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_json(file_path: Path) -> Any:
    """
    Load data from JSON file.

    Args:
        file_path: Input file path

    Returns:
        Loaded data
    """
    with open(file_path, 'r') as f:
        return json.load(f)


def create_report_dict(
    task_name: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized report dictionary.

    Args:
        task_name: Name of the task
        status: Status (success, failure, warning)
        details: Additional details
        error: Error message if failed

    Returns:
        Report dictionary
    """
    report = {
        "task": task_name,
        "status": status,
        "timestamp": format_iso_timestamp(),
        "details": details or {}
    }

    if error:
        report["error"] = error

    return report


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string to seconds.

    Args:
        duration_str: Duration string (e.g., "1h", "30m", "60s")

    Returns:
        Duration in seconds
    """
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }

    if not duration_str:
        return 0

    match = re.match(r'^(\d+)([smhd])?$', duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value = int(match.group(1))
    unit = match.group(2) or 's'
    return value * units.get(unit, 1)


# Lazy import for regex
import re