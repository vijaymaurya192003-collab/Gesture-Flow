# Database Design & MongoDB Atlas Schema
## Gesture Flow Cloud Persistence

---

## 1. Overview & Privacy Principles

Gesture Flow uses **MongoDB Atlas** for user profile, gesture customization, and preference storage.

> [!IMPORTANT]
> **Strict Privacy Policy**:
> - Never store or upload raw camera frames, screenshots, or continuous video streams.
> - Hand processing coordinates remain local on the client device.
> - Telemetry tracks only aggregate gesture event counts and session duration.

---

## 2. Collections & Document Schemas

### 2.1 Collection: `users`
```json
{
  "_id": "8f3b2d1e-...",
  "user_id": "8f3b2d1e-...",
  "email": "student@college.edu",
  "name": "Alex Johnson",
  "password_hash": "$2b$12$...",
  "created_at": "2026-08-25T14:30:00Z"
}
```
- **Indexes**:
  - `email` (Unique)
  - `user_id` (Unique)

### 2.2 Collection: `gesture_mappings`
```json
{
  "_id": ObjectId("..."),
  "user_id": "8f3b2d1e-...",
  "gesture": "PINCH",
  "action": "TAP",
  "sensitivity": 1.2,
  "confidence_threshold": 0.75,
  "cooldown_ms": 400,
  "enabled": true,
  "description": "Tap / Click at pointer position"
}
```
- **Indexes**:
  - Compound Index: `{ user_id: 1, gesture: 1 }` (Unique)

### 2.3 Collection: `user_settings`
```json
{
  "_id": ObjectId("..."),
  "user_id": "8f3b2d1e-...",
  "theme": "Dark",
  "camera_resolution": "640x480",
  "target_fps": 30,
  "pointer_sensitivity": 1.2,
  "scroll_sensitivity": 1.0,
  "show_landmark_overlay": true,
  "vibration_feedback": true
}
```
- **Indexes**:
  - `user_id` (Unique)

### 2.4 Collection: `calibration_profiles`
```json
{
  "_id": ObjectId("..."),
  "user_id": "8f3b2d1e-...",
  "pinch_threshold": 0.35,
  "hand_size_baseline": 0.35,
  "neutral_jitter_std": 0.003,
  "min_confidence_floor": 0.65,
  "calibrated_at": "2026-08-25T14:35:00Z"
}
```

### 2.5 Collection: `stats`
```json
{
  "_id": ObjectId("..."),
  "user_id": "8f3b2d1e-...",
  "session_duration_seconds": 240.5,
  "gesture_counts": {
    "INDEX_POINT": 450,
    "PINCH": 24,
    "SWIPE_DOWN": 12
  },
  "average_fps": 29.8,
  "platform": "Android",
  "timestamp": "2026-08-25T14:40:00Z"
}
```

