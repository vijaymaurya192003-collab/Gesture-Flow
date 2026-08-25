"""
Kivy Texture Bridge
Converts OpenCV BGR image arrays into Kivy Texture buffers for ultra-low latency UI rendering.
"""
from typing import Optional
import cv2
import numpy as np


class KivyTextureBridge:
    """Helper to convert OpenCV numpy arrays to Kivy Texture format."""

    @staticmethod
    def frame_to_kivy_texture(frame_bgr: np.ndarray):
        """
        Converts an OpenCV BGR frame into a Kivy Texture.
        Returns None if Kivy is not available in the current environment.
        """
        try:
            from kivy.graphics.texture import Texture
        except ImportError:
            return None

        if frame_bgr is None or frame_bgr.size == 0:
            return None

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        # Flip vertically because Kivy texture coordinates have origin at bottom-left
        buf = cv2.flip(frame_rgb, 0).tobytes()

        h, w, _ = frame_rgb.shape
        texture = Texture.create(size=(w, h), colorfmt='rgb')
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        return texture

