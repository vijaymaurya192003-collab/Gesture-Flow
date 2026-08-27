# Software Requirements Specification (SRS)
## Project: Gesture Flow — Touchless Android & Desktop HCI System

---

## 1. Introduction

### 1.1 Purpose
Gesture Flow is a touchless Human-Computer Interaction (HCI) application designed for commodity Android mobile devices and desktop environments. It utilizes the front-facing camera to track 21 hand landmarks in real time and translate discrete and continuous hand gestures into safe operating system actions (taps, cursor navigation, page scrolling, system back/home/recents, and media volume control).

### 1.2 Motivation & Objectives
- **Sterile & Hands-Free Interaction**: Provide reliable device interaction in culinary environments, medical laboratories, automotive setups, or for individuals with temporary or permanent motor impairments.
- **Privacy by Design**: Execute 100% of computer vision and coordinate processing locally on-device without uploading video streams or camera frames.
- **Offline-First Resilience**: Operate seamlessly in low-connectivity or offline settings via local SQLite caching and acknowledgement-based background sync.

---

## 2. Overall Description

### 2.1 System Environment & Architecture
- **Client (Android / Desktop)**: Python 3.11, OpenCV, MediaPipe Hands (Desktop) / Native Tasks Vision (Android), NumPy, Kivy Multi-Screen UI, PyJNIus, SQLite3.
- **Native Android Accessibility Service**: `org.gestureflow.GestureAccessibilityService` extending Android `AccessibilityService` (API 24+) for system-wide gesture injection and global navigation (`BACK`, `HOME`, `RECENTS`).
- **Backend (Render Cloud)**: FastAPI, Pydantic, Uvicorn, Bcrypt, PyJWT.
- **Database (MongoDB Atlas)**: Cloud document store with collections: `users`, `gesture_mappings`, `user_settings`, `calibration_profiles`, `stats` (with in-memory mock fallback strictly for offline development).
- **Frontend (Vercel)**: Responsive HTML5/CSS3/JavaScript web dashboard with 21-joint skeleton simulator.

---

## 3. Functional Requirements

### 3.1 Computer Vision & Hand Landmark Extraction
- **FR-01**: Capture camera frames at a configurable resolution (480p/720p) and target frame rate (15–30 FPS) in a non-blocking background thread.
- **FR-02**: Track 21 3D hand landmarks locally using MediaPipe Hands Lite (Desktop) or native Android Vision.
- **FR-03**: Apply adaptive One-Euro smoothing and deadzone jitter filtering on raw landmarks.

### 3.2 Gesture Classification & State Machine
- **FR-04**: Classify the following MVP gestures deterministically:
  1. `INDEX_POINT` &rarr; Pointer movement
  2. `PINCH` (Thumb Tip & Index Tip proximity) &rarr; Tap / Click
  3. `SWIPE_UP` / `SWIPE_DOWN` &rarr; Vertical Scroll
  4. `SWIPE_LEFT` / `SWIPE_RIGHT` &rarr; Back / Home Navigation
  5. `OPEN_PALM` &rarr; Pause / Resume Gestures
  6. `TWO_FINGERS` (Peace Sign) &rarr; Media Play / Pause
  7. `FIST` &rarr; Emergency Stop Lockout
- **FR-05**: Enforce state transitions: `IDLE -> TRACKING -> GESTURE_DETECTED -> ACTION_TRIGGERED -> COOLDOWN -> TRACKING`.
- **FR-06**: Prevent double-firing via configurable debounce windows (300–600ms) and hold-time confirmation (80ms for pinch).

### 3.3 Safe Action Dispatching & Platform Bridge
- **FR-07**: Restrict all action executions to an explicit whitelist (`ActionRegistry`). Reject any arbitrary command execution.
- **FR-08 (Android AccessibilityService)**: Dispatch gestures globally via `org.gestureflow.GestureAccessibilityService` (`dispatchGesture`) and system navigation (`performGlobalAction`). The user must explicitly enable the service in Android Accessibility Settings; silent activation is disallowed by OS security model.
- **FR-09 (Desktop)**: Provide hardware mouse and keyboard events on PC for rapid HCI prototyping.

### 3.4 Mobile Multi-Screen Interface
- **FR-10 (Dashboard)**: Display live viewfinder texture, HUD overlay, FPS, active gesture, confidence score, action badge, Accessibility Service status indicator, and emergency stop toggle.
- **FR-11 (Mappings)**: View, customize, enable/disable, save, and reset gesture-to-action bindings against safe whitelist.
- **FR-12 (Calibration)**: 3-step wizard measuring hand size baseline, pinch threshold, and jitter deadzone with local and cloud persistence.
- **FR-13 (Settings)**: Tune sensitivity, smoothing factors, haptic vibration, HUD display, launch Android Accessibility Settings, and trigger manual cloud sync.

### 3.5 Cloud Backend & Synchronization
- **FR-14**: Provide secure FastAPI REST endpoints with JWT authentication and route aliases (`/mappings` and `/gestures`).
- **FR-15**: Maintain an offline SQLite queue with retry counters and acknowledgement-based deletion upon confirmed server response.
- **FR-16**: Local-vs-cloud conflict policy: user local edits take priority on push, and cloud mappings update local defaults safely.

---

## 4. Non-Functional Requirements

### 4.1 Security & Privacy
- Zero raw camera footage or video streams shall be transmitted or stored in the cloud.
- Passwords must be hashed using direct Bcrypt with salt factor 12.
- The mobile client must never contain database credentials or administrative secrets.

### 4.2 Usability & Safety
- Provide clear visual HUD feedback (FPS, skeleton overlay, active gesture, confidence %).
- Immediate Emergency Stop button for safety lockout across all platforms.
