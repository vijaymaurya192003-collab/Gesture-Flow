# REST API Specification
## Gesture Flow Backend API (FastAPI)

Base Path: `/api/v1`

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

## 2. Gesture Mapping Endpoints

### 2.1 Get Mappings
- **GET** `/mappings`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** `200 OK`: Array of active mapping objects.

### 2.2 Upsert Mapping
- **POST** `/mappings` or **PUT** `/mappings/{gesture}`
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
    "vibration_feedback": true
  }
  ```

### 3.2 Get / Update Calibration Profile
- **GET** `/calibration` | **PUT** `/calibration`
- **Payload**:
  ```json
  {
    "pinch_threshold": 0.35,
    "hand_size_baseline": 0.35,
    "min_confidence_floor": 0.65
  }
  ```

---

## 4. Telemetry & Stats

- **POST** `/stats`: Record anonymous usage counters (durations, gesture counts, average FPS).
- **GET** `/stats/summary`: Aggregate usage statistics.
- **GET** `/health`: System health and database connectivity status.

