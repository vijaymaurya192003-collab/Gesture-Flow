"""
Abstract interface for video frame sources.
Allows swapping between OpenCV camera, Android Camera2, or synthetic test feeds.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np


class BaseFrameSource(ABC):
    """Abstract frame capture provider."""

    @abstractmethod
    def start(self) -> bool:
        """Start acquiring frames."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop frame acquisition and release resources."""
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Fetch the most recent available frame.
        Returns (success, frame_numpy_bgr).
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if frame source is active."""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """Get current calculated FPS."""
        pass

