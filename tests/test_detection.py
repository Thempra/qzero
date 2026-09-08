"""
Tests for real-time detection module.
"""

import pytest

# Conditional import — detection module may not exist yet
pytest.importorskip("qzero.detection.DetectionStream")

import asyncio
import sys
import numpy as np
from pathlib import Path
from dataclasses import asdict

from qzero.detection import (
    DetectionStream,
    DetectionResult,
    StreamConfig,
    NetFlowHandler,
    PCAPHandler,
    LoggerHandler,
    QZeroDetector,
    run_detection_stream,
)
