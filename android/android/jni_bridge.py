"""
PyJNIus Java Native Interface (JNI) Bridge
Provides direct access to Android system services via PyJNIus when running on an Android device.
"""
import sys
from typing import Optional


class JNIBridge:
    """JNI Bridge to Android Context, AudioManager, and Vibrator."""

    _is_android = False
    _autoclass = None
    _context = None

    @classmethod
    def is_android(cls) -> bool:
        """Check if currently executing on Android OS."""
        if cls._is_android:
            return True
        try:
            from jnius import autoclass
            cls._autoclass = autoclass
            cls._is_android = True
            return True
        except (ImportError, Exception):
            cls._is_android = False
            return False

    @classmethod
    def get_android_context(cls):
        """Retrieve the active Android Activity Context via PyJNIus."""
        if not cls.is_android():
            return None
        if cls._context is None and cls._autoclass:
            PythonActivity = cls._autoclass('org.kivy.android.PythonActivity')
            cls._context = PythonActivity.mActivity
        return cls._context

    @classmethod
    def adjust_volume(cls, direction: int) -> bool:
        """
        Adjust volume using Android AudioManager.
        direction: +1 for Volume Up, -1 for Volume Down.
        """
        if not cls.is_android():
            return False

        try:
            Context = cls._autoclass('android.content.Context')
            AudioManager = cls._autoclass('android.media.AudioManager')
            context = cls.get_android_context()
            if not context:
                return False

            audio_mgr = context.getSystemService(Context.AUDIO_SERVICE)
            # STREAM_MUSIC = 3
            # ADJUST_RAISE = 1, ADJUST_LOWER = -1
            adj = AudioManager.ADJUST_RAISE if direction > 0 else AudioManager.ADJUST_LOWER
            flag_show_ui = AudioManager.FLAG_SHOW_UI
            audio_mgr.adjustStreamVolume(AudioManager.STREAM_MUSIC, adj, flag_show_ui)
            return True
        except Exception as e:
            print(f"[JNIBridge] Volume adjustment error: {e}")
            return False

    @classmethod
    def vibrate(cls, duration_ms: int = 50) -> bool:
        """Trigger Android haptic vibration feedback."""
        if not cls.is_android():
            return False

        try:
            Context = cls._autoclass('android.content.Context')
            context = cls.get_android_context()
            if not context:
                return False

            vibrator = context.getSystemService(Context.VIBRATOR_SERVICE)
            if vibrator:
                vibrator.vibrate(duration_ms)
                return True
        except Exception as e:
            print(f"[JNIBridge] Vibration error: {e}")
        return False

