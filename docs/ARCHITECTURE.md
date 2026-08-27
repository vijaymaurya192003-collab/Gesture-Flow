# System Architecture Documentation
## Gesture Flow — Touchless Android & Desktop HCI System

---

## 1. High-Level Architectural Overview

Gesture Flow is split into two major subsystems:
1. **Local Real-Time HCI Engine (Device-Side)**: Real-time computer vision, One-Euro coordinate smoothing, rule-based geometric gesture classification, state machine debounce, and native Android / Desktop action execution.
2. **Cloud Synchronization & Management (Server-Side)**: FastAPI REST backend on Render, MongoDB Atlas database, and Vercel web management dashboard.

```
+-----------------------------------------------------------------------------------+
|                            MOBILE CLIENT (Kivy UI & Engine)                       |
|                                                                                   |
|  [ScreenManager] -> [Dashboard HUD] [Mappings] [Calibration Wizard] [Settings]    |
|           |                                                                       |
|  [Camera Capture (OpenCV)]  <-- Worker Thread (30 FPS)                            |
|           |                                                                       |
|           v                                                                       |
|  [Hand Detector]            --> 21 3D Normalized Landmarks (MediaPipe / Tasks)    |
|           |                                                                       |
|           v                                                                       |
|  [One-Euro Filter Smoother] --> Dynamic Jitter Deadbands & Velocity Filter       |
|           |                                                                       |
|           v                                                                       |
|  [Gesture Classifier]       --> Rule-Based Geometric Feature Extraction           |
|           |                                                                       |
|           v                                                                       |
|  [State Machine & Debounce] --> IDLE -> TRACKING -> TRIGGERED -> COOLDOWN         |
|           |                                                                       |
|           v                                                                       |
|  [Safe Action Whitelist]    --> ActionRegistry Whitelist Verification             |
|           |                                                                       |
|           v                                                                       |
|  [PyJNIus Bridge]           --> org.gestureflow.GestureAccessibilityService       |
|                                 (dispatchTap, dispatchScroll, Global Actions)     |
|                                                                                   |
|  [Offline SQLite Storage]   <-- Stores Mappings, Profiles, and Sync Queue         |
+------------------------------------------+----------------------------------------+
                                           | HTTPS REST API (JWT Bearer)
                                           v
+-----------------------------------------------------------------------------------+
|                            FASTAPI BACKEND (Render)                               |
|   /api/v1/auth   *   /api/v1/mappings (/gestures)   *   /api/v1/settings          |
+------------------------------------------+----------------------------------------+
                                           | TLS / Motor Driver
                                           v
+-----------------------------------------------------------------------------------+
|                              MONGODB ATLAS CLUSTER                                |
|   users  *  gesture_mappings  *  user_settings  *  calibration_profiles  * stats  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Android Native Accessibility Bridge Architecture

When executing on Android, `android.android.accessibility.AndroidAccessibilityBridge` utilizes `PyJNIus` to communicate with the native Java service:
- **`org.gestureflow.GestureAccessibilityService`**: Java `AccessibilityService` (API 24+) registered in AndroidManifest with `BIND_ACCESSIBILITY_SERVICE` permission.
- **Touch Gesture Injection**: Injects simulated taps and continuous scroll strokes using `GestureDescription.Builder` and `StrokeDescription`.
- **Global Actions**: Triggers system navigation (`GLOBAL_ACTION_BACK`, `GLOBAL_ACTION_HOME`, `GLOBAL_ACTION_RECENTS`) system-wide.
- **User Activation**: Android requires the user to explicitly grant permission in Settings > Accessibility. An in-app status badge and direct settings launcher guide the user.
- **`AudioManager` & `Vibrator`**: Controls media volume and provides discrete haptic vibration feedback.

---

## 3. Computer Vision & Landmark Pipeline

1. **Thread-Safe Capture (`android.camera.opencv_camera`)**: Dedicated worker reads frames into an atomic single-frame buffer with rate limiting.
2. **Landmark Extraction (`android.vision.hand_detector`)**: Detects 21 landmarks locally. On Desktop, uses MediaPipe Hands Lite; on Android, interfaces with native Tasks Vision AAR.
3. **One-Euro Coordinate Smoothing (`android.vision.landmark_smoother`)**:
   Adapts cutoff frequency dynamically based on hand velocity to eliminate jitter at rest while preserving instantaneous responsiveness during rapid swipes.

---

## 4. Gesture Classification & State Machine

```
      +------------+
      |    IDLE    |<-----------------------------------+
      +-----+------+                                    |
            | Hand Detected                             | No Hand
            v                                           |
      +------------+                                    |
      |  TRACKING  |------------------------------------+
      +-----+------+                                    |
            | Conf >= Threshold                         |
            v                                           |
+------------------------+                              |
|   GESTURE_DETECTED     | (Verifying Hold Duration)    |
+-----------+------------+                              |
            | Hold Time >= 80ms                         |
            v                                           |
+------------------------+                              |
|   ACTION_TRIGGERED     |                              |
+-----------+------------+                              |
            | Dispatch Action to Hardware               |
            v                                           |
+------------------------+                              |
|       COOLDOWN         | (Debounce Window 300-600ms) -+
+------------------------+
```

---

## 5. Offline Sync & Conflict Resolution

1. **SQLite Local Database**: Stores mappings, calibration profiles, user settings, and a persistent `sync_queue`.
2. **Retry & Backoff**: Failed network synchronization attempts increment `retry_count` and log `last_error`. After 3 consecutive unrecoverable failures, items transition to `dead_letter` status to avoid head-of-line blocking.
3. **Acknowledgement-Based Deletion**: Items are removed from the sync queue only upon receiving an explicit `2xx` HTTP response from the backend.
4. **Conflict Policy**: Local modifications take precedence on push (Last-Write-Wins), while remote synchronization safely updates unmodified local defaults.
