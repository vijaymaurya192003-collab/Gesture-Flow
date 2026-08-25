# 🖐️ Gesture Flow — Touchless Android & Desktop HCI System

> **Academic Capstone & Real-Time Computer Vision HCI Application**  
> *Touchless Control. Natural Interaction. Privacy by Design.*

---

## 📌 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VERCEL WEB DASHBOARD                              │
│  • Modern Glassmorphic UI with Landing Page, Auth Flow, and Live Canvas     │
│  • Centralized api.js client (reads VITE_API_URL / API_BASE_URL)            │
│  • Automatic JWT Bearer token attachment on all protected requests          │
│  • ZERO MongoDB credentials in frontend JavaScript                          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS REST API
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RENDER FASTAPI BACKEND                               │
│  • Endpoints: /health, /auth/register, /auth/login, /gestures, /settings    │
│  • Strict CORS configured for localhost & production Vercel domains         │
│  • Salted Bcrypt password hashing & JWT token validation                    │
│  • Centralized async MongoDB database manager with ServerApi('1')           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Async MongoDB Driver (ServerApi)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             MONGODB ATLAS                                   │
│  Database: gesture_flow                                                     │
│  Collections: users, gesture_mappings, user_settings,                       │
│               calibration_profiles, stats                                   │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                      LOCAL REAL-TIME CV PIPELINE (OFFLINE)
═══════════════════════════════════════════════════════════════════════════════
[ FRONT CAMERA ] ──▶ [ MediaPipe Lite ] ──▶ [ Geometric Classifier ] ──▶ [ OS Action Dispatcher ]
                               ▲ (100% Local Real-Time CV — ZERO Video Uploads)
                               │
                [ Local SQLite Database (Offline-First Cache) ]
                               │
                 (Background Non-Blocking Sync Daemon)
                               │
                               ▼ [ HTTPS Bearer JWT ]
                 [ FastAPI Cloud Backend (Render) ]
```

---

## 🚀 Key Features

- **⚡ Real-Time Gesture Tracking**: MediaPipe Hands Lite with One-Euro smoothing filter yielding **15.9ms total latency (>60 FPS)**.
- **🖱️ Native Hardware Cursor Control**: Win32 hardware mouse positioning (`ctypes.windll.user32.SetCursorPos`) with effortless 12% margin screen reach.
- **🛡️ Strict Safe Action Whitelist**: Dispatches only authorized OS actions (`POINTER_MOVE`, `TAP`, `SCROLL_UP`, `SCROLL_DOWN`, `BACK`, `HOME`, `VOLUME`, `EMERGENCY_STOP`). Zero arbitrary command execution.
- **📶 100% Offline-First**: Continues recognizing gestures and applying actions when offline using local SQLite caching.
- **🍃 Cloud Synchronization**: Non-blocking background sync with MongoDB Atlas on Render for cross-device profile portability.
- **🔒 Privacy by Design**: Camera frames are processed strictly in RAM locally on-device. Zero video frames are ever uploaded or stored.

---

## ✋ Gesture Library & Controls

| Gesture | Hand Posture | Action | Hardware Target |
| :--- | :--- | :--- | :--- |
| **Index Point** (`INDEX_POINT`) | Extend index finger | **Moves Mouse Cursor** | Win32 / Android Pointer |
| **Pinch** (`PINCH`) | Thumb tip + Index tip touching | **Left Click / Tap** | Hardware Click Event |
| **Swipe Up / Down** | Rapid vertical hand motion | **Scroll Up / Down** | Wheel Event / Touch Injection |
| **Swipe Left / Right** | Rapid horizontal hand motion | **Back / Home** | Alt+Left / Win+D / Global Back |
| **Two Fingers** (`TWO_FINGERS`) | Index + Middle extended (Peace) | **Media Play / Pause** | Audio Manager / PlayPause Key |
| **Open Palm** (`OPEN_PALM`) | All fingers extended | **Pause / Resume Gestures**| Local State Machine Toggle |
| **Closed Fist** (`FIST`) | Clench all fingers | **Emergency Stop Lockout** | Hardware Safety Lockout |

---

## 📁 Repository Structure

```text
Gesture Flow/
├── android/                      # Local CV & Android / Desktop Application
│   ├── actions/                  # Action Dispatcher & Platform Executors (Win32 / Android)
│   ├── camera/                   # OpenCV Camera provider (DirectShow/MSMF/Simulated fallback)
│   ├── config/                   # Constants, Whitelists, and Default Mappings
│   ├── gestures/                 # Classifier, Feature Extractor, State Machine, Confidence
│   ├── models/                   # Pydantic & Dataclass Data Models
│   ├── sync/                     # Local SQLite Cache & Background Cloud Sync Client
│   ├── ui/                       # Kivy Mobile UI views
│   ├── vision/                   # MediaPipe detector, smoother, and overlay renderer
│   └── main.py                   # Desktop & Android application entry point
├── backend/                      # Cloud REST API (FastAPI + MongoDB Atlas)
│   ├── models/                   # Pydantic API request/response schemas
│   ├── routes/                   # Auth (/auth), Gestures (/gestures), Settings, Calibration, Stats
│   ├── config.py                 # Environment configuration loader
│   ├── database.py               # Async PyMongo/Motor DatabaseManager with ServerApi('1')
│   ├── security.py               # Bcrypt password hashing & JWT Bearer token validation
│   └── main.py                   # FastAPI server entry point
├── frontend/                     # Web Management Dashboard (Vercel)
│   ├── index.html                # Landing Page, Auth Modal, and Interactive Dashboard
│   ├── style.css                 # Cosmic Obsidian glassmorphism & responsive styles
│   ├── api.js                    # Centralized, reusable API client module
│   ├── app.js                    # View routing, state management, and 21-joint skeleton simulator
│   └── vercel.json               # Vercel deployment and security header configuration
├── tests/                        # Automated Pytest Suite (36 passing tests)
├── .env.example                  # Environment variable template with placeholders
├── buildozer.spec                # Android APK build packaging specification
├── render.yaml                   # Declarative Render Web Service specification
├── requirements.txt              # Complete project dependencies
├── requirements-backend.txt      # Production backend-only dependencies
├── run_all.py                    # 1-command master launcher shortcut
└── main.py                       # Root launcher
```

---

## ⚙️ Quick Start (Single Command)

To run the entire Gesture Flow stack (Backend on port 8000, Web Dashboard on port 3000, and Desktop CV Camera Viewfinder) in a **single command**:

```powershell
python main.py
```

*(or `python run_all.py`)*

### Individual Launch Commands:
- **Backend Server Only**: `python main.py backend` (Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs))
- **Web Frontend Only**: `python -m http.server 3000 --directory frontend` ([http://localhost:3000](http://localhost:3000))
- **Desktop CV Camera Demo Only**: `python main.py cv`
- **Run Complete Test Suite**: `pytest -v`

---

## 🍃 MongoDB Atlas Configuration

1. In the **MongoDB Atlas Console**, create a cluster and a database named **`gesture_flow`**.
2. Add a Database User with **Read and write to any database** permissions.
3. In **Network Access**, whitelist `0.0.0.0/0` to allow connections from Render and local development.
4. Copy your SRV connection string:
   ```ini
   MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?appName=Gesture-Flow
   MONGODB_DATABASE=gesture_flow
   JWT_SECRET=your_super_secret_jwt_signing_key_min_32_characters
   FRONTEND_URL=https://gestureflow.vercel.app
   ```
5. **Security Notice**: *Never commit real database passwords or secrets to Git. Store them strictly in `.env` (ignored by Git) or Render Environment Settings. If a credential was ever shared publicly, rotate it immediately in the Atlas console.*

---

## 🌐 Cloud Deployment (Vercel & Render)

### 1. Backend on Render
- **Build Command**: `pip install -r requirements-backend.txt`
- **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `MONGODB_URI` = `mongodb+srv://...`
  - `MONGODB_DATABASE` = `gesture_flow`
  - `JWT_SECRET` = *(Secure random 32+ character key)*
  - `CORS_ORIGINS` = `https://gestureflow.vercel.app,https://gesture-flow.vercel.app`

### 2. Frontend on Vercel
- Import the `frontend/` directory.
- **Environment Variable**: `VITE_API_URL` = `https://<your-render-backend>.onrender.com`
- *Never add `MONGODB_URI` or `JWT_SECRET` to Vercel environment variables.*

---

## 🧪 Verification Status & Benchmarks

| Milestone / Component | Implementation Status | Verification Method |
| :--- | :---: | :--- |
| **FastAPI REST API** | `[VERIFIED LOCALLY]` | Tested with `fastapi.testclient` & live Uvicorn (36/36 tests passed) |
| **MongoDB Atlas Connection** | `[VERIFIED LOCALLY]` | Live Atlas ping, collection creation, and CRUD persistence verified |
| **Native Win32 Mouse Control** | `[VERIFIED LOCALLY]` | Sub-millisecond hardware cursor positioning with 12% margin scaling |
| **Web Dashboard & Landing Page**| `[VERIFIED LOCALLY]` | Responsive layout, Auth modal, and 21-joint skeleton canvas verified |
| **Automated Test Suite** | `[VERIFIED LOCALLY]` | **36 / 36 Tests Passed** (`pytest -v` in 26.09s) |
| **Buildozer Android Spec** | `[IMPLEMENTED]` | `buildozer.spec` configured (API 33, permissions, JNI hooks) |
| **Physical Android Hardware** | `[NOT VERIFIED on hardware]`| Requires building `.apk` on Ubuntu/WSL2 and deploying via USB ADB |

---

## 📜 Academic Capstone & License
Developed as an academic Computer Science & Engineering capstone project in Human-Computer Interaction (HCI).
Released under the **MIT License**.
