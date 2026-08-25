# System Architecture Documentation
## Gesture Flow — Touchless Android HCI System

---

## 1. High-Level Architectural Overview

Gesture Flow is split into two major subsystems:
1. **Local Real-Time HCI Engine (Device-Side)**: Real-time computer vision, coordinate smoothing, rule-based gesture classification, state machine debounce, and native Android / Desktop action execution.
2. **Cloud Synchronization & Management (Server-Side)**: FastAPI REST backend on Render, MongoDB Atlas database, and Vercel web management dashboard.

```
+-----------------------------------------------------------------------------------+
|                                  ANDROID DEVICE                                   |
|                                                                                   |
|  [Camera Capture (OpenCV)]  <-- Worker Thread (30 FPS)                            |
|           |                                                                       |
|           v                                                                       |
|  [MediaPipe Hands (Local)]  --> 21 3D Normalized Landmarks                        |
|           |                                                                       |
|           v                                                                       |
|  [Adaptive Smoother (EMA)]  --> Jitter Deadbands & Velocity Filter                |
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
|  [Android Accessibility]    --> dispatchGesture(Tap/Scroll) & Global Actions      |
|                                                                                   |
|  [Offline SQLite Cache]     <-- Stores Mappings, Calibration, & Sync Queue        |
+------------------------------------------+----------------------------------------+
                                           | HTTPS REST API (JWT Bearer)
                                           v
+-----------------------------------------------------------------------------------+
|                            FASTAPI BACKEND (Render)                               |
|   /api/v1/auth   *   /api/v1/mappings   *   /api/v1/settings   *   /api/v1/stats  |
+------------------------------------------+----------------------------------------+
                                           | TLS / Motor Driver
                                           v
+-----------------------------------------------------------------------------------+
|                              MONGODB ATLAS CLUSTER                                |
|   users  *  gesture_mappings  *  user_settings  *  calibration_profiles  * stats  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Computer Vision Pipeline

1. **Thread-Safe Capture (`android.camera.opencv_camera`)**: A dedicated capture worker reads frames from the camera hardware into a single-item buffer with rate-limiting, preventing UI thread blockage.
2. **Landmark Extraction (`android.vision.hand_detector`)**: MediaPipe Hands detects 21 keypoints. The normalized 3D $(x, y, z)$ coordinates are scaled to device resolution.
3. **Adaptive Coordinate Smoothing (`android.vision.landmark_smoother`)**:
   $$\text{smoothed}_t = \text{prev}_{t-1} + \alpha_{\text{dyn}} \cdot (\text{curr}_t - \text{prev}_{t-1})$$
   where $\alpha_{\text{dyn}}$ dynamically scales based on Euclidean displacement velocity, balancing responsiveness with jitter suppression.

---

## 3. Gesture Classification & State Machine

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

## 4. Android Native Bridge Architecture

When executing on Android, `android.android.jni_bridge.JNIBridge` utilizes `PyJNIus` to communicate with the Android OS:
- **`AccessibilityService`**: Injects simulated touch down/move/up events using `GestureDescription.Builder` for tap and scroll gestures.
- **Global Actions**: Performs hardware navigation (`GLOBAL_ACTION_BACK`, `GLOBAL_ACTION_HOME`, `GLOBAL_ACTION_RECENTS`) system-wide.
- **`AudioManager`**: Adjusts hardware volume (`STREAM_MUSIC`) via `ADJUST_RAISE` / `ADJUST_LOWER`.
- **`Vibrator`**: Provides haptic tactile feedback upon discrete action confirmation.

