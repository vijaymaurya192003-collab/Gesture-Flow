# REST API Specification
## Gesture Flow Backend API (FastAPI)

Base Paths Supported: `/`, `/api`, `/api/v1`

---

## 1. Authentication Endpoints

### 1.1 Register User
- **POST** `/auth/register`
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "name": "Alex Johnson",
    "password": "securePassword123"
  }
  ```
- **Response** `201 Created`:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "user_id": "8f3b2d1e-...",
      "email": "user@example.com",
      "name": "Alex Johnson",
      "created_at": "2026-08-25T14:30:00Z"
    }
  }
  ```

### 1.2 Login
- **POST** `/auth/login`
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "securePassword123"
  }
  ```
- **Response** `200 OK`: Returns JWT `access_token` and user profile.

### 1.3 Get Current User Profile
- **GET** `/auth/me`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** `200 OK`: Returns current authenticated user object.

---

## 2. Gesture Mapping Endpoints (Parity on `/mappings` & `/gestures`)

### 2.1 Get Mappings
- **GET** `/mappings` or **GET** `/gestures`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** `200 OK`: Array of active mapping objects.

### 2.2 Create or Upsert Mapping
- **POST** `/mappings` or **POST** `/gestures`
- **PUT** `/mappings/{gesture}` or **PUT** `/gestures/{gesture}`
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
  ```json
  {
    "gesture": "PINCH",
    "action": "TAP",
    "sensitivity": 1.2,
    "confidence_threshold": 0.75,
    "cooldown_ms": 400,
    "enabled": true,
    "description": "Custom Tap Action"
  }
  ```
- **Response** `200 OK` / `201 Created`

### 2.3 Delete / Reset Mapping
- **DELETE** `/mappings/{gesture}` or **DELETE** `/gestures/{gesture}`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** `204 No Content`

---

## 3. Settings & Calibration Endpoints

### 3.1 Get / Update Settings
- **GET** `/settings` | **PUT** `/settings`
- **Payload**:
  ```json
  {
    "theme": "Dark",
    "camera_resolution": "640x480",
    "target_fps": 30,
    "pointer_sensitivity": 1.2,
    "scroll_sensitivity": 1.0,
    "vibration_feedback": true,
    "show_landmark_overlay": true
  }
  ```

### 3.2 Get / Update Calibration Profile
- **GET** `/calibration` | **PUT** `/calibration`
- **Payload**:
  ```json
  {
    "pinch_threshold": 0.052,
    "hand_size_baseline": 0.35,
    "neutral_jitter_std": 0.0028,
    "min_confidence_floor": 0.65
  }
  ```

---

## 4. Telemetry & Stats

- **POST** `/stats`: Record session metrics (durations, gesture counts, FPS).
- **GET** `/stats/summary`: Aggregate telemetry.
- **GET** `/health`: System health and database connectivity status.
