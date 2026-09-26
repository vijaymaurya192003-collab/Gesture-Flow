"""
Unit Tests for Hand Calibration Wizard and Profiles
"""
import pytest
from pathlib import Path
from android.models.settings_models import CalibrationProfileModel
from android.sync.local_storage import LocalStorageManager
from android.gestures.gesture_classifier import GestureClassifier


def test_calibration_profile_defaults():
    """Verify default biometric calibration baseline parameters."""
    profile = CalibrationProfileModel()
    assert 0.04 <= profile.pinch_threshold <= 0.50
    assert profile.hand_size_baseline > 0.20
    assert profile.neutral_jitter_std > 0


def test_calibration_persistence_and_classifier_wiring(tmp_path: Path):
    """Test saving calibrated profile and updating classifier thresholds."""
    test_db = tmp_path / "test_calib.db"
    storage = LocalStorageManager(db_path=test_db)
    classifier = GestureClassifier()

    custom_profile = CalibrationProfileModel(
        profile_id="default",
        pinch_threshold=0.048,
        hand_size_baseline=0.360,
        neutral_jitter_std=0.0025,
        min_confidence_floor=0.65
    )

    storage.save_calibration(custom_profile)
    loaded = storage.load_calibration()

    assert loaded.pinch_threshold == 0.048
    assert loaded.hand_size_baseline == 0.360

    # Wire to classifier
    classifier.set_pinch_threshold(loaded.pinch_threshold)
    assert classifier.pinch_threshold == 0.048

